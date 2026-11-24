# LIMO Pro 车载环境记录

采集日期为 2026-11-18（北京时间）。在本机通过 `ssh LimoPro` 连接小车，读取系统和设备信息，检查两套 ROS 工作区并解析基础启动文件。

手册章节、配置差异和已找到的巡检示例见[资料索引](README.md)。

## 连接和系统

| 项目 | 实测结果 |
| --- | --- |
| SSH | 本机别名 `LimoPro`，用户 `agilex`，SSH 端口 `22`，车载主机名 `master` |
| 本次局域网地址 | `wlan0` 为 `192.168.137.175/24`。重连时以实际地址为准 |
| 车载计算机 | NVIDIA Orin Nano Developer Kit，ARM64，系统可用内存总量约 7.3 GiB |
| 系统 | Ubuntu 20.04.6 LTS，内核 `5.10.120-tegra`，NVIDIA Jetson Linux `R35.4.1` |

## ROS 工作区

小车的 `~/.bashrc` 设置了交互菜单 `ros:noetic(1) foxy(2) ?`。两个环境都能加载并找到 LIMO 底盘和启动包。

| 菜单选项 | ROS 版本 | 小车端工作区 | 工作区环境脚本 | LIMO 源码位置与提交 |
| --- | --- | --- | --- | --- |
| `1` | ROS 1 Noetic | `/home/agilex/agilex_ws` | `devel/setup.bash` | `src/limo_ros`，`4d7dc93` |
| `2` | ROS 2 Foxy | `/home/agilex/limo_ros2_ws` | `install/setup.bash` | `src/limo_ros2`，`77dad8a` |

- **Noetic** 的交互配置为 `ROS_MASTER_URI=http://master:11311`、`ROS_HOSTNAME=master`。本次 `master` 在车端解析为 `127.0.1.1`。后续若从其他设备接入 ROS 1，要核实该设备解析到的车端地址。
- **Foxy** 的交互配置将 `ROS_DOMAIN_ID` 设为 `2`。本次在该域查询 ROS 2 节点列表，结果为空。
- **采集时状态**　Noetic 的 `rosnode list` 未能连接到 ROS master。两套环境的 ROS 日志目录均可从 `~/.ros/log` 开始查找，目录已存在。

## 设备和软件接口

| 设备 | 系统识别和现有驱动配置 |
| --- | --- |
| 底盘 | 两套 `limo_base` 默认串口均为 `/dev/ttyTHS0`，设备存在，`agilex` 用户有读写权限 |
| 激光雷达 | `/dev/ydlidar` 指向 `/dev/ttyUSB0`。Noetic 使用 YDLIDAR `Tmini.launch`，Foxy 的 YDLIDAR 启动文件默认加载 `TminiPro.yaml`。两者配置中雷达坐标系均为 `laser_link` |
| 深度相机 | 系统识别为 Orbbec Dabai DC1，对应 `/dev/video0` 和 `/dev/video1`。Noetic 有 `ros_astra_camera/launch/dabai_dc1.launch`，Foxy 已安装的 `orbbec_camera` 提供 `dabai.launch.py` 和 `dabai_d1.launch.py` |
| IMU | 底盘驱动代码发布 `/imu`，基础启动文件定义 `base_link` 到 `imu_link` 的静态变换 |

现有驱动代码中的接口如下，实际发布和订阅情况待启动后核对。

| 话题 | 用途 |
| --- | --- |
| `/cmd_vel` | 底盘订阅的速度指令 |
| `/odom` | 底盘里程计 |
| `/limo_status` | 控制模式、电池电压、错误码和运动模式 |
| `/imu` | IMU 数据 |
| `/scan` | 激光雷达扫描数据 |

## 核实的启动与导航入口

| ROS 环境 | 基础启动入口 | 本次验证 |
| --- | --- | --- |
| Noetic | `roslaunch limo_bringup limo_start.launch` | 用 `roslaunch --nodes` 成功解析出底盘、雷达和静态坐标变换节点 |
| Foxy | `ros2 launch limo_bringup limo_start.launch.py` | 用 `--show-args` 成功解析已安装的启动文件，文件包含底盘、雷达和静态坐标变换 |

相机驱动有独立启动文件。两套基础启动入口都声明了相机坐标变换，相机取流需单独验证。

| ROS 环境 | 现有建图和导航资产 | 已检查的默认地图 |
| --- | --- | --- |
| Noetic | `limo_gmapping.launch`、`limo_cartographer.launch`，以及使用 AMCL 和 `move_base` 的差速、阿克曼导航入口 | `limo_navigation_diff.launch` 引用 `map1017.yaml`，`limo_navigation_ackerman.launch` 引用 `map11.yaml`。两份地图的 YAML 和 PGM 都能读取，位于 `/home/agilex/agilex_ws/src/limo_ros/limo_bringup/maps` |
| Foxy | `cartographer.launch.py`、已安装的 `slam_toolbox`，以及 `limo_nav2.launch.py`、`limo_nav2_ackmann.launch.py` | 两个 Nav2 入口默认使用 `map1021.yaml`。YAML 和 PGM 都能读取，位于 `/home/agilex/limo_ros2_ws/install/limo_bringup/share/limo_bringup/maps` |

## 待实车验证

- 两套 ROS 中实际使用的版本，以及底盘当前的运动模式。
- 开机自启方式、基础启动和停止流程，以及 `/limo_status`、`/odom`、`/imu`、`/scan` 和相机数据是否正常。
- 现有地图对应的实际场地、初始定位点，以及遥控和导航测试结果。

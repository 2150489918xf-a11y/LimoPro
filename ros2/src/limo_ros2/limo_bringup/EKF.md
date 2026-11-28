# 固定 EKF 局部里程计

已撤回算法注册表与方案选择机制。保留原有底盘、雷达和 Cartographer 使用方式，
`limo_start.launch.py` 现在固定使用 `robot_localization/ekf_node`。
小车显示模型继续保留。

## 看实车局部里程计

在加载 ROS 2 Foxy 和工作区环境的终端中：

```bash
ros2 launch limo_bringup limo_start.launch.py rviz:=true
```

这条命令启动一套底盘和雷达、EKF、模型发布器与 RViz。不需要启动建图或 AMCL。
RViz 的固定坐标系是 `odom`：绿色箭头为 EKF `/odom`，橙色箭头为 `/odom/raw`，
模型跟随 EKF 的 TF。箭头保留最近一段轨迹，移动超过 5 cm 或转角超过约 2.9° 时增加箭头。
静止时两套轨迹可能重叠。橙色轨迹用于对照，不是定位真值。

已有底盘/雷达进程时先结束旧会话，不能重复打开串口。`Ctrl+C` 可停止当前启动的整套节点。
如果本次部署已经启动了观察窗口，直接在该窗口观察，不要再次执行同一启动命令。

可先用遥控器缓慢直行、转弯、停车和回到起点，观察轨迹、停车漂移和雷达点是否稳定。
这些现象只能辅助检查；判断精度改善仍需要外部参考测量。本次没有自动发送实车行驶指令。

## 建图时使用

两个终端分别运行：

```bash
ros2 launch limo_bringup limo_start.launch.py
ros2 launch limo_bringup cartographer.launch.py
```

基础层默认不启用局部观察 RViz，Cartographer 入口负责自己的模型和建图 RViz。
不要在 `rviz:=true` 的局部观察会话上再叠加默认 Cartographer 模型发布器。

## 数据流与参数

```text
底盘唯一串口驱动 ── /odom/raw：vx、vy ──┐
                 └─ /imu：gyro Z ──────┤
                                      ↓
                                 local_ekf
                                      ├── /odom
                                      └── odom → base_link
```

底盘 `pub_odom_tf=false`；EKF 是局部 TF 的唯一发布者，输出频率为 50 Hz。
原始底盘位姿已经使用 IMU yaw，EKF 不再次融合它；仅使用底盘 vx/vy 和 IMU Z 轴角速度，
二维模式，不融合绝对航向或加速度。建图/全局定位仍单独负责 `map → odom`。

参数文件为 [`param/ekf_odom.yaml`](param/ekf_odom.yaml)，是普通 ROS 参数文件，没有算法注册层。
底盘驱动保留必要的话题与数据修正：里程计输出参数生效、非零速度/陀螺方差、
明确初始化，并修复原始 yaw 的小增量丢弃和跨界问题。
速度方差默认 `0.0025 (m/s)^2`，陀螺方差默认 `0.0004 (rad/s)^2`，均为待标定初值。

## 构建与检查

车上已有 ROS 2 `robot_localization 3.1.2`；其他 Foxy 环境可安装对应二进制依赖：

```bash
sudo apt install ros-foxy-robot-localization
cd ~/limo_ros2_ws
colcon build --packages-select limo_base limo_bringup --cmake-args -DBUILD_TESTING=ON
source install/setup.bash
colcon test --packages-select limo_bringup
colcon test-result --test-result-base build/limo_bringup
```

集成测试只使用虚拟串口与隔离 ROS domain，验证：真实启动入口固定启动 EKF，
速度/IMU 数据带有非零方差，原始航向和角速度与 IMU 矛盾时 EKF 仍按配置的 gyro 响应，
底盘关闭局部 TF、滤波器启用局部 TF。不会读写实车串口。

2026-11-28 车端构建与上述集成测试通过，已启动 `rviz:=true` 的实车观察会话。
10 秒运行检查收到 EKF 501 帧、原始里程计 500 帧、IMU 1000 帧、雷达 101 帧、
关节状态 100 帧、局部 TF 500 帧；测量方差已生效，输出与协方差均为有限值。
RViz 已确认显示模型、雷达和两种里程计箭头。仅验证静止运行和数据链，未自动驾驶车辆，
尚未完成真实行驶精度评估。

运行时检查：

```bash
ros2 topic info /odom --verbose       # 发布者应为 local_ekf
ros2 topic info /odom/raw --verbose   # 发布者应为 limo_base
ros2 param get /limo_base pub_odom_tf # false
ros2 param get /local_ekf publish_tf  # true
ros2 run tf2_ros tf2_echo odom base_link
```

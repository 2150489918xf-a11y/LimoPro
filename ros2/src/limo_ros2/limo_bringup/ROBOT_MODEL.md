# 建图时显示实车模型

`cartographer.launch.py` 默认包含 `limo_model.launch.py`，启动
`robot_state_publisher` 和无 GUI 的 `joint_state_publisher`。前者发布
`/robot_description` 及模型部件 TF，后者以 10 Hz 发布四个车轮的默认关节位置。
RViz 的 RobotModel 已订阅 `/robot_description`，使用 Transient Local 接收模型。
地图设置为 Draw Behind，避免地图平面遮挡位于 `base_link` 下方的车轮。

## 启动

两个终端使用相同的 Foxy 环境，先启动一套底盘和雷达，再启动建图：

```bash
ros2 launch limo_bringup limo_start.launch.py
ros2 launch limo_bringup cartographer.launch.py
```

向已经运行的建图会话补充模型，可在另一终端单独运行：

```bash
ros2 launch limo_bringup limo_model.launch.py
```

随后在已有 RViz 中把 RobotModel 的 Description Topic 设为
`/robot_description`，Durability Policy 设为 Transient Local，并启用
Map 的 Draw Behind。无需重启底盘或丢弃正在建立的地图。
后续重新启动建图前，应先停止这份单独运行的模型发布进程，避免重复启动。
需要复用已有模型发布节点时，可以关闭建图入口自带的模型：

```bash
ros2 launch limo_bringup cartographer.launch.py use_robot_model:=false
```

## TF 所有权和模型范围

```text
map -> odom                         Cartographer
odom -> base_link                   limo_base
base_link -> laser_link 等传感器    limo_start 的静态 TF
base_link -> limo_visual_body_link  robot_state_publisher
base_link -> limo_visual_*_wheel_link
                                   robot_state_publisher + joint_state_publisher
```

`urdf/limo_mapping.urdf.xacro` 以 `base_link` 为根，仅定义车体和四轮的显示几何。
它不定义 `base_footprint`、`odom`、`map` 或传感器 link，避免与实车已有变换冲突。
部件外观偏移和车轮布局参考车端原有 `limo_four_diff.xacro`，只用于显示，
不改变底盘运动学、雷达外参、定位输入或碰撞模型。关节位置默认保持零，
不表示已经读取编码器，也不模拟真实轮速或阿克曼转角。

外观使用车端已有 `limo_description/meshes/limo_base.dae` 和
`limo_wheel.dae`。这两个厂商模型资源不在本仓库重复分发；部署到新环境时，
需另外提供含这些资源的 `limo_description` 包。运行依赖已在 `package.xml` 声明。

更新本包后，需要在车端工作区重新构建并加载环境：

```bash
colcon build --packages-select limo_bringup
source install/setup.bash
```

## 检查

```bash
ros2 node list
ros2 topic info /robot_description -v
ros2 topic echo /joint_states
ros2 run tf2_ros tf2_echo base_link limo_visual_front_left_wheel_link
```

应只有一份模型发布节点；每个模型 link 具有唯一父坐标系。
模型可以跟随 `base_link` 在地图中移动，四个轮子在没有实际关节反馈时保持默认姿态。

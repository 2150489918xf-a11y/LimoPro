
建图入口现已默认加载实车显示模型，模型依赖、TF 分工和已运行会话的接入方法见
[建图模型显示说明](ROBOT_MODEL.md)。下面保留历史操作记录，其中部分建图命令不是当前推荐入口。

下面的脚本一条一条运行， 注意不能在后台运行
 
# 导航

```shell
rviz2
## 启动底盘
ros2 launch limo_bringup limo_start.launch.py
sleep 2
## 启动导航
ros2 launch limo_bringup limo_navigation.launch.py
sleep 2
## 启动定位
ros2 launch limo_bringup limo_localization.launch.py
```

# 建图

```shell
ros2 launch limo_bringup limo_start.launch.py
ros2 launch build_map_2d revo_build_map_2d.launch.py
#上面三条指令启动之后，用遥控器控制车子行走
# 建完图保存， 放到 limo_bringup/maps 里， 再 colcon build 编译一下XXX
```


# 键盘控制

```shell
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 launch limo_bringup limo_start.launch.py
```

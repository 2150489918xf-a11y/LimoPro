"""Start the chassis and lidar with fixed EKF local odometry."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    base_dir = get_package_share_directory('limo_base')
    lidar_dir = get_package_share_directory('ydlidar_ros2_driver')
    bringup_dir = get_package_share_directory('limo_bringup')
    get_package_share_directory('robot_localization')
    use_sim_time = LaunchConfiguration('use_sim_time')

    actions = [
        DeclareLaunchArgument('port_name', default_value='ttyTHS0'),
        DeclareLaunchArgument('use_mcnamu', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('start_lidar', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='Show local EKF and raw odometry with the robot model'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(base_dir, 'launch', 'limo_base.launch.py')),
            launch_arguments={
                'port_name': LaunchConfiguration('port_name'),
                'use_mcnamu': LaunchConfiguration('use_mcnamu'),
                'use_sim_time': use_sim_time,
                'odom_topic_name': '/odom/raw',
                'pub_odom_tf': 'false',
            }.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(lidar_dir, 'launch', 'ydlidar_launch.py')),
            condition=IfCondition(LaunchConfiguration('start_lidar'))),
        Node(
            package='robot_localization', executable='ekf_node', name='local_ekf',
            output='screen',
            parameters=[os.path.join(bringup_dir, 'param', 'ekf_odom.yaml'),
                        {'use_sim_time': use_sim_time}],
            remappings=[('odometry/filtered', '/odom')]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(bringup_dir, 'launch', 'limo_model.launch.py')),
            condition=IfCondition(LaunchConfiguration('rviz')),
            launch_arguments={'use_sim_time': use_sim_time}.items()),
        Node(
            package='rviz2', executable='rviz2', name='rviz2',
            condition=IfCondition(LaunchConfiguration('rviz')),
            arguments=['-d', os.path.join(bringup_dir, 'rviz', 'ekf_odom.rviz')],
            parameters=[{'use_sim_time': use_sim_time}]),
    ]
    for name, xyz, child in (
            ('base_to_laser', ['0.18', '0', '0'], 'laser_link'),
            ('base_to_camera', ['0.18', '0', '0.18'], 'camera_link'),
            ('base_to_imu', ['0', '0', '0'], 'imu_link')):
        actions.append(Node(
            package='tf2_ros', executable='static_transform_publisher', name=name,
            arguments=xyz + ['0', '0', '0', '1', 'base_link', child],
            parameters=[{'use_sim_time': use_sim_time}]))
    return LaunchDescription(actions)

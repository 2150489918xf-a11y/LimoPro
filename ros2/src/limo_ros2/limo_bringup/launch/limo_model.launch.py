"""Publish a display-only LIMO model without taking ownership of sensor TF."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    bringup_dir = get_package_share_directory('limo_bringup')
    # Fail early if the vehicle's external mesh package has not been installed.
    get_package_share_directory('limo_description')
    model_file = os.path.join(bringup_dir, 'urdf', 'limo_mapping.urdf.xacro')
    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_description = ParameterValue(
        Command(['xacro ', model_file]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': use_sim_time,
            }]),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                # No measured wheel joints are exposed by limo_base. Publish
                # stationary wheel poses for visualization, not fake odometry.
                'rate': 10,
            }]),
    ])

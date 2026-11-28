import os
import launch
import launch_ros

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    port_name_arg = DeclareLaunchArgument('port_name', default_value='ttyTHS0',
                                         description='usb bus name, e.g. ttyTHS1')
    odom_frame_arg = DeclareLaunchArgument('odom_frame', default_value='odom',
                                           description='Odometry frame id')
    base_link_frame_arg = DeclareLaunchArgument('base_frame', default_value='base_link',
                                                description='Base link frame id')
    odom_topic_arg = DeclareLaunchArgument('odom_topic_name', default_value='odom',
                                           description='Odometry topic name')
    odom_tf_arg = DeclareLaunchArgument('pub_odom_tf', default_value='True',
                                           description='Odometry topic name')
    sim_control_rate_arg = DeclareLaunchArgument('control_rate', default_value='50',
                                                 description='Simulation control loop update rate')
    use_mcnamu_arg = DeclareLaunchArgument('use_mcnamu', default_value='False',
                                                 description='use mcnamu')
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='false')
    linear_variance_arg = DeclareLaunchArgument('twist_linear_variance', default_value='0.0025')
    angular_variance_arg = DeclareLaunchArgument('twist_angular_variance', default_value='0.0025')
    gyro_variance_arg = DeclareLaunchArgument('imu_angular_velocity_variance', default_value='0.0004')
    


    limo_base_node = launch_ros.actions.Node(
        package='limo_base',
        executable='limo_base',  #foxy executable='limo_base',
        output='screen',
        emulate_tty=True,
        parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'port_name': launch.substitutions.LaunchConfiguration('port_name'),                
                'odom_frame': launch.substitutions.LaunchConfiguration('odom_frame'),
                'base_frame': launch.substitutions.LaunchConfiguration('base_frame'),
                'odom_topic_name': launch.substitutions.LaunchConfiguration('odom_topic_name'),
                'pub_odom_tf': launch.substitutions.LaunchConfiguration('pub_odom_tf'),
                'control_rate': launch.substitutions.LaunchConfiguration('control_rate'),
                'use_mcnamu': launch.substitutions.LaunchConfiguration('use_mcnamu'),
                'twist_linear_variance': LaunchConfiguration('twist_linear_variance'),
                'twist_angular_variance': LaunchConfiguration('twist_angular_variance'),
                'imu_angular_velocity_variance': LaunchConfiguration('imu_angular_velocity_variance'),

        }])

    return LaunchDescription([
        use_sim_time_arg,
        linear_variance_arg,
        angular_variance_arg,
        gyro_variance_arg,
        port_name_arg,        
        odom_frame_arg,
        base_link_frame_arg,
        odom_topic_arg,
        odom_tf_arg,
        sim_control_rate_arg,
        use_mcnamu_arg,
        limo_base_node
    ])

"""Start one hardware stack and select local odometry from a YAML registry."""

import math
import os

import yaml
from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def load_profile(path, requested):
    """Validate the selected profile before any serial driver is started."""
    with open(path, encoding='utf-8') as stream:
        registry = yaml.safe_load(stream)
    if not isinstance(registry, dict) or registry.get('schema_version') != 1:
        raise ValueError('Local odometry registry must have schema_version: 1')
    profiles = registry.get('profiles', {})
    selected = registry.get('default_profile') if requested == 'default' else requested
    if selected not in profiles:
        raise ValueError('Unknown odometry profile {!r}. Available: {}'.format(
            selected, ', '.join(sorted(profiles))))
    profile = profiles[selected]
    driver = profile['driver']
    nodes = profile.get('nodes', [])
    if not isinstance(driver.get('publish_tf'), bool):
        raise ValueError('driver.publish_tf must be a YAML boolean')
    if not isinstance(driver.get('odom_topic'), str) or not driver['odom_topic'].startswith('/'):
        raise ValueError('driver.odom_topic must be an absolute topic')
    if not isinstance(nodes, list):
        raise ValueError('nodes must be a list')
    if nodes:
        if driver['publish_tf'] or driver['odom_topic'] == '/odom':
            raise ValueError('Estimator profiles require driver TF off and a separate raw topic')
    elif not driver['publish_tf'] or driver['odom_topic'] != '/odom':
        raise ValueError('A passthrough profile must publish /odom and its TF from the driver')
    for key in ('twist_linear_variance', 'twist_angular_variance', 'imu_angular_velocity_variance'):
        if key in driver:
            value = driver[key]
            if (isinstance(value, bool) or not isinstance(value, (float, int))
                    or not math.isfinite(value) or value <= 0):
                raise ValueError('driver.{} must be a finite positive variance'.format(key))
    names = set()
    for node in nodes:
        for key in ('package', 'executable', 'name'):
            if not isinstance(node.get(key), str) or not node[key]:
                raise ValueError('Each estimator node requires {}'.format(key))
        if node['name'] in names:
            raise ValueError('Duplicate estimator node name: ' + node['name'])
        names.add(node['name'])
        if not isinstance(node.get('parameters', {}), dict):
            raise ValueError('Estimator parameters must be a mapping')
        remaps = node.get('remappings', [])
        if not all(isinstance(pair, list) and len(pair) == 2
                   and all(isinstance(value, str) for value in pair) for pair in remaps):
            raise ValueError('remappings must be a list of [source, destination] pairs')
    return selected, profile


def start_stack(context):
    path = LaunchConfiguration('odometry_config').perform(context)
    selected, profile = load_profile(path, LaunchConfiguration('odometry').perform(context))
    driver = profile['driver']
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'

    # Resolve every selected package now: invalid profiles fail before opening ports.
    base_dir = get_package_share_directory('limo_base')
    estimator_nodes = []
    for spec in profile.get('nodes', []):
        prefix = get_package_prefix(spec['package'])
        executable = os.path.join(prefix, 'lib', spec['package'], spec['executable'])
        if not os.access(executable, os.X_OK):
            raise ValueError('Estimator executable is unavailable: ' + executable)
        estimator_nodes.append(Node(
            package=spec['package'], executable=spec['executable'], name=spec['name'],
            output='screen',
            parameters=[dict(spec.get('parameters', {}), use_sim_time=use_sim_time)],
            remappings=[tuple(pair) for pair in spec.get('remappings', [])],
        ))

    start_lidar = LaunchConfiguration('start_lidar').perform(context).lower() == 'true'
    lidar_dir = get_package_share_directory('ydlidar_ros2_driver') if start_lidar else None
    base_args = {key: LaunchConfiguration(key).perform(context)
                 for key in ('port_name', 'use_mcnamu', 'control_rate', 'use_sim_time')}
    base_args.update({
        'odom_frame': 'odom', 'base_frame': 'base_link',
        'odom_topic_name': driver['odom_topic'],
        'pub_odom_tf': str(driver['publish_tf']).lower(),
    })
    for key in ('twist_linear_variance', 'twist_angular_variance', 'imu_angular_velocity_variance'):
        if key in driver:
            base_args[key] = str(driver[key])

    actions = [
        LogInfo(msg='Local odometry profile: {} ({})'.format(selected, path)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(base_dir, 'launch', 'limo_base.launch.py')),
            launch_arguments=base_args.items()),
    ]
    if start_lidar:
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(lidar_dir, 'launch', 'ydlidar_launch.py'))))
    for name, xyz, child in (
            ('base_to_laser', ['0.18', '0', '0'], 'laser_link'),
            ('base_to_camera', ['0.18', '0', '0.18'], 'camera_link'),
            ('base_to_imu', ['0', '0', '0'], 'imu_link')):
        actions.append(Node(
            package='tf2_ros', executable='static_transform_publisher', name=name,
            arguments=xyz + ['0', '0', '0', '1', 'base_link', child],
            parameters=[{'use_sim_time': use_sim_time}]))
    return actions + estimator_nodes


def generate_launch_description():
    default_registry = os.path.join(
        get_package_share_directory('limo_bringup'), 'param', 'local_odometry.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('odometry', default_value='default',
                              description='Profile in local_odometry.yaml: default, raw, ekf'),
        DeclareLaunchArgument('odometry_config', default_value=default_registry,
                              description='Local odometry algorithm/profile registry'),
        DeclareLaunchArgument('port_name', default_value='ttyTHS0'),
        DeclareLaunchArgument('use_mcnamu', default_value='false'),
        DeclareLaunchArgument('control_rate', default_value='50'),
        DeclareLaunchArgument('use_sim_time', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('start_lidar', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=start_stack),
    ])

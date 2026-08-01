import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('ardupilot_mavros_utils')

    default_pluginlists_path = os.path.join(pkg_share, 'config', 'apm_pluginlists.yaml')
    default_config_path = os.path.join(pkg_share, 'config', 'apm_config.yaml')

    # Declare all configurable launch arguments
    fcu_url_arg = DeclareLaunchArgument(
        'fcu_url',
        default_value='/dev/ttyACM0:57600',
        description='FCU connection URL'
    )
    gcs_url_arg = DeclareLaunchArgument(
        'gcs_url',
        default_value='',
        description='GCS proxy URL (leave blank if none)'
    )
    tgt_system_arg = DeclareLaunchArgument(
        'tgt_system',
        default_value='1',
        description='Target MAVLink system ID'
    )
    tgt_component_arg = DeclareLaunchArgument(
        'tgt_component',
        default_value='1',
        description='Target MAVLink component ID'
    )
    system_id_arg = DeclareLaunchArgument(
        'system_id',
        default_value='255',
        description='MAVROS local system ID'
    )
    component_id_arg = DeclareLaunchArgument(
        'component_id',
        default_value='240',
        description='MAVROS local component ID'
    )
    log_output_arg = DeclareLaunchArgument(
        'log_output',
        default_value='screen',
        description='Log output target'
    )
    fcu_protocol_arg = DeclareLaunchArgument(
        'fcu_protocol',
        default_value='v2.0',
        description='MAVLink FCU protocol version'
    )
    respawn_mavros_arg = DeclareLaunchArgument(
        'respawn_mavros',
        default_value='false',
        description='Whether to respawn MAVROS if it crashes'
    )
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='mavros',
        description='ROS namespace for MAVROS nodes'
    )
    pluginlists_yaml_arg = DeclareLaunchArgument(
        'pluginlists_yaml',
        default_value=default_pluginlists_path,
        description='Path to MAVROS plugin blacklist/whitelist YAML'
    )
    config_yaml_arg = DeclareLaunchArgument(
        'config_yaml',
        default_value=default_config_path,
        description='Path to MAVROS general config YAML'
    )

    # Define the MAVROS node with target IDs and local system/component IDs
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        namespace=LaunchConfiguration('namespace'),
        output=LaunchConfiguration('log_output'),
        respawn=LaunchConfiguration('respawn_mavros'),
        parameters=[
            {
                'fcu_url': LaunchConfiguration('fcu_url'),
                'gcs_url': LaunchConfiguration('gcs_url'),
                'tgt_system': LaunchConfiguration('tgt_system'),
                'tgt_component': LaunchConfiguration('tgt_component'),
                'system_id': LaunchConfiguration('system_id'),
                'component_id': LaunchConfiguration('component_id'),
                'fcu_protocol': LaunchConfiguration('fcu_protocol'),
            },
            LaunchConfiguration('pluginlists_yaml'),
            LaunchConfiguration('config_yaml'),
        ]
    )

    return LaunchDescription([
        fcu_url_arg,
        gcs_url_arg,
        tgt_system_arg,
        tgt_component_arg,
        system_id_arg,
        component_id_arg,
        log_output_arg,
        fcu_protocol_arg,
        respawn_mavros_arg,
        namespace_arg,
        pluginlists_yaml_arg,
        config_yaml_arg,
        mavros_node
    ])

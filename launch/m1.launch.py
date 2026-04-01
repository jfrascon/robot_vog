import os

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from robot_agr_4sw import robot_model_utils


def generate_launch_description() -> LaunchDescription:
    """
    Build the launch description for the m1 robot model.
    """
    robot_model = 'm1'

    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='agr4sw', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('robot_agr_4sw'), 'config', 'example_m1.yaml'),
            description='Path to params file. If empty, the selected model launch picks its default.',
        ),
        DeclareLaunchArgument(
            'bridge_file',
            default_value=os.path.join(
                get_package_share_directory('robot_agr_4sw'), 'config', 'example_m1_bridge.yaml'
            ),
            description='Path to bridge file. If empty, the selected model launch picks its default.',
        ),
    ]

    # Declare the launch arguments for the xacro:args of the selected model
    # These launch arguments configure the robot model when building the robot description with
    # the xacro command.
    ldes.extend(robot_model_utils.declare_launch_arguments(robot_model))

    ldes.extend(
        [
            ####################################################################
            # REMAPPINGS
            ####################################################################
            DeclareLaunchArgument('rsp_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
            # Bridge does not need remappings, since it gets the topics from a file.
            DeclareLaunchArgument(
                'four_swerve_kinematics_node_topic_remappings',
                default_value='',
                description=rlh.TOPIC_REMAPPINGS_DESC,
            ),
            ####################################################################
            # NODE OPTIONS
            ####################################################################
            DeclareLaunchArgument(
                'rsp_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
            ),
            DeclareLaunchArgument(
                'four_swerve_kinematics_node_options',
                default_value=rlh.default_node_options_str(),
                description=rlh.NODE_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'bridge_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
            ),
            ####################################################################
            # LOGGING OPTIONS
            ####################################################################
            DeclareLaunchArgument(
                'rsp_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'four_swerve_kinematics_node_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'bridge_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            ####################################################################
            # NODES
            ####################################################################
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare('robot_agr_4sw'), 'launch', '_rsp.launch.py'])
                ),
                # Forward the xacro:args of the selected model to _rsp.launch.py.
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'robot_model': robot_model,
                    'namespace': LaunchConfiguration('namespace'),
                    'robot_name': LaunchConfiguration('robot_name'),
                    'params_file': LaunchConfiguration('params_file'),
                    'rsp_topic_remappings': LaunchConfiguration('rsp_topic_remappings'),
                    'rsp_node_options': LaunchConfiguration('rsp_node_options'),
                    'rsp_logging_options': LaunchConfiguration('rsp_logging_options'),
                    # Add the LaunchConfigurations associated to the launch arguments declared
                    # based on the xacro:args of the selected model.
                    **{
                        xarg_name: LaunchConfiguration(xarg_name)
                        for xarg_name in robot_model_utils.get_xarg_names(robot_model)
                    },
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare('robot_agr_4sw'), 'launch', '_bridge.launch.py'])
                ),
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'namespace': LaunchConfiguration('namespace'),
                    'robot_name': LaunchConfiguration('robot_name'),
                    'params_file': LaunchConfiguration('params_file'),
                    'bridge_file': LaunchConfiguration('bridge_file'),
                    'bridge_node_options': LaunchConfiguration('bridge_node_options'),
                    'bridge_logging_options': LaunchConfiguration('bridge_logging_options'),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare('ground_vehicle_kinematics'), 'launch', 'four_swerve_kinematics.launch.py']
                    )
                ),
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'namespace': LaunchConfiguration('namespace'),
                    'robot_name': LaunchConfiguration('robot_name'),
                    'params_file': LaunchConfiguration('params_file'),
                    'topic_remappings': LaunchConfiguration('four_swerve_kinematics_node_topic_remappings'),
                    'node_options': LaunchConfiguration('four_swerve_kinematics_node_options'),
                    'logging_options': LaunchConfiguration('four_swerve_kinematics_node_logging_options'),
                }.items(),
            ),
        ]
    )

    return LaunchDescription(ldes)

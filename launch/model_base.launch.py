import os

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetLaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from robot_vog import model_utils


def generate_launch_description() -> LaunchDescription:
    """
    Build the launch description for the `base` model of the `robot_vog`
    package.
    """

    ldes: list[LaunchDescriptionEntity] = [
        SetLaunchConfiguration('robot_type', 'vog'),
        SetLaunchConfiguration('robot_model', 'forklift'),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='vog', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('robot_vog'), 'config', 'example_model_base.yaml'),
            description='Path to params file. If empty, the selected model launch picks its default.',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'bridge_file',
            default_value=os.path.join(
                get_package_share_directory('robot_vog'), 'config', 'example_model_base_bridge.yaml'
            ),
            description='Path to bridge file. If empty, the selected model launch picks its default.',
        ),
    ]

    # Declare the launch arguments for the xacro:args of the selected model
    # These launch arguments configure the robot model when building the robot description with
    # the xacro command.
    ldes.extend(model_utils.declare_launch_arguments(robot_model))

    ldes.extend(
        [
            ####################################################################
            # NODE REMAPPINGS
            ####################################################################
            DeclareLaunchArgument('rsp_node_remappings', default_value='', description=rlh.REMAPPINGS_DESC),
            # Bridge does not need remappings, since it gets the topics from a file.
            DeclareLaunchArgument(
                'four_swerve_kinematics_node_remappings', default_value='', description=rlh.REMAPPINGS_DESC
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
            _include_rsp(robot_model),
            _include_bridge(),
            _include_four_swerve_kinematics(),
        ]
    )

    return LaunchDescription(ldes)


def _include_bridge() -> IncludeLaunchDescription:
    """
    Include the bridge launch file for this model.
    """
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('robot_vog'), 'launch', '_bridge.launch.py'])
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
    )


def _include_four_swerve_kinematics() -> IncludeLaunchDescription:
    """
    Include the four-swerve kinematics launch file for this model.
    """
    return IncludeLaunchDescription(
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
            'node_remappings': LaunchConfiguration('four_swerve_kinematics_node_remappings'),
            'node_options': LaunchConfiguration('four_swerve_kinematics_node_options'),
            'node_logging_options': LaunchConfiguration('four_swerve_kinematics_node_logging_options'),
        }.items(),
    )


def _include_rsp(robot_model: str) -> IncludeLaunchDescription:
    """
    Include the robot state publisher launch file for the selected model.
    """
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('robot_vog'), 'launch', '_rsp.launch.py'])
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'robot_model': robot_model,
            'namespace': LaunchConfiguration('namespace'),
            'robot_name': LaunchConfiguration('robot_name'),
            'params_file': LaunchConfiguration('params_file'),
            'rsp_node_remappings': LaunchConfiguration('rsp_node_remappings'),
            'rsp_node_options': LaunchConfiguration('rsp_node_options'),
            'rsp_logging_options': LaunchConfiguration('rsp_logging_options'),
            **model_utils.get_launch_configuration_entries(robot_model),
        }.items(),
    )

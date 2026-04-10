import os

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetLaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription, LaunchDescriptionEntity
from robot_vog import model_utils


def generate_launch_description() -> LaunchDescription:
    """
    Build the launch description for this model of the `robot_vog` package.
    """

    robot_model = 'base'

    ldes: list[LaunchDescriptionEntity] = [
        SetLaunchConfiguration('robot_type', 'vog'),
        SetLaunchConfiguration('robot_model', robot_model),
        DeclareLaunchArgument('project_namespace', default_value='', description="Project's namespace"),
        DeclareLaunchArgument('robot_name', default_value='vog', description="Robot's name"),
        OpaqueFunction(function=rlh.set_robot_namespace),
        OpaqueFunction(function=rlh.set_robot_prefix),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(
                get_package_share_directory('robot_vog'), 'config', f'model_{robot_model}', 'example_params.yaml'
            ),
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
                get_package_share_directory('robot_vog'), 'config', f'model_{robot_model}', 'example_bridge.yaml'
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
                'rsp_node_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'four_swerve_kinematics_node_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'bridge_node_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            ####################################################################
            # NODES
            ####################################################################
            _include_rsp(),
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
        # Launch file `_bridge.lauch.py` uses the launch context keys:
        # `project_namespace` (def: '')
        # `robot_name` (def: 'vog')
        # `params_file` (def: '')
        # `use_sim_time` (def: 'False')
        # `config_file` (def: '')
        # `subscription_heartbeat` (def: '')
        # `expand_gz_topic_names` (def: '')
        # `override_timestamps_with_wall_time` (def: '')
        # `override_frame_id` (def: '')
        # DeclareLaunchArguments for node remappings, node options and node logging options.
        #
        # Launch context keys used by `_bridge.lauch.py` that do not appear in `launch_arguments`
        # either are already present in the launch context, so there is no need to set them again in
        # `launch_arguments`, or they will be inserted in the launch context with default value when
        # the proper DeclaredLaunchArgument action from the file `_bridge.lauch.py` is executed.
        launch_arguments={
            'config_file': LaunchConfiguration('bridge_file'),
            'bridge_node_options': LaunchConfiguration('bridge_node_options'),
            'bridge_node_logging_options': LaunchConfiguration('bridge_node_logging_options'),
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
        # Launch file `four_swerve_kinematics.lauch.py` uses the launch context keys:
        # `namespace` (def: 'robot')
        # `robot_prefix` (def: 'robot_')
        # `params_file` (def: 'package://ground_vehicle_kinematics/config/example_four_swerve_kinematics.yaml')
        # `use_sim_time` (def: 'False')
        # DeclareLaunchArguments for node remappings, node options and node logging options.
        #
        # Launch context keys used by `four_swerve_kinematics.lauch.py` that do not appear in
        # `launch_arguments` either are already present in the launch context, so there is no need
        # to set them again in `launch_arguments`, or they will be inserted in the launch context
        # with default value when the proper DeclaredLaunchArgument action from the file
        # `four_swerve_kinematics.lauch.py` is executed.
        launch_arguments={
            'node_remappings': LaunchConfiguration('four_swerve_kinematics_node_remappings'),
            'node_options': LaunchConfiguration('four_swerve_kinematics_node_options'),
            'node_logging_options': LaunchConfiguration('four_swerve_kinematics_node_logging_options'),
        }.items(),
    )


def _include_rsp() -> IncludeLaunchDescription:
    """
    Include the robot state publisher launch file for the selected model.
    """
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('robot_vog'), 'launch', '_rsp.launch.py'])
        ),
        # Launch file `_rsp.lauch.py` uses the launch context keys:
        # `project_namespace` (def: '')
        # `robot_model` (def: 'base')
        # `robot_name` (def: 'vog')
        # `params_file` (def: '')
        # `use_sim_time` (def: 'False')
        # `publish_frequency` (def: '')
        # `ignore_timestamp` (def: '')
        # `use_robot_description_topic` (def: '')
        # DeclareLaunchArguments for node remappings, node options and node logging options.
        #
        # Launch context keys used by `_rsp.lauch.py` that do not appear in `launch_arguments`
        # either are already present in the launch context, so there is no need to set them again in
        # `launch_arguments`, or they will be inserted in the launch context with default value when
        # the proper DeclaredLaunchArgument action from the file `_rsp.lauch.py` is executed.
        launch_arguments={
            'node_remappings': LaunchConfiguration('rsp_node_remappings'),
            'node_options': LaunchConfiguration('rsp_node_options'),
            'node_logging_options': LaunchConfiguration('rsp_node_logging_options'),
        }.items(),
    )

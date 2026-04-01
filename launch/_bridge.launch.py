from pathlib import Path
from typing import Any, List

import ros2_launch_helpers as rlh
from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile


def generate_launch_description() -> LaunchDescription:
    """
    Build the Gazebo bridge launch description.
    """
    ldes: List[LaunchDescriptionEntity] = [
        ####################################################################
        # COMMON ARGUMENTS
        ####################################################################
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='agr4sw', description='The unique name for the robot'),
        DeclareLaunchArgument('params_file', default_value='', description='Path to params file'),
        DeclareLaunchArgument('bridge_file', default_value='', description='Path to bridge file'),
        ####################################################################
        # NODE OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'bridge_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        ####################################################################
        # LOGGING OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'bridge_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
        ####################################################################
        # NODES
        ####################################################################
        OpaqueFunction(function=_launch_bridge),
    ]

    return LaunchDescription(ldes)


def _launch_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    Launch the Gazebo bridge for one robot instance.
    """
    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    if not use_sim_time:
        return []

    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)

    bridge_file = LaunchConfiguration('bridge_file').perform(ctx).strip()

    if bridge_file and not Path(bridge_file).is_file():
        raise FileNotFoundError(f"[ERROR][{robot_ns}] Bridge file '{bridge_file}' not found.")

    params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if params_file and not Path(params_file).is_file():
        raise FileNotFoundError(f"[ERROR][{robot_ns}] Params file '{params_file}' not found.")

    parameters: List[Any] = []

    # If bridge_file is empty, start the bridge with an empty config_file value.
    # The node may not bridge the expected topics, but that is left to the caller.
    # If params_file is empty, start the bridge without an external params file.
    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=False))

    parameters.append(
        {
            'use_sim_time': True,
            'config_file': bridge_file,
            'expand_gz_topic_names': True,
            'override_timestamps_with_wall_time': False,
        }
    )

    node_options = rlh.process_node_options(LaunchConfiguration('bridge_node_options').perform(ctx))
    node_name = str(node_options['name']) or 'bridge'

    return [
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('bridge_logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    ]

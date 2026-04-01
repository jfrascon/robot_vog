import os
from pathlib import Path
from typing import Any, List, Tuple

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue

from robot_agr_4sw import robot_model_utils


def generate_launch_description() -> LaunchDescription:
    """
    Build the robot_state_publisher launch description.
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
        # _rsp.launch.py is an internal reusable launch file, but it can also be launched
        # directly from the terminal, so it declares and validates the model xacro:args here.
        # Declare the launch arguments for the xacro:args of the selected model.
        OpaqueFunction(function=_declare_model_launch_arguments),
        ####################################################################
        # REMAPPINGS
        ####################################################################
        DeclareLaunchArgument('rsp_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        ####################################################################
        # NODE OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'rsp_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        ####################################################################
        # LOGGING OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'rsp_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
        ####################################################################
        # NODES
        ####################################################################
        OpaqueFunction(function=_launch_rsp),
    ]

    return LaunchDescription(ldes)


def _build_xacro_command(ctx: LaunchContext) -> Tuple[List[Any], List[str]]:
    """
    Build the xacro command list and collect diagnostics for the selected model.
    """
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)

    xacro_file = os.path.join(get_package_share_directory('robot_agr_4sw'), 'urdf', 'models', f'{robot_model}.xacro')

    if not Path(xacro_file).is_file():
        raise FileNotFoundError(f"[ERROR][{robot_ns}] File '{xacro_file}' not found")

    use_sim_time_lc = LaunchConfiguration('use_sim_time')

    cmd: List[Any] = [
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' use_sim_mode:=',
        use_sim_time_lc,
        ' namespace:=',
        LaunchConfiguration('namespace'),
        ' robot_name:=',
        LaunchConfiguration('robot_name'),
    ]

    use_sim_time_bool = perform_typed_substitution(ctx, normalize_typed_substitution(use_sim_time_lc, bool), bool)

    msgs: List[str] = []

    for xarg_name in robot_model_utils.get_xarg_names(robot_model):
        value = LaunchConfiguration(xarg_name).perform(ctx).strip()

        if xarg_name == 'sim_file':
            # sim_file belongs to the model xargs. Outside simulation this xarg is forced to the
            # empty value. In simulation it falls back to the example file of the selected model.
            if not use_sim_time_bool:
                value = ''
            elif not value:
                value = os.path.join(
                    get_package_share_directory('robot_agr_4sw'), 'config', f'example_{robot_model}_simulation.yaml'
                )

            if value and not Path(value).is_file():
                msgs.append(f"[WARNING][{robot_ns}] Simulation file '{value}' not found")
                value = ''

        cmd.extend([' ', f'{xarg_name}:=', _quote_xarg_value_if_needed(value)])

    return cmd, msgs


def _declare_model_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    Declare the model launch arguments for the selected robot model.
    """
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()

    if not robot_model_utils.model_exists(robot_model):
        raise ValueError(
            f"Model '{robot_model}' for the 'robot_agr_4sw' robot is not available. "
            f'Available robot models: {", ".join(robot_model_utils.get_models())}'
        )

    if not robot_model_utils.model_has_xargs(robot_model):
        return []

    # Declare the launch arguments for the xacro:args of the selected model.
    return robot_model_utils.declare_launch_arguments(robot_model)


def _launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    Launch robot_state_publisher for the selected robot model.
    """
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    ldes: List[LaunchDescriptionEntity] = []

    cmd, msgs = _build_xacro_command(ctx)
    ldes.extend(rlh.to_log_info_actions(msgs))

    params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if params_file and not Path(params_file).is_file():
        raise FileNotFoundError(
            f"[ERROR][{robot_ns}] Params file '{params_file}' does not exist. "
            "Please provide a valid params file via the 'params_file' launch argument."
        )

    parameters: List[Any] = []

    # If params_file is empty, start robot_state_publisher without an external params file.
    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=False))

    parameters.append(
        {
            'use_sim_time': perform_typed_substitution(
                ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
            ),
            'robot_description': ParameterValue(Command(cmd), value_type=str),
            'frame_prefix': '',
            'use_robot_description_topic': False,
        }
    )

    node_options = rlh.process_node_options(LaunchConfiguration('rsp_node_options').perform(ctx))
    node_name = str(node_options['name']) or 'robot_state_publisher'

    ldes.append(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            remappings=rlh.process_topic_remappings(LaunchConfiguration('rsp_topic_remappings').perform(ctx)),
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('rsp_logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes


def _quote_xarg_value_if_needed(raw_value: str) -> str:
    """
    Quote xarg values containing whitespace so xacro parses them as one token.
    """
    return f'"{raw_value}"' if any(ch.isspace() for ch in raw_value) else raw_value

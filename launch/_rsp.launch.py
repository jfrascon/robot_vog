import os
from pathlib import Path
from typing import Any, List, Tuple

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue
from robot_vog import model_utils


def generate_launch_description() -> LaunchDescription:
    """
    Build the internal robot_state_publisher launch description for one model
    wrapper.

    This launch file is meant to be included by `model_*.launch.py`, not to be
    used as the user entry point for the `robot_vog` package.

    The model wrapper is responsible for passing the selected `robot_model` and
    the model-specific `params_file` when an external params file should be
    loaded. If this launch file is called directly and `params_file` is left
    empty, robot_state_publisher starts without an external params file.
    """
    ldes: List[LaunchDescriptionEntity] = [
        DeclareLaunchArgument('project_namespace', default_value='', description='Project namespace'),
        DeclareLaunchArgument(
            'robot_model', default_value='base', choices=model_utils.get_models(), description='Robot model to publish'
        ),
        DeclareLaunchArgument('robot_name', default_value='vog', description='The unique name for the robot'),
        OpaqueFunction(function=rlh.set_robot_namespace),
        OpaqueFunction(function=rlh.set_robot_prefix),
        DeclareLaunchArgument('params_file', default_value='', description='Path to params file'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'publish_frequency',
            default_value='',
            description='Frequency at which robot_state_publisher publishes the TF transforms.'
            'Good default value is 20.0',
        ),
        DeclareLaunchArgument(
            'ignore_timestamp',
            default_value='',
            choices=['True', 'true', 'False', 'false', ''],
            description='If True, robot_state_publisher accepts joint_state messages no matter their timestamp',
        ),
        DeclareLaunchArgument(
            'use_robot_description_topic',
            default_value='',
            choices=['True', 'true', 'False', 'false', ''],
            description='If set, override whether robot_state_publisher uses robot_description as a topic.',
        ),
        # Force the frame prefix to empty string, since the robot_prefix is managed explicitly in
        # this package with robot_prefix.
        SetLaunchConfiguration('frame_prefix', ''),  # DO NOT USE FRAME PREFIX HERE.
        # _rsp.launch.py is an internal reusable launch file, but it can also be launched
        # directly from the terminal, so it declares and validates the model xacro:args here.
        # Declare the launch arguments for the xacro:args of the selected model.
        OpaqueFunction(function=_declare_model_launch_arguments),
        ####################################################################
        # NODE REMAPPINGS
        ####################################################################
        DeclareLaunchArgument('node_remappings', default_value='', description=rlh.REMAPPINGS_DESC),
        ####################################################################
        # NODE OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        ####################################################################
        # LOGGING OPTIONS
        ####################################################################
        DeclareLaunchArgument(
            'node_logging_options',
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
    robot_model = LaunchConfiguration('robot_model').perform(ctx)

    # Get the xacro file for the selected model.
    xacro_file = os.path.join(get_package_share_directory('robot_vog'), 'urdf', 'models', f'model_{robot_model}.xacro')

    if not Path(xacro_file).is_file():
        raise FileNotFoundError(f"File '{xacro_file}' not found")

    use_sim_time_lc = LaunchConfiguration('use_sim_time')

    cmd: List[Any] = [
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' use_sim_mode:=',
        use_sim_time_lc,
        ' namespace:=',
        LaunchConfiguration('project_namespace'),
        ' robot_name:=',
        LaunchConfiguration('robot_name'),
    ]

    use_sim_time_bool = perform_typed_substitution(ctx, normalize_typed_substitution(use_sim_time_lc, bool), bool)

    msgs: List[str] = []

    # Configure the robot's xacro file by means of xacro:args  passed as launch context keys.
    # Iterate over the xacro:arg names of the selected model and get their values from the launch
    # context.
    for xarg_name in model_utils.get_xarg_names(robot_model):
        value = LaunchConfiguration(xarg_name).perform(ctx)

        if xarg_name == 'sim_file':
            # `sim_file` is a xacro argument.
            # When the application is running in real-time mode, the `sim_file` is not used, so
            # its value can be set to false.
            if not use_sim_time_bool:
                value = ''
            # If in simulation-mode, if no sim_file is provided, the default `sim_file` for the
            # selected model is used.
            elif not value:
                value = os.path.join(
                    get_package_share_directory('robot_vog'),
                    'config',
                    f'model_{robot_model}',
                    'example_simulation.yaml',
                )

            if value and not Path(value).is_file():
                msgs.append(f"Simulation file '{value}' not found")
                value = ''

        cmd.extend([' ', f'{xarg_name}:=', _quote_xarg_value_if_needed(value)])

    return cmd, msgs


def _declare_model_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    Declare the model launch arguments for the selected robot model.
    """
    robot_model = LaunchConfiguration('robot_model').perform(ctx)

    if not model_utils.model_exists(robot_model):
        raise ValueError(
            f"Model '{robot_model}' for the 'robot_vog' robot is not available. "
            f'Available robot models: {", ".join(model_utils.get_models())}'
        )

    if not model_utils.model_has_xargs(robot_model):
        return []

    # Declare the launch arguments for the xacro:args of the selected model.
    return model_utils.declare_launch_arguments(robot_model)


def _launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    Launch robot_state_publisher for the selected robot model.

    An empty `params_file` means that no external ROS params file is loaded.
    """
    ldes: List[LaunchDescriptionEntity] = []

    cmd, msgs = _build_xacro_command(ctx)
    ldes.extend(rlh.to_log_info_actions(msgs))

    # If the params_file exists, load it as a ParameterFile.
    # If any parameter is also provided to this launch file, it takes precedence over the
    # params_file.
    # This allows to override specific parameters in the params_file without having to create a new
    # params file.
    parameters: List[Any] = []

    params_file = LaunchConfiguration('params_file').perform(ctx)
    publish_frequency = LaunchConfiguration('publish_frequency').perform(ctx)
    ignore_timestamp = LaunchConfiguration('ignore_timestamp').perform(ctx)
    use_robot_description_topic = LaunchConfiguration('use_robot_description_topic').perform(ctx)
    frame_prefix = LaunchConfiguration('frame_prefix').perform(ctx)

    # If `use_robot_description_topic` is provided, it overrides the value
    # from the params file.

    # Launch context key `frame_prefix` is empty string, since its value was set with
    # SetLaunchConfiguration to empty string.

    if params_file:
        if not Path(params_file).is_file():
            raise FileNotFoundError(f"Params file '{params_file}' does not exist. ")

        parameters.append(ParameterFile(params_file, allow_substs=True))

    if publish_frequency:
        try:
            parameters.append({'publish_frequency': float(publish_frequency)})
        except ValueError as exc:
            raise ValueError(f"Invalid value for publish_frequency: '{publish_frequency}'. Must be a float.") from exc

    if ignore_timestamp:
        parameters.append({'ignore_timestamp': ignore_timestamp.lower() == 'true'})

    if use_robot_description_topic:
        parameters.append({'use_robot_description_topic': use_robot_description_topic.lower() == 'true'})

    if frame_prefix:
        parameters.append({'frame_prefix': frame_prefix})

    # The parameters `use_sim_time` and `robot_description` are always passed to the node after the
    # params_file, if any, so they take precedence over the same parameters from the params file.
    parameters.append(
        {
            'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
            'robot_description': ParameterValue(Command(cmd), value_type=str),
        }
    )

    # node_options include 'name', 'output', 'emulate_tty', 'respawn', 'respawn_delay',
    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'robot_state_publisher'

    if not rlh.is_valid_name(node_name):
        raise RuntimeError(f"The name of the node must be ASCII [A-Za-z0-9_] only: '{node_name}'")

    ldes.append(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name=node_name,
            namespace=LaunchConfiguration('namespace'),
            parameters=parameters,
            remappings=rlh.process_remappings(LaunchConfiguration('node_remappings').perform(ctx)),
            ros_arguments=rlh.process_node_logging_options(LaunchConfiguration('node_logging_options').perform(ctx)),
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

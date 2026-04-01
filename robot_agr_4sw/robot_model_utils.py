"""
Helpers to work with the robot models provided by this package.

This package exposes public robot models through Xacro files such as `m1` and
`m2`.

The file `includes/common.xacro` is not a public robot model. It is an internal
Xacro file that is included by the public robot models, and it defines the
arguments that are shared by every model of the family.

Each public robot model therefore uses:
- the arguments defined in `includes/common.xacro`
- plus any extra arguments defined in the Xacro file of that specific model

To declare launch arguments for those `xacro:arg` entries, this package uses
an internal YAML-based system:
- `xargs/common.yaml` stores the arguments shared by all public robot models
- `xargs/<model>.yaml` stores the arguments specific to one public model when
  that model defines additional arguments

When the launch code asks for the arguments of one public robot model, this
module resolves them as:
- the arguments from `common.yaml` if that file exists
- plus the arguments from `<model>.yaml` if that file exists

One public robot model therefore has internal xargs if at least one of these
files exists:
- `xargs/common.yaml`
- `xargs/<model>.yaml`
"""

from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import PackageNotFoundError
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch import LaunchDescriptionEntity


def declare_launch_arguments(robot_model: str) -> List[LaunchDescriptionEntity]:
    """
    Return the launch argument declarations for the xargs of one robot model.
    """
    ldes: List[LaunchDescriptionEntity] = []

    for xarg_name, xarg_cfg in _get_xargs(robot_model).items():
        kwargs = {'default_value': xarg_cfg['default_value'], 'description': xarg_cfg['description']}

        if 'choices' in xarg_cfg:
            kwargs['choices'] = xarg_cfg['choices']

        ldes.append(DeclareLaunchArgument(xarg_name, **kwargs))

    return ldes


def get_launch_configurations(robot_model: str) -> Dict[str, LaunchConfiguration]:
    """
    Return launch configurations for the xargs of one robot model.
    """
    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in _get_xargs(robot_model).keys()}


def get_models() -> List[str]:
    """
    Return the public robot models provided by the package xacro files.
    """
    try:
        urdf_dir = _get_urdf_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in urdf_dir.glob('*.xacro') if path.is_file())


def get_models_with_xargs() -> List[str]:
    """
    Return the public robot models that have internal xargs YAML files.
    """
    return [robot_model for robot_model in get_models() if model_has_xargs(robot_model)]


def get_xarg_names(robot_model: str) -> List[str]:
    """
    Return the xarg names for the requested robot model.
    """
    return list(_get_xargs(robot_model).keys())


def model_exists(robot_model: str) -> bool:
    """
    Return whether one public robot model is provided by the package xacro files.
    """
    robot_model = (robot_model or '').strip()

    if not robot_model:
        return False

    return robot_model in get_models()


def model_has_xargs(robot_model: str) -> bool:
    """
    Return whether one public robot model has internal xargs YAML files.
    """
    robot_model = (robot_model or '').strip()

    if not model_exists(robot_model):
        return False

    return _xargs_file_exists('common') or _xargs_file_exists(robot_model)


def _check_xarg_fields(xarg_name: str, xarg_cfg: Dict[str, Any], xargs_file: Path) -> None:
    """
    Validate required fields, allowed fields and field types for one xarg.
    """
    # Each xarg must define these fields. Additional fields are only accepted
    # when they are part of the supported xargs schema.
    required_xarg_fields = {'default_value', 'description'}
    optional_xarg_fields = {'choices'}
    allowed_fields = required_xarg_fields.union(optional_xarg_fields)
    # Get a set of the fields that are present in the xarg configuration. This
    # will be used to check for unknown fields and missing required fields.
    present_fields = set(xarg_cfg.keys())

    # Check for fields that are not part of the supported xargs schema.
    unknown_fields = present_fields.difference(allowed_fields)

    if unknown_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} has fields that are not allowed: '
            f'{sorted(unknown_fields)}. Allowed fields: {sorted(allowed_fields)}.'
        )

    # At this point we know that all fields in the xarg configuration are part
    # of the supported xargs schema, but some required fields may still be
    # missing. Check for that next.
    missing_fields = required_xarg_fields.difference(present_fields)

    if missing_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} is missing required fields: {sorted(missing_fields)}.'
        )

    # At this point we know that all required fields are present and all fields
    # are part of the supported xargs schema, but some fields may have invalid
    # types. Check for that next.
    for field_name, field_value in xarg_cfg.items():
        if field_name == 'choices':
            if not isinstance(field_value, list) or not all(isinstance(choice, str) for choice in field_value):
                raise ValueError(
                    f"Field 'choices' for xarg {xarg_name!r} in file {xargs_file!r} must be a list of strings."
                )
        else:
            if not isinstance(field_value, str):
                raise ValueError(
                    f'Field {field_name!r} for xarg {xarg_name!r} in file {xargs_file!r} must be a string.'
                )


def _get_urdf_dir() -> Path:
    """
    Return the directory that stores robot xacro files.
    """
    # Public robot models are installed under urdf/models in the package share.
    # Resolve that directory through ament in normal ROS execution.
    #
    # Some direct Python test runs import this module from the source tree
    # without sourcing the workspace. In that case, the package share may not be
    # discoverable through ament yet, so fall back to the source-tree layout.
    try:
        urdf_dir = Path(get_package_share_directory('robot_agr_4sw')).joinpath('urdf', 'models')
    except PackageNotFoundError:
        urdf_dir = Path(__file__).resolve().parent.parent.joinpath('urdf', 'models')

    if not urdf_dir.is_dir():
        raise FileNotFoundError(f'URDF directory {urdf_dir!r} not found.')

    return urdf_dir


def _get_xargs_dir() -> Path:
    """
    Return the directory that stores the internal xargs YAML files.
    """
    # The xargs YAML files are an internal implementation detail of this Python
    # module. Resolve them relative to this file instead of treating them as
    # ROS package share resources.
    xargs_dir = Path(__file__).resolve().parent.joinpath('xargs')

    if not xargs_dir.is_dir():
        raise FileNotFoundError(f'Xargs directory {xargs_dir!r} not found.')

    return xargs_dir


def _get_xargs(robot_model: str) -> Dict[str, Dict[str, Any]]:
    """
    Return the internal xargs mapping for the requested robot model.
    """
    robot_model = (robot_model or '').strip()

    if not model_has_xargs(robot_model):
        return {}

    common_xargs: Dict[str, Dict[str, Any]] = {}

    # Resolve the xargs of one public model as:
    # - the arguments from common.yaml when that file exists
    # - plus the arguments from <model>.yaml when that file exists
    # If the model-specific YAML does not exist, the model uses only the common
    # arguments.
    # Both YAML files must define disjoint xargs. If the same xarg appears in
    # both files, this is a model design mistake and the code fails before
    # performing the merge.
    if _xargs_file_exists('common'):
        common_xargs = _load_xargs_yaml('common.yaml')

    if not _xargs_file_exists(robot_model):
        return common_xargs

    model_xargs = _load_xargs_yaml(f'{robot_model}.yaml')

    duplicated_xargs = set(common_xargs).intersection(model_xargs)

    if duplicated_xargs:
        raise ValueError(
            f"Xargs are duplicated between 'common.yaml' and '{robot_model}.yaml': {sorted(duplicated_xargs)}"
        )

    return {**common_xargs, **model_xargs}


def _load_xargs_yaml(xargs_file: str) -> Dict[str, Dict[str, Any]]:
    """
    Load xargs directly from one internal YAML filename.
    """
    # The argument is the YAML filename itself, for example 'common.yaml' or
    # 'm2.yaml'. The file content is a YAML mapping of xarg names to their
    # configurations.
    xargs_file_path = _get_xargs_dir().joinpath(xargs_file)

    if not xargs_file_path.is_file():
        raise FileNotFoundError(f'Xargs file {xargs_file_path!r} not found.')

    # Load the YAML file content as a mapping of xarg names to their
    # configurations. If the file is empty, treat it as an empty mapping.
    with xargs_file_path.open('r', encoding='utf-8') as file:
        loaded = yaml.safe_load(file) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f'Xargs file {xargs_file_path!r} must contain a YAML mapping.')

    # Validate the structure of the loaded xargs. Each xarg configuration must
    # be a mapping.
    for xarg_name, xarg_cfg in loaded.items():
        if not isinstance(xarg_cfg, dict):
            raise ValueError(f'Xarg {xarg_name!r} in file {xargs_file_path!r} must be a YAML mapping.')

        _check_xarg_fields(xarg_name, xarg_cfg, xargs_file_path)

        default_value = xarg_cfg['default_value']

        if default_value.startswith('package://') or default_value.startswith('file://'):
            xarg_cfg['default_value'] = rlh.resolve_file(default_value)

    return loaded


def _xargs_file_exists(name: str) -> bool:
    """
    Return whether one internal xargs YAML file exists.
    """
    return _get_xargs_dir().joinpath(f'{name}.yaml').is_file()

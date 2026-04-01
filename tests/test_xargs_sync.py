import re
from pathlib import Path

from conftest import PACKAGE_DIR

from robot_agr_4sw import robot_model_utils

RESERVED_LAUNCH_ARGS = {'use_sim_mode', 'namespace', 'robot_name'}


def _xacro_arg_names(xacro_file: Path) -> set[str]:
    pattern = re.compile(r'<xacro:arg\s+name="([^"]+)"')
    return set(pattern.findall(xacro_file.read_text(encoding='utf-8')))


def test_xargs_models_match_available_robot_models() -> None:
    assert robot_model_utils.get_models() == ['m1', 'm2']
    assert robot_model_utils.get_models_with_xargs() == ['m1', 'm2']


def test_model_exists_matches_available_robot_models() -> None:
    assert robot_model_utils.model_exists('m1')
    assert robot_model_utils.model_exists('m2')
    assert not robot_model_utils.model_exists('common')
    assert not robot_model_utils.model_exists('')
    assert not robot_model_utils.model_exists('m3')


def test_model_has_xargs_matches_current_xargs_files() -> None:
    assert robot_model_utils.model_has_xargs('m1')
    assert robot_model_utils.model_has_xargs('m2')
    assert not robot_model_utils.model_has_xargs('common')
    assert not robot_model_utils.model_has_xargs('')
    assert not robot_model_utils.model_has_xargs('m3')


def test_common_xargs_match_common_xacro_args() -> None:
    common_arg_names = _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro') - RESERVED_LAUNCH_ARGS

    assert set(robot_model_utils.get_xarg_names('m1')) == common_arg_names


def test_m2_xargs_match_common_and_fork_module_xacro_args() -> None:
    merged_arg_names = (
        _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro')
        | _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'fork_simple_module.xacro')
    ) - RESERVED_LAUNCH_ARGS

    assert set(robot_model_utils.get_xarg_names('m2')) == merged_arg_names

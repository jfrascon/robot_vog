import re
from pathlib import Path

from conftest import PACKAGE_DIR

from robot_vog import model_utils

RESERVED_LAUNCH_ARGS = {'use_sim_mode', 'namespace', 'robot_name'}


def _xacro_arg_names(xacro_file: Path) -> set[str]:
    pattern = re.compile(r'<xacro:arg\s+name="([^"]+)"')
    return set(pattern.findall(xacro_file.read_text(encoding='utf-8')))


def _xacro_arg_defaults(xacro_file: Path) -> dict[str, str]:
    pattern = re.compile(r'<xacro:arg\s+name="([^"]+)"\s+default="([^"]*)"')
    return dict(pattern.findall(xacro_file.read_text(encoding='utf-8')))


def test_xargs_models_match_available_robot_models() -> None:
    assert model_utils.get_models() == ['base', 'forklift']
    assert model_utils.get_models_with_xargs() == ['base', 'forklift']


def test_model_exists_matches_available_robot_models() -> None:
    assert model_utils.model_exists('base')
    assert model_utils.model_exists('forklift')
    assert not model_utils.model_exists('common')
    assert not model_utils.model_exists('')
    assert not model_utils.model_exists('arm')


def test_model_has_xargs_matches_current_xargs_files() -> None:
    assert model_utils.model_has_xargs('base')
    assert model_utils.model_has_xargs('forklift')
    assert not model_utils.model_has_xargs('common')
    assert not model_utils.model_has_xargs('')
    assert not model_utils.model_has_xargs('arm')


def test_common_xargs_match_common_xacro_args() -> None:
    common_arg_names = _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro') - RESERVED_LAUNCH_ARGS

    assert set(model_utils.get_xarg_names('base')) == common_arg_names


def test_forklift_xargs_match_common_and_fork_module_xacro_args() -> None:
    merged_arg_names = (
        _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro')
        | _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'includes' / 'fork_simple_module.xacro')
    ) - RESERVED_LAUNCH_ARGS

    assert set(model_utils.get_xarg_names('forklift')) == merged_arg_names


def test_common_xargs_defaults_match_common_xacro_defaults() -> None:
    xacro_defaults = _xacro_arg_defaults(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro')
    xacro_defaults = {k: v for k, v in xacro_defaults.items() if k not in RESERVED_LAUNCH_ARGS}

    for xarg_name in xacro_defaults:
        assert model_utils._load_xargs_yaml('common.yaml')[xarg_name]['default_value'] == xacro_defaults[xarg_name]


def test_forklift_xargs_defaults_match_xacro_defaults() -> None:
    common_defaults = _xacro_arg_defaults(PACKAGE_DIR / 'urdf' / 'includes' / 'common.xacro')
    fork_defaults = _xacro_arg_defaults(PACKAGE_DIR / 'urdf' / 'includes' / 'fork_simple_module.xacro')
    merged_defaults = {
        **{k: v for k, v in common_defaults.items() if k not in RESERVED_LAUNCH_ARGS},
        **{k: v for k, v in fork_defaults.items() if k not in RESERVED_LAUNCH_ARGS},
    }

    xargs = model_utils._get_xargs('forklift')

    for xarg_name in merged_defaults:
        assert xargs[xarg_name]['default_value'] == merged_defaults[xarg_name]

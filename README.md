# [`robot_vog`](https://github.com/jfrascon/robot_vog/)

`robot_vog` models one family of ground robots with four steerable wheels.

The package name identifies the robot family. The public models inside that
family use short model names:
- `base`
- `forklift`

The public files inside this package use the prefix `model_` to make it clear
that they belong to one concrete model of the family:
- `urdf/models/model_base.xacro`
- `urdf/models/model_forklift.xacro`
- `launch/model_base.launch.py`
- `launch/model_forklift.launch.py`

## Quick Start

Launch the `base` model:

```bash
ros2 launch robot_vog model_base.launch.py
```

Launch the `forklift` model:

```bash
ros2 launch robot_vog model_forklift.launch.py
```

Launch the `forklift` model in simulation mode:

```bash
ros2 launch robot_vog model_forklift.launch.py use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches the ROS-GZ bridge for the
selected model.

## Public Structure

The public launch entry points are:
- [launch/model_base.launch.py](launch/model_base.launch.py)
- [launch/model_forklift.launch.py](launch/model_forklift.launch.py)

The public Xacro model files are:
- [urdf/models/model_base.xacro](urdf/models/model_base.xacro)
- [urdf/models/model_forklift.xacro](urdf/models/model_forklift.xacro)

The internal reusable launch files are:
- [launch/_rsp.launch.py](launch/_rsp.launch.py)
- [launch/_bridge.launch.py](launch/_bridge.launch.py)

`model_base.launch.py` and `model_forklift.launch.py` are the user entry
points. They fix the short model name internally and reuse the internal launch
files for `robot_state_publisher` and the Gazebo bridge.

## Model Naming

Inside the Python and launch code, the public model identifier is the short
model name:
- `base`
- `forklift`

Inside the file tree, the model files use `model_<robot_model>`:
- `model_base.xacro`
- `model_forklift.xacro`
- `model_base.yaml`
- `model_forklift.yaml`

This package therefore separates:
- the package name: `robot_vog`
- the model name used by launch and Python code: `base` or `forklift`
- the file naming convention used inside the package: `model_<robot_model>`

## Xargs

The xargs system uses one complete YAML file for each public model:
- [robot_vog/xargs/model_base.yaml](robot_vog/xargs/model_base.yaml)
- [robot_vog/xargs/model_forklift.yaml](robot_vog/xargs/model_forklift.yaml)

Each `model_<robot_model>.yaml` file lists every `xacro:arg` exposed by that
public model. The YAML file includes arguments defined by internal Xacro
includes such as `urdf/includes/common.xacro`.

`common.xacro` remains an internal URDF reuse point. It is not a public robot
model and it does not have a launch-facing xargs YAML file.

## Example Configuration Files

Example files are stored in:
- [config/example_model_base.yaml](config/example_model_base.yaml)
- [config/example_model_forklift.yaml](config/example_model_forklift.yaml)
- [config/example_model_base_simulation.yaml](config/example_model_base_simulation.yaml)
- [config/example_model_forklift_simulation.yaml](config/example_model_forklift_simulation.yaml)
- [config/example_model_base_bridge.yaml](config/example_model_base_bridge.yaml)
- [config/example_model_forklift_bridge.yaml](config/example_model_forklift_bridge.yaml)

Typical use:
- use `example_model_*.yaml` for robot and kinematics parameters
- use `example_model_*_simulation.yaml` for Gazebo plugin configuration
- use `example_model_*_bridge.yaml` for ROS <-> Gazebo channel configuration

If `params_file` or `sim_file` are not provided, the model launch file picks
the matching example file for that model. If `bridge_file` is not provided, the
model launch file picks the matching example bridge file.

## Launch Architecture

`model_base.launch.py` and `model_forklift.launch.py` each declare the public
launch arguments for one model launch file. Each one fixes `robot_model`
internally and forwards the model arguments to [launch/_rsp.launch.py](launch/_rsp.launch.py).

[launch/_rsp.launch.py](launch/_rsp.launch.py):
- resolves `urdf/models/model_<robot_model>.xacro`
- declares the xargs of the selected model
- starts `robot_state_publisher`

[launch/_bridge.launch.py](launch/_bridge.launch.py):
- starts the Gazebo bridge node

`four_swerve_kinematics.launch.py` from `ground_vehicle_kinematics` is
included directly from each public model launch file. The kinematics node uses
the `params_file` chosen by that model launch file.

## Inspecting Launch Arguments

To inspect the static launch arguments of one model launch file:

```bash
ros2 launch robot_vog model_base.launch.py --show-args
```

`--show-args` does not include the xargs that are declared dynamically after
the selected model is known. Those dynamic xargs come from the complete
`model_<robot_model>.yaml` file for the selected public model.

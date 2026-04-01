# robot_agr_4sw

`robot_agr_4sw` is a package that models a family of rectangular autonomous ground robots
with four steerable wheels.

The description above uses the term `family` because the package is designed to support multiple robot variants. In this package, the family is identified by the package name and each concrete variant is identified by a robot `model`.
The `m1` model is the base robot, the `m2` model adds a fork module and its current sensor set.
In the future, more robot models can be added, `m3`, `m4`, etc., each with their own set of capabilities and sensors, but all sharing the same base robot description and kinematics.

## Quick Start

Launch the robot without simulation:

```bash
ros2 launch robot_agr_4sw m1.launch.py
```

Launch the `m2` robot:

```bash
ros2 launch robot_agr_4sw m2.launch.py
```

Launch the robot in simulation mode:

```bash
ros2 launch robot_agr_4sw m2.launch.py use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches automatically the ROS-GZ bridge for the robot model, so the topics can be bridged between ROS and Gazebo.

## Main Launch Files

The public launch entry points are:
- [launch/m1.launch.py](launch/m1.launch.py)
- [launch/m2.launch.py](launch/m2.launch.py)

These two launch files are the entry points a user is expected to start directly.
Each one selects its robot model internally .

The package also contains these internal reusable launch files:
- [launch/_rsp.launch.py](launch/_rsp.launch.py)
- [launch/_bridge.launch.py](launch/_bridge.launch.py)

These internal launch files are not the main user entry points. They exist so that `m1.launch.py` and `m2.launch.py` can reuse the `robot_state_publisher` and Gazebo bridge setup without duplicating that code.

Useful launch arguments:
- `use_sim_time`: set to `True` for simulation
- `robot_name`: robot instance name
- `namespace`: namespace prefix for the robot resources
- `params_file`: kinematics / node parameters file
- `sim_file`: simulation plugin configuration file for the selected robot model
- `bridge_file`: Gazebo bridge channel configuration file used by the selected model launch file

To inspect all launch arguments:

```bash
ros2 launch robot_agr_4sw m1.launch.py --show-args
```

`m1.launch.py --show-args` shows the launch arguments that are declared statically in
`launch/m1.launch.py`.

This output does not include the xargs that are declared dynamically after `robot_model`
is read. Those xargs are created from the YAML file that corresponds to the selected robot
model. For example:
- `m1` uses `robot_agr_4sw/xargs/common.yaml`
- `m2` uses `robot_agr_4sw/xargs/common.yaml` plus
  `robot_agr_4sw/xargs/m2.yaml`

This means that `--show-args` is useful to inspect the static launch arguments, but it is
not a complete listing of the xargs that the selected robot model accepts.

## Launch Architecture

`m1.launch.py` and `m2.launch.py` each declare the public launch arguments of that
model launch file. They fix `robot_model` internally and forward the selected model
arguments to `launch/_rsp.launch.py`.

`launch/_rsp.launch.py` builds the `xacro` command, declares the xargs of the selected
model, and starts `robot_state_publisher`.

`launch/_bridge.launch.py` starts the Gazebo bridge node.

`four_swerve_kinematics.launch.py` from `ground_vehicle_kinematics` is included
directly from each model launch file. The kinematics node uses the `params_file`
chosen by `m1.launch.py` or `m2.launch.py`.

## Configuration Files

Example files are stored in:
- [config/example_m1.yaml](config/example_m1.yaml)
- [config/example_m2.yaml](config/example_m2.yaml)
- [config/example_m1_simulation.yaml](config/example_m1_simulation.yaml)
- [config/example_m2_simulation.yaml](config/example_m2_simulation.yaml)
- [config/example_m1_bridge.yaml](config/example_m1_bridge.yaml)
- [config/example_m2_bridge.yaml](config/example_m2_bridge.yaml)

Typical use:
- use `example_*.yaml` for robot and kinematics parameters
- use `example_*_simulation.yaml` for Gazebo plugin configuration
- use `example_*_bridge.yaml` for ROS <-> Gazebo channel configuration

If `params_file` or `sim_file` are not provided, the package picks the matching
example file for the selected model launch file. If `bridge_file` is not
provided, the selected model launch file picks the matching example bridge file.

`sim_file` belongs to the xargs set of the selected robot model, so it is part of the
dynamic xargs mechanism described above. That is why `sim_file` can be accepted by the
launch file even though `ros2 launch ... --show-args` does not list it.

## Robot Models

Currently the package exposes these robot models:
- `m1`
- `m2`

`m1` is the base robot.

`m2` extends the base robot with the current fork module and its sensor set.

## Advanced Use

Most users should choose the launch file that matches the model they want to start:
- [launch/m1.launch.py](launch/m1.launch.py)
- [launch/m2.launch.py](launch/m2.launch.py)

These launch files keep the robot description, kinematics, and bridge aligned for
that concrete model.

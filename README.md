# ardupilot_mavros_utils

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-34a853.svg)](#)

ROS 2 utility package for bridging ArduPilot flight controllers via MAVROS, maintained by the Dartmouth Reality and Robotics Lab.

## Overview

`ardupilot_mavros_utils` provides a minimal MAVROS interface for companion computers. It replaces the default MAVROS configurations with a lab-standardized setup tailored for surface, underwater, and aerial vehicles.

### Key Features
* **Python Launch API:** Uses `apm.launch.py` instead of legacy XML wrappers.
* **Minimal Overheads:** Uses custom `apm_config.yaml` and `apm_pluginlists.yaml` to load only essential plugins.
* **GCS Authority:** Configured with MAVLink System/Component IDs (255/240) to authorize ArduPilot RC overrides.
* **Hardware Agnostic:** Handles MAVROS only. Sensor bringup and logging are managed in external vehicle-specific packages.

## Dependencies

Requires ROS 2 (Jazzy/Humble) and MAVROS.

```bash
sudo apt update
sudo apt install ros-$ROS_DISTRO-mavros ros-$ROS_DISTRO-mavros-extras
```
*Note: The GeographicLib datasets required by MAVROS must be installed prior to use.*

## Usage

### Standalone Launch

```bash
ros2 launch ardupilot_mavros_utils apm.launch.py
```

### Optional Launch Arguments
* `fcu_url`: Flight controller connection string (Default: `/dev/ttyACM0:57600`).
* `gcs_url`: GCS connection string.
* `tgt_system`: Target system ID (Default: `1`).
* `tgt_component`: Target component ID (Default: `1`).

*Note: This is just a subset of the available arguments. You can also pass `namespace`, `log_output`, `fcu_protocol`, `config_yaml`, and `pluginlists_yaml` directly via the launch command to override the defaults.*

Example:
```bash
ros2 launch ardupilot_mavros_utils apm.launch.py fcu_url:=udp://:14550@127.0.0.1:14555
```

### Integration via Python Launch

To include this interface in a top-level robot bringup package:

```python
import os
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

mavros_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory('ardupilot_mavros_utils'), 'launch', 'apm.launch.py')
    ),
    launch_arguments={
        'fcu_url': '/dev/ttyTTYUSB0:57600'
    }.items()
)
```

## Configuration

Located in `config/`:
* `apm_config.yaml`: Stream rates, coordinate frames, and system IDs.
* `apm_pluginlists.yaml`: Explicit MAVROS plugin toggles.

## License & Authors

Licensed under the MIT License. See [LICENSE](LICENSE). 

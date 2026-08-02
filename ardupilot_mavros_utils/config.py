# Copyright 2026 Dartmouth Reality and Robotics Lab
#
# Licensed under the MIT License.

"""Default configuration parameters for ArduPilot MAVROS utilities."""

# Default number of RC channels supported by the interface
# ROS2 currently sets it as 18
DEFAULT_NUM_CHANNELS = 18

# Standard PWM limits
PWM_MIN = 1100
PWM_NEUTRAL = 1500
PWM_MAX = 1900

# Default channel mapping for ardurover (0-indexed array positions)
# https://ardupilot.org/rover/docs/common-rcmap.html
DEFAULT_ROVER_CHANNEL_MAP = {
    'roll': 0,       # Channel 1 -- roll means steering
    'throttle': 2,  # Channel 3
}

# Default channel mapping for ardusub (0-indexed array positions)
# https://ardupilot.org/sub/docs/common-rcmap.html
DEFAULT_SUB_CHANNEL_MAP = {
    'pitch': 0,      # Channel 1
    'roll': 1,     # Channel 2
    'throttle': 2,  # Channel 3 (vertical)
    'yaw': 3,       # Channel 4
    'forward': 4,       # Channel 5
    'lateral': 5,       # Channel 6
}

# ArduPilot Flight Mode Constants (Strings used by MAVROS custom_mode)
MODE_MANUAL = 'MANUAL'
MODE_GUIDED = 'GUIDED'
MODE_AUTO = 'AUTO'
MODE_LOITER = 'LOITER'
MODE_RTL = 'RTL'
MODE_ALT_HOLD = 'ALT_HOLD'
MODE_ACRO = 'ACRO'

# Default service timeout in seconds
DEFAULT_TIMEOUT_SEC = 2.0

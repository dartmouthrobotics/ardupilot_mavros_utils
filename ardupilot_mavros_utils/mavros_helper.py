# Copyright 2026 Dartmouth Reality and Robotics Lab
#
# Licensed under the MIT License.

import asyncio

from contextlib import asynccontextmanager

from ardupilot_mavros_utils.config import (
    DEFAULT_NUM_CHANNELS,
    DEFAULT_TIMEOUT_SEC,
)
from mavros_msgs.msg import OverrideRCIn, State
from mavros_msgs.srv import CommandBool, CommandLong, SetMode
import rclpy
from rclpy.node import Node


class MavrosHelper:
    """
    Helper class to interact with MAVROS services and topics from any ROS 2 Node.

    NOTE ON ARCHITECTURE:
    This class utilizes the modern ROS 2 async/await pattern for all blocking
    service calls (arm, set_mode, set_servo, set_servos_batch). This makes the
    helper 100% immune to deadlocks and safe to use with both SingleThreaded
    and MultiThreaded executors.

    Usage requirement: Any ROS 2 timer or subscriber callback that calls these
    methods must be defined as `async def` and use the `await` keyword.
    Example: `await self.mav.arm()`
    """

    def __init__(self, node: Node, num_channels: int = DEFAULT_NUM_CHANNELS):
        self.node = node

        # Clients for MAVROS services using the provided node
        self.arming_client = self.node.create_client(CommandBool, 'mavros/cmd/arming')
        self.command_client = self.node.create_client(CommandLong, 'mavros/cmd/command')
        self.set_mode_client = self.node.create_client(SetMode, 'mavros/set_mode')

        # Publisher for RC Overrides using the provided node
        self.rc_override_pub = self.node.create_publisher(OverrideRCIn, 'mavros/rc/override', 10)

        # Initialize default override array (8 channels, 0 means no override)
        self.num_channels = num_channels
        self.current_rc_channels = [0] * self.num_channels

        # Check for connection
        self.fcu_connected = False
        self.state_sub = self.node.create_subscription(
            State, 'mavros/state', self._state_cb, 10)

        self.current_mode = ''
        self.is_armed = False

    def _state_cb(self, msg: State):
        self.fcu_connected = msg.connected
        self.is_armed = msg.armed
        self.current_mode = msg.mode

    async def wait_for_connection(self, timeout_sec: float = 30.0) -> bool:
        """Wait asynchronously for MAVROS to establish a connection with the Flight Controller."""
        self.node.get_logger().info('Waiting for FCU connection...')
        start_time = self.node.get_clock().now()
        timeout = rclpy.duration.Duration(seconds=timeout_sec)

        while not self.fcu_connected:
            if (self.node.get_clock().now() - start_time) > timeout:
                self.node.get_logger().error('FCU connection timeout!')
                return False
            await asyncio.sleep(0.5)

        self.node.get_logger().info('FCU connected!')
        return True

    async def arm(self, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> bool:
        """Arms the vehicle asynchronously."""
        return await self._send_arming_request(True, timeout_sec)

    async def disarm(self, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> bool:
        """Disarms the vehicle asynchronously."""
        return await self._send_arming_request(False, timeout_sec)

    async def _send_arming_request(
            self, arm_state: bool, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> bool:
        """Arm or disarm the vehicle asynchronously."""
        if not self.arming_client.wait_for_service(timeout_sec=timeout_sec):
            self.node.get_logger().error('Arming service not available!')
            return False

        request = CommandBool.Request()
        request.value = arm_state

        try:
            future = self.arming_client.call_async(request)

            while not future.done():
                await asyncio.sleep(0.01)

            response = future.result()
            return response.success if response else False
        except Exception as e:
            self.node.get_logger().error(f'Arming service call failed: {e}')
            return False

    async def set_mode(self, mode_string: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> bool:
        """
        Set the vehicle flight mode using a string identifier asynchronously.

        (e.g., 'GUIDED', 'LOITER', 'AUTO' -- see config.py).
        Requires the mavros/set_mode service to be available.
        """
        if not self.set_mode_client.wait_for_service(timeout_sec=timeout_sec):
            self.node.get_logger().error('Set mode service not available!')
            return False

        request = SetMode.Request()
        request.custom_mode = mode_string

        try:
            future = self.set_mode_client.call_async(request)
            while not future.done():
                await asyncio.sleep(0.01)

            response = future.result()
            return response.mode_sent if response else False
        except Exception as e:
            self.node.get_logger().error(f'Failed to set mode to {mode_string}: {e}')
            return False

    def set_rc_override(self, channel_updates: dict):
        """
        Override specific RC channels.

        Passed as a dictionary mapping 1-based channel numbers to PWM values.
        Example: {3: 1600, 4: 1500, 9: 1800}
        Pass 0 for a channel's PWM to release control back to the transmitter.
        """
        msg = OverrideRCIn()
        channels = list(self.current_rc_channels)

        for ch_num, pwm in channel_updates.items():
            # Convert 1-based channel (e.g., Channel 3) to 0-based index (index 2)
            index = ch_num - 1
            if 0 <= index < len(channels):
                channels[index] = int(pwm)
            else:
                self.node.get_logger().warn(
                    f'Channel {ch_num} out of bounds (max {len(channels)})')

        msg.channels = channels
        self.current_rc_channels = channels
        self.rc_override_pub.publish(msg)

    def clear_rc_override(self):
        """
        Instantly release all RC overrides.

        It will  hand full control back to the physical RC transmitter.
        """
        # Reset the internal tracker to all zeros
        self.current_rc_channels = [0] * 18

        msg = OverrideRCIn()
        msg.channels = self.current_rc_channels
        self.rc_override_pub.publish(msg)
        self.node.get_logger().info('RC overrides cleared. Transmitter has control.')

    @asynccontextmanager
    async def temporary_rc_override(self, channel_updates: dict):
        """
        Context manager to temporarily override channels and clear after.

        It ensures they clear automatically when exiting the block.

        Example:
        -------
        async with self.mav.temporary_rc_override({3: 1700}):
                await asyncio.sleep(2.0)

        """
        try:
            self.set_rc_override(channel_updates)
            yield
        finally:
            self.clear_rc_override()

    async def set_servo(self, servo_number: int, pwm: int,
                        timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> bool:
        """
        Send a direct MAVLink command to set an individual servo/motor PWM asynchronously.

        servo_number: Output channel, 1-indexed (e.g., 1, 2, 3...)
        pwm: PWM value (typically 1000 to 2000)
        """
        if not self.command_client.wait_for_service(timeout_sec=timeout_sec):
            self.node.get_logger().error('Command service not available!')
            return False

        request = CommandLong.Request()
        request.command = 183  # 183 is MAV_CMD_DO_SET_SERVO
        request.param1 = float(servo_number)
        request.param2 = float(pwm)

        try:
            future = self.command_client.call_async(request)
            while not future.done():
                await asyncio.sleep(0.01)

            response = future.result()
            return response.success if response else False
        except Exception as e:
            self.node.get_logger().error(f'Servo command service call failed: {e}')
            return False

    async def set_servos_batch(
        self,
        servo_updates: dict,
        delay_sec: float = 0.0,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC
    ) -> bool:
        """
        Send direct MAVLink commands to set multiple individual servo PWMs asynchronously.

        An optional delay between each command is possible. Note the possible delay
        between each command even when delay_sec is 0.0.

        servo_updates: A dictionary mapping servo/output numbers to PWM values.
                    Example: {1: 1500, 2: 1600, 3: 1400}
        delay_sec: Time to wait (in seconds) between successive servo commands.
        """
        success_all = True
        total_servos = len(servo_updates)

        for i, (servo_number, pwm) in enumerate(servo_updates.items(), start=1):
            # Await the individual servo command
            result = await self.set_servo(
                servo_number=servo_number, pwm=pwm, timeout_sec=timeout_sec)

            if not result:
                self.node.get_logger().warn(f'Failed to set servo output {servo_number}')
                success_all = False

            # If a delay is specified and this isn't the last item, yield via asyncio
            if delay_sec > 0.0 and i < total_servos:
                await asyncio.sleep(delay_sec)

        return success_all

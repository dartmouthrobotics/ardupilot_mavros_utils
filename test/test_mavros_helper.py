import asyncio
import threading
import unittest

from ardupilot_mavros_utils.mavros_helper import MavrosHelper

from mavros_msgs.msg import OverrideRCIn, State
from mavros_msgs.srv import CommandBool, CommandLong, SetMode

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node


class MockMavrosNode(Node):
    """A fake MAVROS node that hosts services to test the helper against."""

    def __init__(self):
        super().__init__('mock_mavros')

        # State tracking for assertions
        self.arm_called = False
        self.arm_request_value = False
        self.mode_requested = ''
        self.last_servo_cmd = None
        self.last_rc_msg = None

        # Mock Services
        self.srv_arm = self.create_service(
            CommandBool, 'mavros/cmd/arming', self.arm_cb)
        self.srv_mode = self.create_service(
            SetMode, 'mavros/set_mode', self.mode_cb)
        self.srv_cmd = self.create_service(
            CommandLong, 'mavros/cmd/command', self.cmd_cb)

        # Mock Subscriber
        self.sub_rc = self.create_subscription(
            OverrideRCIn, 'mavros/rc/override', self.rc_cb, 10)

        # Mock Publisher for FCU State (heartbeat/connection status)
        self.state_pub = self.create_publisher(State, 'mavros/state', 10)

        # Publish initial connected state periodically via timer
        self.timer = self.create_timer(0.1, self.publish_state)

    def publish_state(self):
        msg = State()
        msg.connected = True
        msg.armed = True
        msg.mode = 'GUIDED'
        self.state_pub.publish(msg)

    def arm_cb(self, request, response):
        self.arm_called = True
        self.arm_request_value = request.value
        response.success = True
        return response

    def mode_cb(self, request, response):
        self.mode_requested = request.custom_mode
        response.mode_sent = True
        return response

    def cmd_cb(self, request, response):
        # 183 is MAV_CMD_DO_SET_SERVO
        if request.command == 183:
            self.last_servo_cmd = (int(request.param1), int(request.param2))
            response.success = True
        else:
            response.success = False
        return response

    def rc_cb(self, msg):
        self.last_rc_msg = msg


class TestMavrosHelper(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.mock_node = MockMavrosNode()
        cls.test_node = rclpy.create_node('test_node')

        # Run ROS executor in a background thread so async tests can await freely
        cls.executor = MultiThreadedExecutor()
        cls.executor.add_node(cls.mock_node)
        cls.executor.add_node(cls.test_node)

        cls.executor_thread = threading.Thread(target=cls.executor.spin, daemon=True)
        cls.executor_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.executor.shutdown()
        cls.mock_node.destroy_node()
        cls.test_node.destroy_node()
        rclpy.shutdown()
        cls.executor_thread.join(timeout=1.0)

    async def test_wait_for_connection_and_telemetry(self):
        helper = MavrosHelper(self.test_node)
        connected = await helper.wait_for_connection(timeout_sec=2.0)
        self.assertTrue(connected)

        # Give a brief moment for the state callback to process
        await asyncio.sleep(0.1)
        self.assertTrue(helper.is_armed)
        self.assertEqual(helper.current_mode, 'GUIDED')

    async def test_arm_vehicle(self):
        helper = MavrosHelper(self.test_node)

        success = await helper.arm(timeout_sec=2.0)
        self.assertTrue(success)
        self.assertTrue(self.mock_node.arm_called)
        self.assertTrue(self.mock_node.arm_request_value)

    async def test_disarm_vehicle(self):
        helper = MavrosHelper(self.test_node)

        success = await helper.disarm(timeout_sec=2.0)
        self.assertTrue(success)
        self.assertTrue(self.mock_node.arm_called)
        self.assertFalse(self.mock_node.arm_request_value)

    async def test_set_mode(self):
        helper = MavrosHelper(self.test_node)

        success = await helper.set_mode('GUIDED', timeout_sec=2.0)
        self.assertTrue(success)
        self.assertEqual(self.mock_node.mode_requested, 'GUIDED')

    async def test_set_servo(self):
        helper = MavrosHelper(self.test_node)

        success = await helper.set_servo(servo_number=9, pwm=1500, timeout_sec=2.0)
        self.assertTrue(success)
        self.assertEqual(self.mock_node.last_servo_cmd, (9, 1500))

    async def test_set_rc_override(self):
        helper = MavrosHelper(self.test_node)

        # Channel 3 (index 2) to 1600
        helper.set_rc_override({3: 1600})

        # Allow a tiny bit of time for the pub/sub to process in the background executor
        await asyncio.sleep(0.1)

        self.assertIsNotNone(self.mock_node.last_rc_msg)
        self.assertEqual(self.mock_node.last_rc_msg.channels[2], 1600)

    async def test_clear_rc_override(self):
        helper = MavrosHelper(self.test_node)

        # Override a channel then clear it
        helper.set_rc_override({3: 1600})
        await asyncio.sleep(0.05)

        helper.clear_rc_override()
        await asyncio.sleep(0.05)

        self.assertIsNotNone(self.mock_node.last_rc_msg)
        # Verify all 18 channels have reset to 0
        self.assertTrue(all(ch == 0 for ch in self.mock_node.last_rc_msg.channels))

    async def test_temporary_rc_override(self):
        helper = MavrosHelper(self.test_node)

        async with helper.temporary_rc_override({3: 1700}):
            await asyncio.sleep(0.05)
            self.assertEqual(self.mock_node.last_rc_msg.channels[2], 1700)

        # Verify it automatically cleared after exiting the block
        await asyncio.sleep(0.05)
        self.assertTrue(all(ch == 0 for ch in self.mock_node.last_rc_msg.channels))

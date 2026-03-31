#!/usr/bin/env python3

import os
import cv2
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

from xarm_pickup_interfaces.action import RetrieveItems


class CameraViewerNode(Node):
    def __init__(self):
        super().__init__('camera_viewer')

        # Parameters
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('save_directory', '~/images')
        #self.declare_parameter('motor_cmd_topic', '/motor-cmd')
        #self.declare_parameter('enable_motor_keys', True)
        #self.declare_parameter('enable_pickup_action', True)
        #self.declare_parameter('default_num_items', 1)

        image_topic = self.get_parameter('image_topic').value
        save_dir = self.get_parameter('save_directory').value
        motor_cmd_topic = self.get_parameter('motor_cmd_topic').value
        self.enable_motor_keys = self.get_parameter('enable_motor_keys').value
        self.enable_pickup_action = self.get_parameter('enable_pickup_action').value
        self.default_num_items = self.get_parameter('default_num_items').value

        self.save_directory = os.path.expanduser(save_dir)
        os.makedirs(self.save_directory, exist_ok=True)

        # Image handling
        self.bridge = CvBridge()
        self.latest_frame = None

        self.subscription = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            10
        )
        """
        # Motor command publisher
        #self.motor_pub = self.create_publisher(String, motor_cmd_topic, 10)

        # Pickup action client
        #self.action_client = None
        #self.goal_in_progress = False
        #if self.enable_pickup_action:
        #    self.action_client = ActionClient(self, RetrieveItems, 'retrieve_items')

        #= 30 Hz display / input timer
        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)

        self.get_logger().info(
            f'\n'
            f'  Camera Viewer started\n'
            f'  Subscribed topic : {image_topic}\n'
            f'  Save directory   : {self.save_directory}\n'
            f'  Motor cmd topic  : {motor_cmd_topic}\n'
            f'  Key bindings:\n'
            f'    [s] save image\n'
            f'    [q] quit\n'
            f'    [w] forward 50 cm\n'
            f'    [a] left turn 90 deg\n'
            f'    [d] right turn 90 deg\n'
            f'    [x] stop\n'
            f'    [p] call RetrieveItems action'
        )

        """
    def image_callback(self, msg: Image):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'cv_bridge conversion error: {e}')

    def timer_callback(self):
        if self.latest_frame is None:
            return

        cv2.imshow('Camera Viewer', self.latest_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            self._save_frame()

        elif key == ord('q'):
            self.get_logger().info('Quit key pressed. Shutting down.')
            cv2.destroyAllWindows()
            rclpy.shutdown()
        """
        elif self.enable_motor_keys and key == ord('w'):
            self._send_motor_cmd('F15,50')

        elif self.enable_motor_keys and key == ord('a'):
            self._send_motor_cmd('T40,90')

        elif self.enable_motor_keys and key == ord('d'):
            self._send_motor_cmd('T-40,90')

        elif self.enable_motor_keys and key == ord('x'):
            self._send_motor_cmd('STOP')

        elif self.enable_pickup_action and key == ord('p'):
            self._send_pickup_goal(self.default_num_items)
        """
    def _save_frame(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f'capture_{timestamp}.jpg'
        filepath = os.path.join(self.save_directory, filename)
        cv2.imwrite(filepath, self.latest_frame)
        self.get_logger().info(f'Frame saved: {filepath}')
    """
    def _send_motor_cmd(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.motor_pub.publish(msg)
        self.get_logger().info(f'Published motor command: {cmd}')

    def _send_pickup_goal(self, num_items: int):
        if self.goal_in_progress:
            self.get_logger().warn('Pickup goal already in progress.')
            return

        if self.action_client is None:
            self.get_logger().warn('Pickup action client is disabled.')
            return

        if not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn('RetrieveItems action server not available.')
            return

        goal_msg = RetrieveItems.Goal()
        goal_msg.num_items = num_items

        self.goal_in_progress = True
        self.get_logger().info(f'Sending pickup goal: num_items={num_items}')

        future = self.action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback
        )
        future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().warn('Pickup goal rejected.')
            self.goal_in_progress = False
            return

        self.get_logger().info('Pickup goal accepted.')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f'Pickup feedback: state={feedback.state}, '
            f'box={feedback.current_box}, '
            f'items={feedback.items_collected}'
        )

    def _result_callback(self, future):
        result = future.result().result
        self.get_logger().info(
            f'Pickup result: success={result.success}, '
            f'items_collected={result.items_collected}, '
            f'message={result.message}'
        )
        self.goal_in_progress = False

"""
def main(args=None):
    rclpy.init(args=args)
    node = CameraViewerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
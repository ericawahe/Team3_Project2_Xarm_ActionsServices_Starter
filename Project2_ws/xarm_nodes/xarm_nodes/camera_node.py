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

#from xarm_pickup_interfaces.action import RetrieveItems


class CameraViewerNode(Node):
    def __init__(self):
        super().__init__('camera_viewer')
        self.get_logger().info("Camera viewer running...")
        # Parameters
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('save_directory', '~/images')
        #self.declare_parameter('motor_cmd_topic', '/motor-cmd')
        #self.declare_parameter('enable_motor_keys', True)
        #self.declare_parameter('enable_pickup_action', True)
        #self.declare_parameter('default_num_items', 1)

        image_topic = self.get_parameter('image_topic').value
        save_dir = self.get_parameter('save_directory').value
        #motor_cmd_topic = self.get_parameter('motor_cmd_topic').value
        #self.enable_motor_keys = self.get_parameter('enable_motor_keys').value
        #self.enable_pickup_action = self.get_parameter('enable_pickup_action').value
        #self.default_num_items = self.get_parameter('default_num_items').value

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

        #= 30 Hz display / input timer
        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)
   
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

    def _save_frame(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f'capture_{timestamp}.jpg'
        filepath = os.path.join(self.save_directory, filename)
        cv2.imwrite(filepath, self.latest_frame)
        self.get_logger().info(f'Frame saved: {filepath}')

        if not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn('RetrieveItems action server not available.')
            return

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
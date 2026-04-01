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

from std_srvs.srv import Trigger

#from xarm_pickup_interfaces.action import RetrieveItems


class CameraViewerNode(Node):
    def __init__(self):
        super().__init__('camera_viewer')
        self.get_logger().info("Camera viewer running...")
        # Parameters
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('save_directory', '~/images')


        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        save_dir = self.get_parameter('save_directory').get_parameter_value().string_value
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
        #self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)
   
        # Service for headless image capture used by orchestrator
        self.save_service = self.create_service(Trigger, '/save_image', self.save_image_callback)

        self.get_logger().info(
            f'\n'
            f'  Camera Viewer started (headless)\n'
            f'  Subscribed topic : {image_topic}\n'
            f'  Save directory   : {self.save_directory}\n'
            f'  Service          : /save_image'
        )

    def image_callback(self, msg: Image):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'cv_bridge conversion error: {e}')


    def save_image_callback(self, request, response):
        del request
        if self.latest_frame is None:
            response.success = False
            response.message = 'No frame available yet.'
            return response

        try:
            filepath = self._save_frame()
            response.success = True
            response.message = filepath
            return response
        except Exception as exc:
            response.success = False
            response.message = f'Failed to save frame: {exc}'
            return response

    def _save_frame(self):
        """Save the current frame as a timestamped JPEG."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # trim µs → ms
        filename = f'capture_{timestamp}.jpg'
        filepath = os.path.join(self.save_directory, filename)
        cv2.imwrite(filepath, self.latest_frame)
        self.get_logger().info(f'Frame saved: {filepath}')
        return filepath


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
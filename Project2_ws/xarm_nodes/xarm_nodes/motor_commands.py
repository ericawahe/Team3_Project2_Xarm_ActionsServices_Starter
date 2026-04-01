#!/usr/bin/env python3
"""
pickup_gui.py — Pre-built GUI client for the xArm pickup action.

NOTE FOR STUDENTS: You do not need to modify this file.
Run it as-is to interact with the RetrieveItems action server you implement
in your action server node.

Overview:
  - PickupGuiWindow     : tkinter window that lets the operator set the number
                          of items to collect, trigger the action, and cancel it.
  - XarmPickupGuiClient : ROS2 action client that sends RetrieveItems goals,
                          processes feedback, and handles results/cancellation.

Thread safety:
  tkinter is not thread-safe, so all GUI updates are posted through a
  queue.Queue. The window polls that queue every 50 ms via tkinter's
  after() scheduler and applies updates on the main thread.
"""

import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from xarm_pickup_interfaces.action import RetrieveItems

from std_msgs.msg import String
import serial

class MotorCommander(Node):
    def __init__(self):
        super().__init__('motor_commander')

        self.ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

        self.create_subscription(String, '/motor-cmd', self.cmd_callback, 10)

    def cmd_callback(self, msg):
        cmd = msg.data + '\n'
        self.ser.write(cmd.encode())


def main():
    rclpy.init()
    node = MotorCommander()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

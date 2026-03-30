from os import read
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
import serial
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

#from xarm_pickup_interfaces.action import RetrieveItems
arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=.1)

class Arduino(Node):

    def __init__(self, ):
        super().__init__('arduino_node')

    input = 'F15,50'
    arduino.write(bytes(input, 'utf-8'))
    value = arduino.readline().decode('utf-8')
    i=0
    while value[:4] != 'Done':
        value = arduino.readline().decode('utf-8')

        time.sleep(0.5)
        i += 1
        if i>20:
            break
    
def main(args=None):
    rclpy.init(args=args)
    node = Arduino()
    print("Node created")
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
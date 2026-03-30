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

from xarm_pickup_interfaces.action import RetrieveItems
arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=.1)
from xarm_pickup_interfaces.srv import SetGripper

class DrivePickup(Node):
    """ROS2 action client node for the RetrieveItems action.

    Runs inside a background thread (see _spin_ros) so that ROS callbacks do
    not block the tkinter event loop. All GUI updates are posted to ui_queue
    as (key, value) tuples and consumed by PickupGuiWindow._poll_queue().
    """

    def __init__(self, ui_queue: queue.Queue):
        super().__init__('xarm_pickup_gui_client')
        self.ui_queue = ui_queue          # Thread-safe channel to the GUI
        self.action_client = ActionClient(self, RetrieveItems, 'retrieve_items')
        self.goal_handle = None
        self._goal_lock = threading.Lock()  # Protects self.goal_handle across threads
        self.set_gripper_client = self.create_client(SetGripper, 'SetGripper')

    input = 'F15,50'
    arduino.write(bytes(input, 'utf-8'))
    value = arduino.readline().decode('utf-8')
    i=0
    while value[:4] != 'Done':
        value = arduino.readline().decode('utf-8')
        print(value)
        time.sleep(0.5)
        i += 1
        if i>20:
            break

    def _post(self, key: str, value):
        """Post a GUI update to the queue."""
        self.ui_queue.put((key, value))

    def send_goal(self, num_items: int):
        """Send a RetrieveItems goal to the action server."""
        if not self.action_client.wait_for_server(timeout_sec=2.0):
            self._post('status', 'Server not available')
            self._post('goal_active', False)
            return

        goal_msg = RetrieveItems.Goal()
        goal_msg.num_items = num_items

        self._post('status', f'Sending goal: num_items={num_items}')
        send_future = self.action_client.send_goal_async(
            goal_msg, feedback_callback=self._feedback_callback
        )
        send_future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        """Called when the server accepts or rejects the goal."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._post('status', 'Goal rejected')
            self._post('goal_active', False)
            return

        with self._goal_lock:
            self.goal_handle = goal_handle

        self._post('status', 'Goal accepted')
        self._post('goal_active', True)

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _feedback_callback(self, feedback_msg):
        """Forward action feedback fields to the GUI via the queue."""
        feedback = feedback_msg.feedback
        box_text = str(feedback.current_box) if feedback.current_box >= 0 else 'N/A'

        self._post('state', feedback.state)
        self._post('box', box_text)
        self._post('items', str(feedback.items_collected))
        self._post('status', 'Feedback received')

    def _result_callback(self, future):
        """Called when the action finishes (success, failure, or cancelled)."""
        result = future.result().result
        self._post('status', f'Done: success={result.success} items={result.items_collected}')
        self._post('goal_active', False)

        with self._goal_lock:
            self.goal_handle = None

    def cancel_goal(self):
        """Request cancellation of the currently active goal, if any."""
        with self._goal_lock:
            active_goal = self.goal_handle

        if active_goal is None:
            self._post('status', 'No active goal to cancel')
            return

        self._post('status', 'Cancel requested')
        cancel_future = active_goal.cancel_goal_async()
        cancel_future.add_done_callback(self._cancel_done_callback)

    def _cancel_done_callback(self, future):
        cancel_response = future.result()
        if len(cancel_response.goals_canceling) > 0:
            self._post('status', 'Cancel accepted by server')
        else:
            self._post('status', 'Cancel rejected or goal already finished')
    

    #call action

    '''
    # release object
    req.state = 'open'
    future = self.set_gripper_client.call_async(req)
    rclpy.spin_until_future_complete(self, future)
    time.sleep(1.0) # wait until gripper has released object
    '''


def main(args=None):
    rclpy.init(args=args)
    node = DrivePickup()
    '''
    def read():
        time.sleep(0.05)
        data = arduino.readline()
        return data
    

    input = 'F15,50'
    arduino.write(bytes(input, 'utf-8'))
    value = read()
    i=0
    while value != 'Done':
        value = read()
        time.sleep(0.5)
        i += 1
        if i>20:
            break
    '''


if __name__ == '__main__':
    main()
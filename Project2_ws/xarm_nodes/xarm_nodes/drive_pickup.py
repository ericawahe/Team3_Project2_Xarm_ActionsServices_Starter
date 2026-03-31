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
from xarm_pickup_interfaces.srv import SetGripper
arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=.1)

class DrivePickup(Node):
    """ROS2 action client node for the RetrieveItems action.
    """

    def __init__(self):
        super().__init__('DrivePickup')

        self.set_gripper_client = self.create_client(SetGripper, 'SetGripper')

        # Create an action client that will call an action hosted by the action server. 
        self._action_client = ActionClient(
            self,                                  
            RetrieveItems,                       
            'retrieve_items'                     
        )

        self.get_logger().info("Waiting for target action server...")
        
        # Block until the action server is available before sending goals.
        while not self._action_client.wait_for_server(timeout_sec=1.0):
            pass
        self.get_logger().info("Target action server is available.")
    
    def send_goal(self, num_items: int):
        """
        Send a goal to the action server.
        
        Args:
            num_items: The number of items to retrieve
        """
        # ========================== STUDENT TODO ==========================
        # Replace the goal message fields to match your `.action` Goal.
        # Add any client-side validation before sending a goal.
        # =================================================================

        # Build the action goal message and set the requested target value.
        goal_msg = RetrieveItems.Goal()
        goal_msg.num_items = num_items

        
        # Ensure the server is still available before sending.
        self._action_client.wait_for_server()
        
        # Send the goal asynchronously and register a feedback callback.

        self.get_logger().info(f"Sending goal: target={num_items}") #changed from target to num_items
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        
        # Register callback that runs when the server accepts/rejects the goal.
        self._send_goal_future.add_done_callback(self.goal_response_callback)
    
    def goal_response_callback(self, future):
        """Handle the response to the goal request."""
        # Read the goal handle from the completed future.
        goal_handle = future.result()
        
        # Exit early if the action server rejected the goal.
        if not goal_handle.accepted:
            self.get_logger().warn("Goal rejected by target action server.")
            rclpy.shutdown()
            return

        self.get_logger().info("Goal accepted by target action server.")
        
        # Request the final action result asynchronously.
        self._get_result_future = goal_handle.get_result_async()
        # Register callback to process the final action result.
        self._get_result_future.add_done_callback(self.get_result_callback)
    
    def get_result_callback(self, future):
        """Handle the final result from the action."""
        # ========================== STUDENT TODO ==========================
        # Use `result` fields from your custom action result definition.
        # Add your project-specific success/failure handling here.
        # =================================================================

        # Extract the result payload from the finished future.
        result = future.result().result
        self.get_logger().info(
            f"Action result: success={result.success}, final_value={result.items_collected}"
        )


        # Shut down ROS after this one-shot demo goal completes.
        rclpy.shutdown()
    
    def feedback_callback(self, feedback_msg):
        """Handle feedback from the action server."""
        # ========================== STUDENT TODO ==========================
        # Use feedback fields from your custom action feedback definition.
        # Add any progress display or control behavior needed by your app.
        # =================================================================

        # Extract the feedback payload for logging.
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f"Feedback: current_value={feedback.items_collected}, status='{feedback.state}'"
        )
class Turn(Node):
    def __init__(self, ):
        super().__init__('turning_node')

    input = 'T40,90'
    arduino.write(bytes(input, 'utf-8'))
    value = arduino.readline().decode('utf-8')
    i=0
    while value[:4] != 'Done':
        value = arduino.readline().decode('utf-8')
        time.sleep(0.5)
        i += 1
        if i>20:
            break


class DriveForward(Node):
    def __init__(self, ):
        super().__init__('driving_node')

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

    executor = rclpy.executors.SingleThreadedExecutor()
    
    # First Drive
    drive_node1 = DriveForward()
    executor.add_node(drive_node1)
    executor.spin_once()
    executor.remove_node(drive_node1)
    drive_node1.destroy_node()
    time.sleep(10.0)
    '''
    # Then Pickup
    pickup_node = DrivePickup()
    executor.add_node(pickup_node)
    pickup_node.send_goal(1)
    executor.spin_once()
    executor.remove_node(pickup_node)
    pickup_node.destroy_node()
    
    # Then Turn
    turn_node = Turn()
    executor.add_node(turn_node)
    executor.spin_once()
    executor.remove_node(turn_node)
    turn_node.destroy_node()
    '''
    # Then Drive again
    drive_node2 = DriveForward()
    executor.add_node(drive_node2)
    executor.spin_once()
    executor.remove_node(drive_node2)
    drive_node2.destroy_node()
    
    executor.shutdown()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
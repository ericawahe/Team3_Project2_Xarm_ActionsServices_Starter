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
from std_srvs.srv import Trigger
from xarm_pickup_interfaces.action import RetrieveItems
from xarm_pickup_interfaces.srv import SetGripper
arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=0.1)

##get_logger instead of print because of ros//maybe better? 

class DrivePickup(Node):
    def __init__(self):
        super().__init__('drive_pickup')

        #action service for moving
        self._action_client = ActionClient(
            self,
            RetrieveItems,
            'retrieve_items'
        )

        #service client for image
        self.save_image_client = self.create_client(Trigger, '/save_image')

        #checks with nodes to make sure they are running before doing anything
        self.get_logger().info('Waiting for retrieve_items action server...')
        while not self._action_client.wait_for_server(timeout_sec=1.0):
            pass
        self.get_logger().info('retrieve_items action server available.')

        self.get_logger().info('Waiting for /save_image service...')
        while not self.save_image_client.wait_for_service(timeout_sec=1.0):
            pass
        self.get_logger().info('/save_image service available.')
#################################################################################

    #calling node to save an image
    def save_image(self):
        req = Trigger.Request() #no input only an output message /success status
        future = self.save_image_client.call_async(req)

        #wait until image is saved
        rclpy.spin_until_future_complete(self, future)

        #error handling
        if future.result() is None:
            self.get_logger().error('Save image call failed.')
            return False

        response = future.result()
        if response.success:
            self.get_logger().info(f'Image saved: {response.message}')
            return True
        else:
            self.get_logger().error(f'Image save failed: {response.message}')
            return False
####################################################################################

    #calling node to pick up item(s) using action server
    def retrieve_items(self, num_items):

        #make goal
        goal_msg = RetrieveItems.Goal()
        goal_msg.num_items = num_items

        self.get_logger().info(f'Sending pickup goal for {num_items} item(s)')
        
        #sends goal to action server and waits for result
        send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        #wait until goal response is received
        rclpy.spin_until_future_complete(self, send_goal_future)

        #error handling for goal response
        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('Pickup goal rejected.')
            return False

        self.get_logger().info('Pickup goal accepted.')
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result_msg = result_future.result()
        if result_msg is None:
            self.get_logger().error('Pickup action returned no result.')
            return False

        result = result_msg.result
        self.get_logger().info(
            f'Pickup result: success={result.success}, items_collected={result.items_collected}'
        )
        return result.success
####################################################################################

    #print statement of feedback
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f"Feedback: items_collected={feedback.items_collected}, state='{feedback.state}'"
        )
####################################################################################

    #main run 
    def run_sequence(self):

        #Drive forward 50 cm
        self.get_logger().info('Driving forward 50 cm')
        arduino.reset_input_buffer()
        arduino.write(b'(F15,50)\n')

        value = ''
        i = 0
        while not value.startswith('Done'):
            value = arduino.readline().decode('utf-8', errors='ignore').strip()
            if value:
                self.get_logger().info(f'Arduino: {value}')
            time.sleep(0.25)
            i += 1
            if i > 40:
                self.get_logger().error('Timeout during first drive command')
                return

        #calls save_image function /error handling if image can't be saved
        if not self.save_image():
            self.get_logger().warn('Could not save first image')

        #Pickup item
        if not self.retrieve_items(1):
            self.get_logger().error('Pickup failed')
            return

        #turn
        self.get_logger().info('Turning 90 degrees')
        arduino.reset_input_buffer()
        arduino.write(b'(T40,90)\n')

        value = ''
        i = 0
        while not value.startswith('Done'):
            value = arduino.readline().decode('utf-8', errors='ignore').strip()
            if value:
                self.get_logger().info(f'Arduino: {value}')
            time.sleep(0.25)
            i += 1
            if i > 40:
                self.get_logger().error('Timeout during turn command')
                return

        #drive 50 cm
        self.get_logger().info('Driving forward 50 cm again')

        #resets arduino
        arduino.reset_input_buffer()
        arduino.write(b'(F15,50)\n')

        value = ''
        i = 0
        while not value.startswith('Done'):
            value = arduino.readline().decode('utf-8', errors='ignore').strip()
            if value:
                self.get_logger().info(f'Arduino: {value}')
            time.sleep(0.25)
            i += 1
            if i > 40:
                self.get_logger().error('Timeout during second drive command')
                return

        #how to drop???
        #self.get_logger().info('Drop item step goes here')

        # arduino.reset_input_buffer()
        # arduino.write(b'(DROP)\n')
        # value = ''
        # i = 0
        # while not value.startswith('Done'):
        #     value = arduino.readline().decode('utf-8', errors='ignore').strip()
        #     if value:
        #         self.get_logger().info(f'Arduino: {value}')
        #     time.sleep(0.25)
        #     i += 1
        #     if i > 40:
        #         self.get_logger().error('Timeout during drop command')
        #         return

        #second image
        if not self.save_image():
            self.get_logger().warn('Could not save second image')

        self.get_logger().info('Sequence complete')


def main(args=None):
    rclpy.init(args=args)
    node = DrivePickup()

    try:
        node.run_sequence()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()







"""
class DrivePickup(Node):

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
        #Send a goal to the action server.
        #Args:
            #num_items: The number of items to retrieve
        

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
        #Handle the response to the goal request.
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
        #Handle the final result from the action.
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
        #Handle feedback from the action server.
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

    def turn(self, input):
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

    def drive_forward(self, input):
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
    drive_node1 = DriveForward()
    pickup_node = DrivePickup()
    drive_node2 = DriveForward()
    turn_node = Turn()

    #executor = rclpy.executors.SingleThreadedExecutor()
    #executor.add_node(drive_node1)
    #executor.add_node(pickup_node)
    #executor.add_node(drive_node2)

    # First Drive


    drive_node1.drive_forward('F15,50')
    #executor.add_node(drive_node1)
    #executor.spin_once()
    #executor.remove_node(drive_node1)
    #drive_node1.destroy_node()
    
    # Then Pickup

    pickup_node.send_goal(1)
    #pickup_node.spin_once()
    #executor.add_node(pickup_node)
    #executor.spin_once()
    #executor.remove_node(pickup_node)
    #pickup_node.destroy_node()
    #pickup_node.get_result_callback() #wait until pickup is done before proceeding to next step
    time.sleep(10)
    print("moving along")

    # Then Turn
    turn_node.turn('T40,90')
    #executor.add_node(turn_node)
    #executor.spin_once()
    #executor.remove_node(turn_node)
    #turn_node.destroy_node()
    time.sleep(5)
    print("moving along")

    # Then Drive again
    drive_node2.drive_forward('F15,50')
    #executor.add_node(drive_node2)
    #executor.spin_once()
    #executor.remove_node(drive_node2)
    #drive_node2.destroy_node()
    
    #executor.shutdown()
    drive_node1.destroy_node()
    pickup_node.destroy_node()
    drive_node2.destroy_node()
    turn_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

"""

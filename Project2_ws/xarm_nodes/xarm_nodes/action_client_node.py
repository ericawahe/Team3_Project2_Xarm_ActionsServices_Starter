#!/usr/bin/env python3
"""
Action Client Node Template
This node sends an action goal to increment to a target number.
It displays feedback as the action progresses.

Students: replace this node/action naming and goal fields with your own interfaces and use case.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from interface_templates.action import IncrementToGoal

# ============================== STUDENT TODO ==============================
# Replace `IncrementToGoal` import with your own action interface.
# Update node/action names to match your project conventions.
# ========================================================================


class ActionClientNode(Node):
    def __init__(self):
        # Initialize this class as a ROS 2 node named 'action_client_node'.
        super().__init__('action_client_node')
        
        # Create an action client that will call an action hosted by the action server. 
        self._action_client = ActionClient(         # Instantiate the action client object
            self,                                   # Define the scope of the client (this node)
            IncrementToGoal,                        # Specify the action interface (defined in .action file)
            'increment_to_goal'                     # Specify the name of the action (must match the server's action name) 
        )

        self.get_logger().info("Waiting for target action server...")
        
        # Block until the action server is available before sending goals.
        while not self._action_client.wait_for_server(timeout_sec=1.0):
            pass
        self.get_logger().info("Target action server is available.")
    
    def send_goal(self, target):
        """
        Send a goal to the action server.
        
        Args:
            target: The target number to increment to
        """
        # ========================== STUDENT TODO ==========================
        # Replace the goal message fields to match your `.action` Goal.
        # Add any client-side validation before sending a goal.
        # =================================================================

        # Build the action goal message and set the requested target value.
        goal_msg = IncrementToGoal.Goal()
        goal_msg.target = target
        
        # Ensure the server is still available before sending.
        self._action_client.wait_for_server()
        
        # Send the goal asynchronously and register a feedback callback.
        self.get_logger().info(f"Sending goal: target={target}")
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
            f"Action result: success={result.success}, final_value={result.final_value}"
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
            f"Feedback: current_value={feedback.current_value}, status='{feedback.status}'"
        )


def main(args=None):
    rclpy.init(args=args)
    
    node = ActionClientNode()
    
    # ============================ STUDENT TODO ============================
    # Replace this input flow with your own goal source (CLI, config, UI,
    # test harness, sensor values, etc.).
    # =====================================================================

    # Prompt user for target value
    target = int(input("Enter target value (2-10): "))
    node.send_goal(target=target)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
retrieve_items_action_server.py — Scaffold for the RetrieveItems action server.

TODO(STUDENTS): Implement the action server logic in this file.
You will need to:
  1. Define any service types you need and import them below.
  2. Create service clients in __init__ for each hardware service you call.
  3. Fill in goal_callback, cancel_callback, and execute_callback.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.action import CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
import asyncio

from xarm_pickup_interfaces.action import RetrieveItems
from xarm_pickup_interfaces.srv import (
    MoveToCell,
    MoveGraspedToDeposit,
    GetGripperPosition,
    SetGripper,
)
# TODO(STUDENTS): Import your service types here.


class RetrieveItemsActionServer(Node):
    """Action server that executes a RetrieveItems goal."""

    def __init__(self):
        super().__init__('retrieve_items_action_server')

        # Create service clients for the hardware services we will call.
        self.move_to_cell_client = self.create_client(MoveToCell, 'Move_To_Cell')
        self.move_grasped_to_deposit_client = self.create_client(MoveGraspedToDeposit, 'Move_Grasped_To_Deposit')
        self.get_gripper_pos_client = self.create_client(GetGripperPosition, 'GetGripperPosition')
        self.set_gripper_client = self.create_client(SetGripper, 'SetGripper')

        # Wait for the service servers to become available.
        self.get_logger().info("Waiting for service servers...")
        self.move_to_cell_client.wait_for_service()
        self.move_grasped_to_deposit_client.wait_for_service()
        self.set_gripper_client.wait_for_service()
        self.get_gripper_pos_client.wait_for_service()
        self.get_logger().info("Hardware services connected.")

        self._action_server = ActionServer(
            self,
            RetrieveItems,
            'retrieve_items',
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            execute_callback=self.execute_callback,
        )

        self.get_logger().info('retrieve_items_action_server is running.')

    def goal_callback(self, goal_request):
        """Accept or reject an incoming goal request.

        TODO(STUDENTS): Add any validation logic here (e.g. reject if num_items is out of range).
        Return GoalResponse.REJECT to refuse a goal before execution begins.
        """
        num = goal_request.num_items
        if 1 <= num <= 9:
            self.get_logger().info(f'Received goal: num_items={num}')
            return GoalResponse.ACCEPT
        else:
            self.get_logger().warn(f'Goal rejected: num_items={num} out of range')
            return GoalResponse.REJECT

    def cancel_callback(self, goal_handle):
        """Accept or reject a cancel request for an active goal.

        TODO(STUDENTS): Return CancelResponse.REJECT if cancellation should be refused.
        """
        self.get_logger().info('Received cancel request.')
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        """Execute the RetrieveItems goal.

        This method runs in a separate thread via the MultiThreadedExecutor.
        It publishes feedback and returns a Result when the goal finishes.
        """
        self.get_logger().info('Executing goal...')

        num_items = goal_handle.request.num_items
        feedback_msg = RetrieveItems.Feedback()
        result = RetrieveItems.Result()

      
        index = 0
        items_so_far = 0

        while (items_so_far < num_items):

            if index < 9: index +=1 # index initialized as zero, add one to move to the first box and so on
            else: 
                print('\nAll cells searched, not enough objects found.')
                # if index = 9 all boxes searched and not enough objects found so cancel
                result.success = False
                result.message = 'Goal failed.'
                return result

            #move to index cell
            req = MoveToCell.Request()
            req.box_index = index
            response = await self.move_to_cell_client.call_async(req)

            feedback_msg.state = 'searching'
            feedback_msg.current_box = index

            #attempt to grasp object
            req = SetGripper.Request()
            req.state = 'close'
            response = await self.set_gripper_client.call_async(req)

            req = GetGripperPosition.Request()
            pose = await self.get_gripper_pos_client.call_async(req)

            #attempt to move grasped item to dropoff location
            if pose.position <= 750: # not fully closed -> object has been grasped!
                items_so_far += 1
                req = MoveGraspedToDeposit.Request()
                req.item_grasped = True
                response = await self.move_grasped_to_deposit_client.call_async(req)
            else: # fully closed therefore no object was grasped :(
                req = MoveGraspedToDeposit.Request()
                req.item_grasped = False
                response = await self.move_grasped_to_deposit_client.call_async(req)

            feedback_msg.items_collected = items_so_far
            goal_handle.publish_feedback(feedback_msg)


            # check for cancellation request
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.success = False
                result.message = 'Goal cancelled.'
                return result



      
        # TODO(STUDENTS): Implement your item retrieval loop.
        # A typical loop might:
        #   1. Determine the next grid box to visit.
        #   2. Call a hardware service to move the arm.
        #   3. Call a hardware service to operate the gripper.
        #   4. Publish feedback after each step.
        #   5. Check for cancellation and abort cleanly if requested.
        #
        # --- Calling a service with await ---
        # request = YourServiceType.Request()
        # request.box_index = current_box
        # response = await self._your_client.call_async(request)
        # if not response.success:
        #     self.get_logger().error(f'Service call failed: {response.message}')
        #
        # --- Publishing feedback ---
        # feedback_msg.state = 'searching'
        # feedback_msg.current_box = current_box
        # feedback_msg.items_collected = items_so_far
        # goal_handle.publish_feedback(feedback_msg)
        #
        # --- Checking for cancellation ---
        # if goal_handle.is_cancel_requested:
        #     goal_handle.canceled()
        #     result.success = False
        #     result.message = 'Goal cancelled.'
        #     return result

        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)
    node = RetrieveItemsActionServer()

    # MultiThreadedExecutor allows goal, cancel, and execute callbacks to run
    # concurrently — required when the execute_callback blocks or uses await.
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

"""
# ================= COPY/PASTE BELOW =================
gripper_closed_count = 700
gripper_open_count   = 332

POSITIONS = {
    0: [332, 500, 500, 500, 500, 500],
    1: [332, 499, 799, 139, 528, 631],
    2: [332, 498, 852, 158, 528, 510],
    3: [332, 498, 818, 163, 542, 386],
    4: [332, 498, 739, 190, 593, 610],
    5: [332, 498, 767, 170, 565, 507],
    6: [332, 498, 768, 204, 590, 421],
    7: [332, 498, 704, 256, 661, 586],
    8: [332, 498, 736, 261, 651, 510],
    9: [332, 499, 704, 261, 660, 436],
}

POSITION_DROP = [700, 498, 864, 264, 561, 145]
# ================== COPY/PASTE ABOVE =================
"""

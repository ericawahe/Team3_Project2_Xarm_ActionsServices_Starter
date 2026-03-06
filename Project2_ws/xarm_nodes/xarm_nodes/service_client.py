#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from xarm_pickup_interfaces.srv import (
    MoveToCell,
    MoveGraspedToDeposit,
    GetGripperPosition,
    SetGripper,
)


class XArmServiceClient(Node):
    def __init__(self):
        super().__init__('xarm_service_client')

        # create clients for all four services
        self.move_to_cell_client = self.create_client(MoveToCell, 'Move_To_Cell')
        self.move_grasped_to_deposit_client = self.create_client(
            MoveGraspedToDeposit, 'Move_Grasped_To_Deposit'
        )
        self.get_gripper_pos_client = self.create_client(GetGripperPosition, 'GetGripperPosition')
        self.set_gripper_client = self.create_client(SetGripper, 'SetGripper')

        self.get_logger().info('waiting for service servers...')
        self.move_to_cell_client.wait_for_service()
        self.move_grasped_to_deposit_client.wait_for_service()
        self.get_gripper_pos_client.wait_for_service()
        self.set_gripper_client.wait_for_service()
        self.get_logger().info('all hardware services are available')

    def move_to_cell(self, index: int):
        # add debug information to help diagnose call failures
        self.get_logger().info(f'calling MoveToCell service with index {index}')
        req = MoveToCell.Request()
        req.box_index = index
        future = self.move_to_cell_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        resp = future.result()
        if resp is None:
            self.get_logger().error('MoveToCell service call failed: no response (service may not be available)')
            return None
        self.get_logger().info(f"MoveToCell response: success={resp.success} message={getattr(resp,'message','')}")
        return resp

    def move_grasped_to_deposit(self, item_grasped: bool):
        req = MoveGraspedToDeposit.Request()
        req.item_grasped = item_grasped
        future = self.move_grasped_to_deposit_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def get_gripper_position(self, position: int):
        req = GetGripperPosition.Request()
        req.position = position
        future = self.get_gripper_pos_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def set_gripper(self, state: str):
        req = SetGripper.Request()
        req.state = state
        future = self.set_gripper_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def initialize_joints(self):
        """Move all joints to their neutral 500-count position.

        This uses the existing MoveToCell service with a special index of 0.
        The hardware node must be aware of this convention and treat 0 as a
        request to drive every servo to 500 counts.
        """
        self.get_logger().info('initializing arm joints to 500 counts')
        req = MoveToCell.Request()
        req.box_index = 0
        future = self.move_to_cell_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        resp = future.result()
        if resp is None:
            self.get_logger().error('initialization service call returned no response')
            return None
        self.get_logger().info(f'init response: success={resp.success} message={getattr(resp, "message", "")}')
        return resp


def prompt_integer(prompt_text: str) -> int:
    while True:
        try:
            value = int(input(prompt_text))
            return value
        except ValueError:
            print('please enter a valid integer')


def prompt_state() -> str:
    while True:
        state = input('enter gripper state (open/close): ').strip().lower()
        if state in ('open', 'close'):
            return state
        print('invalid state, must be "open" or "close"')


def main(args=None):
    rclpy.init(args=args)
    client = XArmServiceClient()

    try:
        while rclpy.ok():
            print('\nchoose a service to call:')
            print('1) Move_To_Cell')
            print('2) Move_Grasped_To_Deposit')
            print('3) GetGripperPosition')
            print('4) SetGripper')
            print('5) Initialize joints (all -> 500)')
            print('q) quit')

            choice = input('selection: ').strip().lower()
            if choice == 'q':
                break

            if choice == '1':
                idx = prompt_integer('enter box index (1-9): ')
                resp = client.move_to_cell(idx)
                print(f'success: {resp.success}')
            elif choice == '2':
                grasped = input('Is item grasped? (yes/no): ').strip().lower() == 'yes'
                resp = client.move_grasped_to_deposit(grasped)
                print(f'success: {resp.success}, message: {getattr(resp, "message", "")}')
            elif choice == '3':
                position = 500
                resp = client.get_gripper_position(position)
                print(f'success: {resp.success}, position: {resp.position}')
            elif choice == '4':
                state = prompt_state()
                resp = client.set_gripper(state)
                print(f'success: {resp.success}, message: {getattr(resp, "message", "")}')
            elif choice == '5':
                resp = client.initialize_joints()
                if resp is not None:
                    print(f'success: {resp.success}, message: {getattr(resp, "message", "")}')
                else:
                    print('failed to initialize joints')
            else:
                print('invalid selection, try again')
    except KeyboardInterrupt:
        pass
    finally:
        client.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

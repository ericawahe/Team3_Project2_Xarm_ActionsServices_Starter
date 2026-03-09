#!/usr/bin/env python3

import time
import rclpy
from rclpy.node import Node
from xarm_pickup_interfaces.srv import MoveToCell, MoveGraspedToDeposit, GetGripperPosition, SetGripper, ServoOff  # TODO(STUDENTS): Import your service types here.

try:
    import xarm
except ImportError:
    xarm = None


class XArmHardwareNode(Node):
    def __init__(self):
        super().__init__('x_arm_hardware_node')
        self.arm = None

        # Cell Positions
        self.cell_servo_targets = [
        [332, 499, 799, 139, 518, 631], # cell 1
        [332, 498, 852, 158, 518, 510], # cell 2
        [332, 498, 818, 163, 532, 386], # cell 3
        [332, 498, 739, 190, 583, 610], # cell 4
        [332, 498, 767, 170, 555, 507], # cell 5
        [332, 450, 768, 204, 580, 421], # cell 6
        [332, 498, 704, 256, 651, 586], # cell 7
        [332, 498, 736, 261, 641, 510], # cell 8
        [332, 499, 704, 261, 650, 436], # cell 9
        ]

        self._connect_usb()

        self.MoveToCell_client = self.create_service(MoveToCell, 'Move_To_Cell', self.MoveToCell_callback)
        self.MoveGraspedToDeposit_client = self.create_service(MoveGraspedToDeposit, 'Move_Grasped_To_Deposit', self.MoveGraspedToDeposit_callback)
        self.GetGripperPosition_client = self.create_service(GetGripperPosition, 'GetGripperPosition', self.GetGripperPosition_callback)
        self.SetGripper_client = self.create_service(SetGripper, 'SetGripper', self.SetGripper_callback)
        self.ServoOff_client = self.create_service(ServoOff, 'ServoOff', self.ServoOff_callback)
        self.get_logger().info('x_arm_hardware_node is running.')

    def _connect_usb(self):
        if xarm is None:
            self.get_logger().error('xarm Python library not found. Install it before running hardware control.')
            return

        try:
            self.arm = xarm.Controller('USB')
            self.get_logger().info('Connected to xArm over USB.')
        except Exception as exc:
            self.get_logger().error(f'Failed to connect to xArm over USB: {exc}')

    def MoveToCell_callback(self, request, response):
        self.get_logger().info(f"Moving to cell {request.box_index}")
        # special case: index 0 means "initialize all joints to 500 counts".
        if request.box_index == 0:
            self.get_logger().info('Initializing all joints to 500 counts')
            if self.arm is None:
                self.get_logger().error('Arm not connected, cannot initialize.')
                response.success = False
                return response
            for servo_id in range(1, 7):
                self.arm.setPosition(servo_id, 500, 1300)
                time.sleep(0.01)
            response.success = True
            response.message = 'joints initialized'
            return response
        cell = request.box_index - 1
        # validate index range
        if cell < 0 or cell >= 9:
            self.get_logger().error(f"Invalid cell index: {cell}")
            response.success = False
            return response

        # check arm connection
        if self.arm is None:
            self.get_logger().error('Arm not connected, cannot move.')
            response.success = False
            return response

        # Move up to avoid obstacles
        for servo_id in range (1,7):
            self.arm.setPosition(servo_id, 500, 1300)
            time.sleep(0.01)
        time.sleep(2.0)

        servo_target = self.cell_servo_targets[cell]
        for servo_id, target in enumerate(servo_target, start=1):
            self.arm.setPosition(servo_id, target, 1300)
            time.sleep(0.01)
            response.success = True
        return response

    def MoveGraspedToDeposit_callback(self, request, response):
        self.get_logger().info(f"Item grasped: {request.item_grasped}")
        
        # If item is not grasped, do nothing
        if not request.item_grasped:
            self.get_logger().info('Item not grasped, continuing')
            response.success = True
            return response
        
        # check arm connection
        if self.arm is None:
            self.get_logger().error('Arm not connected, cannot move.')
            response.success = False
            return response
        
        # Move up to avoid obstacles
        for servo_id in range (1,7):
            self.arm.setPosition(servo_id, 500, 1300)
            time.sleep(0.01)
        time.sleep(1.0)

        # Move to drop target
        self.get_logger().info('Moving to drop target')
        drop_target = [700, 498, 864, 264, 561, 145]
        for servo_id, target in enumerate(drop_target, start=1):
            self.arm.setPosition(servo_id, target, 1300)
            time.sleep(0.01)
        
        response.success = True
        return response

    def GetGripperPosition_callback(self, request, response):
        self.get_logger().info("Getting gripper position")

        pose = request.pose1
        SERVO_IDS = [1, 2, 3, 4, 5, 6]
        vals = [self.arm.getPosition(servo_id) for servo_id in SERVO_IDS]
        pose = vals[0]

        response.position = pose
        response.success = True

        return response

    def SetGripper_callback(self, request, response):
        self.get_logger().info(f"Setting gripper to {request.state}")
        
        # check arm connection
        if self.arm is None:
            self.get_logger().error('Arm not connected, cannot set gripper.')
            response.success = False
            return response
        
        # Set servo 1 based on gripper state
        if request.state == "close":
            target = 800
            self.get_logger().info('Closing gripper (servo 1 -> 800 counts)')
        elif request.state == "open":
            target = 200
            self.get_logger().info('Opening gripper (servo 1 -> 200 counts)')
        else:
            self.get_logger().error(f'Invalid gripper state: {request.state}')
            response.success = False
            return response
        
        # Set the gripper position
        self.arm.setPosition(1, target, 1300)
        response.success = True
        response.message = f'Gripper set to {request.state}'
        return response
    
    def ServoOff_callback(self, request, response):
        if self.arm is None:
            self.get_logger().error('Arm not connected, cannot set gripper.')
            response.success = False
            return response
        
        try:
            self.arm.servoOff()
            response.success = True
        except Exception:
            response.success = False


def main(args=None):
    rclpy.init(args=args)
    node = XArmHardwareNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
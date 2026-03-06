#!/usr/bin/env python3

import time
import rclpy
from rclpy.node import Node
from xarm_pickup_interfaces.srv import MoveToCell, MoveGraspedToDeposit, GetGripperPosition, SetGripper  # TODO(STUDENTS): Import your service types here.

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
        [332, 499, 799, 139, 528, 631], # cell 1
        [332, 498, 852, 158, 528, 510], # cell 2
        [332, 498, 818, 163, 542, 386], # cell 3
        [332, 498, 739, 190, 593, 610], # cell 4
        [332, 498, 767, 170, 565, 507], # cell 5
        [332, 498, 768, 204, 590, 421], # cell 6
        [332, 498, 704, 256, 661, 586], # cell 7
        [332, 498, 736, 261, 651, 510], # cell 8
        [332, 499, 704, 261, 660, 436], # cell 9
        ]

        self._connect_usb()

        # TODO(STUDENTS): Add your service servers here. Make sure that all services are defined in the xarm_pickup_interfaces package and that you import them at the top of this file.
        # Example:
        # self.create_service(YourServiceType, 'service_name', self.service_callback)
        self.MoveToCell_client = self.create_service(MoveToCell, 'Move_To_Cell', self.MoveToCell_callback)
        self.MoveGraspedToDeposit_client = self.create_service(MoveGraspedToDeposit, 'Move_Grasped_To_Deposit', self.MoveGraspedToDeposit_callback)
        self.GetGripperPosition_client = self.create_service(GetGripperPosition, 'GetGripperPosition', self.GetGripperPosition_callback)
        self.SetGripper_client = self.create_service(SetGripper, 'SetGripper', self.SetGripper_callback)
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

    # TODO(STUDENTS): Add your service callback methods here.
    # Suggestions:
    # 1) Validate inputs before sending commands (e.g. are joint angles within limits?).
    # 2) Return clear success/failure info to the caller via the response object.
    #
    # Example:
    # def service_callback(self, request, response):
    #     # ... perform arm action ...
    #     response.success = True
    #     return response
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
        self.arm.setPosition(3, 600, 1300)
        self.arm.setPosition(5, 500, 1300)
        time.sleep(2.0)

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
        
        # Read all servo angles (degrees)
        code, angles = self.arm.get_servo_angle(is_radian=False)

        if code != 0:
            self.get_logger().error(f"Failed to read servo angles, code={code}")
            response.success = False
            return response

        # Assuming gripper is servo 1 (index 0)
        gripper_angle_deg = angles[0]

        #Convert angle to counts (xArm servos use 0.1° per count)
        counts = int(gripper_angle_deg / 0.1)

        response.position = counts
        response.success = True

        self.get_logger().info(f"Gripper position (counts): {counts}")

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
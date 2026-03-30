from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='xarm_nodes',
            executable='arduino',
            output='screen'
        ),
        Node(
            package='xarm_nodes',
            executable='x_arm_hardware_node',
            output='screen'
        ),
        Node(
            package='xarm_nodes',
            executable='RetrieveItemsActionServer',
            output='screen'
        ),




        Node(
            package='xarm_nodes',
            executable='drive_pickup',
            output='screen'
        ),
    ])
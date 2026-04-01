from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    usb_cam_params = PathJoinSubstitution([
        FindPackageShare('xarm_nodes'),
        'config',
        'usb_cam_params.yaml'
    ])
     
    return LaunchDescription([
        Node(
            package='xarm_nodes',
            executable='retrieve_items_action_server',
            output='screen'
        ),
        Node(
            package='xarm_nodes',
            executable='x_arm_hardware_node',
            output='screen'
        ),
        Node(
            package='xarm_nodes',
            executable='drive_pickup',
            output='screen'
        ),

        Node(
            package='xarm_nodes',
            executable='camera_node', 
            output='screen'
        ),

        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            #parameters=['usb_cam_params.yaml'],
            parameters=[usb_cam_params],
            output='screen'
        ),

    ])
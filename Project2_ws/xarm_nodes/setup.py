from setuptools import find_packages, setup

package_name = 'xarm_nodes'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),


    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/project2_launch.py']),
    ],



    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='laptopuser',
    maintainer_email='laptopuser@todo.todo',
    description='Hardware node skeleton for Xarm student projects.',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'x_arm_hardware_node = xarm_nodes.x_arm_hardware_node:main',
            'pickup_gui = xarm_nodes.pickup_gui:main',
            'retrieve_items_action_server = xarm_nodes.retrieve_items_action_server:main',
            'service_client = xarm_nodes.service_client:main',
            'arduino = xarm_nodes.arduino:main',
            'drive_pickup = xarm_nodes.drive_pickup:main',
        ],
    },
)

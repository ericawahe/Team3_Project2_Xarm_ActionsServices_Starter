#!/usr/bin/env python3
"""
pickup_gui.py — Pre-built GUI client for the xArm pickup action.

NOTE FOR STUDENTS: You do not need to modify this file.
Run it as-is to interact with the RetrieveItems action server you implement
in your action server node.

Overview:
  - PickupGuiWindow     : tkinter window that lets the operator set the number
                          of items to collect, trigger the action, and cancel it.
  - XarmPickupGuiClient : ROS2 action client that sends RetrieveItems goals,
                          processes feedback, and handles results/cancellation.

Thread safety:
  tkinter is not thread-safe, so all GUI updates are posted through a
  queue.Queue. The window polls that queue every 50 ms via tkinter's
  after() scheduler and applies updates on the main thread.
"""

import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from xarm_pickup_interfaces.action import RetrieveItems


class XarmPickupGuiClient(Node):
    """ROS2 action client node for the RetrieveItems action.

    Runs inside a background thread (see _spin_ros) so that ROS callbacks do
    not block the tkinter event loop. All GUI updates are posted to ui_queue
    as (key, value) tuples and consumed by PickupGuiWindow._poll_queue().
    """

    def __init__(self, ui_queue: queue.Queue):
        super().__init__('xarm_pickup_gui_client')
        self.ui_queue = ui_queue          # Thread-safe channel to the GUI
        self.action_client = ActionClient(self, RetrieveItems, 'retrieve_items')
        self.goal_handle = None
        self._goal_lock = threading.Lock()  # Protects self.goal_handle across threads

    def _post(self, key: str, value):
        """Post a GUI update to the queue."""
        self.ui_queue.put((key, value))

    def send_goal(self, num_items: int):
        """Send a RetrieveItems goal to the action server."""
        if not self.action_client.wait_for_server(timeout_sec=2.0):
            self._post('status', 'Server not available')
            self._post('goal_active', False)
            return

        goal_msg = RetrieveItems.Goal()
        goal_msg.num_items = num_items

        self._post('status', f'Sending goal: num_items={num_items}')
        send_future = self.action_client.send_goal_async(
            goal_msg, feedback_callback=self._feedback_callback
        )
        send_future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        """Called when the server accepts or rejects the goal."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._post('status', 'Goal rejected')
            self._post('goal_active', False)
            return

        with self._goal_lock:
            self.goal_handle = goal_handle

        self._post('status', 'Goal accepted')
        self._post('goal_active', True)

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _feedback_callback(self, feedback_msg):
        """Forward action feedback fields to the GUI via the queue."""
        feedback = feedback_msg.feedback
        box_text = str(feedback.current_box) if feedback.current_box >= 0 else 'N/A'

        self._post('state', feedback.state)
        self._post('box', box_text)
        self._post('items', str(feedback.items_collected))
        self._post('status', 'Feedback received')

    def _result_callback(self, future):
        """Called when the action finishes (success, failure, or cancelled)."""
        result = future.result().result
        self._post('status', f'Done: success={result.success} items={result.items_collected}')
        self._post('goal_active', False)

        with self._goal_lock:
            self.goal_handle = None

    def cancel_goal(self):
        """Request cancellation of the currently active goal, if any."""
        with self._goal_lock:
            active_goal = self.goal_handle

        if active_goal is None:
            self._post('status', 'No active goal to cancel')
            return

        self._post('status', 'Cancel requested')
        cancel_future = active_goal.cancel_goal_async()
        cancel_future.add_done_callback(self._cancel_done_callback)

    def _cancel_done_callback(self, future):
        cancel_response = future.result()
        if len(cancel_response.goals_canceling) > 0:
            self._post('status', 'Cancel accepted by server')
        else:
            self._post('status', 'Cancel rejected or goal already finished')


class PickupGuiWindow:
    """Main tkinter application window.

    Provides controls to set the number of items to collect, send the action
    goal, cancel an in-progress goal, and display live feedback from the
    action server.
    """

    _POLL_MS = 50  # How often (ms) to drain the update queue

    def __init__(self, root: tk.Tk, ros_node: XarmPickupGuiClient, ui_queue: queue.Queue):
        self.root = root
        self.ros_node = ros_node
        self.ui_queue = ui_queue

        root.title('Xarm Grid Pickup')
        root.resizable(False, False)

        self._build_ui()
        self._poll_queue()  # Start the recurring queue-drain loop

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        # --- Input row ---
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill='x', **pad)
        ttk.Label(input_frame, text='Number of items (1–9):').pack(side='left')
        self._spin_var = tk.IntVar(value=1)
        ttk.Spinbox(input_frame, from_=1, to=9, textvariable=self._spin_var, width=4).pack(side='left', padx=4)

        # --- Buttons ---
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', **pad)
        self._btn_call = ttk.Button(btn_frame, text='Call Action', command=self._on_call_action)
        self._btn_call.pack(side='left', padx=(0, 4))
        self._btn_cancel = ttk.Button(btn_frame, text='Cancel', command=self._on_cancel_action, state='disabled')
        self._btn_cancel.pack(side='left')

        # --- Status grid ---
        status_frame = ttk.LabelFrame(self.root, text='Status')
        status_frame.pack(fill='x', **pad)

        labels = [('Status', 'Idle'), ('Current state', '—'), ('Current box', '—'), ('Items collected', '0')]
        self._value_status = tk.StringVar(value='Idle')
        self._value_state  = tk.StringVar(value='—')
        self._value_box    = tk.StringVar(value='—')
        self._value_items  = tk.StringVar(value='0')
        string_vars = [self._value_status, self._value_state, self._value_box, self._value_items]

        for row, ((lbl, _), var) in enumerate(zip(labels, string_vars)):
            ttk.Label(status_frame, text=lbl).grid(row=row, column=0, sticky='w', **pad)
            ttk.Label(status_frame, textvariable=var, width=30, anchor='w').grid(row=row, column=1, sticky='w', **pad)

    def _poll_queue(self):
        """Drain all pending GUI updates from the queue and apply them."""
        try:
            while True:
                key, value = self.ui_queue.get_nowait()
                if key == 'status':
                    self._value_status.set(value)
                elif key == 'state':
                    self._value_state.set(value)
                elif key == 'box':
                    self._value_box.set(value)
                elif key == 'items':
                    self._value_items.set(value)
                elif key == 'goal_active':
                    self._set_goal_active(value)
        except queue.Empty:
            pass
        finally:
            # Reschedule unconditionally so the loop keeps running
            self.root.after(self._POLL_MS, self._poll_queue)

    def _on_call_action(self):
        self._set_goal_active(True)
        threading.Thread(
            target=self.ros_node.send_goal,
            args=(self._spin_var.get(),),
            daemon=True,
        ).start()

    def _on_cancel_action(self):
        self.ros_node.cancel_goal()

    def _set_goal_active(self, active: bool):
        self._btn_call.config(state='disabled' if active else 'normal')
        self._btn_cancel.config(state='normal' if active else 'disabled')


def _spin_ros(node: Node):
    """Spin the ROS node in a background thread so it does not block tkinter."""
    rclpy.spin(node)


def main(args=None):
    rclpy.init(args=args)

    ui_queue = queue.Queue()
    ros_node = XarmPickupGuiClient(ui_queue)

    ros_thread = threading.Thread(target=_spin_ros, args=(ros_node,), daemon=True)
    ros_thread.start()

    root = tk.Tk()
    PickupGuiWindow(root, ros_node, ui_queue)
    root.mainloop()

    ros_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()


# filename: dashboard_ui.py
import tkinter as tk
from tkinter import ttk
import asyncio
import websockets
import threading
import queue
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import time
import os

WEBSOCKET_URI = "ws://localhost:8765"
SAMPLE_LIMIT = 200

incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gripper Force Monitor")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        s = ttk.Style()
        s.configure('Emergency.TButton', foreground='white', background='red', font=('Helvetica', 10, 'bold'))
        s.configure('Highlight.TButton', foreground='black', background='#4CAF50', font=('Helvetica', 10, 'bold'))
        s.configure('TButton', font=('Helvetica', 10))

        self.start_time = time.time()
        self.time_axis = deque(maxlen=SAMPLE_LIMIT)
        self.left_claw_raw = deque(maxlen=SAMPLE_LIMIT)
        self.left_claw_filtered = deque(maxlen=SAMPLE_LIMIT)
        self.right_claw_raw = deque(maxlen=SAMPLE_LIMIT)
        self.right_claw_filtered = deque(maxlen=SAMPLE_LIMIT)
        self.pid_input_force = deque(maxlen=SAMPLE_LIMIT)

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        control_frame = ttk.Frame(main_frame, width=250)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        control_frame.pack_propagate(False)

        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
        self.line_left_raw, = self.ax1.plot([], [], 'r-', alpha=0.5, label="Raw Average")
        self.line_left_filtered, = self.ax1.plot([], [], 'r-', linewidth=2, label="Kalman Filtered")
        self.ax1.set_title("Left Claw Force")
        self.ax1.set_ylabel("FSR ADC Value")
        self.ax1.set_ylim(-100, 4200)
        self.ax1.grid(True)
        self.ax1.legend()
        self.line_right_raw, = self.ax2.plot([], [], 'b-', alpha=0.5, label="Raw Average")
        self.line_right_filtered, = self.ax2.plot([], [], 'b-', linewidth=2, label="Kalman Filtered")
        self.ax2.set_title("Right Claw Force")
        self.ax2.set_ylabel("FSR ADC Value")
        self.ax2.set_ylim(-100, 4200)
        self.ax2.grid(True)
        self.ax2.legend()
        self.line_pid_input, = self.ax3.plot([], [], 'g-', linewidth=2.5, label="PID Input (Max Force)")
        self.ax3.set_title("PID Controller Input")
        self.ax3.set_ylabel("FSR ADC Value")
        self.ax3.set_xlabel("Time (s)")
        self.ax3.set_ylim(-100, 4200)
        self.ax3.grid(True)
        self.ax3.legend()
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        status_panel = ttk.LabelFrame(control_frame, text="Object Identification", padding=10)
        status_panel.pack(fill=tk.X, padx=10, pady=10)
        self.status_label = ttk.Label(status_panel, text="Initializing...", font=("Helvetica", 11, "italic"), wraplength=200)
        self.status_label.pack(pady=(0, 10))
        self.egg_btn = ttk.Button(status_panel, text="EGG")
        self.egg_btn.pack(fill=tk.X, pady=2)
        self.pbox_btn = ttk.Button(status_panel, text="PAPER BOX")
        self.pbox_btn.pack(fill=tk.X, pady=2)
        self.pbank_btn = ttk.Button(status_panel, text="POWER BANK")
        self.pbank_btn.pack(fill=tk.X, pady=2)
        self.reset_btn = ttk.Button(status_panel, text="Reset Identification", command=lambda: self._send_command("CMD:RESET"))
        self.reset_btn.pack(fill=tk.X, pady=(10, 0))

        command_panel = ttk.LabelFrame(control_frame, text="Gripper Commands", padding=10)
        command_panel.pack(fill=tk.X, padx=10, pady=10)
        self.grasp_btn = ttk.Button(command_panel, text="GRASP", command=lambda: self._send_command("CMD:GRASP"))
        self.grasp_btn.pack(fill=tk.X, padx=10, pady=5)
        self.release_btn = ttk.Button(command_panel, text="RELEASE", command=lambda: self._send_command("CMD:RELEASE"))
        self.release_btn.pack(fill=tk.X, padx=10, pady=5)
        emergency_btn = ttk.Button(command_panel, text="EMERGENCY RELEASE", style='Emergency.TButton', command=lambda: self._send_command("CMD:EMERGENCY"))
        emergency_btn.pack(fill=tk.X, padx=10, pady=(15, 5))

        self._update_ui_state("STATUS:IDENTIFYING")
        self.ani = animation.FuncAnimation(self.fig, self._animate, interval=100, blit=False, cache_frame_data=False)
        self.root.after(100, self._process_incoming_data)

    def _send_command(self, cmd):
        print(f"[Dashboard] Sending command: {cmd}")
        outgoing_queue.put(cmd)

    def _update_ui_state(self, status_msg):
        parts = status_msg.split(':')
        state = parts[1]
        self.egg_btn.configure(style='TButton')
        self.pbox_btn.configure(style='TButton')
        self.pbank_btn.configure(style='TButton')
        if state == "IDENTIFYING":
            self.status_label.configure(text="Show object to the camera...")
            self.grasp_btn.configure(state=tk.DISABLED)
            self.reset_btn.configure(state=tk.DISABLED)
        elif state == "LOCKED":
            locked_object = parts[2]
            self.status_label.configure(text=f"Object Locked: {locked_object}")
            self.grasp_btn.configure(state=tk.NORMAL)
            self.reset_btn.configure(state=tk.NORMAL)
            if locked_object == "EGG":
                self.egg_btn.configure(style='Highlight.TButton')
            elif locked_object == "PAPER_BOX":
                self.pbox_btn.configure(style='Highlight.TButton')
            elif locked_object == "POWER_BANK":
                self.pbank_btn.configure(style='Highlight.TButton')

    def _process_incoming_data(self):
        try:
            while not incoming_queue.empty():
                msg = incoming_queue.get_nowait()
                if msg.startswith("DATA:"):
                    parts = msg.split(':')[1].split(',')
                    if len(parts) == 5:
                        left_raw, left_filt, right_raw, right_filt, pid_in = map(float, parts)
                        self.time_axis.append(time.time() - self.start_time)
                        self.left_claw_raw.append(left_raw)
                        self.left_claw_filtered.append(left_filt)
                        self.right_claw_raw.append(right_raw)
                        self.right_claw_filtered.append(right_filt)
                        self.pid_input_force.append(pid_in)
                elif msg.startswith("STATUS:"):
                    self._update_ui_state(msg)
        finally:
            self.root.after(100, self._process_incoming_data)

    def _animate(self, frame):
        self.line_left_raw.set_data(self.time_axis, self.left_claw_raw)
        self.line_left_filtered.set_data(self.time_axis, self.left_claw_filtered)
        self.line_right_raw.set_data(self.time_axis, self.right_claw_raw)
        self.line_right_filtered.set_data(self.time_axis, self.right_claw_filtered)
        self.line_pid_input.set_data(self.time_axis, self.pid_input_force)
        if self.time_axis:
            t_min = self.time_axis[0]
            t_max = self.time_axis[-1] if len(self.time_axis) > 1 else t_min + 1
            if t_max - t_min < 10:
                t_max = t_min + 10
            for ax in [self.ax1, self.ax2, self.ax3]:
                ax.set_xlim(t_min, t_max)
        return self.line_left_raw, self.line_left_filtered, self.line_right_raw, self.line_right_filtered, self.line_pid_input

    def _on_closing(self):
        print("[Dashboard] Shutdown signal received. Closing application.")
        shutdown_event.set()
        self.root.quit()
        self.root.destroy()
        os._exit(0)

def websocket_thread():
    async def receiver(websocket):
        async for message in websocket:
            if shutdown_event.is_set(): break
            incoming_queue.put(message)
    async def sender(websocket):
        while not shutdown_event.is_set():
            try:
                command = outgoing_queue.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                await asyncio.sleep(0.05)
    async def client_handler():
        while not shutdown_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print("[NetworkThread] Connected to server.")
                    await asyncio.gather(receiver(websocket), sender(websocket))
            except (ConnectionRefusedError, OSError):
                if not shutdown_event.is_set():
                    print(f"[NetworkThread] Connection refused. Is server.py running? Retrying...")
                    await asyncio.sleep(2)
            except Exception as e:
                if not shutdown_event.is_set():
                    print(f"[NetworkThread] An unexpected network error occurred: {type(e).__name__}: {e}")
                    await asyncio.sleep(2)
    asyncio.run(client_handler())


if __name__ == "__main__":
    net_thread = threading.Thread(target=websocket_thread, daemon=True)
    net_thread.start()
    root = tk.Tk()
    app = DashboardApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app._on_closing()
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

# --- CONFIGURATION ---
WEBSOCKET_URI = "ws://localhost:8765"
SAMPLE_LIMIT = 200

# --- FSR SENSOR MAPPING ---
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# --- THREADING AND QUEUES ---
incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Robotic Gripper Control Panel")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.start_time = time.time()
        self.time_axis = deque(maxlen=SAMPLE_LIMIT)
        self.left_claw_force = deque(maxlen=SAMPLE_LIMIT)
        self.right_claw_force = deque(maxlen=SAMPLE_LIMIT)

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        control_frame = ttk.Frame(main_frame, width=200)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        control_frame.pack_propagate(False)

        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
        
        self.line_left, = self.ax1.plot([], [], 'r-', label="Left Claw Force")
        self.ax1.set_title("Left Claw Force")
        self.ax1.set_ylabel("Average FSR ADC")
        self.ax1.set_ylim(-100, 4200)
        self.ax1.grid(True)
        self.ax1.legend()

        self.line_right, = self.ax2.plot([], [], 'b-', label="Right Claw Force")
        self.ax2.set_title("Right Claw Force")
        self.ax2.set_ylabel("Average FSR ADC")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylim(-100, 4200)
        self.ax2.grid(True)
        self.ax2.legend()
        
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ttk.Label(control_frame, text="Commands", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        grasp_btn = ttk.Button(control_frame, text="GRASP", command=lambda: self._send_command("CMD:GRASP"))
        grasp_btn.pack(fill=tk.X, padx=20, pady=5)
        
        release_btn = ttk.Button(control_frame, text="RELEASE", command=lambda: self._send_command("CMD:RELEASE"))
        release_btn.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=20, padx=5)

        s = ttk.Style()
        s.configure('Emergency.TButton', foreground='white', background='red', font=('Helvetica', 10, 'bold'))
        
        emergency_btn = ttk.Button(control_frame, text="EMERGENCY RELEASE", style='Emergency.TButton', command=lambda: self._send_command("CMD:EMERGENCY"))
        emergency_btn.pack(fill=tk.X, padx=20, pady=5)

        self.ani = animation.FuncAnimation(self.fig, self._animate, interval=100, blit=False, cache_frame_data=False)
        self.root.after(100, self._process_incoming_data)

    def _send_command(self, cmd):
        print(f"[Dashboard] Sending command: {cmd}")
        outgoing_queue.put(cmd)

    def _process_incoming_data(self):
        try:
            while not incoming_queue.empty():
                msg = incoming_queue.get_nowait()
                parts = msg.split(',')
                if len(parts) == 10 and parts[0].isdigit():
                    left_vals = [int(parts[i]) for i in LEFT_CLAW_INDICES]
                    avg_left = sum(left_vals) / len(left_vals)
                    right_vals = [int(parts[i]) for i in RIGHT_CLAW_INDICES]
                    avg_right = sum(right_vals) / len(right_vals)
                    self.time_axis.append(time.time() - self.start_time)
                    self.left_claw_force.append(avg_left)
                    self.right_claw_force.append(avg_right)
        finally:
            self.root.after(100, self._process_incoming_data)

    def _animate(self, frame):
        self.line_left.set_data(self.time_axis, self.left_claw_force)
        self.line_right.set_data(self.time_axis, self.right_claw_force)
        if self.time_axis:
            self.ax1.set_xlim(self.time_axis[0], self.time_axis[-1])
        return self.line_left, self.line_right,

    def _on_closing(self):
        """Handles the shutdown sequence."""
        print("[Dashboard] Shutdown signal received. Closing application.")
        shutdown_event.set()
        self.root.quit()
        self.root.destroy()
        os._exit(0)

# --- CORRECTED WEBSOCKET THREAD ---
def websocket_thread():
    """Handles all websocket communication in a separate, robust thread."""
    
    # This task handles receiving messages from the server
    async def receiver(websocket):
        async for message in websocket:
            if shutdown_event.is_set(): break
            # Only put sensor data into the queue for the GUI
            if not message.startswith("CMD:") and not message.startswith("SERVO"):
                incoming_queue.put(message)

    # This task handles sending messages from the GUI
    async def sender(websocket):
        while not shutdown_event.is_set():
            try:
                command = outgoing_queue.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                # Use a small sleep to prevent this loop from running at 100% CPU
                await asyncio.sleep(0.05) 
            except websockets.exceptions.ConnectionClosed:
                break # Exit if the connection is closed

    # The main handler that connects and runs the tasks
    async def client_handler():
        while not shutdown_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print("[NetworkThread] Connected to server.")
                    # Run listener and sender tasks concurrently. They will run until one fails.
                    await asyncio.gather(
                        receiver(websocket),
                        sender(websocket)
                    )
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
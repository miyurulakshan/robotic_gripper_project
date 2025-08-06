# filename: dashboard.py
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from collections import deque
import threading

class Dashboard:
    def __init__(self, root, sample_limit=200):
        self.root = root
        self.sample_limit = sample_limit
        self.root.title("Single Servo PID Control Dashboard")

        self.data_lock = threading.Lock()
        
        # Data deques for a single claw
        self.time_axis = deque(maxlen=sample_limit)
        self.claw1_force = deque(maxlen=sample_limit)
        self.claw1_setpoint = deque(maxlen=sample_limit)
        self.servo1_angle = deque(maxlen=sample_limit)

        plot_frame = ttk.Frame(self.root, padding="10")
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create a 2x1 plot layout
        self.fig, self.axs = plt.subplots(2, 1, figsize=(8, 10))
        
        # --- Plot 1: Claw 1 Force Control ---
        self.ax1 = self.axs[0]
        self.line_force1, = self.ax1.plot([], [], 'r-', label="Claw Avg Force")
        self.line_setpoint1, = self.ax1.plot([], [], 'g--', label="Setpoint")
        self.ax1.set_title("Claw Force Control")
        self.ax1.set_ylabel("FSR ADC Value")
        self.ax1.set_ylim(0, 4100)
        self.ax1.legend()
        self.ax1.grid(True)

        # --- Plot 2: Servo 1 Angle ---
        self.ax2 = self.axs[1]
        self.line_servo1, = self.ax2.plot([], [], 'b-', label="Servo Angle")
        self.ax2.set_title("Servo Motor Angle")
        self.ax2.set_ylabel("Angle (degrees)")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylim(-5, 185)
        self.ax2.legend()
        self.ax2.grid(True)
        
        self.fig.suptitle('Gripper State Monitoring', fontsize=16, weight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_data(self, data_dict):
        with self.data_lock:
            self.time_axis.append(data_dict['time'])
            self.claw1_force.append(data_dict['c1_force'])
            self.claw1_setpoint.append(data_dict['c1_setpoint'])
            self.servo1_angle.append(data_dict['s1_angle'])

    def _animate(self, frame):
        with self.data_lock:
            # Update data for all plots
            self.line_force1.set_data(self.time_axis, self.claw1_force)
            self.line_setpoint1.set_data(self.time_axis, self.claw1_setpoint)
            self.line_servo1.set_data(self.time_axis, self.servo1_angle)

            # Update x-axis limits
            if self.time_axis:
                min_time, max_time = self.time_axis[0], self.time_axis[-1]
                for ax in [self.ax1, self.ax2]:
                    ax.set_xlim(min_time, max_time)
        
        return [self.line_force1, self.line_setpoint1, self.line_servo1]

    def run(self):
        self.ani = animation.FuncAnimation(self.fig, self._animate, interval=50, blit=False)
        self.root.mainloop()

    def stop(self):
        if hasattr(self, 'ani') and self.ani.event_source:
            self.ani.event_source.stop()
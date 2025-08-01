import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from collections import deque
import threading

class Dashboard:
    def __init__(self, root, num_sensors=8, sample_limit=200):
        self.root = root
        self.num_sensors = num_sensors
        self.sample_limit = sample_limit
        self.root.title("Robotic Gripper Monitoring Dashboard")

        self.data_lock = threading.Lock()
        self.raw_data = [deque(maxlen=sample_limit) for _ in range(num_sensors)]
        self.filtered_data = [deque(maxlen=sample_limit) for _ in range(num_sensors)]
        self.time_axis = deque(maxlen=sample_limit)

        plot_frame = ttk.Frame(self.root, padding="10")
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- Matplotlib Plotting Setup (Reordered) ---
        # Create a 4-row, 2-column grid for the subplots
        self.fig, self.axs = plt.subplots(4, 2, figsize=(14, 10))
        # NOTE: We do NOT flatten the axs array, we will access it by (row, col)
        
        self.lines_raw = [None] * num_sensors
        self.lines_filtered = [None] * num_sensors

        for i in range(num_sensors):
            # Determine the correct row and column for the plot
            if i < 4:  # FSR 1-4 go in the left column
                row, col = i, 0
            else:      # FSR 5-8 go in the right column
                row, col = i - 4, 1
            
            ax = self.axs[row, col] # Select the correct subplot

            line_raw, = ax.plot([], [], 'b-', alpha=0.5, animated=True, label="Raw")
            line_filtered, = ax.plot([], [], 'r-', linewidth=1.5, animated=True, label="Filtered")
            
            # Store the line objects in the correct index
            self.lines_raw[i] = line_raw
            self.lines_filtered[i] = line_filtered

            ax.set_title(f'FSR Sensor {i+1}', fontsize=9)
            ax.set_ylim(0, 4100)
            ax.grid(True)
            ax.legend(fontsize='x-small')
        
        self.fig.suptitle('Real-Time FSR Sensor Data', fontsize=16, weight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_data(self, raw, filtered, time):
        with self.data_lock:
            self.time_axis.append(time)
            for i in range(self.num_sensors):
                self.raw_data[i].append(raw[i])
                self.filtered_data[i].append(filtered[i])

    def _animate(self, frame):
        with self.data_lock:
            for i in range(self.num_sensors):
                # Determine the correct subplot axis to update
                if i < 4:
                    row, col = i, 0
                else:
                    row, col = i - 4, 1
                ax = self.axs[row, col]

                self.lines_raw[i].set_data(self.time_axis, self.raw_data[i])
                self.lines_filtered[i].set_data(self.time_axis, self.filtered_data[i])
                if self.time_axis:
                    ax.set_xlim(self.time_axis[0], self.time_axis[-1])
        
        # Return a flattened list of all line objects for the animation
        return self.lines_raw + self.lines_filtered

    def run(self):
        self.ani = animation.FuncAnimation(self.fig, self._animate, interval=50, blit=True)
        self.root.mainloop()

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

class MultiPlotter:
    def __init__(self, num_sensors=8, sample_limit=200):
        """
        Initializes the multi-plotter for real-time data visualization.
        Args:
            num_sensors (int): The number of sensors to plot (e.g., 8).
            sample_limit (int): The number of historical data points to show on each graph.
        """
        self.num_sensors = num_sensors
        self.sample_limit = sample_limit

        # Create deques (double-ended queues) to efficiently store data
        self.raw_data = [deque(maxlen=sample_limit) for _ in range(num_sensors)]
        self.filtered_data = [deque(maxlen=sample_limit) for _ in range(num_sensors)]
        self.time_axis = deque(maxlen=sample_limit)

        # --- Scientific Plot Setup for 8 Graphs ---
        # Create a figure with 4 rows and 2 columns of subplots
        self.fig, self.axs = plt.subplots(4, 2, figsize=(15, 12))
        self.axs = self.axs.flatten()  # Flatten the 2D array of axes for easy iteration
        self.lines_raw = []
        self.lines_filtered = []

        for i in range(num_sensors):
            # Plot raw data line (blue, semi-transparent)
            line_raw, = self.axs[i].plot([], [], 'b-', alpha=0.5, label='Raw Data')
            # Plot filtered data line (red, solid)
            line_filtered, = self.axs[i].plot([], [], 'r-', linewidth=2, label='Kalman Filtered')
            
            self.lines_raw.append(line_raw)
            self.lines_filtered.append(line_filtered)

            # Configure aesthetics for each subplot
            self.axs[i].set_title(f'FSR Sensor {i+1}', fontsize=10)
            self.axs[i].set_ylim(0, 4100) # ESP32-S3 ADC is 12-bit
            self.axs[i].grid(True)
            self.axs[i].legend(fontsize='small')

        self.fig.suptitle('Real-Time FSR Gripper Data', fontsize=16, weight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout to make room for suptitle

    def update_data(self, raw_readings, filtered_readings, timestamp):
        """Public method to add new data points to the plot queues."""
        self.time_axis.append(timestamp)
        for i in range(self.num_sensors):
            self.raw_data[i].append(raw_readings[i])
            self.filtered_data[i].append(filtered_readings[i])

    def _animate(self, frame):
        """Internal animation function called by matplotlib."""
        for i in range(self.num_sensors):
            self.lines_raw[i].set_data(self.time_axis, self.raw_data[i])
            self.lines_filtered[i].set_data(self.time_axis, self.filtered_data[i])
            
            # Dynamically adjust x-axis limits
            if self.time_axis:
                self.axs[i].set_xlim(self.time_axis[0], self.time_axis[-1])

        return self.lines_raw + self.lines_filtered

    def run(self):
        """Starts the plotting window and animation."""
        print("[Plotter] Starting real-time plotting window...")
        ani = animation.FuncAnimation(self.fig, self._animate, interval=50, blit=True)
        plt.show()


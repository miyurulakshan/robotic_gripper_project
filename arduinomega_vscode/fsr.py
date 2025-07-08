# In here we are testing the FSR and getting the delay of FSR readings and addressing 
# the delay in the FSR readings using kalman filter.

import serial
import time
import matplotlib.pyplot as plt
from collections import deque
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.live import Live

# --- Configuration ---
# IMPORTANT: Change this to your Arduino's serial port
SERIAL_PORT = 'COM5'  # For Windows. For Mac/Linux, it might be '/dev/tty.usbmodemXXXX'
# This matches your Arduino code's baud rate
BAUD_RATE = 115200
MAX_DATA_POINTS = 100  # Number of data points to display on the plot

# --- Global Variables ---
ser = None
data_queue = deque(maxlen=MAX_DATA_POINTS)
time_queue = deque(maxlen=MAX_DATA_POINTS)
last_time = time.perf_counter()
delays = deque(maxlen=MAX_DATA_POINTS)

# --- Rich Table Setup ---
console = Console()
table = Table(show_header=True, header_style="bold magenta")
table.add_column("Timestamp (s)", style="dim", width=20)
table.add_column("FSR Reading", justify="right")
table.add_column("Delay (ms)", justify="right")

def setup_serial():
    """Initializes the serial connection to the Arduino."""
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for the connection to establish
        console.print(f"✅ Serial connection established on {SERIAL_PORT} at {BAUD_RATE} baud.", style="bold green")
        return True
    except serial.SerialException as e:
        console.print(f"❌ Error: Could not open serial port {SERIAL_PORT}.", style="bold red")
        console.print(f"   Please check the port name and ensure the Arduino is connected.", style="red")
        console.print(f"   Error details: {e}", style="red")
        return False

def read_serial_data():
    """Reads a line of data from the serial port."""
    global last_time
    if not ser or not ser.in_waiting > 0:
        return None, None, None
    
    try:
        # Read the line and decode it from bytes to a string
        line = ser.readline().decode('utf-8').strip()
        
        if line:
            # Convert the line directly to an integer
            fsr_value = int(line)
            
            current_time = time.perf_counter()
            delay = (current_time - last_time) * 1000  # Delay in milliseconds
            last_time = current_time

            data_queue.append(fsr_value)
            time_queue.append(current_time)
            delays.append(delay)
            
            return current_time, fsr_value, delay
    except ValueError:
        console.print(f"⚠️ Warning: Could not convert data to integer: '{line}'", style="yellow")
    except UnicodeDecodeError:
        console.print(f"⚠️ Warning: Unicode decode error. A non-UTF8 byte was received.", style="yellow")
    
    return None, None, None

def update_plot(ax):
    """Manually redraws the plot with the latest data."""
    if not time_queue:
        return

    start_time = time_queue[0]
    relative_time = [t - start_time for t in time_queue]

    ax.clear()
    ax.plot(relative_time, data_queue, 'o-', color='b', markersize=4, label='FSR Reading')
    
    # --- Scientific Plot Styling ---
    ax.set_title("Real-Time FSR Sensor Readings", fontsize=16, fontweight='bold')
    ax.set_xlabel("Time Elapsed (s)", fontsize=12)
    ax.set_ylabel("FSR Reading (Analog Value)", fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left')
    ax.minorticks_on()
    
    if data_queue:
        min_val = min(data_queue)
        max_val = max(data_queue)
        ax.set_ylim(max(0, min_val - 50), min(1023, max_val + 50))
    
    if relative_time:
        ax.set_xlim(min(relative_time), max(relative_time) + 1)

    plt.tight_layout()

def main():
    """Main function to run the data acquisition and visualization."""
    if not setup_serial():
        return

    # --- Matplotlib Setup ---
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.show()

    # ** THE FIX IS HERE **
    # Clear the input buffer to discard any stale data that
    # accumulated while the script was starting up.
    console.print("Clearing serial buffer of any stale data...", style="italic blue")
    ser.reset_input_buffer()
    console.print("Buffer cleared. Starting live acquisition.", style="italic blue")

    # Reset the timer right before the loop starts for accurate delay measurement
    global last_time
    last_time = time.perf_counter()

    with Live(table, refresh_per_second=10, screen=True) as live:
        live.console.print("🚀 Starting data acquisition... Press Ctrl+C or close the plot window to stop.", style="bold cyan")
        
        while True:
            try:
                if not plt.get_fignums():
                    break

                timestamp, fsr_reading, delay = read_serial_data()
                if timestamp is not None:
                    if len(table.rows) > 15:
                        table.rows.pop(0)
                    table.add_row(f"{timestamp:.4f}", str(fsr_reading), f"{delay:.2f}", style="green")
                
                update_plot(ax)
                plt.pause(0.05)

            except KeyboardInterrupt:
                console.print("\n🛑 Stopping data acquisition.", style="bold yellow")
                break
            except Exception as e:
                console.print(f"An unexpected error occurred: {e}", style="bold red")
                break

    if ser and ser.is_open:
        ser.close()
        console.print("🔌 Serial port closed.", style="bold blue")

    # --- Final Analysis ---
    if len(delays) > 1:
        delays.popleft()
        avg_delay = np.mean(list(delays))
        max_delay = np.max(list(delays))
        min_delay = np.min(list(delays))
        std_dev = np.std(list(delays))
        
        console.print("\n--- Delay Analysis ---", style="bold magenta")
        console.print(f"Average Delay: {avg_delay:.2f} ms")
        console.print(f"Max Delay:     {max_delay:.2f} ms")
        console.print(f"Min Delay:     {min_delay:.2f} ms")
        console.print(f"Std Deviation: {std_dev:.2f} ms")
    
    console.print("👋 Program finished.")


if __name__ == "__main__":
    main()

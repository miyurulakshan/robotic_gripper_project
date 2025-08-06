# filename: pot_tuner.py
import asyncio
import websockets
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
from kalman_filter import KalmanFilter
import threading
import time

# --- TUNE THESE PARAMETERS ---
PROCESS_NOISE = 1e-3
MEASUREMENT_NOISE = 0.02
# -----------------------------

# --- SCRIPT CONFIGURATION ---
WEBSOCKET_URI = "ws://localhost:8765"
SAMPLE_LIMIT = 200
# -----------------------------

# --- DATA STORAGE ---
time_axis = deque(maxlen=SAMPLE_LIMIT)
raw_data = deque(maxlen=SAMPLE_LIMIT)
filtered_data = deque(maxlen=SAMPLE_LIMIT)
stop_thread = threading.Event()

# --- PLOT SETUP ---
fig, ax = plt.subplots(figsize=(12, 6))
line_raw, = ax.plot([], [], 'b-', alpha=0.6, label='Raw Potentiometer')
line_filtered, = ax.plot([], [], 'r-', linewidth=2, label='Kalman Filtered')
ax.set_title('Live Potentiometer Kalman Filter Tuning')
ax.set_xlabel('Time (s)')
ax.set_ylabel('ADC Value')
ax.set_ylim(0, 4100)
ax.legend()
ax.grid(True)
fig.canvas.manager.set_window_title('Potentiometer Tuner')

def network_thread():
    """Connects to the server and populates the data deques."""
    async def listen():
        print("--- Potentiometer Tuning Script ---")
        kf = KalmanFilter(PROCESS_NOISE, MEASUREMENT_NOISE)
        is_first_reading = True
        start_time = time.time()

        while not stop_thread.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print(f"Connected to {WEBSOCKET_URI}. Waiting for data...")
                    while not stop_thread.is_set():
                        message = await websocket.recv()
                        
                        # --- THIS IS THE FIX ---
                        # Ignore any messages that are servo commands.
                        if message.startswith("SERVO:"):
                            continue

                        readings = message.split(',')
                        raw_pot_value = int(readings[0])

                        if is_first_reading:
                            kf.x_hat = raw_pot_value
                            print("Kalman filter initialized.")
                            is_first_reading = False

                        filtered_pot_value = kf.update(raw_pot_value)
                        current_time = time.time() - start_time

                        time_axis.append(current_time)
                        raw_data.append(raw_pot_value)
                        filtered_data.append(filtered_pot_value)
            except Exception as e:
                print(f"Connection error: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    asyncio.run(listen())

def animate(frame):
    """Redraws the plot."""
    line_raw.set_data(list(time_axis), list(raw_data))
    line_filtered.set_data(list(time_axis), list(filtered_data))
    if time_axis:
        ax.set_xlim(time_axis[0], time_axis[-1] + 1)
    return line_raw, line_filtered

if __name__ == "__main__":
    listener = threading.Thread(target=network_thread, daemon=True)
    listener.start()

    ani = animation.FuncAnimation(fig, animate, interval=50, blit=False)
    
    try:
        plt.show()
    finally:
        print("Plot window closed. Shutting down.")
        stop_thread.set()

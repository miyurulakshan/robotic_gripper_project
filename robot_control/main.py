import threading
import queue
import asyncio
import time
import tkinter as tk

from server import WebSocketServer
from kalman_filter import KalmanFilter
from dashboard import Dashboard

# --- TUNABLE KALMAN FILTER PARAMETERS ---
PROCESS_NOISE = 1e-4
MEASUREMENT_NOISE = 0.05
# ----------------------------------------

def data_processing_thread(fsr_queue, dashboard):
    NUM_SENSORS = 8
    kalman_filters = [KalmanFilter(PROCESS_NOISE, MEASUREMENT_NOISE) for _ in range(NUM_SENSORS)]
    is_first_reading = True
    start_time = time.time()

    while True:
        try:
            data_packet = fsr_queue.get()
            raw_readings = [int(val) for val in data_packet.split(',')]

            if len(raw_readings) != NUM_SENSORS: continue

            if is_first_reading:
                for i in range(NUM_SENSORS):
                    kalman_filters[i] = KalmanFilter(PROCESS_NOISE, MEASUREMENT_NOISE, initial_value=raw_readings[i])
                print("[Main] Kalman filters initialized.")
                is_first_reading = False

            filtered_readings = [kf.update(raw) for kf, raw in zip(kalman_filters, raw_readings)]
            current_time = time.time() - start_time
            
            dashboard.update_data(raw_readings, filtered_readings, current_time)

        except Exception as e:
            print(f"[DataThread] Error: {e}")

def run_server_in_thread(server):
    asyncio.run(server.start())

if __name__ == "__main__":
    fsr_data_queue = queue.Queue()

    ws_server = WebSocketServer(fsr_data_queue)
    server_thread = threading.Thread(target=run_server_in_thread, args=(ws_server,), daemon=True)
    server_thread.start()

    root = tk.Tk()
    dashboard = Dashboard(root)

    processing_thread = threading.Thread(
        target=data_processing_thread,
        args=(fsr_data_queue, dashboard),
        daemon=True
    )
    processing_thread.start()

    dashboard.run()

    print("[Main] Dashboard closed. Application shutting down.")

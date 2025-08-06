# filename: main.py
import threading
import queue
import asyncio
import time
import tkinter as tk
import os
import matplotlib.pyplot as plt
import websockets

from kalman_filter import KalmanFilter
from dashboard import Dashboard

# --- CONFIGURATION ---
WEBSOCKET_URI = "ws://localhost:8765"
FSR_PROCESS_NOISE = 1e-4
FSR_MEASUREMENT_NOISE = 0.05

# --- NEW: Separate Kalman parameters for each potentiometer ---
POT1_PROCESS_NOISE = 1e-3
POT1_MEASUREMENT_NOISE = 0.01
POT2_PROCESS_NOISE = 1e-3
POT2_MEASUREMENT_NOISE = 0.07
# --------------------

incoming_data_queue = queue.Queue()
outgoing_command_queue = queue.Queue()

def data_processing_thread(dashboard, shutdown_event):
    """Processes data and sends back commands for both servos."""
    NUM_SENSORS = 8
    fsr_kalman_filters = [KalmanFilter(FSR_PROCESS_NOISE, FSR_MEASUREMENT_NOISE) for _ in range(NUM_SENSORS)]
    
    # --- NEW: Create two separate Kalman filters ---
    pot1_kf = KalmanFilter(POT1_PROCESS_NOISE, POT1_MEASUREMENT_NOISE)
    pot2_kf = KalmanFilter(POT2_PROCESS_NOISE, POT2_MEASUREMENT_NOISE)
    
    is_first_reading = True
    start_time = time.time()

    while not shutdown_event.is_set():
        try:
            data_packet = incoming_data_queue.get(timeout=1)

            if data_packet.startswith("SERVO"):
                continue

            # --- UPDATED: Expect 2 pot values + 8 FSR values ---
            all_readings = [int(val) for val in data_packet.split(',')]
            if len(all_readings) != NUM_SENSORS + 2:
                print(f"[DataThread] Warning: Received packet with {len(all_readings)} values. Skipping.")
                continue

            # --- UPDATED: Split the data correctly ---
            raw_pot1_reading = all_readings[0]
            raw_pot2_reading = all_readings[1]
            raw_fsr_readings = all_readings[2:]

            if is_first_reading:
                for i in range(NUM_SENSORS):
                    fsr_kalman_filters[i] = KalmanFilter(FSR_PROCESS_NOISE, FSR_MEASUREMENT_NOISE, initial_value=raw_fsr_readings[i])
                pot1_kf.x_hat = raw_pot1_reading
                pot2_kf.x_hat = raw_pot2_reading
                print("[Main] All Kalman filters initialized.")
                is_first_reading = False

            # Update FSR filters for the dashboard
            filtered_fsr_readings = [kf.update(raw) for kf, raw in zip(fsr_kalman_filters, raw_fsr_readings)]
            current_time = time.time() - start_time
            dashboard.update_data(raw_fsr_readings, filtered_fsr_readings, current_time)

            # --- UPDATED: Process and send commands for BOTH servos ---
            # Process Servo 1
            filtered_pot1 = pot1_kf.update(raw_pot1_reading)
            angle1 = int((max(0, min(4095, filtered_pot1)) / 4095) * 180)
            outgoing_command_queue.put(f"SERVO1:{angle1}")
            
            # Process Servo 2
            filtered_pot2 = pot2_kf.update(raw_pot2_reading)
            angle2 = int((max(0, min(4095, filtered_pot2)) / 4095) * 180)
            outgoing_command_queue.put(f"SERVO2:{angle2}")

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[DataThread] An error occurred: {e}")
    
    print("[DataThread] Processing thread has been shut down.")

def websocket_client_thread(shutdown_event):
    """Handles all websocket communication."""
    async def client_handler():
        while not shutdown_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print("[ClientThread] Connected to server.")
                    listen_task = asyncio.create_task(listen_for_messages(websocket))
                    send_task = asyncio.create_task(send_commands(websocket))
                    done, pending = await asyncio.wait([listen_task, send_task], return_when=asyncio.FIRST_COMPLETED)
                    for task in pending:
                        task.cancel()
            except (ConnectionRefusedError, websockets.exceptions.ConnectionClosed):
                print("[ClientThread] Connection lost. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    async def listen_for_messages(websocket):
        async for message in websocket:
            incoming_data_queue.put(message)

    async def send_commands(websocket):
        while not shutdown_event.is_set():
            try:
                command = outgoing_command_queue.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                await asyncio.sleep(0.01)
    
    asyncio.run(client_handler())


if __name__ == "__main__":
    shutdown_event = threading.Event()
    client_thread = threading.Thread(target=websocket_client_thread, args=(shutdown_event,), daemon=True)
    root = tk.Tk()
    dashboard = Dashboard(root)
    processing_thread = threading.Thread(target=data_processing_thread, args=(dashboard, shutdown_event))

    def on_closing():
        print("[Main] Close button pressed. Shutting down application...")
        shutdown_event.set()
        dashboard.stop()
        plt.close('all')
        processing_thread.join(timeout=2)
        root.destroy()
        print("[Main] Application has been shut down successfully.")
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    client_thread.start()
    processing_thread.start()
    dashboard.run()

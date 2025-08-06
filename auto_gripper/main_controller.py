# filename: main_controller.py
import threading
import queue
import asyncio
import time
import os
import websockets
from enum import Enum
import numpy as np

from kalman_filter import MultivariateKalmanFilter
from pid_controller import PIDController

# --- SYSTEM STATE ---
class GripperState(Enum):
    OPEN = 1
    CLOSING = 2
    HOLDING = 3
    RELEASING = 4

# --- CONFIGURATION & TUNING ---
WEBSOCKET_URI = "ws://localhost:8765"
OVERALL_TARGET_FORCE = 1600
MIN_FORCE_PER_CLAW = 1000
KP = 0.008
KI = 0.0005
KD = 0.001
SERVO_OPEN_PULSE = 0
SERVO_MAX_CLOSE_PULSE = 2000
SERVO_STEP_SIZE = 1.0
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# --- GLOBAL QUEUES & EVENTS ---
incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()


def data_processing_thread():
    current_state = GripperState.OPEN
    
    # --- KALMAN FILTER SETUP ---
    A = np.array([[1]])
    H = np.array([[1], [1], [1], [1]])
    x_hat_initial = np.array([[0]])
    P_initial = np.array([[100]])
    # Left Claw Tuning
    Q_left = np.array([[0.0001]])
    R_left = np.diag([0.5, 0.05, 0.05, 0.5]) 
    # Right Claw Tuning
    Q_right = np.array([[0.0001]])
    R_right = np.diag([0.5, 0.05, 0.05, 0.5])
    # Create filter instances
    kf_left_claw = MultivariateKalmanFilter(A, H, Q_left, R_left, x_hat_initial, P_initial)
    kf_right_claw = MultivariateKalmanFilter(A, H, Q_right, R_right, x_hat_initial, P_initial)

    pid = PIDController(Kp=KP, Ki=KI, Kd=KD, setpoint=OVERALL_TARGET_FORCE)
    is_first_reading = True
    servo_pulse = float(SERVO_OPEN_PULSE) 
    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
    
    print("[Controller] System initialized with Max Force logic. Press Ctrl+C to shut down.")

    while not shutdown_event.is_set():
        try:
            raw_packet = incoming_queue.get(timeout=0.5)
            data_packet = raw_packet.strip()

            if data_packet.startswith("CMD:"):
                command = data_packet.split(':')[1]
                print(f"[Controller] Command received: {command}")
                if command == "GRASP" and current_state == GripperState.OPEN:
                    current_state = GripperState.CLOSING
                    pid.reset()
                elif command in ("RELEASE", "EMERGENCY"):
                    current_state = GripperState.RELEASING
                print(f"[State Change] New state: {current_state.name}")
                continue

            try:
                all_readings = [int(val) for val in data_packet.split(',')]
                if len(all_readings) != 10: continue

                # --- DATA PROCESSING & FUSION ---
                left_raw_readings = [all_readings[i] for i in LEFT_CLAW_INDICES]
                right_raw_readings = [all_readings[i] for i in RIGHT_CLAW_INDICES]

                # Calculate the simple, unfiltered average for comparison
                left_raw_avg = sum(left_raw_readings) / len(left_raw_readings)
                right_raw_avg = sum(right_raw_readings) / len(right_raw_readings)

                # Create measurement vectors (z) for the Kalman filter
                left_z = np.array([[r] for r in left_raw_readings])
                right_z = np.array([[r] for r in right_raw_readings])

                if is_first_reading:
                    kf_left_claw.x_hat = np.array([[left_raw_avg]])
                    kf_right_claw.x_hat = np.array([[right_raw_avg]])
                    is_first_reading = False

                # Get the high-quality filtered force value
                left_force = kf_left_claw.update(left_z)[0, 0]
                right_force = kf_right_claw.update(right_z)[0, 0]
                
                # Use the maximum force for PID feedback
                overall_force = max(left_force, right_force)

                # --- SEND DETAILED DATA TO DASHBOARD ---
                data_to_send = f"DATA:{left_raw_avg},{left_force},{right_raw_avg},{right_force},{overall_force}"
                outgoing_queue.put(data_to_send)
                # -----------------------------------------

                if current_state == GripperState.CLOSING:
                    pid_output = pid.update(overall_force)
                    servo_pulse += pid_output * SERVO_STEP_SIZE
                    servo_pulse = max(SERVO_OPEN_PULSE, min(SERVO_MAX_CLOSE_PULSE, servo_pulse))
                    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
                    
                    if left_force > MIN_FORCE_PER_CLAW and right_force > MIN_FORCE_PER_CLAW:
                        current_state = GripperState.HOLDING
                        print(f"[State Change] Successful grasp. State: {current_state.name}")

                elif current_state == GripperState.RELEASING:
                    servo_pulse = float(SERVO_OPEN_PULSE)
                    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
                    current_state = GripperState.OPEN
                    print(f"[State Change] Release complete. State: {current_state.name}")

            except ValueError:
                continue

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Controller CRITICAL ERROR] An unexpected error occurred: {e}")
            break
    
    print("[Controller] Processing thread has been shut down.")


def websocket_client_thread(out_q, in_q, stop_event):
    async def sender(websocket):
        while not stop_event.is_set():
            try:
                command = out_q.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                await asyncio.sleep(0.02)
            except websockets.exceptions.ConnectionClosed:
                break
    async def receiver(websocket):
        while not stop_event.is_set():
            try:
                message = await websocket.recv()
                in_q.put(message)
            except websockets.exceptions.ConnectionClosed:
                break
    async def client_handler():
        while not stop_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI, open_timeout=3.0) as websocket:
                    print("[Controller Network] Connected to server.")
                    await asyncio.gather(sender(websocket), receiver(websocket))
            except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
                if not stop_event.is_set():
                    print("[Controller Network] Connection failed. Is server.py running? Retrying...")
                    await asyncio.sleep(2)
            except Exception as e:
                if not stop_event.is_set():
                    print(f"[Controller Network] An unexpected error occurred: {type(e).__name__}: {e}")
                    await asyncio.sleep(2)
    asyncio.run(client_handler())


if __name__ == "__main__":
    processing_thread = threading.Thread(target=data_processing_thread)
    client_thread = threading.Thread(target=websocket_client_thread, args=(outgoing_queue, incoming_queue, shutdown_event), daemon=True)

    print("[Main] Starting controller application.")
    client_thread.start()
    processing_thread.start()

    try:
        while processing_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Main] Ctrl+C detected. Initiating shutdown.")
    
    shutdown_event.set()
    processing_thread.join()
    print("[Main] Application has shut down.")

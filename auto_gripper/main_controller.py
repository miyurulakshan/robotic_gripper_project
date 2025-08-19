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
OVERALL_TARGET_FORCE = 700
ACCEPTABLE_ERROR_MARGIN = 100
MAX_CLAW_FORCE = 2000
MIN_FORCE_PER_CLAW = OVERALL_TARGET_FORCE


# --- PID GAINS (placeholder, you should tune these) ---
KP = 0.0002
KI = 0.0000001
KD = 0.000001

# --- MODIFIED: Servo Physical Parameters ---
SERVO_OPEN_PULSE = 1000  # The pulse value where the servo starts moving
SERVO_MAX_CLOSE_PULSE = 2100 # Maximum safe pulse value
SERVO_STEP_SIZE = 20.0   # The effective minimum step size of the servo

# --- SENSOR & KALMAN CONFIG ---
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# Kalman Gains from your tuning session
Q_left = np.array([[0.09]])
R_left = np.diag([3.1623, 3.1623, 3.1623, 3.1623])
Q_right = np.array([[0.09]])
R_right = np.diag([3.9811, 3.9811, 3.9811, 10.6606])


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
    kf_left_claw = MultivariateKalmanFilter(A, H, Q_left, R_left, x_hat_initial, P_initial)
    kf_right_claw = MultivariateKalmanFilter(A, H, Q_right, R_right, x_hat_initial, P_initial)

    pid = PIDController(Kp=KP, Ki=KI, Kd=KD, setpoint=OVERALL_TARGET_FORCE)
    is_first_reading = True
    servo_pulse = float(SERVO_OPEN_PULSE) 
    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
    
    print("[Controller] System initialized. Press Ctrl+C to shut down.")

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

                left_z = np.array([[r] for r in left_raw_readings])
                right_z = np.array([[r] for r in right_raw_readings])

                if is_first_reading:
                    left_raw_avg = np.mean(left_raw_readings)
                    right_raw_avg = np.mean(right_raw_readings)
                    kf_left_claw.x_hat = np.array([[left_raw_avg]])
                    kf_right_claw.x_hat = np.array([[right_raw_avg]])
                    is_first_reading = False

                left_force = kf_left_claw.update(left_z)[0, 0]
                right_force = kf_right_claw.update(right_z)[0, 0]
                
                overall_force = max(left_force, right_force)

                # Send processed data for visualization
                left_raw_avg = np.mean(left_raw_readings)
                right_raw_avg = np.mean(right_raw_readings)
                data_to_send = f"DATA:{left_raw_avg},{left_force},{right_raw_avg},{right_force},{overall_force}"
                outgoing_queue.put(data_to_send)

                if current_state == GripperState.CLOSING:
                    if left_force > MAX_CLAW_FORCE or right_force > MAX_CLAW_FORCE:
                        current_state = GripperState.HOLDING
                        print(f"[SAFETY OVERRIDE] Force limit of {MAX_CLAW_FORCE} exceeded. Switching to HOLDING.")
                        continue 
                    
                    pid_output = pid.update(overall_force)
                    # The PID output is now scaled by the effective step size
                    servo_pulse += pid_output * SERVO_STEP_SIZE
                    # Clamp the pulse to the servo's physical limits
                    servo_pulse = max(SERVO_OPEN_PULSE, min(SERVO_MAX_CLOSE_PULSE, servo_pulse))
                    
                    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
                    
                    error = OVERALL_TARGET_FORCE - overall_force
                    if abs(error) < ACCEPTABLE_ERROR_MARGIN and left_force > MIN_FORCE_PER_CLAW and right_force > MIN_FORCE_PER_CLAW:
                        current_state = GripperState.HOLDING
                        print(f"[State Change] Target force achieved. State: {current_state.name}")

                elif current_state == GripperState.RELEASING:
                    servo_pulse = float(SERVO_OPEN_PULSE)
                    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
                    current_state = GripperState.OPEN
                    print(f"[State Change] Release complete. State: {current_state.name}")

            except (ValueError, IndexError):
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

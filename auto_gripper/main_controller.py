# filename: main_controller.py
import threading
import queue
import asyncio
import time
import os
import websockets
from enum import Enum

from kalman_filter import KalmanFilter
from pid_controller import PIDController

# --- SYSTEM STATE ---
class GripperState(Enum):
    OPEN = 1
    CLOSING = 2
    HOLDING = 3
    RELEASING = 4

# --- CONFIGURATION & TUNING ---
WEBSOCKET_URI = "ws://localhost:8765"

OVERALL_TARGET_FORCE = 1500
MIN_FORCE_PER_CLAW = 1000

# NEW, GENTLER VALUES FOR FINE-TUNING
KP = 0.001  # <-- Drastically reduce Kp to slow down the closing speed
KI = 0.0005 # <-- Reduce Ki as well
KD = 0.001  # <-- Kd can often be small or zero

SERVO_OPEN_ANGLE = 0
SERVO_MAX_CLOSE_ANGLE = 170
SERVO_STEP_SIZE = 1
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# --- GLOBAL QUEUES & EVENTS ---
incoming_queue = queue.Queue()
outgoing_queue = queue.Queue() # <-- This is the correct, official name
shutdown_event = threading.Event()


def data_processing_thread():
    current_state = GripperState.OPEN
    NUM_SENSORS = 8
    fsr_kalman_filters = [KalmanFilter() for _ in range(NUM_SENSORS)]
    pid = PIDController(Kp=KP, Ki=KI, Kd=KD, setpoint=OVERALL_TARGET_FORCE)
    is_first_reading = True
    servo1_angle = SERVO_OPEN_ANGLE
    # --- FIX 1: Using the correct queue name ---
    outgoing_queue.put(f"SERVO1:{servo1_angle}")
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
                if len(all_readings) != NUM_SENSORS + 2: continue

                fsr_readings = all_readings[2:]
                if is_first_reading:
                    for i, reading in enumerate(fsr_readings):
                        fsr_kalman_filters[i].x_hat = reading
                    is_first_reading = False

                filtered_fsr = [kf.update(raw) for kf, raw in zip(fsr_kalman_filters, fsr_readings)]
                
                left_force = sum(filtered_fsr[i-2] for i in LEFT_CLAW_INDICES) / len(LEFT_CLAW_INDICES)
                right_force = sum(filtered_fsr[i-2] for i in RIGHT_CLAW_INDICES) / len(RIGHT_CLAW_INDICES)
                overall_force = (left_force + right_force) / 2

                if current_state == GripperState.CLOSING:
                    pid_output = pid.update(overall_force)
                    servo1_angle += pid_output * SERVO_STEP_SIZE
                    servo1_angle = max(SERVO_OPEN_ANGLE, min(SERVO_MAX_CLOSE_ANGLE, servo1_angle))
                    
                    if left_force > MIN_FORCE_PER_CLAW and right_force > MIN_FORCE_PER_CLAW:
                        current_state = GripperState.HOLDING
                        print(f"[State Change] Successful balanced grasp achieved. State: {current_state.name}")

                elif current_state == GripperState.RELEASING:
                    servo1_angle = SERVO_OPEN_ANGLE
                    current_state = GripperState.OPEN
                    print(f"[State Change] Release complete. State: {current_state.name}")
                
                # --- FIX 2: Using the correct queue name ---
                outgoing_queue.put(f"SERVO1:{int(servo1_angle)}")

            except ValueError:
                continue

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Controller CRITICAL ERROR] An unexpected error occurred: {e}")
            break
    
    print("[Controller] Processing thread has been shut down.")

# --- FIX 3: Rewritten this entire function to be more robust and explicitly use arguments ---
def websocket_client_thread(out_q, in_q, stop_event):
    """Handles all websocket communication, using queues passed as arguments."""
    
    async def sender(websocket):
        while not stop_event.is_set():
            try:
                command = out_q.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                await asyncio.sleep(0.02)
            except websockets.exceptions.ConnectionClosed:
                print("[Controller Network] Sender: Connection closed.")
                break

    async def receiver(websocket):
        while not stop_event.is_set():
            try:
                message = await websocket.recv()
                in_q.put(message)
            except websockets.exceptions.ConnectionClosed:
                print("[Controller Network] Receiver: Connection closed.")
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
    # --- FIX 4: Pass the queues and event as arguments to the thread ---
    client_thread = threading.Thread(
        target=websocket_client_thread,
        args=(outgoing_queue, incoming_queue, shutdown_event),
        daemon=True
    )

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
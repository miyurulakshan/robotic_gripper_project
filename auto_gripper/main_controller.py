# filename: main_controller.py
import threading
import queue
import asyncio
import time
import websockets
from enum import Enum
import numpy as np
from kalman_filter import MultivariateKalmanFilter
from pid_controller import PIDController

# --- SYSTEM STATE ---
class SystemState(Enum):
    IDENTIFYING = 1
    READY_TO_GRASP = 2
    EXECUTING_GRASP = 3
    RELEASING = 4

class GripperState(Enum):
    OPEN = 1
    CLOSING = 2
    HOLDING = 3

# --- CONFIGURATION & TUNING ---
TARGET_FORCES = {
    "paper_box": 300,
    "power_bank": 1700,
    "egg": 600,
    "default": 700
}
OVERALL_TARGET_FORCE = TARGET_FORCES["default"]

WEBSOCKET_URI = "ws://localhost:8765"
ACCEPTABLE_ERROR_MARGIN = 50
MAX_CLAW_FORCE = 2000
MIN_FORCE_PER_CLAW = 200
KP = 0.0005
KI = 0.0000003
KD = 0.000006
SERVO_OPEN_PULSE = 800
SERVO_MAX_CLOSE_PULSE = 2100
SERVO_STEP_SIZE = 20.0
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

Q_left = np.array([[0.09]])
R_left = np.diag([3.1623, 3.1623, 3.1623, 3.1623])
Q_right = np.array([[0.09]])
R_right = np.diag([3.9811, 3.9811, 3.9811, 10.6606])

incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()


def data_processing_thread():
    current_system_state = SystemState.IDENTIFYING
    current_gripper_state = GripperState.OPEN
    locked_object = None
    global OVERALL_TARGET_FORCE

    A = np.array([[1]])
    H = np.array([[1], [1], [1], [1]])
    x_hat_initial = np.array([[0]])
    P_initial = np.array([[100]])
    kf_left_claw = MultivariateKalmanFilter(A, H, Q_left, R_left, x_hat_initial, P_initial)
    kf_right_claw = MultivariateKalmanFilter(A, H, Q_right, R_right, x_hat_initial, P_initial)

    pid = PIDController(Kp=KP, Ki=KI, Kd=KD, setpoint=OVERALL_TARGET_FORCE)
    servo_pulse = float(SERVO_OPEN_PULSE)
    outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
    outgoing_queue.put("STATUS:IDENTIFYING")
    
    # MODIFICATION: Set servo 2 to its initial identification position.
    outgoing_queue.put("PULSE2:2300")

    print("[Controller] System initialized in IDENTIFYING mode.")

    while not shutdown_event.is_set():
        try:
            raw_packet = incoming_queue.get(timeout=0.1)
            data_packet = raw_packet.strip()

            # --- Handle State-Specific Messages (OBJECT, CMD) ---
            if current_system_state == SystemState.IDENTIFYING and data_packet.startswith("OBJECT:"):
                detected = data_packet.split(':')[1]
                # --- THIS IS THE MODIFIED LOGIC ---
                # Lock on the first valid detection.
                if detected != "None":
                    locked_object = detected.lower()
                    OVERALL_TARGET_FORCE = TARGET_FORCES.get(locked_object, TARGET_FORCES["default"])
                    pid.set_setpoint(OVERALL_TARGET_FORCE)
                    current_system_state = SystemState.READY_TO_GRASP
                    
                    # MODIFICATION: Move servo 2 to the grasping position.
                    outgoing_queue.put("PULSE2:1600")
                    
                    print(f"[Controller] Object locked: {locked_object}. Target force set to: {OVERALL_TARGET_FORCE}")
                    outgoing_queue.put(f"STATUS:LOCKED:{locked_object.upper()}")

            elif current_system_state == SystemState.READY_TO_GRASP and data_packet.startswith("CMD:"):
                command = data_packet.split(':')[1]
                if command == "GRASP":
                    current_system_state = SystemState.EXECUTING_GRASP
                    current_gripper_state = GripperState.CLOSING
                    pid.reset()
                elif command == "RESET":
                    current_system_state = SystemState.RELEASING

            elif current_system_state == SystemState.EXECUTING_GRASP and data_packet.startswith("CMD:"):
                command = data_packet.split(':')[1]
                if command in ("RELEASE", "EMERGENCY", "RESET"):
                    current_system_state = SystemState.RELEASING

            # --- Always Process Sensor Data ---
            try:
                all_readings = [int(val) for val in data_packet.split(',')]
                if len(all_readings) == 10:
                    left_raw_readings = [all_readings[i] for i in LEFT_CLAW_INDICES]
                    right_raw_readings = [all_readings[i] for i in RIGHT_CLAW_INDICES]
                    left_z = np.array([[r] for r in left_raw_readings])
                    right_z = np.array([[r] for r in right_raw_readings])

                    left_force = kf_left_claw.update(left_z)[0, 0]
                    right_force = kf_right_claw.update(right_z)[0, 0]
                    overall_force = max(left_force, right_force)

                    data_to_send = f"DATA:{np.mean(left_raw_readings)},{left_force},{np.mean(right_raw_readings)},{right_force},{overall_force}"
                    outgoing_queue.put(data_to_send)

                    if current_system_state == SystemState.EXECUTING_GRASP and current_gripper_state == GripperState.CLOSING:
                        pid_output = pid.update(overall_force)
                        servo_pulse += pid_output * SERVO_STEP_SIZE
                        servo_pulse = max(SERVO_OPEN_PULSE, min(SERVO_MAX_CLOSE_PULSE, servo_pulse))
                        outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")

                        error = OVERALL_TARGET_FORCE - overall_force
                        if abs(error) < ACCEPTABLE_ERROR_MARGIN and left_force > MIN_FORCE_PER_CLAW and right_force > MIN_FORCE_PER_CLAW:
                            current_gripper_state = GripperState.HOLDING
                            print(f"[State Change] Target force of {OVERALL_TARGET_FORCE} achieved. State: HOLDING")

            except (ValueError, IndexError):
                pass

            # --- Handle Releasing State Action ---
            if current_system_state == SystemState.RELEASING:
                servo_pulse = float(SERVO_OPEN_PULSE)
                outgoing_queue.put(f"PULSE1:{int(servo_pulse)}")
                
                # MODIFICATION: Wait 1 second, then move servo 2 to its home position.
                time.sleep(1)
                outgoing_queue.put("PULSE2:2300")

                current_system_state = SystemState.IDENTIFYING
                current_gripper_state = GripperState.OPEN
                locked_object = None
                print("[Controller] Release complete. Returning to identification mode.")
                outgoing_queue.put("STATUS:IDENTIFYING")

        except queue.Empty:
            continue
    print("[Controller] Processing thread has been shut down.")


def websocket_client_thread(out_q, in_q, stop_event):
    async def sender(websocket):
        while not stop_event.is_set():
            try:
                command = out_q.get_nowait()
                await websocket.send(command)
            except queue.Empty:
                await asyncio.sleep(0.02)
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
    client_thread.start()
    processing_thread.start()
    try:
        while processing_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown_event.set()
    processing_thread.join()
    print("[Main] Application has shut down.")
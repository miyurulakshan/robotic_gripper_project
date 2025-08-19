# filename: kalman_tuner_logger.py
# This script performs a "hold test" specifically for Kalman filter tuning.
import asyncio
import websockets
import time
import queue
import threading
import numpy as np
from kalman_filter import MultivariateKalmanFilter

# --- CONFIGURATION ---
WEBSOCKET_URI = "ws://localhost:8765"
LOG_FILE_NAME = "gripper_kalman_log_3_sponge.csv" # Use a new file name

# --- TEST PARAMETERS ---
HOLD_TEST_TARGET_FORCE = 1500  # The force level to reach and holdSSSS
HOLD_DURATION_SECONDS = 15     # How long to hold the position
HOLD_TEST_STEP_SIZE = 10       # How fast to approach the target
SERVO_MAX_CLOSE_PULSE = 2000   # Safety limit

# --- SENSOR CONFIG ---
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# --- THREADING AND QUEUES ---
incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

def hold_test_controller_thread():
    """
    Actively controls the gripper to reach a target force, hold it,
    and then release, logging data throughout.
    """
    print("\n[Controller] This script will perform a HOLD TEST for Kalman filter tuning.")
    input("[Controller] Place a soft object in the gripper and press Enter to begin...")
    print("[Controller] Starting test...")

    # --- KALMAN FILTER SETUP ---
    A = np.array([[1]])
    H = np.array([[1], [1], [1], [1]])
    x_hat_initial = np.array([[0]])
    P_initial = np.array([[100]])
    Q = np.array([[0.0001]])
    R = np.diag([0.5, 0.05, 0.05, 0.5])
    kf_left_claw = MultivariateKalmanFilter(A, H, Q, R, x_hat_initial, P_initial)
    kf_right_claw = MultivariateKalmanFilter(A, H, Q, R, x_hat_initial, P_initial)
    is_first_reading = True
    
    start_time = time.time()
    servo_pulse = 0
    test_phase = "APPROACH" # Can be APPROACH, HOLD, or DONE

    with open(LOG_FILE_NAME, "w") as log_file:
        log_file.write("Time,ServoPulse,MeasuredForce,FSR1,FSR2,FSR3,FSR4,FSR5,FSR6,FSR7,FSR8\n")
        
        hold_start_time = 0

        while test_phase != "DONE" and not shutdown_event.is_set():
            # --- Get the latest sensor reading ---
            overall_force = 0
            fsr_values = [0] * 8
            try:
                raw_packet = ""
                while not incoming_queue.empty():
                    raw_packet = incoming_queue.get_nowait()
                
                all_readings = [int(val) for val in raw_packet.strip().split(',')]
                if len(all_readings) == 10:
                    fsr_values = all_readings[2:]
                    left_z = np.array([[all_readings[i]] for i in LEFT_CLAW_INDICES])
                    right_z = np.array([[all_readings[i]] for i in RIGHT_CLAW_INDICES])
                    if is_first_reading:
                        # Initialize filter
                        left_raw_avg = np.mean([all_readings[i] for i in LEFT_CLAW_INDICES])
                        right_raw_avg = np.mean([all_readings[i] for i in RIGHT_CLAW_INDICES])
                        kf_left_claw.x_hat = np.array([[left_raw_avg]])
                        kf_right_claw.x_hat = np.array([[right_raw_avg]])
                        is_first_reading = False
                    # Update filter
                    left_force = kf_left_claw.update(left_z)[0, 0]
                    right_force = kf_right_claw.update(right_z)[0, 0]
                    overall_force = max(left_force, right_force)
            except (queue.Empty, ValueError, IndexError):
                pass # Use default 0 values if no data

            # --- Log the current state ---
            current_time = time.time() - start_time
            fsr_values_str = ",".join(map(str, fsr_values))
            log_file.write(f"{current_time},{servo_pulse},{overall_force},{fsr_values_str}\n")
            print(f"Phase: {test_phase}, Time: {current_time:.2f}s, Pulse: {servo_pulse}, Force: {overall_force:.2f}")

            # --- State Machine Logic ---
            if test_phase == "APPROACH":
                if overall_force >= HOLD_TEST_TARGET_FORCE or servo_pulse >= SERVO_MAX_CLOSE_PULSE:
                    print(f"[Controller] Target force reached. Switching to HOLD phase for {HOLD_DURATION_SECONDS} seconds.")
                    test_phase = "HOLD"
                    hold_start_time = time.time()
                else:
                    servo_pulse += HOLD_TEST_STEP_SIZE
                    outgoing_queue.put(f"PULSE1:{servo_pulse}")

            elif test_phase == "HOLD":
                # Do nothing, just keep logging data at the fixed servo position
                if time.time() - hold_start_time > HOLD_DURATION_SECONDS:
                    test_phase = "DONE"

            time.sleep(0.1) # Loop delay

    # Test finished, fully open the gripper
    print("[Controller] Test complete. Opening gripper.")
    outgoing_queue.put("PULSE1:0")
    time.sleep(1)
    shutdown_event.set()


async def websocket_client_thread():
    print(f"[Network] Attempting to connect to {WEBSOCKET_URI}")
    try:
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            print("[Network] Connected to server.")
            async def sender(ws):
                while not shutdown_event.is_set():
                    try:
                        command = outgoing_queue.get_nowait()
                        await ws.send(command)
                    except queue.Empty:
                        await asyncio.sleep(0.02)
            async def receiver(ws):
                while not shutdown_event.is_set():
                    try:
                        message = await ws.recv()
                        if not message.startswith("DATA:") and not message.startswith("PULSE1:"):
                             incoming_queue.put(message)
                    except websockets.exceptions.ConnectionClosed:
                        break
            await asyncio.gather(sender(websocket), receiver(websocket))
    except (ConnectionRefusedError, OSError):
        print("[Network] Connection failed. Is server.py running?")
    finally:
        shutdown_event.set()

if __name__ == "__main__":
    controller_thread = threading.Thread(target=hold_test_controller_thread)
    controller_thread.start()
    try:
        asyncio.run(websocket_client_thread())
    except KeyboardInterrupt:
        print("\n[Main] Shutdown signal received.")
    shutdown_event.set()
    controller_thread.join()
    print("[Main] Data logger has shut down successfully.")

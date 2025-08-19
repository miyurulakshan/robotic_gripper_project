# filename: data_logger.py
# This script is now an active test controller for system identification.
import asyncio
import websockets
import time
import queue
import threading
import numpy as np
from kalman_filter import MultivariateKalmanFilter

# --- CONFIGURATION ---
WEBSOCKET_URI = "ws://localhost:8765"
LOG_FILE_NAME = "gripper_log.csv"

# --- TEST PARAMETERS ---
# How much to increment the servo pulse at each step
LOGGING_STEP_SIZE = 1
# How long to wait (in seconds) at each step for the system to settle
LOGGING_DELAY = 0.05
# The safety force limit. If this is reached, the test stops.
LOGGING_MAX_FORCE = 2000
# The maximum pulse width for the servo
SERVO_MAX_CLOSE_PULSE = 2100

# --- SENSOR CONFIG (Copied from main_controller.py) ---
LEFT_CLAW_INDICES = [2, 3, 4, 5]
RIGHT_CLAW_INDICES = [6, 7, 8, 9]

# --- THREADING AND QUEUES ---
incoming_queue = queue.Queue()
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

def logging_controller_thread():
    """
    This thread now actively controls the gripper to perform a step test
    and logs the resulting data.
    """
    print("\n[Controller] Place a soft object in the gripper.")
    input("[Controller] Press Enter to begin the data logging process...")
    print("[Controller] Starting test...")

    # --- KALMAN FILTER SETUP (Copied from main_controller.py) ---
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
    servo_pulse = 1000

    with open(LOG_FILE_NAME, "w") as log_file:
        # --- MODIFIED: Added columns for all 8 FSR sensors ---
        log_file.write("Time,ServoPulse,MeasuredForce,FSR1,FSR2,FSR3,FSR4,FSR5,FSR6,FSR7,FSR8\n")
        
        while servo_pulse <= SERVO_MAX_CLOSE_PULSE and not shutdown_event.is_set():
            # 1. Send command to move the servo
            outgoing_queue.put(f"PULSE1:{servo_pulse}")
            
            # 2. Wait for the system to settle
            time.sleep(LOGGING_DELAY)
            
            # 3. Process the most recent sensor reading
            overall_force = 0
            # --- MODIFIED: Default fsr_values to a list of 8 zeros ---
            fsr_values = [0] * 8
            
            try:
                # Get the latest message, clearing out any old ones
                raw_packet = ""
                while not incoming_queue.empty():
                    raw_packet = incoming_queue.get_nowait()
                
                all_readings = [int(val) for val in raw_packet.strip().split(',')]
                
                if len(all_readings) == 10:
                    # --- MODIFIED: Capture the 8 raw FSR values ---
                    # The FSR readings start from the 3rd element (index 2)
                    fsr_values = all_readings[2:]

                    left_z = np.array([[all_readings[i]] for i in LEFT_CLAW_INDICES])
                    right_z = np.array([[all_readings[i]] for i in RIGHT_CLAW_INDICES])

                    if is_first_reading:
                        left_raw_avg = np.mean([all_readings[i] for i in LEFT_CLAW_INDICES])
                        right_raw_avg = np.mean([all_readings[i] for i in RIGHT_CLAW_INDICES])
                        kf_left_claw.x_hat = np.array([[left_raw_avg]])
                        kf_right_claw.x_hat = np.array([[right_raw_avg]])
                        is_first_reading = False

                    left_force = kf_left_claw.update(left_z)[0, 0]
                    right_force = kf_right_claw.update(right_z)[0, 0]
                    overall_force = max(left_force, right_force)

            except (queue.Empty, ValueError, IndexError):
                # If no data is available or it's malformed, the defaults (0) will be used
                pass

            # 4. Log the data point
            current_time = time.time() - start_time
            # --- MODIFIED: Convert list of FSR values to a comma-separated string ---
            fsr_values_str = ",".join(map(str, fsr_values))
            log_file.write(f"{current_time},{servo_pulse},{overall_force},{fsr_values_str}\n")
            print(f"Time: {current_time:.2f}s, Pulse: {servo_pulse}, Force: {overall_force:.2f}")

            # 5. Check safety limit
            if overall_force > LOGGING_MAX_FORCE:
                print(f"[Controller] SAFETY LIMIT REACHED ({LOGGING_MAX_FORCE}). Aborting test.")
                break
            
            # 6. Increment for next step
            servo_pulse += LOGGING_STEP_SIZE

    # Test finished, fully open the gripper
    print("[Controller] Test complete. Opening gripper.")
    outgoing_queue.put("PULSE1:0")
    time.sleep(1) # Give it time to send
    shutdown_event.set()


async def websocket_client_thread():
    """
    Connects to the server and handles both sending and receiving messages.
    """
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
                        # Only care about raw data from ESP32, not DATA: packets
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
    controller_thread = threading.Thread(target=logging_controller_thread)
    controller_thread.start()

    try:
        asyncio.run(websocket_client_thread())
    except KeyboardInterrupt:
        print("\n[Main] Shutdown signal received.")
    
    shutdown_event.set()
    controller_thread.join()
    print("[Main] Data logger has shut down successfully.")

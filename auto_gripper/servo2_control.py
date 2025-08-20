# filename: servo2_control.py
import asyncio
import websockets

# --- CONFIGURATION ---
WEBSOCKET_URI = "ws://192.168.1.13:8765"  # Must match the IP in your ESP32 code

# ★★★ DEFINE YOUR SERVO MOVEMENT SEQUENCE HERE ★★★
# The script will move the servo to each of these pulse values in order.
MOVE_SEQUENCE = [1200, 2000, 1600,2300]

# ★★★ SET THE SPEED HERE ★★★
# This is the delay in seconds between each small step.
# A larger number means SLOWER movement. Good values are between 0.01 and 0.05.
MOVE_DELAY = 0.01

# This is the size of each small step in microseconds.
# A smaller number means SMOOTHER movement.
STEP_SIZE = 20

async def perform_servo_sequence():
    """
    Connects to the server and moves the servo through a predefined sequence
    at a controlled speed.
    """
    print("--- Starting Servo Sequence ---")
    try:
        # Establish a single, persistent connection for the whole sequence
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            print(f"[Client] Connected to server at {WEBSOCKET_URI}")
            
            # Assume the servo starts at a neutral position
            current_pulse = 1500
            
            # Go through each target position in the sequence
            for target_pulse in MOVE_SEQUENCE:
                print(f"Moving from {current_pulse} to {target_pulse}...")

                # Determine direction and create the range of steps
                if target_pulse > current_pulse:
                    # Move forwards
                    pulse_range = range(current_pulse, target_pulse + 1, STEP_SIZE)
                else:
                    # Move backwards
                    pulse_range = range(current_pulse, target_pulse - 1, -STEP_SIZE)

                # Send each small step to the ESP32
                for pulse in pulse_range:
                    command = f"PULSE2:{pulse}"
                    await websocket.send(command)
                    await asyncio.sleep(MOVE_DELAY) # This delay controls the speed

                # Update the current position for the next move in the sequence
                current_pulse = target_pulse
                print(f"Move to {target_pulse} complete. Pausing before next move...")
                await asyncio.sleep(1.0) # Pause for 1 second at the target position

    except ConnectionRefusedError:
        print(f"[Client] Connection refused. Is server.py running?")
    except Exception as e:
        print(f"[Client] An error occurred: {e}")
        
    print("--- Servo Sequence Finished ---")


if __name__ == "__main__":
    # Run the entire sequence in one go
    asyncio.run(perform_servo_sequence())
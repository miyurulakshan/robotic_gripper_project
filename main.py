# File: main.py
# OPTIMIZED VERSION to reduce read delay.

import serial
import time
import sys

# Import our custom modules
from fsr_visualization import FSRVisualizer
from gripper_control import GripperController
from object_detection import ObjectDetector

# --- CONFIGURATION ---
# You MUST change these values to match your setup

# Serial port for the Arduino Mega (e.g., 'COM3' on Windows, '/dev/ttyACM0' on Linux)
ARDUINO_PORT = 'COM5' # Using the port you confirmed
BAUD_RATE = 115200

# URL of the ESP32-CAM video stream. Get this from the Arduino Serial Monitor.
ESP32_CAM_URL = 'http://192.168.1.104/stream' # <-- CHANGE THIS IF NEEDED

# Control loop settings
PRESSURE_LIMIT = 400 # The FSR value (0-1023) that triggers a release. Adjust this.

def main():
    """
    The main function to run the entire application.
    """
    print("--- Robotic Gripper Control System ---")

    # --- Initialize Hardware Communication ---
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for the serial connection to establish
        print(f"Successfully connected to Arduino on {ARDUINO_PORT}")
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {ARDUINO_PORT}.")
        print(f"Please check the port name and ensure the Arduino is connected. Details: {e}")
        sys.exit(1) # Exit the program if we can't connect

    # --- Initialize Modules ---
    visualizer = FSRVisualizer()
    controller = GripperController(pressure_limit=PRESSURE_LIMIT)
    #detector = ObjectDetector(stream_url=ESP32_CAM_URL)
    #detector.start() # Start object detection in the background

    # --- Main Control Loop ---
    running = True
    try:
        # Example: Command the gripper to close to 90 degrees to start
        print("Commanding gripper to close to 90 degrees.")
        controller.set_target_angle(90)

        while running:
            # 1. Read FSR data from Arduino
            fsr_data = []
            if arduino.in_waiting > 0:
                # *** SPEED OPTIMIZATION: Clear any old data in the buffer ***
                arduino.reset_input_buffer() 
                try:
                    line = arduino.readline().decode('utf-8').rstrip()
                    # Ensure the line is not empty before processing
                    if line:
                        fsr_data = [int(val) for val in line.split(',')]
                except (ValueError, UnicodeDecodeError) as e:
                    # This can happen if the buffer is cleared mid-transmission. It's safe to ignore.
                    # print(f"Warning: Could not parse FSR data '{line}'. Error: {e}. Skipping cycle.")
                    continue
            
            if len(fsr_data) == 8:
                # 2. Update the visualization
                running = visualizer.update(fsr_data)

                # 3. Run the control logic
                new_angle = controller.control_step(fsr_data)

                # 4. Send the new servo angle to the Arduino
                arduino.write(bytes([new_angle]))
                # Optional: The print statement itself adds a small delay. Comment it out for max speed.
                # print(f"FSR: {fsr_data} -> Servo Angle: {new_angle}")

            # *** SPEED OPTIMIZATION: Removed time.sleep() ***
            # The loop will now run as fast as possible, keeping up with the Arduino.
            
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        # --- Cleanup ---
        print("Shutting down...")
        # Ensure arduino object exists and port is open before trying to write to it
        if 'arduino' in locals() and arduino.is_open:
            arduino.write(bytes([0])) # Command servo to fully open
            arduino.close()
        visualizer.close()
        detector.stop()
        print("Cleanup complete. Exiting.")

if __name__ == '__main__':
    main()

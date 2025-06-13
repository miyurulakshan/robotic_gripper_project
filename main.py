# File: main.py
# This version passes the real-time feedback to the controller for synced logic.

import serial
import time
import sys
import pygame

# Import the classes for our unified window and the controller
from interactive_gripper_visualization import InteractiveGripperVisualizer
from gripper_control import GripperController 

# --- CONFIGURATION ---
ARDUINO_PORT = 'COM5'
BAUD_RATE = 115200

def main():
    """The main function to initialize and run the fully synchronized system."""
    print("--- Robotic Gripper Control System: Fully Synchronized ---")

    # --- Initialize Pygame ---
    pygame.init()
    pygame.font.init()

    # --- Initialize Hardware Communication ---
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        print(f"Successfully connected to Arduino on {ARDUINO_PORT}")
    except serial.SerialException as e:
        print(f"FATAL: Could not open serial port {ARDUINO_PORT}. Details: {e}")
        sys.exit(1)

    # --- Create the single, unified window and the controller ---
    visualizer = InteractiveGripperVisualizer()
    controller = GripperController()

    # --- Data Persistence Variables ---
    last_known_angle = 0
    last_known_fsr_data = [0] * 8

    # --- Main Application Loop ---
    running = True
    try:
        while running:
            # 1. Handle Events for the window
            command = visualizer.check_events(pygame.event.get())
            if command == "quit":
                running = False
                continue
            if command:
                controller.handle_command(command)

            # 2. Read and Parse the feedback packet from Arduino
            if arduino.in_waiting > 0:
                try:
                    arduino.reset_input_buffer()
                    line = arduino.readline().decode('utf-8').rstrip()
                    if line:
                        parsed_data = [int(val) for val in line.split(',')]
                        if len(parsed_data) == 9:
                            last_known_angle = parsed_data[0]
                            last_known_fsr_data = parsed_data[1:]
                except (ValueError, UnicodeDecodeError):
                    pass
            
            # 3. FIX: Run control logic, giving it the REAL-TIME angle feedback
            target_angle = controller.update(last_known_fsr_data, last_known_angle)

            # 4. Send the new TARGET angle command to the Arduino
            arduino.write(bytes([target_angle]))

            # 5. Update the visualization using the REAL-TIME FEEDBACK
            visualizer.update(last_known_angle, controller.state.name, last_known_fsr_data, controller.object_detected)
            
            # 6. Refresh the entire display once
            pygame.display.update()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        print("Shutting down...")
        if 'arduino' in locals() and arduino.is_open:
            arduino.write(bytes([0]))
            time.sleep(0.5)
            arduino.close()
        pygame.quit()
        print("Cleanup complete. Exiting.")

if __name__ == '__main__':
    main()

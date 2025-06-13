# File: main.py
# This version uses the correct, stable, and fast closed-loop architecture.

import serial
import time
import sys
import pygame
import socket

from interactive_gripper_visualization import InteractiveGripperVisualizer
from gripper_control import GripperController 

# --- CONFIGURATION ---
ARDUINO_PORT = 'COM5'
BAUD_RATE = 115200
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

def main():
    print("--- Robotic Gripper Control System: Fully Synchronized ---")
    pygame.init()
    pygame.font.init()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        print(f"Successfully connected to Arduino on {ARDUINO_PORT}")
        print(f"Broadcasting FSR data to {UDP_IP}:{UDP_PORT}. Run data_logger.py to view.")
    except serial.SerialException as e:
        print(f"FATAL: Could not open serial port {ARDUINO_PORT}. Details: {e}")
        sys.exit(1)

    visualizer = InteractiveGripperVisualizer()
    controller = GripperController()

    last_known_angle = 0
    last_known_fsr_data = [0] * 8
    serial_buffer = ""

    running = True
    try:
        # --- STABLE & FAST CLOSED-LOOP ARCHITECTURE ---
        while running:
            # 1. Read the latest state from the hardware
            if arduino.in_waiting > 0:
                serial_buffer += arduino.read(arduino.in_waiting).decode('utf-8', errors='ignore')

            start_index = serial_buffer.find('S')
            end_index = serial_buffer.find('E')

            if start_index != -1 and end_index != -1 and start_index < end_index:
                packet_str = serial_buffer[start_index + 1 : end_index]
                serial_buffer = serial_buffer[end_index + 1:]
                try:
                    parsed_data = [int(val) for val in packet_str.split(',')]
                    if len(parsed_data) == 9:
                        last_known_angle = parsed_data[0]
                        last_known_fsr_data = parsed_data[1:]
                        sock.sendto(packet_str.encode('utf-8'), (UDP_IP, UDP_PORT))
                except (ValueError):
                    pass
            
            # 2. Decide on the next action based on user input and the real state
            command = visualizer.check_events(pygame.event.get())
            if command == "quit": running = False; continue
            if command: controller.handle_command(command)
            
            target_angle = controller.update(last_known_fsr_data, last_known_angle)

            # 3. Act by sending the new command to the hardware
            arduino.write(bytes([target_angle]))

            # 4. Visualize the real state that was read in step 1
            visualizer.update(last_known_angle, controller.state.name, last_known_fsr_data, controller.object_detected)
            pygame.display.update()
            
            # Minimal delay to keep the loop fast without maxing out the CPU
            time.sleep(0.002)


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

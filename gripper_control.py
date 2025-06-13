# File: gripper_control.py
# This version has more robust grab detection logic.

from enum import Enum, auto

class GripperState(Enum):
    IDLE = auto()
    GRABBING = auto()
    HOLDING = auto()
    RELEASING = auto()
    FAILED_GRAB = auto()
    EMERGENCY_RELEASE = auto()

class GripperController:
    """
    Implements a state machine with more robust grab detection.
    """
    def __init__(self):
        self.GRAB_THRESHOLD = 300
        self.EMERGENCY_PRESSURE = 600
        self.GRAB_SPEED = 0.1
        self.RELEASE_SPEED = 2

        self.state = GripperState.IDLE
        self.target_angle = 0.0
        self.object_detected = False

    def _check_emergency(self, fsr_values):
        if any(v > self.EMERGENCY_PRESSURE for v in fsr_values):
            self.state = GripperState.EMERGENCY_RELEASE
            print(f"!!! EMERGENCY: Pressure > {self.EMERGENCY_PRESSURE}. Releasing!")
            return True
        return False

    def _check_grab_success(self, fsr_values, actual_angle):
        """
        Checks if the grip is successful.
        A grip is now considered successful if ANY 2 sensors on a single jaw
        are over the threshold.
        """
        left_jaw = fsr_values[0:4]
        right_jaw = fsr_values[4:8]

        for jaw in [left_jaw, right_jaw]:
            # Count how many sensors on this jaw are being pressed
            pressed_sensor_count = 0
            for sensor_value in jaw:
                if sensor_value > self.GRAB_THRESHOLD:
                    pressed_sensor_count += 1
            
            # If 2 or more sensors on this jaw are pressed, we have a successful grab
            if pressed_sensor_count >= 2:
                self.state = GripperState.HOLDING
                self.object_detected = True
                self.target_angle = actual_angle 
                print(f"Object detected and held at angle {int(self.target_angle)}°")
                return True
            
        return False # Return false if no jaw had at least 2 pressed sensors

    def handle_command(self, command):
        if command == "grab" and self.state in [GripperState.IDLE, GripperState.FAILED_GRAB]:
            self.state = GripperState.GRABBING
            self.target_angle = 0
            self.object_detected = False
            print("Command: GRAB. Starting grab sequence.")
        
        elif command == "release" and self.state in [GripperState.HOLDING]:
            self.state = GripperState.RELEASING
            print("Command: RELEASE. Releasing object.")

        elif command == "emergency":
            self.state = GripperState.EMERGENCY_RELEASE
            print("Command: EMERGENCY. Releasing immediately.")
            
    def update(self, fsr_values, actual_angle):
        """
        Runs the state machine, using the actual_angle for decisions.
        """
        if not fsr_values:
            return int(self.target_angle)

        if self.state not in [GripperState.EMERGENCY_RELEASE, GripperState.RELEASING]:
            if self._check_emergency(fsr_values):
                pass

        if self.state == GripperState.GRABBING:
            if not self._check_grab_success(fsr_values, actual_angle):
                self.target_angle += self.GRAB_SPEED
                if actual_angle >= 99:
                    self.state = GripperState.FAILED_GRAB
                    print("Grab failed: Physical gripper reached 100 degrees with no object.")
        
        elif self.state == GripperState.HOLDING:
            pass

        elif self.state in [GripperState.RELEASING, GripperState.EMERGENCY_RELEASE, GripperState.FAILED_GRAB]:
            self.target_angle -= self.RELEASE_SPEED
            if actual_angle <= 1:
                self.state = GripperState.IDLE
                self.object_detected = False
                print("Gripper is now physically open and IDLE.")

        self.target_angle = max(0, min(100, self.target_angle))
        return int(self.target_angle)

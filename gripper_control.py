# File: gripper_control.py
# This version has more robust grab detection logic AND dynamic grab speed.

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
    Implements a state machine with robust grab detection and dynamic grab speed.
    """
    def __init__(self):
        self.GRAB_THRESHOLD = 200 # The pressure at which a grab is considered successful
        self.EMERGENCY_PRESSURE = 700 # The pressure for an emergency release
        self.RELEASE_SPEED = 2 # The speed for releasing the object
        
        # --- NEW: Parameters for Dynamic Grab Speed ---
        self.MAX_GRAB_SPEED = 0.2         # Speed when no force is detected
        self.MIN_GRAB_SPEED = 0.001        # Speed when force is high (just before grabbing)
        self.FORCE_SENSITIVITY_START = 50 # FSR value at which to start slowing down
        self.FORCE_SENSITIVITY_END = 280  # FSR value at which speed is at its minimum
        # --- END NEW ---

        self.state = GripperState.IDLE # The initial state is IDLE
        self.target_angle = 0.0 # The initial target angle is 0.0
        self.object_detected = False # Initially, no object is detected

    def _check_emergency(self, fsr_values):
        if any(v > self.EMERGENCY_PRESSURE for v in fsr_values): # Checks if any FSR value exceeds the emergency pressure
            self.state = GripperState.EMERGENCY_RELEASE # Sets the state to EMERGENCY_RELEASE
            print(f"!!! EMERGENCY: Pressure > {self.EMERGENCY_PRESSURE}. Releasing!")
            return True
        return False

    def _check_grab_success(self, fsr_values, actual_angle):
        """
        Checks if the grip is successful.
        A grip is now considered successful if ANY 2 sensors on a single jaw
        are over the threshold.
        """
        left_jaw = fsr_values[0:4] # The first four FSR values belong to the left jaw
        right_jaw = fsr_values[4:8] # The next four FSR values belong to the right jaw

        for jaw in [left_jaw, right_jaw]:
            pressed_sensor_count = 0
            for sensor_value in jaw:
                if sensor_value > self.GRAB_THRESHOLD: # Counts sensors with a value greater than the grab threshold
                    pressed_sensor_count += 1
            
            if pressed_sensor_count >= 2: # A successful grab requires at least 2 sensors on a jaw to be pressed
                self.state = GripperState.HOLDING # The state is set to HOLDING on a successful grab
                self.object_detected = True # object_detected is set to True
                self.target_angle = actual_angle # The target angle is set to the current actual angle to hold the position
                print(f"Object detected and held at angle {int(self.target_angle)}°")
                return True
            
        return False

    def handle_command(self, command):
        if command == "grab" and self.state in [GripperState.IDLE, GripperState.FAILED_GRAB]: # A "grab" command starts the grab sequence
            self.state = GripperState.GRABBING
            self.target_angle = 0
            self.object_detected = False
            print("Command: GRAB. Starting grab sequence.")
        
        elif command == "release" and self.state in [GripperState.HOLDING]: # A "release" command starts the release sequence
            self.state = GripperState.RELEASING
            print("Command: RELEASE. Releasing object.")

        elif command == "emergency": # An "emergency" command starts the emergency release
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
                
                # --- MODIFIED: Dynamic Speed Calculation ---
                max_force = max(fsr_values) if fsr_values else 0
                
                dynamic_speed = self.MAX_GRAB_SPEED

                if max_force > self.FORCE_SENSITIVITY_START:
                    # Calculate how far the force is into the sensitivity range (0.0 to 1.0)
                    force_progress = (max_force - self.FORCE_SENSITIVITY_START) / (self.FORCE_SENSITIVITY_END - self.FORCE_SENSITIVITY_START)
                    clamped_progress = max(0.0, min(1.0, force_progress))
                    
                    # Linearly interpolate the speed based on the force progress
                    # As progress goes from 0 to 1, speed goes from MAX to MIN
                    dynamic_speed = self.MAX_GRAB_SPEED - (self.MAX_GRAB_SPEED - self.MIN_GRAB_SPEED) * clamped_progress
                
                self.target_angle += dynamic_speed
                # --- END MODIFIED ---

                if actual_angle >= 99: # Checks if the gripper has reached its physical limit
                    self.state = GripperState.FAILED_GRAB
                    print("Grab failed: Physical gripper reached 100 degrees with no object.")
        
        elif self.state == GripperState.HOLDING:
            pass

        elif self.state in [GripperState.RELEASING, GripperState.EMERGENCY_RELEASE, GripperState.FAILED_GRAB]:
            self.target_angle -= self.RELEASE_SPEED # The target angle is decreased during release
            if actual_angle <= 1: # When the gripper is fully open, the state becomes IDLE
                self.state = GripperState.IDLE
                self.object_detected = False
                print("Gripper is now physically open and IDLE.")

        self.target_angle = max(0, min(100, self.target_angle)) # The target angle is constrained between 0 and 100
        return int(self.target_angle)
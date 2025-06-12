# File: gripper_control.py

class GripperController:
    """
    Implements the force control loop for the gripper.
    """
    def __init__(self, pressure_limit, initial_angle=0, step=5):
        """
        Initializes the controller.
        - pressure_limit: The FSR reading above which the gripper should release.
        - initial_angle: The starting angle of the servo (0-100).
        - step: How many degrees to release the gripper by when pressure is too high.
        """
        self.pressure_limit = pressure_limit
        self.current_angle = initial_angle
        self.release_step = step
        self.is_gripping = False # State to control gripper action

    def set_target_angle(self, angle):
        """
        Allows manually setting a new target angle. Call this to close the gripper.
        """
        self.current_angle = max(0, min(100, angle)) # Clamp between 0 and 100
        self.is_gripping = True

    def control_step(self, fsr_values):
        """
        Executes one step of the control loop.
        Checks pressure and adjusts the servo angle if necessary.
        Returns the new angle to be sent to the Arduino.
        """
        if not self.is_gripping or not fsr_values:
            return int(self.current_angle)
            
        # Check if any sensor has exceeded the pressure limit
        is_over_limit = any(value > self.pressure_limit for value in fsr_values)

        if is_over_limit:
            print(f"Pressure limit of {self.pressure_limit} exceeded! Releasing...")
            # Decrease the angle to release pressure
            self.current_angle -= self.release_step
            # Ensure the angle does not go below 0 (fully open)
            if self.current_angle < 0:
                self.current_angle = 0
        
        # Return the calculated angle, ensuring it's an integer
        return int(self.current_angle)

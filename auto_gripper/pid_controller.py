# filename: pid_controller.py
import time

class PIDController:
    """A simple PID controller class."""

    def __init__(self, Kp, Ki, Kd, setpoint, output_limits=(-180, 180)):
        """
        Initializes the PID controller.
        Args:
            Kp (float): Proportional gain.
            Ki (float): Integral gain.
            Kd (float): Derivative gain.
            setpoint (float): The target value for the controller.
            output_limits (tuple): A tuple (min, max) for the output value.
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits

        self._integral = 0
        self._previous_error = 0
        self._last_time = time.time()

    def update(self, current_value):
        """
        Calculates the PID output value for a given measurement.
        Args:
            current_value (float): The current measured value.
        Returns:
            float: The calculated output signal.
        """
        current_time = time.time()
        delta_time = current_time - self._last_time
        if delta_time == 0:
            return 0 # Avoid division by zero

        error = self.setpoint - current_value
        
        # Proportional term
        P_out = self.Kp * error

        # Integral term
        self._integral += error * delta_time
        I_out = self.Ki * self._integral

        # Derivative term
        derivative = (error - self._previous_error) / delta_time
        D_out = self.Kd * derivative

        # Calculate the total output
        output = P_out + I_out + D_out
        
        # Clamp the output to the defined limits
        if self.output_limits:
            output = max(self.output_limits[0], min(self.output_limits[1], output))

        # Update state for next iteration
        self._previous_error = error
        self._last_time = current_time

        return output

    def set_setpoint(self, setpoint):
        """Updates the target setpoint."""
        self.setpoint = setpoint
        self.reset()

    def reset(self):
        """Resets the integral and previous error, useful when changing setpoints."""
        self._integral = 0
        self._previous_error = 0
        self._last_time = time.time()
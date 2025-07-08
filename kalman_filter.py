class KalmanFilter:
    def __init__(self):
        """
        Initializes the Kalman Filter.
        Args:
            process_noise (float): The process noise covariance (Q).
                                   Represents how much the true value is expected to change.
            measurement_noise (float): The measurement noise covariance (R).
                                       Represents how noisy the sensor readings are.
            initial_value (float): The initial estimate for the value.
        """
        self.Q = 1e-5
        self.R = 0.1
        self.P = 1.0  # Initial estimate error covariance
        self.x_hat = 0.0  # Initial estimate of the state

    def update(self, measurement):
        """
        Takes a new measurement and returns the filtered value.
        Args:
            measurement (float): The new noisy measurement from the sensor.
        Returns:
            float: The new filtered estimate.
        """
        # --- Prediction Step ---
        # In our simple case, we predict the next state will be the same as the current one.
        x_hat_minus = self.x_hat
        P_minus = self.P + self.Q

        # --- Update Step (Correction) ---
        # Calculate Kalman Gain
        K = P_minus / (P_minus + self.R)
        
        # Update the estimate with the new measurement
        self.x_hat = x_hat_minus + K * (measurement - x_hat_minus)
        
        # Update the estimate error covariance
        self.P = (1 - K) * P_minus

        return self.x_hat

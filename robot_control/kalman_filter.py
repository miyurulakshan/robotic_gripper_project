# filename: kalman_filter.py
class KalmanFilter:
    def __init__(self, process_noise=1e-5, measurement_noise=0.1, initial_value=0):
        """
        Initializes the Kalman Filter.
        Args:
            process_noise (float): The process noise covariance (Q).
            measurement_noise (float): The measurement noise covariance (R).
            initial_value (float): The initial estimate for the value.
        """
        self.Q = process_noise
        self.R = measurement_noise
        self.P = 1.0
        self.x_hat = initial_value

    def update(self, measurement):
        """
        Takes a new measurement and returns the filtered value.
        """
        # Prediction Step
        x_hat_minus = self.x_hat
        P_minus = self.P + self.Q

        # Update Step (Correction)
        K = P_minus / (P_minus + self.R)
        self.x_hat = x_hat_minus + K * (measurement - x_hat_minus)
        self.P = (1 - K) * P_minus

        return self.x_hat

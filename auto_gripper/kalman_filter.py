# filename: kalman_filter.py
# This version implements a Multivariate Kalman Filter for sensor fusion.
import numpy as np

class MultivariateKalmanFilter:
    """
    A Kalman Filter for fusing multiple sensor inputs into a single state estimate.
    This implementation uses numpy for matrix operations.
    """
    def __init__(self, A, H, Q, R, x_hat_initial, P_initial):
        """
        Initializes the Multivariate Kalman Filter.

        Args:
            A (np.ndarray): State Transition Matrix.
            H (np.ndarray): Measurement Matrix.
            Q (np.ndarray): Process Noise Covariance Matrix.
            R (np.ndarray): Measurement Noise Covariance Matrix.
            x_hat_initial (np.ndarray): Initial state estimate vector.
            P_initial (np.ndarray): Initial estimate covariance matrix.
        """
        self.A = A  # State Transition Matrix
        self.H = H  # Measurement Matrix
        self.Q = Q  # Process Noise Covariance
        self.R = R  # Measurement Noise Covariance
        
        self.x_hat = x_hat_initial  # Estimated state vector
        self.P = P_initial          # Estimate covariance matrix

    def update(self, z):
        """
        Performs one full prediction and update cycle of the filter.

        Args:
            z (np.ndarray): The measurement vector (e.g., from 4 FSRs).

        Returns:
            np.ndarray: The updated state estimate vector.
        """
        # --- Prediction Step ---
        # Predict the next state: x_hat_minus = A * x_hat
        x_hat_minus = self.A @ self.x_hat
        
        # Predict the next estimate covariance: P_minus = A * P * A_transpose + Q
        P_minus = self.A @ self.P @ self.A.T + self.Q

        # --- Update Step (Correction) ---
        # Calculate the Kalman Gain: K = P_minus * H_transpose * (H * P_minus * H_transpose + R)^-1
        # The term (H @ P_minus @ self.H.T + self.R) is the innovation covariance
        innovation_cov = self.H @ P_minus @ self.H.T + self.R
        K = P_minus @ self.H.T @ np.linalg.inv(innovation_cov)

        # Update the state estimate with the measurement z: x_hat = x_hat_minus + K * (z - H * x_hat_minus)
        self.x_hat = x_hat_minus + K @ (z - self.H @ x_hat_minus)

        # Update the estimate covariance: P = (I - K * H) * P_minus
        # Where I is the identity matrix of the same size as P
        I = np.eye(self.P.shape[0])
        self.P = (I - K @ self.H) @ P_minus

        return self.x_hat

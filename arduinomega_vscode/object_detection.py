# File: object_detection.py

import cv2
import numpy as np
import threading
import time

class ObjectDetector:
    """
    Handles the video stream from the ESP32-CAM and performs object detection.
    """
    def __init__(self, stream_url):
        self.stream_url = stream_url
        self.capture = None
        self.is_running = False
        self.thread = None

    def start(self):
        """
        Starts the video processing in a separate thread to not block the main program.
        """
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Object detection thread started.")

    def _run(self):
        """
        The main loop for capturing and processing video frames.
        """
        while self.is_running:
            try:
                if self.capture is None:
                    self.capture = cv2.VideoCapture(self.stream_url)
                
                ret, frame = self.capture.read()
                if not ret:
                    print("Failed to get frame from camera stream. Retrying...")
                    self.capture.release()
                    self.capture = None
                    time.sleep(2) # Wait before retrying
                    continue

                # --- Object Detection Logic ---
                # This example detects the largest blue object.
                # You can replace this with more advanced models later.

                # Convert frame to HSV color space for easier color filtering
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Define the range for blue color in HSV
                lower_blue = np.array([100, 150, 50])
                upper_blue = np.array([140, 255, 255])
                
                # Create a mask to isolate blue pixels
                mask = cv2.inRange(hsv, lower_blue, upper_blue)

                # Find contours (shapes) in the mask
                contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    # Find the largest contour by area
                    largest_contour = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest_contour)

                    # Only draw if the object is of a reasonable size
                    if area > 500:
                        # Get bounding rectangle for the largest contour
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        # Draw a green rectangle around the detected object
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, "Object Detected", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Display the resulting frame in a window
                cv2.imshow('Object Detection - ESP32-CAM', frame)

                # Check for 'q' key to close the window
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()
                    break

            except Exception as e:
                print(f"Error in object detection loop: {e}")
                time.sleep(2)

        if self.capture:
            self.capture.release()
        cv2.destroyAllWindows()
        print("Object detection thread stopped.")

    def stop(self):
        """
        Signals the thread to stop running.
        """
        self.is_running = False
        if self.thread:
            self.thread.join() # Wait for the thread to finish

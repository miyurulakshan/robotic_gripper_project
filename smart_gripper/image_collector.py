# filename: image_collector.py
import cv2
import os
import time

# --- CONFIGURATION ---
# Make sure this URL matches the one from your object_recognizer.py file
ESP32_CAMERA_URL = "http://192.168.1.200:81/stream" 
DATASET_PATH = "dataset"
IMAGES_PER_OBJECT = 150

def main():
    """
    Main function to run the image collection process.
    """
    # First, check if the main 'dataset' directory exists. If not, create it.
    if not os.path.exists(DATASET_PATH):
        os.makedirs(DATASET_PATH)
        print(f"INFO: Created main directory: {DATASET_PATH}")

    # This main loop allows you to capture images for multiple objects in one session.
    while True:
        # Prompt the user to enter a name for the object they are about to capture.
        # This name will be used for the sub-folder (e.g., 'dataset/egg').
        object_name = input("\nEnter the name for the object ('background', 'egg', 'paper_box', 'power_bank') or type 'q' to quit: ").lower().strip()

        # If the user types 'q', break the loop and end the program.
        if object_name == 'q':
            print("Exiting program.")
            break
        
        # Ensure the user provides a valid name.
        if not object_name:
            print("ERROR: Object name cannot be empty. Please try again.")
            continue

        # Create the specific folder for the object inside the 'dataset' directory.
        object_path = os.path.join(DATASET_PATH, object_name)
        if not os.path.exists(object_path):
            os.makedirs(object_path)
            print(f"INFO: Created object directory: {object_path}")
        else:
            # Inform the user if the folder already exists.
            print(f"INFO: Directory '{object_path}' already exists. Images will be added/overwritten.")

        # Connect to the ESP32 camera stream.
        cap = cv2.VideoCapture(ESP32_CAMERA_URL)
        if not cap.isOpened():
            print(f"CRITICAL ERROR: Could not open camera stream at {ESP32_CAMERA_URL}.")
            print("Please check the URL and your ESP32-CAM's Wi-Fi connection.")
            continue # Go back to asking for an object name.

        print("\nSUCCESS: Camera connected. Get ready to capture.")
        
        # Give the user a 5-second countdown to position the object.
        for i in range(5, 0, -1):
            print(f"Starting capture in {i}...")
            time.sleep(1)

        print("\n--- Starting image capture ---")
        print("Slightly move the object around to get different angles.")
        
        img_count = 0
        while img_count < IMAGES_PER_OBJECT:
            # Read a frame from the camera.
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to grab frame. Please check the connection.")
                break

            # Create a copy of the frame to display information without saving it on the image.
            display_frame = frame.copy()
            text = f"Capturing for '{object_name}' | Image: {img_count + 1}/{IMAGES_PER_OBJECT}"
            cv2.putText(display_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Image Collector - Press 'q' to stop early", display_frame)

            # Save the original, clean frame to the disk.
            image_name = f"{img_count}.jpg"
            image_path = os.path.join(object_path, image_name)
            cv2.imwrite(image_path, frame)
            print(f"Saved {image_path}")
            
            img_count += 1
            
            # A short delay gives you time to move the object slightly for the next shot.
            time.sleep(0.2) 

            # Allow the user to quit the capture process for the current object early.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("WARNING: Capture interrupted by user.")
                break
        
        if img_count >= IMAGES_PER_OBJECT:
            print(f"\nSUCCESS: Captured {IMAGES_PER_OBJECT} images for '{object_name}'.")

        # Release the camera and close the OpenCV window before the next loop.
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

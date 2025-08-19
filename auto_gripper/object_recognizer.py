# filename: object_recognizer.py
import cv2
import numpy as np
import asyncio
import websockets
import threading
import queue
import time
import tensorflow as tf

# --- CONFIGURATION ---
ESP32_CAMERA_URL = "http://192.168.1.17:81/stream"
WEBSOCKET_URI = "ws://localhost:8765"

# The class names must match the alphabetical order of your dataset folder names
CLASS_NAMES = ["background", "egg", "paper_box", "power_bank"]
CONFIDENCE_THRESHOLD = 75.0 # You can adjust this value if needed

# --- ML MODEL LOADING ---
print("[Recognizer] Loading machine learning model...")
try:
    model = tf.keras.models.load_model('my_object_model.h5')
    print("[Recognizer] Model loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load model. Error: {e}")
    exit()

# --- THREADING FOR WEBSOCKETS (Unchanged) ---
outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

def websocket_thread():
    async def client_handler():
        while not shutdown_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print("[Network] Connected to WebSocket server.")
                    while not shutdown_event.is_set():
                        try:
                            message = outgoing_queue.get(timeout=0.1)
                            await websocket.send(message)
                            outgoing_queue.task_done()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                        except websockets.exceptions.ConnectionClosed:
                            print("[Network] Connection lost. Reconnecting...")
                            break
            except (ConnectionRefusedError, OSError, websockets.exceptions.InvalidURI) as e:
                if not shutdown_event.is_set():
                    print(f"[Network] Connection failed: {e}. Retrying in 2 seconds...")
                    await asyncio.sleep(2)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client_handler())
    loop.close()
    print("[Network] WebSocket thread has shut down.")

def main():
    print(f"Attempting to connect to camera stream at {ESP32_CAMERA_URL}")
    cap = cv2.VideoCapture(ESP32_CAMERA_URL)

    if not cap.isOpened():
        print("Error: Could not open camera stream.")
        return

    print("Camera stream opened successfully.")
    last_sent_message = None

    while not shutdown_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(ESP32_CAMERA_URL)
            continue

        # --- MACHINE LEARNING LOGIC ---
        detected_object = None
        
        # 1. Pre-process the frame for the model
        img_resized = cv2.resize(frame, (224, 224))
        img_array = tf.keras.utils.img_to_array(img_resized)
        img_array = tf.expand_dims(img_array, 0)

        # 2. Make a prediction
        predictions = model.predict(img_array)
        score = tf.nn.softmax(predictions[0])

        # 3. Interpret the result
        confidence = 100 * np.max(score)
        predicted_index = np.argmax(score)

        # Check if confidence is high enough
        if confidence > CONFIDENCE_THRESHOLD:
            predicted_class = CLASS_NAMES[predicted_index]
            
            # If the model confidently sees the background, we treat it as no object.
            if predicted_class == "background":
                detected_object = None
            else:
                detected_object = predicted_class
                # Prepare and draw label on the screen
                label = f"Object: {detected_object} ({confidence:.2f}%)"
                cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # --- Display the result in a window ---
        cv2.imshow("Object Recognition - Gripper View", frame)

        # --- Send the detected object to the controller ---
        message_to_send = f"OBJECT:{detected_object}" if detected_object else "OBJECT:None"
        
        if message_to_send != last_sent_message:
            outgoing_queue.put(message_to_send)
            last_sent_message = message_to_send
            print(f"[Recognition] Sent: {message_to_send}")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # --- Cleanup ---
    print("Shutting down application...")
    shutdown_event.set()
    cap.release()
    cv2.destroyAllWindows()
    ws_thread.join(timeout=2)
    print("Application shut down successfully.")

if __name__ == "__main__":
    ws_thread = threading.Thread(target=websocket_thread, daemon=True)
    ws_thread.start()
    main()
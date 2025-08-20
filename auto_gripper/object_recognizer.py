# filename: object_recognizer.py
import cv2
import numpy as np
import asyncio
import websockets
import threading
import queue
import time
import tensorflow as tf

ESP32_CAMERA_URL = "http://192.168.1.200:81/stream" 
WEBSOCKET_URI = "ws://localhost:8765"
CLASS_NAMES = ["background", "egg", "paper_box", "power_bank"]
CONFIDENCE_THRESHOLD = 75.0 

print("[Recognizer] Loading machine learning model...")
try:
    model = tf.keras.models.load_model('my_object_model.h5')
    print("[Recognizer] Model loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load model. Error: {e}")
    exit()

outgoing_queue = queue.Queue()
shutdown_event = threading.Event()

def websocket_thread():
    async def client_handler():
        while not shutdown_event.is_set():
            try:
                async with websockets.connect(WEBSOCKET_URI) as websocket:
                    print("[Recognizer Network] Connected to server.")
                    while not shutdown_event.is_set():
                        try:
                            message = outgoing_queue.get(timeout=0.1)
                            await websocket.send(message)
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                        except websockets.exceptions.ConnectionClosed:
                            print("[Recognizer Network] Connection lost. Reconnecting...")
                            break 
            except (ConnectionRefusedError, OSError, websockets.exceptions.InvalidURI) as e:
                if not shutdown_event.is_set():
                    print(f"[Recognizer Network] Connection failed: {e}. Retrying in 2 seconds...")
                    await asyncio.sleep(2)
    asyncio.run(client_handler())

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
            print("Error: Failed to grab frame.")
            time.sleep(1)
            continue
        
        detected_object = None
        img_resized = cv2.resize(frame, (224, 224))
        img_array = tf.keras.utils.img_to_array(img_resized)
        img_array = tf.expand_dims(img_array, 0)
        predictions = model.predict(img_array)
        score = tf.nn.softmax(predictions[0])
        confidence = 100 * np.max(score)
        predicted_index = np.argmax(score)

        if confidence > CONFIDENCE_THRESHOLD:
            predicted_class = CLASS_NAMES[predicted_index]
            if predicted_class != "background":
                detected_object = predicted_class
                label = f"Object: {detected_object} ({confidence:.2f}%)"
                cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        cv2.imshow("Object Recognition - Gripper View", frame)
        message_to_send = f"OBJECT:{detected_object.upper()}" if detected_object else "OBJECT:None"
        
        # Only send if the detection changes, to reduce network spam
        if message_to_send != last_sent_message:
            outgoing_queue.put(message_to_send)
            last_sent_message = message_to_send
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(0.1)

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
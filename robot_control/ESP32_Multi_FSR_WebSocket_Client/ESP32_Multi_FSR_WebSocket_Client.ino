#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <ESP32Servo.h>

using namespace websockets;

// --- IMPORTANT: CHANGE THESE VALUES ---
const char* ssid = "SLT-4G_12BED";
const char* password = "11221122";
const char* websockets_server = "ws://192.168.1.13:8765";
// --- ---

// --- SENSOR CONFIGURATION for ESP32-S3 ---
const int NUM_SENSORS = 8;
const int fsrPins[NUM_SENSORS] = {6, 8, 7, 5, 3, 4, 2, 1};
// --- ---

// --- SERVO & POTENTIOMETER CONFIGURATION ---
const int servoPin = 10;
const int potPin = 9;
Servo myServo;
// --- ---

// --- KALMAN FILTER for POTENTIOMETER ---
struct KalmanFilter {
    float Q = 1e-4; // Process noise
    float R = 0.0005; // Measurement noise
    float P = 1.0;  // Estimation error covariance
    float x_hat = 0;// Estimated value
};

KalmanFilter potFilter;

float updateKalman(KalmanFilter &kf, float measurement) {
    // Prediction
    float x_hat_minus = kf.x_hat;
    float P_minus = kf.P + kf.Q;

    // Update (Correction)
    float K = P_minus / (P_minus + kf.R);
    kf.x_hat = x_hat_minus + K * (measurement - x_hat_minus);
    kf.P = (1 - K) * P_minus;
    return kf.x_hat;
}
// --- ---

WebsocketsClient client;

void onWebsocketEvent(WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
        Serial.println("Connection to server opened.");
    } else if (event == WebsocketsEvent::ConnectionClosed) {
        Serial.println("Connection closed.");
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    myServo.attach(servoPin);
    Serial.println("Servo Initialized.");
    
    // --- Initialize Kalman Filter with the first reading ---
    potFilter.x_hat = analogRead(potPin);
    Serial.println("Potentiometer Kalman Filter Initialized.");

    WiFi.begin(ssid, password);
    Serial.print("Connecting to Wi-Fi...");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
    }
    Serial.println("\nConnected to Wi-Fi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    client.onEvent(onWebsocketEvent);

    Serial.println("Connecting to WebSocket server...");
    while (!client.connect(websockets_server)) {
        Serial.println("Connection failed, retrying...");
        delay(2000);
    }
}

void loop() {
    // --- Servo Control Logic (Local & Filtered) ---
    int potValueRaw = analogRead(potPin);
    float potValueFiltered = updateKalman(potFilter, potValueRaw);
    
    // Map the FILTERED potentiometer value to the servo angle
    int servoAngle = map(potValueFiltered, 0, 4095, 0, 180);
    myServo.write(servoAngle);

    // --- WebSocket Communication Logic ---
    if (client.available()) {
        client.poll();

        String message = "";
        for (int i = 0; i < NUM_SENSORS; i++) {
            int fsrReading = analogRead(fsrPins[i]);
            message += String(fsrReading);
            if (i < NUM_SENSORS - 1) {
                message += ",";
            }
        }
        client.send(message);

    } else {
        Serial.println("Client disconnected. Trying to reconnect...");
        while (!client.connect(websockets_server)) {
            Serial.println("Connection failed, retrying...");
            delay(2000);
        }
    }
    delay(20);
}

#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <ESP32Servo.h>

using namespace websockets;

// --- CONFIGURATION ---
const char* ssid = "SLT-4G_12BED";
const char* password = "11221122";
const char* websockets_server = "ws://192.168.1.13:8765"; // Your PC's IP address

const int NUM_SENSORS = 8;
const int fsrPins[NUM_SENSORS] = {6, 8, 7, 5, 3, 4, 2, 1};

// --- CALIBRATION ---: Array to store the initial sensor offsets
int fsrOffsets[NUM_SENSORS];

const int potPin1 = 9;
const int servoPin1 = 10;
const int potPin2 = 11;
const int servoPin2 = 12;

Servo myServo1;
Servo myServo2;
WebsocketsClient client;

void onEventsCallback(WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
        Serial.println("Connection to server opened.");
    } else if (event == WebsocketsEvent::ConnectionClosed) {
        Serial.println("Connection closed.");
    }
}

void onMessageCallback(WebsocketsMessage message) {
    String msg = message.data();
    
    if (msg.startsWith("PULSE1:")) {
        int pulse_width = msg.substring(7).toInt();
        myServo1.writeMicroseconds(pulse_width);
    } 
    else if (msg.startsWith("PULSE2:")) {
        int pulse_width = msg.substring(7).toInt();
        myServo2.writeMicroseconds(pulse_width);
        Serial.print("Set Servo 2 pulse to: ");
        Serial.println(pulse_width);
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    // --- CALIBRATION ---: Run the FSR calibration routine
    Serial.println("Starting FSR calibration... Do not touch the sensors.");
    delay(2000); // Wait for sensors to stabilize
    for (int i = 0; i < NUM_SENSORS; i++) {
        fsrOffsets[i] = analogRead(fsrPins[i]);
        Serial.print("FSR ");
        Serial.print(i);
        Serial.print(" offset: ");
        Serial.println(fsrOffsets[i]);
    }
    Serial.println("Calibration complete.");
    // --- END CALIBRATION ---

    myServo1.attach(servoPin1, 1000, 2000); 
    myServo2.attach(servoPin2, 500, 2500);
    myServo2.writeMicroseconds(2300); 

    Serial.println("Both Servos Initialized.");
    
    WiFi.begin(ssid, password);
    Serial.print("Connecting to Wi-Fi...");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
    }
    Serial.println("\nConnected to Wi-Fi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    client.onEvent(onEventsCallback);
    client.onMessage(onMessageCallback);

    Serial.println("Connecting to WebSocket server...");
    while (!client.connect(websockets_server)) {
        Serial.println("Connection failed, retrying...");
        delay(2000);
    }
}

void loop() {
    if (client.available()) {
        client.poll(); 

        int potValue1 = analogRead(potPin1);
        int potValue2 = analogRead(potPin2);

        String message = String(potValue1) + "," + String(potValue2);
        
        for (int i = 0; i < NUM_SENSORS; i++) {
            message += ",";
            
            // --- CALIBRATION ---: Apply the offset to the current reading
            int fsrReading = analogRead(fsrPins[i]);
            int calibratedValue = fsrReading - fsrOffsets[i];
            
            // Ensure the reading doesn't go below zero due to noise
            if (calibratedValue < 0) {
                calibratedValue = 0;
            }
            
            message += String(calibratedValue);
        }
        client.send(message);
        Serial.println(message);

    } else {
        Serial.println("Client disconnected. Trying to reconnect...");
        while (!client.connect(websockets_server)) {
            Serial.println("Connection failed, retrying...");
            delay(2000);
        }
    }
    delay(20);
}
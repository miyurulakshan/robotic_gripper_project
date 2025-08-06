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

// --- NEW: Define pins for both servos and potentiometers ---
const int potPin1 = 9;
const int servoPin1 = 10;
const int potPin2 = 11;    // New potentiometer pin
const int servoPin2 = 12;    // New servo pin

Servo myServo1;
Servo myServo2; // New servo object
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
    Serial.print("Command received from server: ");
    Serial.println(msg);

    // --- UPDATED: Handle commands for both servos ---
    if (msg.startsWith("SERVO1:")) {
        int angle = msg.substring(7).toInt();
        myServo1.write(constrain(angle, 0, 180));
    } else if (msg.startsWith("SERVO2:")) {
        int angle = msg.substring(7).toInt();
        myServo2.write(constrain(angle, 0, 180));
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    myServo1.attach(servoPin1);
    myServo2.attach(servoPin2); // Attach the second servo
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

        // Read both raw potentiometer values
        int potValue1 = analogRead(potPin1);
        int potValue2 = analogRead(potPin2);

        // --- UPDATED: Create the new message string ---
        // Format: "pot1,pot2,fsr1,fsr2,..."
        String message = String(potValue1) + "," + String(potValue2);
        
        for (int i = 0; i < NUM_SENSORS; i++) {
            message += ",";
            int fsrReading = analogRead(fsrPins[i]);
            message += String(fsrReading);
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

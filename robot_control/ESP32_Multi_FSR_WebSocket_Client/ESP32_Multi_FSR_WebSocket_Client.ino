#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <ESP32Servo.h>

using namespace websockets;

// --- CONFIGURATION ---
const char* ssid = "SLT-4G_12BED";
const char* password = "11221122";
const char* websockets_server = "ws://192.168.1.13:8765"; // Your PC's IP address

const int NUM_SENSORS = 8;
const int fsrPins[NUM_SENSORS] = {6, 8, 7, 5, 3, 4, 2, 2};

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

// --- THIS FUNCTION IS UPDATED ---
void onMessageCallback(WebsocketsMessage message) {
    String msg = message.data();
    //Serial.print("Command received from server: ");
    //Serial.println(msg);

    // Look for the new "PULSE1:" command for high-precision control
    if (msg.startsWith("PULSE1:")) {
        int pulse_width = msg.substring(7).toInt();
        myServo1.writeMicroseconds(pulse_width); // Use the high-precision function
    } 
    // You could add a "PULSE2:" command here later if needed
    // else if (msg.startsWith("PULSE2:")) { ... }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Attach the servo. For ESP32, you can optionally specify the min/max pulse widths.
    // This improves the accuracy of the standard .write() but we will use .writeMicroseconds() directly.
    myServo1.attach(servoPin1, 1000, 2000); // min and max pulse in microseconds
    myServo2.attach(servoPin2);
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
            int fsrReading = analogRead(fsrPins[i]);
            message += String(fsrReading);
            Serial.println(message);
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
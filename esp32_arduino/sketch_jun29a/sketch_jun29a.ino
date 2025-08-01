#include <WiFi.h>
#include <ArduinoWebsockets.h>

// This line is the fix for the compilation error
using namespace websockets;

// --- IMPORTANT: CHANGE THESE VALUES ---
const char* ssid = "SLT-4G_12BED";         // Your Wi-Fi network name
const char* password = "11221122"; // Your Wi-Fi network password
const char* websockets_server = "ws://192.168.1.11:8765"; // Your computer's IP address
// --- ---

// Pin where the FSR is connected (use an ADC1 pin for best results)
const int fsrPin = 34; // GPIO34 is a good choice (ADC1_CH6)

// Create a WebSocket client object
WebsocketsClient client;

// This function gets called when a WebSocket event occurs
void onWebsocketEvent(WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
        Serial.println("Connection to server opened.");
    } else if (event == WebsocketsEvent::ConnectionClosed) {
        Serial.println("Connection closed.");
    } else if (event == WebsocketsEvent::GotPing) {
        Serial.println("Got a Ping!");
    } else if (event == WebsocketsEvent::GotPong) {
        Serial.println("Got a Pong!");
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Connect to Wi-Fi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to Wi-Fi...");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
    }
    Serial.println("\nConnected to Wi-Fi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Set the function to handle WebSocket events
    client.onEvent(onWebsocketEvent);

    // Try to connect to the WebSocket server
    Serial.println("Connecting to WebSocket server...");
    while (!client.connect(websockets_server)) {
        Serial.println("Connection failed, retrying...");
        delay(2000);
    }
}

void loop() {
    // Make sure the client is still connected
    if (client.available()) {
        // Let the client library do its work
        client.poll();

        // Read the FSR sensor value (0-4095)
        int fsrReading = analogRead(fsrPin);

        // Convert the integer reading to a String to send it
        String message = String(fsrReading);

        // Send the FSR reading to the server
        client.send(message);

        // Print the reading to the local serial monitor for debugging
         Serial.print("Sent FSR Reading: "); // You can uncomment this for debugging
         Serial.println(message);

    } else {
        // If the client is not available, try to reconnect
        Serial.println("Client disconnected. Trying to reconnect...");
        while (!client.connect(websockets_server)) {
            Serial.println("Connection failed, retrying...");
            delay(2000);
        }
    }

    // Wait for a short period before sending the next reading
    delay(20); // Send data 10 times per second. Adjust as needed.
}

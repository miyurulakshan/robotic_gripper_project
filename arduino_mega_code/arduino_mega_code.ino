// File: arduino_mega_code/arduino_mega_code.ino
// This version sends back the current servo angle for a closed-loop system.

#include <Servo.h>

// Define the pin for the servo motor
const int SERVO_PIN = 2;

// Create a servo object
Servo gripperServo;

// Define the analog input pins for the 8 FSRs
const int FSR_PINS[8] = {A6, A7, A5, A4, A2, A1, A3, A8};

// This variable will store the last commanded angle
int currentServoAngle = 0;

void setup() {
  // Start serial communication at a high baud rate for responsiveness
  Serial.begin(115200);

  // Attach the servo to its pin
  gripperServo.attach(SERVO_PIN);

  // Set the initial position of the servo to fully open (0 degrees)
  gripperServo.write(currentServoAngle);
}

void loop() {
  // === Part 1: Receive servo command from Python ===
  if (Serial.available() > 0) {
    // Read the incoming byte. We expect a value from 0 to 100.
    int commandedAngle = Serial.read();

    // Constrain the value to be within the 0-100 degree range for safety
    commandedAngle = constrain(commandedAngle, 0, 100);

    // Update our state variable
    currentServoAngle = commandedAngle;

    // Command the servo to move to the new position
    gripperServo.write(currentServoAngle);
  }

  // === Part 2: Read FSRs and send feedback to Python ===
  
  // Create a string for the data packet
  String dataPacket = "";

  // FEEDBACK: Add the current angle as the FIRST part of the packet
  dataPacket += String(currentServoAngle);
  dataPacket += ",";

  // Now, add all the FSR readings
  for (int i = 0; i < 8; i++) {
    int sensorValue = analogRead(FSR_PINS[i]);
    dataPacket += String(sensorValue);

    // Add a comma after each value, except for the last one
    if (i < 7) {
      dataPacket += ",";
    }
  }

  // Send the complete packet (e.g., "90,12,5,300,...") to the PC
  Serial.println(dataPacket);

  // A small delay to control the loop frequency
  delay(50); // This creates a feedback rate of about 20 Hz
}

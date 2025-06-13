// File: arduino_mega_code/arduino_mega_code.ino
// This code is for the Arduino Mega.

#include <Servo.h>

// Define the pin for the servo motor
const int SERVO_PIN = 2;

// Create a servo object
Servo gripperServo;

// Define the analog input pins for the 8 FSRs
const int FSR_PINS[8] = {A6, A7, A5, A4, A2, A1, A3, A8};

void setup() {
  // Start serial communication at a high baud rate for responsiveness
  Serial.begin(115200);

  // Attach the servo to its pin
  gripperServo.attach(SERVO_PIN);

  // Set the initial position of the servo to fully open (0 degrees)
  gripperServo.write(0);
}

void loop() {
  // === Part 1: Receive servo command from Python ===
  // Check if there is any data available to be read from the serial port
  if (Serial.available() > 0) {
    // Read the incoming byte. We expect a value from 0 to 100.
    int servoAngle = Serial.read();

    // Constrain the value to be within the 0-100 degree range for safety
    servoAngle = constrain(servoAngle, 0, 100);

    // Command the servo to move to the new position
    gripperServo.write(servoAngle);
  }

  // === Part 2: Read FSR sensors and send data to Python ===
  String fsrReadings = "";
  for (int i = 0; i < 8; i++) {
    // Read the analog value from the current FSR pin (0-1023)
    int sensorValue = analogRead(FSR_PINS[i]);
    
    // Add the value to our string
    fsrReadings += String(sensorValue);

    // Add a comma after each value, except for the last one
    if (i < 7) {
      fsrReadings += ",";
    }
  }

  // Send the complete comma-separated string of sensor values to the PC
  Serial.println(fsrReadings);

  // A small delay to control the loop frequency and prevent flooding the serial port
  delay(50); // This creates a control loop of about 20 Hz
}

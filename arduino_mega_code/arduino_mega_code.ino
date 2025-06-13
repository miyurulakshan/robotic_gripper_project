// File: arduino_mega_code/arduino_mega_code.ino
// This version runs at a much higher frequency for faster response times.

#include <Servo.h>

const int SERVO_PIN = 2;
Servo gripperServo;
const int FSR_PINS[8] = {A6, A7, A5, A4, A2, A1, A3, A8};
int currentServoAngle = 0;

void setup() {
  Serial.begin(115200);
  gripperServo.attach(SERVO_PIN);
  gripperServo.write(currentServoAngle);
}

void loop() {
  // === Part 1: Receive servo command from Python ===
  if (Serial.available() > 0) {
    int commandedAngle = Serial.read();
    commandedAngle = constrain(commandedAngle, 0, 100);
    currentServoAngle = commandedAngle;
    gripperServo.write(currentServoAngle);
  }

  // === Part 2: Build and send a verified data packet ===
  String dataPacket = "";
  dataPacket += String(currentServoAngle);
  dataPacket += ",";
  for (int i = 0; i < 8; i++) {
    int sensorValue = analogRead(FSR_PINS[i]);
    dataPacket += String(sensorValue);
    if (i < 7) {
      dataPacket += ",";
    }
  }

  // --- Send the framed packet ---
  Serial.print('S');
  Serial.print(dataPacket);
  Serial.println('E');

  // --- SPEED INCREASE ---
  // Reduced delay from 50ms to 5ms for a ~200Hz loop rate.
  delay(5); 
}

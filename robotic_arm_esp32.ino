/*
=============================================================
  🤖  ROBOTIC ARM — ESP32 WiFi Command Server
  Commands: /pick  /right  /left  /drop
=============================================================
*/

#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// --- Network Credentials ---
const char* ssid     = "Air";
const char* password = "99999999";

WebServer server(80);
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVO_FREQ 50
#define SERVOMIN   150
#define SERVOMAX   500

int currentPos[4] = {90, 40, 140, 40};

// ── Helpers ──────────────────────────────────
int degreeToPulse(int deg) {
  return map(deg, 0, 180, SERVOMIN, SERVOMAX);
}

void moveSmooth(int channel, int targetDeg, int stepDelay = 15) {
  int startDeg = currentPos[channel];
  if (startDeg < targetDeg) {
    for (int pos = startDeg; pos <= targetDeg; pos++) {
      pwm.setPWM(channel, 0, degreeToPulse(pos));
      delay(stepDelay);
    }
  } else {
    for (int pos = startDeg; pos >= targetDeg; pos--) {
      pwm.setPWM(channel, 0, degreeToPulse(pos));
      delay(stepDelay);
    }
  }
  currentPos[channel] = targetDeg;
}

// ── Command Handlers ─────────────────────────
void handlePick() {
  Serial.println("[CMD] PICK received");
  server.send(200, "text/plain", "OK:pick");
  moveSmooth(0, 90);
  moveSmooth(2, 140);
  moveSmooth(1, 0);
  moveSmooth(3, 40);
  moveSmooth(3, 0);
  delay(1000);
  moveSmooth(1, 40);
}

void handleRight() {
  Serial.println("[CMD] RIGHT received");
  server.send(200, "text/plain", "OK:right");
  moveSmooth(1, 40);
  moveSmooth(2, 140);
  moveSmooth(0, 0);
}

void handleLeft() {
  Serial.println("[CMD] LEFT received");
  server.send(200, "text/plain", "OK:left");
  moveSmooth(1, 40);
  moveSmooth(2, 140);
  moveSmooth(0, 150);
}

void handleDrop() {
  Serial.println("[CMD] DROP received");
  server.send(200, "text/plain", "OK:drop");
  moveSmooth(2, 140);
  moveSmooth(1, 0);
  moveSmooth(3, 0);
  moveSmooth(3, 40);
  delay(1000);
  moveSmooth(1, 40);
}

void handleHome() {
  Serial.println("[CMD] HOME received");
  server.send(200, "text/plain", "OK:home");
  moveSmooth(0, 90);
  moveSmooth(1, 40);
  moveSmooth(2, 140);
  moveSmooth(3, 40);
}

void handleNotFound() {
  server.send(404, "text/plain", "ERROR:unknown_command");
  Serial.println("[WARN] Unknown endpoint requested");
}

void handleStatus() {
  String msg = "ONLINE | pos:";
  for (int i = 0; i < 4; i++) {
    msg += String(currentPos[i]);
    if (i < 3) msg += ",";
  }
  server.send(200, "text/plain", msg);
}

// ── Setup ────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n========================================");
  Serial.println("  🤖  Robotic Arm — ESP32 Booting ...");
  Serial.println("========================================");

  // Init PCA9685
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(100);

  // Move to home position
  Serial.println("[INIT] Moving to home position ...");
  for (int i = 0; i < 4; i++) {
    pwm.setPWM(i, 0, degreeToPulse(currentPos[i]));
    delay(300);
  }

  // Connect WiFi
  Serial.printf("[WiFi] Connecting to: %s\n", ssid);
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts > 30) {
      Serial.println("\n[ERROR] WiFi failed. Restarting ...");
      ESP.restart();
    }
  }

  Serial.println("\n[WiFi] ✅ Connected!");
  Serial.print("[WiFi] IP Address: ");
  Serial.println(WiFi.localIP());   // ← COPY THIS IP INTO speech_to_text.py
  Serial.println("========================================\n");

  // Register routes
  server.on("/pick",   handlePick);
  server.on("/right",  handleRight);
  server.on("/left",   handleLeft);
  server.on("/drop",   handleDrop);
  server.on("/home",   handleHome);
  server.on("/status", handleStatus);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("[SERVER] HTTP server started.");
  Serial.println("[SERVER] Listening for commands ...\n");
}

// ── Loop ─────────────────────────────────────
void loop() {
  server.handleClient();
}

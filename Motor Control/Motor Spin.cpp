#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ─────────────────────────────────────────────────────────────────
// CONFIGURATION — fill in before uploading
// ─────────────────────────────────────────────────────────────────
const char* SSID      = "YOUR_WIFI_SSID";
const char* PASSWORD  = "YOUR_WIFI_PASSWORD";
const char* SERVER_IP = "192.168.x.x";    // your PC's LAN IP (run ipconfig to find it)

// ─────────────────────────────────────────────────────────────────
// HARDWARE CONSTANTS — verify before first run
// ─────────────────────────────────────────────────────────────────

// Wheel geometry
const float PI_VAL            = 3.14159265;
const float WHEEL_DIAMETER_MM = 66.0;
const float WHEEL_CIRCUMFERENCE = PI_VAL * WHEEL_DIAMETER_MM;  // 210.49 mm

// Encoder counts per full wheel revolution.
// To verify: hold the car still, spin one wheel exactly one full turn by hand,
// and count the pulse count printed to Serial. Replace 823.1 if different.
const float COUNTS_PER_REV = 823.1;

// Distance between the two wheel contact points (axle width).
// Measure with a ruler, centre-to-centre of the two wheels, in mm.
// This value controls how accurately turnByAngle() hits the target angle.
const float WHEELBASE_MM = 150.0;  // ← REPLACE WITH YOUR MEASUREMENT

// Base motor PWM speed (0–255). Lower = more controllable, higher = faster.
const int BASE_PWM = 100;

// ─────────────────────────────────────────────────────────────────
// PIN ASSIGNMENTS
// ─────────────────────────────────────────────────────────────────
const int L_AIN1 = 12;
const int L_AIN2 = 13;
const int L_SLP  = 14;

const int R_AIN1 = 19;
const int R_AIN2 = 18;
const int R_SLP  = 17;

const int L_ENCA = 11;
const int R_ENCA = 20;

// DHT_PIN must not conflict with motor or encoder pins (12,13,14,17,18,19,11,20)
#define DHT_PIN  2
#define DHT_TYPE DHT22
DHT dht(DHT_PIN, DHT_TYPE);

// ─────────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────────
volatile long leftCount  = 0;
volatile long rightCount = 0;

// Tracked position from home base (updated by movement functions)
float currentAngleDeg   = 0.0;
float currentDistanceMm = 0.0;
float lastTraveledMm    = 0.0;  // distance of last go_to — used for return trip

// Tracks which server command was last executed (by issued_at timestamp)
// so the same command is not re-run after the car finishes and goes idle
String lastCommandIssuedAt = "";

// Timing
unsigned long lastHeartbeatMs = 0;
unsigned long lastPollMs      = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 10000;
const unsigned long POLL_INTERVAL_MS      = 500;

// ─────────────────────────────────────────────────────────────────
// ENCODER ISRs
// ─────────────────────────────────────────────────────────────────
void leftEncoderISR()  { leftCount++;  }
void rightEncoderISR() { rightCount++; }

// ─────────────────────────────────────────────────────────────────
// MOTOR CONTROL — low level
// ─────────────────────────────────────────────────────────────────
void setLeftForward (int pwm) { digitalWrite(L_AIN2, LOW); analogWrite(L_AIN1, pwm); }
void setRightForward(int pwm) { digitalWrite(R_AIN2, LOW); analogWrite(R_AIN1, pwm); }
void setLeftBackward(int pwm) { digitalWrite(L_AIN1, LOW); analogWrite(L_AIN2, pwm); }
void setRightBackward(int pwm){ digitalWrite(R_AIN1, LOW); analogWrite(R_AIN2, pwm); }
void stopLeft()  { analogWrite(L_AIN1, 0); analogWrite(L_AIN2, 0); }
void stopRight() { analogWrite(R_AIN1, 0); analogWrite(R_AIN2, 0); }
void stopAll()   { stopLeft(); stopRight(); }

// ─────────────────────────────────────────────────────────────────
// UNIT CONVERSION
// ─────────────────────────────────────────────────────────────────
long distanceToCounts(float distance_mm) {
  return (long)((distance_mm / WHEEL_CIRCUMFERENCE) * COUNTS_PER_REV);
}

// Returns encoder counts for one wheel during an in-place turn.
// Each wheel travels an arc = (angle_deg / 360) * PI * WHEELBASE_MM
long angleToCounts(float angle_deg) {
  float arc_mm = (abs(angle_deg) / 360.0) * PI_VAL * WHEELBASE_MM;
  return (long)((arc_mm / WHEEL_CIRCUMFERENCE) * COUNTS_PER_REV);
}

// ─────────────────────────────────────────────────────────────────
// HTTP HELPERS
// ─────────────────────────────────────────────────────────────────
void postToServer(const char* path, String body) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String("http://") + SERVER_IP + ":5000" + path);
  http.addHeader("Content-Type", "application/json");
  http.POST(body);
  http.end();
}

// Minimal JSON field extractors — avoids needing ArduinoJson library
String jsonGetString(String json, String key) {
  String k = "\"" + key + "\":\"";
  int s = json.indexOf(k);
  if (s < 0) return "";
  s += k.length();
  return json.substring(s, json.indexOf("\"", s));
}

float jsonGetFloat(String json, String key) {
  String k = "\"" + key + "\":";
  int s = json.indexOf(k);
  if (s < 0) return 0.0;
  s += k.length();
  int e  = json.indexOf(",", s);
  int e2 = json.indexOf("}", s);
  if (e < 0 || (e2 >= 0 && e2 < e)) e = e2;
  return json.substring(s, e).toFloat();
}

// GETs /api/car/command and populates the output parameters.
// Returns true if a valid response was received.
bool fetchCommand(String& type, float& angleDeg, float& distMm, String& issuedAt) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(String("http://") + SERVER_IP + ":5000/api/car/command");
  int code = http.GET();
  if (code != 200) { http.end(); return false; }
  String body = http.getString();
  http.end();

  type     = jsonGetString(body, "type");
  issuedAt = jsonGetString(body, "issued_at");
  angleDeg = jsonGetFloat(body, "angle_deg");
  distMm   = jsonGetFloat(body, "distance_mm");
  return true;
}

void postTelemetry(String status) {
  String body = "{\"angle_deg\":"    + String(currentAngleDeg, 1)
              + ",\"distance_mm\":"  + String(currentDistanceMm, 1)
              + ",\"status\":\""     + status + "\"}";
  postToServer("/api/car/telemetry", body);
}

void postSensor(float humidity, float temperature) {
  String body = "{\"humidity_pct\":" + String(humidity, 1)
              + ",\"temperature_c\":" + String(temperature, 1) + "}";
  postToServer("/api/car/sensor", body);
}

// ─────────────────────────────────────────────────────────────────
// MOVEMENT — forward
// ─────────────────────────────────────────────────────────────────
void moveForwardDistance(float distance_mm) {
  long target = distanceToCounts(distance_mm);
  noInterrupts(); leftCount = 0; rightCount = 0; interrupts();

  // Timeout scales with distance; minimum 3 seconds
  unsigned long timeoutMs  = (unsigned long)(distance_mm / 50.0) * 1000 + 3000;
  unsigned long startTime  = millis();
  unsigned long lastTelems = millis();

  while (true) {
    long l, r;
    noInterrupts(); l = leftCount; r = rightCount; interrupts();

    if (l >= target && r >= target) break;
    if (millis() - startTime > timeoutMs) { Serial.println("Forward timeout"); break; }

    int lPwm = BASE_PWM, rPwm = BASE_PWM;

    // Drift correction: slow the faster wheel to keep straight
    if      (l > r + 5) { lPwm = BASE_PWM - 10; rPwm = BASE_PWM + 10; }
    else if (r > l + 5) { lPwm = BASE_PWM + 10; rPwm = BASE_PWM - 10; }

    // Slow down near target to reduce overshoot
    if (l > target * 0.8) lPwm = min(lPwm, BASE_PWM / 2);
    if (r > target * 0.8) rPwm = min(rPwm, BASE_PWM / 2);

    if (l < target) setLeftForward(lPwm);  else stopLeft();
    if (r < target) setRightForward(rPwm); else stopRight();

    // Post live telemetry every 2 seconds so the dashboard stays updated
    // and the device doesn't appear offline during long runs
    if (millis() - lastTelems > 2000) {
      lastTelems = millis();
      float traveled = (float(l) / COUNTS_PER_REV) * WHEEL_CIRCUMFERENCE;
      currentDistanceMm = traveled;
      postTelemetry("investigating");
    }
  }
  stopAll();
  // Sync final position
  long l, r;
  noInterrupts(); l = leftCount; r = rightCount; interrupts();
  currentDistanceMm += (float((l + r) / 2) / COUNTS_PER_REV) * WHEEL_CIRCUMFERENCE;
}

// ─────────────────────────────────────────────────────────────────
// MOVEMENT — backward (used for return trip if needed)
// ─────────────────────────────────────────────────────────────────
void moveBackwardDistance(float distance_mm) {
  long target = distanceToCounts(distance_mm);
  noInterrupts(); leftCount = 0; rightCount = 0; interrupts();

  unsigned long timeoutMs = (unsigned long)(distance_mm / 50.0) * 1000 + 3000;
  unsigned long startTime = millis();

  while (true) {
    long l, r;
    noInterrupts(); l = leftCount; r = rightCount; interrupts();

    if (l >= target && r >= target) break;
    if (millis() - startTime > timeoutMs) { Serial.println("Backward timeout"); break; }

    int lPwm = BASE_PWM, rPwm = BASE_PWM;

    if      (l > r + 5) { lPwm = BASE_PWM - 10; rPwm = BASE_PWM + 10; }
    else if (r > l + 5) { lPwm = BASE_PWM + 10; rPwm = BASE_PWM - 10; }

    if (l > target * 0.8) lPwm = min(lPwm, BASE_PWM / 2);
    if (r > target * 0.8) rPwm = min(rPwm, BASE_PWM / 2);

    if (l < target) setLeftBackward(lPwm);  else stopLeft();
    if (r < target) setRightBackward(rPwm); else stopRight();
  }
  stopAll();
}

// ─────────────────────────────────────────────────────────────────
// MOVEMENT — in-place turn
// ─────────────────────────────────────────────────────────────────
// Positive angle_deg = clockwise (right turn) when viewed from above
// Negative angle_deg = counter-clockwise (left turn)
//
// Accuracy depends on WHEELBASE_MM being correct.
// Calibrate: command a 90° turn, measure actual rotation with a protractor,
// then adjust WHEELBASE_MM until 90° command = 90° actual.
void turnByAngle(float angle_deg) {
  long target = angleToCounts(angle_deg);
  noInterrupts(); leftCount = 0; rightCount = 0; interrupts();

  unsigned long timeoutMs = 5000;
  unsigned long startTime = millis();

  while (true) {
    long l, r;
    noInterrupts(); l = leftCount; r = rightCount; interrupts();

    if (l >= target && r >= target) break;
    if (millis() - startTime > timeoutMs) { Serial.println("Turn timeout"); break; }

    int lPwm = BASE_PWM, rPwm = BASE_PWM;

    // Slow down near end of turn
    if (l > target * 0.8) lPwm = min(lPwm, BASE_PWM / 2);
    if (r > target * 0.8) rPwm = min(rPwm, BASE_PWM / 2);

    if (angle_deg > 0) {
      // Clockwise: left wheel forward, right wheel backward
      if (l < target) setLeftForward(lPwm);   else stopLeft();
      if (r < target) setRightBackward(rPwm); else stopRight();
    } else {
      // Counter-clockwise: left wheel backward, right wheel forward
      if (l < target) setLeftBackward(lPwm);  else stopLeft();
      if (r < target) setRightForward(rPwm);  else stopRight();
    }
  }
  stopAll();
  currentAngleDeg += angle_deg;
}

// ─────────────────────────────────────────────────────────────────
// NAVIGATION SEQUENCES
// ─────────────────────────────────────────────────────────────────

// Executes a full go_to command:
//   1. Turn to heading
//   2. Drive forward to target distance
//   3. Read DHT22
//   4. POST humidity/temperature to server — server determines fire_detected
void executeGoTo(float angleDeg, float distMm) {
  Serial.println("go_to: angle=" + String(angleDeg) + "deg  dist=" + String(distMm) + "mm");
  lastTraveledMm = distMm;

  // Step 1: turn to heading (skip if angle is negligible)
  if (abs(angleDeg) > 1.0) {
    Serial.println("Turning...");
    turnByAngle(angleDeg);
    postTelemetry("investigating");
    delay(300);
  }

  // Step 2: drive to target
  Serial.println("Driving...");
  moveForwardDistance(distMm);
  postTelemetry("investigating");
  delay(300);

  // Step 3: read DHT22 — wait 2 seconds first; sensor needs settling time
  Serial.println("Reading DHT22...");
  delay(2000);
  float humidity    = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("DHT22 read failed — check wiring and pull-up resistor");
    // Post telemetry with error status so dashboard reflects this
    postToServer("/api/car/telemetry",
      "{\"status\":\"sensor_error\""
      ",\"angle_deg\":"   + String(currentAngleDeg, 1) +
      ",\"distance_mm\":" + String(currentDistanceMm, 1) + "}");
  } else {
    Serial.println("Humidity: "    + String(humidity)    + "%");
    Serial.println("Temperature: " + String(temperature) + "C");
    postSensor(humidity, temperature);
  }
}

// Executes a return_home command:
//   1. Turn 180° to face home
//   2. Drive the same distance back
//   3. Realign to original heading
void executeReturnHome() {
  Serial.println("Returning home");
  postTelemetry("returning");

  // Turn to face home
  turnByAngle(180.0);
  delay(300);

  // Drive home — car is now facing the return direction, so forward = toward home
  moveForwardDistance(lastTraveledMm);
  delay(300);

  // Realign to original heading (0°).
  // After the outbound trip + 180° turn, currentAngleDeg = originalAngle + 180.
  // Turning by -currentAngleDeg returns us to 0°.
  if (abs(currentAngleDeg) > 1.0) {
    turnByAngle(-currentAngleDeg);
  }

  currentAngleDeg   = 0.0;
  currentDistanceMm = 0.0;
  postTelemetry("home");
  Serial.println("Home");
}

// ─────────────────────────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Car firmware starting...");

  // Motor pins
  pinMode(L_AIN1, OUTPUT); pinMode(L_AIN2, OUTPUT); pinMode(L_SLP, OUTPUT);
  pinMode(R_AIN1, OUTPUT); pinMode(R_AIN2, OUTPUT); pinMode(R_SLP, OUTPUT);
  digitalWrite(L_SLP, HIGH);  // enable motor driver boards
  digitalWrite(R_SLP, HIGH);

  // Encoder pins + interrupts
  pinMode(L_ENCA, INPUT_PULLUP);
  pinMode(R_ENCA, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(L_ENCA), leftEncoderISR, RISING);
  attachInterrupt(digitalPinToInterrupt(R_ENCA), rightEncoderISR, RISING);

  analogWriteFreq(20000);
  analogWriteRange(255);

  // DHT22
  dht.begin();

  // WiFi
  WiFi.begin(SSID, PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.print("Connected. IP: ");
  Serial.println(WiFi.localIP());  // open Serial Monitor to read this

  postToServer("/api/heartbeat", "{\"device_id\":\"car\"}");
  Serial.println("Car ready — polling for commands");
}

// ─────────────────────────────────────────────────────────────────
// MAIN LOOP — polls server for commands, sends periodic heartbeats
// ─────────────────────────────────────────────────────────────────
void loop() {
  unsigned long now = millis();

  // Heartbeat — keeps the device marked ONLINE on the dashboard
  if (now - lastHeartbeatMs > HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = now;
    postToServer("/api/heartbeat", "{\"device_id\":\"car\"}");
  }

  // Poll server for command
  if (now - lastPollMs > POLL_INTERVAL_MS) {
    lastPollMs = now;

    String type, issuedAt;
    float angleDeg = 0, distMm = 0;

    if (fetchCommand(type, angleDeg, distMm, issuedAt)) {
      // issuedAt acts as a command ID — only execute each command once
      bool isNew = (issuedAt.length() > 0 && issuedAt != lastCommandIssuedAt);

      if (isNew) {
        if (type == "go_to") {
          lastCommandIssuedAt = issuedAt;
          executeGoTo(angleDeg, distMm);
        } else if (type == "return_home") {
          lastCommandIssuedAt = issuedAt;
          executeReturnHome();
        }
        // type == "idle": do nothing
      }
    }
  }
}

#include <RH_ASK.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ── Configuration — fill in before uploading ────────────────────
const char* SSID      = "YOUR_WIFI_SSID";
const char* PASSWORD  = "YOUR_WIFI_PASSWORD";
const char* SERVER_IP = "192.168.x.x";    // your PC's LAN IP (run ipconfig to find it)

// ── Hardware ─────────────────────────────────────────────────────
const int LED_PIN = 15;

// RH_ASK(speed, rxPin, txPin, pttPin, pttInverted)
// Receiver uses GPIO 16; txPin unused (255)
RH_ASK driver(2000, 16, 255, 255, false);

// ── Debounce: ignore duplicate Fire signals within this window ───
const unsigned long FIRE_COOLDOWN_MS = 2000;
unsigned long lastFireTime = 0;

// ── Heartbeat timing ─────────────────────────────────────────────
const unsigned long HEARTBEAT_INTERVAL_MS = 10000;
unsigned long lastHeartbeatMs = 0;

// ── LED non-blocking timer ───────────────────────────────────────
unsigned long ledOffTime = 0;
bool ledActive = false;

// ─────────────────────────────────────────────────────────────────
// HTTP helper — posts JSON body to a server path
// ─────────────────────────────────────────────────────────────────
void postToServer(const char* path, const char* body) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String("http://") + SERVER_IP + ":5000" + path);
  http.addHeader("Content-Type", "application/json");
  http.POST(body);
  http.end();
}

// ─────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Connect to WiFi
  WiFi.begin(SSID, PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.print("Connected. IP: ");
  Serial.println(WiFi.localIP());  // open Serial Monitor to read this

  // Initialise RF driver
  if (!driver.init()) {
    Serial.println("RF driver init failed — check wiring");
  } else {
    Serial.println("RF receiver ready");
  }
}

// ─────────────────────────────────────────────────────────────────
void loop() {
  uint8_t buf[RH_ASK_MAX_MESSAGE_LEN];
  uint8_t buflen = sizeof(buf);

  // Check for incoming RF message
  if (driver.recv(buf, &buflen)) {
    if (strcmp((char*)buf, "Fire") == 0) {
      unsigned long now = millis();

      // Debounce: the transmitter sends "Fire" 5× in rapid succession;
      // only forward the first one to the server within the cooldown window
      if (now - lastFireTime > FIRE_COOLDOWN_MS) {
        lastFireTime = now;

        Serial.println("Fire signal received — notifying server");
        postToServer("/api/lightning", "{\"signal\":\"Fire\"}");

        // Visual indicator
        digitalWrite(LED_PIN, HIGH);
        ledActive  = true;
        ledOffTime = millis() + 1000;
      }
    }
  }

  // Turn LED off after 1 second
  if (ledActive && millis() > ledOffTime) {
    digitalWrite(LED_PIN, LOW);
    ledActive = false;
  }

  // Periodic heartbeat so the dashboard keeps the device marked online
  if (millis() - lastHeartbeatMs > HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = millis();
    postToServer("/api/heartbeat", "{\"device_id\":\"receiver\"}");
  }
}

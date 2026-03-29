# Mechatronics Notes — Issues & Action Items

This file tracks hardware/firmware gaps identified during server development.
Work through these before integration testing.

---

## 1. Lightning Control / Receiver

### CRITICAL — `driver.init()` is commented out
**File:** `Lightning Control/Reciever`
Line 11:
```cpp
// driver.init();
```
This line must be uncommented. Without it, the RF receiver never initializes and
no messages will ever be received.

---

### MISSING — HTTP POST to server on signal detection
The current code only blinks an LED. After detecting "Fire", the Pico W needs to
POST to the Flask server at `/api/lightning`.

Since this is a Pico W running the Arduino framework, add WiFi + HTTP:

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* SSID       = "YOUR_WIFI_SSID";
const char* PASSWORD   = "YOUR_WIFI_PASSWORD";
const char* SERVER_IP  = "192.168.x.x";   // replace with your PC's LAN IP

// In setup():
WiFi.begin(SSID, PASSWORD);
while (WiFi.status() != WL_CONNECTED) delay(500);

// Replace the LED blink section with:
HTTPClient http;
http.begin(String("http://") + SERVER_IP + ":5000/api/lightning");
http.addHeader("Content-Type", "application/json");
http.POST("{\"signal\":\"Fire\"}");
http.end();
```

---

### MISSING — Heartbeat to server
The server marks each device offline after 15 seconds of silence.
Add a periodic POST to `/api/heartbeat` in the main loop:

```cpp
// Every ~10 seconds:
HTTPClient http;
http.begin(String("http://") + SERVER_IP + ":5000/api/heartbeat");
http.addHeader("Content-Type", "application/json");
http.POST("{\"device_id\":\"receiver\"}");
http.end();
```

---

### NOTE — Duplicate signal debouncing
The transmitter already sends "Fire" 5 times in rapid succession for reliability.
Add a cooldown on the receiver side to avoid logging 5 separate events for one
button press. A simple approach:

```cpp
unsigned long lastFireTime = 0;
const unsigned long FIRE_COOLDOWN_MS = 2000;

// Before POSTing to server, check:
if (millis() - lastFireTime > FIRE_COOLDOWN_MS) {
    lastFireTime = millis();
    // POST to server
}
```

---

## 2. Motor Control / Robot Car

### MISSING — Turn function (required for polar coordinate navigation)
The server sends `{"type": "go_to", "target": {"angle_deg": X, "distance_mm": Y}}`.
The car's navigation sequence must be:
1. Turn in place by `angle_deg`
2. Drive forward `distance_mm`
3. Read DHT22, POST sensor data
4. Wait for `return_home` command

No `turnByAngle()` function exists. A differential turn approach:
- Left motor backward, right motor forward (or vice versa) for turning
- Use encoder counts to estimate angle turned

The encoder count for a 360° in-place turn:
```
counts_for_360 = (PI * WHEELBASE_MM) / WHEEL_CIRCUMFERENCE * COUNTS_PER_REV
```
You need to measure `WHEELBASE_MM` (distance between wheel contact points on your
specific car). Then scale linearly for any angle.

---

### MISSING — Return-home movement
When the server sends `{"type": "return_home"}`, the car needs to:
1. Turn 180°
2. Drive the same `distance_mm` it originally travelled
3. Turn back to 0° (facing original direction)

The car should track its total travelled distance and remember it for the return
trip. The server also sends telemetry (`/api/car/telemetry`) during travel so the
operator can monitor progress.

---

### MISSING — WiFi + HTTP integration on the car
The car Pico W needs to:

```
Loop:
  1. GET /api/car/command  every ~500ms
     → if type == "go_to":   execute navigation sequence
     → if type == "return_home": execute return sequence

  2. While moving: POST /api/car/telemetry  every ~500ms
     body: {"angle_deg": <current>, "distance_mm": <current>, "status": "investigating"}

  3. On arrival: POST /api/car/sensor
     body: {"humidity_pct": <reading>, "temperature_c": <reading>}

  4. POST /api/heartbeat  every ~10s
     body: {"device_id": "car"}
```

---

### MISSING — DHT22 sensor code
There is no DHT22 code in `Motor Control/Motor Spin`.

```cpp
#include <DHT.h>

#define DHT_PIN  2        // pick an available GPIO pin
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

// In setup():
dht.begin();

// At the target location:
float humidity    = dht.readHumidity();
float temperature = dht.readTemperature();

if (isnan(humidity) || isnan(temperature)) {
    // Sensor read failed — retry or report error
} else {
    // POST to /api/car/sensor
}
```

Make sure `DHT_PIN` is not already used by a motor driver or encoder pin.
Current motor pins: 11, 12, 13, 14, 17, 18, 19, 20 — avoid those.

---

### WARNING — Encoder constants need hardware verification
```cpp
const float WHEEL_CIRCUMFERENCE = 210.63; // mm  (assumes 67mm diameter)
const float COUNTS_PER_REV      = 823.1;
```
These must match your actual hardware. Verify by:
1. Spinning one wheel exactly one full rotation by hand and counting encoder pulses
   via Serial output.
2. Measuring the actual wheel circumference with a tape measure.

If these are wrong, all distance-based movement will be off.

---

### WARNING — 8-second timeout in `moveForwardDistance()`
The hardcoded 8-second timeout will cut off travel prematurely for distances
over ~400–500mm (depending on speed). Make it proportional to distance:

```cpp
unsigned long timeout_ms = (unsigned long)(distanceMM / 50.0) * 1000 + 3000;
// ~20mm/s assumed speed + 3s buffer — tune to your actual motor speed
```

---

### NOTE — Motor board must be TARGET: Pico W
In your Arduino/PlatformIO board selection, confirm you are targeting
`raspberry-pi-pico-w` (not `raspberry-pi-pico`). WiFi.h is only available on
the W variant.

---

## 3. Transmitter (Lightning Control)

The transmitter code looks functionally correct for the prototype:
- INPUT_PULLUP + falling-edge detection for the button is correct
- Sending "Fire" 5× for redundancy is good practice
- Baud rate (2000) matches the receiver

No changes needed here. This runs on a regular Pico (no WiFi required).

---

## 4. Coordinate System Summary

The server uses **polar coordinates measured from home base**:

| Field         | Meaning                                               |
|---------------|-------------------------------------------------------|
| `angle_deg`   | Degrees to turn in place before driving (0 = forward) |
| `distance_mm` | Millimetres to drive forward after turning            |

The return trip is the reverse:
1. Turn 180°
2. Drive same `distance_mm`
3. Turn -180° (back to original heading)

If your test arena uses a fixed straight-line path, `angle_deg` will always be 0
for your prototype runs, which simplifies things until turning is implemented.

---

## 5. Integration Test Checklist (suggested order)

- [ ] Verify encoder counts per revolution match actual hardware
- [ ] Verify `driver.init()` uncommented in receiver — LED blinks on test signal
- [ ] Receiver connects to WiFi and POSTs to `/api/lightning` successfully
- [ ] Server dashboard shows Receiver as ONLINE
- [ ] Car connects to WiFi, polls `/api/car/command`, heartbeat works
- [ ] Server dashboard shows Car as ONLINE
- [ ] Manual "Send Car" from dashboard issues correct `go_to` command
- [ ] Car drives `distance_mm` and stops (forward movement only, `angle_deg = 0`)
- [ ] Car reads DHT22 and POSTs to `/api/car/sensor`
- [ ] Fire/no-fire result shows on dashboard
- [ ] End-to-end: button press → RF signal → lightning event → manual dispatch → car travels → result displayed
- [ ] Repeat end-to-end with AUTO_DISPATCH = True

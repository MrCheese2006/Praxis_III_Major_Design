# Setup Guide — First-Time Configuration

This guide walks through everything needed to get the full system running:
the Flask server on your PC, the Receiver Pico W, and the Robot Car Pico W.

---

## Part 1 — Flask Server (Your PC)

### 1.1 Install Python
Download from https://www.python.org/downloads/ (3.10 or newer).
During install, check **"Add Python to PATH"**.

Verify in a terminal:
```
python --version
```

### 1.2 Install Flask
Open a terminal and run:
```
pip install flask
```

### 1.3 Find your PC's LAN IP address
This is the IP address you will hard-code into the Pico W firmware so they know
where to send data.

**On Windows:**
1. Open Command Prompt (`Win + R` → type `cmd` → Enter)
2. Run: `ipconfig`
3. Look for the section matching your connection type:
   - If on Wi-Fi:   `Wireless LAN adapter Wi-Fi`
   - If on Ethernet: `Ethernet adapter Ethernet`
4. Copy the **IPv4 Address** (e.g. `192.168.1.105`)

> Important: this IP can change if your router reassigns it. For reliable
> development, consider setting a static IP on your router (DHCP reservation)
> or use your PC's hostname. For a quick prototype, just re-check with
> `ipconfig` each session if anything stops connecting.

### 1.4 Run the server
Navigate to the Server folder and run:
```
cd "path\to\Praxis_III_Major_Design\Server"
python app.py
```

You should see:
```
  Dashboard: http://localhost:5000
  LAN:       http://<your-ip>:5000
```

Open `http://localhost:5000` in a browser to verify the dashboard loads.
Both Pico Ws will connect to `http://<your-ip>:5000`.

---

## Part 2 — Arduino IDE Setup (applies to both Pico Ws)

### 2.1 Install Arduino IDE
Download Arduino IDE 2.x from https://www.arduino.cc/en/software

### 2.2 Add Raspberry Pi Pico W board support
The Arduino IDE does not include Pico W support by default. Add it:

1. Open Arduino IDE
2. Go to **File → Preferences**
3. Find the field **"Additional boards manager URLs"**
4. Paste this URL:
   ```
   https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
   ```
5. Click OK
6. Go to **Tools → Board → Boards Manager**
7. Search for `pico`
8. Find **"Raspberry Pi Pico/RP2040 by Earle F. Philhower"** and click **Install**
   (this takes a few minutes)

### 2.3 Select the correct board
**This step is critical — the Pico W and regular Pico look identical but the W
has WiFi and must be selected for wireless communication to work.**

1. Go to **Tools → Board → Raspberry Pi RP2040 Boards**
2. Select **"Raspberry Pi Pico W"** for any board that needs WiFi
   (Receiver Pico W, Robot Car Pico W)
3. Select **"Raspberry Pi Pico"** for the transmitter (regular Pico, no WiFi)

### 2.4 Upload firmware to a Pico W
1. Hold the **BOOTSEL** button on the Pico W
2. While holding, plug it into your PC via USB
3. Release BOOTSEL — it will appear as a USB drive
4. In Arduino IDE, select the correct port under **Tools → Port**
5. Click the **Upload** button (right arrow icon)

---

## Part 3 — Installing C/C++ Libraries

Libraries extend what your Arduino sketch can do (read sensors, use RF modules, etc.).
They are installed through the Arduino IDE's Library Manager.

### How to open the Library Manager
- **Tools → Manage Libraries** (or `Ctrl + Shift + I`)
- A panel opens. Use the search bar to find libraries by name.
- Click **Install** next to the library. If it asks "Install all dependencies?" — click Yes.

### Libraries needed for this project

#### For the Transmitter and Receiver (RF communication)
| Library | Search term | Author |
|---------|-------------|--------|
| RadioHead | `RadioHead` | Mike McCauley |

> RadioHead provides the `RH_ASK` driver used in the existing transmitter/receiver code.
> Install it on the PC that programs **both** the transmitter Pico and the receiver Pico W.

#### For the Robot Car Pico W (DHT22 sensor)
| Library | Search term | Author |
|---------|-------------|--------|
| DHT sensor library | `DHT sensor library` | Adafruit |
| Adafruit Unified Sensor | `Adafruit Unified Sensor` | Adafruit |

> Install both. DHT sensor library depends on Adafruit Unified Sensor.
> The Library Manager will usually prompt you to install dependencies automatically.

#### WiFi and HTTP (built-in — no install needed)
The `WiFi.h` and `HTTPClient.h` headers are included automatically when you select
the Pico W board. You do not need to install anything extra for WiFi.

---

## Part 4 — Finding Pico W IP Addresses

When a Pico W connects to WiFi, your router assigns it an IP address dynamically.
You need this IP if you ever want to connect to the Pico W directly (not needed for
this project — the Pico Ws connect *to* the server, not the other way around).

### Method 1 — Print to Serial (easiest)
Add this after the WiFi connection code in your sketch:

```cpp
Serial.begin(115200);
WiFi.begin(SSID, PASSWORD);
while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
}
Serial.println();
Serial.print("Connected. IP: ");
Serial.println(WiFi.localIP());
```

Open **Tools → Serial Monitor** in Arduino IDE (baud rate 115200) and the IP
will print when the board boots.

### Method 2 — Check your router
1. Log into your router admin page (usually `192.168.1.1` or `192.168.0.1`)
2. Look for "Connected Devices", "DHCP Clients", or "LAN" section
3. Devices will show as "raspberrypi" or similar

### Method 3 — Dashboard
Once the Pico Ws are running their firmware and calling `/api/heartbeat`,
their IP addresses appear automatically on the dashboard under each device card.
This is the easiest method once firmware is working.

---

## Part 5 — Wiring Quick Reference

### Receiver Pico W
| Component | Pico W Pin |
|-----------|-----------|
| RF Receiver DATA | GPIO 16 |
| LED (signal indicator) | GPIO 15 |
| RF Receiver VCC | 3.3V |
| RF Receiver GND | GND |

### Robot Car Pico W
| Component | Pico W Pin |
|-----------|-----------|
| Left motor AIN1 | GPIO 12 |
| Left motor AIN2 | GPIO 13 |
| Left motor SLP | GPIO 14 |
| Left encoder | GPIO 11 |
| Right motor AIN1 | GPIO 19 |
| Right motor AIN2 | GPIO 18 |
| Right motor SLP | GPIO 17 |
| Right encoder | GPIO 20 |
| DHT22 DATA | GPIO 2 (suggested — not conflicting) |
| DHT22 VCC | 3.3V |
| DHT22 GND | GND |

> Pin numbers are from the existing Motor Spin code. Verify against your actual
> wiring before uploading firmware.

---

## Part 6 — First Boot Checklist

Work through this in order. Each step depends on the previous one.

**Server**
- [ ] `pip install flask` succeeded
- [ ] `python app.py` runs without errors
- [ ] Dashboard loads at `http://localhost:5000`
- [ ] PC LAN IP noted (from `ipconfig`)

**Arduino IDE**
- [ ] Pico/RP2040 board package installed
- [ ] RadioHead library installed
- [ ] DHT sensor library + Adafruit Unified Sensor installed

**Receiver Pico W**
- [ ] Board set to "Raspberry Pi Pico W" in Arduino IDE
- [ ] `driver.init()` uncommented in Reciever.cpp
- [ ] WiFi credentials + server IP added to firmware
- [ ] Uploaded and connects to WiFi (IP prints to Serial Monitor)
- [ ] Dashboard shows Receiver as ONLINE
- [ ] Pressing transmitter button → lightning event appears on dashboard

**Robot Car Pico W**
- [ ] Board set to "Raspberry Pi Pico W" in Arduino IDE
- [ ] `WHEELBASE_MM` measured and updated in `Motor Spin.cpp`
- [ ] WiFi credentials + server IP added to `Motor Spin.cpp`
- [ ] Uploaded and connects to WiFi (IP prints to Serial Monitor)
- [ ] Dashboard shows Car as ONLINE
- [ ] "Send Car" button on dashboard → car receives `go_to` command (check Serial Monitor)

---

## Part 7 — Common Errors

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: flask` | Flask not installed | `pip install flask` |
| Device shows OFFLINE on dashboard | Heartbeat not being sent, or WiFi not connected | Check Serial Monitor on Pico W |
| RF receiver gets no messages | `driver.init()` commented out | Uncomment line 11 in Reciever.cpp |
| Pico W won't connect to WiFi | Wrong SSID/password, or 5GHz network | Pico W only supports 2.4GHz WiFi |
| Arduino IDE can't find Pico W port | Driver not installed | Install Zadig USB driver (google "Zadig RP2040") |
| `WiFi.h` not found | Wrong board selected | Make sure board is set to Pico W, not Pico |
| DHT22 reads `nan` | Bad wiring or missing pull-up resistor | DHT22 data pin needs a 10kΩ pull-up to 3.3V |
| Server IP unreachable from Pico W | PC firewall blocking port 5000 | Allow port 5000 in Windows Firewall, or temporarily disable firewall for testing |

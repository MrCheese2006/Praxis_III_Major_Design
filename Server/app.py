"""
Control Center Server — Unified Flask Backend
Connects: Receiver Pico W, Robot Car Pico W, Auxiliary Pico W

Run:      python app.py
Dashboard: http://localhost:5000
LAN:       http://<your-ip>:5000

Supersedes: flask_server.py, flask_server_remote_control.py
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime
import threading
import time

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────
FIRE_HUMIDITY_THRESHOLD = 30.0   # % RH — below this = fire risk
DEVICE_TIMEOUT_SECONDS  = 15     # seconds of silence before device = offline
MAX_LOG_ENTRIES         = 50
MAX_LIGHTNING_EVENTS    = 20

# Auto-dispatch toggle — uncomment ONE:
AUTO_DISPATCH = False   # Manual: operator clicks "Send Car" on dashboard
# AUTO_DISPATCH = True  # Automatic: car dispatched on every lightning event

# Default target coordinates (polar, from home base)
#   angle_deg:   degrees to turn in place before driving
#   distance_mm: how far forward to drive after turning
DEFAULT_TARGET = {"angle_deg": 0.0, "distance_mm": 1000.0}

# ─────────────────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────────────────
_lock = threading.Lock()

# Registry of known Pico W devices.
# "aux" is the third Pico W slot — purpose to be determined by team.
devices = {
    "receiver": {"last_seen": None, "ip": None, "online": False},
    "car":      {"last_seen": None, "ip": None, "online": False},
    "aux":      {"last_seen": None, "ip": None, "online": False},
}

lightning_events = []  # [{"timestamp", "signal", "rssi"}]

car_state = {
    "status":        "idle",   # idle | dispatched | investigating | returning | home | fire_alert
    "position":      {"angle_deg": 0.0, "distance_mm": 0.0},
    "target":        DEFAULT_TARGET.copy(),
    "humidity_pct":  None,
    "temperature_c": None,
    "fire_detected": None,      # None = unknown, True = fire risk, False = clear
    "last_updated":  None,
}

# Single pending command for the car — polled via GET /api/car/command
car_command = {
    "type":      "idle",        # idle | go_to | return_home
    "target":    DEFAULT_TARGET.copy(),
    "issued_at": None,
}

system_log = []   # [{timestamp, message}] — shown on dashboard

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str):
    entry = {"timestamp": _now(), "message": msg}
    with _lock:
        system_log.append(entry)
        if len(system_log) > MAX_LOG_ENTRIES:
            system_log.pop(0)
    print(f"[{entry['timestamp']}] {msg}")


def _mark_online(device_id: str):
    """Called on any request from a Pico W to keep it marked online."""
    with _lock:
        if device_id in devices:
            devices[device_id]["last_seen"] = datetime.now()
            devices[device_id]["ip"]        = request.remote_addr
            devices[device_id]["online"]    = True


def _dispatch_car(target: dict):
    """Issue a go_to command and reset fire state."""
    with _lock:
        car_command.update({
            "type":      "go_to",
            "target":    target.copy(),
            "issued_at": _now(),
        })
        car_state["status"]        = "dispatched"
        car_state["fire_detected"] = None


def _watchdog():
    """Background thread — marks devices offline after DEVICE_TIMEOUT_SECONDS of silence."""
    while True:
        now = datetime.now()
        with _lock:
            for dev in devices.values():
                if dev["last_seen"] is not None:
                    elapsed = (now - dev["last_seen"]).total_seconds()
                    dev["online"] = elapsed < DEVICE_TIMEOUT_SECONDS
        time.sleep(5)


# ─────────────────────────────────────────────────────────────────
# PICO W ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    """
    All Pico Ws POST here periodically to stay marked online.
    Recommended interval: every 10 seconds.

    Body: {"device_id": "receiver" | "car" | "aux"}
    """
    data      = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "")
    if device_id not in devices:
        return jsonify({"error": f"unknown device_id '{device_id}'"}), 400
    _mark_online(device_id)
    return jsonify({"status": "ok", "server_time": _now()})


@app.route("/api/lightning", methods=["POST"])
def lightning():
    """
    Receiver Pico W POSTs here when it receives the RF 'Fire' signal.

    Body: {"signal": "Fire", "rssi": <optional int>}

    If AUTO_DISPATCH is True, immediately issues go_to command to car.
    Otherwise, just logs the event for operator action.
    """
    _mark_online("receiver")
    data = request.get_json(silent=True) or {}

    event = {
        "timestamp": _now(),
        "signal":    data.get("signal", "Fire"),
        "rssi":      data.get("rssi"),
    }
    with _lock:
        lightning_events.append(event)
        if len(lightning_events) > MAX_LIGHTNING_EVENTS:
            lightning_events.pop(0)

    _log(f"Lightning/fire signal received from {request.remote_addr}")

    if AUTO_DISPATCH:
        with _lock:
            target = car_state["target"].copy()
        _dispatch_car(target)
        _log("Car auto-dispatched to target coordinates.")

    return jsonify({"status": "received"})


@app.route("/api/car/command", methods=["GET"])
def get_car_command():
    """
    Car Pico W polls this to check for a pending command.
    Recommended polling interval: every 500ms–1s.

    Returns: {"type": "idle"|"go_to"|"return_home", "target": {...}, "issued_at": "..."}
    """
    _mark_online("car")
    with _lock:
        cmd = {
            "type":      car_command["type"],
            "target":    car_command["target"].copy(),
            "issued_at": car_command["issued_at"],
        }
    return jsonify(cmd)


@app.route("/api/car/telemetry", methods=["POST"])
def car_telemetry():
    """
    Car Pico W POSTs its current polar position as it moves.
    Call periodically while in motion (e.g., every 500ms).

    Body: {"angle_deg": float, "distance_mm": float, "status": str (optional)}
    """
    _mark_online("car")
    data = request.get_json(silent=True) or {}
    with _lock:
        pos = car_state["position"]
        pos["angle_deg"]   = float(data.get("angle_deg",   pos["angle_deg"]))
        pos["distance_mm"] = float(data.get("distance_mm", pos["distance_mm"]))
        if "status" in data:
            car_state["status"] = data["status"]
        car_state["last_updated"] = _now()
    return jsonify({"status": "ok"})


@app.route("/api/car/sensor", methods=["POST"])
def car_sensor():
    """
    Car Pico W POSTs DHT22 readings after arriving at target location.
    Server computes fire_detected based on FIRE_HUMIDITY_THRESHOLD.

    Body: {"humidity_pct": float, "temperature_c": float}
    Returns: {"status": "ok", "fire_detected": bool|null}
    """
    _mark_online("car")
    data     = request.get_json(silent=True) or {}
    humidity = data.get("humidity_pct")
    temp     = data.get("temperature_c")
    fire     = (humidity < FIRE_HUMIDITY_THRESHOLD) if humidity is not None else None

    with _lock:
        car_state["humidity_pct"]  = humidity
        car_state["temperature_c"] = temp
        car_state["fire_detected"] = fire
        car_state["last_updated"]  = _now()
        if fire:
            car_state["status"] = "fire_alert"
        elif fire is False:
            car_state["status"] = "investigating"

    if fire is True:
        _log(f"FIRE RISK — humidity {humidity:.1f}% below threshold ({FIRE_HUMIDITY_THRESHOLD}%)")
    elif fire is False:
        _log(f"No fire risk — humidity {humidity:.1f}% at target location")

    return jsonify({"status": "ok", "fire_detected": fire})


# ─────────────────────────────────────────────────────────────────
# OPERATOR / UI ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@app.route("/api/dispatch", methods=["POST"])
def manual_dispatch():
    """
    Dashboard 'Send Car' button.
    Uses saved preset target if angle_deg / distance_mm are omitted.

    Body (optional): {"angle_deg": float, "distance_mm": float}
    """
    data = request.get_json(silent=True) or {}
    with _lock:
        target = {
            "angle_deg":   float(data.get("angle_deg",   car_state["target"]["angle_deg"])),
            "distance_mm": float(data.get("distance_mm", car_state["target"]["distance_mm"])),
        }
        car_state["target"] = target.copy()
    _dispatch_car(target)
    _log(f"Car manually dispatched — angle={target['angle_deg']}deg dist={target['distance_mm']}mm")
    return jsonify({"status": "dispatched", "target": target})


@app.route("/api/car/return", methods=["POST"])
def return_home():
    """Dashboard 'Return Home' button — issues return_home command to car."""
    with _lock:
        car_command.update({"type": "return_home", "issued_at": _now()})
        car_state["status"] = "returning"
    _log("Return-home command issued to car.")
    return jsonify({"status": "ok"})


@app.route("/api/target", methods=["POST"])
def set_target():
    """
    Dashboard 'Save Preset' — updates the stored default dispatch coordinates.
    These are used when Send Car is pressed without custom coordinates.

    Body: {"angle_deg": float, "distance_mm": float}
    """
    data = request.get_json(silent=True) or {}
    with _lock:
        if "angle_deg" in data:
            car_state["target"]["angle_deg"]   = float(data["angle_deg"])
            DEFAULT_TARGET["angle_deg"]        = float(data["angle_deg"])
        if "distance_mm" in data:
            car_state["target"]["distance_mm"] = float(data["distance_mm"])
            DEFAULT_TARGET["distance_mm"]      = float(data["distance_mm"])
    _log(
        f"Target preset saved — "
        f"angle={DEFAULT_TARGET['angle_deg']}deg  "
        f"dist={DEFAULT_TARGET['distance_mm']}mm"
    )
    return jsonify({"status": "ok", "target": DEFAULT_TARGET})


@app.route("/api/status", methods=["GET"])
def status():
    """
    Full system snapshot — polled by the dashboard every 2 seconds.
    Also useful for debugging from a browser or curl.
    """
    with _lock:
        devs_out = {}
        for k, v in devices.items():
            devs_out[k] = {
                "online":    v["online"],
                "ip":        v["ip"],
                "last_seen": v["last_seen"].strftime("%H:%M:%S") if v["last_seen"] else None,
            }
        return jsonify({
            "devices":          devs_out,
            "lightning_events": list(lightning_events[-10:]),
            "car":              car_state,
            "car_command":      car_command,
            "system_log":       list(system_log[-20:]),
            "auto_dispatch":    AUTO_DISPATCH,
            "fire_threshold":   FIRE_HUMIDITY_THRESHOLD,
        })


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ─────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=_watchdog, daemon=True).start()
    _log("Control center server started.")
    print("\n  Dashboard: http://localhost:5000")
    print("  LAN:       http://<your-ip>:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)

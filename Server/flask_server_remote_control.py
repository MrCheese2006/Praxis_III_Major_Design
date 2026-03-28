"""
flask_server.py
Remote control server for Pico W robot car.

Endpoints:
  POST /control   - Browser sends movement commands here
  GET  /command   - Pico W polls for latest command here
  GET  /status    - Returns current command state (for dashboard polling)

Run with:
  python flask_server.py

Then open http://localhost:5000 in your browser.
"""

from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ─── STATE ────────────────────────────────────────────────────────────────────
current_command = {
    "direction": "stop",
    "speed": 50,
    "timestamp": None,
}
command_log = []
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/control", methods=["POST"])
def receive_control():
    """Browser POSTs movement commands here."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    direction = data.get("direction", "stop")
    speed = int(data.get("speed", 50))
    speed = max(0, min(100, speed))

    current_command["direction"] = direction
    current_command["speed"] = speed
    current_command["timestamp"] = datetime.now().strftime("%H:%M:%S")

    command_log.append(f"[{current_command['timestamp']}] {direction.upper()} @ {speed}%")
    if len(command_log) > 10:
        command_log.pop(0)

    print(f"Command: {direction} @ {speed}%")
    return jsonify({"status": "ok"}), 200


@app.route("/command", methods=["GET"])
def send_command():
    """Pico W GETs the latest command here."""
    return jsonify({
        "direction": current_command["direction"],
        "speed": current_command["speed"],
    }), 200


@app.route("/status", methods=["GET"])
def status():
    """Dashboard polls this for live state."""
    return jsonify({
        "current": current_command,
        "log": command_log,
    }), 200


if __name__ == "__main__":
    print("=" * 50)
    print("  Robot Remote Control Server")
    print("=" * 50)
    print("  Dashboard:  open control_panel.html in browser")
    print("  Pico W GET: http://<your-pc-ip>:5000/command")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
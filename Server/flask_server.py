# 100.66.65.164

"""
flask_server.py
Local Flask server for Raspberry Pi Pico W communication.

Endpoints:
  POST /data    - Receives sensor data from Pico W (JSON)
  GET  /command - Serves the latest motor/servo command to Pico W (JSON)

Run with:
  python flask_server.py

Then visit http://localhost:5000 in your browser to control the servo.
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

# ─── STATE ────────────────────────────────────────────────────────────────────
# Latest sensor readings received from Pico W
sensor_data = {
    "sensor1": None,
    "sensor2": None,
    "last_updated": None,
}

# Current command to send to Pico W
# Change "angle" (0-180) to control the servo
pending_command = {
    "angle": 90  # Default: centre position
}
# ──────────────────────────────────────────────────────────────────────────────


# ─── PICO W ENDPOINTS ─────────────────────────────────────────────────────────

@app.route("/data", methods=["POST"])
def receive_data():
    """Pico W POSTs sensor readings here."""
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    sensor_data["sensor1"] = data.get("sensor1")
    sensor_data["sensor2"] = data.get("sensor2")
    sensor_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{sensor_data['last_updated']}] Received sensor data: {data}")
    return jsonify({"status": "ok"}), 200


@app.route("/command", methods=["GET"])
def send_command():
    """Pico W GETs the latest motor/servo command here."""
    print(f"Sending command: {pending_command}")
    return jsonify(pending_command), 200

# ──────────────────────────────────────────────────────────────────────────────


# ─── DASHBOARD (browser control panel) ───────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Pico W Dashboard</title>
  <meta http-equiv="refresh" content="5">  <!-- Auto-refresh every 5s -->
  <style>
    body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
    h1 { color: #c13b2b; }
    .card { background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 16px 0; }
    label { display: block; margin-bottom: 6px; font-weight: bold; }
    input[type=range] { width: 100%; }
    button { background: #c13b2b; color: white; border: none; padding: 10px 24px;
             border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 8px; }
    button:hover { background: #a02d20; }
    .value { font-size: 24px; font-weight: bold; color: #333; }
  </style>
</head>
<body>
  <h1>🤖 Pico W Control Panel</h1>

  <div class="card">
    <h2>📡 Sensor Readings</h2>
    <p><b>Sensor 1:</b> <span class="value">{{ sensor1 }}</span> V</p>
    <p><b>Sensor 2:</b> <span class="value">{{ sensor2 }}</span> V</p>
    <p style="color: #888">Last updated: {{ last_updated }}</p>
  </div>

  <div class="card">
    <h2>⚙️ Servo Control</h2>
    <form method="POST" action="/set_command">
      <label for="angle">Angle: <span id="angleVal">{{ current_angle }}</span>°</label>
      <input type="range" id="angle" name="angle" min="0" max="180"
             value="{{ current_angle }}"
             oninput="document.getElementById('angleVal').textContent = this.value">
      <br>
      <button type="submit">Set Servo Angle</button>
    </form>
  </div>
</body>
</html>
"""

DASHBOARD_HTML_2 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ROBOT CTRL</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #0a0c0f;
    --panel:    #0f1318;
    --border:   #1e2530;
    --accent:   #00ff88;
    --accent2:  #ff4444;
    --dim:      #2a3340;
    --text:     #c8d8e8;
    --muted:    #4a5a6a;
    --key-bg:   #141920;
    --key-active: #00ff88;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 16px;
    background-image:
      linear-gradient(rgba(0,255,136,0.015) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,136,0.015) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  /* ── HEADER ── */
  header {
    width: 100%;
    max-width: 780px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 14px;
    margin-bottom: 28px;
  }
  .logo {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 900;
    font-size: 2rem;
    letter-spacing: 0.15em;
    color: var(--accent);
    text-shadow: 0 0 24px rgba(0,255,136,0.4);
  }
  .logo span { color: var(--text); }
  .server-status {
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    color: var(--muted);
  }
  .server-status .dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent2);
    margin-right: 6px;
    transition: background 0.3s;
  }
  .server-status.online .dot { background: var(--accent); box-shadow: 0 0 6px var(--accent); }

  /* ── MAIN GRID ── */
  .grid {
    width: 100%;
    max-width: 780px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto;
    gap: 16px;
  }

  /* ── PANEL ── */
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 20px;
    position: relative;
  }
  .panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
    opacity: 0.4;
  }
  .panel-label {
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: var(--muted);
    margin-bottom: 16px;
    text-transform: uppercase;
  }

  /* ── D-PAD ── */
  .dpad-panel { grid-column: 1; grid-row: 1 / 3; }
  .dpad {
    display: grid;
    grid-template-columns: repeat(3, 72px);
    grid-template-rows: repeat(3, 72px);
    gap: 6px;
    margin: 0 auto;
    width: fit-content;
  }
  .key {
    background: var(--key-bg);
    border: 1px solid var(--dim);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    user-select: none;
    transition: all 0.08s ease;
    gap: 4px;
    position: relative;
    overflow: hidden;
  }
  .key::after {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--accent);
    opacity: 0;
    transition: opacity 0.08s;
  }
  .key.active, .key:active {
    border-color: var(--accent);
    box-shadow: 0 0 16px rgba(0,255,136,0.3), inset 0 0 12px rgba(0,255,136,0.08);
  }
  .key.active::after { opacity: 0.06; }
  .key.stop-key {
    background: #1a0f0f;
    border-color: #3a1515;
  }
  .key.stop-key.active, .key.stop-key:active {
    border-color: var(--accent2);
    box-shadow: 0 0 16px rgba(255,68,68,0.3);
  }
  .key-arrow {
    font-size: 1.4rem;
    color: var(--text);
    line-height: 1;
    position: relative; z-index: 1;
  }
  .key-label {
    font-size: 0.55rem;
    letter-spacing: 0.12em;
    color: var(--muted);
    position: relative; z-index: 1;
  }
  .key.active .key-arrow, .key:active .key-arrow { color: var(--accent); }
  .key.stop-key.active .key-arrow { color: var(--accent2); }
  .empty { visibility: hidden; }

  /* ── STATUS PANEL ── */
  .status-panel { grid-column: 2; grid-row: 1; }
  .direction-display {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 900;
    font-size: 3rem;
    letter-spacing: 0.1em;
    color: var(--accent);
    text-shadow: 0 0 20px rgba(0,255,136,0.3);
    margin-bottom: 8px;
    min-height: 3.5rem;
    transition: color 0.1s;
  }
  .direction-display.stop { color: var(--accent2); text-shadow: 0 0 20px rgba(255,68,68,0.3); }
  .speed-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
  }
  .speed-label { font-size: 0.65rem; letter-spacing: 0.15em; color: var(--muted); white-space: nowrap; }
  .speed-bar-track {
    flex: 1;
    height: 4px;
    background: var(--dim);
    position: relative;
  }
  .speed-bar-fill {
    height: 100%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    transition: width 0.15s ease;
    width: 50%;
  }
  .speed-value { font-size: 0.85rem; color: var(--text); width: 38px; text-align: right; }

  /* Speed slider */
  .slider-row { margin-top: 20px; }
  input[type=range] {
    -webkit-appearance: none;
    width: 100%;
    height: 3px;
    background: var(--dim);
    outline: none;
    cursor: pointer;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px; height: 16px;
    background: var(--accent);
    border-radius: 0;
    box-shadow: 0 0 8px var(--accent);
    cursor: pointer;
  }

  /* ── LOG PANEL ── */
  .log-panel { grid-column: 2; grid-row: 2; }
  .log-list {
    list-style: none;
    font-size: 0.72rem;
    color: var(--muted);
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 180px;
    overflow: hidden;
  }
  .log-list li { border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .log-list li:last-child { color: var(--text); }
  .log-list li span { color: var(--accent); }

  /* ── KEYBOARD HINT ── */
  .hint {
    margin-top: 20px;
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    color: var(--muted);
    text-align: center;
  }
  .hint b { color: var(--text); }

  /* ── PING INDICATOR ── */
  .ping {
    position: fixed;
    bottom: 20px; right: 20px;
    font-size: 0.6rem;
    letter-spacing: 0.1em;
    color: var(--muted);
  }
</style>
</head>
<body>

<header>
  <div class="logo">ROBOT<span>CTRL</span></div>
  <div class="server-status" id="serverStatus">
    <span class="dot"></span>CONNECTING
  </div>
</header>

<div class="grid">

  <!-- D-PAD -->
  <div class="panel dpad-panel">
    <div class="panel-label">// DIRECTIONAL CONTROL</div>
    <div class="dpad">
      <div class="empty"></div>
      <div class="key" id="key-forward" data-dir="forward">
        <div class="key-arrow">↑</div>
        <div class="key-label">W / ↑</div>
      </div>
      <div class="empty"></div>

      <div class="key" id="key-left" data-dir="left">
        <div class="key-arrow">←</div>
        <div class="key-label">A / ←</div>
      </div>
      <div class="key stop-key" id="key-stop" data-dir="stop">
        <div class="key-arrow">■</div>
        <div class="key-label">SPACE</div>
      </div>
      <div class="key" id="key-right" data-dir="right">
        <div class="key-arrow">→</div>
        <div class="key-label">D / →</div>
      </div>

      <div class="empty"></div>
      <div class="key" id="key-backward" data-dir="backward">
        <div class="key-arrow">↓</div>
        <div class="key-label">S / ↓</div>
      </div>
      <div class="empty"></div>
    </div>
  </div>

  <!-- STATUS -->
  <div class="panel status-panel">
    <div class="panel-label">// CURRENT STATE</div>
    <div class="direction-display stop" id="dirDisplay">STOP</div>
    <div class="speed-row">
      <div class="speed-label">SPD</div>
      <div class="speed-bar-track">
        <div class="speed-bar-fill" id="speedBar"></div>
      </div>
      <div class="speed-value" id="speedVal">50%</div>
    </div>
    <div class="slider-row">
      <div class="panel-label" style="margin-top:16px; margin-bottom:8px;">// SPEED</div>
      <input type="range" id="speedSlider" min="0" max="100" value="50">
    </div>
  </div>

  <!-- LOG -->
  <div class="panel log-panel">
    <div class="panel-label">// COMMAND LOG</div>
    <ul class="log-list" id="logList">
      <li>— waiting for input —</li>
    </ul>
  </div>

</div>

<div class="hint">
  <b>W A S D</b> or <b>ARROW KEYS</b> to move &nbsp;·&nbsp; <b>SPACE</b> to stop &nbsp;·&nbsp; slider to adjust speed
</div>

<div class="ping" id="ping"></div>

<script>
  const SERVER = 'http://localhost:5000';
  let speed = 50;
  let currentDir = 'stop';
  let activeKeys = new Set();

  // ── SEND COMMAND ──────────────────────────────────────────────────────────
  async function sendCommand(direction) {
    try {
      const t0 = performance.now();
      const res = await fetch(`${SERVER}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, speed }),
      });
      const ms = Math.round(performance.now() - t0);
      document.getElementById('ping').textContent = `PING ${ms}ms`;
      setServerStatus(res.ok);
      if (res.ok) updateUI(direction);
    } catch {
      setServerStatus(false);
    }
  }

  // ── POLL STATUS ───────────────────────────────────────────────────────────
  async function pollStatus() {
    try {
      const res = await fetch(`${SERVER}/status`);
      const data = await res.json();
      setServerStatus(true);
      updateLog(data.log);
    } catch {
      setServerStatus(false);
    }
  }
  setInterval(pollStatus, 2000);
  pollStatus();

  // ── UI UPDATES ────────────────────────────────────────────────────────────
  function updateUI(direction) {
    currentDir = direction;
    const disp = document.getElementById('dirDisplay');
    disp.textContent = direction.toUpperCase();
    disp.className = 'direction-display' + (direction === 'stop' ? ' stop' : '');

    document.querySelectorAll('.key').forEach(k => k.classList.remove('active'));
    const activeKey = document.getElementById(`key-${direction}`);
    if (activeKey) activeKey.classList.add('active');
  }

  function updateSpeedUI(val) {
    document.getElementById('speedBar').style.width = val + '%';
    document.getElementById('speedVal').textContent = val + '%';
    document.getElementById('speedSlider').value = val;
  }

  function updateLog(log) {
    const list = document.getElementById('logList');
    if (!log || log.length === 0) return;
    list.innerHTML = log.slice().reverse().map((entry, i) => {
      const parts = entry.match(/\[(.+?)\] (.+)/);
      if (!parts) return `<li>${entry}</li>`;
      return `<li><span>[${parts[1]}]</span> ${parts[2]}</li>`;
    }).join('');
  }

  function setServerStatus(online) {
    const el = document.getElementById('serverStatus');
    el.className = 'server-status' + (online ? ' online' : '');
    el.innerHTML = `<span class="dot"></span>${online ? 'SERVER ONLINE' : 'OFFLINE'}`;
  }

  // ── KEYBOARD ──────────────────────────────────────────────────────────────
  const keyMap = {
    'w': 'forward', 'ArrowUp': 'forward',
    's': 'backward', 'ArrowDown': 'backward',
    'a': 'left', 'ArrowLeft': 'left',
    'd': 'right', 'ArrowRight': 'right',
    ' ': 'stop',
  };

  document.addEventListener('keydown', e => {
    const dir = keyMap[e.key];
    if (!dir || activeKeys.has(e.key)) return;
    e.preventDefault();
    activeKeys.add(e.key);
    sendCommand(dir);
  });

  document.addEventListener('keyup', e => {
    const dir = keyMap[e.key];
    if (!dir) return;
    activeKeys.delete(e.key);
    // If no movement keys held, stop
    const movementKeys = ['w','s','a','d','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'];
    const anyHeld = movementKeys.some(k => activeKeys.has(k));
    if (!anyHeld && e.key !== ' ') sendCommand('stop');
  });

  // ── MOUSE / TOUCH ON BUTTONS ──────────────────────────────────────────────
  document.querySelectorAll('.key').forEach(key => {
    const dir = key.dataset.dir;
    key.addEventListener('mousedown', () => sendCommand(dir));
    key.addEventListener('touchstart', e => { e.preventDefault(); sendCommand(dir); });
    key.addEventListener('mouseup', () => { if (dir !== 'stop') sendCommand('stop'); });
    key.addEventListener('touchend', () => { if (dir !== 'stop') sendCommand('stop'); });
  });

  // ── SPEED SLIDER ──────────────────────────────────────────────────────────
  document.getElementById('speedSlider').addEventListener('input', e => {
    speed = parseInt(e.target.value);
    updateSpeedUI(speed);
    if (currentDir !== 'stop') sendCommand(currentDir);
  });

  // Init
  updateSpeedUI(50);
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def dashboard():
    return render_template_string(DASHBOARD_HTML,
        sensor1=f"{sensor_data['sensor1']:.3f}" if sensor_data["sensor1"] is not None else "—",
        sensor2=f"{sensor_data['sensor2']:.3f}" if sensor_data["sensor2"] is not None else "—",
        last_updated=sensor_data["last_updated"] or "No data yet",
        current_angle=pending_command["angle"]
    )

@app.route("/set_command", methods=["POST"])
def set_command():
    """Browser submits a new servo angle here."""
    angle = int(request.form.get("angle", 90))
    angle = max(0, min(180, angle))
    pending_command["angle"] = angle
    print(f"Command updated: angle={angle}")
    return dashboard()

# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Flask server...")
    print("Dashboard: http://localhost:5000")
    print("Pico POST endpoint: http://<your-pc-ip>:5000/data")
    print("Pico GET endpoint:  http://<your-pc-ip>:5000/command")
    # host="0.0.0.0" makes it accessible from other devices on your LAN
    app.run(host="0.0.0.0", port=5000, debug=True)
#!/usr/bin/env python3
"""Flask server for PiCar-X (Unit C) — runs on the Raspberry Pi.

Exposes sensor data and drive commands over HTTP so the AI agent
can reach the car via MCC tunnel (http://picar-x.staex:8080).

Start on RPi:
    python3 picar_server.py

MCC tunnel (run once, then agent uses DNS name):
    mcc create-tunnel --targets tcp:8080 --remote-node <picar-x-node-id>

Watch live from PC:
    curl http://picar-x.staex:8080/telemetry   # SSE stream
    ssh pi@picar-x.staex 'tail -f /tmp/picar.log'
"""

import json
import logging
import os
import time
from threading import Lock

from flask import Flask, Response, jsonify, request

from picarx import Picarx
from vilib import Vilib

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PORT = int(os.getenv("PICAR_PORT", "8080"))
DRIVE_SPEED_MAX = int(os.getenv("DRIVE_SPEED_MAX", "60"))   # 0-100 scale
DRIVE_ANGLE_MAX = int(os.getenv("DRIVE_ANGLE_MAX", "35"))   # degrees left/right
TELEMETRY_INTERVAL_S = float(os.getenv("TELEMETRY_INTERVAL", "1.0"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/picar.log"),
    ],
)
log = logging.getLogger("picar_server")

# ---------------------------------------------------------------------------
# Hardware init
# ---------------------------------------------------------------------------
px = Picarx()
# 0/0 is not optically dead-ahead on this unit's camera mount (mechanical, not
# a code issue) - 20/0 was found by live testing to point at the box in front
# of the car. Re-check with /camera/angle if the mount ever gets adjusted.
cam_pan, cam_tilt = 20, 0
px.set_cam_pan_angle(cam_pan)
px.set_cam_tilt_angle(cam_tilt)
Vilib.camera_start(vflip=False, hflip=False, size=(1280, 960))  # default 640x480 was too low-res for pyzbar to decode dense QR codes
Vilib.qrcode_detect_switch(True)
Vilib.display(local=False, web=True)  # live MJPEG stream at http://<rpi-ip>:9000/mjpg, for framing/positioning
time.sleep(0.5)  # give camera a moment to initialise


def read_qr():
    """Vilib updates this dict continuously in its own frame-processing thread;
    the default/no-detection value is the literal string "None", not Python None."""
    data = Vilib.detect_obj_parameter.get("qr_data")
    return data if data and data != "None" else None

drive_lock = Lock()
log.info("PiCar-X hardware initialised")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    # the order app (order_app_pc.py) runs on a different host:port and
    # fetches /ultrasonic + /camera/qr via JS - browsers block that
    # cross-origin without this header (images like the mjpg stream aren't
    # affected by CORS, which is why the camera worked but sensor data didn't).
    response.headers["Access-Control-Allow-Origin"] = "*"
    # POST endpoints (/drive, /camera/angle) with a JSON body are
    # "non-simple" cross-origin requests - browsers send an OPTIONS
    # preflight first and check for these two headers before allowing the
    # real POST through. Only setting Allow-Origin (above) covers GET but
    # silently blocks POST at the preflight stage.
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/health")
def health():
    return jsonify({"status": "ok", "t": time.time()})


@app.route("/ultrasonic")
def ultrasonic():
    """Read ultrasonic distance sensor. Returns distance in cm."""
    dist = px.get_distance()
    log.info("ultrasonic: %.1f cm", dist)
    return jsonify({"distance_cm": round(dist, 1), "t": time.time()})


@app.route("/camera/qr")
def camera_qr():
    """Read QR code from camera. Returns scanned string or null."""
    result = read_qr()
    log.info("qr: %s", result)
    return jsonify({"qr": result, "t": time.time()})


@app.route("/camera/angle", methods=["GET", "POST"])
def camera_angle():
    """
    Get/set camera pan/tilt.

    POST JSON body:
        pan   int   -35..35  (negative = left, positive = right)
        tilt  int   -35..35  (negative = down, positive = up)
    """
    global cam_pan, cam_tilt
    if request.method == "GET":
        return jsonify({"pan": cam_pan, "tilt": cam_tilt})

    body = request.get_json(force=True)
    cam_pan = max(-35, min(35, int(body.get("pan", cam_pan))))
    cam_tilt = max(-35, min(35, int(body.get("tilt", cam_tilt))))
    px.set_cam_pan_angle(cam_pan)
    px.set_cam_tilt_angle(cam_tilt)
    log.info("camera angle: pan=%d tilt=%d", cam_pan, cam_tilt)
    return jsonify({"ok": True, "pan": cam_pan, "tilt": cam_tilt})


@app.route("/dashboard")
def dashboard():
    """Live control/telemetry page: video feed, ultrasonic + QR readout, pan/tilt buttons."""
    mjpg_host = request.host.split(":")[0]
    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PiCar-X — Unit C Dashboard</title>
<style>
  body {{ margin:0; padding:16px; background:#111; color:#eee; font-family:system-ui,sans-serif; }}
  h1 {{ font-size:1.1rem; font-weight:600; margin:0 0 12px; }}
  .row {{ display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }}
  .video {{ max-width:100%; border:2px solid #333; border-radius:8px; }}
  .panel {{ background:#1b1b1b; border:1px solid #333; border-radius:8px; padding:12px 16px; min-width:200px; }}
  .stat {{ font-size:2rem; font-weight:700; margin:4px 0; }}
  .label {{ color:#888; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.04em; }}
  .qr-ok {{ color:#4ade80; }}
  .qr-none {{ color:#666; }}
  .dpad {{ display:grid; grid-template-columns:repeat(3,44px); grid-template-rows:repeat(3,44px); gap:6px; margin-top:8px; }}
  .dpad button {{ background:#2a2a2a; color:#eee; border:1px solid #444; border-radius:6px; font-size:1.1rem; cursor:pointer; }}
  .dpad button:hover {{ background:#3a3a3a; }}
  .dpad .center {{ background:#333; }}
  #angleReadout {{ font-size:0.85rem; color:#aaa; margin-top:6px; }}
  .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
  .dot.up {{ background:#4ade80; }}
  .dot.down {{ background:#f87171; }}
</style>
</head>
<body>
<h1>PiCar-X — Unit C Live Dashboard</h1>
<div class="row">
  <img class="video" src="http://{mjpg_host}:9000/mjpg" alt="live camera feed">

  <div class="panel">
    <div class="label"><span id="statusDot" class="dot down"></span>Status</div>
    <div id="statusText" style="margin-bottom:12px;">verbinde...</div>

    <div class="label">Ultraschall</div>
    <div class="stat" id="dist">— cm</div>

    <div class="label">QR-Code</div>
    <div class="stat" id="qr" style="font-size:1rem;" class="qr-none">—</div>

    <div class="label" style="margin-top:12px;">Kamera-Winkel</div>
    <div class="dpad">
      <div></div><button onclick="nudge(0,10)">▲</button><div></div>
      <button onclick="nudge(-10,0)">◀</button><button class="center" onclick="setAngle(20,0)">●</button><button onclick="nudge(10,0)">▶</button>
      <div></div><button onclick="nudge(0,-10)">▼</button><div></div>
    </div>
    <div id="angleReadout">pan=? tilt=?</div>
  </div>
</div>

<script>
let curPan = 20, curTilt = 0;

async function setAngle(pan, tilt) {{
  curPan = Math.max(-35, Math.min(35, pan));
  curTilt = Math.max(-35, Math.min(35, tilt));
  await fetch('/camera/angle', {{
    method: 'POST', headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{pan: curPan, tilt: curTilt}})
  }});
  document.getElementById('angleReadout').textContent = `pan=${{curPan}} tilt=${{curTilt}}`;
}}
function nudge(dPan, dTilt) {{ setAngle(curPan + dPan, curTilt + dTilt); }}

async function pollAngle() {{
  const r = await fetch('/camera/angle');
  const d = await r.json();
  curPan = d.pan; curTilt = d.tilt;
  document.getElementById('angleReadout').textContent = `pan=${{curPan}} tilt=${{curTilt}}`;
}}

async function poll() {{
  try {{
    const [distRes, qrRes] = await Promise.all([
      fetch('/ultrasonic'), fetch('/camera/qr')
    ]);
    const dist = await distRes.json();
    const qr = await qrRes.json();
    document.getElementById('dist').textContent = dist.distance_cm + ' cm';
    const qrEl = document.getElementById('qr');
    if (qr.qr) {{
      qrEl.textContent = qr.qr;
      qrEl.className = 'stat qr-ok';
    }} else {{
      qrEl.textContent = '— kein QR erkannt —';
      qrEl.className = 'stat qr-none';
    }}
    document.getElementById('statusDot').className = 'dot up';
    document.getElementById('statusText').textContent = 'verbunden';
  }} catch (e) {{
    document.getElementById('statusDot').className = 'dot down';
    document.getElementById('statusText').textContent = 'Verbindung verloren';
  }}
}}

pollAngle();
poll();
setInterval(poll, 500);
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/debug/qr_raw")
def debug_qr_raw():
    """Decode the current raw in-memory frame directly (no JPEG round-trip),
    to isolate whether JPEG compression is destroying QR detail."""
    from pyzbar import pyzbar
    import cv2
    cv2.imwrite("/tmp/qr_raw_debug.png", Vilib.flask_img)
    results = pyzbar.decode(Vilib.flask_img)
    return jsonify({
        "n_results": len(results),
        "data": [r.data.decode("utf-8", "replace") for r in results],
        "frame_shape": list(Vilib.flask_img.shape),
    })


@app.route("/debug/frame")
def debug_frame():
    """Return the current camera frame as a JPEG — for manual QR-framing checks."""
    import cv2
    ok, buf = cv2.imencode(".jpg", Vilib.flask_img)
    if not ok:
        return jsonify({"error": "no frame available yet"}), 503
    return Response(buf.tobytes(), mimetype="image/jpeg")


@app.route("/drive", methods=["POST"])
def drive():
    """
    Drive the car.

    JSON body:
        speed   int     0-60  (positive = forward, negative = backward)
        angle   int     -35..35  (negative = left, positive = right)
        duration_s  float   seconds to drive before auto-stop (0 = no auto-stop)
    """
    body = request.get_json(force=True)
    speed = int(body.get("speed", 0))
    angle = int(body.get("angle", 0))
    duration = float(body.get("duration_s", 0))

    speed = max(-DRIVE_SPEED_MAX, min(DRIVE_SPEED_MAX, speed))
    angle = max(-DRIVE_ANGLE_MAX, min(DRIVE_ANGLE_MAX, angle))

    log.info("drive: speed=%d angle=%d duration=%.1fs", speed, angle, duration)

    with drive_lock:
        px.set_dir_servo_angle(angle)
        if speed > 0:
            px.forward(speed)
        elif speed < 0:
            px.backward(abs(speed))
        else:
            px.stop()

        if duration > 0:
            time.sleep(duration)
            px.stop()
            log.info("drive: auto-stopped after %.1fs", duration)

    return jsonify({"ok": True, "speed": speed, "angle": angle, "duration_s": duration})


@app.route("/stop")
def stop():
    """Emergency stop — halts all motors immediately."""
    with drive_lock:
        px.stop()
    log.info("STOP")
    return jsonify({"ok": True})


@app.route("/telemetry")
def telemetry():
    """
    Server-Sent Events stream — ultrasonic + QR, every TELEMETRY_INTERVAL_S.

    Connect once and leave open; the AI agent or MCC stream viewer receives
    live sensor snapshots without polling individual endpoints.

    Example (from PC via MCC):
        curl http://picar-x.staex:8080/telemetry
    """
    def generate():
        log.info("SSE client connected")
        while True:
            dist = px.get_distance()
            qr = read_qr()
            payload = json.dumps({
                "distance_cm": round(dist, 1),
                "qr": qr,
                "t": time.time(),
            })
            log.info("telemetry: dist=%.1f cm  qr=%s", dist, qr)
            yield f"data: {payload}\n\n"
            time.sleep(TELEMETRY_INTERVAL_S)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("Starting PiCar-X server on port %d", PORT)
    log.info("Endpoints: /health  /ultrasonic  /camera/qr  /drive  /stop  /telemetry")
    # vilib sets FLASK_DEBUG=development as an import side effect, which would
    # otherwise enable Werkzeug's reloader — fatal here, since the reloader
    # re-execs this script in a child process that tries to open the camera
    # a second time while the parent still holds it (see vilib/vilib.py).
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False, use_reloader=False)

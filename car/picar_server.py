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
Vilib.camera_start(vflip=False, hflip=False)
time.sleep(0.5)  # give camera a moment to initialise

drive_lock = Lock()
log.info("PiCar-X hardware initialised")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


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
    result = Vilib.qr_coder_reader()
    log.info("qr: %s", result)
    return jsonify({"qr": result, "t": time.time()})


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
            qr = Vilib.qr_coder_reader()
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
    app.run(host="0.0.0.0", port=PORT, threaded=True)

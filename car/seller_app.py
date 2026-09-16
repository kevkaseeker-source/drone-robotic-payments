#!/usr/bin/env python3
"""Seller / car-operator app for RoboPay Unit C — live camera + ultrasonic
(reads picar_server.py directly, works over an MCC tunnel once
PICAR_SERVER_URL points at the tunnel's DNS name), drive + camera-angle
controls, the owner's Devnet wallet balance, and a link to the
Escrow-Release TX once the car has confirmed a delivery. Split out of the
old order_app_pc.py - this app never touches the buyer's or the car's
private keys, it only calls picar_server.py's HTTP API and reads the
shared order_state.json (written by buyer_app.py / car_main.py) for the
transaction history.

This is the foundation for the future Car Owner Solana Mobile dApp - same
picar_server.py endpoints, same read-only relationship to the wallets.

Env vars required: SELLER_USERNAME, SELLER_PASSWORD
Also needs PICAR_SERVER_URL (e.g. http://backend-server or http://192.168.178.84)
Run:
    venv\\Scripts\\python.exe seller_app.py
"""

import os

from flask import Flask, Response, jsonify

import robopay_common as common

PORT = int(os.getenv("SELLER_APP_PORT", "5002"))

app = Flask(__name__)
common.make_auth(app, "SELLER_USERNAME", "SELLER_PASSWORD")


@app.route("/")
def index():
    html = INDEX_HTML.replace("__PICAR_SERVER_URL__", common.PICAR_SERVER_URL)
    return Response(html, mimetype="text/html")


@app.route("/wallet")
def wallet():
    return jsonify({"pubkey": common.SELLER_PUBKEY, "sol": common.get_balance_sol(common.SELLER_PUBKEY)})


@app.route("/order_status")
def order_status():
    active_order, _ = common.load_state()
    return jsonify(active_order or {"status": "no_order"})


@app.route("/transactions")
def transactions():
    _, tx_history = common.load_state()
    mine = [t for t in tx_history if t["type"] == "confirm_delivery"]
    return jsonify(list(reversed(mine)))


INDEX_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RoboPay — Auto steuern</title>
<style>
  body { margin:0; padding:16px; background:#111; color:#eee; font-family:system-ui,sans-serif; }
  h1 { font-size:1.1rem; margin:0 0 16px; }
  .grid { display:flex; flex-wrap:wrap; gap:16px; }
  .panel { background:#1b1b1b; border:1px solid #333; border-radius:8px; padding:14px 16px; flex:1; min-width:260px; }
  .label { color:#888; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; }
  a { color:#60a5fa; }
  .mono { font-family:ui-monospace,monospace; font-size:0.85rem; word-break:break-all; }
  .status-pending { color:#facc15; }
  .status-delivered { color:#4ade80; }
  .video { max-width:320px; width:100%; border-radius:6px; border:1px solid #333; display:block; }
  .car-row { display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }
  .sensor-box { flex:1; min-width:160px; }
  .sensor-stat { font-size:1.4rem; font-weight:700; margin:4px 0; }
  table { width:100%; border-collapse:collapse; font-size:0.85rem; }
  td { padding:4px 0; border-bottom:1px solid #2a2a2a; }
  .dpad { display:grid; grid-template-columns:repeat(3,48px); grid-template-rows:repeat(3,48px); gap:6px; margin-top:8px; }
  .dpad button { background:#2a2a2a; color:#eee; border:1px solid #444; border-radius:6px; font-size:1.2rem; padding:0; }
  .dpad button:hover { background:#3a3a3a; }
  .ctrl-row { display:flex; gap:24px; flex-wrap:wrap; margin-top:10px; }
</style>
</head>
<body>
<h1>RoboPay — Auto steuern (Seller/Operator)</h1>
<div class="grid">

  <div class="panel">
    <div class="label">Owner-Wallet</div>
    <div id="ownerWallet" class="mono">lädt...</div>
  </div>

  <div class="panel">
    <div class="label">Aktuelle Order</div>
    <div id="orderStatus">— keine aktive Bestellung —</div>
  </div>

  <div class="panel">
    <div class="label">Escrow-Release-Transaktionen</div>
    <table id="txTable"><tbody></tbody></table>
  </div>

  <div class="panel" style="flex-basis:100%;">
    <div class="label">Auto — Live-Kamera, Sensoren &amp; Steuerung</div>
    <div class="ctrl-row" style="align-items:flex-start;">
      <div id="carFeed">__PICAR_SERVER_URL__ nicht konfiguriert.</div>
      <div>
        <div class="label">Fahren</div>
        <div class="dpad">
          <button onmousedown="drive(30,-30)" onmouseup="driveStop()" ontouchstart="drive(30,-30)" ontouchend="driveStop()">↖</button><button onmousedown="drive(40,0)" onmouseup="driveStop()" ontouchstart="drive(40,0)" ontouchend="driveStop()">▲</button><button onmousedown="drive(30,30)" onmouseup="driveStop()" ontouchstart="drive(30,30)" ontouchend="driveStop()">↗</button>
          <button onmousedown="drive(30,-30)" onmouseup="driveStop()" ontouchstart="drive(30,-30)" ontouchend="driveStop()">◀</button>
          <button onclick="driveStop()">■</button>
          <button onmousedown="drive(30,30)" onmouseup="driveStop()" ontouchstart="drive(30,30)" ontouchend="driveStop()">▶</button>
          <button onmousedown="drive(-30,-30)" onmouseup="driveStop()" ontouchstart="drive(-30,-30)" ontouchend="driveStop()">↙</button><button onmousedown="drive(-40,0)" onmouseup="driveStop()" ontouchstart="drive(-40,0)" ontouchend="driveStop()">▼</button><button onmousedown="drive(-30,30)" onmouseup="driveStop()" ontouchstart="drive(-30,30)" ontouchend="driveStop()">↘</button>
        </div>
      </div>
      <div>
        <div class="label">Kamera</div>
        <div class="dpad">
          <div></div><button onclick="nudgeCam(0,10)">▲</button><div></div>
          <button onclick="nudgeCam(-10,0)">◀</button>
          <button onclick="setCam(20,0)">●</button>
          <button onclick="nudgeCam(10,0)">▶</button>
          <div></div><button onclick="nudgeCam(0,-10)">▼</button><div></div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
const picarUrl = "__PICAR_SERVER_URL__";

async function pollWallet() {
  try {
    const r = await fetch('/wallet');
    const d = await r.json();
    document.getElementById('ownerWallet').textContent = `${d.pubkey}\\n${d.sol} SOL`;
  } catch (e) {}
}

async function pollOrder() {
  try {
    const r = await fetch('/order_status');
    const d = await r.json();
    const el = document.getElementById('orderStatus');
    if (d.status === 'no_order') { el.textContent = '— keine aktive Bestellung —'; return; }
    const cls = d.status === 'delivered' ? 'status-delivered' : 'status-pending';
    el.innerHTML = `<span class="${cls}">${d.status}</span><br>Käufer: <span class="mono">${d.buyer_pubkey}</span>`;
  } catch (e) {}
}

async function pollTx() {
  try {
    const r = await fetch('/transactions');
    const d = await r.json();
    const tbody = document.querySelector('#txTable tbody');
    tbody.innerHTML = d.map(tx =>
      `<tr><td>Escrow-Release</td><td><a href="https://explorer.solana.com/tx/${tx.sig}?cluster=devnet" target="_blank">${tx.sig.slice(0,12)}...</a></td></tr>`
    ).join('') || '<tr><td>— noch keine Auszahlungen —</td></tr>';
  } catch (e) {}
}

async function drive(speed, angle) {
  if (!picarUrl) return;
  try {
    await fetch(picarUrl + ':8080/drive', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ speed, angle })
    });
  } catch (e) {}
}
async function driveStop() {
  if (!picarUrl) return;
  try { await fetch(picarUrl + ':8080/stop'); } catch (e) {}
}
let camPan = 20, camTilt = 0;
async function setCam(pan, tilt) {
  if (!picarUrl) return;
  camPan = pan; camTilt = tilt;
  try {
    await fetch(picarUrl + ':8080/camera/angle', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ pan: camPan, tilt: camTilt })
    });
  } catch (e) {}
}
function nudgeCam(dPan, dTilt) { setCam(camPan + dPan, camTilt + dTilt); }

if (picarUrl) {
  document.getElementById('carFeed').innerHTML = `
    <div class="car-row">
      <img class="video" src="${picarUrl}:9000/mjpg">
      <div class="sensor-box">
        <div class="label">Ultraschall</div>
        <div class="sensor-stat" id="distStat">— cm</div>
        <div class="label" style="margin-top:10px;">QR-Code</div>
        <div class="sensor-stat" id="qrStat" style="font-size:1rem;">—</div>
      </div>
    </div>`;
  setInterval(async () => {
    try {
      const [d, q] = await Promise.all([
        fetch(picarUrl + ':8080/ultrasonic').then(r => r.json()),
        fetch(picarUrl + ':8080/camera/qr').then(r => r.json()),
      ]);
      document.getElementById('distStat').textContent = `${d.distance_cm} cm`;
      document.getElementById('qrStat').textContent = q.qr || '— kein QR erkannt —';
    } catch (e) {}
  }, 1000);
}

pollWallet(); pollOrder(); pollTx();
setInterval(pollWallet, 5000);
setInterval(pollOrder, 2000);
setInterval(pollTx, 5000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False, use_reloader=False)

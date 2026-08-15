# Letterbox Node — Implementation Guide

Author: Xinyan (Hardware & Mechatronics) | Device: RPi 4B 2GB | Purpose: the second autonomous machine in the two-machine demo

---

## 1. Architecture: two parallel links (revised to current state)

```
Carrier (RPi 4 + SIM7600E-H, existing)          Letterbox (RPi 4B + servo, NEW)
    |                                               |
    |-- Link 1 (COMMS) -----------------------------|
    |    GPS arrival -> notify server -> letterbox  |
    |    receives "arrived" -> opens door -> micro  |
    |    switch confirms -> reports "opened"        |
    |                                               |
    +-- Link 2 (PAYMENT): carrier signs Solana tx -> escrow release |
```

IMPORTANT current state: the repo code has **no Staex SDK integration yet**.
Communication today is ngrok + Flask server (main.py polls a PC server).
So proceed in two steps:
- MVP (get it working first): reuse the existing Flask server; the letterbox polls it too — zero new dependencies, can be up in days
- Final form: switch to Staex MCC point-to-point tunnel (requires SDK + 2nd Staex SIM from Kevin / Prof. Mikityuk)

## 2. Shopping list (Conrad / Amazon, indicative prices)

| Item | Notes | Price |
|---|---|---|
| Servo MG996R-class (13 kg metal gear) | door-opening power; 2-pack on Amazon ~EUR 18 | ~9-18 EUR |
| Micro switch | door-open detection, ~EUR 3 | ~3 EUR |
| Jumper wires (male-female) | wiring | ~5 EUR |
| Breadboard (optional) | handy for first-time debugging | ~5 EUR |
| 5V PSU (second USB charger) | dedicated servo power | have/8 EUR |
| Wall-mount letterbox | off-the-shelf Briefkasten | 15-30 EUR |
| 5V relay module (backup option) | only if moving to magnetic-lock plan B | ~5 EUR |

Already owned: RPi 4B, SD card, PSU, card reader.
Buy first: servo + micro switch + jumper wires (~25-30 EUR). Everything else
only after the logic is proven.

## 3. Mechanics: how "servo rotates 90°" becomes "door opens"

Core trio: hinge + return spring + drive point.

Plan A (recommended, start here):
- Mount the letterbox door on regular hinges
- Fix the servo to the inner wall of the box; servo horn (cross metal arm) faces the door
- At 90° the horn pushes the door open (door must be light: acrylic / thin sheet metal)
- Attach a tension spring inside: after opening, the spring pulls the door back to closed (when the servo returns, the door closes itself)

Key point: the contact between horn and door is the tricky part — a small screw + washer as a push rod works fine.
Do NOT build a complex linkage first; validate the logic with a direct "horn pushes door" setup.

Plan B (backup): 12V magnetic lock + relay — lock holds the door, releases on signal, gravity/spring pops it open. Needs an extra 12V supply; do not buy yet.

## 4. Wiring (critical — read carefully)

Servo, 3 wires:
- Red → external 5V positive (servo power)
- Brown/black → GND (must share ground with the Pi!)
- Orange/yellow (signal) → GPIO 18 (BCM numbering, physical pin 12)

Micro switch, 3 pins:
- COM (common) → Pi GND
- NO (normally open) → GPIO 17 (BCM, physical pin 11)
- NC (normally closed) → not connected

! WARNINGS:
- NEVER power the servo from the Pi's 3.3V or 5V pins! MG996R peaks at 2.5 A; the Pi's 5V rail cannot handle it and the board can be damaged.
- Servo power comes from a separate 5V source (USB charger or 5V UBEC from battery); its ground MUST be tied to the Pi's GND (common ground), otherwise the signal is not recognized.
- The signal wire can go to the pass-through header pins on top of the SIM7600 HAT (Waveshare HAT pins are usually pass-through).

## 5. Code (letterbox node, mirrors main.py)

Install on the Pi (via SSH):
```
sudo apt install -y python3-gpiozero
pip3 install --user requests
```

Create `letterbox_node.py`:

```python
#!/usr/bin/env python3
"""Letterbox node: waits for 'arrived', opens door, confirms with micro switch."""
from gpiozero import Servo, Button
from time import sleep
import requests

SERVER_URL = "https://<your-ngrok-domain>/"   # same as PC_SERVER_URL in main.py
BOX_ID = "letterbox-1"
POLL_INTERVAL_S = 2.0

servo = Servo(18)               # signal wire -> GPIO18
door_switch = Button(17)        # micro switch -> GPIO17 (pull-up default, pressed = open)

def open_door():
    print("opening door...")
    servo.max()                  # rotate to open position (90 deg)
    sleep(2.5)
    servo.min()                  # back to closed (spring pulls door shut)
    print("door cycle done")

def main():
    print(f"letterbox {BOX_ID} running, polling {SERVER_URL}")
    while True:
        try:
            r = requests.get(f"{SERVER_URL}/letterbox_event",
                             params={"box": BOX_ID}, timeout=5)
            if r.status_code == 200:
                evt = r.json().get("event")
                if evt == "arrived":
                    print(">>> arrived event received")
                    open_door()
                    opened = door_switch.is_pressed
                    print(f">>>> door physically open: {opened}")
                    requests.post(f"{SERVER_URL}/letterbox_report",
                                  json={"box": BOX_ID, "opened": opened},
                                  timeout=5)
        except Exception as e:
            print("poll error:", e)
        sleep(POLL_INTERVAL_S)

if __name__ == "__main__":
    main()
```

Server side (order_server_pc.py — Kevin to confirm, or Xinyan/agent can edit), add 3 endpoints:
- `POST /arrived` — carrier calls on arrival; server records the event
- `GET /letterbox_event?box=letterbox-1` — letterbox polls; returns {"event":"arrived"} when an event is pending
- `POST /letterbox_report` — letterbox reports {"opened": true/false}; server stores it; carrier signs the Solana tx only after opened=true

Carrier side (main.py) addition: when haversine distance < 15 m, first POST /arrived, wait for opened=true, then sign the Solana transaction.

## 6. Test sequence (each step must pass before the next)

1. Servo local test (no network): 3-line script, servo.max()/servo.min() — verify wiring and power
2. Micro switch test: print(door_switch.is_pressed), press by hand, watch True/False
3. Full-flow simulation (KEY): no real GPS needed — trigger an arrived event manually on the server, watch letterbox open + report opened
4. Integration: carrier on phone hotspot, GPS-arrival logic triggers the complete chain
5. Outdoor demo: switch to 4G + Staex (final form)

## 7. Pitfalls (memorize these)

- Servo must have independent power + common ground, or you get resets/burned board
- Metal letterbox shields 4G — route the antenna outside
- Door too heavy -> servo stalls: keep the door light, or move to plan B (magnetic lock)
- Mount the micro switch where it senses "the door is actually open", not "the servo finished turning" — the physical confirmation is this paper's selling point, don't fake it
- Server polling is fine, but keep the interval reasonable (2 s is good; don't spam the server)

---
*Next step: buy servo + micro switch + jumper wires, then do local tests 1-2. Ask the agent to edit the server code when ready.*

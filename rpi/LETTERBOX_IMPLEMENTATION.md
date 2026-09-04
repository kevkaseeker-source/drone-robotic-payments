# Smart Letterbox — Implementation Guide

Author: Xinyan (Hardware & Mechatronics) | Audience: all team members
Scope: this document describes the **baseline version** of the smart letterbox
— a single node that opens upon arrival of a delivery machine. Section 8
outlines the extension path towards multi-machine coordination.

---

## 1. Purpose

The smart letterbox is a conventional wall-mounted letterbox augmented with a
small computer. It performs four functions:

1. receives a notification ("a delivery machine has arrived"),
2. opens its door autonomously,
3. verifies that the door is physically open (via a contact sensor),
4. reports the confirmation back, which serves as the trigger for payment.

The letterbox constitutes the **second autonomous machine** in the project
demo: the carrier (machine 1) approaches the box, the box (machine 2) opens,
and the payment settles automatically. No human interaction is required at
any point.

## 2. System Overview

```
Machine 1 (carrier; existing: RPi + 4G)        Machine 2 (letterbox; new)
   |                                                |
   |--- "arrived" (message over network) ---------->|  opens door
   |                                                |  verifies door state
   |<--- "opened" (confirmation) -------------------|
   |                                                |
   +-- payment (Solana escrow; existing code) ------+
```

In the baseline version the messages travel through the existing server
(the one already used by main.py). A later migration to the Staex private
network is possible without changes to the letterbox logic, since the
message protocol remains identical.

## 3. Bill of Materials

| Item | Description | Price |
|---|---|---|
| Servo motor, MG996R-class (metal gear) | a small motor that rotates to a commanded angle; drives the door opening | ~9-18 EUR |
| Micro switch | a contact sensor that closes an electrical circuit when pressed; detects the open door | ~3 EUR |
| Jumper wires | short connecting wires | ~5 EUR |
| Letterbox | any wall-mounted model | 15-30 EUR |
| Second 5V USB power supply | dedicated servo power (mandatory; see section 5) | available / 8 EUR |

Available: Raspberry Pi 4B, SD card, power supply.
Initial purchase: servo, micro switch, jumper wires (~25-30 EUR). The
letterbox itself can be acquired once the control logic is validated.

## 4. Mechanical Design

Objective: a servo rotates 90 degrees and pushes the door open; a spring
returns the door to the closed position.

Implementation (baseline):
- The door is mounted on standard hinges.
- The servo is fixed to the inner wall of the box, its horn aligned with the door.
- Rotation of the servo drives the horn against the door, opening it.
- A tension spring inside the box returns the door when the servo releases.

The door must be lightweight (acrylic or thin sheet metal). A direct-drive
configuration is sufficient for the baseline; complex linkage mechanisms are
explicitly deferred. If the door load exceeds the servo torque, a magnetic
lock serves as the fallback (section 9).

## 5. Electrical Wiring

Servo (3 wires):
- Red — external 5V positive (servo power supply)
- Brown/black — ground (common ground with the Pi required)
- Yellow/orange (signal) — GPIO 18 (BCM numbering; physical pin 12)

Micro switch (2 connections):
- Common — Pi ground
- Normally-open — GPIO 17 (physical pin 11)

> ⚠️ Critical constraint: the servo must be powered from a **separate** 5V
> supply, never from the Raspberry Pi's pins. The servo can draw up to 2.5 A
> transiently, which exceeds the Pi's pin ratings and can damage the board.
> The two supplies must share a common ground for reliable signal levels.

## 6. Software

The letterbox node runs a continuous polling loop:

```
loop:
    query server: "is there an arrival event for this box?"
    if event present:
        actuate servo -> door opens
        read micro switch -> is the door physically open?
        report to server: "opened: yes/no"
    wait 2 seconds; repeat
```

The complete implementation (~40 lines, appendix) mirrors the structure of
the carrier's main.py and is therefore familiar to team members who have
worked with the existing code.

Server-side changes (Kevin or the agent): three new endpoints are required —
one to record the "arrived" event, one polled by the letterbox, and one
receiving the "opened" confirmation. The carrier signs the payment
transaction only after a positive confirmation.

## 7. Test Procedure

1. Servo test: a three-line script actuates the servo; verifies wiring and power.
2. Switch test: the micro switch is pressed manually; the state change is observed.
3. Full-flow simulation: an "arrived" event is triggered manually on the
   server; the letterbox opens and reports back. This validates the complete loop.
4. Integration: the carrier approaches for real; GPS arrival triggers the chain.
5. Outdoor demo: full operation over 4G.

Each step is a prerequisite for the next.

## 8. Extension Path: from Single Letterbox to Multi-Machine Coordination

The baseline is deliberately minimal. Its significance lies in the fact that
the same node generalizes into a component of a machine economy:

- **Carrier independence.** The message protocol does not depend on the
  carrier type. The ground vehicle (Unit C) and, in a later stage, the drone
  (Unit B) use the same "arrive -> open -> confirm -> pay" sequence.
- **Multiple letterboxes.** Each box carries an identifier; a delivery
  targets a specific box_id, and only that box responds. The server logic
  scales to fleets without structural change.
- **Authentication.** The box can verify the arriving machine (e.g. QR code
  presented by the carrier, or a credential in the message) before opening,
  preventing unauthorized triggering. This contributes to the security
  analysis in the paper.
- **Agent-based decision making** (paper section 17.2). The hard-coded rule
  ("arrive -> open") can be replaced by an agent that authorizes the delivery
  after checking order data, carrier reputation, and escrow state. The
  letterbox then acts as the executor of agent decisions.
- **Physical confirmation remains the trust anchor.** Independent of future
  extensions, the micro-switch signal ("the door is physically open") remains
  the basis of the confirmation chain — the project's research differentiator,
  already present in the baseline.

## 9. Known Pitfalls

- Servo power: dedicated supply plus common ground (the critical constraint
  of section 5).
- Metal letterbox enclosures attenuate mobile signals; the 4G antenna must
  be routed outside.
- Excessive door weight stalls the servo; keep the door light or adopt the
  magnetic-lock fallback.
- The micro switch must sense the door state, not the servo state; physical
  verification is the project's core principle.
- Each test stage must pass before the next is attempted.

---
*Next action: acquire servo, micro switch, jumper wires; perform test steps
1-2. Server endpoints: request the three routes from the agent or Kevin.*

## Appendix: Letterbox Node Code (letterbox_node.py)

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
door_switch = Button(17)        # micro switch -> GPIO17 (pull-up default; pressed = open)

def open_door():
    print("opening door...")
    servo.max()                  # rotate to open position (90 deg)
    sleep(2.5)
    servo.min()                  # return to closed position (spring pulls door shut)
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
                    print(f">>> door physically open: {opened}")
                    requests.post(f"{SERVER_URL}/letterbox_report",
                                  json={"box": BOX_ID, "opened": opened},
                                  timeout=5)
        except Exception as e:
            print("poll error:", e)
        sleep(POLL_INTERVAL_S)

if __name__ == "__main__":
    main()
```

Dependencies (installed on the Pi via SSH):
```
sudo apt install -y python3-gpiozero
pip3 install --user requests
```

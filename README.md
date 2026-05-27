# DePIN Drone Delivery PoC

Autonomous drone delivery system with on-chain GPS-verified payment using Solana, MAVLink, and Staex secure connectivity.

**Status:** Indoor PoC complete — confirm_delivery TX finalized on Solana Devnet ✓

---

## How it works

```
Buyer (Phone/Browser)
  │
  ├─ create_delivery TX ──▶ Solana Escrow (SOL locked)
  │
  └─ POST /order ──▶ Flask PC ──ngrok──▶ Internet
                                              │
RPi4 ──GET /active_order (every 5s) ◀─────────┘
  │
  ├─ MAVLink UART ◀──▶ Pixhawk FC ◀──▶ M8N GPS
  │
  └─ GPS within 13m of target?
       └─ confirm_delivery TX ──▶ Solana (SOL → Seller)
```

When the drone arrives at the buyer's GPS coordinates, the Raspberry Pi 4 automatically fires a `confirm_delivery` transaction signed by the drone operator wallet. The Solana smart contract verifies the GPS coordinates on-chain (±22m tolerance) and releases the SOL from escrow to the seller.

---

## Hardware

| Component | Details |
|---|---|
| Raspberry Pi 4 | Main compute — runs MAVLink bridge + Solana TX signing |
| Pixhawk (Flight Controller) | MAVLink telemetry via UART (TELEM1) |
| M8N GPS Module | Connected to Pixhawk — provides cm-accurate positioning |
| Waveshare SIM7600E-H 4G HAT | 4G LTE modem for RPi4 connectivity |
| **Staex IoT SIM Card** | Secure device identity + global IoT connectivity via Staex network |
| Powerbank 1 | Powers RPi4 + 4G HAT |
| Powerbank 2 | Powers Pixhawk separately (prevents undervoltage) |
| Drone frame, motors, ESCs, props | ~€200–400 (Phase 2) |

### Wiring — Pixhawk UART to RPi4 GPIO

```
Pixhawk TELEM1 TX  ──▶  RPi4 GPIO15 (Pin 10, RX)
Pixhawk TELEM1 RX  ──▶  RPi4 GPIO14 (Pin 8, TX)
Pixhawk GND        ──▶  RPi4 GND (Pin 6)

Port: /dev/ttyAMA0 (serial0) @ 57600 baud
```

---

## Software

| File | Description |
|---|---|
| `rpi/main.py` | Main loop — polls Flask server, monitors GPS, fires confirm_delivery TX |
| `rpi/pixhawk_bridge.py` | MAVLink connection via pymavlink — reads GLOBAL_POSITION_INT |
| `rpi/solana_client.py` | confirm_delivery + close_escrow TX builder and sender |
| `rpi/config.py` | Connection strings, wallet paths, program ID |
| `rpi/order_server_pc.py` | Flask server (runs on PC) — receives orders, serves browser app |
| `rpi/index.html` | Browser PWA — wallet, GPS, escrow TX, order status |
| `rpi/startup_rpi.sh` | Boot script — starts pppd (4G) + main.py |

### Smart Contract (Anchor, Solana Devnet)

**Program ID:** `3NmsWVX39uvzG3PBNPdSe4FTgudqSeLphJSbMDhV5F8Y`

| Instruction | Caller | Action |
|---|---|---|
| `create_delivery` | Buyer (browser) | Lock SOL in escrow PDA |
| `confirm_delivery` | Drone (RPi4) | Verify GPS on-chain → release SOL to seller |
| `cancel_delivery` | Buyer | Refund after deadline |
| `close_escrow` | Drone | Close PDA, reclaim rent |

---

## Whitepapers

The drone delivery concept was developed before the Turbin3 DePIN Cohort:

- [Whitepaper 1 (Aug 2025)](https://drive.google.com/file/d/1jAlIEzMXRwHfi5iX24QuDZeIgeXCyYw0/view?usp=drive_link)
- [Whitepaper 2 (Aug 2025)](https://drive.google.com/file/d/1EAghRdOFmiYza4A5TDOuNY5xfbVkrSe-/view?usp=drive_link)

---

## Turbin3 DePIN Cohort — Q4 2025

Participating in the [Solana Turbin3 DePIN Cohort](https://github.com/solana-turbin3/drone-delivery-powered-by-depin) together with **Hsien Hsiu Liao** and **Eduardo Ramirez** strongly advanced this project — from concept to working on-chain smart contract. The cohort provided the Solana/Anchor foundation that this hardware integration builds on.

The current implementation extends the cohort work with full hardware integration: Raspberry Pi 4, Pixhawk flight controller, M8N GPS, 4G LTE via Staex SIM, and real MAVLink telemetry.

---

## Architecture

```
[Buyer Phone]          [PC (Windows)]           [RPi4]
     │                      │                      │
     │── GPS coords ──▶      │                      │
     │── create_delivery ──▶ Solana Devnet          │
     │── POST /order ──▶     │ Flask                │
     │                      │ ◀── GET /active_order ┤ (every 5s via 4G)
     │                      │                      │── MAVLink UART
     │                      │                      │◀─ Pixhawk ◀─ M8N GPS
     │                      │                      │
     │                      │                      │── GPS match?
     │                      │                      └──▶ confirm_delivery TX
     │                      │                               │
     │◀── POST /delivered ───┤◀──────────────────────────────┘
     │ 🎉 Delivered!         │
```

---

## Proof of Delivery

Every delivery generates two verifiable on-chain transactions:

1. **create_delivery** — Buyer locks SOL in escrow with GPS target coordinates
2. **confirm_delivery** — Drone operator wallet signs TX with actual GPS coordinates → SOL released to seller

Both transactions are publicly verifiable on [Solana Explorer (Devnet)](https://explorer.solana.com/?cluster=devnet).

---

## Integrations

| | |
|---|---|
| **[Staex](https://staex.io)** | IoT SIM card — secure 4G connectivity for the drone hardware |
| **[Solana](https://solana.com)** | RoboticPayments layer — autonomous GPS-triggered escrow release, no human approval required |

---

## Phase Roadmap

| Phase | Description |
|---|---|
| Phase 1 (current) | Devnet PoC — indoor + outdoor GPS delivery |
| Phase 2 | Split payment: delivery_fee → operator, product_price → seller |
| Phase 3 | Mainnet, USDC, GEODNET RTK cm-GPS, real drone frame |

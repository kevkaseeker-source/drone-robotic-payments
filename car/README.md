# Delivery Car — Unit C

Ref: paper §6.1–6.2 ("System Architecture" / "Hardware & Network Architecture", Figure 13/14)
and §7.5–7.6 (outdoor GPS/trust-model detail).

Owner: **Yashdeep Singh**.

## Platform

Unit C is built on the **SunFounder PiCar-X** platform (not the Freenove kit — that was
evaluated and rejected; see "Alternatives considered" below). Per the paper, PiCar-X was
chosen for its camera + OpenCV/MediaPipe integration, line tracking, obstacle avoidance,
and Python programmability, all of which are directly usable for this project.

Current hardware:
- Raspberry Pi 4 Model B
- Waveshare SIM HAT (same GPS + 4G module family used on Unit B / the drone)
- Staex M2M SIM card for connectivity

## Role

Same escrow logic as Unit B (the drone): GPS-triggered `confirm_delivery`, own Solana
wallet, own Staex MCC endpoint — the only difference is delivery happens on land instead
of by air. Reuses the existing escrow ([`../anchor/`](../anchor/)) and GPS/Solana node
code ([`../rpi/`](../rpi/)) already proven on the drone.

Initial control phase: manual operation via the PlaySolana Gen 1 app, to keep the first
build phase simple. Fully autonomous driving is deferred until escrow settlement is
proven end-to-end on a manually-guided vehicle.

## Status

- [ ] Assemble PiCar-X chassis
- [ ] Mount Raspberry Pi 4B + Waveshare SIM HAT on chassis
- [ ] Wire/validate GPS (reuse `pixhawk_bridge.py` GPS logic from the drone, minus MAVLink/flight-controller parts)
- [ ] Provision Solana keypair + MCC endpoint for Unit C
- [ ] Manual drive test via PlaySolana Gen 1 app
- [ ] End-to-end escrow test (GPS arrival → `confirm_delivery` → Unit A co-sign)

## Alternatives considered

Freenove 4WD Smart Car Kit was evaluated as a cheaper/simpler alternative (~€65–70,
4WD skid-steer, larger community) before the PiCar-X decision in the paper was found.
Not pursued further — PiCar-X is the documented choice and matches hardware already on
hand.

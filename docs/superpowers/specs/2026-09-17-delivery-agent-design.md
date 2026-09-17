# AI delivery-confirmation agent — design

Brainstormed 2026-09-17 by Kevin Ehrentraut and Gabriel Mandtler.

## Research question

RoboPay Unit C currently triggers escrow release with a **deterministic,
hardcoded rule** in `car/car_main.py`: the camera's decoded QR string must
exactly match `BOX_QR_CODE`, optionally combined with an ultrasonic
distance window. This is one point along a spectrum of "how does a
machine prove it's allowed to release payment" designs — Unit B (the
drone) uses a GPS geofence instead of QR+distance, and x402 (HTTP 402
payment-challenge protocol) is a third, protocol-based paradigm.

The research goal is to **compare these trigger paradigms** —
condition-triggered (QR/GPS, what exists today) vs. **agent-decided**
(an LLM autonomously judging when to release funds) — as part of the
broader Machine Economy Lab research. x402 is a later extension of the
agent path (§ Future work), not part of this first build.

## What this spec covers

Building a standalone AI agent that can read the car's existing sensors
and autonomously decide to sign and send the `confirm_delivery`
transaction, running **in parallel with the existing `car_main.py`**, not
replacing it — so both trigger paradigms can be compared side by side
without risking the delivery flow that's already live and working.

## Decisions made during brainstorming

- **Agent runtime:** Claude API with a tool-use loop (matches the existing
  Claude Code workflow this whole project is built through; well-documented,
  good fit for "read sensor tools, then decide to call a sign-and-send tool").
- **v1 capabilities:** read sensor/context data (QR, ultrasonic) and reason
  over it; independently sign and send the Solana transaction. x402-as-client
  (agent paying for external resources/verification) is explicitly deferred
  to a later round — v1 stays minimal.
- **Trigger condition:** the agent recognizes the QR code (via the same
  `/camera/qr` reading car_main.py already uses) as the box's code, and on
  that basis signs the escrow-release transaction itself — an LLM judgment
  call standing in for the current `qr == BOX_QR_CODE` Python comparison.
- **Relationship to `car_main.py`:** parallel, not a replacement. Own
  wallet, own escrow order, `car_main.py` stays untouched and keeps running
  the existing proven flow.

## Architecture

A new standalone script, `agent/delivery_agent.py`, separate from
`car/car_main.py` and not started by any of the existing systemd services.

**Tools exposed to the agent (Claude tool-use):**
1. `get_qr()` — reads `/camera/qr` (reuses the same endpoint `car_main.py`
   already polls, e.g. via `PICAR_SERVER_URL` or the seller-app proxy)
2. `get_distance()` — reads `/ultrasonic`, same pattern
3. `sign_confirm_delivery(actual_lat, actual_lon)` — wraps the **existing**
   `SolanaClient.confirm_delivery()` from `rpi/solana_client.py` unchanged;
   this spec adds no new signing logic, only a new caller

**System prompt (sketch):** the agent is told it's monitoring a delivery
robot's camera/sensor feed and must decide, using its own judgment, when
the delivery is genuinely confirmed — then call the sign tool. No fixed
"call the tool the instant the string matches" instruction — the point of
the experiment is that the agent is *reasoning*, not pattern-matching.

**Loop:** poll `get_qr()`/`get_distance()` → feed results to Claude →
Claude either asks for more reads or calls `sign_confirm_delivery` →
script exits (or logs and idles) once signed.

## Important wrinkle: the escrow PDA is per-operator

`anchor/programs/drone-delivery/src/lib.rs` derives the escrow account as
`seeds = [b"escrow", drone_operator.key().as_ref()]` — **one escrow slot
per operator pubkey.** The existing flow always creates orders against the
fixed `OPERATOR_PUBKEY` (`car_main.py`'s operator, `7Viz...hXia`). For the
agent to have "its own escrow" to sign against (needed for a real
parallel, non-interfering comparison), a delivery order has to be created
with the **agent's own pubkey** passed as `drone_operator` in
`create_delivery` — the existing buyer app always targets the fixed
operator pubkey, so it can't order "for the agent" as-is.

**v1 approach:** don't extend the buyer app's UI for this. Write a small,
separate CLI/test script (reusing `create_delivery()`'s logic from
`car/buyer_app.py`, parameterized by operator pubkey) to place a test
order specifically targeting the agent's wallet. This keeps the buyer app
untouched and the experiment self-contained — revisit only if the
comparison needs to run outside a dev/test context.

## Wallet / funding

New, dedicated **agent operator keypair**, generated fresh (not reusing
`picarx_operator.json`) — makes the two paths cleanly distinguishable
on-chain (separate pubkeys in transaction history) and means a bug in the
experimental agent path can't touch the funds/state of the working system.
Needs its own small Devnet SOL balance for transaction fees (faucet).

## Testing

Run the agent against the **real, already-live sensors** (via
`PICAR_SERVER_URL` / the seller-app proxy, same endpoints `car_main.py`
uses) — no need to mock sensor data, the hardware is already exposed over
HTTP and reachable. Compare: does the agent sign at a materially different
moment than the deterministic rule would have, on the same physical QR/
distance sequence? That comparison — timing, false-positive/negative
judgment, reasoning trace — is the actual research output.

## Out of scope for this spec (future work)

- x402 as a tool the agent pays through (e.g., paying an external
  verification/oracle service before it trusts its own read enough to
  sign) — the natural next round once v1's baseline agent-vs-rule
  comparison exists.
- Deciding where the agent ultimately "lives" on the PiCarX itself
  (on-device vs. cloud-side) — explicitly deferred per Kevin: build the
  agent first, decide PiCarX placement afterward.
- Any change to `car_main.py`, the buyer/seller apps, or the Anchor
  program — v1 touches none of them.

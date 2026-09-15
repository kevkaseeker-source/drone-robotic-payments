# Unit C (PiCar-X) — Setup & Architecture Notes

Written 2026-09-10 while doing the first full software setup on the physical
RPi (hostname `picarx`), documenting how the pieces actually talk to each
other end to end. Keep this updated as the design changes — it's meant to
answer "how does X actually reach Y" without having to re-read every script.

## 1. Physical / network setup

- Raspberry Pi 4B, Raspberry Pi OS 64-bit (Debian 13 "trixie"), Python 3.13.5
- SIM7600G-H USB dongle + GPS antenna mounted (SIM card not yet inserted —
  GPS/4G connectivity is not used for anything on Unit C right now, see §3)
- Robot HAT has its own Type-C charging port, separate from the RPi's own
  power — the RPi can stay on wall power while the HAT runs off its battery
  for motors/servos/ultrasonic. Main power switch must be on for the HAT's
  I2C peripherals to respond (confirmed via `i2cdetect -y 1`: nothing at
  power-off, device at `0x14` once the switch is on).
- SSH key auth set up for remote (non-interactive) control, in addition to
  the picarx/picarx12 password login.

## 2. Software stack installed on the RPi

System-wide (`/usr/local/lib/python3.13/dist-packages`, via `sudo pip3
install --break-system-packages`, Debian's PEP 668 lock requires this flag):

- `robot-hat` (branch `2.5.x`) — low-level HAT driver, official install.py
- `vilib` (main branch) — camera/QR/vision, official install.py. Note:
  `mediapipe`/`tflite-runtime` are skipped on Python 3.13 (no wheels yet) —
  only affects face/gesture recognition, **not** QR reading (pyzbar-based).
- `picar-x` (branch `2.1.x`) — motor/servo/ultrasonic driver

Isolated venv at `~/robopay-research-group/venv` (**no** `--system-site-packages`)
— used only for the Solana side:

- `solana==0.36.6`, `solders==0.26.0` (auto-resolved), `requests`
- Deliberately pinned old: `solana>=0.40` dropped the synchronous
  `solana.rpc.api.Client` entirely (only `AsyncClient` remains), which
  `rpi/solana_client.py` depends on. Installing it into the *system*
  site-packages also collided with the `solders` version already pulled in
  by `vilib`/`robot-hat`, corrupting both — hence a fully separate venv
  rather than trying to make one Python environment satisfy both stacks.
- Run any script that imports `solana_client` (i.e. `car_main.py`) with
  `~/robopay-research-group/venv/bin/python3`, not system `python3`.
  `picar_server.py` (no Solana import) keeps using system `python3`.

## 3. Data flow / how the pieces talk to each other

```
 Buyer's phone/browser                     PC server (order_server_pc.py,
        |  places order (lat/lon,               Kevin's PC, via ngrok)
        |  buyer_pubkey, escrow_tx)                     ^  |
        v                                                |  | GET /active_order
 create_delivery() on-chain                              |  | POST /delivered, /rpi_log
 (Anchor program, Devnet)                                |  v
                                                    car_main.py (RPi, venv python)
                                                           |
                                    polls over HTTP (localhost:8080)
                                                           |
                                                           v
                                                  picar_server.py (RPi, system python)
                                                    /camera/qr   -> Vilib QR read
                                                    /ultrasonic  -> Picarx distance read
```

`car_main.py` (new, this session) is the car's equivalent of the drone's
`rpi/main.py`. It does **not** talk to hardware directly — it polls
`picar_server.py`'s own HTTP endpoints on localhost, which is what actually
holds the `Picarx()`/`Vilib` singletons.

**Arrival detection, and why it's safe not to use real GPS here:** the
on-chain `confirm_delivery` instruction ([lib.rs:41-77](../anchor/programs/drone-delivery/src/lib.rs))
only checks that the lat/lon *we submit* are within tolerance of the
escrow's stored target — it has no independent way to verify the RPi is
actually where it claims. Whoever controls the RPi's signing key is
already a fully trusted oracle for GPS-based delivery, too (documented in
the paper, chapter 12, as the "RPi as sole signer of truth" limitation).
Given that, Unit C's physical trigger (QR code matching the order's
`escrow_tx`, read within 15–25cm via ultrasonic) is just a different,
*additional* real-world gate in front of the same trust boundary — when it
passes, `car_main.py` re-submits the order's own `lat`/`lon` values
(not real sensor GPS) to `confirm_delivery`. No smart-contract changes
were needed for this.

**Known limitation, not yet mitigated:** anyone with SSH access to the RPi
could call `confirm_delivery` directly, bypassing the QR/ultrasonic check
entirely — same limitation as the drone. Worth a line in the paper's
Security Analysis (ch. 12) as an accepted PoC-stage limitation, not a
solved problem.

## 4. Wallets (Devnet)

Two new keypairs generated directly on the RPi with `solders` (no Solana
CLI installed — not needed, `solders.keypair.Keypair()` + writing the
64-byte secret as a JSON array is the same file format the CLI produces):

| Role | Path (RPi) | Pubkey |
|---|---|---|
| Unit C operator (signs `confirm_delivery`, pays gas) | `~/.config/solana/picarx_operator.json` | `7VizNvqBSnHnP8ySnsjxxyUnBQCybVnJHBDRyvaThXia` |
| PiCarOwner / seller (receives the SOL payout) | `~/.config/solana/picarowner.json` | `7uoFeSG546UvK5HYyA97GVmJUTvrXWgGgkTgxspH4d1C` |

Operator wallet funded with 5 Devnet SOL via the manual web faucet
(`faucet.solana.com`) — the RPC-based `request_airdrop` call against
`api.devnet.solana.com` returned `Internal error` (that public faucet is
commonly rate-limited/overloaded).

`car_main.py` reuses the existing `rpi/config.py` env-var mechanism rather
than a separate config file (so it doesn't collide with the drone's
config): run it with `WALLET_KEYPAIR_PATH` and `SELLER_PUBKEY` env vars set
to the two paths/pubkeys above. "PiCarOwner" is our naming for what the
shared code calls `SELLER_PUBKEY`/`seller` — same on-chain field, just
labeled for clarity in Unit C's own logs/docs.

## 5. Bugs found and fixed in `picar_server.py` (this session)

1. **Flask reloader crash-loops the camera.** `vilib/vilib.py` sets
   `os.environ['FLASK_DEBUG'] = 'development'` as an import side effect.
   Since `picar_server.py` imports `vilib` before calling `app.run()`, this
   silently enabled Werkzeug's debug reloader, which re-execs the whole
   script in a child process — re-running `Vilib.camera_start()` while the
   parent still holds the camera open, crashing with `RuntimeError: Failed
   to acquire camera: Device or resource busy`. Fixed by passing
   `debug=False, use_reloader=False` explicitly to `app.run()`.
2. **`Vilib.qr_coder_reader()` doesn't exist** in the installed vilib
   version (0.3.19) — 500 error on `/camera/qr`. The real API is:
   call `Vilib.qrcode_detect_switch(True)` once after `camera_start()`,
   then read the continuously-updated `Vilib.detect_obj_parameter['qr_data']`
   (default value is the **string** `"None"`, not Python `None`, when
   nothing is detected — normalized to real `None` in a small `read_qr()`
   helper added to `picar_server.py`).

## 6. QR camera-detection limits (found 2026-09-11, live testing)

Dense QR codes (e.g. a Luma event-ticket QR encoding a long URL) reliably
failed to decode from the camera — tested across many distances (15-45cm),
lighting levels, `pyzbar`, OpenCV's built-in `QRCodeDetector`, and even
OpenCV's CNN-based `WeChatQRCode` detector (model weights downloaded from
`github.com/WeChatCV/opencv_3rdparty`) — all failed identically. A short/
simple QR code (a "https://scandit.com" demo QR) decoded on the first try,
same camera/lighting/distance. Root cause: QR **module density** (too many
small modules for this 5MP fixed-focus camera to resolve), not focus,
lighting, or a software bug.

**Design decision that follows from this (supersedes the original plan):**
The QR the camera reads is a **fixed, static marker on the delivery box**
(`BOX_QR_CODE` in `car_main.py`, default `"ROBOPAY-BOX-C"`) — the same one
every time, not generated per order. It only proves "the car found the
box"; which order is being fulfilled is tracked separately via the single
active order from `order_server_pc.py`. For the PoC, no physical cube is
needed — a phone just displaying the QR code is enough. This also means
the buyer-ordering flow doesn't need to generate/display a QR at all.
Consequence for later: the real `escrow_tx` (~88 base58 chars) must never
be used directly as QR content — it's exactly the kind of dense code that
fails here.

## 7. MCC (Staex connectivity) — set up 2026-09-11

**SIM as a full network interface:** the SIM7600G-H is a plain USB modem
(not the HAT variant with built-in ECM/RNDIS), so it needed a classic PPP
dial-up rather than just an AT-command PDP context:
- APN set via AT command: `AT+CGDCONT=1,"IP","iot.truphone.com"` on
  `/dev/ttyUSB2` (the AT-command port; `/dev/ttyUSB0` errors, `ttyUSB1`/
  `ttyUSB4` are silent/other-purpose ports — found by probing all 5 with a
  hard `timeout` wrapper, since a naive open-and-read can hang indefinitely
  on the wrong port).
- PPP config: `/etc/ppp/peers/staex-sim` (peer options) +
  `/etc/chatscripts/staex-sim.chat` (dial script, `ATD*99#`). Brought up
  with `sudo pppd call staex-sim` — creates `ppp0`, confirmed working with
  real internet (ping to 8.8.8.8, HTTP to bild.de) and does **not**
  override the existing default route (car stayed reachable over
  Ethernet/WLAN throughout — pppd logged "not replacing existing default
  route").
- `/etc/resolv.conf` fixed to `8.8.8.8`/`1.1.1.1` and locked with
  `chattr +i` — same fix as the MIBO fleet needed; without it MCC can't
  resolve the parent address ("No CAS address resolved").

**MCC install (`docs.staex.io`):**
```bash
curl -sL -o /tmp/staex-repo.noarch.deb https://packages.staex.io/linux/deb/staex-repo.noarch.deb
sudo apt-get install -y /tmp/staex-repo.noarch.deb
sudo apt-get update
sudo apt-get install -y mcc
```
**Init — the key trick for non-interactive init (SSH, no TTY prompt):**
`mcc init` normally prompts interactively for the network certificate and
private key. Both can be passed non-interactively instead: certificate as
a positional base64 argument, private key piped via `--stdin`. Do **not**
pipe the sudo password into the same command — it eats the stdin meant for
the private key. Cache sudo first (`sudo -S -v`), then run mcc init as a
plain `sudo` call so its stdin is free:
```bash
echo picarx12 | sudo -S -v
echo "<network-private-key-base64>" | sudo mcc init --force --stdin "<network-certificate-base64>"
sudo chmod 400 /etc/mcc/node-private-key.txt
sudo systemctl enable --now mcc
```
Credentials for this node came from Maksim (Staex) — not reused from any
other project's node.

**Parent connection:** a freshly-init'd node has no parent configured
(`/etc/mcc/mcc.conf` ships with `parents =` empty) — `mcc nodes` shows only
itself until one is set. Fixed by editing `mcc.conf`:
`parents = public.staex.io:9376`, then `sudo systemctl restart mcc`. Confirmed
via `sudo journalctl -u mcc`: `active parent is 88.99.68.57:9376`, and
`sudo mcc parent` returns the same.

**Result:** Unit C's MCC node is live — ID
`pbraybxmydh10prae3hdv87t0q7pwetgzrqdahbtckewnsb7tywg`, connected to parent
`88.99.68.57:9376`, service enabled (survives reboot).

**Not done yet:** no tunnel created for `picar_server.py`'s port 8080
(`mcc create-tunnel --targets tcp:8080 --remote-node <id>`) — needs a
`--remote-node` value (whichever node should be allowed to reach this car,
e.g. Kevin's own PC if it also runs MCC) that wasn't available this
session. Once created, the dashboard/API would be reachable at
`http://picar-x.staex:8080` per the docstring in `picar_server.py`,
matching the drone project's `http://picar-x.staex` naming convention.

**Follow-up bug found 2026-09-15:** `/dev/ttyUSB2` (the AT-command port used
in `/etc/ppp/peers/staex-sim`) is not stable — the SIM7600 dongle's ttyUSB
numbering shifted after a replug/reboot (`ttyUSB2` disappeared, remaining
ports renumbered), so `ppp-staex-sim.service` crash-looped with `pppd:
unrecognized option '/dev/ttyUSB2'` (a confusing error for what's actually
"device doesn't exist"). Re-probed all `/dev/ttyUSB*` the same way as in
§7 and found the AT port had moved to `ttyUSB3`. Fixed properly this time
by pointing the peers file at the **stable** udev path instead of the
numbered one: `/dev/serial/by-id/usb-SimTech__Incorporated_SimTech__Incorporated_0123456789ABCDEF-if02-port0`
(`ls /dev/serial/by-id/` lists these — the `-if02-port0` suffix is the USB
interface number, which doesn't change on replug/renumbering the way the
`ttyUSB*` number does). If `ppp-staex-sim` ever crash-loops again with a
similar "unrecognized option" error, check `ls /dev/serial/by-id/` first —
the underlying device is very likely just fine.

## 8. systemd autostart — set up 2026-09-12

Two units, `/etc/systemd/system/picar-server.service` and `car-trigger.service`:
- `picar-server.service` — runs `python3 picar_server.py` as `User=root`
  (needed for I2C/GPIO hardware access), `Restart=on-failure`
- `car-trigger.service` — runs `car_main.py` via the venv python, as the
  `picarx` user, `After=picar-server.service` + `Requires=picar-server.service`
  so it only starts once the sensor server is up, `Restart=always` (so it
  loops back to "waiting for order" after each dry-run demo cycle instead
  of exiting once). Currently launches with `--demo --dry-run` — real
  (non-demo, non-dry-run) mode needs the PC order server actually running
  first (see §8 open items), and dry-run stays the safe default for
  something that starts unattended on every boot.

**Bug found and fixed:** the `picarx` library calls `os.getlogin()` during
`Picarx.__init__` (`picarx.py:48`) to tag its config file's owner. This
throws `OSError: [Errno -25] Unknown error -25` under systemd, because
`os.getlogin()` needs a controlling terminal/login session (queries utmp)
that a systemd service simply doesn't have — a well-known Python gotcha,
not specific to this library. It worked fine every time we'd started
`picar_server.py` manually over SSH, because an SSH session does have one,
which is exactly why this didn't show up until switching to systemd.
Patched in `/usr/local/lib/python3.13/dist-packages/picarx/picarx.py` to
`os.environ.get('USER') or os.environ.get('LOGNAME') or 'picarx'` instead.

**Verified with a real reboot** (not just `systemctl restart`): both
services come up with zero manual intervention. `car-trigger.service`
takes ~20-40s longer than `picar-server.service` to actually start after
boot — it waits on `network-online.target`, which takes a bit to resolve
over WiFi (association + DHCP) — this is expected, not a bug; give it
under a minute after power-on before expecting it to be polling.

**Also verified by an unplanned power loss** (2026-09-12, car battery/RPi
lost power mid-session): `picar-server`, `car-trigger`, and `mcc` all came
back on their own with zero intervention — a stronger test than the
scripted reboot, since it wasn't a clean shutdown. Only the PPP/SIM
connection (§7) didn't come back, because it had only ever been started
manually (`nohup pppd ...`), never as a systemd unit. Fixed the same way:
`/etc/systemd/system/ppp-staex-sim.service` running
`/usr/sbin/pppd call staex-sim` (the peers file already has `nodetach` +
`persist`, so a plain `Type=simple` unit with `Restart=always` is enough
— no wrapper script needed). All four services — `picar-server`,
`car-trigger`, `mcc`, `ppp-staex-sim` — are now `systemctl enable`d and
confirmed to survive both a clean reboot and a hard power loss.

## 9. Current status / open next steps

- [x] robot-hat / vilib / picar-x installed, hardware confirmed live
      (ultrasonic + I2C tested with the car's main power on)
- [x] `picar_server.py` fixed and running, all endpoints verified
      (`/health`, `/ultrasonic`, `/camera/qr`, `/dashboard`)
- [x] `car_main.py` written, demo+dry-run polling loop verified end-to-end,
      updated to match against a fixed `BOX_QR_CODE` (see §6)
- [x] Unit C Devnet wallets generated and operator wallet funded
- [x] Live QR test done — confirmed a real camera-detection limitation
      (§6), not a bug; simple/short QR codes decode fine
- [x] SIM card (Staex M2M) physically inserted, working as a full PPP
      network interface, MCC installed and connected to its parent (§7)
- [ ] Owner-side keypair (`picarowner.json`) still lives on the RPi —
      should move to Kevin's own wallet/phone before any real MWA dApp
      login flow is built (see plan discussed 2026-09-11, not yet actioned)
- [ ] MCC tunnel for port 8080 not yet created (needs a remote-node id, §7)
- [ ] Real (non-dry-run) `confirm_delivery` TX not yet fired end-to-end
- [ ] No phone-ordering flow exists yet for Unit C specifically — right now
      `car_main.py --demo` uses a fixed local order for testing. Wiring it
      to a real PC-side order server (reusing `order_server_pc.py`, which
      is generic enough to work as-is) is a separate follow-up. Since the
      QR is now static (§6), the order flow no longer needs to generate a
      QR at all — simplifies this step.
- [ ] Owner-side Solana Mobile dApp (MWA wallet-connect, live
      video/telemetry over the MCC tunnel once it exists, drive controls)
      — architecture discussed 2026-09-11, not yet started
- [x] systemd autostart for `picar_server.py` + `car_main.py`, verified
      with a real reboot — power on car, wait under a minute, everything
      runs with no SSH/terminal needed (§8). Currently in `--demo --dry-run`
      mode by design (see §8) until the real order flow exists.

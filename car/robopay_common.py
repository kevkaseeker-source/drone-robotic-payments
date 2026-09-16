#!/usr/bin/env python3
"""Shared config/helpers for buyer_app.py and seller_app.py — the two apps
split out of the original order_app_pc.py so the buyer and the car
owner/seller each get their own app with their own login, matching their
actual separate roles (see SETUP_AND_ARCHITECTURE.md).
"""

import functools
import hashlib
import json
import os
import secrets
import struct
import time
from pathlib import Path

from flask import Response, request
from solana.rpc.api import Client
from solders.pubkey import Pubkey

# ---------------------------------------------------------------------------
# Config (shared)
# ---------------------------------------------------------------------------
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
PROGRAM_ID = os.getenv("DRONE_PROGRAM_ID", "3NmsWVX39uvzG3PBNPdSe4FTgudqSeLphJSbMDhV5F8Y")
OPERATOR_PUBKEY = os.getenv("OPERATOR_PUBKEY", "7VizNvqBSnHnP8ySnsjxxyUnBQCybVnJHBDRyvaThXia")
SELLER_PUBKEY = os.getenv("SELLER_PUBKEY", "7uoFeSG546UvK5HYyA97GVmJUTvrXWgGgkTgxspH4d1C")

DELIVERY_AMOUNT_SOL = float(os.getenv("DELIVERY_AMOUNT_SOL", "0.20"))
DEADLINE_MINUTES = int(os.getenv("DEADLINE_MINUTES", "60"))
TARGET_LAT = float(os.getenv("TARGET_LAT", "52.3609"))
TARGET_LON = float(os.getenv("TARGET_LON", "14.0600"))

BOX_QR_CODE = os.getenv("BOX_QR_CODE", "ROBOPAY-BOX-C")
PICAR_SERVER_URL = os.getenv("PICAR_SERVER_URL", "")

DEVNET_EXPLORER = "https://explorer.solana.com/tx/{}?cluster=devnet"

STATE_FILE = Path(__file__).parent / "order_state.json"

TX_LABELS = {
    "create_delivery": "Buyer TX (Escrow-Einzahlung)",
    "confirm_delivery": "Escrow-Release TX (Auszahlung)",
    "cancel_delivery": "Cancel TX (Rueckerstattung)",
}

rpc = Client(SOLANA_RPC_URL)
program_id = Pubkey.from_string(PROGRAM_ID)
operator_pubkey = Pubkey.from_string(OPERATOR_PUBKEY)


def disc(name: str) -> bytes:
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]


def derive_escrow_pda() -> Pubkey:
    pda, _ = Pubkey.find_program_address([b"escrow", bytes(operator_pubkey)], program_id)
    return pda


def get_balance_sol(pubkey_str: str):
    try:
        bal = rpc.get_balance(Pubkey.from_string(pubkey_str))
        return round(bal.value / 1e9, 4)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Shared state file (order_state.json) - both apps read it; only buyer_app
# writes to active_order/tx_history for create/cancel, car_main.py's
# /delivered call (proxied through buyer_app) appends confirm_delivery.
# ---------------------------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        d = json.loads(STATE_FILE.read_text())
        return d.get("active_order"), d.get("tx_history", [])
    return None, []


def save_state(active_order, tx_history):
    STATE_FILE.write_text(json.dumps({"active_order": active_order, "tx_history": tx_history}))


# ---------------------------------------------------------------------------
# HTTP Basic Auth - username/password set via env vars, exempts the
# machine-to-machine endpoints car_main.py calls directly (it has no
# concept of HTTP auth, and these aren't sensitive on their own - they
# only expose/accept order status, not wallet actions).
# ---------------------------------------------------------------------------
def make_auth(app, username_env, password_env, exempt_paths=()):
    username = os.environ.get(username_env)
    password = os.environ.get(password_env)
    if not username or not password:
        raise RuntimeError(f"Set {username_env} and {password_env} before starting this app.")

    @app.before_request
    def _check_auth():
        if request.path in exempt_paths:
            return None
        auth = request.authorization
        ok = auth and secrets.compare_digest(auth.username, username) and secrets.compare_digest(auth.password, password)
        if not ok:
            return Response(
                "Login erforderlich", 401,
                {"WWW-Authenticate": 'Basic realm="RoboPay"'},
            )
        return None

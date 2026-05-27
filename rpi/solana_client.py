import hashlib
import json
import logging
import struct
import time
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.instruction import AccountMeta, Instruction
from solders.message import Message
from solders.transaction import Transaction
from solana.rpc.api import Client

import config as cfg

log = logging.getLogger(__name__)


def _disc(name: str) -> bytes:
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]


CONFIRM_DELIVERY_DISC = _disc("confirm_delivery")
CLOSE_ESCROW_DISC = _disc("close_escrow")


def _load_keypair(path):
    data = json.loads(Path(path).read_text())
    return Keypair.from_bytes(bytes(data))


class SolanaClient:
    def __init__(self, rpc_url, keypair_path, program_id):
        self._rpc = Client(rpc_url)
        self._keypair = _load_keypair(keypair_path)
        self._program_id = Pubkey.from_string(program_id)
        log.info("Drone operator wallet: %s", self._keypair.pubkey())

    def derive_escrow_pda(self) -> Pubkey:
        pda, _ = Pubkey.find_program_address(
            [b"escrow", bytes(self._keypair.pubkey())], self._program_id
        )
        return pda

    def confirm_delivery(self, actual_lat: float, actual_lon: float, timestamp: int = None) -> str:
        """GPS-verified payment release: escrow → seller."""
        ts = int(timestamp or time.time())
        data = (CONFIRM_DELIVERY_DISC
                + struct.pack("<qqq", int(actual_lat * 1e7), int(actual_lon * 1e7), ts))

        escrow_pda = self.derive_escrow_pda()
        seller = Pubkey.from_string(cfg.SELLER_PUBKEY)

        accounts = [
            AccountMeta(pubkey=escrow_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self._keypair.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=seller, is_signer=False, is_writable=True),
        ]
        ix = Instruction(program_id=self._program_id, accounts=accounts, data=data)
        blockhash = self._rpc.get_latest_blockhash().value.blockhash
        msg = Message.new_with_blockhash([ix], self._keypair.pubkey(), blockhash)
        tx = Transaction([self._keypair], msg, blockhash)
        sig = str(self._rpc.send_transaction(tx).value)
        log.info("confirm_delivery TX: %s", sig)
        return sig

    def close_escrow(self) -> str:
        """Close delivered escrow and reclaim rent to drone operator."""
        escrow_pda = self.derive_escrow_pda()
        accounts = [
            AccountMeta(pubkey=escrow_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self._keypair.pubkey(), is_signer=True, is_writable=True),
        ]
        ix = Instruction(program_id=self._program_id, accounts=accounts, data=CLOSE_ESCROW_DISC)
        blockhash = self._rpc.get_latest_blockhash().value.blockhash
        msg = Message.new_with_blockhash([ix], self._keypair.pubkey(), blockhash)
        tx = Transaction([self._keypair], msg, blockhash)
        sig = str(self._rpc.send_transaction(tx).value)
        log.info("close_escrow TX: %s", sig)
        return sig

    def confirm_transaction(self, signature: str, timeout: float = 60.0) -> bool:
        sig_obj = Signature.from_string(signature)
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self._rpc.get_signature_statuses([sig_obj])
            status = resp.value[0]
            if status:
                if status.err is not None:
                    log.error("TX failed on-chain: %s", status.err)
                    return False
                if status.confirmation_status:
                    return True
            time.sleep(2.0)
        log.warning("TX confirmation timeout: %s", signature)
        return False

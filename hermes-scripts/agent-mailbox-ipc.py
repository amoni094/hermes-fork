#!/usr/bin/env python3
"""
agent-mailbox-ipc.py — File-based encrypted agent-to-agent IPC for Hermes sessions.

Subcommands:
  send     <recipient> <message>   Encrypt and deliver a message.
  receive  <recipient>             Decrypt and consume unread messages.
  list     <recipient>             Show unread message metadata (no decryption).
  purge    <recipient>             Delete read/ messages older than 24 h.

Encryption: AESGCM (via `cryptography` package).
Fallback:   XOR + BLAKE2b keystream (stdlib only, noted in output).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MAILBOX_ROOT = Path.home() / ".hermes" / "cache" / "mailbox"
SESSION_KEY_FILE = MAILBOX_ROOT / ".session_key"

# ---------------------------------------------------------------------------
# Crypto backend selection
# ---------------------------------------------------------------------------
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM  # type: ignore[assignment]
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF as _HKDF  # type: ignore[assignment]
    from cryptography.hazmat.primitives import hashes as _hashes  # type: ignore[assignment]

    CRYPTO_AVAILABLE = True
except ImportError:
    _AESGCM = None  # type: ignore[assignment,misc]
    _HKDF = None  # type: ignore[assignment,misc]
    _hashes = None  # type: ignore[assignment]
    CRYPTO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Session key derivation / storage
# ---------------------------------------------------------------------------

def _get_session_seed() -> bytes:
    """Return a stable 32-byte seed shared across all agents in this Hermes session.

    Priority:
    1. ~/.hermes/cache/mailbox/.session_key file (created on first call).
       If HERMES_SESSION_ID is set when the file is first created, the ID is
       mixed in via BLAKE2b so the seed is session-scoped.
    2. Pure-random fallback written to the key file for reuse.

    All agents on the same filesystem read the same file → same seed → can
    decrypt each other's messages.  HERMES_SESSION_ID is used only as the
    *sender label*, not as the solo key source.
    """
    MAILBOX_ROOT.mkdir(parents=True, exist_ok=True)
    if SESSION_KEY_FILE.exists():
        raw = SESSION_KEY_FILE.read_bytes()
        if len(raw) == 32:
            return raw

    # First-time creation: optionally mix in the session ID
    session_id = os.environ.get("HERMES_SESSION_ID", "")
    random_part = secrets.token_bytes(32)
    if session_id:
        seed = hashlib.blake2b(
            random_part + session_id.encode(), digest_size=32
        ).digest()
    else:
        seed = random_part

    SESSION_KEY_FILE.write_bytes(seed)
    SESSION_KEY_FILE.chmod(0o600)
    return seed


def _derive_key(seed: bytes) -> bytes:
    """Derive a 32-byte AES key from seed (HKDF-SHA256 when available, else BLAKE2b)."""
    if CRYPTO_AVAILABLE:
        hkdf = _HKDF(  # type: ignore[operator]
            algorithm=_hashes.SHA256(),  # type: ignore[union-attr]
            length=32,
            salt=b"hermes-mailbox-v1",
            info=b"aesgcm-session-key",
        )
        return hkdf.derive(seed)
    # Fallback: BLAKE2b stretch
    return hashlib.blake2b(seed, digest_size=32,
                           salt=b"hermes-mb"[:16], person=b"session-key"[:16]).digest()


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _encrypt_aesgcm(key: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
    """Return (nonce, ciphertext+tag)."""
    nonce = secrets.token_bytes(12)
    aesgcm = _AESGCM(key)  # type: ignore[operator]
    ct = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce, ct


def _decrypt_aesgcm(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    aesgcm = _AESGCM(key)  # type: ignore[operator]
    return aesgcm.decrypt(nonce, ciphertext, aad)


def _xor_keystream(seed: bytes, nonce: bytes, data: bytes) -> bytes:
    """XOR data against a BLAKE2b-derived keystream (fallback, not authenticated)."""
    key = hashlib.blake2b(seed, digest_size=32).digest()
    out = bytearray(len(data))
    block_size = 32
    offset = 0
    block_idx = 0
    while offset < len(data):
        # Mix nonce + block index into each keystream block
        block_key = hashlib.blake2b(
            key + nonce + block_idx.to_bytes(4, "little"), digest_size=32
        ).digest()
        chunk = data[offset : offset + block_size]
        for i, b in enumerate(chunk):
            out[offset + i] = b ^ block_key[i % block_size]
        offset += block_size
        block_idx += 1
    return bytes(out)


def encrypt_message(plaintext: bytes, aad: bytes, seed: bytes) -> tuple[bytes, bytes]:
    """Return (nonce_bytes, ciphertext_bytes). Uses AESGCM or XOR fallback."""
    key = _derive_key(seed)
    if CRYPTO_AVAILABLE:
        return _encrypt_aesgcm(key, plaintext, aad)
    nonce = secrets.token_bytes(12)
    ct = _xor_keystream(seed, nonce, plaintext)
    return nonce, ct


def decrypt_message(nonce: bytes, ciphertext: bytes, aad: bytes, seed: bytes) -> bytes:
    key = _derive_key(seed)
    if CRYPTO_AVAILABLE:
        return _decrypt_aesgcm(key, nonce, ciphertext, aad)
    return _xor_keystream(seed, nonce, ciphertext)


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_send(args: argparse.Namespace) -> None:
    recipient: str = args.recipient
    message_text: str = args.message

    sender = os.environ.get("HERMES_SESSION_ID", "unknown")
    seed = _get_session_seed()

    aad_str = sender + recipient
    aad = aad_str.encode()
    plaintext = message_text.encode()

    nonce, ciphertext = encrypt_message(plaintext, aad, seed)

    ts = time.time()
    ts_int = int(ts * 1000)  # millisecond precision for uniqueness
    nonce_hex = nonce.hex()
    filename = f"{ts_int}_{nonce_hex[:8]}.json"

    dest_dir = MAILBOX_ROOT / recipient
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / filename

    payload = {
        "sender": sender,
        "recipient": recipient,
        "ts": ts,
        "nonce_hex": nonce_hex,
        "ciphertext_hex": ciphertext.hex(),
        "aad": aad_str,
    }
    _dest_tmp = dest_file.with_suffix(".json.tmp")
    _dest_tmp.write_text(json.dumps(payload, indent=2))
    _dest_tmp.replace(dest_file)

    backend = "AESGCM" if CRYPTO_AVAILABLE else "XOR+BLAKE2b(fallback)"
    print(f"[send] → {recipient}  file={filename}  backend={backend}")


def cmd_receive(args: argparse.Namespace) -> None:
    recipient: str = args.recipient
    seed = _get_session_seed()

    inbox_dir = MAILBOX_ROOT / recipient
    if not inbox_dir.exists():
        print(f"[receive] No mailbox for '{recipient}'.")
        return

    read_dir = inbox_dir / "read"
    read_dir.mkdir(exist_ok=True)

    files = sorted(
        f for f in inbox_dir.glob("*.json") if f.is_file()
    )
    if not files:
        print(f"[receive] No unread messages for '{recipient}'.")
        return

    backend = "AESGCM" if CRYPTO_AVAILABLE else "XOR+BLAKE2b(fallback, NOT authenticated)"
    for f in files:
        try:
            payload = json.loads(f.read_text())
            nonce = bytes.fromhex(payload["nonce_hex"])
            ciphertext = bytes.fromhex(payload["ciphertext_hex"])
            aad = payload["aad"].encode()
            plaintext = decrypt_message(nonce, ciphertext, aad, seed)
            text = plaintext.decode()
            print(f"[receive] from={payload['sender']}  ts={payload['ts']:.3f}  backend={backend}")
            print(f"  Message: {text}")
            shutil.move(str(f), str(read_dir / f.name))
        except Exception as exc:
            print(f"[receive] ERROR decrypting {f.name}: {exc}", file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> None:
    recipient: str = args.recipient
    inbox_dir = MAILBOX_ROOT / recipient

    if not inbox_dir.exists():
        print(f"[list] No mailbox for '{recipient}'.")
        return

    files = sorted(f for f in inbox_dir.glob("*.json") if f.is_file())
    if not files:
        print(f"[list] No unread messages for '{recipient}'.")
        return

    print(f"[list] Unread messages for '{recipient}':")
    for f in files:
        try:
            payload = json.loads(f.read_text())
            print(f"  {f.name}  sender={payload.get('sender','?')}  ts={payload.get('ts','?')}")
        except Exception:
            print(f"  {f.name}  (unreadable metadata)")


def cmd_purge(args: argparse.Namespace) -> None:
    recipient: str = args.recipient
    read_dir = MAILBOX_ROOT / recipient / "read"

    if not read_dir.exists():
        print(f"[purge] No read/ directory for '{recipient}'.")
        return

    cutoff = time.time() - 86400  # 24 hours
    removed = 0
    for f in read_dir.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    print(f"[purge] Removed {removed} read message(s) older than 24 h for '{recipient}'.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agent-mailbox-ipc",
        description="Encrypted file-based IPC mailbox for Hermes agents.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # send
    ps = sub.add_parser("send", help="Encrypt and deliver a message.")
    ps.add_argument("recipient", help="Recipient agent name.")
    ps.add_argument("message", help="Plaintext message to send.")

    # receive
    pr = sub.add_parser("receive", help="Decrypt and consume unread messages.")
    pr.add_argument("recipient", help="Recipient agent name.")

    # list
    pl = sub.add_parser("list", help="List unread message metadata (no decryption).")
    pl.add_argument("recipient", help="Recipient agent name.")

    # purge
    pp = sub.add_parser("purge", help="Delete read/ messages older than 24 h.")
    pp.add_argument("recipient", help="Recipient agent name.")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Ensure mailbox root exists
    MAILBOX_ROOT.mkdir(parents=True, exist_ok=True)

    dispatch = {
        "send": cmd_send,
        "receive": cmd_receive,
        "list": cmd_list,
        "purge": cmd_purge,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

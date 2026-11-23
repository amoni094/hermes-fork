#!/usr/bin/env python3
"""
secure-message.py — AES-GCM (or XOR+HMAC fallback) message encryption/decryption.

Tries to use: from cryptography.hazmat.primitives.ciphers.aead import AESGCM
Falls back to XOR+HMAC with a clear warning when the cryptography library is unavailable.

Functions:
  encrypt_message(plaintext: bytes, key: bytes) -> bytes
  decrypt_message(ciphertext: bytes, key: bytes) -> bytes

CLI:
  python3 secure-message.py encrypt --key <hex32> --message "hello"
  python3 secure-message.py decrypt --key <hex32> --ciphertext <hex>

Key must be exactly 32 bytes (256-bit), provided as hex.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import secrets
import sys

# ── Backend selection ─────────────────────────────────────────────────────────
_AESGCM = None  # type: ignore[assignment]
_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM  # type: ignore[assignment]
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    pass

_FALLBACK_WARNING = (
    "WARNING: cryptography library not available — using XOR+HMAC fallback. "
    "This is NOT secure AES-GCM. Install 'cryptography' for real encryption."
)

# ── AES-GCM backend ───────────────────────────────────────────────────────────

def _aesgcm_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-256-GCM: returns nonce(12) || ciphertext+tag."""
    aesgcm = _AESGCM(key)  # type: ignore[operator]
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ct


def _aesgcm_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """AES-256-GCM: expects nonce(12) || ciphertext+tag."""
    if len(ciphertext) < 12 + 16:
        raise ValueError("Ciphertext too short for AES-GCM (need nonce+tag).")
    aesgcm = _AESGCM(key)  # type: ignore[operator]
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    return aesgcm.decrypt(nonce, ct, None)


# ── XOR+HMAC fallback backend (NOT SECURE, clearly labelled) ─────────────────

def _xor_hmac_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    NOT SECURE AES — XOR+HMAC fallback only.
    Format: nonce(32) || xor_ciphertext || hmac_tag(32)
    """
    print(_FALLBACK_WARNING, file=sys.stderr)
    nonce = secrets.token_bytes(32)
    # XOR with SHA256(key || nonce || counter) keystream (single block — not for large data)
    ks = hashlib.sha256(key + nonce).digest()
    # Pad keystream with repeated hashing for longer plaintexts
    keystream = b""
    counter = 0
    while len(keystream) < len(plaintext):
        keystream += hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        counter += 1
    ct = bytes(p ^ k for p, k in zip(plaintext, keystream))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return nonce + ct + tag


def _xor_hmac_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """NOT SECURE AES — XOR+HMAC fallback only."""
    print(_FALLBACK_WARNING, file=sys.stderr)
    if len(ciphertext) < 64:
        raise ValueError("Ciphertext too short for XOR+HMAC fallback.")
    nonce = ciphertext[:32]
    tag = ciphertext[-32:]
    ct = ciphertext[32:-32]
    expected_tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        raise ValueError("HMAC verification failed — ciphertext tampered or wrong key.")
    keystream = b""
    counter = 0
    while len(keystream) < len(ct):
        keystream += hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(c ^ k for c, k in zip(ct, keystream))


# ── Public API ─────────────────────────────────────────────────────────────────

def encrypt_message(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt plaintext with key. Uses AES-GCM if available, else XOR+HMAC fallback."""
    if len(key) != 32:
        raise ValueError(f"Key must be exactly 32 bytes, got {len(key)}.")
    if _HAS_CRYPTOGRAPHY:
        return _aesgcm_encrypt(plaintext, key)
    return _xor_hmac_encrypt(plaintext, key)


def decrypt_message(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt ciphertext with key. Uses AES-GCM if available, else XOR+HMAC fallback."""
    if len(key) != 32:
        raise ValueError(f"Key must be exactly 32 bytes, got {len(key)}.")
    if _HAS_CRYPTOGRAPHY:
        return _aesgcm_decrypt(ciphertext, key)
    return _xor_hmac_decrypt(ciphertext, key)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_key(hex_str: str) -> bytes:
    try:
        key = bytes.fromhex(hex_str)
    except ValueError:
        print("[ERROR] Key must be a 64-char hex string (32 bytes).", file=sys.stderr)
        sys.exit(2)
    if len(key) != 32:
        print(f"[ERROR] Key must be exactly 32 bytes, got {len(key)}.", file=sys.stderr)
        sys.exit(2)
    return key


def cmd_encrypt(args: argparse.Namespace) -> int:
    key = _parse_key(args.key)
    plaintext = args.message.encode("utf-8")
    ct = encrypt_message(plaintext, key)
    backend = "AES-GCM" if _HAS_CRYPTOGRAPHY else "XOR+HMAC (NOT SECURE)"
    print(f"backend: {backend}")
    print(f"ciphertext: {ct.hex()}")
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    key = _parse_key(args.key)
    try:
        ct = bytes.fromhex(args.ciphertext)
    except ValueError:
        print("[ERROR] Ciphertext must be a hex string.", file=sys.stderr)
        return 2
    try:
        pt = decrypt_message(ct, key)
    except Exception as exc:
        print(f"[ERROR] Decryption failed: {exc}", file=sys.stderr)
        return 1
    backend = "AES-GCM" if _HAS_CRYPTOGRAPHY else "XOR+HMAC (NOT SECURE)"
    print(f"backend: {backend}")
    print(f"plaintext: {pt.decode('utf-8', errors='replace')}")
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    key = secrets.token_bytes(32)
    print(f"key (hex): {key.hex()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AES-GCM (or XOR+HMAC fallback) message encrypt/decrypt")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_enc = sub.add_parser("encrypt", help="Encrypt a message")
    p_enc.add_argument("--key", required=True, help="32-byte key as 64-char hex")
    p_enc.add_argument("--message", required=True, help="Plaintext message")

    p_dec = sub.add_parser("decrypt", help="Decrypt a ciphertext")
    p_dec.add_argument("--key", required=True, help="32-byte key as 64-char hex")
    p_dec.add_argument("--ciphertext", required=True, help="Ciphertext as hex")

    sub.add_parser("keygen", help="Generate a random 32-byte key (hex)")

    args = ap.parse_args()
    dispatch = {"encrypt": cmd_encrypt, "decrypt": cmd_decrypt, "keygen": cmd_keygen}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

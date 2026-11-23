#!/usr/bin/env python3
"""
session-token.py — HMAC-SHA256 session token generator/verifier.

token = HMAC-SHA256(master_key, session_id || timestamp_ns)

Master key: ~/.hermes/cache/session.key (auto-generated, chmod 600)

Subcommands:
  generate  — generate a new session token for a given session_id
  verify    — verify a token against a session_id + timestamp_ns

Usage:
  python3 session-token.py generate --session-id my-session
  python3 session-token.py verify --session-id my-session --ts 1234567890 --token <hex>
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import secrets
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
KEY_PATH = HERMES_HOME / "cache" / "session.key"


def _load_or_create_key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        raw = KEY_PATH.read_bytes()
        if len(raw) == 32:
            return raw
    key = secrets.token_bytes(32)
    KEY_PATH.write_bytes(key)
    KEY_PATH.chmod(0o600)
    print(f"[INFO] New session master key generated at {KEY_PATH}", file=sys.stderr)
    return key


def _compute_token(key: bytes, session_id: str, ts_ns: int) -> str:
    msg = (session_id + str(ts_ns)).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def cmd_generate(args: argparse.Namespace) -> int:
    key = _load_or_create_key()
    session_id = args.session_id.strip()
    ts_ns = time.time_ns()
    token = _compute_token(key, session_id, ts_ns)
    print(f"session_id: {session_id}")
    print(f"timestamp_ns: {ts_ns}")
    print(f"token: {token}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    key = _load_or_create_key()
    session_id = args.session_id.strip()
    token_provided = args.token.strip()
    try:
        ts_ns = int(args.ts)
    except (TypeError, ValueError):
        print(f"[ERROR] --ts must be an integer (nanoseconds)", file=sys.stderr)
        return 2

    expected = _compute_token(key, session_id, ts_ns)
    if hmac.compare_digest(expected, token_provided):
        print(f"[OK] Token VALID for session_id={session_id} ts={ts_ns}")
        return 0
    else:
        print(f"[FAIL] Token INVALID for session_id={session_id} ts={ts_ns}")
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="HMAC-SHA256 session token generator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="Generate a new session token")
    p_gen.add_argument("--session-id", required=True, help="Session identifier")

    p_ver = sub.add_parser("verify", help="Verify a token")
    p_ver.add_argument("--session-id", required=True, help="Session identifier")
    p_ver.add_argument("--ts", required=True, help="timestamp_ns from generation")
    p_ver.add_argument("--token", required=True, help="Token hex string to verify")

    args = ap.parse_args()
    dispatch = {"generate": cmd_generate, "verify": cmd_verify}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

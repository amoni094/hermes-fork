#!/usr/bin/env python3
"""
action-log.py — Append-only, hash-chained tamper-evident action log.

Format (JSONL): {ts, action, context_hash, prev_hash, entry_hash}
  entry_hash = SHA256(prev_hash || ts || action || context_hash)

Subcommands:
  log        — append a new entry to the log
  verify-chain — walk the log, check each hash chains correctly

Store: ~/.hermes/cache/action-log.jsonl

Usage:
  python3 action-log.py log --action "ran skill X" [--context-hash <hex>]
  python3 action-log.py verify-chain
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
LOG_PATH = HERMES_HOME / "cache" / "action-log.jsonl"

GENESIS_HASH = "0" * 64  # sentinel prev_hash for first entry


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _entry_hash(prev_hash: str, ts: str, action: str, context_hash: str) -> str:
    data = (prev_hash + ts + action + context_hash).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _last_entry_hash() -> str:
    if not LOG_PATH.exists():
        return GENESIS_HASH
    last_line = ""
    try:
        text = LOG_PATH.read_text(encoding="utf-8")
    except OSError:
        return GENESIS_HASH
    for line in text.splitlines():
        line = line.strip()
        if line:
            last_line = line
    if not last_line:
        return GENESIS_HASH
    try:
        entry = json.loads(last_line)
        return entry.get("entry_hash", GENESIS_HASH)
    except json.JSONDecodeError:
        return GENESIS_HASH


def cmd_log(args: argparse.Namespace) -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    action = args.action.strip()
    context_hash = (args.context_hash or "").strip() or hashlib.sha256(b"").hexdigest()
    ts = _now()
    prev_hash = _last_entry_hash()
    eh = _entry_hash(prev_hash, ts, action, context_hash)
    entry = {
        "ts": ts,
        "action": action,
        "context_hash": context_hash,
        "prev_hash": prev_hash,
        "entry_hash": eh,
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "entry_hash": eh, "prev_hash": prev_hash}, indent=2))
    return 0


def cmd_verify_chain(args: argparse.Namespace) -> int:
    if not LOG_PATH.exists():
        print("[INFO] No action log found — nothing to verify.")
        return 0
    try:
        lines = [l.strip() for l in LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError as exc:
        print(f"[ERROR] Cannot read log: {exc}", file=sys.stderr)
        return 1

    if not lines:
        print("[INFO] Log is empty.")
        return 0

    errors: list[str] = []
    expected_prev = GENESIS_HASH

    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"Line {i+1}: JSON parse error: {exc}")
            continue

        ts = entry.get("ts", "")
        action = entry.get("action", "")
        context_hash = entry.get("context_hash", "")
        prev_hash = entry.get("prev_hash", "")
        stored_eh = entry.get("entry_hash", "")

        # Check prev_hash continuity
        if prev_hash != expected_prev:
            errors.append(
                f"Line {i+1}: prev_hash mismatch — expected {expected_prev[:12]}…, "
                f"got {prev_hash[:12]}…"
            )

        # Recompute entry_hash
        recomputed = _entry_hash(prev_hash, ts, action, context_hash)
        if recomputed != stored_eh:
            errors.append(
                f"Line {i+1}: entry_hash mismatch — stored {stored_eh[:12]}…, "
                f"recomputed {recomputed[:12]}…"
            )

        expected_prev = stored_eh  # advance chain

    if errors:
        print(f"[FAIL] Chain broken — {len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"[OK] Chain verified — {len(lines)} entry/entries intact.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Append-only hash-chained action log")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("log", help="Append a new action entry")
    p_log.add_argument("--action", required=True, help="Action description")
    p_log.add_argument("--context-hash", default="", help="SHA256 hex of relevant context (optional)")

    sub.add_parser("verify-chain", help="Walk log and verify hash chain")

    args = ap.parse_args()
    dispatch = {"log": cmd_log, "verify-chain": cmd_verify_chain}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

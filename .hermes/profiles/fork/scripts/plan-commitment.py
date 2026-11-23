#!/usr/bin/env python3
"""
plan-commitment.py — SHA256 commitment scheme for agent plans.

Subcommands:
  commit  — read plan from --plan arg or stdin, generate nonce, store commitment
  verify  — check a plan against a stored commitment file
  reveal  — print the nonce from a stored commitment file (for audit)

Store: ~/.hermes/cache/plan-commitments/<timestamp>.json
  Schema: {commitment, nonce, ts}
  commitment = SHA256(nonce || plan_bytes)
  nonce = secrets.token_bytes(32), stored as hex

Usage:
  echo "my plan" | python3 plan-commitment.py commit
  python3 plan-commitment.py commit --plan "my plan"
  python3 plan-commitment.py verify --file <path> --plan "my plan"
  python3 plan-commitment.py reveal --file <path>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
COMMITMENTS_DIR = HERMES_HOME / "cache" / "plan-commitments"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _compute_commitment(nonce_bytes: bytes, plan_bytes: bytes) -> str:
    return hashlib.sha256(nonce_bytes + plan_bytes).hexdigest()


def cmd_commit(args: argparse.Namespace) -> int:
    if args.plan:
        plan_text = args.plan
    else:
        plan_text = sys.stdin.read()

    if not plan_text.strip():
        print("[ERROR] Plan is empty.", file=sys.stderr)
        return 2

    plan_bytes = plan_text.encode("utf-8")
    nonce = secrets.token_bytes(32)
    commitment = _compute_commitment(nonce, plan_bytes)
    ts = _now_ts()

    COMMITMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = COMMITMENTS_DIR / f"{ts}.json"
    record = {
        "commitment": commitment,
        "nonce": nonce.hex(),
        "ts": ts,
    }
    _tmp = out_path.with_suffix('.tmp')
    _tmp.write_text(json.dumps(record, indent=2), encoding='utf-8')
    _tmp.replace(out_path)
    print(json.dumps({
        "ok": True,
        "commitment": commitment,
        "file": str(out_path),
        "ts": ts,
    }, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    if not args.file:
        print("[ERROR] --file is required for verify.", file=sys.stderr)
        return 2
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] Commitment file not found: {file_path}", file=sys.stderr)
        return 2

    try:
        record = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ERROR] Cannot read commitment file: {exc}", file=sys.stderr)
        return 2

    if args.plan:
        plan_text = args.plan
    else:
        plan_text = sys.stdin.read()

    if not plan_text.strip():
        print("[ERROR] Plan is empty.", file=sys.stderr)
        return 2

    plan_bytes = plan_text.encode("utf-8")
    try:
        nonce = bytes.fromhex(record["nonce"])
    except (KeyError, ValueError) as exc:
        print(f"[ERROR] Invalid nonce in commitment file: {exc}", file=sys.stderr)
        return 2

    recomputed = _compute_commitment(nonce, plan_bytes)
    stored = record.get("commitment", "")

    if recomputed == stored:
        print(json.dumps({
            "ok": True,
            "match": True,
            "commitment": stored,
            "file": str(file_path),
        }, indent=2))
        return 0
    else:
        print(json.dumps({
            "ok": False,
            "match": False,
            "stored_commitment": stored,
            "recomputed_commitment": recomputed,
            "file": str(file_path),
        }, indent=2))
        return 1


def cmd_reveal(args: argparse.Namespace) -> int:
    if not args.file:
        print("[ERROR] --file is required for reveal.", file=sys.stderr)
        return 2
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] Commitment file not found: {file_path}", file=sys.stderr)
        return 2

    try:
        record = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ERROR] Cannot read commitment file: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "file": str(file_path),
        "nonce": record.get("nonce"),
        "commitment": record.get("commitment"),
        "ts": record.get("ts"),
        "note": "nonce revealed for audit; commitment is SHA256(nonce_bytes || plan_bytes)",
    }, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SHA256 plan commitment scheme")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_commit = sub.add_parser("commit", help="Commit to a plan (reads stdin or --plan)")
    p_commit.add_argument("--plan", default="", help="Plan text (or pipe via stdin)")

    p_verify = sub.add_parser("verify", help="Verify a plan against a stored commitment")
    p_verify.add_argument("--file", required=True, help="Path to commitment JSON file")
    p_verify.add_argument("--plan", default="", help="Plan text to verify (or pipe via stdin)")

    p_reveal = sub.add_parser("reveal", help="Reveal the nonce from a commitment file")
    p_reveal.add_argument("--file", required=True, help="Path to commitment JSON file")

    args = ap.parse_args()
    dispatch = {"commit": cmd_commit, "verify": cmd_verify, "reveal": cmd_reveal}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

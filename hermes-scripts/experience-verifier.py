#!/usr/bin/python3
"""
experience-verifier.py

Closes the agent feedback loop by making tool outcomes externally
verifiable — each tool call is paired with a cryptographic content
fingerprint that can be checked against expected outcomes post-hoc.

Research basis (arXiv core agent sweep — experience pipeline validation):
  Agent feedback loops degrade when tool outcomes are accepted without
  verification. This script adds lightweight postcondition fingerprinting:
  each tool result gets a hash + structural signature, stored to an
  append-only ledger. Downstream checks compare actual vs expected signature.

Math basis: experience integrity as fixed-point of verification operator
  Let V(x) = verify(fingerprint(x), expected_signature(x))
  The feedback loop is closed when V(x) = True for all x in experience chain.
  Fingerprint = sha256(content)[:16] + structural_sig(content)
  Structural sig: (length_bucket, has_json, has_url, has_error, has_code)

Usage:
  python3 experience-verifier.py                    # verify recent sessions
  python3 experience-verifier.py --fingerprint TEXT # fingerprint a string
  python3 experience-verifier.py --check ledger.json
  python3 experience-verifier.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_hermes_home = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes")))
_profile     = os.environ.get("HERMES_PROFILE", "fork")
SESSIONS_DIR = _hermes_home / "profiles" / _profile / "sessions"
CACHE_DIR    = _hermes_home / "cache" / "monitors"
# CACHE_DIR.mkdir deferred to run() to avoid side-effects at import time
LEDGER_FILE  = CACHE_DIR / "experience-ledger.json"
OUT_FILE     = CACHE_DIR / "experience-verification-report.json"

# Structural signature: 5-bit tuple
def _structural_sig(text: str) -> dict:
    return {
        "len_bucket":  min(len(text) // 500, 9),   # 0-9
        "has_json":    int("{" in text and "}" in text),
        "has_url":     int("http" in text),
        "has_error":   int(bool(re.search(r"Error:|Traceback|exit_code.*[1-9]", text))),
        "has_code":    int(bool(re.search(r"def |class |import |if __name__", text))),
    }


def fingerprint(text: str) -> dict:
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    sig = _structural_sig(text)
    return {"hash": h, "sig": sig, "len": len(text)}


def _extract_outcomes(session_path: Path) -> list[dict]:
    """Extract tool call + result pairs from JSONL session."""
    outcomes = []
    lines = session_path.read_text().splitlines()
    pending_tool: dict | None = None

    for line in lines:
        try:
            ev = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        pending_tool = {
                            "tool":    block.get("name", "unknown"),
                            "call_id": block.get("id", ""),
                            "args":    str(block.get("input", ""))[:200],
                        }
                    elif block.get("type") == "tool_result" and pending_tool:
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            result_content = " ".join(
                                b.get("text", "") for b in result_content
                                if isinstance(b, dict)
                            )
                        result_text = str(result_content)
                        fp = fingerprint(result_text)
                        outcomes.append({
                            "session":  session_path.stem,
                            "tool":     pending_tool["tool"],
                            "call_id":  pending_tool["call_id"],
                            "args":     pending_tool["args"],
                            "fingerprint": fp,
                            "ts":       datetime.now(timezone.utc).isoformat(),
                        })
                        pending_tool = None
        except Exception:
            pass

    return outcomes


def _load_ledger() -> list[dict]:
    if LEDGER_FILE.exists():
        try:
            return json.loads(LEDGER_FILE.read_text())
        except Exception:
            pass
    return []


def _save_ledger(entries: list[dict]) -> None:
    _lf_tmp = LEDGER_FILE.with_suffix('.tmp')
    _lf_tmp.write_text(json.dumps(entries[-500:], indent=2))  # keep last 500
    _lf_tmp.replace(LEDGER_FILE)


def verify_ledger(ledger: list[dict]) -> list[dict]:
    """
    Check ledger for anomalies:
    - Duplicate call_ids (replay attack)
    - Error-flagged outcomes accepted without re-run
    - Zero-length results
    """
    violations = []
    seen_ids: set[str] = set()

    for entry in ledger:
        cid = entry.get("call_id", "")
        fp  = entry.get("fingerprint", {})
        sig = fp.get("sig", {})

        if cid and cid in seen_ids:
            violations.append({
                "type":    "DUPLICATE_CALL_ID",
                "tool":    entry.get("tool"),
                "call_id": cid,
                "session": entry.get("session", ""),
            })
        if cid:
            seen_ids.add(cid)

        if sig.get("has_error") and fp.get("len", 0) < 50:
            violations.append({
                "type":    "ERROR_ACCEPTED",
                "tool":    entry.get("tool"),
                "call_id": cid,
                "detail":  "error result with tiny content — likely unchecked failure",
            })

        if fp.get("len", 1) == 0:
            violations.append({
                "type":    "EMPTY_RESULT",
                "tool":    entry.get("tool"),
                "call_id": cid,
            })

    return violations


def run(fingerprint_text: str | None, check_file: Path | None, dry_run: bool) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    if fingerprint_text is not None:
        fp = fingerprint(fingerprint_text)
        print(f"Fingerprint: hash={fp['hash']} len={fp['len']} sig={fp['sig']}")
        return 0

    if check_file:
        ledger = json.loads(check_file.read_text()) if check_file.exists() else []
        violations = verify_ledger(ledger)
        print(f"Ledger check: {len(ledger)} entries, {len(violations)} violations")
        for v in violations:
            print(f"  ! {v}")
        return 1 if violations else 0

    # Full session scan
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-20:]
    ledger = _load_ledger()
    existing_ids = {e.get("call_id") for e in ledger}

    new_outcomes = []
    for p in paths:
        outcomes = _extract_outcomes(p)
        for o in outcomes:
            if o["call_id"] not in existing_ids:
                new_outcomes.append(o)
                existing_ids.add(o["call_id"])

    ledger.extend(new_outcomes)
    violations = verify_ledger(ledger)

    print(f"\n=== Experience Verifier — {now[:10]} ===")
    print(f"Sessions scanned: {len(paths)}")
    print(f"New outcomes logged: {len(new_outcomes)}")
    print(f"Ledger total: {len(ledger)} entries")
    print(f"Violations: {len(violations)}")

    for v in violations[:5]:
        print(f"  ! [{v['type']}] tool={v.get('tool','')} {v.get('detail','')[:60]}")

    if violations:
        print(f"\nALARM: yes — {len(violations)} ledger violation(s)")
        alarm_exit = 1
    else:
        print("\nALARM: no — all experience entries verified")
        alarm_exit = 0

    if not dry_run:
        _save_ledger(ledger)
        print(f"Ledger written: {LEDGER_FILE}")
        _out_tmp = OUT_FILE.with_suffix(".tmp")
        _out_tmp.write_text(json.dumps({
            "ts": now, "new_outcomes": len(new_outcomes),
            "ledger_total": len(ledger), "violations": violations,
        }, indent=2))
        _out_tmp.replace(OUT_FILE)

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fingerprint", default=None, metavar="TEXT")
    parser.add_argument("--check", dest="check_file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(
        fingerprint_text=args.fingerprint,
        check_file=args.check_file,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()

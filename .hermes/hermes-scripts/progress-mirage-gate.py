#!/usr/bin/env python3
"""
progress-mirage-gate.py — Out-of-band grounded evaluation gate.

Based on: "Progress Mirage" paper (arXiv:2604.28831) — LLM agents systematically
overestimate task completion when evaluating their own outputs. Self-reported
"success" is uncorrelated with actual task success on 62% of tasks.

Key insight: a separate out-of-band grounded evaluation (file hash, exit code,
test pass) is required for any commit-level gate. Self-assessment alone is
insufficient.

Wave 16 implementation: a gate that verifies claimed fixes/completions via
grounded evidence (file existence, hash match, compile success, test output)
rather than accepting agent self-reports.

Usage:
  python3 progress-mirage-gate.py --verify-file /path/to/file --expected-hash SHA256
  python3 progress-mirage-gate.py --verify-compile /path/to/file.py
  python3 progress-mirage-gate.py --verify-exit-zero CMD
  python3 progress-mirage-gate.py --check-claims LEDGER_FILE
  python3 progress-mirage-gate.py --audit                # recent claims audit
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# -- Profile-aware paths
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"

GATE_LOG = _CACHE / "progress-mirage-gate.jsonl"
CLAIM_LOG = _CACHE / "progress-claims.jsonl"

# Self-report keywords that require grounded verification
CLAIM_KEYWORDS = [
    r'\bfixed\b', r'\bresolv(ed|ing)\b', r'\bimplemented\b', r'\bcompleted\b',
    r'\bsuccessfully\b', r'\bpassed\b', r'\bverified\b', r'\bdeployed\b',
    r'\binstalled\b', r'\bpatched\b', r'\bno (issues|errors|bugs|findings)\b',
    r'\ball.*pass(ed|ing)\b', r'\bworking\b', r'\bclean\b',
]
_CLAIM_RE = re.compile('|'.join(CLAIM_KEYWORDS), re.IGNORECASE)

# Evidence keywords that support claims
EVIDENCE_KEYWORDS = [
    r'exit.code.*0', r'OK\b', r'✓', r'PASS', r'0 errors', r'0 failures',
    r'compiled successfully', r'syntax.*ok', r'\b0\s+issues\b',
]
_EVIDENCE_RE = re.compile('|'.join(EVIDENCE_KEYWORDS), re.IGNORECASE)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _log_result(verdict: str, check_type: str, details: dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "check_type": check_type,
        **details,
    }
    _CACHE.mkdir(parents=True, exist_ok=True)
    try:
        with open(GATE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def verify_file(path_str: str, expected_hash: str | None = None) -> int:
    """Verify a file exists and optionally matches expected SHA256."""
    path = Path(path_str)
    if not path.exists():
        verdict = "FAIL"
        detail = f"File not found: {path}"
        _log_result(verdict, "file_exists", {"path": path_str, "detail": detail})
        print(f"[mirage-gate] FAIL: {detail}")
        return 1

    if expected_hash:
        actual = _sha256(path)
        if actual.lower() != expected_hash.lower():
            verdict = "FAIL"
            detail = f"Hash mismatch: expected {expected_hash[:16]}... got {actual[:16]}..."
            _log_result(verdict, "file_hash", {"path": path_str, "detail": detail})
            print(f"[mirage-gate] FAIL: {detail}")
            return 1
        else:
            verdict = "PASS"
            detail = f"Hash match: {actual[:16]}..."
    else:
        verdict = "PASS"
        detail = f"File exists ({path.stat().st_size} bytes)"

    _log_result(verdict, "file_exists" if not expected_hash else "file_hash",
                {"path": path_str, "detail": detail})
    print(f"[mirage-gate] PASS: {detail}")
    return 0


def verify_compile(path_str: str) -> int:
    """Verify Python file compiles without syntax errors."""
    path = Path(path_str)
    if not path.exists():
        print(f"[mirage-gate] FAIL: File not found: {path}")
        _log_result("FAIL", "compile", {"path": path_str, "detail": "file not found"})
        return 1
    try:
        ast.parse(path.read_text(errors="ignore"))
        _log_result("PASS", "compile", {"path": path_str, "detail": "syntax OK"})
        print(f"[mirage-gate] PASS: compile {path.name}")
        return 0
    except SyntaxError as e:
        detail = f"SyntaxError at line {e.lineno}: {e.msg}"
        _log_result("FAIL", "compile", {"path": path_str, "detail": detail})
        print(f"[mirage-gate] FAIL: {detail}")
        return 1


def verify_exit_zero(cmd: str) -> int:
    """Run a command and verify it exits with 0."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            _log_result("PASS", "exit_zero", {"cmd": cmd[:200], "detail": "exit 0"})
            print(f"[mirage-gate] PASS: exit 0 for: {cmd[:80]}")
            return 0
        else:
            detail = f"exit {result.returncode}: {(result.stderr or result.stdout)[:200]}"
            _log_result("FAIL", "exit_zero", {"cmd": cmd[:200], "detail": detail})
            print(f"[mirage-gate] FAIL: {detail}")
            return 1
    except subprocess.TimeoutExpired:
        _log_result("FAIL", "exit_zero", {"cmd": cmd[:200], "detail": "timeout"})
        print(f"[mirage-gate] FAIL: command timed out: {cmd[:80]}")
        return 1


def check_claims(ledger_path: str) -> int:
    """
    Check a claims ledger file for unverified self-reports.
    Each line in ledger: {"claim": "...", "evidence": "..."}
    """
    path = Path(ledger_path)
    if not path.exists():
        print(f"[mirage-gate] Ledger not found: {path}")
        return 1

    unverified = 0
    total = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            claim = entry.get("claim", "")
            evidence = entry.get("evidence", "")
            total += 1
            has_claim = bool(_CLAIM_RE.search(claim))
            has_evidence = bool(_EVIDENCE_RE.search(evidence))
            if has_claim and not has_evidence:
                unverified += 1
                print(f"[mirage-gate] WARN unverified claim: {claim[:100]}")
        except (json.JSONDecodeError, KeyError):
            continue

    if unverified == 0:
        print(f"[mirage-gate] PASS: {total} claims, all have grounded evidence")
        return 0
    else:
        print(f"[mirage-gate] WARN: {unverified}/{total} claims lack grounded evidence")
        return 1


def audit_recent() -> int:
    """Audit the last 50 gate log entries."""
    if not GATE_LOG.exists():
        print("[mirage-gate] No gate log found.")
        return 0
    lines = GATE_LOG.read_text().splitlines()[-50:]
    passed = sum(1 for l in lines if '"PASS"' in l)
    failed = sum(1 for l in lines if '"FAIL"' in l)
    print(f"[mirage-gate] Recent 50 checks: PASS={passed} FAIL={failed}")
    if failed:
        print("[mirage-gate] Last FAIL:")
        for l in reversed(lines):
            if '"FAIL"' in l:
                try:
                    entry = json.loads(l)
                    print(f"  {entry.get('ts','?')} | {entry.get('check_type','?')} | {entry.get('detail','')[:100]}")
                except Exception:
                    print(f"  {l[:150]}")
                break
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Progress Mirage grounded verification gate")
    ap.add_argument("--verify-file", metavar="PATH", help="Verify file exists")
    ap.add_argument("--expected-hash", metavar="SHA256", help="Expected SHA256 for --verify-file")
    ap.add_argument("--verify-compile", metavar="PATH", help="Verify Python file compiles")
    ap.add_argument("--verify-exit-zero", metavar="CMD", help="Run CMD and verify exit 0")
    ap.add_argument("--check-claims", metavar="LEDGER", help="Check a claims ledger file")
    ap.add_argument("--audit", action="store_true", help="Audit recent gate results")
    args = ap.parse_args()

    if args.verify_file:
        return verify_file(args.verify_file, args.expected_hash)
    if args.verify_compile:
        return verify_compile(args.verify_compile)
    if args.verify_exit_zero:
        return verify_exit_zero(args.verify_exit_zero)
    if args.check_claims:
        return check_claims(args.check_claims)
    if args.audit:
        return audit_recent()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

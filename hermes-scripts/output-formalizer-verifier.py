#!/usr/bin/env python3
"""Output formalizer/verifier: JSON, completeness, repetition, emptiness."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import hashlib
import json
import sqlite3
import sys

LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")


def _read_text(args) -> str:
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def check_json_valid(output: str) -> str | None:
    s = (output or "").lstrip()
    if not s:
        return None
    if s[0] not in "{[":
        return None
    try:
        json.loads(s)
        return None
    except Exception:
        return "json_invalid"


def check_complete_sentences(output: str) -> str | None:
    t = (output or "").rstrip()
    if not t:
        return "incomplete_sentence"
    if t.endswith(".") or t.endswith("!") or t.endswith("?"):
        return None
    if t.endswith("```") or t.endswith("}"):
        return None
    return "incomplete_sentence"


def check_no_repetition(output: str) -> str | None:
    toks = (output or "").split()
    if len(toks) < 8:
        return None
    counts = {}
    for i in range(len(toks) - 7):
        gram = tuple(toks[i:i + 8])
        counts[gram] = counts.get(gram, 0) + 1
        if counts[gram] > 3:
            return "repetition"
    return None


def check_non_empty(output: str) -> str | None:
    if len((output or "").strip()) > 0:
        return None
    return "empty"


def verify(output: str) -> dict:
    violations = []
    for fn in (check_non_empty, check_json_valid, check_complete_sentences, check_no_repetition):
        v = fn(output)
        if v:
            violations.append(v)
    digest = hashlib.sha256((output or "").encode("utf-8")).hexdigest()
    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "output_hash": digest,
    }


def _log_violations(result: dict) -> None:
    if result.get("valid"):
        return
    conn = sqlite3.connect(str(LIFECYCLE_DB))
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS output_violations(
            id INTEGER PRIMARY KEY,
            ts TEXT,
            output_hash TEXT,
            violation_type TEXT)"""
        )
        for vt in result.get("violations") or []:
            conn.execute(
                """INSERT INTO output_violations (ts, output_hash, violation_type)
                VALUES (datetime('now'), ?, ?)""",
                (result.get("output_hash"), vt),
            )
        conn.commit()
    finally:
        conn.close()


def self_test() -> dict:
    gram = "alpha beta gamma delta epsilon zeta eta theta"
    repeated = (gram + " ") * 6
    r = verify(repeated.strip() + ".")
    assert "repetition" in r["violations"], r
    empty = verify("   ")
    assert "empty" in empty["violations"], empty
    ok = verify("This is a complete sentence.")
    assert ok["valid"] is True, ok
    return {"self_test": "PASS", "repetition": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--text", default=None)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    try:
        text = _read_text(args)
        result = verify(text)
        try:
            _log_violations(result)
        except Exception:
            pass
        print(json.dumps(result))
    except Exception:
        pass


if __name__ == "__main__":
    main()

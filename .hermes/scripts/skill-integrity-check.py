#!/usr/bin/env python3
"""
skill-integrity-check.py — HMAC-SHA256 integrity baseline for all SKILL.md files.

Subcommands:
  generate  — scan all SKILL.md files, compute MACs, write baseline
  verify    — compare current files against baseline, report mismatches
  update    — regenerate MACs only for files that have changed

Key: ~/.hermes/cache/skill-integrity.key  (chmod 600, auto-generated)
DB:  ~/.hermes/cache/skill-integrity.json

Usage:
  python3 skill-integrity-check.py generate
  python3 skill-integrity-check.py verify
  python3 skill-integrity-check.py update
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
from pathlib import Path

# Profile-aware HERMES_HOME: if HERMES_HOME env is set, use it directly.
# If not, fall back to ~/.hermes and further sub-select by HERMES_PROFILE if set,
# so that running without env vars still resolves to the correct fork profile path.
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if _hermes_profile and "profiles" not in os.environ.get("HERMES_HOME", ""):
    HERMES_HOME = _hermes_base / "profiles" / _hermes_profile
else:
    HERMES_HOME = _hermes_base
SKILLS_DIR = HERMES_HOME / "skills"
KEY_PATH = HERMES_HOME / "cache" / "skill-integrity.key"
DB_PATH = HERMES_HOME / "cache" / "skill-integrity.json"


def _load_or_create_key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        raw = KEY_PATH.read_bytes()
        if len(raw) == 32:
            return raw
    key = secrets.token_bytes(32)
    _key_tmp = KEY_PATH.with_suffix(".tmp")
    _key_tmp.write_bytes(key)
    _key_tmp.chmod(0o600)
    _key_tmp.replace(KEY_PATH)
    print(f"[INFO] New master key generated at {KEY_PATH}", file=sys.stderr)
    return key


def _compute_mac(key: bytes, file_bytes: bytes) -> str:
    return hmac.new(key, file_bytes, hashlib.sha256).hexdigest()


def _scan_skills() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    # rglob from SKILLS_DIR may not traverse if dir perms prevent stat from parent;
    # iterate top-level category dirs explicitly instead.
    results: list[Path] = []
    for child in SKILLS_DIR.iterdir():
        if child.is_dir():
            results.extend(child.rglob("SKILL.md"))
        elif child.name == "SKILL.md":
            results.append(child)
    return sorted(results)


def _load_db() -> dict:
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_db(db: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _db_tmp = DB_PATH.with_suffix(".tmp")
    _db_tmp.write_text(json.dumps(db, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _db_tmp.replace(DB_PATH)


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(HERMES_HOME))
    except ValueError:
        return str(p)


def cmd_generate(args: argparse.Namespace) -> int:
    key = _load_or_create_key()
    files = _scan_skills()
    db: dict = {}
    for f in files:
        data = f.read_bytes()
        db[_rel(f)] = _compute_mac(key, data)
    _save_db(db)
    print(f"[OK] Baseline written: {len(db)} file(s) → {DB_PATH}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    key = _load_or_create_key()
    db = _load_db()
    if not db:
        print("[WARN] No baseline found — run 'generate' first.")
        return 1
    files = _scan_skills()
    current: dict = {}
    for f in files:
        data = f.read_bytes()
        current[_rel(f)] = _compute_mac(key, data)

    mismatches: list[str] = []
    missing: list[str] = []
    new_files: list[str] = []

    for rel, stored_mac in db.items():
        if rel not in current:
            missing.append(rel)
        elif current[rel] != stored_mac:
            mismatches.append(rel)

    for rel in current:
        if rel not in db:
            new_files.append(rel)

    if not mismatches and not missing and not new_files:
        print(f"[OK] All {len(db)} file(s) verified — no mismatches.")
        return 0

    if mismatches:
        print(f"[FAIL] {len(mismatches)} MISMATCH(es):")
        for rel in mismatches:
            print(f"  MISMATCH: {rel}")
    if missing:
        print(f"[WARN] {len(missing)} file(s) in baseline but missing on disk:")
        for rel in missing:
            print(f"  MISSING: {rel}")
    if new_files:
        print(f"[INFO] {len(new_files)} new file(s) not in baseline (run 'update'):")
        for rel in new_files:
            print(f"  NEW: {rel}")
    return 1 if (mismatches or missing) else 0


def cmd_update(args: argparse.Namespace) -> int:
    key = _load_or_create_key()
    db = _load_db()
    files = _scan_skills()
    updated = 0
    added = 0
    for f in files:
        rel = _rel(f)
        data = f.read_bytes()
        mac = _compute_mac(key, data)
        if rel not in db:
            db[rel] = mac
            added += 1
        elif db[rel] != mac:
            db[rel] = mac
            updated += 1
    _save_db(db)
    print(f"[OK] Update complete: {updated} updated, {added} added → {DB_PATH}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="HMAC-SHA256 skill integrity checker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate", help="Write baseline MACs for all SKILL.md files")
    sub.add_parser("verify", help="Check current files against baseline")
    sub.add_parser("update", help="Regenerate MACs for changed/new files")
    args = ap.parse_args()
    dispatch = {"generate": cmd_generate, "verify": cmd_verify, "update": cmd_update}
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
run-header.py — Content-addressed execution identity for Hermes cron runs
arXiv:2608.23610 (From Traceability to Justifiability, Sep 2026)

Finding: 47 agent/CI platforms audited; zero emit content-addressed identity of
(model, instructions, tools, retrieval config) at execution time. Makes runs
non-reproducible and drift undetectable.

Usage:
    # At the start of any cron script, emit a run header:
    python3 ~/.hermes/scripts/run-header.py \
        --script cs-paper-interpreter.py \
        --model claude-haiku-4-5 \
        --skill hermes-cs-research \
        --note "weekly CS sweep"

    # Outputs a JSON block logged to ~/.hermes/logs/run-headers.jsonl
    # and printed to stdout for embedding in script logs.

Run-header fields:
    run_id:       sha256(script + model + skills + config_hash)[:16]  — content-addressed, no ts
    script:       script filename
    script_hash:  sha256 of script file content
    model:        LLM model name
    config_hash:  sha256 of config.yaml (detects config drift between runs)
    skill_hashes: {skill_name: sha256(skill_body)[:8]} for each named skill
    ts:           ISO8601 UTC timestamp
    note:         optional free-text label
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_DIR = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS_DIR = HERMES_DIR / "skills"
CONFIG_PATH = HERMES_DIR / "config.yaml"
LOG_PATH = HERMES_DIR / "logs" / "run-headers.jsonl"
SCRIPTS_DIR = HERMES_DIR / "scripts"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "unreadable"


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def find_skill_path(skill_name: str) -> Path | None:
    """Search skills dir recursively for SKILL.md matching skill name."""
    for p in SKILLS_DIR.rglob(f"{skill_name}/SKILL.md"):
        return p
    return None


def main():
    parser = argparse.ArgumentParser(description="Emit content-addressed run header")
    parser.add_argument("--script", required=True, help="Script filename (basename or path)")
    parser.add_argument("--model", default="unknown", help="LLM model name")
    parser.add_argument("--skill", action="append", default=[], dest="skills",
                        help="Skill name to hash (repeat for multiple)")
    parser.add_argument("--note", default="", help="Optional label for this run")
    parser.add_argument("--no-log", action="store_true", help="Print only, don't append to log")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).isoformat()

    # Resolve script path
    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = SCRIPTS_DIR / script_path
    script_hash = sha256_file(script_path)

    # Config hash
    config_hash = sha256_file(CONFIG_PATH)[:12]

    # Skill hashes
    skill_hashes = {}
    for skill_name in args.skills:
        skill_path = find_skill_path(skill_name)
        if skill_path:
            skill_hashes[skill_name] = sha256_file(skill_path)[:8]
        else:
            skill_hashes[skill_name] = "not_found"

    # Composite run_id — content-addressed (script content + model + config + skills).
    # Includes script_hash so two different script bodies with the same filename get
    # different run_ids. Use run_id for drift detection; use ts to order runs.
    composite = "|".join([
        script_hash[:16], args.model, config_hash,
        ",".join(f"{k}:{v}" for k, v in sorted(skill_hashes.items())),
    ])
    run_id = sha256_str(composite)[:16]

    header = {
        "run_id": run_id,
        "ts": ts,
        "script": args.script,
        "script_hash": script_hash[:12],
        "model": args.model,
        "config_hash": config_hash,
        "skill_hashes": skill_hashes,
        "note": args.note,
    }

    # Print to stdout (for embedding in script logs)
    print(json.dumps(header))

    # Append to run log
    if not args.no_log:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(header) + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()

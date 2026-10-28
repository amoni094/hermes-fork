#!/usr/bin/env python3
"""Cron stub: quantify removal risk for stale skills and memory entries."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import sys
import json
import sqlite3
import time
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "obstruction-certificate-cache.json"
SKILLS = _hermes_root / "skills"
LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")
STALE_DAYS = 90


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def mtime_age_days(p: Path) -> float:
    try:
        return max(0.0, (time.time() - p.stat().st_mtime) / 86400.0)
    except OSError:
        return 0.0


def scan() -> dict:
    stale_skills = []
    if SKILLS.is_dir():
        for d in sorted(SKILLS.iterdir()):
            skill = d / "SKILL.md"
            if not skill.exists():
                continue
            age = mtime_age_days(skill)
            if age >= STALE_DAYS:
                risk = min(1.0, (age - STALE_DAYS) / 180.0)
                stale_skills.append({"name": d.name, "age_days": round(age, 2), "removal_risk": round(risk, 6)})
    stale_mem = []
    try:
        if LIFECYCLE_DB.exists():
            conn = sqlite3.connect(str(LIFECYCLE_DB))
            try:
                names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                if "fact_lifecycle" in names:
                    cols = [r[1] for r in conn.execute("PRAGMA table_info(fact_lifecycle)").fetchall()]
                    if "last_accessed" in cols:
                        for mid, la in conn.execute("SELECT memory_id, last_accessed FROM fact_lifecycle LIMIT 500"):
                            stale_mem.append({"memory_id": mid, "last_accessed": la})
            finally:
                conn.close()
    except Exception:
        pass
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "stale_days": STALE_DAYS,
        "stale_skill_count": len(stale_skills),
        "stale_skills": stale_skills[:50],
        "memory_candidates": len(stale_mem),
        "action": "report_only",
    }


def self_test() -> dict:
    r = scan()
    assert "stale_skill_count" in r
    assert r["action"] == "report_only"
    return {"self_test": "PASS", "sample": {k: r[k] for k in r if k != "stale_skills"}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    out = scan()
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

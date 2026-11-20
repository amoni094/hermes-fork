#!/usr/bin/env python3
"""memory-needle-classifier.py — classify staging.md facts as needle categories.

claude-mem observation needle classification (Wave 23-CM):
  decision, bugfix, security_alert, sensitive, pitfall, none

Needle facts get a priority_boost for promotion scoring. Highest boost wins
when a fact matches multiple categories.

Stdlib only. Exit 0 when staging.md is missing or empty.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

MIN_FACT_LEN = 15
PRIORITY_BOOST = {
    "security_alert": 0.4,
    "decision": 0.3,
    "bugfix": 0.25,
    "pitfall": 0.25,
    "sensitive": 0.2,
    "none": 0.0,
}
# Highest boost first for multi-match resolution.
CATEGORY_ORDER = (
    "security_alert",
    "decision",
    "bugfix",
    "pitfall",
    "sensitive",
)

# Word-boundary patterns. High-FP tokens ('we use', 'architecture', 'never',
# 'auth', 'token', 'private', 'fix') are phrase-gated, not bare substrings.
PATTERNS = {
    "decision": (
        re.compile(r"\bdecided\b", re.IGNORECASE),
        re.compile(r"\bchose\b", re.IGNORECASE),
        re.compile(r"\bswitched to\b", re.IGNORECASE),
        re.compile(r"\bgoing with\b", re.IGNORECASE),
        re.compile(r"\bdesign choice\b", re.IGNORECASE),
        re.compile(r"\bconvention is\b", re.IGNORECASE),
        re.compile(r"\bwe (?:now )?use\b.{0,80}\b(?:instead|rather than|by default|convention)\b", re.IGNORECASE),
        re.compile(r"\b(?:system|memory|plugin) architecture\b", re.IGNORECASE),
    ),
    "bugfix": (
        re.compile(r"\bbugfix\b", re.IGNORECASE),
        re.compile(r"\bbugs?\b", re.IGNORECASE),
        re.compile(r"\bbroken\b", re.IGNORECASE),
        re.compile(r"\bworkaround\b", re.IGNORECASE),
        re.compile(r"\bpatched\b", re.IGNORECASE),
        re.compile(r"\bcaused by\b", re.IGNORECASE),
        re.compile(r"\broot cause\b", re.IGNORECASE),
        re.compile(r"\bfix(?:ed|es|ing)?\b", re.IGNORECASE),
    ),
    "security_alert": (
        re.compile(r"\bpasswords?\b", re.IGNORECASE),
        re.compile(r"\bsecrets?\b", re.IGNORECASE),
        re.compile(r"\bcredentials?\b", re.IGNORECASE),
        re.compile(r"\bapi[_ ]keys?\b", re.IGNORECASE),
        re.compile(r"\bprivate keys?\b", re.IGNORECASE),
        re.compile(r"\b(?:authn|authz|oauth)\b", re.IGNORECASE),
        re.compile(r"\bexposed\b", re.IGNORECASE),
        re.compile(r"\b(?:access|bearer|refresh) tokens?\b", re.IGNORECASE),
    ),
    "sensitive": (
        re.compile(r"\bPII\b"),
        re.compile(r"\bpersonal data\b", re.IGNORECASE),
        re.compile(r"\bemail address(?:es)?\b", re.IGNORECASE),
        re.compile(r"\bphone numbers?\b", re.IGNORECASE),
        re.compile(r"\bSSN\b"),
        re.compile(r"\bprivate (?:data|info(?:rmation)?|details?)\b", re.IGNORECASE),
    ),
    "pitfall": (
        re.compile(r"\balways avoid\b", re.IGNORECASE),
        re.compile(r"\bdo not\b", re.IGNORECASE),
        re.compile(r"\bdon't\b", re.IGNORECASE),
        re.compile(r"\bfootguns?\b", re.IGNORECASE),
        re.compile(r"\bpitfalls?\b", re.IGNORECASE),
        re.compile(r"\bgotchas?\b", re.IGNORECASE),
        re.compile(r"\btraps?\b", re.IGNORECASE),
        re.compile(r"\bnever (?:use|call|pass|store|run|put|mix|assume|rely|write|read|set)\b", re.IGNORECASE),
    ),
}


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _staging_path() -> Path | None:
    env = os.environ.get("MEMORY_STAGING_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.exists() else None
    candidates = [
        _hermes_base / "memory-facts" / "staging.md",
        _hermes_root / "memory-facts" / "staging.md",
        _hermes_base / "profiles" / "fork" / "memory-facts" / "staging.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def classify(text: str) -> str:
    """Return highest-priority matching category, or 'none'."""
    best = "none"
    best_boost = 0.0
    for cat in CATEGORY_ORDER:
        pats = PATTERNS.get(cat) or ()
        if any(p.search(text) for p in pats):
            boost = PRIORITY_BOOST.get(cat, 0.0)
            if boost > best_boost:
                best = cat
                best_boost = boost
    return best


def parse_facts(text: str) -> list[tuple[int, str]]:
    """Yield (1-based line number, fact text) for lines starting with '- '."""
    out: list[tuple[int, str]] = []
    for i, raw in enumerate((text or "").splitlines(), 1):
        line = raw.rstrip("\n")
        stripped = line.lstrip()
        if not stripped.startswith("- "):
            continue
        fact = stripped[2:].strip()
        if len(fact) < MIN_FACT_LEN:
            continue
        out.append((i, fact))
    return out


def classify_facts(facts: list[tuple[int, str]]) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for line_no, fact in facts:
        key = fact.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        cat = classify(fact)
        rows.append(
            {
                "fact": fact,
                "category": cat,
                "source_line": line_no,
                "priority_boost": PRIORITY_BOOST.get(cat, 0.0),
            }
        )
    return rows


def _load_prev(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("facts"), list):
        return obj["facts"]
    return []


def _needle_keys(rows: list[dict]) -> set[str]:
    keys = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("category") or "none") == "none":
            continue
        keys.add(str(r.get("fact") or "").lower().strip())
    return keys


def run(staging: Path | None, out_path: Path, alarm_path: Path) -> dict:
    if staging is None or not staging.exists():
        payload = []
        alarm = {
            "ts": _now(),
            "alarm": False,
            "new_needles": [],
            "new_count": 0,
            "reason": "staging_missing",
        }
        _atomic_write(out_path, payload)
        _atomic_write(alarm_path, alarm)
        return {"ok": True, "n": 0, "needles": 0, "new": 0, "reason": "staging_missing"}

    try:
        text = staging.read_text(encoding="utf-8", errors="replace")
    except OSError:
        payload = []
        alarm = {
            "ts": _now(),
            "alarm": False,
            "new_needles": [],
            "new_count": 0,
            "reason": "staging_unreadable",
        }
        _atomic_write(out_path, payload)
        _atomic_write(alarm_path, alarm)
        return {"ok": True, "n": 0, "needles": 0, "new": 0, "reason": "staging_unreadable"}

    prev = _load_prev(out_path)
    rows = classify_facts(parse_facts(text))
    prev_keys = _needle_keys(prev)
    cur_keys = _needle_keys(rows)
    new_needles = [
        r for r in rows
        if r["category"] != "none" and r["fact"].lower().strip() not in prev_keys
    ]
    alarm = {
        "ts": _now(),
        "alarm": bool(new_needles),
        "new_needles": new_needles,
        "new_count": len(new_needles),
        "needle_count": len(cur_keys),
        "fact_count": len(rows),
        "reason": "ok",
    }
    _atomic_write(out_path, rows)
    _atomic_write(alarm_path, alarm)
    return {
        "ok": True,
        "n": len(rows),
        "needles": len(cur_keys),
        "new": len(new_needles),
        "reason": "ok",
    }


def _self_test() -> int:
    failures: list[str] = []
    uid = uuid.uuid4().hex
    td = Path(tempfile.mkdtemp(prefix="needle-" + uid[:8] + "-"))
    try:
        # missing staging
        missing_out = td / f"out_{uid}.json"
        missing_alarm = td / f"alarm_{uid}.json"
        r = run(None, missing_out, missing_alarm)
        if r.get("reason") != "staging_missing":
            failures.append("missing staging reason")
        if json.loads(missing_out.read_text()) != []:
            failures.append("missing staging should write empty list")
        alarm = json.loads(missing_alarm.read_text())
        if alarm.get("new_needles") != []:
            failures.append("missing staging alarm not empty list")

        staging = td / "staging.md"
        staging.write_text(
            "\n".join(
                [
                    "- we use tabs for indentation in python files",  # must NOT be decision
                    "- decided to switch the memory store to sqlite",
                    "- prefix and suffix are normal words",
                    "- fixed the broken cron wrapper after root cause analysis",
                    "- never store credentials or api keys in MEMORY.md",
                    "- email address of the user is private data",
                    "- short",  # < 15
                    "- Do not call WAL on a read-only sqlite open",
                    "- decided to switch the memory store to sqlite",  # dup
                    "not a fact line",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        out = td / f"class_{uid}.json"
        alarm_p = td / f"class_alarm_{uid}.json"
        r = run(staging, out, alarm_p)
        rows = json.loads(out.read_text())
        by_fact = {x["fact"]: x for x in rows}
        tabs = "we use tabs for indentation in python files"
        if tabs not in by_fact or by_fact[tabs]["category"] != "none":
            failures.append("FP: we use tabs classified as " + str(by_fact.get(tabs)))
        if "prefix and suffix are normal words" in by_fact:
            if by_fact["prefix and suffix are normal words"]["category"] != "none":
                failures.append("FP: prefix/suffix matched fix")
        dec = by_fact.get("decided to switch the memory store to sqlite")
        if not dec or dec["category"] != "decision" or dec["priority_boost"] != 0.3:
            failures.append("decision miss: " + str(dec))
        bug = by_fact.get("fixed the broken cron wrapper after root cause analysis")
        if not bug or bug["category"] != "bugfix":
            failures.append("bugfix miss: " + str(bug))
        sec = by_fact.get("never store credentials or api keys in MEMORY.md")
        # security_alert 0.4 beats pitfall 0.25
        if not sec or sec["category"] != "security_alert" or sec["priority_boost"] != 0.4:
            failures.append("security/multi miss: " + str(sec))
        sens = by_fact.get("email address of the user is private data")
        if not sens or sens["category"] != "sensitive":
            failures.append("sensitive miss: " + str(sens))
        pit = by_fact.get("Do not call WAL on a read-only sqlite open")
        if not pit or pit["category"] != "pitfall":
            failures.append("pitfall miss: " + str(pit))
        if any(len(x["fact"]) < MIN_FACT_LEN for x in rows):
            failures.append("short fact leaked")
        facts_lower = [x["fact"].lower() for x in rows]
        if facts_lower.count("decided to switch the memory store to sqlite") != 1:
            failures.append("dedup failed")
        alarm = json.loads(alarm_p.read_text())
        if alarm.get("new_count", 0) < 1:
            failures.append("first-run alarm should list new needles")
        if alarm.get("alarm") is not True:
            failures.append("first-run aggregator alarm flag")

        # second run: no new needles
        r2 = run(staging, out, alarm_p)
        alarm2 = json.loads(alarm_p.read_text())
        if alarm2.get("new_needles") != [] or alarm2.get("new_count") != 0:
            failures.append("second run should write empty new_needles list")
        if alarm2.get("alarm") is not False:
            failures.append("second-run aggregator alarm should be false")
        if r2.get("n") != r.get("n"):
            failures.append("second run fact count drifted")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS"}))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Classify staging.md facts as needles")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    cache = _cache_dir()
    out = cache / "needle-classified.json"
    alarm = cache / "needle-classifier-alarm.json"
    result = run(_staging_path(), out, alarm)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "ts": _now()}))
        sys.exit(0)

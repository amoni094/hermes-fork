#!/usr/bin/python3
"""
mask-coupling-monitor.py

Detects when episodic memories are retrieved through a degraded or
corrupted association path — monitors the coupling between memory
retrieval masks and the underlying stored patterns.

Math basis: mask-coupled Hopfield retrieval
  In associative memory, a retrieval mask M_t selects a subset of
  stored pattern dimensions. Retrieval quality degrades when:
    coupling(M_t, P) = |M_t ∩ support(P)| / |support(P)| < THRESHOLD
  where P = stored pattern, M_t = current retrieval mask.
  
  Operationally: proxy via recall key → skill description overlap.
  Alarm when avg coupling < COUPLING_THRESHOLD across recent retrievals.

Usage:
  python3 mask-coupling-monitor.py          # scan recent sessions
  python3 mask-coupling-monitor.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
SKILLS_DIR   = _RT / "skills"
ALT_SKILLS   = HOME / ".hermes/skills"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "mask-coupling-report.json"

COUPLING_THRESHOLD = 0.15   # alarm if avg mask-pattern coupling < 15%
MIN_QUERIES        = 2


def _load_skill_keywords() -> dict[str, set[str]]:
    """Map skill name → keyword set from SKILL.md descriptions."""
    skills: dict[str, set[str]] = {}
    for sd in [SKILLS_DIR, ALT_SKILLS]:
        if not sd.exists():
            continue
        for md in sd.rglob("SKILL.md"):
            name = md.parent.name
            try:
                text = md.read_text()[:400]
                kw   = set(re.findall(r"[a-z]{4,}", text.lower()))
                skills[name] = kw
            except Exception:
                pass
    return skills


def _extract_skill_queries(session_path: Path) -> list[str]:
    """Extract skill_view tool calls from session."""
    queries = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("name") == "skill_view":
                            inp = block.get("input", {})
                            name = inp.get("name", "")
                            if name:
                                queries.append(name)
        except Exception:
            pass
    return queries


def _coupling(query_kw: set, pattern_kw: set) -> float:
    if not pattern_kw:
        return 0.0
    return len(query_kw & pattern_kw) / len(pattern_kw)


def analyse_session(session_path: Path, skill_db: dict[str, set[str]]) -> dict:
    queries = _extract_skill_queries(session_path)
    if len(queries) < MIN_QUERIES:
        return {
            "session": session_path.stem,
            "note":    f"only {len(queries)} skill_view calls",
            "alarm":   False,
        }

    couplings = []
    for q in queries:
        q_kw = set(q.replace("-", " ").replace("_", " ").split())
        if q in skill_db:
            c = _coupling(q_kw, skill_db[q])
        else:
            # Fuzzy: find best-matching skill
            best = max(
                (_coupling(q_kw, kw) for kw in skill_db.values()),
                default=0.0,
            )
            c = best
        couplings.append(c)

    avg_c = sum(couplings) / len(couplings)
    alarm = avg_c < COUPLING_THRESHOLD

    return {
        "session":       session_path.stem,
        "queries":       len(queries),
        "avg_coupling":  round(avg_c, 4),
        "min_coupling":  round(min(couplings), 4),
        "alarm":         alarm,
    }


def run(dry_run: bool) -> int:
    now      = datetime.now(timezone.utc).isoformat()
    skill_db = _load_skill_keywords()
    paths    = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[mask-coupling] No sessions found")
        return 0

    results     = [analyse_session(p, skill_db) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Mask-Coupling Monitor — {now[:10]} ===")
    print(f"Skills loaded: {len(skill_db)}  Sessions: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"avg_coupling={r['avg_coupling']:.3f}  "
                  f"min={r['min_coupling']:.3f}  "
                  f"queries={r['queries']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show degraded mask-pattern coupling")
        rc = 1
    else:
        print(f"\nALARM: no — memory retrieval coupling within bounds")
        rc = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "results": results, "alarm_count": len(alarm_cases),
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()

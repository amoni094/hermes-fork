#!/usr/bin/env python3
"""skill-beta-feedback.py -- Skill beta-bandit feedback writer.

Reads recent session logs, extracts skill_view invocations,
and records success signals to skill-router-index beta posteriors.

Theory: Beta(alpha, beta) bandit (Lattimore & Szepesvari Ch 3).
Source: arXiv:2604.01707 -- skill routing feedback loop closure.
"""
from __future__ import annotations

import json, os, subprocess, sys, time
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

SESSIONS_DIR = _hermes_root / "sessions"
LOOKBACK_HOURS = 6
SKILL_ROUTER = Path(__file__).resolve().parent / "skill-router-index.py"
_PYTHON = sys.executable


def _recent_sessions(since_ts: float) -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(
        (f for f in SESSIONS_DIR.glob("*.jsonl") if f.stat().st_mtime >= since_ts),
        key=lambda f: f.stat().st_mtime,
    )


def _extract_skill_hits(session_path: Path) -> set:
    hits: set = set()
    try:
        for line in session_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = msg.get("content", "") or ""
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
            # Extract skill names from skill_view(name=...) calls
            idx = 0
            while True:
                pos = content.find("skill_view(name=", idx)
                if pos < 0:
                    break
                start = pos + len("skill_view(name=")
                if start < len(content) and content[start] in (chr(39), chr(34)):
                    start += 1
                end = content.find(")", start)
                if end > start:
                    skill = content[start:end].strip(chr(39) + chr(34))
                    if skill:
                        hits.add(skill)
                idx = max(start, end + 1)
    except Exception:
        pass
    return hits


def main() -> None:
    since_ts = time.time() - LOOKBACK_HOURS * 3600
    sessions = _recent_sessions(since_ts)
    if not sessions:
        print(f"[skill-beta-feedback] No recent sessions in last {LOOKBACK_HOURS}h")
        return

    all_hits: set = set()
    for sf in sessions:
        all_hits.update(_extract_skill_hits(sf))

    if not all_hits:
        print("[skill-beta-feedback] No skill invocations found in recent sessions")
        return

    print(f"[skill-beta-feedback] Recording {len(all_hits)} skill success signals")
    for skill_name in sorted(all_hits):
        r = subprocess.run(
            [_PYTHON, str(SKILL_ROUTER), "--feedback", skill_name + ":success"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"  OK: {skill_name}")
        else:
            print(f"  ERR: {skill_name} -> {r.stderr.strip()[:60]}", file=sys.stderr)


if __name__ == "__main__":
    main()

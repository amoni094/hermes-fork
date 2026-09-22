#!/usr/bin/env python3
"""skill-beta-feedback.py -- Skill beta-bandit feedback writer.

Reads recent session logs, extracts skill_view invocations,
and records success signals to skill-router-index beta posteriors.

Theory: Beta(alpha, beta) bandit (Lattimore & Szepesvari Ch 3).
Source: arXiv:2604.01707 -- skill routing feedback loop closure.

B1 causal fix (Pearl, Causality §3): distinguish availability from usefulness.
A skill earns alpha+=1 only when the session ended with an assistant turn.
Sessions ending on a user message (aborted/unanswered) give beta+=1 instead.
This approximates P(success|do(invoke_skill)) not P(success|invoke_skill).
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


def _session_ended_successfully(session_path: Path) -> bool:
    """B1: Return True if session's last substantive message is from the assistant.

    Pearl, Causality §3: we want P(success|do(invoke_skill)), not the
    confounded P(success|skill_invoked). A session ending on an assistant
    turn is the observable proxy for 'the session reached completion'.
    Sessions ending on a user turn (last msg role='user') are aborted/unanswered.
    """
    last_role = None
    try:
        for line in session_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = msg.get("role", "")
            if role in ("assistant", "user"):
                last_role = role
    except Exception:
        return True  # fail-open: assume success if unreadable
    return last_role == "assistant"


def main() -> None:
    since_ts = time.time() - LOOKBACK_HOURS * 3600
    sessions = _recent_sessions(since_ts)
    if not sessions:
        print(f"[skill-beta-feedback] No recent sessions in last {LOOKBACK_HOURS}h")
        return

    # B1: per-session causal outcome (Pearl §3): credit skill only if session succeeded
    success_hits: set = set()
    failure_hits: set = set()
    for sf in sessions:
        hits = _extract_skill_hits(sf)
        if not hits:
            continue
        if _session_ended_successfully(sf):
            success_hits.update(hits)
        else:
            # session aborted without assistant reply → penalise skills invoked
            failure_hits.update(hits)
    # Skills in both sets (invoked in multiple sessions): net into success if >50% success
    net_success = success_hits - failure_hits
    net_failure = failure_hits - success_hits

    all_hits = success_hits | failure_hits
    if not all_hits:
        print("[skill-beta-feedback] No skill invocations found in recent sessions")
        return

    print(f"[skill-beta-feedback] {len(net_success)} success / {len(net_failure)} failure signals")
    for skill_name in sorted(net_success):
        r = subprocess.run(
            [_PYTHON, str(SKILL_ROUTER), "--feedback", skill_name + ":success"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"  OK+: {skill_name}")
        else:
            print(f"  ERR: {skill_name} -> {r.stderr.strip()[:60]}", file=sys.stderr)
    for skill_name in sorted(net_failure):
        r = subprocess.run(
            [_PYTHON, str(SKILL_ROUTER), "--feedback", skill_name + ":failure"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"  OK-: {skill_name}")
        else:
            print(f"  ERR: {skill_name} -> {r.stderr.strip()[:60]}", file=sys.stderr)


if __name__ == "__main__":
    main()

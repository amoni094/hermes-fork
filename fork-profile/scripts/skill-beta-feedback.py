#!/usr/bin/env python3
"""skill-beta-feedback.py -- Skill beta-bandit feedback writer.

Reads recent session logs, extracts skill_view invocations,
and records success/failure signals to skill-router-index beta posteriors.

Theory: Beta(alpha, beta) bandit (Lattimore & Szepesvari Ch 3).
Source: arXiv:2604.01707 -- skill routing feedback loop closure.

B1 causal fix (Pearl, Causality §3): distinguish availability from usefulness.
A skill earns alpha+=1 only when the session ended with an assistant turn.
Sessions ending on a user message (aborted/unanswered) give beta+=1 instead.
This approximates P(success|do(invoke_skill)) not P(success|invoke_skill).
"""
from __future__ import annotations

import json, os, subprocess, sys, time
from collections import Counter
from pathlib import Path
from typing import Optional

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


def _add_skill_name(hits: set, raw) -> None:
    if isinstance(raw, str):
        name = raw.strip().strip("'\"")
        if name:
            hits.add(name)


def _hits_from_tool_calls(tool_calls, hits: set) -> None:
    if not isinstance(tool_calls, list):
        return
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        fn = call.get("function")
        if not isinstance(fn, dict):
            fn = {}
        name = fn.get("name") or call.get("name") or call.get("tool_name")
        if name != "skill_view":
            continue
        args = fn.get("arguments")
        if args is None:
            args = call.get("arguments", call.get("input"))
        parsed = {}
        if isinstance(args, dict):
            parsed = args
        elif isinstance(args, str) and args.strip():
            try:
                loaded = json.loads(args)
            except json.JSONDecodeError:
                loaded = {}
            if isinstance(loaded, dict):
                parsed = loaded
        _add_skill_name(hits, parsed.get("name"))


def _hits_from_content(content, hits: set) -> None:
    if isinstance(content, list):
        content = " ".join(
            c.get("text", "") for c in content if isinstance(c, dict)
        )
    if not isinstance(content, str) or "skill_view" not in content:
        return
    idx = 0
    needle = "skill_view(name="
    while True:
        pos = content.find(needle, idx)
        if pos < 0:
            break
        start = pos + len(needle)
        if start < len(content) and content[start] in ("'", '"'):
            start += 1
        end = content.find(")", start)
        if end > start:
            _add_skill_name(hits, content[start:end])
        idx = max(start, end + 1)


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
            if not isinstance(msg, dict):
                continue
            _hits_from_tool_calls(msg.get("tool_calls"), hits)
            if msg.get("tool_name") == "skill_view" or msg.get("name") == "skill_view":
                args = msg.get("arguments") or msg.get("input") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if isinstance(args, dict):
                    _add_skill_name(hits, args.get("name"))
            _hits_from_content(msg.get("content", ""), hits)
    except Exception:
        pass
    return hits


def _session_ended_successfully(session_path: Path) -> Optional[bool]:
    """B1: True if last user/assistant role is assistant, False if user, None if unknown.

    Tool-only transcripts (no user/assistant roles) must not be scored as failures.
    Unreadable files are unknown (skip), not fail-open success.
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
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            if role in ("assistant", "user"):
                last_role = role
    except Exception:
        return None
    if last_role == "assistant":
        return True
    if last_role == "user":
        return False
    return None


def main() -> None:
    since_ts = time.time() - LOOKBACK_HOURS * 3600
    sessions = _recent_sessions(since_ts)
    if not sessions:
        print(f"[skill-beta-feedback] No recent sessions in last {LOOKBACK_HOURS}h")
        return

    success_counts: Counter = Counter()
    failure_counts: Counter = Counter()
    skipped = 0
    for sf in sessions:
        hits = _extract_skill_hits(sf)
        if not hits:
            continue
        ended = _session_ended_successfully(sf)
        if ended is True:
            success_counts.update(hits)
        elif ended is False:
            failure_counts.update(hits)
        else:
            skipped += 1

    all_skills = set(success_counts) | set(failure_counts)
    if not all_skills:
        print("[skill-beta-feedback] No skill invocations found in recent sessions")
        return

    net_success = []
    net_failure = []
    ties = 0
    for skill_name in sorted(all_skills):
        s = success_counts[skill_name]
        f = failure_counts[skill_name]
        if s > f:
            net_success.append(skill_name)
        elif f > s:
            net_failure.append(skill_name)
        else:
            ties += 1

    print(
        f"[skill-beta-feedback] {len(net_success)} success / {len(net_failure)} failure"
        f" / {ties} tie / {skipped} unknown-end sessions"
    )
    for skill_name in net_success:
        r = subprocess.run(
            [_PYTHON, str(SKILL_ROUTER), "--feedback", skill_name + ":success"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print(f"  OK+: {skill_name}")
        else:
            print(f"  ERR: {skill_name} -> {r.stderr.strip()[:60]}", file=sys.stderr)
    for skill_name in net_failure:
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

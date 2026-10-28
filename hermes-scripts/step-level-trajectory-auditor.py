#!/usr/bin/env python3
"""Audit each step in an agent trajectory for process quality (AgentProcessBench)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "trajectory-audit.json"
LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def audit_step(step: dict, prev_sigs: set, next_step: dict | None) -> dict:
    tool = step.get("tool") or step.get("action") or ""
    args = step.get("args") if isinstance(step.get("args"), dict) else {}
    args_valid = bool(tool) and (args is not None)
    consumed = True
    if next_step is not None:
        blob = json.dumps(next_step, default=str)
        out = step.get("output")
        consumed = (out is None) or (str(out)[:40] in blob) or bool(next_step.get("uses_prior"))
    sig = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
    redundant = sig in prev_sigs
    prev_sigs.add(sig)
    quality = (
        0.3 * float(bool(tool))
        + 0.3 * float(args_valid)
        + 0.2 * float(consumed)
        + 0.2 * float(not redundant)
    )
    return {
        "tool_used": str(tool),
        "args_valid": bool(args_valid),
        "output_consumed": bool(consumed),
        "redundant_call": bool(redundant),
        "quality": round(quality, 6),
    }


def audit_trajectory(steps: list, episode_id: str = "") -> dict:
    prev = set()
    scored = []
    seq = steps or []
    for i, step in enumerate(seq):
        if not isinstance(step, dict):
            step = {"tool": str(step)}
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        row = audit_step(step, prev, nxt)
        row["step"] = i
        scored.append(row)
    q = sum(s["quality"] for s in scored) / float(len(scored) or 1)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "episode_id": episode_id,
        "step_count": len(scored),
        "quality_score": round(q, 6),
        "steps": scored,
    }


def _log_lifecycle(report: dict) -> None:
    conn = sqlite3.connect(str(LIFECYCLE_DB))
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS trajectory_audits(
            id INTEGER PRIMARY KEY,
            ts TEXT,
            episode_id TEXT,
            step_count INTEGER,
            quality_score REAL)"""
        )
        conn.execute(
            """INSERT INTO trajectory_audits (ts, episode_id, step_count, quality_score)
            VALUES (datetime('now'), ?, ?, ?)""",
            (
                report.get("episode_id") or "",
                int(report.get("step_count") or 0),
                float(report.get("quality_score") or 0.0),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def self_test() -> dict:
    steps = [
        {"tool": "read_file", "args": {"path": "a"}, "output": "hello"},
        {"tool": "read_file", "args": {"path": "a"}, "output": "hello", "uses_prior": True},
        {"tool": "write_file", "args": {"path": "b"}, "output": "ok", "uses_prior": True},
    ]
    r = audit_trajectory(steps, episode_id="t1")
    assert r["step_count"] == 3, r
    assert r["steps"][1]["redundant_call"] is True
    assert 0.0 <= r["quality_score"] <= 1.0
    assert audit_trajectory([])["step_count"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--episode-id", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    raw = args.json
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    steps = []
    if raw:
        try:
            obj = json.loads(raw)
            steps = obj if isinstance(obj, list) else obj.get("steps") or obj.get("trace") or []
        except json.JSONDecodeError:
            steps = []
    out = audit_trajectory(steps, args.episode_id)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    try:
        _log_lifecycle(out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

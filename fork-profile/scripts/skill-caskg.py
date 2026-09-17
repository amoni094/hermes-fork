#!/usr/bin/env python3
"""skill-caskg.py — CaSKG candidate DAG: skill-load → terminal-outcome edges.

CaSKG (Counterfactual-Causal Skill Graphs; arXiv:2608.25500 — searched as CASKG;
arXiv:2501.12286 is unrelated PIR work) builds a high-recall directed candidate
graph from trace co-occurrence, then calibrates edges with counterfactual probes
(remove / substitute / reorder).

This spike implements only the *candidate* graph from Hermes delegation history:
for each session under ~/.hermes/cache/delegation/live/, scan task logs for
skill_view loads and attach the session's terminal outcome (completed / partial /
failed). Output is a list of edges:

    {from_skill, to_outcome, session_id, timestamp}

This is the dependency graph for skill sequencing. Counterfactual probing and
Bayesian edge publication are out of scope.

Usage:
  python3 skill-caskg.py
  python3 skill-caskg.py --live-dir PATH --output PATH
  python3 skill-caskg.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
DEFAULT_LIVE = HERMES_HOME / "cache" / "delegation" / "live"
DEFAULT_OUT = HERMES_HOME / "cache" / "skill-caskg-dag.json"

# Logs look like: -> skill_view(hermes-fork)  or  skill_view(name='hermes-fork')
SKILL_VIEW_RE = re.compile(
    r"skill_view\(\s*(?:name\s*=\s*)?['\"]?([A-Za-z0-9_.:-]+)['\"]?",
    re.IGNORECASE,
)
STARTED_RE = re.compile(r"^started:\s*(.+)$", re.MULTILINE)

TERMINAL_MAP = {
    "completed": "completed",
    "success": "completed",
    "partial": "partial",
    "partially_completed": "partial",
    "failed": "failed",
    "error": "failed",
    "aborted": "failed",
    "cancelled": "failed",
    "canceled": "failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_outcome(status: str | None, exit_reason: str | None) -> str | None:
    for raw in (status, exit_reason):
        if not raw:
            continue
        key = str(raw).strip().lower()
        if key in TERMINAL_MAP:
            return TERMINAL_MAP[key]
    return None


def _skills_from_text(text: str) -> list[str]:
    seen: list[str] = []
    for match in SKILL_VIEW_RE.finditer(text or ""):
        name = (match.group(1) or "").strip().rstrip("),")
        if not name or name in seen:
            continue
        seen.append(name)
    return seen


def _timestamp_from_log(text: str, fallback: str) -> str:
    m = STARTED_RE.search(text or "")
    if m:
        return m.group(1).strip()
    return fallback


def _iter_sessions(live_dir: Path) -> Iterable[Path]:
    if not live_dir.is_dir():
        return []
    return sorted(p for p in live_dir.iterdir() if p.is_dir())


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_edges(live_dir: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    edges: list[dict[str, str]] = []
    sessions_scanned = 0
    tasks_scanned = 0
    skipped_running = 0

    for session_dir in _iter_sessions(live_dir):
        sessions_scanned += 1
        session_id = session_dir.name
        manifest = _load_json(session_dir / "manifest.json") or {}
        session_started = str(manifest.get("started") or manifest.get("completed") or "")
        tasks = manifest.get("tasks")
        task_rows: list[dict[str, Any]] = []
        if isinstance(tasks, list) and tasks:
            task_rows = [t for t in tasks if isinstance(t, dict)]
        else:
            # Manifest missing: treat each task-*.log as one task with unknown outcome.
            for log_path in sorted(session_dir.glob("task-*.log")):
                task_rows.append({"log": str(log_path), "status": None, "index": log_path.stem})

        for task in task_rows:
            tasks_scanned += 1
            outcome = _normalize_outcome(task.get("status"), task.get("exit_reason"))
            if outcome is None:
                skipped_running += 1
                continue
            log_field = task.get("log")
            log_path = Path(log_field) if log_field else None
            if log_path is None or not log_path.is_file():
                idx = task.get("index", 0)
                candidate = session_dir / f"task-{idx}.log"
                log_path = candidate if candidate.is_file() else None
            text = ""
            if log_path and log_path.is_file():
                try:
                    text = log_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
            ts = _timestamp_from_log(text, session_started or _now())
            skills = _skills_from_text(text)
            if not skills:
                # Still record a sentinel so sessions with no skill_view stay visible.
                edges.append(
                    {
                        "from_skill": "(none)",
                        "to_outcome": outcome,
                        "session_id": session_id,
                        "timestamp": ts,
                    }
                )
                continue
            for skill in skills:
                edges.append(
                    {
                        "from_skill": skill,
                        "to_outcome": outcome,
                        "session_id": session_id,
                        "timestamp": ts,
                    }
                )

    stats = {
        "sessions_scanned": sessions_scanned,
        "tasks_scanned": tasks_scanned,
        "skipped_non_terminal": skipped_running,
        "edge_count": len(edges),
        "unique_skills": len({e["from_skill"] for e in edges}),
    }
    return edges, stats


def write_dag(edges: list[dict[str, str]], stats: dict[str, Any], output: Path, live_dir: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now(),
        "source": "caskg-candidate-dag",
        "paper": "arXiv:2608.25500 (CaSKG); arXiv:2501.12286 is unrelated PIR",
        "live_dir": str(live_dir),
        "stats": stats,
        "edges": edges,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Build CaSKG skill→outcome candidate DAG from delegation logs")
    p.add_argument("--live-dir", type=Path, default=DEFAULT_LIVE)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--dry-run", action="store_true", help="Print stats only; do not write")
    args = p.parse_args()

    live_dir = args.live_dir.expanduser()
    if not live_dir.is_dir():
        print(f"[skill-caskg] live dir missing: {live_dir}", file=sys.stderr)
        return 1

    edges, stats = build_edges(live_dir)
    print(f"[skill-caskg] sessions={stats['sessions_scanned']} tasks={stats['tasks_scanned']} "
          f"edges={stats['edge_count']} skills={stats['unique_skills']} "
          f"skipped_non_terminal={stats['skipped_non_terminal']}")
    if args.dry_run:
        return 0
    write_dag(edges, stats, args.output.expanduser(), live_dir)
    print(f"[skill-caskg] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

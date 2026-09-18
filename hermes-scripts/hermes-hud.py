#!/usr/bin/env python3
"""
hermes-hud — live status of active subagents and session budget
~/.hermes/scripts/hermes-hud.py

Usage:
  python3 ~/.hermes/scripts/hermes-hud.py [--session SESSION_ID] [--watch]

Shows:
  - Active / recently completed subagents from hud-active-agents.json
  - Session budget counters from budget-<session>.json
"""

import json
import sys
import time
import glob
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

STATE_DIR = Path("/var/home/rainbow/.hermes/state")
HUD_FILE = STATE_DIR / "hud-active-agents.json"


def fmt_duration(iso_start: str) -> str:
    try:
        start = datetime.fromisoformat(iso_start)
        delta = datetime.now(timezone.utc) - start
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s"
        elif s < 3600:
            return f"{s//60}m{s%60:02d}s"
        else:
            return f"{s//3600}h{(s%3600)//60:02d}m"
    except Exception:
        return "?"


def show_hud():
    lines = []
    lines.append("=" * 60)
    lines.append("  HERMES AGENT HUD")
    lines.append(f"  {datetime.now().strftime('%H:%M:%S')}")
    lines.append("=" * 60)

    # Active agents
    if HUD_FILE.exists():
        try:
            hud = json.loads(HUD_FILE.read_text())
            agents = hud.get("agents", [])
        except Exception:
            agents = []
    else:
        agents = []

    running = [a for a in agents if a.get("status") == "running"]
    done = [a for a in agents if a.get("status") != "running"]

    if running:
        lines.append(f"\n  ACTIVE ({len(running)}):")
        for a in running:
            dur = fmt_duration(a.get("started_at", ""))
            goal = (a.get("goal") or "")[:50]
            lines.append(f"    [{a.get('role','?')}] {a.get('id','?')[:12]}  {dur}  {goal}")
    else:
        lines.append("\n  No active subagents.")

    # --- FLEET METRICS (Little's Law occupancy, numerical_optimization primer) ---
    try:
        import yaml as _yaml
        _cfg_path = Path("/var/home/rainbow/.hermes/config.yaml")
        _max_children = 10
        if _cfg_path.exists():
            _cfg = _yaml.safe_load(_cfg_path.read_text()) or {}
            _max_children = (_cfg.get("delegation") or {}).get("max_concurrent_children", 10)
    except Exception:
        _max_children = 10
    _n_running = len(running)
    _rho = _n_running / max(_max_children, 1)
    _durations = []
    for _a in running:
        try:
            _start = datetime.fromisoformat(_a.get("started_at", ""))
            _durations.append((datetime.now(timezone.utc) - _start).total_seconds())
        except Exception:
            pass
    _mean_dur = sum(_durations) / len(_durations) if _durations else 0.0
    lines.append(f"\n  FLEET: rho={_rho:.2f} ({_n_running}/{_max_children} slots)  mean_dur={_mean_dur:.0f}s")

    if done:
        lines.append(f"\n  RECENT:")
        for a in done[-5:]:
            status = a.get("status", "?")
            started = a.get("started_at", "")[:19]
            goal = (a.get("goal") or "")[:40]
            lines.append(f"    [{status}] {a.get('id','?')[:12]}  {started}  {goal}")

    # Budget state
    lines.append("\n  BUDGET:")
    budget_files = list(STATE_DIR.glob("budget-*.json"))
    if budget_files:
        # Show most recently modified
        budget_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for bf in budget_files[:3]:
            try:
                b = json.loads(bf.read_text())
                sid = bf.stem.replace("budget-", "")[:12]
                lines.append(
                    f"    [{sid}]  tools={b.get('tool_calls',0)}  "
                    f"destructive={b.get('destructive_calls',0)}  "
                    f"max_depth={b.get('max_delegation_depth',0)}"
                )
            except Exception:
                pass
    else:
        lines.append("    No budget state yet.")

    lines.append("=" * 60)
    print("\n".join(lines))


if __name__ == "__main__":
    watch = "--watch" in sys.argv
    if watch:
        try:
            while True:
                subprocess.run(["clear"], check=False)  # safe: no user input, fixed arg list
                show_hud()
                time.sleep(3)
        except KeyboardInterrupt:
            pass
    else:
        show_hud()

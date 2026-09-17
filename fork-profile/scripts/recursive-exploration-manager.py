#!/usr/bin/python3
"""
recursive-exploration-manager.py

Embeds RSIAgent's recursive self-improvement loop into Hermes' cron
scheduler: each run discovers new implementable ideas, prioritises them,
and queues the top-N for implementation in the next session.

Research basis (RSIAgent — Autonomous Exploration for Recursive Self-Improvement):
  RSIAgent demonstrates that agents can improve their own capabilities by
  building causal models of their environment through recursive exploration.
  This script operationalises that loop for Hermes: scan idea queues,
  score by implementability + expected benefit, write a ranked TODO to
  a durable file that the next session picks up.

Math basis: greedy exploration under an information-gain budget
  Score(idea) = implementability × benefit_estimate × (1 - staleness)
  implementability: 1 if artifact is a .py script, 0.5 if skill, 0.2 otherwise
  benefit_estimate: keyword overlap with current alarm signals (from suite)
  staleness: exp(-age_days / 30)   — ideas decay in relevance over time
  Budget B: top-B ideas selected via greedy knapsack (each idea costs 1 unit)

Usage:
  python3 recursive-exploration-manager.py           # score and write TODO
  python3 recursive-exploration-manager.py --top 10
  python3 recursive-exploration-manager.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE     = HOME / ".hermes/cache/research"
MONITORS  = HOME / ".hermes/cache/monitors"
MONITORS.mkdir(parents=True, exist_ok=True)
TODO_FILE = HOME / ".hermes/cache/research/recursive-exploration-todo.json"
OUT_FILE  = MONITORS / "recursive-exploration-manager-report.json"

SCRIPTS_DIR = HOME / ".hermes/scripts"
DEFAULT_TOP = 8

# Keywords from known active alarms → boost relevance of matching ideas
ALARM_KEYWORDS = {
    "saturation", "consensus", "fragmentation", "session", "stability",
    "spec", "guard", "enforcement", "retrieval", "compression", "context",
    "delegation", "skill", "containment", "causal", "parametric",
}


def _implementability(artifact: str) -> float:
    if artifact.endswith(".py"):
        # Check if already implemented — normalise _ to - for filename matching
        stem_dash  = artifact.replace("_", "-")
        stem_under = artifact.replace("-", "_")
        if (SCRIPTS_DIR / artifact).exists() or \
           (SCRIPTS_DIR / stem_dash).exists() or \
           (SCRIPTS_DIR / stem_under).exists():
            return 0.0   # already done
        return 1.0
    if "skill" in artifact.lower():
        return 0.5
    return 0.2


def _benefit_estimate(text: str) -> float:
    words = set(re.findall(r"[a-z]+", text.lower()))
    overlap = len(words & ALARM_KEYWORDS) / max(len(ALARM_KEYWORDS), 1)
    return min(overlap * 3.0, 1.0)   # scale up; keywords are sparse


def _staleness(idea: dict, now: datetime) -> float:
    ts = idea.get("generated_at", idea.get("ts", ""))
    if not ts:
        return 0.5   # unknown age → moderate staleness
    try:
        generated = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        age_days   = (now - generated).total_seconds() / 86400
        return math.exp(-age_days / 30.0)
    except Exception:
        return 0.5


def _load_ideas() -> list[dict]:
    ideas = []
    for fname in ["math-ideas-queue.json", "cs-ideas-queue.json",
                  "research-ideas-queue.json"]:
        fpath = CACHE / fname
        if not fpath.exists():
            continue
        d = json.loads(fpath.read_text())
        batch = d.get("ideas", d.get("queue", []))
        for item in batch:
            item["_source"] = fname.replace("-ideas-queue.json", "")
        ideas.extend(batch)
    return ideas


def score_idea(idea: dict, now: datetime) -> float:
    artifact = idea.get("hermes_artifact", idea.get("name", ""))
    benefit  = idea.get("hermes_benefit", idea.get("benefit", ""))
    impl     = _implementability(artifact)
    if impl == 0.0:
        return 0.0   # already implemented
    bene   = _benefit_estimate(benefit + " " + artifact)
    stale  = _staleness(idea, now)
    return impl * (0.6 + 0.4 * bene) * stale


def run(top_n: int, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc)
    ideas = _load_ideas()

    scored = []
    for idea in ideas:
        s = score_idea(idea, now)
        if s > 0:
            scored.append((s, idea))

    scored.sort(key=lambda x: -x[0])
    top   = scored[:top_n]
    total = len(scored)

    print(f"\n=== Recursive Exploration Manager — {now.date()} ===")
    print(f"Ideas scanned: {len(ideas)} total, {total} actionable (not yet implemented)")
    print(f"Top {top_n} queued for next session:\n")

    todo_items = []
    for rank, (score, idea) in enumerate(top, 1):
        artifact = idea.get("hermes_artifact", idea.get("name", "?"))
        benefit  = idea.get("hermes_benefit", idea.get("benefit", ""))[:70]
        source   = idea.get("_source", "?")
        print(f"  {rank:2}. [{score:.3f}] {artifact:<45} ({source})")
        print(f"       {benefit}")
        todo_items.append({
            "rank":     rank,
            "score":    round(score, 4),
            "artifact": artifact,
            "benefit":  benefit,
            "source":   source,
            "math":     idea.get("math_grounding", idea.get("math", ""))[:100],
        })

    if not dry_run:
        TODO_FILE.write_text(json.dumps({
            "generated_at": now.isoformat(),
            "total_actionable": total,
            "todo": todo_items,
        }, indent=2))
        OUT_FILE.write_text(json.dumps({
            "ts": now.isoformat(), "scanned": len(ideas),
            "actionable": total, "top": todo_items,
        }, indent=2))
        print(f"\nTODO written: {TODO_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--top",     type=int, default=DEFAULT_TOP)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.top, args.dry_run))


if __name__ == "__main__":
    main()

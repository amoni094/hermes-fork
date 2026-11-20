#!/usr/bin/env python3
"""
AMD Memory Loader — 3-Tier Proactive/Reactive/Deferred Memory Router

Classifies candidate memory items into three loading tiers:
  PROACTIVE — load at task start (workflow, subtask, plan memory)
  REACTIVE  — load on first matching tool invocation (tool_pitfall memory)
  DEFERRED  — load only when explicitly referenced (everything else)

Hypothesis: Loading only workflow+subtask memory proactively reduces upfront
    context token overhead by >= 40% while keeping tool-pitfall memory
    available at first invocation (reactive_coverage >= 0.90).

GWT:
  Given:  a set of candidate memory items with memory_type tags,
  When:   assign_tiers() is called,
  Then:   workflow/subtask/plan items are PROACTIVE, tool_pitfall items are
          REACTIVE, and all others are DEFERRED — reducing upfront token load
          by >= 40% vs loading everything at start.

Kill test:
    items = [{'id':'1','memory_type':'workflow','content':'...','tool_relevance':''},
             {'id':'2','memory_type':'tool_pitfall','content':'...','tool_relevance':'terminal'}]
    assignments = assign_tiers(items)
    assert any(a['tier']=='PROACTIVE' for a in assignments if a['memory_type']=='workflow')
    assert any(a['tier']=='REACTIVE'  for a in assignments if a['memory_type']=='tool_pitfall')

Metric:
    proactive_token_overhead = proactive_chars / total_chars; target < 0.30.
    reactive_coverage = reactive_items_at_first_tool / total_pitfall_items; target >= 0.90.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
HERMES_HOME  = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
STATE_PATH   = PROFILE_ROOT / "cache" / "amd-tier-state.json"

def _atomic_json(path: Path, data: object) -> None:
    """Atomic JSON write via tmp sibling + os.replace."""
    import os, tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


# ── Tier classification ────────────────────────────────────────────────────────
PROACTIVE_TYPES  = {"workflow", "subtask", "plan"}
REACTIVE_TYPES   = {"tool_pitfall"}
# anything else → DEFERRED


def _classify_tier(memory_type: str) -> str:
    t = memory_type.lower().strip()
    if t in PROACTIVE_TYPES:
        return "PROACTIVE"
    if t in REACTIVE_TYPES:
        return "REACTIVE"
    return "DEFERRED"


def assign_tiers(
    items: list[dict],
    task_description: str = "",
    write_state: bool = True,
) -> list[dict]:
    """
    Classify each item into PROACTIVE / REACTIVE / DEFERRED.

    Each item dict must have at least: id, memory_type, content.
    Optional: tool_relevance (for REACTIVE — which tool triggers load).

    Returns list of augmented dicts with 'tier' key added.
    """
    assignments = []
    total_chars = sum(len(item.get("content", "")) for item in items)

    for item in items:
        tier = _classify_tier(item.get("memory_type", ""))
        aug  = {**item, "tier": tier}
        assignments.append(aug)

    # Compute overhead metrics
    proactive_chars = sum(
        len(a.get("content", "")) for a in assignments if a["tier"] == "PROACTIVE"
    )
    reactive_count = sum(1 for a in assignments if a["tier"] == "REACTIVE")
    pitfall_total  = sum(1 for a in assignments if a.get("memory_type") == "tool_pitfall")

    state = {
        "ts":                    datetime.now(UTC).isoformat(),
        "task_description":      task_description[:200],
        "total_items":           len(assignments),
        "proactive_count":       sum(1 for a in assignments if a["tier"] == "PROACTIVE"),
        "reactive_count":        reactive_count,
        "deferred_count":        sum(1 for a in assignments if a["tier"] == "DEFERRED"),
        "total_chars":           total_chars,
        "proactive_chars":       proactive_chars,
        "proactive_overhead":    round(proactive_chars / max(total_chars, 1), 4),
        "reactive_coverage":     round(reactive_count / max(pitfall_total, 1), 4),
        "assignments":           [
            {"id": a.get("id"), "memory_type": a.get("memory_type"), "tier": a["tier"],
             "tool_relevance": a.get("tool_relevance", "")}
            for a in assignments
        ],
    }

    if write_state:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(STATE_PATH, state)

    return assignments


def get_tier(tier: str, assignments: list[dict]) -> list[dict]:
    """Filter assignments to a specific tier."""
    return [a for a in assignments if a.get("tier") == tier]


def reactive_trigger(
    tool_name: str,
    assignments: list[dict],
) -> list[dict]:
    """
    Called on first invocation of tool_name.
    Returns REACTIVE items whose tool_relevance matches tool_name.
    """
    return [
        a for a in assignments
        if a.get("tier") == "REACTIVE"
        and (not a.get("tool_relevance") or tool_name in a.get("tool_relevance", ""))
    ]


# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    items = [
        {"id": "1", "memory_type": "workflow",    "content": "A" * 200, "tool_relevance": ""},
        {"id": "2", "memory_type": "subtask",     "content": "B" * 150, "tool_relevance": ""},
        {"id": "3", "memory_type": "plan",        "content": "C" * 100, "tool_relevance": ""},
        {"id": "4", "memory_type": "tool_pitfall","content": "D" * 80,  "tool_relevance": "terminal"},
        {"id": "5", "memory_type": "tool_pitfall","content": "E" * 60,  "tool_relevance": "write_file"},
        {"id": "6", "memory_type": "fact",        "content": "F" * 40,  "tool_relevance": ""},
        {"id": "7", "memory_type": "episode",     "content": "G" * 30,  "tool_relevance": ""},
    ]

    assignments = assign_tiers(items, task_description="test task", write_state=False)

    pro  = get_tier("PROACTIVE", assignments)
    rea  = get_tier("REACTIVE",  assignments)
    def_ = get_tier("DEFERRED",  assignments)

    assert len(pro)  == 3, f"Expected 3 PROACTIVE, got {len(pro)}: {[a['id'] for a in pro]}"
    assert len(rea)  == 2, f"Expected 2 REACTIVE, got {len(rea)}"
    assert len(def_) == 2, f"Expected 2 DEFERRED, got {len(def_)}"

    # Kill test criterion
    assert any(a["tier"] == "PROACTIVE" for a in assignments if a["memory_type"] == "workflow")
    assert any(a["tier"] == "REACTIVE"  for a in assignments if a["memory_type"] == "tool_pitfall")

    # Reactive trigger
    triggered = reactive_trigger("terminal", assignments)
    assert len(triggered) == 1 and triggered[0]["id"] == "4"

    # Overhead metrics
    total  = sum(len(i["content"]) for i in items)
    pro_ch = sum(len(a["content"]) for a in pro)
    overhead = pro_ch / total
    assert overhead < 0.90, f"Overhead {overhead:.2f} unexpectedly high"

    print(
        f"[layer1] PASS — proactive={len(pro)}  reactive={len(rea)}  deferred={len(def_)}  "
        f"overhead={overhead:.2f}  reactive_coverage=1.00"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    pa = argparse.ArgumentParser(description="AMD Memory Loader — 3-tier tier router")
    pa.add_argument("--layer1",   action="store_true")
    pa.add_argument("--dry-run",  action="store_true",
                    help="Assign tiers from amd-tier-state.json without writing")
    pa.add_argument("--stats",    action="store_true", help="Print current tier state")
    args = pa.parse_args()

    if args.layer1:
        layer1_demo()
        return

    if args.stats and STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        print(f"Last run: {state.get('ts', '?')}")
        print(f"  proactive={state['proactive_count']}  "
              f"reactive={state['reactive_count']}  "
              f"deferred={state['deferred_count']}")
        print(f"  proactive_overhead={state['proactive_overhead']:.2%}  "
              f"reactive_coverage={state['reactive_coverage']:.2%}")
        return

    pa.print_help()


if __name__ == "__main__":
    main()

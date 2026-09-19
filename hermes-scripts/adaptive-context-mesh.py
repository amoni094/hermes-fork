#!/usr/bin/python3
"""
adaptive-context-mesh.py

Reduces context bloat and token waste by dynamically allocating memory
slots based on the current task's information-density requirements.

CS SPIKE basis (Adaptive Meshing for CPA Lyapunov Function Synthesis):
Applies adaptive mesh refinement to context management: high-uncertainty
regions of the context receive more "resolution" (kept verbatim); low-
uncertainty settled regions are compressed or evicted.

Math basis: Lyapunov-guided adaptive partitioning
  Define a "context energy" E(block) for each context block:
    E(block) = uncertainty(block) × recency_weight(block) × relevance(block)
  
  Mesh refinement rule:
    If E(block) > refine_threshold  → keep verbatim (high resolution)
    If E(block) < coarsen_threshold → compress/summarise (low resolution)
    Otherwise                       → keep as-is

  Applied to Hermes sessions: score each tool-result block by
  (a) how recently it was used as input to another tool call,
  (b) how many subsequent tool calls referenced its content,
  (c) its raw token length (longer = more expensive to keep).

  Output: ranked compression recommendations for the current session.

Usage:
  python3 adaptive-context-mesh.py [session_id] [--dry-run]
  python3 adaptive-context-mesh.py --all-sessions
"""

from __future__ import annotations
import os

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "adaptive-context-mesh.json"

REFINE_THRESHOLD  = 0.65   # E > this → keep verbatim
COARSEN_THRESHOLD = 0.25   # E < this → compress / evict
RECENCY_DECAY     = 0.80   # per-step decay on recency weight


def _load_session_blocks(session_path: Path) -> list[dict]:
    """Parse JSONL session into context blocks with metadata."""
    blocks = []
    lines  = session_path.read_text().splitlines()
    for idx, line in enumerate(lines):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        role    = ev.get("role", "")
        content = ev.get("content", ev.get("api_content", ""))
        text    = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict):
                    text += b.get("text", "") + str(b.get("input", ""))

        token_est = len(text) // 4
        blocks.append({
            "idx":        idx,
            "role":       role,
            "token_est":  token_est,
            "text_snippet": text[:120].replace("\n", " "),
            "has_tool":   "tool_use" in text or "tool_result" in text,
        })
    return blocks


def _compute_energy(blocks: list[dict]) -> list[dict]:
    """
    Compute context energy E(block) for each block.
    E = uncertainty × recency × relevance
    """
    n = len(blocks)
    results = []

    for i, b in enumerate(blocks):
        # Recency: exponential decay from the end
        steps_from_end  = n - 1 - i
        recency         = RECENCY_DECAY ** steps_from_end

        # Relevance proxy: blocks with tool calls/results are higher relevance
        relevance = 0.8 if b["has_tool"] else 0.3
        # Longer blocks are slightly less relevant per token (diminishing returns)
        length_penalty = min(1.0, 500 / max(b["token_est"], 1))
        relevance *= length_penalty

        # Uncertainty: assistant blocks with large output = high uncertainty
        if b["role"] == "assistant" and b["token_est"] > 200:
            uncertainty = 0.7
        elif b["role"] == "user":
            uncertainty = 0.5
        else:
            uncertainty = 0.4

        energy = float(uncertainty * recency * relevance)
        action = "KEEP" if energy >= REFINE_THRESHOLD else \
                 "COMPRESS" if energy < COARSEN_THRESHOLD else "RETAIN"

        results.append({
            **b,
            "recency":     round(recency, 4),
            "relevance":   round(relevance, 4),
            "uncertainty": uncertainty,
            "energy":      round(energy, 4),
            "action":      action,
        })

    return results


def _summarise_mesh(scored: list[dict]) -> dict:
    keep     = [b for b in scored if b["action"] == "KEEP"]
    compress = [b for b in scored if b["action"] == "COMPRESS"]
    retain   = [b for b in scored if b["action"] == "RETAIN"]

    tokens_total    = sum(b["token_est"] for b in scored)
    tokens_keep     = sum(b["token_est"] for b in keep)
    tokens_compress = sum(b["token_est"] for b in compress)
    savings_pct     = tokens_compress / max(tokens_total, 1)

    return {
        "total_blocks":   len(scored),
        "keep_count":     len(keep),
        "retain_count":   len(retain),
        "compress_count": len(compress),
        "tokens_total":   tokens_total,
        "tokens_keep":    tokens_keep,
        "tokens_compress": tokens_compress,
        "savings_pct":    round(savings_pct, 4),
    }


def run_session(session_path: Path, dry_run: bool) -> dict:
    blocks = _load_session_blocks(session_path)
    if not blocks:
        return {"session": session_path.stem, "error": "empty"}
    scored = _compute_energy(blocks)
    summary = _summarise_mesh(scored)
    return {"session": session_path.stem, "summary": summary, "scored": scored}


def run(session_id: str | None, all_sessions: bool, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    all_results = []

    if all_sessions or not session_id:
        paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]
    else:
        paths = list(SESSIONS_DIR.glob(f"*{session_id}*.jsonl"))

    if not paths:
        print(f"[adaptive-mesh] No sessions found")
        return 0

    print(f"[adaptive-mesh] Analysing {len(paths)} session(s)")

    for p in paths:
        result = run_session(p, dry_run)
        if "error" in result:
            continue
        s = result["summary"]
        all_results.append(result)

        if s["savings_pct"] > 0.40 and s["total_blocks"] >= 8 and s["tokens_total"] >= 500:
            alarms.append(
                f"HIGH_BLOAT: session {result['session'][:16]} — "
                f"{s['savings_pct']:.0%} of tokens in COMPRESS zone "
                f"({s['tokens_compress']:,} of {s['tokens_total']:,})"
            )

    print(f"\n=== Adaptive Context Mesh — {now[:10]} ===")
    for r in all_results:
        s = r["summary"]
        print(f"  {r['session'][:20]}: blocks={s['total_blocks']} "
              f"tokens={s['tokens_total']:,} "
              f"KEEP={s['keep_count']} RETAIN={s['retain_count']} COMPRESS={s['compress_count']} "
              f"savings={s['savings_pct']:.0%}")

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} high-bloat session(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — context density within bounds")
        alarm_exit = 0

    if not dry_run and all_results:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now,
            "sessions": [{
                "session": r["session"],
                "summary": r["summary"],
                # omit full scored list to keep file small
            } for r in all_results],
            "alarms": alarms,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id", nargs="?", default=None)
    parser.add_argument("--all-sessions", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import sys
    sys.exit(run(session_id=args.session_id, all_sessions=args.all_sessions, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

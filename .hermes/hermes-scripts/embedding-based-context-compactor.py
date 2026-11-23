#!/usr/bin/python3
"""
embedding-based-context-compactor.py

Reduces context-routing overhead by summarising noisy/tangential agent
history using rate-distortion optimal selection — keeps only context
blocks that maximise mutual information with the current task.

Math basis: Rate-Distortion View of Memory (arXiv spike)
  Optimal context = argmin_{S ⊆ blocks} |S| s.t. I(S; task) ≥ I_min
  Operationally (without embeddings): proxy I(block; task) via TF-IDF-like
  relevance = |tokens(block) ∩ tokens(task)| / sqrt(|tokens(block)|)
  Compression: drop blocks with relevance < RELEVANCE_FLOOR until
  budget |S| ≤ MAX_BLOCKS.

Usage:
  python3 embedding-based-context-compactor.py --task "TASK" [--budget 8]
  python3 embedding-based-context-compactor.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "context-compaction-report.json"

MAX_BLOCKS      = 8      # target context budget in blocks
RELEVANCE_FLOOR = 0.05   # drop blocks below this relevance to task
CHARS_PER_TOKEN = 4


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _relevance(block_text: str, task_tokens: set[str]) -> float:
    """TF-IDF-proxy relevance: overlap normalised by block length."""
    bt = _tokens(block_text)
    if not bt or not task_tokens:
        return 0.0
    return len(bt & task_tokens) / math.sqrt(len(bt))


def compact_session(session_path: Path, task: str, budget: int) -> dict:
    task_tokens = _tokens(task)
    blocks: list[dict] = []

    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            role    = ev.get("role", "")
            content = ev.get("api_content", ev.get("content", ""))
            text    = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        text += b.get("text", "")
            if text.strip() and role in ("user", "assistant", "tool"):
                rel = _relevance(text, task_tokens)
                blocks.append({
                    "role":     role,
                    "tokens":   len(text) // CHARS_PER_TOKEN,
                    "relevance": round(rel, 4),
                    "preview":  text[:60].replace("\n", " "),
                })
        except Exception:
            pass

    if not blocks:
        return {"session": session_path.stem, "note": "no blocks", "kept": 0, "dropped": 0}

    # Rate-distortion selection: keep top-budget blocks by relevance,
    # always keeping blocks above RELEVANCE_FLOOR
    above_floor = [b for b in blocks if b["relevance"] >= RELEVANCE_FLOOR]
    selected    = sorted(above_floor, key=lambda b: b["relevance"], reverse=True)[:budget]
    dropped     = len(blocks) - len(selected)
    saved_tok   = sum(b["tokens"] for b in blocks) - sum(b["tokens"] for b in selected)

    return {
        "session":    session_path.stem,
        "total":      len(blocks),
        "kept":       len(selected),
        "dropped":    dropped,
        "saved_tok":  saved_tok,
        "top_blocks": selected[:3],
    }


def run(task: str, budget: int, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-5:]

    if not paths:
        print("[compactor] No sessions found")
        return 0

    print(f"\n=== Embedding-Based Context Compactor — {now[:10]} ===")
    print(f"Task: \"{task[:70]}\"  Budget: {budget} blocks\n")

    results = []
    for p in paths:
        r = compact_session(p, task, budget)
        results.append(r)
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            pct = r['dropped'] / max(r['total'], 1) * 100
            print(f"  {r['session'][:30]}  "
                  f"kept={r['kept']}/{r['total']}  "
                  f"dropped={r['dropped']} ({pct:.0f}%)  "
                  f"saved≈{r['saved_tok']} tok")
            for b in r.get("top_blocks", []):
                print(f"    [{b['role']} rel={b['relevance']:.3f}] {b['preview']}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "task": task, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",    default="implement agent memory compression")
    p.add_argument("--budget",  type=int, default=MAX_BLOCKS)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.budget, args.dry_run))


if __name__ == "__main__":
    main()

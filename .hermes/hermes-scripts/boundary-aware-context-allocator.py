#!/usr/bin/python3
"""
boundary-aware-context-allocator.py

Session context is pruned not uniformly but task-aware: critical state
transitions near semantic decision boundaries get higher context budget.

Math basis: Cramér–Rao bound (CRB)
  Var(θ̂) >= 1 / I(θ)   where I(θ) = Fisher information at boundary.
  Near a semantic decision boundary, I(θ) is high → estimation variance
  is low → context blocks near boundaries are HIGH VALUE and should be
  kept. Far from boundaries, I(θ) ≈ 0 → blocks can be pruned.
  
  Operationally: score each context block by proximity to a decision
  boundary (topic shift, tool change, error, constraint mention) and
  allocate budget proportional to boundary proximity score.

Usage:
  python3 boundary-aware-context-allocator.py --budget 8000 [--session F]
  python3 boundary-aware-context-allocator.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "boundary-context-allocation.json"

# Boundary signals: each pattern adds to boundary score
BOUNDARY_PATTERNS = [
    (r"(?i)\b(error|exception|failed|crash|traceback)\b",    2.0),
    (r"(?i)\b(constraint|must not|forbidden|blocked|deny)\b", 1.5),
    (r"(?i)\b(decision|choose|select|pick|route|branch)\b",   1.2),
    (r"(?i)\b(alarm|warning|alert|critical|urgent)\b",        1.8),
    (r"(?i)\b(changed|switched|now using|instead|pivot)\b",   1.3),
    (r"(?i)\b(result|output|conclusion|therefore|thus)\b",    1.0),
]

MIN_BLOCK_CHARS = 50


def _boundary_score(text: str) -> float:
    """Fisher-information proxy: sum of pattern weights in text."""
    score = 0.0
    for pat, weight in BOUNDARY_PATTERNS:
        score += weight * len(re.findall(pat, text))
    # Normalise by text length so short blocks aren't penalised
    length_factor = min(1.0, len(text) / 200)
    return score * length_factor


def _load_blocks(session_path: Path) -> list[dict]:
    """Load session messages as text blocks."""
    try:
        data = json.loads(session_path.read_text())
    except Exception:
        return []
    messages = data if isinstance(data, list) else data.get("messages", [])
    blocks   = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
            )
        else:
            text = str(content)
        if len(text) < MIN_BLOCK_CHARS:
            continue
        blocks.append({
            "idx":   i,
            "role":  role,
            "chars": len(text),
            "text":  text[:120],
            "score": _boundary_score(text),
        })
    return blocks


def allocate(blocks: list[dict], budget: int) -> dict:
    """Allocate budget proportional to boundary score, with floor."""
    if not blocks:
        return {"blocks": [], "total_chars": 0, "kept": 0, "budget": budget}

    total_chars = sum(b["chars"] for b in blocks)
    if total_chars <= budget:
        # Everything fits
        for b in blocks:
            b["allocated"] = b["chars"]
            b["kept"]      = True
        return {"blocks": blocks, "total_chars": total_chars,
                "kept": len(blocks), "budget": budget}

    # Score-proportional allocation with uniform floor
    total_score = sum(b["score"] for b in blocks) or 1.0
    floor       = budget * 0.4 / len(blocks)   # 40% budget split equally

    allocations = []
    for b in blocks:
        prop = (b["score"] / total_score) * budget * 0.6   # 60% score-weighted
        alloc = floor + prop
        allocations.append(min(alloc, b["chars"]))

    # Scale to exactly fill budget
    scale = budget / max(sum(allocations), 1)
    kept  = 0
    for b, alloc in zip(blocks, allocations):
        b["allocated"] = round(alloc * scale)
        b["kept"]      = b["allocated"] >= MIN_BLOCK_CHARS
        if b["kept"]:
            kept += 1

    return {"blocks": blocks, "total_chars": total_chars,
            "kept": kept, "budget": budget}


def run(budget: int, session_path: Path | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Demo blocks if no session
    demo_blocks = [
        {"idx": 0, "role": "user",      "chars": 120, "text": "Read the config file and show me the settings.", "score": 0.0},
        {"idx": 1, "role": "assistant", "chars": 340, "text": "error: permission denied reading config.json — traceback follows.", "score": 0.0},
        {"idx": 2, "role": "user",      "chars": 80,  "text": "Try a different approach instead.", "score": 0.0},
        {"idx": 3, "role": "assistant", "chars": 520, "text": "Result: successfully read via sudo. Conclusion: use elevated mode.", "score": 0.0},
        {"idx": 4, "role": "user",      "chars": 200, "text": "Deploy to production. Critical: must not exceed rate limit constraint.", "score": 0.0},
        {"idx": 5, "role": "assistant", "chars": 400, "text": "Checking current load. Warning: approaching 90% capacity threshold.", "score": 0.0},
    ]

    if session_path and session_path.exists():
        blocks = _load_blocks(session_path)
    else:
        blocks = demo_blocks

    # Compute boundary scores
    for b in blocks:
        b["score"] = _boundary_score(b["text"])

    result = allocate(blocks, budget)

    print(f"\n=== Boundary-Aware Context Allocator — {now[:10]} ===")
    print(f"Budget: {budget} chars  Blocks: {len(blocks)}  "
          f"Total: {result['total_chars']}  Kept: {result['kept']}\n")

    print(f"  {'#':<3} {'Role':<10} {'Score':>6} {'Chars':>6} {'Alloc':>6}  Status")
    print("  " + "-" * 52)
    for b in result["blocks"]:
        icon = "✓" if b.get("kept", True) else "✗"
        print(f"  {icon} {b['idx']:<2} {b['role']:<10} {b['score']:>6.2f} "
              f"{b['chars']:>6} {b.get('allocated', b['chars']):>6}")

    print(f"\nALARM: no — allocation complete")
    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "budget": budget, "kept": result["kept"],
            "total": result["total_chars"],
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--budget",  type=int, default=800)
    p.add_argument("--session", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.budget, args.session, args.dry_run))


if __name__ == "__main__":
    main()

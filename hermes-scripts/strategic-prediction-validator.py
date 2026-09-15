#!/usr/bin/python3
"""
strategic-prediction-validator.py

Enables multi-agent task delegation by routing predictions to different
skill subsets and validating that they agree — detects when agents are
making strategically inconsistent predictions about the same task.

Math basis: strategic prediction consistency via Condorcet-style voting
  Given k agents each predicting outcome O_i for task T:
  A prediction set is CONSISTENT iff there exists a majority winner W such
  that |{i : O_i agrees with W}| > k/2.
  INCONSISTENT (strategic fragmentation) when no majority exists.
  
  Agreement metric: token-level Jaccard similarity between predictions.
  Majority winner: prediction with highest average similarity to all others.
  Fragmentation score: 1 - max_agreement  (0=unanimous, 1=fully fragmented)

Usage:
  python3 strategic-prediction-validator.py --predictions "pred1" "pred2" "pred3"
  python3 strategic-prediction-validator.py --file predictions.json
  python3 strategic-prediction-validator.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "strategic-prediction-validation.json"

FRAGMENTATION_THRESHOLD = 0.55   # flag if fragmentation > 0.55


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]{2,}", text.lower()))


def _jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 1.0


def validate_predictions(predictions: list[str]) -> dict:
    n = len(predictions)
    if n < 2:
        return {"error": f"need ≥2 predictions, got {n}"}

    tokens = [_tokenize(p) for p in predictions]

    # Pairwise similarity matrix
    sim = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            sim[i, j] = _jaccard(tokens[i], tokens[j])

    # Majority winner: highest average similarity to others
    avg_sim     = sim.mean(axis=1)
    winner_idx  = int(np.argmax(avg_sim))
    max_agree   = float(avg_sim[winner_idx])
    frag_score  = 1.0 - max_agree

    # Majority check: how many agree with winner (Jaccard > 0.3)?
    agree_count = sum(1 for j in range(n) if j != winner_idx and sim[winner_idx, j] > 0.30)
    has_majority = agree_count > (n - 1) / 2

    fragmented = frag_score > FRAGMENTATION_THRESHOLD or not has_majority

    return {
        "n_predictions":    n,
        "winner_idx":       winner_idx,
        "winner_preview":   predictions[winner_idx][:80],
        "max_agreement":    round(max_agree, 4),
        "fragmentation":    round(frag_score, 4),
        "majority_count":   agree_count,
        "has_majority":     has_majority,
        "fragmented":       fragmented,
        "pairwise_sim":     [[round(float(sim[i,j]),3) for j in range(n)] for i in range(n)],
    }


def run(predictions: list[str] | None, input_file: Path | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if input_file and input_file.exists():
        data        = json.loads(input_file.read_text())
        predictions = data if isinstance(data, list) else data.get("predictions", [])

    if not predictions:
        # Demo
        predictions = [
            "The root cause is a missing null check in the validation function.",
            "The bug occurs because the validation function doesn't handle null inputs.",
            "I cannot determine the root cause without more context and stack traces.",
            "The issue is in the validation module — null values bypass the guard.",
        ]
        print(f"[strategic-validator] Using {len(predictions)} demo predictions")

    result = validate_predictions(predictions)
    print(f"\n=== Strategic Prediction Validator — {now[:10]} ===")

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1

    print(f"Predictions:     {result['n_predictions']}")
    print(f"Winner (idx {result['winner_idx']}): {result['winner_preview']}")
    print(f"Max agreement:   {result['max_agreement']:.4f}")
    print(f"Fragmentation:   {result['fragmentation']:.4f}  (threshold={FRAGMENTATION_THRESHOLD})")
    print(f"Majority:        {result['majority_count']}/{result['n_predictions']-1} agree  "
          f"({'YES' if result['has_majority'] else 'NO'})")

    print(f"\nPairwise similarity matrix:")
    for i, row in enumerate(result["pairwise_sim"]):
        print(f"  [{i}] {row}")

    if result["fragmented"]:
        print(f"\nALARM: yes — predictions are strategically fragmented "
              f"(fragmentation={result['fragmentation']:.3f})")
        alarm_exit = 1
    else:
        print(f"\nALARM: no — predictions show sufficient consensus")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "result": result}, indent=2))
        print(f"Written: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", nargs="+", default=None)
    p.add_argument("--file",        type=Path, default=None, dest="input_file")
    p.add_argument("--dry-run",     action="store_true")
    args = p.parse_args()
    sys.exit(run(args.predictions, args.input_file, args.dry_run))


if __name__ == "__main__":
    main()

#!/usr/bin/python3
"""
consensus-reward-scorer.py

Enables test-time policy scoring for code generation and skill outputs
without labeled answers — uses probe consensus (rank-masked majority
agreement) as a reward signal.

CS SPIKE basis (Entropy-Regularized Rank-Masked Policy Optimization):
  Ground-truth labels are unavailable at test time. Instead, probe outputs
  are ranked; masked majority agreement acts as a reward proxy. High
  agreement → high reward. Entropy regularization prevents collapse to
  degenerate consensus.

Math basis: entropy-regularized consensus reward
  R_consensus(y_1..y_k) = (1/k) Σ sim(y_i, mode(Y)) - λ·H(Y)
  where:
    sim: normalized overlap (Jaccard on token sets)
    mode(Y): plurality answer (most common structure)
    H(Y): entropy of agreement distribution (discourages uniformity collapse)
    λ: entropy regularization weight (default 0.1)

  Rank-masking: discard bottom-p fraction of outputs by length-normalised
  score before computing consensus, preventing outliers from skewing mode.

Usage:
  python3 consensus-reward-scorer.py --outputs "ans1" "ans2" "ans3"
  python3 consensus-reward-scorer.py --file outputs.json
  python3 consensus-reward-scorer.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import numpy as np

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "consensus-reward-scores.json"

LAMBDA_ENT  = 0.10   # entropy regularization weight
MASK_FRAC   = 0.20   # discard bottom 20% by raw length-normalised score
MIN_OUTPUTS = 2


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]{2,}", text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def _structural_key(text: str) -> str:
    """Coarse structural fingerprint for mode detection."""
    has_json  = int("{" in text and "}" in text)
    has_list  = int(bool(re.search(r"^\s*[-*\d]", text, re.MULTILINE)))
    has_code  = int(bool(re.search(r"def |class |import ", text)))
    len_bin   = min(len(text) // 200, 5)
    return f"j{has_json}l{has_list}c{has_code}L{len_bin}"


def _entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p + 1e-12) for p in probs if p > 0)


def score_outputs(outputs: list[str], lambda_ent: float = LAMBDA_ENT,
                  mask_frac: float = MASK_FRAC) -> dict:
    n = len(outputs)
    if n < MIN_OUTPUTS:
        return {"error": f"need ≥{MIN_OUTPUTS} outputs, got {n}"}

    tokens = [_tokenize(o) for o in outputs]

    # Length-normalised raw score: average Jaccard with all others
    raw_scores = []
    for i, ti in enumerate(tokens):
        others = [tokens[j] for j in range(n) if j != i]
        avg_j = np.mean([_jaccard(ti, tj) for tj in others]) if others else 0.0
        len_norm = min(len(outputs[i]) / 500.0, 1.0)
        raw_scores.append(float(avg_j) * (0.5 + 0.5 * len_norm))

    # Rank-masking: discard bottom mask_frac
    threshold = np.quantile(raw_scores, mask_frac)
    kept = [(i, o, tokens[i]) for i, o in enumerate(outputs)
            if raw_scores[i] >= threshold]

    if not kept:
        kept = [(i, o, tokens[i]) for i, o in enumerate(outputs)]

    # Mode: plurality structural key among kept outputs
    struct_keys = [_structural_key(o) for _, o, _ in kept]
    mode_key    = Counter(struct_keys).most_common(1)[0][0]

    # Consensus reward: similarity to mode outputs
    mode_tokens = _tokenize(
        " ".join(o for _, o, _ in kept
                 if _structural_key(o) == mode_key)
    )

    sims = [_jaccard(t, mode_tokens) for _, _, t in kept]
    r_consensus = float(np.mean(sims)) if sims else 0.0

    # Entropy of agreement distribution
    sim_probs = np.array(sims)
    if sim_probs.sum() > 0:
        sim_probs = sim_probs / sim_probs.sum()
    ent = _entropy(list(sim_probs))

    # Final regularized reward
    reward = r_consensus - lambda_ent * ent

    # Per-output rank
    ranked = sorted(
        [(i, raw_scores[i], _jaccard(tokens[i], mode_tokens))
         for i in range(n)],
        key=lambda x: -x[2]
    )

    return {
        "n_outputs":      n,
        "n_kept":         len(kept),
        "mode_key":       mode_key,
        "r_consensus":    round(r_consensus, 4),
        "entropy":        round(ent, 4),
        "lambda":         lambda_ent,
        "reward":         round(reward, 4),
        "ranked":         [(idx, round(rs, 4), round(sim, 4))
                           for idx, rs, sim in ranked],
    }


def run(outputs: list[str] | None, input_file: Path | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if input_file and input_file.exists():
        data    = json.loads(input_file.read_text())
        outputs = data if isinstance(data, list) else data.get("outputs", [])

    if not outputs:
        # Demo with synthetic outputs
        outputs = [
            "The answer is 42. Compute using: result = sum(range(10))",
            "Result: 42, via sum of first 9 integers: sum(range(10))",
            "42 is the answer. Code: sum(i for i in range(10))",
            "The total is 45 actually, sum(range(10)) = 45",   # outlier
        ]
        print(f"[consensus-scorer] Using {len(outputs)} demo outputs")

    result = score_outputs(outputs)

    print(f"\n=== Consensus Reward Scorer — {now[:10]} ===")
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1

    print(f"Outputs:      {result['n_outputs']} total, {result['n_kept']} kept after masking")
    print(f"Mode key:     {result['mode_key']}")
    print(f"R_consensus:  {result['r_consensus']:.4f}")
    print(f"Entropy H(Y): {result['entropy']:.4f}")
    print(f"Reward:       {result['reward']:.4f}  (= R - λ·H, λ={result['lambda']})")
    print(f"\nRanked outputs (idx, raw_score, consensus_sim):")
    for idx, rs, sim in result["ranked"]:
        flag = "  ← best" if idx == result["ranked"][0][0] else ""
        print(f"  [{idx}] raw={rs:.4f}  sim={sim:.4f}{flag}")

    alarm_exit = 0  # scorer is a utility, not a monitor; alarms handled upstream

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "result": result}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", nargs="+", default=None)
    parser.add_argument("--file",    type=Path,  default=None, dest="input_file")
    parser.add_argument("--lambda-ent", type=float, default=LAMBDA_ENT)
    parser.add_argument("--mask-frac",  type=float, default=MASK_FRAC)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(
        outputs=args.outputs,
        input_file=args.input_file,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()

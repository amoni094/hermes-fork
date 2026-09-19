#!/usr/bin/python3
"""
simulator-fisher-estimator.py

Enables uncertainty quantification and confidence intervals on learned
skill parameters and routing decisions by estimating Fisher information
from simulated perturbations.

Math basis: Fisher information via simulation
  I(θ) = E[(∂/∂θ log p(x|θ))²] = -E[∂²/∂θ² log p(x|θ)]
  Estimated via finite differences on log-likelihood:
    Î(θ) ≈ [log p(x|θ+ε) - 2·log p(x|θ) + log p(x|θ-ε)] / ε²  (negated)
  High Fisher information → sharp, confident parameter estimates.
  Low Fisher information → flat likelihood → routing decision uncertain.
  
  Applied to: skill routing weight θ = weight vector over skills.
  p(x|θ) = softmax(θ·features(x)) probability of correct skill selection.

Usage:
  python3 simulator-fisher-estimator.py --query QUERY
  python3 simulator-fisher-estimator.py --dry-run
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

import numpy as np

HOME       = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SKILLS_DIR = _RT / "skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "fisher-estimation.json"

EPS        = 0.01    # finite-difference step
LOW_FISHER = 1e-5    # alarm if Fisher info < 1e-5 (essentially zero — uniform routing)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _load_skills(n: int = 20) -> list[dict]:
    skills = []
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in list(base.rglob("SKILL.md"))[:n - len(skills)]:
            try:
                text = md.read_text()[:400]
                skills.append({"name": md.parent.name, "tokens": _tokenize(text)})
            except Exception:
                pass
        if len(skills) >= n:
            break
    return skills[:n]


def _log_likelihood(theta: np.ndarray, features: np.ndarray, target_idx: int) -> float:
    """Log p(target | theta) via softmax over per-skill scores."""
    # theta shape (n,), features shape (n,) — dot gives per-skill score
    scores  = theta * features          # element-wise: each skill's weighted feature
    log_sum = np.log(np.sum(np.exp(scores - scores.max()))) + scores.max()
    log_sm  = scores - log_sum          # log-softmax, shape (n,)
    return float(log_sm[target_idx])


def estimate_fisher(query: str, skills: list[dict]) -> dict:
    q_tok = _tokenize(query)
    n     = len(skills)

    # Feature vector: each skill's Jaccard overlap with query (shape n,)
    feat_vec = np.array([
        len(q_tok & s["tokens"]) / max(len(q_tok | s["tokens"]), 1)
        for s in skills
    ])  # shape (n,)

    # Guard: if all features are zero, query has no overlap with any skill
    # This is a skill-coverage gap, not a routing uncertainty problem
    if feat_vec.max() < 1e-9:
        return {
            "query":      query[:60],
            "n_skills":   n,
            "best_skill": None,
            "avg_fisher": 0.0,
            "max_fisher": 0.0,
            "uncertain":  False,
            "no_coverage": True,
            "top5_fisher": [],
        }

    # Initial routing weights: uniform
    theta     = np.ones(n) / n   # shape (n,)
    # Target: best-matching skill
    overlaps  = [len(q_tok & s["tokens"]) for s in skills]
    target_i  = int(np.argmax(overlaps))

    # Compute log-likelihood at θ, θ±ε for each dimension
    fishers = []
    for k in range(n):
        theta_p = theta.copy(); theta_p[k] += EPS
        theta_m = theta.copy(); theta_m[k] -= EPS

        ll   = _log_likelihood(theta,   feat_vec, target_i)
        ll_p = _log_likelihood(theta_p, feat_vec, target_i)
        ll_m = _log_likelihood(theta_m, feat_vec, target_i)

        # Finite-difference second derivative (negated = Fisher)
        fi = -(ll_p - 2*ll + ll_m) / (EPS ** 2)
        fishers.append(max(0.0, fi))

    avg_fisher = float(np.mean(fishers))
    max_fisher = float(np.max(fishers))
    best_skill = skills[target_i]["name"]

    return {
        "query":       query[:60],
        "n_skills":    n,
        "best_skill":  best_skill,
        "avg_fisher":  round(avg_fisher, 6),
        "max_fisher":  round(max_fisher, 6),
        "uncertain":   avg_fisher < LOW_FISHER,
        "top5_fisher": [
            {"skill": skills[i]["name"], "fisher": round(fishers[i], 6)}
            for i in sorted(range(n), key=lambda x: fishers[x], reverse=True)[:5]
        ],
    }


def run(query: str, dry_run: bool) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    skills = _load_skills(20)

    if not skills:
        print("[fisher-estimator] No skills found")
        return 1

    demo_queries = [query] if query != "agent memory compression" else [
        "agent memory compression",
        "configure hermes settings",
        "search for research papers",
        "debug python runtime error",
    ]

    print(f"\n=== Simulator Fisher Estimator — {now[:10]} ===")
    print(f"Skills: {len(skills)}\n")

    all_results = []
    uncertain   = 0
    no_coverage = 0

    for q in demo_queries:
        r = estimate_fisher(q, skills)
        if r.get("no_coverage"):
            icon = "○"
            print(f"  {icon} \"{r['query']}\"")
            print(f"      no_coverage — query has no overlap with loaded skills (coverage gap)")
            no_coverage += 1
        else:
            icon = "⚠" if r["uncertain"] else "✓"
            print(f"  {icon} \"{r['query']}\"")
            print(f"      best={r['best_skill']}  "
                  f"avg_fisher={r['avg_fisher']:.6f}  "
                  f"max={r['max_fisher']:.6f}  "
                  f"{'UNCERTAIN' if r['uncertain'] else 'confident'}")
            if r["uncertain"]:
                uncertain += 1
        all_results.append(r)

    print(f"\nUncertain queries: {uncertain}/{len(demo_queries)}  No-coverage: {no_coverage}/{len(demo_queries)}")
    if uncertain:
        print("ALARM: yes — routing Fisher information too low for confident decisions")
    else:
        print("ALARM: no — routing decisions are well-supported")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": all_results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return 1 if uncertain else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query",   default="agent memory compression")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.query, args.dry_run))


if __name__ == "__main__":
    main()

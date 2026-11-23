#!/usr/bin/env python3
"""
bps-skill-selector.py — Best Prefix Selection for budget-aware skill selection.

Based on: arXiv:2608.19993 "Optimal Skill Selection for LLM Agents with Provable
Bicriteria Guarantees". BPS finds a skill set under a hard token budget to maximize
a monotone submodular benefit minus context penalty.

Key result: bicriteria (1-1/e, 1) approximation — optimal in polynomial time.
Outperforms top-k/greedy on BigCodeBench by 0.73 vs 0.20-0.52 task success.

Wave 16 implementation: augments skill-router-index.py with budget-aware selection
that avoids redundant/overlapping skills and stays within context token budget.

Usage:
  python3 bps-skill-selector.py --query "some query" --budget 4000
  python3 bps-skill-selector.py --query "some query" --topk 3 --budget 6000
  python3 bps-skill-selector.py --stats
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# -- Profile-aware paths
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"
_SKILLS = _RT / "skills"

SELECTION_LOG = _CACHE / "bps-selection-log.jsonl"

# BPS hyperparams
REDUNDANCY_THRESHOLD = 0.65   # Jaccard overlap to penalize redundancy
CONTEXT_PENALTY = 0.15        # penalty per redundant pair
AVG_TOKENS_PER_SKILL = 600    # estimated token cost per SKILL.md load


def _tokenize(text: str) -> set[str]:
    return set(re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _skill_text(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text(errors="ignore")[:3000]
    return ""


def _estimate_tokens(text: str) -> int:
    return max(100, len(text) // 4)


def _relevance_score(skill_tokens: set[str], query_tokens: set[str]) -> float:
    """BM25-like relevance heuristic (no IDF available without corpus stats)."""
    overlap = len(skill_tokens & query_tokens)
    return overlap / (1 + len(skill_tokens) * 0.001)


def _submodular_benefit(selected: list[str], candidate: str,
                         relevances: dict[str, float],
                         skill_tokens: dict[str, set[str]]) -> float:
    """
    Monotone submodular benefit of adding candidate to selected set.
    Models: benefit = relevance - context_penalty * max_redundancy_with_selected
    The submodularity ensures greedy (1-1/e) approximation.
    """
    cand_rel = relevances.get(candidate, 0.0)
    if not selected:
        return cand_rel

    # Penalty: how much does candidate overlap with the selected set?
    cand_tok = skill_tokens.get(candidate, set())
    max_overlap = max(
        _jaccard(cand_tok, skill_tokens.get(s, set()))
        for s in selected
    )
    penalty = CONTEXT_PENALTY * max_overlap
    return max(0.0, cand_rel - penalty)


def bps_select(query: str, budget_tokens: int = 4000, topk: int = 5) -> list[dict]:
    """
    BPS greedy algorithm with token budget constraint.
    Returns ordered list of selected skills with metadata.
    """
    # Load all skills
    skills = {}
    for skill_dir in sorted(_SKILLS.iterdir()):
        if not skill_dir.is_dir():
            continue
        text = _skill_text(skill_dir)
        if not text:
            continue
        tokens = _tokenize(text)
        token_cost = _estimate_tokens(text)
        skills[skill_dir.name] = {
            "tokens": tokens,
            "text": text,
            "token_cost": token_cost,
            "snippet": text[:200],
        }

    if not skills:
        return []

    query_tokens = _tokenize(query)
    # Pre-compute relevance scores
    relevances = {
        name: _relevance_score(info["tokens"], query_tokens)
        for name, info in skills.items()
    }
    skill_tokens = {name: info["tokens"] for name, info in skills.items()}

    # BPS greedy: repeatedly pick skill with highest marginal submodular benefit
    # subject to token budget constraint
    selected = []
    remaining_budget = budget_tokens
    candidates = list(skills.keys())

    while candidates and len(selected) < topk:
        # Score each candidate: marginal benefit / token cost (efficiency)
        scored = []
        for cand in candidates:
            cost = skills[cand]["token_cost"]
            if cost > remaining_budget:
                continue  # over budget
            marginal = _submodular_benefit(selected, cand, relevances, skill_tokens)
            efficiency = marginal / max(1, cost)
            scored.append((efficiency, marginal, cand))

        if not scored:
            break

        scored.sort(reverse=True)
        _, marginal, best = scored[0]
        if marginal <= 0:
            break  # no beneficial addition

        selected.append(best)
        remaining_budget -= skills[best]["token_cost"]
        candidates.remove(best)

    # Build result
    results = []
    for name in selected:
        info = skills[name]
        results.append({
            "skill": name,
            "relevance": round(relevances.get(name, 0.0), 4),
            "token_cost": info["token_cost"],
            "snippet": info["snippet"][:120],
        })

    # Log
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query[:200],
        "budget_tokens": budget_tokens,
        "topk": topk,
        "selected": [r["skill"] for r in results],
        "total_tokens": sum(r["token_cost"] for r in results),
    }
    _CACHE.mkdir(parents=True, exist_ok=True)
    try:
        with open(SELECTION_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError:
        pass

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="BPS budget-aware skill selector")
    ap.add_argument("--query", help="Task query")
    ap.add_argument("--budget", type=int, default=4000, help="Token budget for skill set")
    ap.add_argument("--topk", type=int, default=5, help="Max skills to select")
    ap.add_argument("--stats", action="store_true", help="Show selection log stats")
    args = ap.parse_args()

    if args.stats:
        if not SELECTION_LOG.exists():
            print("[bps] No selection log found.")
            return 0
        lines = SELECTION_LOG.read_text().splitlines()
        print(f"[bps] Selection log: {len(lines)} entries")
        if lines:
            last = json.loads(lines[-1])
            print(f"[bps] Last: {last.get('ts')} | query: {last.get('query','')[:60]}")
            print(f"[bps] Selected: {last.get('selected')}")
        return 0

    if not args.query:
        ap.print_help()
        return 1

    results = bps_select(args.query, args.budget, args.topk)
    if not results:
        print("[bps] No skills selected within budget.")
        return 0

    print(f"[bps] Top-{len(results)} skills for: {args.query!r}")
    print(f"[bps] Token budget: {args.budget} | Used: {sum(r['token_cost'] for r in results)}")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r['skill']} (rel={r['relevance']:.4f}, cost={r['token_cost']}t)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

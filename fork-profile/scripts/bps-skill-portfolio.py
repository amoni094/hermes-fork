#!/usr/bin/env python3
"""
bps-skill-portfolio.py — Greedy submodular skill-portfolio filter (count budget).

Standalone fork-profile wrapper. Core greedy logic is copied from
hermes-scripts/bps-skill-selector.py (do not import that module).

Accepts (score, skill_dict) pairs from skill-router-index.route() and
selects a diverse subset under a count budget.

Usage:
  python3 bps-skill-portfolio.py --query TEXT --budget 5 --json
  python3 bps-skill-portfolio.py --self-test
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# -- Profile-aware paths (hermes-fork boilerplate)
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

# Copied from bps-skill-selector.py
REDUNDANCY_THRESHOLD = 0.65
CONTEXT_PENALTY = 0.15
AVG_TOKENS_PER_SKILL = 600

_ROUTER_NAME = "skill-router-index.py"


def _tokenize(text: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _submodular_benefit(
    selected: list[str],
    candidate: str,
    relevances: dict[str, float],
    skill_tokens: dict[str, set[str]],
) -> float:
    """
    Monotone submodular benefit of adding candidate to selected set.
    benefit = relevance - context_penalty * max_redundancy_with_selected
    Copied from bps-skill-selector.py.
    """
    cand_rel = relevances.get(candidate, 0.0)
    if not selected:
        return cand_rel

    cand_tok = skill_tokens.get(candidate, set())
    max_overlap = max(
        _jaccard(cand_tok, skill_tokens.get(s, set()))
        for s in selected
    )
    penalty = CONTEXT_PENALTY * max_overlap
    return max(0.0, cand_rel - penalty)


def _pair_key(idx: int, skill: dict) -> str:
    name = str(skill.get("name") or skill.get("skill") or "")
    return f"{idx}:{name}"


def filter_scored_skills(
    scored_pairs: list,
    budget: int = 5,
) -> list[dict]:
    """Greedy submodular maximization with a count budget.

    scored_pairs: list of (score, skill_dict) from skill-router-index.
    skill_dict fields used: name, description (score taken from the pair).
    Returns selected skill_dicts in greedy order (length <= budget).
    """
    if not scored_pairs or budget <= 0:
        return []

    relevances: dict[str, float] = {}
    skill_tokens: dict[str, set[str]] = {}
    skill_by_key: dict[str, dict] = {}
    candidates: list[str] = []

    for idx, item in enumerate(scored_pairs):
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        score, skill = item[0], item[1]
        if not isinstance(skill, dict):
            continue
        try:
            rel = float(score)
        except (TypeError, ValueError):
            rel = 0.0
        if rel < 0.0:
            rel = 0.0
        key = _pair_key(idx, skill)
        text = " ".join(
            str(skill.get(k, "") or "")
            for k in ("name", "description", "category")
        )
        relevances[key] = rel
        skill_tokens[key] = _tokenize(text)
        skill_by_key[key] = skill
        candidates.append(key)

    if not candidates:
        return []

    selected: list[str] = []
    remaining = list(candidates)
    cap = int(budget)

    while remaining and len(selected) < cap:
        scored = []
        for cand in remaining:
            marginal = _submodular_benefit(
                selected, cand, relevances, skill_tokens
            )
            scored.append((marginal, cand))
        if not scored:
            break
        scored.sort(key=lambda x: x[0], reverse=True)
        best_marginal, best = scored[0]
        if best_marginal <= 0:
            break
        # Enforce redundancy threshold: if max Jaccard overlap with any already-selected
        # skill exceeds REDUNDANCY_THRESHOLD, this candidate is too redundant to add.
        if selected:
            cand_tok = skill_tokens.get(best, set())
            max_overlap = max(
                _jaccard(cand_tok, skill_tokens.get(s, set())) for s in selected
            )
            if max_overlap >= REDUNDANCY_THRESHOLD:
                remaining.remove(best)
                continue
        selected.append(best)
        remaining.remove(best)

    return [skill_by_key[k] for k in selected]


def _load_router():
    router_path = Path(__file__).resolve().parent / _ROUTER_NAME
    if not router_path.exists():
        router_path = _hermes_root / "scripts" / _ROUTER_NAME
    if not router_path.exists():
        raise ImportError(f"skill-router-index not found: {router_path}")
    spec = importlib.util.spec_from_file_location(
        "skill_router_index_bps", str(router_path)
    )
    if spec is None or spec.loader is None:
        raise ImportError("failed to load skill-router-index spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def route_then_bps(query: str, budget: int = 5) -> list[dict]:
    """Call skill-router-index.route(), then BPS-filter to `budget` skills."""
    prev = os.environ.get("HERMES_BPS")
    os.environ["HERMES_BPS"] = "0"  # avoid double-filter if route() is wired
    try:
        router = _load_router()
        pool = max(int(budget) * 4, 20)
        candidates = router.route(query, top=pool)
    finally:
        if prev is None:
            os.environ.pop("HERMES_BPS", None)
        else:
            os.environ["HERMES_BPS"] = prev

    if not isinstance(candidates, list):
        candidates = []
    pairs = []
    for r in candidates:
        if not isinstance(r, dict):
            continue
        try:
            sc = float(r.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            sc = 0.0
        pairs.append((sc, r))
    return filter_scored_skills(pairs, budget=budget)


def _self_test() -> int:
    """Two near-identical skills + one different → different skill before clone."""
    clone_text = "linux kernel debugging kprobe ftrace printk oops"
    unique_text = "bayesian gaussian process regression kernel methods"
    pairs = [
        (0.90, {"name": "clone-a", "description": clone_text, "score": 0.90, "category": "sys"}),
        (0.89, {"name": "clone-b", "description": clone_text, "score": 0.89, "category": "sys"}),
        (0.80, {"name": "unique-c", "description": unique_text, "score": 0.80, "category": "ml"}),
    ]

    failures = []

    empty = filter_scored_skills([], budget=5)
    if empty != []:
        failures.append(f"empty input expected [] got {empty!r}")

    zero = filter_scored_skills(pairs, budget=0)
    if zero != []:
        failures.append(f"budget=0 expected [] got {zero!r}")

    selected = filter_scored_skills(pairs, budget=2)
    names = [s.get("name") for s in selected]
    if len(names) != 2:
        failures.append(f"budget=2 expected 2 skills, got {names!r}")
    elif names[0] not in ("clone-a", "clone-b"):
        failures.append(f"first pick should be a high-score clone, got {names!r}")
    elif names[1] != "unique-c":
        failures.append(
            f"BPS should select the different skill before the near-identical clone, got {names!r}"
        )
    if "clone-a" in names and "clone-b" in names:
        failures.append(f"selected both clones, dropped the different skill: {names!r}")

    selected3 = filter_scored_skills(pairs, budget=3)
    names3 = [s.get("name") for s in selected3]
    if "unique-c" not in names3:
        failures.append(f"budget=3 missing unique-c: {names3!r}")
    else:
        u = names3.index("unique-c")
        # The second clone, if present, must come after the different skill.
        clones_after = [i for i, n in enumerate(names3) if n in ("clone-a", "clone-b")]
        if clones_after and u < clones_after[-1] and u > clones_after[0]:
            pass  # unique between the two clones — correct
        if len(clones_after) == 2 and u > max(clones_after):
            failures.append(
                f"different skill selected last (after both clones): {names3!r}"
            )

    if failures:
        print("[bps-skill-portfolio] SELF-TEST FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[bps-skill-portfolio] SELF-TEST PASS")
    print("  empty=[] budget0=[]")
    print(f"  budget=2 order={names}  (different skill before second clone)")
    print(f"  budget=3 order={names3}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="BPS greedy submodular skill portfolio (count budget)"
    )
    ap.add_argument("--query", help="Task query (calls skill-router-index.route)")
    ap.add_argument(
        "--budget", type=int, default=5, help="Max skills to select (count budget)"
    )
    ap.add_argument("--json", action="store_true", help="Print JSON list")
    ap.add_argument(
        "--self-test", action="store_true", help="Run diversity self-test and exit"
    )
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.query:
        ap.print_help()
        return 1

    try:
        results = route_then_bps(args.query, budget=args.budget)
    except ImportError as exc:
        err = {"error": "import_failed", "detail": str(exc)}
        if args.json:
            print(json.dumps(err))
        else:
            print(f"[bps-skill-portfolio] import failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False))
        return 0

    if not results:
        print("[bps-skill-portfolio] No skills selected.")
        return 0
    print(f"[bps-skill-portfolio] budget={args.budget} selected={len(results)}")
    for i, r in enumerate(results, 1):
        name = r.get("name", "")
        score = r.get("score", "")
        desc = str(r.get("description", "")).replace("\n", " ")[:80]
        print(f"  {i}. {name}  score={score}  {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

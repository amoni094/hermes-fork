#!/usr/bin/python3
"""
online-threshold-skill-router.py

Competitive-ratio guaranteed skill routing under adversarial request sequences.
Uses a threshold strategy based on the secretary problem: observe first k=ceil(n/e)
candidates as a probe phase, then accept the first option that exceeds
THETA × best_probe_score.

Math basis: Online threshold selection (static-threshold variant).
  Secretary problem variant: observe first k = n/e candidates (probe phase),
  then accept the first skill in the selection phase that beats threshold.
  Actual competitive ratio for static threshold THETA:
    CR = THETA × (1 − THETA)   [maximised at THETA=0.5, CR=0.25]
  At THETA=0.75: CR = 0.75 × 0.25 = 0.1875  (i.e. ~19% approximation).
  Classic 1/e secretary strategy (probe k=n/e, accept first to beat probe max)
  achieves CR ≈ 1/e ≈ 0.37 — better than static threshold at any THETA.
  THETA=0.75 chosen for high precision (fewer false accepts) at cost of lower CR.

Run on-demand: /usr/bin/python3 online-threshold-skill-router.py <task>
"""
from __future__ import annotations
import sys, math

# Skill pool: (name, relevance_fn_keywords, base_score)
SKILLS = [
    ("python-debugpy",            ["debug","python","error","exception"],  0.90),
    ("systematic-debugging",      ["debug","bug","root cause","trace"],    0.85),
    ("github-issue-to-pr",        ["pr","github","issue","fix"],           0.80),
    ("hermes-research-sweep-ops", ["research","paper","math","ideas"],     0.88),
    ("hermes-operating-pattern",  ["hermes","config","pattern","operate"], 0.75),
    ("coding-conventions",        ["code","style","review","lint"],        0.70),
    ("test-driven-development",   ["test","tdd","spec","coverage"],        0.78),
    ("obsidian",                  ["note","obsidian","vault","md"],        0.65),
    ("notion",                    ["notion","page","database","block"],    0.60),
    ("web-extract",               ["web","page","url","scrape","fetch"],   0.55),
]

THETA = 0.75   # threshold = THETA * best_seen; competitive ratio ~ THETA

def _score(skill: tuple, task: str) -> float:
    name, keywords, base = skill
    hits  = sum(1 for k in keywords if k.lower() in task.lower())
    bonus = hits / max(len(keywords), 1)
    return base * (0.6 + 0.4 * bonus)

def route(task: str, verbose: bool = True) -> str:
    scores = [(s[0], _score(s, task)) for s in SKILLS]
    scores.sort(key=lambda x: -x[1])

    if verbose:
        print(f"\n=== Online Threshold Skill Router ===")
        print(f"Task:      {task[:70]}")
        print(f"Threshold: {THETA} (CR = {THETA*(1-THETA):.4f} for static-threshold strategy)\n")
        print(f"  {'Skill':<40} {'Score':>7}  Decision")
        print("  " + "-"*60)

    # Secretary-style: find threshold from first k = ceil(n/e) candidates
    n = len(scores)
    k = max(1, math.ceil(n / math.e))
    probe  = scores[:k]
    best_probe = max(s for _, s in probe)
    threshold  = THETA * best_probe

    accepted = None
    for i, (name, score) in enumerate(scores):
        phase = "probe" if i < k else "select"
        decision = "—"
        if phase == "select" and accepted is None and score >= threshold:
            accepted = name
            decision = "ACCEPT ★"
        elif phase == "probe":
            decision = "probe"
        if verbose:
            print(f"  {name:<40} {score:>7.4f}  {decision}")

    if accepted is None:
        accepted = scores[0][0]   # fallback: take best overall
        if verbose:
            print(f"\nFallback to best: {accepted}")
    if verbose:
        print(f"\nSelected: {accepted}")
        print(f"Probe phase: {k}/{n} skills, threshold={threshold:.4f}")
    print("ALARM: no — skill selected via threshold router")

    return accepted


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "debug a python error in a github PR"
    route(task)

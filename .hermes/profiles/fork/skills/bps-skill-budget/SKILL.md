---
name: bps-skill-budget
description: "Use when loading skills. BPS budget-aware selection."
tags: [skill-routing, budget, wave16]
---

# BPS Budget-Aware Skill Selection

Based on arXiv:2608.19993. Bicriteria (1-1/e, 1) approximation.
Outperforms top-k: 0.73 vs 0.20-0.52 task success on BigCodeBench.

## Algorithm
Greedy: add skill with highest marginal benefit/token_cost.
benefit = relevance - 0.15 x max_jaccard_overlap_with_selected.
Stop when budget exhausted or marginal benefit <= 0.

## Script
```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork \
  python3 ~/.hermes/hermes-scripts/bps-skill-selector.py --query "task" --budget 4000
python3 ~/.hermes/hermes-scripts/bps-skill-selector.py --stats
```

## Lessons
- budget=4000 normal; 6000-8000 for multi-skill complex tasks
- Prefer over top-k when task spans overlapping skill domains
- Redundancy penalty: 0.65 Jaccard threshold, 0.15 penalty weight
- Selection log: cache/bps-selection-log.jsonl

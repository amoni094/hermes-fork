---
name: ripple-mem-recall
description: "Use when recalling skills. RippleMem anchor expansion."
tags: [memory, recall, wave16]
---

# RippleMem Associative Memory Expansion

Based on arXiv:2607.18844. Anchor expansion via similarity graph finds related skills.

## Algorithm
1. Seed: top-8 anchors by Jaccard similarity
2. Ripple: BFS 2-hop expansion (threshold=0.65)
3. Rank: 0.7 x sim + 0.3 x recency (half-life=7d)

## Script
```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork \
  python3 ~/.hermes/hermes-scripts/ripple-mem-expander.py --build-graph
python3 ~/.hermes/hermes-scripts/ripple-mem-expander.py --query "context compression" --topk 5
python3 ~/.hermes/hermes-scripts/ripple-mem-expander.py --stats
```

## Cron: daily 3am (wave16-ripple-mem-graph-build)

## Lessons
- Rebuild graph after adding skills (stale graph misses edges)
- Lower ALPHA to 0.50 if graph is too sparse
- Graph: cache/ripple-mem-graph.json

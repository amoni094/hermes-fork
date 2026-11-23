---
name: statecomp-compression-timing
description: "Use when compressing context. StateComp span-readiness."
tags: [context, compression, wave16]
---

# StateComp Compression Timing Router

Based on arXiv:2609.27298. Only compress spans where reasoning is externalized to files/tools.

## Gate thresholds
- score >= 0.62, span_length >= 3, tokens >= 800, ready_ratio >= 0.55
- Never compress last 5 turns (recency penalty)

## Script
```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork \
  python3 ~/.hermes/hermes-scripts/statecomp-compression-router.py --check latest
python3 ~/.hermes/hermes-scripts/statecomp-compression-router.py --stats
```

## Cron: every 4h (wave16-statecomp-compression-router)

## Lessons
- Premature compression = context amnesia on uncommitted decisions
- Externalization signals: exit 0, file written, verified, committed
- State file: cache/statecomp-router-state.json

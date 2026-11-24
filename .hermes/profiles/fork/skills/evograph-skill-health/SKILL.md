---
name: evograph-skill-health
description: "Use when auditing skills. EvoGraph health tracker."
tags: [skills, health, wave16]
---

# EvoGraph Skill Health Monitor

Based on arXiv:2606.04917. Failure-aware editable skill health graph.

## Thresholds
- yield < 0.35: low-yield
- 3 consecutive yields < 0.35: failing (needs_review=True)
- yield >= 0.60: healthy

## Script
```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork \
  python3 ~/.hermes/hermes-scripts/evograph-skill-editor.py --build
python3 ~/.hermes/hermes-scripts/evograph-skill-editor.py --report
python3 ~/.hermes/hermes-scripts/evograph-skill-editor.py --query skill-name
```

## Cron: daily 2am (wave16-evograph-skill-health)

## Lessons
- Reads from cache/skill-yield-state.json (skill-yield-tracker output)
- If skill-yield-state.json empty, seed by running skill-yield-tracker first
- Graph: cache/evograph-insight-graph.json

## Hamming Audit Duplicate Pattern
The routing-hamming-audit cron flags skill pairs with Jaccard distance < threshold (default 0.3).
HIGH severity (distance 0.0) means the two skills are token-identical — usually a timestamped backup
copy left alongside the original (e.g. `my-skill` and `my-skill-20261116065017`).

When HIGH pairs appear: delete the timestamped copy via `skill_manage(action='delete', name='...-YYYYMMDDHHMMSS')`. The
timestamped copy is always the stale one — the original was updated after the backup was made.
MED severity (distance 0.27–0.3) often means two legitimately related skills (e.g. vol1/vol2 of the same textbook); review before acting.

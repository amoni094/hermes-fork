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

---
name: cross-fit-recall-bias
description: >
  Use when scoring skill recall without selection bias. Applies cross-fitting to separate
  the data used for skill selection from the data used for outcome scoring. Required to close
  the calibration log GATE GAP: ensures calibration-log.jsonl is wired to selection events.
triggers:
  - scoring skill recall quality
  - calibrating skill selection
  - calibration-log.jsonl not wired
  - detecting selection bias in skill routing metrics
  - closing GATE GAP in calibration
category: software-development
---

# Cross-Fit Recall Bias Prevention

## Problem

If you score a skill on the same data used to select it, you introduce selection bias:
skills that happened to be called on "easy" turns look better than they are. This is the
**Goodhart's Law** failure mode for skill routing: optimizing the metric destroys its validity.

## Solution: Cross-Fitting

Cross-fitting (Chernozhukov et al., 2018 "Double/Debiased Machine Learning") separates:
1. **Selection fold**: data where skill was selected → used to improve routing
2. **Scoring fold**: data where skill was NOT selected but was applicable → unbiased performance

## Hermes Application: calibration-log.jsonl GATE GAP

The GATE GAP (closed 2026-09-28): `calibration-log.jsonl` records every skill selection event.
This file must be written **before** the skill is evaluated (no look-ahead bias).

### Wiring requirement

In the skill-router decision path, BEFORE calling the skill:
```python
# Write selection event to calibration log (no outcome yet)
calib_entry = {
    "ts": time.time(),
    "session": session_id,
    "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
    "skill_selected": skill_name,
    "score_at_selection": selection_score,
    "fold": "selection",  # vs "scoring" for cross-fit evaluation
}
append_to_calib_log(calib_entry)
```

After the skill executes and outcome is observed:
```python
calib_entry["outcome"] = "success" | "failure" | "partial"
calib_entry["fold"] = "outcome"
append_to_calib_log(calib_entry)
```

### Cross-fit scoring

Every N sessions, split calibration log into selection/scoring folds:
```python
def cross_fit_score(log_entries: list[dict], skill_name: str) -> float:
    # Selection fold: entries where skill was selected
    sel_fold = [e for e in log_entries if e["skill_selected"] == skill_name and e["fold"] == "outcome"]
    # Scoring fold: entries from OTHER skills where THIS skill was also applicable
    # (requires storing top-k alternatives at selection time)
    score_fold = [e for e in log_entries if skill_name in e.get("alternatives", []) and e["fold"] == "outcome"]
    
    if not sel_fold or not score_fold:
        return 0.5  # insufficient data
    
    sel_rate = sum(1 for e in sel_fold if e["outcome"] == "success") / len(sel_fold)
    score_rate = sum(1 for e in score_fold if e["outcome"] == "success") / len(score_fold)
    
    # Debiased estimate: average of both folds
    return (sel_rate + score_rate) / 2
```

## GATE GAP Status

CLOSED 2026-09-28: `calibration-log.jsonl` wiring added to skill-router-index.py
feedback path (`--feedback` flag). Selection events written before outcome observed.

## References

- Chernozhukov et al. (2018): Double/Debiased Machine Learning for Treatment Effects
- GATE GAP memory note: calibration-log.jsonl wired (closed wiring sprint 2)
- skill-router-index.py: feedback flag implementation

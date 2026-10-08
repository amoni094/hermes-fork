---
name: rate-distortion-context-budget
description: >
  Use when allocating context prune budget via rate-distortion principles. Treats context
  compression as a rate-distortion problem: find the minimum token budget that preserves
  maximum task-relevant information. Applies to lambda-tuner and pre_compress hook.
triggers:
  - context window approaching limit
  - tuning lambda value for compression
  - deciding which context segments to prune
  - rate-distortion tradeoff in context management
  - token budget allocation
category: software-development
---

# Rate-Distortion Context Budget

## Theory

Rate-Distortion theory (Shannon, 1948; Cover & Thomas, 1991) provides the optimal tradeoff
between representation size (rate = tokens) and reconstruction quality (distortion = task
performance loss). For context management:

- **Rate**: tokens consumed by context
- **Distortion**: degradation in task performance when context is compressed
- **Optimal operating point**: the knee of the R-D curve (steepest slope)

The lambda parameter controls the operating point: `L(lambda) = distortion + lambda * rate`.
Minimizing L over compressions gives the Lagrangian optimal at rate `R(lambda)`.

## Key Insight for Hermes

The lambda-tuner plugin implements this by tracking:
1. Session complexity score (predicts distortion from compression)
2. Current context token count (rate)
3. Model performance signals (task completion quality)

The R-D curve's knee point (where marginal distortion per saved token is highest) determines
the target compression ratio.

## Implementation Guide

### Step 1: Estimate R-D curve knee

```python
def rd_knee(context_segments: list[dict]) -> float:
    """
    Returns target keep-ratio (0..1) at the R-D knee.
    Segments should have 'tokens' and 'importance' fields.
    Importance: 1=task-critical, 0.5=background, 0=noise
    """
    # Sort by importance/tokens ratio (marginal value per token)
    sorted_segs = sorted(context_segments,
                         key=lambda s: -s.get('importance', 0) / max(s.get('tokens', 1), 1))
    total_tokens = sum(s.get('tokens', 0) for s in context_segments)
    
    # Walk from high-value to low-value, find knee using second derivative
    running = 0
    prev_slope = None
    for i, seg in enumerate(sorted_segs):
        running += seg.get('tokens', 0)
        keep_ratio = running / total_tokens
        importance = seg.get('importance', 0)
        slope = importance  # marginal value of next segment
        if prev_slope and slope < prev_slope * 0.3:  # 70% slope drop = knee
            return keep_ratio
        prev_slope = slope
    return 0.7  # default: keep 70%
```

### Step 2: Wire to lambda-tuner

In `plugins/context_engine/lambda_tuner_plugin.py`, `pre_compress` hook:
```python
target_keep = rd_knee(context_segments)
compression_ratio = 1.0 - target_keep
```

### Step 3: Track calibration

Write to `~/.hermes/cache/rd-calibration-log.jsonl`:
```json
{"ts": 1234567, "lambda": 0.7, "keep_ratio": 0.65, "rd_knee": 0.62, "complexity": 0.8}
```

## Pitfalls

- Do NOT compress below 30% keep-ratio (hard floor) regardless of RD curve
- Importance scores should come from the attention weights or task relevance classifier,
  NOT from heuristics like "recent = important"
- The knee is session-specific: recompute per session, do not cache across sessions
- R-D knee tracking requires at least 5 data points; fall back to lambda=default until then

## References

- Shannon (1948): A Mathematical Theory of Communication
- Cover & Thomas (1991): Elements of Information Theory (Chapter 10: Rate Distortion Theory)
- hermes-lambda-tuner skill: lambda-tuner plugin documentation
- rate-distortion-context-budget: this skill

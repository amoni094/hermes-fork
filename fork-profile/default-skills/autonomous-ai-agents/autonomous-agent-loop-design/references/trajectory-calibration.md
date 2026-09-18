# Trajectory-level calibration (HTC / AUQ)

Load when implementing Brier/uncertainty scoring in an autonomous loop.
If the model does not emit confidence, use the **manual shortcut** in SKILL.md — do not invent scores.

## HTC: TrajectoryCalibrator (arXiv 2601.15778)

Trajectory Brier ≠ sum of per-turn Brier. Weight earlier steps more (they cascade).

```python
from statistics import mean, stdev

class TrajectoryCalibrator:
    def __init__(self):
        self.trajectory = []  # list of {confidence, outcome, tool_call}

    def record(self, confidence: float, outcome: bool, tool: str):
        self.trajectory.append({
            'confidence': confidence,
            'outcome': int(outcome),
            'tool': tool
        })

    def trajectory_brier(self) -> float:
        if len(self.trajectory) < 2:
            return 0.0
        total, weight_sum = 0.0, 0.0
        n = len(self.trajectory)
        for i, step in enumerate(self.trajectory):
            w = (n - i) / n
            bs = (step['confidence'] - step['outcome']) ** 2
            total += w * bs
            weight_sum += w
        return total / weight_sum

    def micro_stability(self) -> float:
        if len(self.trajectory) < 3:
            return 1.0
        confs = [s['confidence'] for s in self.trajectory]
        return 1.0 - min(stdev(confs), 1.0)

    def should_pause_and_reflect(self) -> bool:
        bs = self.trajectory_brier()
        ms = self.micro_stability()
        return bs > 0.25 or ms < 0.7
```

## AUQ: dual-process uncertainty (arXiv 2601.15703)

- System 1 (UAM): propagate verbalized confidence with each fact.
- System 2 (UAR): reflect only when confidence drops below threshold.

```python
def uaq_gate(confidence: float, fact: str, threshold: float = 0.6) -> str:
    if confidence >= threshold:
        return fact
    corroboration = search_memory_facts(fact, max_facts=3)
    if len(corroboration) >= 2:
        return f"{fact} [CORROBORATED:{min(confidence+0.2, 1.0):.2f}]"
    return f"{fact} [UNCERTAIN:{confidence:.2f}]"
```

OpenFang per-prediction Brier shortcut remains in SKILL.md.

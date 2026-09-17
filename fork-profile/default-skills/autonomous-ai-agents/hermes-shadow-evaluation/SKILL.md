---
name: hermes-shadow-evaluation
description: Use when testing a feature safely behind a shadow flag.
tags: [shadow, feature-flags, telemetry, evaluation]
related_skills: [hermes-improvement-governance, adaptive-agent-reasoning, hermes-observability-and-task-ledger]
---

# Hermes Shadow Evaluation

Pattern for safely testing new Hermes features. Ported from Denuto (src/pipeline/shadow_telemetry.py).

Every new feature ships behind a flag pair:
  `<feature>: false` (live path off)
  `shadow_<feature>: false` (shadow mode off)

When shadow mode is ON: the feature runs in parallel with the live path,
results are emitted as JSONL telemetry events, live path is untouched.
A gate script reads the JSONL and decides if the feature has earned promotion.

## Script

`~/.hermes/scripts/shadow_telemetry.py` (stdlib only, no external deps)

## Usage

```python
from shadow_telemetry import is_shadow_enabled, record_shadow_event, file_sink, ShadowGate

# Check if shadow mode is on for a feature
if is_shadow_enabled(config, 'consistency_scoring'):
    shadow_result = run_consistency_scorer(finding, context)
    record_shadow_event(
        flag='consistency_scoring',
        live_result=live_analysis,
        shadow_result=shadow_result,
        session_id=session_id,
        sink=file_sink('/tmp/shadow_consistency.jsonl'),
    )

# Gate evaluation:
gate = ShadowGate('consistency_scoring', min_events=10, max_error_rate=0.1)
result = gate.evaluate('/tmp/shadow_consistency.jsonl')
# result['decision'] = 'promote' | 'reject_high_error_rate' | 'insufficient_data'
```

## Design Constraints (MUST follow)

- record() NEVER raises. Shadow failures must not contaminate live path.
- Stdlib only in shadow_telemetry.py. No boto3, no external deps.
- Shadow path runs in parallel - does NOT replace live path result.
- One JSONL event per call per flag.
- Event schema version-pinned (SHADOW_EVENT_SCHEMA_VERSION = 1).

## Promotion Lifecycle

1. Ship with `shadow_<feature>: false` in config
2. Enable shadow mode for canary sessions: `shadow_<feature>: true`
3. Let telemetry accumulate (min_events=10 before gate will decide)
4. Run gate script: `python -m shadow_telemetry --input ... --flag ...`
5. decision=promote: flip `<feature>: true`, remove shadow flag
6. decision=reject: investigate JSONL, fix, restart cycle

## Hermes Config Integration

Add to config.yaml:
```yaml
agent:
  shadow_consistency_scoring: false
  shadow_coverage_audit: false
  shadow_loop_detection: false
```

GATE GAP (Tier-2): Proposed cron job to auto-run gate script nightly and report.

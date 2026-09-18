---
name: hermes-improvement-governance
description: Use when proposing a Hermes self-improvement. Risk gating.
tags: [governance, self-improvement, hitl, risk]
related_skills: [hermes-shadow-evaluation, hermes-observability-and-task-ledger, self-improve-agent]
---

# Hermes Improvement Governance

Structured lifecycle for Hermes self-improvement proposals. Ported from Denuto (src/improvement/governance.py).

## Script

`~/.hermes/scripts/improvement_governance.py`

## Risk Levels and Auto-routing

```
LOW:    skill_update, skill_create, memory_update  -> auto-approved
MEDIUM: script_add, script_modify, cron_add        -> 1 reviewer
HIGH:   config_change, plugin_update, cron_modify  -> 2 senior approvals + cooldown
```

Targets always HIGH (regardless of change_type):
  config.yaml, hermes-agent, plugin_stream_hooks, conversation_compression,
  api_request_hooks, gateway, compression

## Lifecycle States

pending_review -> under_eval -> approved -> deployed -> rolled_back

## Usage

```python
from improvement_governance import ImprovementGovernor, ImprovementPolicy, classify_change_risk

policy = ImprovementPolicy(
    low_risk_auto_approve=True,
    medium_risk_reviewers=1,
    high_risk_reviewers=2,
    high_risk_requires_senior=True,
    max_proposals_per_day=10,
    cooldown_after_rollback_hours=24,
)
gov = ImprovementGovernor(policy=policy)

# LOW risk - auto approved immediately
prop = gov.create_proposal('skill_update', 'agent-runtime-loop-patterns', 'Add AIMD pattern')
assert prop.status.value == 'approved'
gov.deploy(prop.proposal_id)

# HIGH risk - pending until senior approves
prop2 = gov.create_proposal('config_change', 'config.yaml', 'Add shadow flags')
gov.approve(prop2.proposal_id, approver='senior:alexey')
gov.approve(prop2.proposal_id, approver='senior:alexey')  # idempotent

# Rollback + cooldown
gov.rollback(prop.proposal_id, reason='caused session stalls')
# 24h cooldown now active
```

## classify_change_risk()

Pure function: classify_change_risk(change_type, target) -> ImprovementRiskLevel

Call before any change to get the risk level before creating a proposal.

## Rate Limits

- max_proposals_per_day=10 (configurable per ImprovementPolicy)
- 24h cooldown after any rollback
- Thread-safe: uses threading.Lock internally

GATE GAP (Tier-2): Proposed integration point before skill_manage and config writes.

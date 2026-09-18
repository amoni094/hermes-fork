---
name: policy-routing-update
description: "Use when updating a routing map based on eval evidence."
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
  - updating a routing map based on eval results
  - eval shows domain-specific policy loses on its own domain
  - compression profile routing change
  - policy default changed based on benchmark evidence
related_skills:
  - evaluation-driven-development
  - test-driven-development
---

# Policy Routing Update

When eval evidence shows a routing default should change, follow this sequence exactly.
Skipping the grep step causes silent test failures on unrelated shards.

## When to use

- A routing map (`_FORK_PROFILE`, `_POLICY_MAP`, `_MODEL_TIER`) needs a default changed
- Eval evidence (N≥30, domain-matched) shows a different default wins on most domains
- A compression profile, model tier, or policy label is being globally updated

## Sequence

### 1. Document the evidence first

Before touching code, record in a comment in the routing map file:
- Which metric drove the change (combined score, recall by domain)
- Which old value is being replaced and why  
- Which new value was validated and on what lineage / N

```python
# v4 eval (N=30, domain-matched): fork_mixed wins 2/3 domains.
# fork_research/fork_code over-prune the other content type and lose on home domain.
_FORK_PROFILE = {
    "research": "fork_mixed",  # was: fork_research
    "code":     "fork_mixed",  # was: fork_code
    "mixed":    "fork_mixed",
}
```

### 2. Preserve old values (rename, don't delete)

```python
_FORK_PROFILE_DOMAIN_SPECIFIC = {
    "research": "fork_research",
    "code": "fork_code",
    "mixed": "fork_mixed",
}
```

Keeps domain-specific routing available via explicit call without affecting defaults.

### 3. Grep tests for old expected values BEFORE running

```bash
grep -rn 'OLD_VALUE' tests/
```

Common locations:
- `assert hint["compression_profile"] == "fork_research"`
- `assert result["policy"] == "fork_code"`
- Direct string literals in setUp / fixture data

Fix ALL occurrences before running any tests. A missed assertion fails silently on
a shard you didn't run, then surfaces in CI after push.

Update with a context comment so the change is self-documenting:
```python
patch(
    path="tests/test_routing.py",
    old_string='assert hint["compression_profile"] == "fork_research"',
    new_string='assert hint["compression_profile"] == "fork_mixed"  # v4: all types -> fork_mixed',
)
```

Use `replace_all=True` when the old value appears multiple times in one file.

### 4. Run targeted tests first, then full suite

```bash
PYTHONPATH=/path/to/repo pytest tests/test_session_classifier.py tests/test_routing_harmonizer.py -q --tb=short
```

Only expand to full suite after targeted tests pass.

### 5. Commit with evidence in the message

```
fix(<component>): route all session types to fork_mixed (v4 eval finding)

fork_mixed wins or ties on all three content domains based on N=30 domain-matched
lineage eval. Domain-specific policies over-prune the other content type.

Legacy mappings preserved in _FORK_PROFILE_DOMAIN_SPECIFIC for explicit override.
Tests updated to expect fork_mixed from get_routing_hint().
```

## Pitfalls

- **Grep before run**: always grep the test tree for the old value string before
  running tests. Hand-rolled mocks hardcode old expected values and fail silently
  on shards you didn't run.

- **Only update compression_profile, not all hint fields**: `reasoning_effort_bias`,
  `model_tier_hint`, and `session_type` still vary by session type. Confirm those
  fields still return per-type values in tests after the routing map update.

- **Eval must be domain-matched**: require confirmed domain-matched lineages (R/C ratio
  check on cap window) before treating a policy ranking as evidence. See
  `references/compaction-eval-methodology.md` in dispatching-parallel-agents.

- **N≥30 minimum**: N=15 has CI ~±14pp; differences below 15pp are noise. Require
  N≥30 (10/10/10 tiered) before a combined-score delta is treated as routing evidence.

- **Preserve domain-specific mappings**: a policy winning 2/3 domains is sufficient
  for a default change, but the per-domain mappings must stay accessible for callers
  that explicitly need the domain-specific profile.

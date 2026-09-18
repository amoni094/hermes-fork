# Adoption Notes

These workflow skills were added as a Hermes-native adaptation of the most useful ideas from `obra/superpowers`, not as a verbatim port.

## Why this set exists

The goal is to improve default development behavior in Hermes without forcing heavy process on every task.

Preserved ideas:
- scale process to task complexity and risk
- use isolation when repo state or scope makes it worthwhile
- require independent review when changes matter
- do not claim completion from stale or second-hand evidence
- use delegation when it reduces context overload or improves separation of roles

Deliberately not copied:
- one-size-fits-all mandatory ceremony for trivial tasks
- rigid universal gates regardless of risk
- frontend-specific plugin assumptions that do not map cleanly to Hermes

## Intended loading order

For most coding work, load skills in this order:

1. `workflow-map`
2. `complexity-gated-planning`
3. `isolated-workspace-preflight` if repo risk or scope suggests it
4. `test-driven-development` for behavior changes
5. `risk-based-review`
6. `requesting-code-review`
7. `verification-before-completion`

For delegated multi-agent work, extend the sequence with:
- `subagent-driven-development`
- `hermes-role-pipelines` when explicit specialist roles help
- `hermes-acp-routing` only when ACP transport is actually verified

## Routing guidance

### Small low-risk task
Prefer lightweight planning, then direct execution, then final verification.

### Normal feature or bug fix
Use TDD where appropriate, then review, then final verification.

### Risky or cross-cutting change
Consider isolated workspace first, then stronger review depth, then explicit completion verification.

### Delegated work
Use compact context packets, keep worker scopes narrow, and do not trust delegated success claims without direct verification.

## Operating philosophy

This set is meant to make Hermes more reliable, not more ceremonial.

If a task is simple, the workflow should stay light.
If a task is risky, user-facing, security-sensitive, cross-cutting, or delegated, the workflow should become stricter.

## Maintenance note

If future sessions discover better thresholds, missing handoffs, or recurring failure modes, update the linked skills rather than growing this note into a process manual.

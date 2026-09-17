## Aug 2026: FAMA — Forgetting-Aware Memory Accuracy (ACL 2026.findings-acl.1337)

Source: https://aclanthology.org/2026.findings-acl.1337/
Key finding: memory agents offer only marginal improvement over no-memory baselines on long tasks
because they frequently retrieve STALE or INVALIDATED memories and use them as if still true.
"Forgetting-Aware Memory Accuracy" (FAMA) penalizes this pattern explicitly.

Hermes staleness check protocol:
- Before using a recalled Hindsight/memory fact, classify it: preference (stable) / config value
  (may change) / event (stable but may be superseded by later event)
- When a change SUPERSEDES an existing memory/skill section, add an explicit invalidation note:
  "Invalidated by: <date> <what changed>" — so future recall picks up the invalidation
- memory tool: replace stale entries atomically (remove + add in one batch op); never just add
- RUMBA + FAMA together: after ~30 turns, do a staleness audit of loaded memories before acting
  on them — use hindsight_reflect("is X still accurate?") to cross-check volatile facts


*Support files (continued) — see references/support-files-extended.md.*

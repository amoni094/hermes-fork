## Session-Settled Decisions: Provenance Annotation (Compound Engineering, 2026)

When a user makes a decision explicitly during a session (chooses approach A over B,
sets a constraint, confirms a direction), annotate it with a provenance class so that
downstream steps in the same session don't re-ask or silently override it.

### Settlement taxonomy

| Class | Meaning | Downstream handling |
|-------|---------|---------------------|
| `session-settled` | User examined and chose this in the current conversation | Never re-ask; augment only, never reverse |
| `directive` | Merely asserted (by agent or context, not user-examined) | May reconsider if new information arrives |
| `unlabeled` | Agent-inferred, not explicitly confirmed | Surface for user confirmation if high-stakes |

### Settlement test

Before re-asking a question or revisiting a decision already in context:

1. Was this decision explicitly chosen by the user in this session? → `session-settled`, skip
2. Was it merely stated (in a brief, plan, or by the agent)? → `directive`, may revisit with evidence
3. Is it inferred/assumed? → `unlabeled`, confirm before acting on it if the stakes are high

### How to annotate

When recording a user's confirmed decision in Graphiti or Hindsight, tag it:

```python
hindsight_retain(
    content="User confirmed: implement auth with JWT, not sessions",
    context="session-settled decision",
    tags=["session-settled", "auth-architecture"]
)
```

In skill prompts: when passing a settled decision to a subagent, include:
```
SETTLED (user-confirmed): Use JWT for auth. Do not re-evaluate this.
```

### Key rule: settled decisions are not yours to improve

A `session-settled` decision must not be reopened unless it is invalidating-grade
unworkable (e.g. the chosen approach is technically impossible in the current stack).
If new information suggests a different approach might be better, note it but do not
act on it without explicit user instruction. "Session-settled" means the user's
examination is complete — it is not an invitation to re-examine on their behalf.

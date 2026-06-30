# Claude routing matrix for Hermes delegation

Use this pattern when deciding which Claude model should sit at the orchestrator versus the workers.

Default rule
- Orchestrator: strongest reasoning Claude available, usually Opus-class
- Workers/sub-agents: balanced Claude, usually Sonnet-class
- Tiny leaf helpers: Haiku-class only when the subtask is narrow, mechanical, or cheap to retry

Why this split works
- The orchestrator makes the high-leverage decisions: decomposition, scope control, conflict resolution, and final synthesis.
- Workers do the token-heavy reading, editing, and localized debugging, so cost and throughput matter more there.
- A weak orchestrator tends to produce bad task splits, which is usually more expensive than paying for a stronger planner.

Hermes config example from this session
```bash
hermes config set model.default claude-opus-4.1
hermes config set delegation.provider anthropic
hermes config set delegation.model claude-sonnet-4.5
```

Escalation rules
- If a worker hits ambiguity, missing context, or cross-file reasoning, re-route that subtask to a stronger model.
- Keep worker prompts narrow and self-contained; do not hand the orchestrator's whole reasoning chain to every child.
- Use Haiku only for trivial extraction, summary, or mechanical rewrite tasks where mistakes are cheap.

Operational note
- Config changes usually need a fresh session or process restart before they are reflected in live routing.
- If model names change in the provider catalog, keep the class split and substitute the newest Opus/Sonnet equivalents.

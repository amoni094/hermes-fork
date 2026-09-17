# Extended runtime patterns (extracted from SKILL.md)

Load this file when you need paper-level detail on salience defense, zero-replay traces,
SHE/CommitKV/ATP-Bench/PSE/EASy/DreamGuard, Agentao host contracts, Python script pitfalls,
cold-start preambles, Sweep 31 distribution-shift, or Evo-Harness compilation.

Core loop procedures stay in SKILL.md.

## Salience Induction Attack — RAG Agent Defense (arXiv:2607.17535)

Truthfulness and instruction-filtering alone do NOT protect RAG-augmented agents.
A salience-channel attack redirects reasoning via fact position, emphasis, framing,
and semantic proximity — without injected instructions, using only true claims.

Under 30% edit budget: 83.3% ASR on ReAct, Reflexion, and tool-calling agents.
Salience Normalization: 83.3% → 15.3% ASR.

Operators: positional prominence, repetition density, hedge removal, contrast framing,
semantic anchoring, adjacency exploitation.

**Hermes pattern:** before injecting retrieved skill/memory chunks, sort by original
embedding score not source-doc position; flag chunks that repeatedly emphasize one
conclusion; in `web_extract` + skill routing, weight source-position diversity; treat
earliest-match bias in `session_search` as a salience vector.

Cross-ref: `agent-memory-consolidation` retrieval extras (same defense on memory writes).

## Zero-Replay Trace Debugging — Event KG (arXiv:2606.14805)

Compile traces into an event KG over routing, memory, tool-use, uncertainty, latent evidence.
Gradient-boosted predictor: Branch Recall@5 0.73 → 0.93.

Event schema (same as SKILL.md monitoring):
```
event_type: routing | memory_write | memory_read | tool_success | tool_failure | reflection | compaction
session_id: <str>
turn: <int>
entity: <tool_name | skill_name | memory_key>
outcome: success | failure | partial
surprise_score: float   # abs(expected_tokens - actual_tokens) / expected_tokens
causal_predecessor: <event_id>
```

When a trajectory fails, query Graphiti for high-centrality nodes in the failure neighbourhood
instead of re-running.

## SHE: 4-Artifact Harness Evolution (arXiv:2608.09885)

Artifacts: System Prompt, Rule Bank, Safety Memory, Tool Policy. Localize a failure to one
artifact and refine only that artifact. 3.1× ASR reduction vs static harness.

Hermes map: system_prompt in config.yaml; skills-as-markdown; Hindsight tagged
`memory_type: safety`; MCP / computer_use allow-deny. Skill-file gaps → patch that skill
(human-gated via `self-improve-agent`), not the system prompt.

## CommitKV: Lifecycle-Aware KV Cache Compression (arXiv:2608.07855)

GPU KV-cache paper. Transferable principle: compaction boundaries should be **event-aligned
to tool-call commits**, not turn-count-aligned. Tool-result payloads are retirement candidates
once the reasoning step that used them is complete and verified.

Does not override Hermes compression knobs — it argues against a fixed every-N-turns rule.

## ATP-Bench: Multi-Step Tool Planning (arXiv:2603.29902)

Failure classes: over-fetching, wrong order, stale dependency.
Before 3+ tool calls: write the sequence with dependency arrows; flag steps whose input could
be stale by the time they run. https://arxiv.org/abs/2603.29902

## Persistent Semantic Entities (PSEs) (arXiv:2608.07952) — SECURITY

Implicit state persists across sessions via name binding (necessary and dominant; without it
contamination = 0%). Preference contamination does not decay.

Surfaces: Hindsight, Graphiti named entities from `web_extract`/subagents, skill files,
cron `context_from`.

Mitigations: context-isolated self-verify before Hindsight writes; tag `source_type:
external | internal | cron`; never let subagents `skill_manage` or write skills from
external content. Write-path detail: `agent-memory-consolidation`.

## EASy: Milestone-Plan-Act (arXiv:2608.04588)

Orchestrator: milestones → dependency-aware plan → parallel steps. Route each milestone to
the cheapest executor that meets capability needs (see `claude-routing-hierarchy`). Do not
commit the full execution graph upfront.

## DreamGuard: Risk-Aware World Model (arXiv:2608.05695)

Prefix-risk before execution. For long `computer_use` sequences, use `trajectory-risk-guardrail`
(recurrent trajectory-state summary, not independent per-step checks).

## Agentao host contract (arXiv:2608.13574)

5-layer map: host surface → host contract → runtime core → permission-mediated tools →
supporting subsystems. Skill permission declarations (`uses: [...]`) belong in
`hermes-skillspector-guard-maintenance`, not this skill.

## Python runtime pitfalls

Canonical: `references/python-runtime-pitfalls-aug2026.md`.

- Hyphenated `~/.hermes/scripts/*.py`: `importlib.util.spec_from_file_location` + `exec_module`.
- Extract functions for `exec()` tests via `ast.parse` + `lineno`/`end_lineno` (3.8+).
- 5-class retry (`retry-budget-guard.py`): TRANSIENT 5×/2s; RESOURCE 2×/30s; SEMANTIC 2×/1s;
  AUTH 1×/5s; FATAL 0. On load failure, call through — do not crash the caller.
- SQLite `ALTER TABLE ADD COLUMN`: catch `sqlite3.OperationalError` (no `IF NOT EXISTS` for columns).

## Cold-start preamble for cron/scheduled jobs

Canonical: `references/agent-improvements-2026-08.md`. Inject:
```
CONTEXT: task=<name>, schedule=<interval>, prior_run=<ISO date or "none">
CONSTRAINTS: <hard limits>
VERIFY: confirm tools accessible before first substantive action
```
Also see `hermes-cron-and-agents`.

## Tool-use policy under distribution shift (arXiv:2609.00467)

18–31% drop when tool availability or schema changes without re-calibration.
Shifts: tool unavailable; schema change; new tool for an existing class; latency past SLA.

On a tool's first error in a session, check whether the schema changed vs prior calls.
When adding a tool mid-session, state its capabilities explicitly — agents do not discover
new tools reliably. Alert if ≥2 tools degrade together.

## Context-to-harness compilation (Evo-Harness, arXiv:2608.15071)

After a task/subagent loop: harness-update phase is distinct from memory consolidation.
Strip task-specific artifacts; distill cross-domain lessons; update a skill only at 3+
similar tasks. Frozen agent + evolving harness. Human-gated via `self-improve-agent`.
Do not patch agent config/core from loop output.

## Outer-loop governance (pointer)

`should_continue` / `record_feedback` (≤140 tokens) / `fresh_context` and the 4 stop-condition
types live in `autonomous-agent-loop-design`. This skill owns the inner tool loop only.

## Enterprise grounding

Russian enterprise survey (CyberLeninka, HSE, 2026): full autonomy is rare; hybrid HITL
dominates. Validates fixed warning thresholds and `verify_on_stop`.
Russian academic review (RUDN, VAK, 2025): context drift and inter-agent protocol overhead
confirm the context-ceiling finding.

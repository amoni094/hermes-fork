---
name: hermes-observability-and-task-ledger
triggers:
  - need tracing, cost attribution, or task-ledger discipline for a multi-step agent run
  - want to audit what tools were called, in what order, and at what cost
  - debugging agent behavior — a run is slow, expensive, or wedged and you need observability
  - running multiple agents or durable background tasks that need a single control-plane view
description: "Use when you need tracing, cost attribution, task-ledger discipline, or event-driven knowledge sync."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, observability, task-ledger, tracing, cost, latency, task-brain]
    related_skills: [hermes-agent, hermes-operating-pattern, hermes-cron-and-agents, hermes-memory-capture-and-bridge]
related_skills:
  - verification-before-completion
  - plan
  - hermes-agent
  - hermes-operating-pattern
  - hermes-cron-and-agents
  - hermes-memory-capture-and-bridge
---

# Hermes Observability and Task Ledger

## Overview

Use this skill when you need to know what agents are actually doing, how much they cost, or whether long-lived work is being tracked centrally.

The pattern is: measure first, use the task ledger as the source of truth for active work, and prefer event-driven sync over polling when files can notify you directly.

## When to Use

- You cannot easily tell why a run is slow, expensive, or wedged.
- You are running multiple agents or durable background tasks.
- You need a single control-plane view of long-lived work.
- You want knowledge updates to happen when files change rather than on a polling timer.

## Operating Rules

- Instrument before optimizing.
- Track latency, token usage, failures, and tool noise before changing the workflow.
- Use the task ledger for scheduled jobs, sub-agent spawns, and other long-lived work.
- When using Hermes shell hooks, `subagent_stop` is the low-friction event for appending child-run summaries into a local task-ledger JSONL stream.
- Prefer `hermes hooks list` and `hermes hooks doctor` to verify hook registration before assuming observability is live.
- Keep separate lanes for raw evidence, distilled conclusions, and action items.

## Observability First

Use native diagnostics first when available.

Look for:

- startup latency
- tool-surface noise
- stalled or wedged tasks
- cost hotspots
- failure patterns

Only add heavier tracing or dashboards if the native telemetry is not enough for the decision you are trying to make.

### Structured tracing when native telemetry is insufficient (Aug 2026)

**OpenInference 5-point instrumentation** — preferred over OTEL GenAI for richer LLM metadata:

```bash
pip install openinference-instrumentation
```

Instrument exactly 5 areas in order:
1. Every LLM call: prompts, completions, token counts, cost
2. All tool invocations: inputs, outputs, latency
3. RAG/retrieval calls: which docs returned and query used
4. User/session metadata: session_id, user, task type
5. Key decision points: custom spans at branch/escalation points

Exposes Prometheus `/metrics`; integrates with Langfuse, Arize, Phoenix.
Source: https://github.com/Arize-ai/openinference

**TelemetrySuffBench finding (arXiv:2608.07899):** Coarse / OpenTelemetry-compatible / OpenInference-compatible views keep detection F1 at 99.5–100% while origin-step Top-1 accuracy falls to ≤0.5%. Removing decision content drops origin-step accuracy to zero. Detection ≠ localization. Root-cause diagnosis needs **decision-to-provenance links** (prompts/completions + hashed tool I/O on spans) and abstention when evidence is ambiguous — not tool-name+timestamp logs alone. Store input/output hashes on every `execute_code` / `terminal` span for replay.

### Tamper-evident tool call audit (arXiv:2609.01931, Agent Flight Recorder) ★ HIGH

For high-stakes agent actions, maintain a tamper-evident audit trail by hashing each (tool_call + result) pair and chaining into an append-only log (paper also describes on-chain epoch-root anchoring — out of scope for this Hermes host).

Do **not** treat `l1-tracegrant.py` as this. TraceGrant logs *memory-pipeline namespace grants* (`decision_hash` of caller/source_type/allowed_ns) into `lifecycle.db`; `tracegrant_verify()` checks those grant hashes, not tool I/O.

Hermes approximation (principle only — do not patch `l1-tracegrant.py` from this skill):
1. Hash `(tool_name + input_hash + output_hash)` on high-stakes / irreversible tool spans (same hashes TelemetrySuffBench wants on diagnostic spans).
2. Append to a session-local hash chain. Flight Recorder is the integrity chain over those hashes; TelemetrySuffBench hashing is the span-level diagnostic.
3. On a failure, replay the chained tool sequence to find the first diverging step.

### Audit-Runtime Integrity (arXiv:2605.05274)

Skill **admission** (tools listed in skill frontmatter / `tools_allowed` / `ssl_structural.tools_used`) and skill **execution** (tools actually called while the skill is loaded) must be audited for hash/set mismatch.

If a skill calls a tool **not** in its declared tools list, flag as an **audit-runtime gap**.

- Enforcement: `tool-auth-gate` (classify / gate undeclared tools).
- Logging: Flight Recorder hash chain above — include `(skill_name, declared_tools_hash, called_tool)` on the span so the gap is replayable.

## Event-Driven Sync

If a knowledge graph or retrieval layer needs fresh file state, prefer filesystem events over cron polling.

Good pattern:

- file change
- short debounce
- hash / dedupe check
- upload or queue
- retry with backoff if the downstream service is down

Rules:

- do not poll if the OS can notify you directly
- keep the watcher self-healing and quiet when idle
- queue offline changes instead of losing them
- keep logs rotating and bounded

## Task Ledger Rules

- Treat the ledger as the control-plane view of durable work.
- Scheduled jobs and sub-agent runs should be visible there.
- Do not rely on chat transcripts as the only record of long-lived work.
- Keep follow-up tasks linked to the originating work when possible.

## Common Pitfalls

1. Optimizing before measuring.
2. Using cron for a file-change problem.
3. Grepping sessions instead of checking the task ledger.
4. Running too much observability before the native telemetry has been checked.

## Verification Checklist

- [ ] Costs, latency, failures, or tool noise were measured or inspected first.
- [ ] Long-lived work is tracked in the task ledger.
- [ ] File-change sync uses events, not unnecessary polling.
- [ ] Offline / failure behavior is defined.
- [ ] The output is still easy to reason about without a dashboard.

## Async Per-Turn Token Usage Logging (estudy observability pipeline) — S9

Log prompt and completion token usage per turn to ~/.hermes/logs/token-usage.jsonl without blocking the turn loop.

Pattern: use a daemon thread (threading.Thread(daemon=True)) so the log write does not add latency to the turn.

Schema (one JSON object per line, append-only):
  {"ts": "ISO8601", "session_id": "...", "turn_id": "...", "model": "...", "prompt_tokens": N, "completion_tokens": N, "tool_calls_count": N, "run_id": "..."}

Rotation: rotate when file size > 10MB (rename to token-usage.jsonl.1, open fresh token-usage.jsonl).

This complements run-header.py content-addressed run IDs (session/script-level granularity) with per-turn granularity. Enables: (a) identifying expensive individual turns, (b) detecting token-usage spikes from runaway tool loops, (c) cost attribution per task type.

Wire: in agent/turn_usage.py or equivalent, after the LLM call returns usage stats, spawn a daemon thread that appends the record. The main turn loop continues immediately.

Data processing inequality (Cover-Thomas): logging token counts does not distort the session; no information about the session is lost by the append-only log. The observation is lossless.

<!-- why: run-header.py tracks per-run totals but not per-turn breakdown; turn-level data identifies S10 amplification patterns before they become expensive -->


## UPA Policy Kernel — Planned Cross-Tier Governance (C1, estudy multi-tenant LLM platform)

The UPA (Universal Policy Architecture) pattern from estudy's multi-tenant LLM platform design proposes tiered policy enforcement across model/plugin/tool/skill surfaces.

PLANNED: When Hermes fork implements policy_kernel config reading, the desired behavior is:
  model: audit (log model selections for anomaly detection, don't block)
  plugin: warn (emit warnings for unusual plugin combinations, don't block)
  tool: enforce (hard-block tool combinations that violate the policy matrix)
  skill: audit (log skill loads, don't block)
  deny_cross_tier_escalation: true (a plugin cannot grant itself tool-level permissions)

NOT YET WIRED: policy_kernel is not currently read by any Hermes fork source. The config key
was removed to prevent false confidence. Track this as a future implementation:
  - Add policy_kernel loader in hermes_cli/config_loader.py
  - Add policy matrix check in tools/registry.py pre-dispatch
  - Add plugin permission check in plugins/plugin_loader.py at registration

Why it matters (estudy insight): multi-tenant LLM platforms routinely fail from cross-tier
escalation — a plugin that calls a tool that writes to a protected path, bypassing the
plugin-level deny. Tier-gating prevents this class of lateral privilege escalation.

<!-- why: documenting planned architecture prevents rediscovery; actual enforcement must wait until the config reading chain is implemented -->


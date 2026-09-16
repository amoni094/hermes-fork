---
name: hermes-memory-capture-and-bridge
triggers:
  - want automatic durable knowledge capture after a research or investigation session
  - bridging session findings to long-term memory surfaces (Graphiti, Hindsight, Obsidian) — QMD disabled
  - about to spawn a coding sub-agent and need to inject relevant memory context into it upfront
  - post-task memory consolidation before a session compacts or the context is lost
description: "Use when you want automatic durable knowledge capture after sessions and preflight memory injection before spawning coding agents."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, memory, capture, bridge, hooks, knowledge, agents]
    related_skills: [hermes-obsidian-sync, hermes-cron-and-agents, hermes-coding-review-loop, hermes-observability-and-task-ledger]
related_skills:
  - verification-before-completion
  - plan
  - hermes-obsidian-sync
  - hermes-cron-and-agents
  - hermes-coding-review-loop
  - hermes-observability-and-task-ledger
---

# Hermes Memory Capture and Bridge

## Overview

Use this skill to keep durable knowledge from disappearing when a session compacts or when a sub-agent starts blind.

The pattern has two parts:

- **Auto-capture**: after a session or before compaction, extract durable claims into inbox notes.
- **Memory bridge**: before spawning a coding agent, search the vault and write a compact context file the child can read immediately.

## When to Use

- You regularly lose useful findings after long sessions.
- You want durable claims to be captured without manual note-taking.
- You spawn coding agents that should not start from scratch.
- You want a repeatable preflight step that turns vault knowledge into working context.

## Operating Rules

- Treat raw transcripts as source material, not as durable memory.
- Capture only durable claims: decisions, fixes, configuration facts, lessons, and stable version info.
- Skip small talk and one-off facts that will not matter later.
- Prefer claim-named notes so filenames communicate the lesson directly.
- Keep curated summaries separate from raw session output.
- When spawning a coding agent, search the vault from several angles, dedupe the hits, and write a compact `CONTEXT.md` or equivalent in the workdir.
- Tell the child to treat that context as background, not unquestioned truth.

## Hook Pattern

**IMPORTANT (2026-08-30 audit): `hooks:` is NOT wired in the current Hermes runtime config.
The hook-based auto-capture described below is aspirational/manual-only until `hooks.on_session_end`
is added to `~/.hermes/config.yaml`. Treat this section as a design spec, not a live behavior.**

**Atomix non-atomic tool caveat (arXiv:2602.14849):** tool-return != settlement. hindsight_retain
after a crash may be partial or duplicated. Before retaining, check if the fact is already
in the bank (hindsight_recall spot-check). Apply verify-before-retry from trajectory-risk-guardrail.

Use Hermes shell hooks *when configured* for automatic behavior. Until then, run capture manually
at session end by calling `hindsight_retain` + `mcp__graphiti__add_triplet` for durable findings.

When hooks are configured: use `post_llm_call` for compact turn capture, `post_tool_call` for
vault-write event logging; keep each hook script fast and JSON-only.

Good triggers:

- new session start after the prior session ended
- reset / restart boundaries
- compact-before boundaries when the transcript is richest

The hook should:

1. Read the recent transcript.
2. Extract candidate durable claims.
3. Skip short or low-signal sessions.
4. Write the extracted notes into the inbox or vault staging area.

Prefer async, fire-and-forget capture so the capture step does not interrupt the session flow.

## Memory Bridge Pattern

Before spawning a coding agent:

1. Define the task in one sentence.
2. Search the vault from multiple angles.
3. Dedupe and rank the hits.
4. Write a compact context file into the workdir.
5. Include the specific constraints, prior decisions, and known failures.
6. Tell the child how to query memory on demand if it gets stuck.

## Obsidian Live-Sync Pattern

When the user wants ongoing chat-to-vault sync, keep the sync curated and rewrite-oriented rather than append-only.

Recommended shape:

1. Read recent sessions from the local session store.
2. Extract only durable or high-signal items: workflow changes, verified results, stable decisions, maintenance actions, and real follow-ups.
3. Rewrite one canonical vault note for the rolling summary instead of endlessly appending duplicate sections.
4. Mirror the current day into the daily note with a short `## Hermes Chat Sync` or equivalent section that links back to the canonical summary note.
5. If automation is wanted, schedule a local cron job that rewrites the canonical note and refreshes the daily-note mirror on a fixed cadence.
6. Verify by reading back the files that were written.

Rules:

- Do not dump raw transcripts into Obsidian.
- Prefer a stable summary note plus a lightweight daily-note mirror.
- Keep privacy notes explicit when summarizing local chat history.
- For recurring sync, prefer idempotent rewrites over append-only growth.

For the full canonical Obsidian sync workflow (rewrite policy, durable-item filter, daily-note rules, cron patterns), load `hermes-obsidian-sync`.
See `references/runtime-hooks.md` for the live Hermes shell-hook wiring pattern that turns this skill into runtime behavior.

## Good Outputs

- claim-named markdown notes
- a small context file for the child agent
- a short checklist of what is known / unknown
- separate raw-source and distilled-summary artifacts
- one canonical live-sync note plus a lightweight daily-note mirror when summarizing recent chats into Obsidian

## KG Entity Graphs Outperform Document Retrieval for Latent Relations (arXiv:2608.10679)

ENTLORE benchmark: 30.4% of implicit/latent cross-entity relations remain unanswered by RAG systems even with gold documents, vs. 12.6% for explicit queries. KG traversal dramatically outperforms vector search for relational queries.

Hermes implication: after each significant session, extract entity-relation triplets and store in Graphiti — not just episodic summaries. The session Hindsight memory handles episodic recall; Graphiti triplets handle cross-session relational queries ("what did project X decide about Y?").

Add to post-session capture step: after Hindsight write, call `mcp__graphiti__add_triplet` for any new entity relationships surfaced (person-project-decision triplets, tool-pattern-outcome triplets).

## Common Pitfalls

1. Saving raw transcripts as if they were knowledge.
2. Capturing every message instead of only durable claims.
3. Starting coding agents without a preflight memory search.
4. Writing a context file that is too large or too noisy to help.

## Verification Checklist

- [ ] Durable claims were separated from raw transcript material.
- [ ] Low-signal sessions were skipped.
- [ ] Notes are claim-named and easy to rediscover later.
- [ ] Coding-agent preflight context was written before the child started.
- [ ] The child was told how to query memory on demand.

## Runtime hook wiring (from references/runtime-hooks.md)

To turn this skill into live runtime behavior, wire shell hooks under `~/.hermes/agent-hooks/` and register in `config.yaml` under `hooks:`:

```yaml
hooks:
  pre_llm_call:
    - command: "~/.hermes/agent-hooks/inject-hermes-routing-note.py"
      timeout: 5
  post_llm_call:
    - command: "~/.hermes/agent-hooks/capture-turn-memory.py"
      timeout: 5
  post_tool_call:
    - matcher: "write_file|patch"
      command: "~/.hermes/agent-hooks/track-obsidian-write.py"
      timeout: 5
  subagent_stop:
    - command: "~/.hermes/agent-hooks/log-subagent-stop.py"
      timeout: 5
```

**Recommended event mapping**:
- `pre_llm_call` → inject routing/delegation note when turn mentions agents/cron/long-lived work
- `post_llm_call` → capture high-signal turn summaries to JSONL inbox
- `post_tool_call` (write_file|patch matcher) → record Obsidian writes to event log + dirty-path state file
- `subagent_stop` → append child-run completions to task-ledger JSONL

**Local artifacts** (staging inputs for curation, not the final memory store): `~/.hermes/logs/hermes-memory-capture.jsonl`, `~/.hermes/logs/hermes-obsidian-file-events.jsonl`, `~/.hermes/state/obsidian-dirty-paths.json`, `~/.hermes/logs/hermes-task-ledger.jsonl`

**Activation** (hooks gated by shell-hook allowlist):
1. Write scripts; mark executable
2. Register in `config.yaml`
3. Run one Hermes invocation with hook acceptance enabled to allowlist `(event, command)` pairs
4. Verify: `hermes hooks list` + `hermes hooks doctor` (checks executable, allowlisted, unchanged since approval, valid JSON output)

**Design rules**: output compact JSON (not prose), append-only JSONL for event streams, tiny JSON map for dirty state, keep hooks fast (expensive work → cron).

## Reference files

- `references/obsidian-chat-live-sync.md` — Obsidian Chat Live Sync

## Kolmogorov Sufficient Statistic for Memory Capture (Li-Vitanyi Ch 4)

**Theory:** A sufficient statistic for a dataset x is a function T(x) that captures all task-relevant information: the posterior P(θ|x) = P(θ|T(x)) for any parameter θ. The Kolmogorov sufficient statistic is the minimal such description — the shortest program that preserves all task-relevant structure.

**Hermes rules:**
- The sufficient statistic for a session = the minimal description capturing all task-relevant information needed to complete the task.
- Discard observations that do not change the sufficient statistic: if removing an observation does not change any downstream decision or task completion probability, discard it.
- Concretely: before capturing a fact to memory, ask "Would removing this fact change how I approach any remaining step?" If no → do not capture it.
- This operationalizes aggressive memory triage without requiring explicit distortion measurement.

**Citation:** Li & Vitanyi — *An Introduction to Kolmogorov Complexity and Its Applications* (4th ed.), Ch 4 (Algorithmic Complexity and Information — sufficient statistics and minimal descriptions).

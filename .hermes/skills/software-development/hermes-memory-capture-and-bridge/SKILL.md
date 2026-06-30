---
name: hermes-memory-capture-and-bridge
description: "Use when you want automatic durable knowledge capture after sessions and preflight memory injection before spawning coding agents."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, memory, capture, bridge, hooks, knowledge, agents]
    related_skills: [hermes-agent, hermes-workflow-optimization, hermes-cron-and-agents, hermes-coding-review-loop, hermes-observability-and-task-ledger]
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

Use Hermes shell hooks when you want this behavior to run automatically instead of as a manual end-of-session ritual.

Use `post_llm_call` for compact turn capture, `post_tool_call` for vault-write event logging, and keep each hook script fast and JSON-only so the heavy curation can happen later.

Use hook or lifecycle events that happen when a session is ending or about to compact.

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

See `references/obsidian-chat-live-sync.md` for the concrete pattern used in this workspace.
See `references/runtime-hooks.md` for the live Hermes shell-hook wiring pattern that turns this skill into runtime behavior.

## Good Outputs

- claim-named markdown notes
- a small context file for the child agent
- a short checklist of what is known / unknown
- separate raw-source and distilled-summary artifacts
- one canonical live-sync note plus a lightweight daily-note mirror when summarizing recent chats into Obsidian

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

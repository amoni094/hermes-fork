# Hermes scorecard optimization notes

Session-derived checklist for improving Hermes setup scorecard with durable, non-approval changes.

## Goal

Bias Hermes toward local-first, token-efficient, and recoverable operation while keeping changes small and verifiable.

## High-value knobs

- Model routing:
  - Keep a strong default model for general work.
  - Put a local model first in `fallback_model` so the system can degrade cheaply.
  - Use a local delegation model for subagents when acceptable.
- Prompt/token hygiene:
  - Keep `SOUL.md`, `TOOLS.md`, and `AGENTS.md` compact.
  - Prefer reusable reference files over long inline notes.
  - Preserve stable prefixes when updating config-driven prompts.
- Recoverability:
  - Enable checkpoints.
  - Enable pre-update backups.
  - Keep backup retention bounded.
- Observability:
  - Show cost if available.
  - Hide reasoning unless explicitly needed.
- Memory and context:
  - Store durable environment facts in memory, not chat.
  - Update local notes for stable host details.

## Session-specific vault cleanup pattern

When a scorecard pass is about compactness and retrieval hygiene, the quickest durable wins are:

- Shrink the root workspace notes first (`SOUL.md`, `TOOLS.md`, `AGENTS.md`).
- Keep `MEMORY.md` as a pure index of stable facts, not a narrative log.
- Add a lightweight `DREAMS.md` / sweep log only if it helps preserve recent lessons without bloating the hot path.
- Before claiming a memory gap, check `session_search` and local files first.
- Verify the result with live file sizes and the Hermes health/config checks, then record the verified posture in the scorecard note.


## Pitfalls

- Do not overfit to a one-off benchmark score or temporary dependency issue.
- Avoid editing generated prompt artifacts manually if the repo documents an export flow.
- Avoid approval-policy changes when the task is about local efficiency, recovery, or routing.
- Prefer durable config and note updates over chat-only summaries.

---
name: cliff-compaction
description: Use when compacting long-horizon context. Drop originals; never rephrase or recompact.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - context window full / autocompaction
  - CliffCompaction
  - never compact a compaction
  - long-horizon coding agent context
  - NOT for persistent memory stores (use decision-centric-memory)
metadata:
  hermes:
    tags: [compaction, context, tokens, cache]
    related_skills: [hermes-context-hygiene, hermes-context-budgeting, tool-schema-filter-first, l01-token-efficiency]
---

# Cliff Compaction

Source: arXiv:2609.26779 — CliffCompaction.

## Rules

1. Let context grow until a budget cliff, then compact once. Do not drip-compact every turn (destroys KV-cache).
2. Only drop or shorten original content. Never rephrase or rewrite history. Rewrites introduce context drift.
3. Never compact a compaction. Each pass operates on original content. Discard the previous compacted block and rebuild from remaining originals.
4. Compact tool results first (often more than half of tokens), keep tool-call signatures so the agent can re-fetch.

## When to compact

- Context is near the configured threshold (not every N turns).
- Tool outputs dominate; the agent can re-issue the same tool from a preserved signature.

## When not to

- Short sessions (under about 6 turns): filter tool schemas first (arXiv:2609.22114).
- The agent still needs exact bytes for an edit — recall the original segment, do not summarize it.

## SPEC Selective Propagation (arXiv:2609.23877)

On each compaction pass, tag each block as one of:
- KEEP: decision node, error trace, file path/hash, parameter value used in a later call
- TRIM: intermediate reasoning that reached a conclusion (keep only the conclusion)
- DROP: tool output fully superseded by a later tool call on the same resource

Propagation budget: KEEP ≤ 40% of pre-compaction tokens. Trim before dropping.
Never TRIM a KEEP block. Never DROP a block whose output is still unresolved.

## Verification

- [ ] Compaction dropped or shortened originals; no LLM rewrite of history
- [ ] Previous compacted summary was discarded, not nested
- [ ] Tool signatures remain so dropped outputs are recoverable
- [ ] SPEC tags applied: KEEP ≤ 40% budget, TRIM before DROP
- [ ] No KEEP block was trimmed; no unresolved output was dropped

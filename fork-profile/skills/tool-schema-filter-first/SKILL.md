---
name: tool-schema-filter-first
description: Use when cutting agent token cost. Filter tool schemas before content compression.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - token bill too high on multi-turn coding
  - which compression lever actually saves money
  - tool-schema filtering vs file-read compression
  - Paritok / compression gateway cost attribution
  - NOT for KV-cache architecture (use cliff-compaction)
metadata:
  hermes:
    tags: [tokens, tools, compression, cost]
    related_skills: [cliff-compaction, anthropic-api-cost-optimization, hermes-context-budgeting]
---

# Tool-Schema Filter First

Source: arXiv:2609.22114 — Empirical Cost Attribution of Context-Compression Gateways.

## Hierarchy (where tokens actually go)

1. Tool-schema filtering — only lever that is unambiguously positive every turn. Saves a fixed block linear in turn count N. Do this always.
2. Content compression of file reads / tool output — about 2% of the cache-priced prefix per turn, but savings accumulate with N-squared and overtake (1) around turn 6 until the window caps.
3. History summarization — last; easy to drift; never cite a single-shot SWE-bench compression score as a cost argument.

## Recall cost

A non-destructive gateway that can restore original bytes costs one compressed segment per recall, not a multiplicative blowup. If the agent must edit exact bytes, expect recalls and do not count those compressed tokens as saved.

## Hermes mapping

- Prefer enabled_toolsets / deferred tools over shipping every tool schema every turn.
- Compress long tool outputs after turn ~6; keep originals retrievable.
- Do not treat prompt-token pruning as a substitute for tool filtering.

## Script

`~/.hermes/scripts/tool-schema-cost-audit.py` — lists deferred vs always-loaded tools for the active profile.

## Verification

- [ ] Unused tool schemas are not in the hot path
- [ ] Cost claim is end-to-end (cache tier), not a single-shot compression rate

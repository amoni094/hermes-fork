---
name: memory-retrieval-over-write
description: Use when diagnosing agent memory failures. Prefer retrieval over write pipelines.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - memory not found / wrong memory retrieved
  - LoCoMo / LongMemEval style memory QA
  - choosing between raw chunks vs Mem0 vs MemGPT summaries
  - BM25 vs cosine vs hybrid rerank for agent memory
  - NOT for deciding what to store in SOUL.md or skills
metadata:
  hermes:
    tags: [memory, retrieval, hybrid-search, write-strategy]
    related_skills: [decision-centric-memory, hermes-memory-surface-selection, hermes-memory-capture-and-bridge]
---

# Retrieval Over Write (Memory Probe)

Source: arXiv:2603.02473 — Diagnosing Retrieval vs. Utilization Bottlenecks.

## Finding

On LoCoMo, retrieval method spans about 20 accuracy points (57-77%); write strategy spans only 3-8 points. Raw chunked storage (zero LLM calls at write time) matches or beats Mem0-style extraction and MemGPT-style summarization.

Hybrid retrieval (BM25 + cosine) is the default. Precision beats coverage: LLM-extracted facts (about 3 per query) beat heuristic dumps (hundreds per query).

## Rule

When memory QA fails, diagnose in this order:

1. Retrieval failure — the needed fact was stored but not surfaced.
2. Utilization failure — the fact was retrieved but the model ignored or contradicted it.
3. Write failure — the fact was never stored.

Do not add a more expensive write pipeline until (1) is measured.

## Procedure

1. Keep raw (or lightly structured) episodes as the source of truth.
2. Retrieve with hybrid search (lexical + dense), then rerank.
3. Prefer a small set of high-precision facts over a large heuristic dump.
4. If utilization fails (retrieved but unused), tighten the prompt / citation gate — do not rewrite the store.

## Pitfalls

- Lossy write-time summaries discard details future queries need (query-time construction is the alternative).
- BM25 alone degrades significantly after structured distillation; vector search is more robust (arXiv:2603.13017).
- Confidence-based routing without memory is confidently wrong on user-specific facts (arXiv:2603.23013).

## Verification

- [ ] Failure classified as retrieval / utilization / write
- [ ] Hybrid retrieval used before inventing a new extractor

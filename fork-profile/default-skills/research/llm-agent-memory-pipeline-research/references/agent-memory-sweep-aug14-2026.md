# Agent Memory Sweep — Aug 14 2026 (Sweep 13)

Focus: findings NOT in prior sweeps 1–12. Cutoff: Aug 13 2026.

---

## 1. AgentMemBench — Definitive Strategy Comparison (arXiv:2608.00009)

**URL:** https://arxiv.org/abs/2608.00009  
**Date:** Aug 1, 2026 (announced)  
**Authors:** Ahmed Cherif

### What was tested
Five memory management strategies under identical harness conditions:
- **ICW** — in-context windowing (recency)
- **EKV** — external key-value store (dense retrieval)
- **GEM** — graph-based episodic memory
- **CBS** — compression-based summarization
- **WAM** — web-augmented memory

Evaluated across: LoCoMo (long-term multi-session), MultiDoc2Dial (task-grounded), MSC (persona multi-session).
Also benchmarked MemGPT/Letta and HippoRAG against the same harness.

### Results

| Strategy | Recall@5 (macro) | MRR | F1 | Faithfulness | Footprint |
|----------|:---:|:---:|:---:|:---:|:---:|
| **EKV** | **0.792** | **0.677** | **0.156** | **0.354** | ~5,100 tokens |
| CBS | 0.556 | — | — | — | medium |
| GEM | ≤0.005 (LoCoMo) | — | — | — | medium |
| ICW | ≤0.005 (LoCoMo) | — | — | — | ~300 tokens |
| WAM | ≤0.005 (LoCoMo) | — | — | — | ~300 tokens |

### Key finding — EKV is the ONLY strategy that scales at long horizons
At long ranges (LoCoMo, where the gold turn lies many sessions back):
- ICW, WAM, GEM, CBS: Recall@5 ≤ 0.005 — effectively zero recall
- EKV alone: Recall@5 = 0.573

**Summary verdict:** "Recency windows, summaries, and entity graphs collapse at long horizons — only dense retrieval scales."

CBS is runner-up on retrieval (Recall@5 0.556 overall) and is valid under token budget constraints.
EKV's recall advantage carries a footprint cost (~5,100 vs ~300 tokens).

### Hermes implications
1. For long-horizon Hermes tasks (multi-session agents, multi-day cron loops): EKV (dense retrieval) must be available alongside Graphiti. Graphiti alone (GEM-class) is insufficient at long horizons.
2. CBS (compression/summarization) is appropriate when token budget is the binding constraint.
3. GEM / graph memory should NOT be relied on as the sole memory strategy for tasks spanning >5 sessions.
4. The ~5,100 token footprint cost of EKV is worth it at long horizons — don't optimize it away.

---

## 2. RRM — Reflective Retrieval Memory (arXiv:2607.28156)

**URL:** https://arxiv.org/abs/2607.28156  
**Date:** Jul 30, 2026  
**Authors:** Jingxiang Fan, Junbao Zhuo, Bochao Zou

### Core contribution
Introduces a **reflective experience memory** tier that is distinct from:
- Episodic memory (what happened in this task)
- Semantic memory (what is generally true)

Reflective experience memory stores **transferable procedural retrieval strategies** extracted from historical task trajectories — i.e., knowledge about *how to search* rather than *what to find*.

### Architecture
- Entity-centric multimodal memory graph (episodic + semantic)
- Reflective experience memory layer (procedural retrieval strategies)
- Retrieved experiences become *query-level guidance* — not injected into answers, only into search strategy
- **Lifecycle management:** experience nodes pruned by usage frequency, reuse feedback, and temporal decay → prevents noise accumulation from failed strategies

### Results
Outperforms SOTA on M3-Bench-Robot, M3-Bench-Web, Video-MME-Long.

### Hermes mapping

| RRM tier | Hermes analogue |
|----------|----------------|
| Episodic memory | Graphiti episodes, session_search |
| Semantic memory | MEMORY.md / Hindsight long-term facts |
| **Reflective experience memory** | **Hermes skills (SKILL.md files)** |
| Lifecycle management | `skillopt-continuous-improvement` cron |

The key insight: **Hermes skills ARE the reflective experience memory tier**. The RRM lifecycle (usage frequency, reuse feedback, temporal decay) is exactly what `skillopt-continuous-improvement` should implement for skill pruning. Skills that aren't triggering, aren't producing successful outcomes, or are temporally stale should be pruned under the same logic.

The clean separation of "retrieval strategy knowledge" from "factual recall" maps to the Hermes routing choice: load a skill (procedural) vs. query Graphiti/session_search (factual).

---

## 3. Reproducing LightMem — Naive RAG Often Beats Constructed Memory (arXiv:2607.29104)

**URL:** https://arxiv.org/abs/2607.29104  
**Date:** Jul 31, 2026  
**Code:** https://github.com/ielab/Reproducing-LightMem  
**Authors:** Yongjie Zhou, Shuai Wang, Bevan Koopman, Guido Zuccon

### Core finding
Naive RAG (retrieval directly from raw user turns, no memory construction) **generally outperforms** LightMem (constructed compact memory entries) at matched retrieval depths.

### The critical factor: retriever quality dominates strategy
Changing ONLY the retriever over a fixed LightMem store shifts answer accuracy from 58.1% → 75.5%.
Strategy choice matters less than retriever quality.

### When LightMem wins
LightMem (compression-based) outperforms Naive RAG ONLY under tight answering-token budgets.
Memory construction buys efficiency, not quality.

### Oracle evaluation finding
Oracle evaluation confirms memory construction discards some answer-relevant information — it is an accuracy-efficiency trade-off, not a strict improvement.

### Hermes implications
1. **Invest in retriever quality before memory construction complexity.** If `session_search` is producing poor recall, fix the retrieval mechanism before building elaborate Graphiti pipelines.
2. The elaborate Graphiti construction pipeline may not beat direct session_search for short-to-medium horizon tasks — validate empirically before committing.
3. CBS / compression-based memory is valid specifically when the token budget is the binding constraint, not as a general accuracy improvement.

---

## 4. MRAgent — Active Graph Memory Reconstruction (arXiv:2606.06036, ICML 2026)

**URL:** https://arxiv.org/abs/2606.06036  
**Date:** Jun 4, 2026 (ICML 2026 accepted — missed in prior sweeps)

### Core contribution
Replaces static "retrieve-then-reason" with **active reconstruction**:
- Memory structure: **Cue-Tag-Content graph** (3-tier: fine-grained cues → associative tags → content)
- Tags serve as semantic bridges between cues and content — enabling associative lookup
- LLM reasoning integrated directly into memory access (not applied after retrieval)
- Iterative path exploration: agent explores paths, prunes based on accumulated evidence, avoids combinatorial explosion

### Results
+23% improvement over baselines on LoCoMo + LongMemEval with substantially reduced token and runtime cost.

### Hermes implementation path
The Cue-Tag-Content structure is implementable on top of Graphiti:
- **Content nodes** = existing Graphiti entity/fact nodes
- **Cue nodes** = new lightweight query-entry nodes (how user will ask about this)
- **Tags** = semantic bridge labels connecting cues to content nodes

At retrieval time: query hits cues → traverse tags → reach content = active path exploration rather than k-NN lookup.

This is a Graphiti augmentation path, not a replacement.

---

## Summary: Memory Strategy Selection Guide (Aug 2026 State of Art)

| Scenario | Best strategy | Evidence |
|---------|---------------|---------|
| Long-horizon (>5 sessions, gold turn far back) | **EKV (dense retrieval)** | AgentMemBench |
| Token-budget constrained | **CBS (compression/summarization)** | AgentMemBench |
| Short/medium horizon, invest minimally | **Naive RAG (raw turn retrieval)** | Reproducing LightMem |
| Retrieval strategy failure diagnosis | Fix retriever first, not storage structure | Reproducing LightMem |
| Rich associative lookup needed | **Cue-Tag-Content graph (MRAgent)** | MRAgent ICML 2026 |
| Procedural strategy knowledge | **Skills (RRM analogue)** | RRM |

**Priority finding for Hermes:** EKV (dense retrieval) beats graph at long horizons. Graphiti alone is insufficient for multi-session long-horizon agents. Ensure Hindsight (dense vector) is active and populated for sessions that span multiple days.

# AI Agent Memory Systems: Research Knowledge Bank (2024–2026)

Condensed from systematic arXiv survey, July 2026.
Source file: ~/agent-memory-research-2024-2026.md

---

## arXiv Research Workflow Note

Terminal `curl` to `export.arxiv.org/api/query` returns exit -1 silently
in some environments (Fedora Silverblue, July 2026). Reliable fallback:
- **Discovery**: `web_search(query="<topic> arXiv 2024 2025")`
- **Extraction**: `web_extract(urls=["https://arxiv.org/abs/<ID>"])` — batches of ≤5 URLs
- **Full PDF**: `web_extract(urls=["https://arxiv.org/pdf/<ID>"])`

---

## Memory System Architectures

### Mem0 — Production-Ready Scalable Long-Term Memory
- **arXiv**: 2504.19413 | Apr 2025 | cs.CL/cs.AI
- **Key**: Write-time normalization gate — LLM decides insert/update/delete/merge before storage. Dual-mode: flat vector + optional graph-based relational memory.
- **Metrics**: 26% relative improvement on LLM-as-a-Judge (LOCOMO benchmark) over OpenAI full-context; 91% lower p95 latency; >90% token cost reduction.
- **Hermes gap**: Write-time normalization missing — Hermes only checks NLI at read time. Adding a pre-write gate could cut Graphiti dedup noise.

### AgeMem — Agentic Memory with RL-Trained Unified Policy
- **arXiv**: 2601.01885 (v2: Apr 2026) | Jan 2026 | cs.CL
- **Authors**: Yu, Yao, Xie et al. (Alibaba DAMO)
- **Key**: Memory ops (store/retrieve/update/summarize/discard) as tool-based actions trained via 3-stage progressive RL + step-wise GRPO for sparse discontinuous rewards.
- **Metrics**: Outperforms strong baselines on 5 long-horizon benchmarks; higher-quality LTM + more efficient context usage.
- **Hermes gap**: Memory policy is rule/prompt-based; AgeMem shows RL-trained policy outperforms heuristics. Architecture (memory as tool calls) adoptable immediately; RL training approximable with few-shot prompting.
- **Code**: https://github.com/y1y5/AgeMem

### MemoryOS — OS-Inspired 3-Tier Memory Hierarchy
- **arXiv**: 2506.06326 | Jun 2025 | EMNLP 2025
- **Key**: Short-term (context buffer) → mid-term (session history) → long-term (persistent personal). Composite eviction score = α·recency + β·frequency + γ·importance. Consolidation gate before long-term promotion.
- **Hermes gap**: No mid-term tier. Frequency dimension missing from scoring. Adding access_count to Graphiti edge schema is low-effort, high-value.

### MemOS — Memory OS with MemCube Abstraction
- **arXiv**: 2507.03724 (v4: Dec 2025) | Jul 2025 | cs.CL
- **Authors**: Li et al. (39-author consortium; MemTensor)
- **Key**: MemCube = (content, metadata{provenance, versioning, type}, access_log). Types: plaintext / activation-based / parameter-level. MemCubes can be migrated, composed, fused (episodic→parametric via fine-tuning). Unifies RAG + KV-cache + model weights under one API.
- **Hermes gap**: Graphiti edges lack provenance metadata. Adding episode_uuid + valid_at + created_by to edge schema enables tracing + better conflict resolution.

### Zep — Temporal Knowledge Graph for Agent Memory
- **arXiv**: 2501.13956 | Jan 2025 | cs.CL/cs.AI/cs.IR
- **Key**: Graphiti engine. Bi-temporal KG with valid_at/invalid_at edges. Contradiction resolution via LLM verification + edge invalidation (sets invalid_at, preserves history). "Belief at time T" queries.
- **Metrics**: DMR: 94.8% vs 93.4% (MemGPT). LongMemEval: 18.5% accuracy gain + 90% latency reduction.
- **Hermes note**: Hermes uses Graphiti/Zep. Gap: bi-temporal queries may be under-utilized for temporal reasoning tasks. Verify contradicted facts set invalid_at (not just flagged).

---

## Episodic Memory Theory

### Position: Episodic Memory is the Missing Piece
- **arXiv**: 2502.06975 | Feb 2025 | cs.CL
- **Key**: 5 cognitive properties currently missing: (1) cue-dependent retrieval, (2) spatiotemporal indexing, (3) single-shot learning, (4) autonoetic consciousness, (5) constructive reconstruction.
- **Hermes gap**: Retrieval is pure semantic-similarity. Spatiotemporal keys (session timestamp + task context) + cue-based lookup (partial key fragments) are unexplored.

### H-MEM — Hierarchical Memory with Index Routing
- **arXiv**: 2507.22925 | Jul 2025 | cs.CL
- **Key**: Multi-level abstraction tree. Each vector carries positional index pointer to semantically related sub-memories in next layer. Index-based routing = O(log N) vs O(N) k-NN.
- **Metrics**: Outperforms 5 baselines on LoCoMo long-term dialogue dataset.
- **Hermes gap**: Hindsight uses flat vector search. H-MEM scales better as memory grows. Abstract summary nodes double as compression. Implementable via HNSW + periodic LLM summarization passes.

---

## RAG & Context Optimization

### MemoRAG — Global Memory + Draft-Answer Clue Generation
- **arXiv**: 2409.05591 (v3: Apr 2025) | Sep 2024 | TheWebConf 2025
- **Authors**: Qian, Liu, Zhang et al. (RUC / BAAI)
- **Key**: Dual-system: (1) light long-range model creates global memory (KV compression), generates draft answers as retrieval clues; (2) expensive model uses clues + retrieved chunks for final answer. Memory trained with RLGF (RL from Generation Quality Feedback).
- **Hermes gap**: Direct user query → embedding lookup. Draft-answer-as-clue (HyDE variant) would improve recall on vague queries. 1 extra local LLM call pre-retrieval.

### ReadAgent — Gist Memory with Two-Level Compression
- **arXiv**: 2402.09727 | NeurIPS 2024 | Google DeepMind
- **Key**: (1) LLM segments context into coherent episodes; (2) compresses each to short "gist memory" (1-5 sentences) + pointer to original; (3) re-reads original episode on demand.
- **Metrics**: 20× effective context extension. +20% on QuALITY. Consistent gains on NarrativeQA, GovReport.
- **Hermes gap**: MEMORY.md is a flat summary. Two-level gist + pointer allows lossy compression upfront with lossless retrieval on demand. session_search already holds the "original episode" — needs gist index on top.

### RAPTOR — Recursive Abstractive Tree Retrieval
- **arXiv**: 2401.18059 | ICLR 2024 | Stanford NLP + MIT CSAIL
- **Authors**: Sarthi, Abdullah, Tuli, Khanna, Goldie, Manning
- **Key**: Builds summary tree over corpus: leaf = raw chunk, parent = LLM summary of clustered children (Gaussian mixture in embedding space). Retrieval traverses tree at any level.
- **Metrics**: +10.9% QASPER, +3.9% QuALITY (RAPTOR + GPT-4). State-of-the-art multi-step QA.
- **Hermes gap**: No recursive summary tree over QMD/Hindsight. RAPTOR would serve both detail (leaf) and thematic (root) queries from one index.

### RLMs — Recursive Language Models
- **arXiv**: 2512.24601 (v3: May 2026) | Dec 2025 | cs.AI/cs.CL
- **Authors**: Zhang, Kraska, Khattab (MIT CSAIL + Stanford)
- **Key**: Inference-time paradigm: treats long prompt as external environment, decomposes into snippets, recursively calls itself over sub-problems, maintains working memory of intermediate results. Also post-trained RLM-Qwen3-8B.
- **Metrics**: Processes 100× beyond context window. vs GPT-5: +26% vs compaction, +130% vs CodeAct, +13% vs Claude Code. RLM-Qwen3-8B: +28.3% over base Qwen3-8B.
- **Hermes gap**: Long retrieval → truncation/summary. RLM approach: recursively re-read only necessary sub-segments on demand. Scaffold implementable without fine-tuning.
- **Code**: https://github.com/alexzhang13/rlm

### LongRAG — Long-Context Retrieval Units
- **arXiv**: 2406.15319 | Jun 2024 | CMU LTI
- **Authors**: Jiang et al. (Carnegie Mellon Language Technologies Institute)
- **Key**: Replace 100-token chunks with 4K-token documents. Fewer retrieval units (2-8 vs 50-100). Long-context LLM handles full unit in one pass.
- **Metrics**: NQ: 62.7% answer recall with only 4 units (vs 100 short units for equivalent DPR recall).
- **Hermes gap**: Hindsight uses small chunks. Larger units reduce retrieval precision requirements and pipeline complexity.

---

## Forgetting Mechanisms

### Forgetting Mechanism Taxonomy (from memory system surveys)
- **Source**: Multiple surveys including arXiv 2507.05633, 2507.22931
- **Types**:
  1. **Decay-based**: time-weighted score reduction, Ebbinghaus curve approximation
  2. **Interference-based**: proactive (new overwrites old) / retroactive (old interferes with new)
  3. **Capacity-limited eviction**: FIFO, LRU, LFU, importance-weighted
  4. **Selective rehearsal**: periodic replay of at-risk memories (hippocampal SWS replay analog)
  5. **Abstraction-driven compression**: replace episodic set with semantic summary as memories age
- **Metrics**: Importance-weighted eviction outperforms FIFO/LRU by 15-30% on recall benchmarks.
- **Hermes gap**: Importance scoring exists but no time-decay weighting (importance × e^(-λ·age)). No rehearsal mechanism. Frequency not tracked.

### MemoryOS Composite Eviction Score
- Formula: `score = α·recency + β·frequency + γ·importance`
- Short-term: FIFO eviction
- Mid-term: LFU with importance override
- Long-term: importance-only threshold + consolidation gate

---

## Contradiction Detection & Consistency

### Post-Retrieval NLI Consistency Filtering
- **Source**: RAG Survey (arXiv 2506.00054, Jun 2025) + Zep paper
- **Hermes current state**: NLI check at write time only.
- **Gap**: No post-retrieval consistency check. Contradictory retrieved facts injected together can confuse generation even if each is individually valid.
- **Approaches**:
  1. **NLI post-filtering**: score chunks for entailment/contradiction with query+context before injection; ~8-12% hallucination reduction
  2. **Contrastive decoding**: generate with/without retrieval, take difference to isolate retrieval contribution
  3. **Self-consistency voting**: multiple retrieval calls, majority-vote on answers; +5-15% on multi-hop QA
  4. **Attribution-aware generation**: require model to cite source chunk per claim

### Zep Temporal Conflict Resolution
- When new fact conflicts with existing edge: LLM verification → set `invalid_at=now` on old edge → insert new edge with `valid_at=now`
- Preserves both edges for historical queries ("what did the agent believe on date T?")
- Hermes must verify this pattern is actually firing (not just NLI flagging without invalidation)

---

## 2026 update (SerpApi sweep, July 2026) — new papers since last pass

### TrustMem — Learning Trustworthy Memory Consolidation (arXiv:2606.25161, Jun 2026)
- **Authors**: Tianyu Yang, Sudipta Paul, Vijay Srinivasan, Vivek Kulkarni, Srinivas Chappidi
- **Key**: Write-time memory updates (insert/revise/delete) can omit info, corrupt existing memory,
  or hallucinate unsupported content — errors become permanent system-state failures. TrustMem adds
  a Memory Transition Verifier scoring each update on coverage/preservation/faithfulness, then builds
  preference pairs among candidate updates for the SAME memory state and runs preference-guided RL
  to directly optimize the update policy (not just filter bad updates after the fact).
- **Metrics**: SOTA on MemoryAgentBench (ICLR 2026), HaluMem, Mem-alpha validation. +12.14 F1 on
  HaluMem extraction. Reduces omission/corruption/hallucination by 40.1%/79.1%/50.0% vs best baseline.
- **Hermes gap**: Graphiti's write-time NLI contradiction check (Step 5 of consolidation loop above)
  only catches contradiction, not omission or unfaithful paraphrase during an update. TrustMem's
  three-axis verifier (coverage/preservation/faithfulness) is a stronger write-time gate than binary
  NLI — implementable as an LLM self-check prompt before any Graphiti edge write, no RL needed for
  a first pass: "Does this update PRESERVE necessary content from the old fact, COVER the new
  information, and stay FAITHFUL to source (no unsupported additions)? Score each 0/1."
- **Benchmark note**: MemoryAgentBench (ICLR 2026, github.com/HUST-AI-HYZ/MemoryAgentBench) is now
  the standard eval harness for this space — has a follow-up MemoryArena (ICML 2026) for agentic-task
  memory eval specifically, useful if Hermes ever wants a quantified before/after on a memory change.

### Human-Inspired Memory Architecture (arXiv:2605.08538, May 2026)
- **Key**: Six-mechanism biologically-grounded architecture: (1) sleep-phase consolidation (batch
  dedup + integration, run offline/idle), (2) interference-based forgetting (new similar memories
  degrade old ones — proactive/retroactive), (3) engram maturation (memories strengthen with
  reinforced recall, weaken without), (4) reconsolidation upon retrieval (retrieving a memory
  makes it editable/updatable again, mirrors human memory malleability), (5) entity knowledge
  graphs, (6) hybrid multi-cue retrieval (multiple retrieval signals combined, not just top-K
  vector similarity).
- **Hermes gap**: Mechanism (4), reconsolidation-on-retrieval, is not implemented — Hermes/Graphiti
  facts are static once written until an explicit contradiction triggers invalidation. A cheap
  approximation: when a fact is retrieved and used in a response, bump its `access_count` (already
  a known gap, see MemoryOS row below) AND re-run a lightweight staleness check on that specific
  fact (not the whole graph) since it was surfaced. (3) Engram maturation is effectively what the
  time-decay + LRU-promotion scheme in this skill's MemoryOS section already approximates.
- **Related**: SCM (Sleep-Consolidated Memory, arXiv:2604.20943) is a parallel/independent
  sleep-inspired design — multi-stage sleep cycle (consolidation → dreaming → intentional
  forgetting), reports "perfect recall + robust noise pruning" on their benchmark. Two independent
  groups converging on sleep-phase batch consolidation as the right primitive in the same quarter
  is a fairly strong signal — worth flagging as a candidate for the next `agent-memory-consolidation`
  runbook revision (batch idle-time consolidation pass, not just on-demand).

## Implementation Priority for Hermes

| Gap | Effort | ROI |
|-----|--------|-----|
| Time-decay on retrieval scores: `score × exp(-0.1 × days_since_access)` | 1 day | High |
| HyDE query expansion: generate 1-sentence draft answer → use as embedding query | 1 day | High |
| Access frequency counter on Graphiti edges | 1 day | High |
| Post-retrieval pairwise NLI filter (check retrieved facts against each other) | 2 days | High |
| Write-time normalization gate (Mem0 style: insert/update/delete/merge decision) | 3 days | High |
| Gist + pointer 2-level compression (ReadAgent pattern over session_search) | 3 days | Medium |
| Mid-term memory tier in Graphiti (session-scoped, not yet fully consolidated) | 4 days | Medium |
| Hierarchical index routing (H-MEM, HNSW + abstract summary nodes) | 1 week | Medium |
| RAPTOR tree over QMD corpus (offline periodic job) | 1 week | Medium |
| Recursive decomposition scaffold (RLM pattern, no fine-tuning needed) | 3 days | Medium |

---

## Institutional Attribution

| Institution | Key Paper | arXiv |
|-------------|-----------|-------|
| MIT CSAIL | Recursive Language Models | 2512.24601 |
| Stanford NLP + MIT CSAIL | RAPTOR | 2401.18059 |
| CMU LTI | LongRAG | 2406.15319 |
| Alibaba DAMO | AgeMem | 2601.01885 |
| RUC / BAAI | MemoRAG | 2409.05591 |
| MemTensor (Zhejiang/SJT consortium) | MemOS | 2507.03724 |
| NUS WING | Contextual Representation (SSM vs Transformer) | 2510.06640 |

Tsinghua KEG (Jie Tang, Yuxiao Dong): graph-based RAG + knowledge editing (ROME/MEMIT successors 2024-2025). Search "Tsinghua THUNLP knowledge editing LLM 2025" for current papers — relevant for invalidating stale parametric knowledge in locally fine-tuned models.

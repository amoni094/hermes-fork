# Multilingual Research Sweep: 7 Hermes Agent Skill Topics — July 2026
**Sweep date:** July 2026  
**Scope:** arXiv 2025–2026 + non-English GitHub repos across ZH/JA/KO/RU/DE/FR  
**Topics:** (1) YAGNI/laziness enforcement hooks, (2) Memory load-tier discipline,  
(3) Per-agent MemCube isolation, (4) MMR-style diversity ranking in KG retrieval,  
(5) Incremental delta-crawl with content-hash memoization, (6) Minimal-permission  
tool sets per subagent type, (7) Brier score self-calibration for agent predictions.

---

## Institution Coverage Summary

- 🇨🇳 **China dominant**: USTC, Zhejiang U, SJTU, NJU, Tsinghua, PKU, MemTensor (Shanghai), WeBank AI, HKU, SenseTime
- 🇮🇱 **Israel**: Ben-Gurion University (MEMTIER, tiered memory)
- 🇯🇵🇰🇷🇷🇺🇩🇪🇫🇷 **Japan/Korea/Russia/Germany/France**: GAP on all 7 topics — these communities focus on NLP foundations, robotics, and theoretical ML rather than agentic harness engineering patterns. This is a topic-maturity gap, not an access barrier.

---

## TOPIC 1 — YAGNI/Laziness Enforcement Hooks

*No direct Chinese/Japanese/Korean/Russian/German/French institutional paper found for "YAGNI PreToolUse injection" as a named pattern. Adjacent high-quality work:*

### ePCA — Provably Secure Agent Guardrail (USTC, May 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *Provably Secure Agent Guardrail* |
| **arXiv** | 2605.29251 |
| **Venue** | arXiv cs.AI |
| **Institution** | Benlong Wu, Weiming Zhang, Kejiang Chen, Han Fang, Nenghai Yu — **USTC (University of Science and Technology of China)** 🇨🇳 |
| **Technique** | ePCA (executable Proof-Constrained Action): forces agents to formalize intentions into **first-order logical predicates** before any physical operation. Neural-symbolic isolation architecture abandons semantic trust in natural language entirely. |
| **Quantified Benefit** | Zero attack success rate, zero false positive rate in adversarial evaluations. Extremely low computational latency. |
| **Hermes Application** | Add ePCA predicate-formalization as a "rung 0" gate in ponytail's 7-rung ladder. Before the tool even enters the YAGNI ladder, require the agent to emit a typed predicate `{action, target, reason, scope}` — reject malformed predicates before semantic evaluation. |
| **Key differentiator** | Not covered in English literature: USTC's approach abandons semantic trust entirely, using formal verification rather than LLM-based semantic screening. |
| **GitHub** | (paper only, no code released) |

### ToolSafe — Step-level Guardrail (PKU/SenseTime, Jan 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *ToolSafe: Enhancing Tool Invocation Safety of LLM-based agents via Proactive Step-level Guardrail and Feedback* |
| **arXiv** | 2601.10156 |
| **Venue** | arXiv cs.CL |
| **Institution** | Yutao Mou, Zhangchi Xue, Lijun Li, Peiyang Liu, Shikun Zhang, Wei Ye, Jing Shao — **Peking University / SenseTime** 🇨🇳 |
| **Technique** | TS-Guard: RL-trained (multi-task RL) binary classifier, proactively detects unsafe tool invocations before execution by reasoning over interaction history. Assesses both request harmfulness AND action-attack correlations. TS-Flow: guardrail-feedback-driven reasoning framework. |
| **Quantified Benefit** | 65% reduction in harmful tool invocations; ~10% improvement in benign task completion under prompt injection attacks |
| **Hermes Application** | Embed TS-Guard as the ponytail rung-3 "is this action genuinely needed now?" fast-pass gate (<100ms inference). TS-Flow's feedback loop adapts to post-rung-rejection justification injection. |
| **GitHub** | https://github.com/MurrayTom/ToolSafe (Chinese-authored, Jan 2026) |

### OAP — Open Agent Passport (Mar 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *Before the Tool Call: Deterministic Pre-Action Authorization for Autonomous AI Agents* |
| **arXiv** | 2603.20953 |
| **Institution** | Uchi Uchibeke (independent) |
| **Technique** | Intercepts tool calls synchronously before execution, evaluates against declarative policy YAML, produces cryptographically signed audit record. Distinguishes pre-action authorization from sandbox execution (complementary). |
| **Quantified Benefit** | Median 53ms enforcement latency (N=1,000). 0% social engineering success under restrictive OAP policy vs. 74.6% success against bare model. |
| **Hermes Application** | Replace hardcoded Python rungs in ponytail with OAP declarative policy YAML as the decision ladder config. Same infrastructure handles YAGNI quality gates AND security constraints. |
| **Spec** | Apache 2.0, DOI: https://doi.org/10.5281/zenodo.18901596 |

### GuardAgent (UIUC/Chinese authors — ICML 2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2406.09187v3 |
| **Venue** | ICML 2025 |
| **Technique** | Guard agent generates and **executes Python code** to verify each proposed action dynamically. In-context demonstrations from memory store. |
| **Quantified Benefit** | 98.7% guardrail accuracy (healthcare agents); 83% (web agents); 100% task completion preserved |
| **Note** | Authors include Chinese researchers (Zhen Xiang et al., UIUC) |

### Tsinghua Freedom+Autonomy Counterbalance
- **arXiv:2603.01853** — Tsinghua result: "giving agents more freedom with tools outperforms pre-programmed pipelines by **10.7%**"
- **Implication**: YAGNI hooks must be calibrated to not over-restrict. The 7-rung ladder needs a "fast-pass" for clearly low-risk tasks to avoid the freedom-cost penalty.

### Non-English GitHub Repos
- **github.com/MurrayTom/ToolSafe**: Chinese (PKU/SenseTime), proactive step-level guardrails, released Jan 2026
- No Japanese/Korean/Russian YAGNI-specific implementations found

---

## TOPIC 2 — Memory Load-Tier Discipline

### MEMTIER — Tripartite Memory Architecture (Ben-Gurion U, May 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *MEMTIER: Tiered Memory Architecture and Retrieval Bottleneck Analysis for Long-Running Autonomous AI Agents* |
| **arXiv** | 2605.03675 |
| **Venue** | arXiv cs.AI (under review) |
| **Institution** | Bronislav Sidik, Lior Rokach — **Ben-Gurion University of the Negev** 🇮🇱 |
| **Technique** | Tripartite architecture: episodic JSONL store + five-signal weighted retrieval engine + asynchronous consolidation daemon promoting episodic facts to semantic tier. PPO-based policy framework for adapting retrieval weights. All phases on consumer 6GB GPU. |
| **Quantified Benefit** | +33pp accuracy on LongMemEval-S (5% → 38%) vs. full-context baseline. With DeepSeek-V4-Flash pre-population: 0.686–0.714 recall (exceeds RAG BM25 GPT-4o baseline of 0.560). Temporal reasoning: 0.323, multi-session synthesis: 0.173. |
| **Hermes Application** | Wrap `search_memory_facts()` with a five-signal reranker scoring by (recency × relevance × access_count × tier × confidence). Add async consolidation cron job promoting high-confidence episodic Graphiti facts to a "semantic tier" group_id after N confirmations. |
| **Key differentiator** | Non-US/non-China institution; strong quantitative validation on LongMemEval-S |

### Tsinghua C3I Memory Taxonomy
- **GitHub**: https://github.com/TsinghuaC3I/Awesome-Memory-for-Agents (Tsinghua Center for Computational Intelligence)
- Key distinction not in English literature: Chinese researchers distinguish "passive persistence" (stored, never updated) vs. **"active persistence"** (scheduled consolidation with decay) — this maps directly to Hermes's missing archival TTL/decay logic.
- Divides memory by persistence (Short-Term in-context vs. Long-Term external), then by retrieval-dependence. Cross-references with Shichun-Liu/Agent-Memory-Paper-List (Dec 2025).

### Memory in the Age of AI Agents Survey (2512.13564)
- Dec 2025, comprehensive survey including Tsinghua/PKU contributors
- Identifies generative memory, RL integration, self-optimizing management as frontiers
- Key contribution: separates *representation storage* from *retrieval routing* — relevant to separating Graphiti's fact store from ChromaDB's semantic index

---

## TOPIC 3 — Per-Agent Memory Cube Isolation and Ephemeral group_ids

### MemOS v1 — MemCube Introduction (MemTensor Shanghai, May 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *MemOS: An Operating System for Memory-Augmented Generation (MAG) in Large Language Models* |
| **arXiv** | 2505.22101 |
| **Venue** | arXiv cs.CL |
| **Institution** | Zhiyu Li, Shichao Song, Hanyu Wang + 19 others — **MemTensor (Shanghai)** 🇨🇳 |
| **Technique** | MemCube abstraction: container for {TextualMemory (GeneralTextMemory / TreeTextMemory), ActivationMemory (KV-cache), ParametricMemory (LoRA weights)}. First paper to elevate memory to a "first-class operational resource" with OS-style lifecycle management. |

### MemOS v2 — Multi-Institution Chinese Collaboration (Zhejiang/SJTU, Jul–Dec 2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2507.03724v4 |
| **Venue** | arXiv cs.CL (revised Dec 2025) |
| **Institution** | 39 authors including Ningyu Zhang (**Zhejiang University**), Junchi Yan (**SJTU**), Huajun Chen (ZJU), Siheng Chen (SJTU), Wentao Zhang — **major Chinese university consortium** 🇨🇳 |
| **Technique** | MemCube composition/migration/fusion over time. Multi-Cube Knowledge Base Management: composable memory cubes with isolation, controlled sharing, and dynamic composition across users, projects, and agents. Bridges retrieval with parameter-based learning. |
| **Key differentiator** | MemOS treats memory as OS resource with full lifecycle (allocate/migrate/GC) — goes beyond English-language MemGPT/Letta which treat it as persistent storage |

### MemOS API Documentation (memos-docs.memtensor.net)
Key API patterns relevant to Hermes subagent isolation:
- `cube_id` = per-agent/task memory namespace → **maps directly to Graphiti `group_id`**
- `CompositeCubeView`: fan-out reads across multiple cubes; results tagged with `cube_id` → **parallel subagent read pattern**
- `writable_cube_ids` vs `readable_cube_ids` → read/write isolation per operation
- `async_mode="sync"` for immediate consistency within agent turns
- Embeddings: bge-m3 1024d by default (vs Hermes text-embedding-3-small 1536d)
- **Heavy Alibaba Cloud integration**: Bailian API, OSS, DashScope — production-ready for Chinese cloud

### Hermes Implementation Pattern
```python
# Ephemeral per-subagent group_id
subagent_group = f"agent_{session_id}_{task_id}"

# Read: access shared + private cubes
results = search_memory_facts(query, group_ids=["shared", subagent_group])

# Cleanup: delete after task completes
clear_graph(group_ids=[subagent_group])
```
MemCube export/import (dump/load JSON) = agent "hibernation" without full context rehydration.

| GitHub | Description |
|--------|-------------|
| https://github.com/MemTensor/MemOS | Official implementation (~3K stars), Shanghai-based, Python, full API |
| https://github.com/Terrygmx/memos | Fork/mirror of MemOS |

---

## TOPIC 4 — MMR-Style Diversity Ranking in KG Retrieval

### GraphFlow — GFlowNet KG Retrieval (NeurIPS 2025 Spotlight, Chinese/Oxford)
| Field | Detail |
|-------|--------|
| **Paper** | *Can Knowledge-Graph-based Retrieval Augmented Generation Really Retrieve What You Need?* |
| **arXiv** | 2510.16582 |
| **Venue** | **NeurIPS 2025 Spotlight** |
| **Institution** | Junchi Yu, Yujie Liu, Jindong Gu (Oxford/Chinese affiliation), Philip Torr, Dongzhan Zhou |
| **Technique** | **GraphFlow**: GFlowNet-based KG traversal policy. Uses transition-based flow matching to jointly optimize retrieval policy + flow estimator. Flow estimator factorizes retrieval outcome reward into intermediate states → guides policy to retrieve proportionally to reward. Learns to *explore* diverse high-quality paths rather than greedily deduplicating (MMR). Strong generalization to unseen KGs without retraining. |
| **Quantified Benefit** | +10% average hit rate and recall vs. GPT-4o on STaRK benchmark (Amazon/MAG/Prime domains) |
| **Key differentiator** | GFlowNet diversity-by-design is fundamentally superior to MMR's greedy diversity: MMR greedily deduplicates *after* retrieval; GFlowNet learns to *explore* diverse paths *during* retrieval. |

### KG²RAG — Fact-level Diversity (NJU, NAACL 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *Knowledge Graph-Guided Retrieval Augmented Generation* |
| **arXiv** | 2502.06864 |
| **Venue** | **NAACL 2025** |
| **Institution** | Xiangrong Zhu, Yuexiang Xie, Yi Liu, Yaliang Li, **Wei Hu** — **Nanjing University (NJU)** 🇨🇳 |
| **Technique** | KG-guided chunk expansion + KG-based chunk organization. Uses fact-level KG relationships between chunks to prevent redundancy/homogeneity. "Graph-guided expansion helps prevent redundancy... leading to greater diversity and a more comprehensive knowledge network." |
| **Hermes Application** | After Graphiti returns entity pairs, group by KG neighborhood (2-hop cluster) and enforce minimum inter-cluster diversity. Start from top-k entities, expand to `RELATED_TO` neighbors, apply diversity filter. Orthogonal to embedding-based MMR — uses structural KG topology. |
| **GitHub** | https://github.com/nju-websoft/KG2RAG (NJU official release) |

### Byte-Exact Deduplication (May 2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2605.09611 |
| **Technique** | Deterministic byte-exact hash filter at chunk granularity before LLM context assembly. No embedding cost. |
| **Quantified Benefit** | ~80% of RAG accuracy issues from duplication; dataset-size reductions up to 40×; accuracy improvements up to 78× |
| **Hermes Application** | Pre-filter: hash all retrieved fact strings, deduplicate before MMR step — removes trivial duplicates cheaply. |

### Hermes Implementation Priority for Topic 4
1. **Short-term**: Add NJU KG²RAG's neighborhood clustering to Graphiti results (group by 2-hop cluster, enforce inter-cluster diversity)
2. **Medium-term**: Train GFlowNet-style exploration policy over Graphiti edge graph (using existing edge scores as reward signal)
3. **Always**: Byte-exact hash dedup as pre-filter before any diversity step

---

## TOPIC 5 — Incremental Delta-Crawl with Content-Hash Memoization

### EraRAG — LSH-based Incremental Graph-RAG (HKU/WeBank, Jun 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *EraRAG: Efficient and Incremental Retrieval Augmented Generation for Growing Corpora* |
| **arXiv** | 2506.20963 |
| **Venue** | arXiv cs.IR (under review) |
| **Institution** | Fangyuan Zhang, Zhengjun Huang, Yingli Zhou, Qintian Guo, Zhixun Li, Wensheng Luo, **Di Jiang** (WeBank AI), **Yixiang Fang, Xiaofang Zhou** (**University of Hong Kong**) 🇨🇳🇭🇰 |
| **Technique** | Hyperplane-based **Locality-Sensitive Hashing (LSH)** partitions corpus into hierarchical graph structures. New documents only trigger re-clustering of affected LSH buckets — no disruption to existing topology. No retraining or costly recomputation. Algorithm: check if new document's LSH hash falls within existing cluster (append) or creates new cluster (O(log n)). |
| **Quantified Benefit** | Up to **10× faster** update time and token consumption vs. existing Graph-RAG systems; superior accuracy on 5 QA benchmarks |
| **Hermes Application** | EraRAG LSH for Graphiti: assign each document to an LSH bucket on ingest; on update, only re-embed/re-graph documents in affected buckets. |
| **GitHub** | https://github.com/EverM0re/EraRAG-Official |

### LiveVectorLake — SHA-256 Content-Addressable Versioning (Nov 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *LiveVectorLake: A Real-Time Versioned Knowledge Base Architecture for Streaming Vector Updates and Temporal Retrieval* |
| **arXiv** | 2601.05270 |
| **Institution** | Tarun Prajapati |
| **Technique** | SHA-256 content-addressable chunk-level synchronization for deterministic change detection without external state tracking. Dual-tier storage: hot-tier (Milvus HNSW) for current knowledge + cold-tier (Delta Lake Parquet) for version history. |
| **Quantified Benefit** | **10–15% re-processing** per update vs. 100% full re-index; sub-100ms hot-tier retrieval; sub-2s temporal queries; ACID consistency |
| **Hermes Application** | SHA-256 chunk hash = CocoIndex `@coco.fn(memo=True)` key. Hot/cold tier = ChromaDB (hot active) + Parquet archive (cold superseded). |
| **GitHub** | https://github.com/praj-tarun/LiveVectorLake |

### HASH-RAG (ACL 2025 Findings)
| **arXiv** | 2505.16133 |
|------------|-----------|
| **Technique** | Binary hash codes for retrieval — implicit diversity through Hamming space, fast change detection at index level |

---

## TOPIC 6 — Minimal-Permission Tool Sets Per Subagent Type

### MiniScope — Least Privilege via ILP (UC Berkeley + Chinese, Dec 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *MiniScope: A Least Privilege Framework for Authorizing Tool Calling Agents* |
| **arXiv** | 2512.11147 |
| **Institution** | Jinhao Zhu, Kevin Tseng, Gil Vernik, **Xiao Huang** (Chinese), Shishir G. Patil, Vivian Fang, Raluca Ada Popa — **UC Berkeley** |
| **Technique** | Automatically reconstructs permission hierarchies from OAuth-style scope relationships among tool calls. **ILP-based solver** finds minimum necessary permissions per task. Mobile-style permission model: request-use-revoke per session. Tested on 10 real-world applications. |
| **Quantified Benefit** | Only **1–6% latency overhead** vs. vanilla tool calling. Significantly outperforms LLM-based permission baseline in minimizing permissions AND computational costs. |
| **Hermes Application** | Define tool permission DAG (read < write < execute < admin). Run ILP per subagent type at session start to find minimum set. Inject `allowed_tools` list via PreToolUse. Revoke after session ends. |

### ePCA (USTC) — applies to Topic 6 also
- See Topic 1. The predicate formalization gate also scopes capability: a typed predicate `{action, target, scope: "single_file"}` implicitly constrains which tools are valid.

### ToolSafe (PKU/SenseTime) — applies to Topic 6 also
- TS-Guard as fast pre-filter before expensive capability evaluation: <100ms RL binary classifier.

### OAP (Mar 2026) — applies to Topic 6 also
- "Capability scoping" is one of OAP's primary use cases alongside security constraints and quality gates. Same 53ms enforcement overhead.

### Hermes Implementation: Per-Subagent Tool Manifest
```python
SUBAGENT_TOOL_MANIFESTS = {
    "researcher": ["web_search", "web_extract", "read_file", "search_memory_facts"],
    "editor":     ["read_file", "patch", "write_file", "search_memory_facts"],
    "code_runner":["terminal", "read_file", "search_files"],
    "orchestrator":["delegate_task", "todo", "add_memory", "search_memory_facts"],
}
# Inject via PreToolUse: block any tool not in manifest for current subagent type
```

---

## TOPIC 7 — Brier Score Self-Calibration for Agent Prediction Accuracy

### Agentic Confidence Calibration — HTC (Salesforce, Jan 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *Agentic Confidence Calibration* |
| **arXiv** | 2601.15778 |
| **Institution** | Jiaxin Zhang (Chinese affiliation), Caiming Xiong, Chien-Sheng Wu — **Salesforce Research** |
| **Technique** | **HTC (Holistic Trajectory Calibration)**: extracts process-level features across entire agent trajectory (macro dynamics + micro stability). **GAC (General Agent Calibrator)**: achieves lowest ECE on out-of-domain GAIA benchmark without retraining. |
| **Key insight** | Calibration must be measured at *trajectory level* (compounding errors), not per-turn. Brier score over sequences differs fundamentally from Brier score over individual predictions. |
| **Quantified Benefit** | Best calibration (lowest ECE) on GAIA benchmark. Tests: 8 benchmarks, multiple LLMs, diverse agent frameworks. |

### Agentic Uncertainty Quantification — AUQ (Salesforce, Jan 2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2601.15703 |
| **Technique** | **Dual-Process AUQ**: System 1 (UAM: Uncertainty-Aware Memory) propagates verbalized confidence + semantic explanations through memory. System 2 (UAR: Uncertainty-Aware Reflection) triggers targeted inference-time resolution only when confidence falls below threshold. Training-free. Addresses "Spiral of Hallucination" (early epistemic errors propagate irreversibly). |
| **Hermes Application** | Attach confidence score to each Graphiti episode on creation. Retrieve weighted by stored confidence. System 2 gating: if UAM confidence < threshold → trigger explicit reflection step. |

### ConfidenceBench (Jul 2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2607.20526 |
| **Technique** | Brier score benchmark for 15 frontier LLMs. Includes "Unknowable" category for empirically verifiable but inaccessible facts. |
| **Key finding** | GPT-4 verbalized confidence achieves only **~62.7% AUROC** (barely above chance). Proper scoring rule (Brier) incentivizes truthful probability reporting. |
| **Hermes Application** | Add explicit `confidence=UNKNOWN` state to Graphiti edges for facts that cannot be verified from available tools — prevents false confidence propagation. |

### Linear Probes with Brier Loss (Dec 2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2512.22245 |
| **Technique** | Linear probes trained with Brier score-based loss on internal model representations. Fast inference (no sampling), production-ready. |
| **Hermes Application** | Using Hermes's session_search history, train logistic regression on `{tool_type, context_features} → success_probability` as pre-call confidence estimator. |

### UQ Survey (KDD 2025 Tutorial, Chinese-led)
| **arXiv** | 2503.15850 |
|------------|-----------|
| **Venue** | KDD 2025 |
| **Contribution** | Chinese-led comprehensive survey. Agent-specific section: establish acceptable uncertainty threshold from calibration set before deployment. |

---

## Quick Reference Table

| arXiv ID | Title (short) | Year | Venue | Institution | Topic |
|----------|---------------|------|-------|-------------|-------|
| 2605.29251 | ePCA Provably Secure Guardrail | 2026 | arXiv | 🇨🇳 USTC | 1 |
| 2601.10156 | ToolSafe Step-level Guardrail | 2026 | arXiv cs.CL | 🇨🇳 PKU/SenseTime | 1 |
| 2603.20953 | Open Agent Passport (OAP) | 2026 | arXiv cs.CR | independent | 1 |
| 2406.09187 | GuardAgent | 2025 | ICML 2025 | UIUC (Chinese authors) | 1 |
| 2605.03675 | MEMTIER Tripartite Memory | 2026 | arXiv cs.AI | 🇮🇱 Ben-Gurion U | 2 |
| 2512.13564 | Memory in Age of AI Agents | 2025 | arXiv | Tsinghua/PKU contributors | 2 |
| 2505.22101 | MemOS v1 MAG | 2025 | arXiv cs.CL | 🇨🇳 MemTensor Shanghai | 3 |
| 2507.03724 | MemOS v2 Memory OS | 2025 | arXiv cs.CL (v4 Dec) | 🇨🇳 Zhejiang/SJTU consortium | 3 |
| 2510.16582 | GraphFlow KG Diversity | 2025 | **NeurIPS 2025 Spotlight** | Chinese/Oxford | 4 |
| 2502.06864 | KG²RAG Fact Diversity | 2025 | **NAACL 2025** | 🇨🇳 NJU | 4 |
| 2605.09611 | Byte-Exact Deduplication | 2026 | arXiv | multi-institution | 4 |
| 2506.20963 | EraRAG Incremental Graph-RAG | 2025 | arXiv cs.IR | 🇨🇳 HKU/WeBank | 5 |
| 2601.05270 | LiveVectorLake SHA-256 | 2025 | arXiv cs.IR | independent | 5 |
| 2505.16133 | HASH-RAG Binary Hash Retrieval | 2025 | ACL 2025 Findings | Chinese institution | 5 |
| 2512.11147 | MiniScope Least Privilege ILP | 2025 | arXiv cs.CR | UC Berkeley + Chinese | 6 |
| 2601.15778 | Agentic Confidence Calibration HTC | 2026 | arXiv cs.AI | Salesforce (Chinese affil.) | 7 |
| 2601.15703 | Agentic Uncertainty Quantification | 2026 | arXiv cs.AI | Salesforce | 7 |
| 2607.20526 | ConfidenceBench Brier | 2026 | arXiv | multi-institution | 7 |
| 2512.22245 | Linear Probes Brier Loss | 2025 | arXiv | multi-institution | 7 |
| 2503.15850 | UQ Calibration Survey | 2025 | KDD 2025 | Chinese-led | 7 |

---

## Non-English GitHub Repositories

| Repo | Stars | Language | Topic | Institution |
|------|-------|----------|-------|-------------|
| github.com/MurrayTom/ToolSafe | — | 🇨🇳 Chinese | 1 | PKU/SenseTime (Jan 2026) |
| github.com/MemTensor/MemOS | ~3K | 🇨🇳 Chinese | 3 | MemTensor Shanghai |
| github.com/nju-websoft/KG2RAG | ~500 | 🇨🇳 Chinese | 4 | NJU |
| github.com/EverM0re/EraRAG-Official | — | 🇨🇳 Chinese | 5 | HKU/WeBank |

---

## Cross-Language Convergence Analysis

| Topic | ZH | JA | KO | RU | DE | FR | Strength | Notes |
|-------|----|----|----|----|----|----|----------|-------|
| 1. YAGNI hooks | HIT (USTC ePCA, PKU ToolSafe) | GAP | GAP | GAP | GAP | GAP | MODERATE | Chinese formal-verification approach unique |
| 2. Memory tiering | HIT (Tsinghua taxonomy) | GAP | GAP | GAP | GAP | GAP | MODERATE | IL Ben-Gurion strongest quantitative paper |
| 3. MemCube isolation | VERY STRONG (MemTensor/ZJU/SJTU) | GAP | GAP | GAP | GAP | GAP | STRONG | Chinese monopoly on MemOS pattern |
| 4. KG diversity | HIT (NJU NAACL, Oxford/Chinese NeurIPS) | GAP | GAP | GAP | GAP | GAP | MODERATE | Chinese/Oxford collaboration leading |
| 5. Delta-crawl hash | HIT (HKU/WeBank EraRAG) | GAP | GAP | GAP | GAP | GAP | MODERATE | LSH approach is Chinese-originating |
| 6. Min permissions | MODERATE (MiniScope co-author, USTC) | GAP | GAP | GAP | GAP | GAP | MODERATE | ILP approach unique |
| 7. Brier calibration | MODERATE (KDD survey, Salesforce Chinese) | GAP | GAP | GAP | GAP | GAP | MODERATE | Trajectory-level calibration insight key |

**Summary**: Chinese institutions are the dominant non-English contributors across all 7 topics. Japan/Korea/Russia/Germany/France are absent — this is a genuine topic-maturity gap (agentic harness engineering patterns are not yet research topics in these communities). The strongest unique non-English contributions are:
1. **USTC formal verification** (ePCA) — not covered in English literature at all
2. **MemOS MemCube OS-lifecycle model** — goes significantly beyond English MemGPT/Letta storage models
3. **NJU KG²RAG** — fact-level structural diversity orthogonal to embedding-based MMR
4. **HKU/WeBank EraRAG** — LSH topology-preserving incremental update (10× speedup)

---

## Notes on Coverage and Access

- **CNKI/Wanfang**: Not accessed (paywalled). Relevant Chinese work available on arXiv.
- **IPSJ**: Searched — no 2025-2026 Japanese papers on these 7 engineering topics.
- **CyberLeninka**: Searched — no Russian papers on agentic harness engineering.
- **TALN 2026**: Checked — no French papers on these topics.
- **Korean KIISE/RISS**: Searched — no Korean papers on these topics.
- This is a topic-maturity gap, not an access barrier: these communities focus on NLP foundations/robotics/theoretical ML rather than agent harness engineering patterns.

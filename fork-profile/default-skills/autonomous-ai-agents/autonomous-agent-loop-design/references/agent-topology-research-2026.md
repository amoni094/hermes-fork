# Agent Topology & Token Optimization: Research Evidence Base (2024–2026)

Citable reference for skill patches in `harness-first-agent-design`, `autonomous-agent-loop-design`,
and `hermes-context-hygiene`. 29 papers retrieved July 2026 via targeted arXiv + web extraction.

---

## TOPOLOGY SELECTION

### Single vs. Multi-Agent

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| "Single-agent or Multi-agent? Why Not Both?" (UIUC) | 2505.18286 | 2025 | Hybrid routing: +1.1–12% accuracy; up to 88% cost reduction; 15 datasets, 9 frameworks |
| Incident Response MAS (Drammeh) | 2511.15755 | 2025 | SAS: 1.7% actionable rate; MAS: 100%. 80× action specificity, 140× solution correctness. 348 trials |

Decision rule: SAS for short/well-scoped tasks with frontier models. MAS required for structured
operational tasks (incident response, RCA) — the gap is qualitative, not quantitative.

### Topology Patterns

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| AdaptOrch (Korea National Open U) | 2602.16873 | 2026 | 12–23% over static single-topology; topology Ω(1/ε²) dominates model selection when models within 3 MMLU pts |
| MoA (Wang et al.) | 2406.04692 | 2024 | 65.1% AlpacaEval 2.0 vs. 57.5% GPT-4o using open-source only |
| Self-MoA (Princeton) | 2502.00674 | 2025 | +6.6% over MoA on AlpacaEval; +3.8% avg on MMLU/CRUX/MATH; same model ×N beats cross-model |
| GPTSwarm (Zhuge et al., ICML 2024) | 2402.16823 | 2024 | Graph abstraction baseline; node=LLM call, edge=info flow; both are optimizable |
| AgentPrune (Zhang et al., ICLR 2025) | 2410.02506 | 2024 | $5.60 vs $43.70 dense (7.8× cheaper); 28–73% token reduction; +3.5–10.8% robustness vs adversarial |
| DyTopo (Lu et al., Peking/Georgia Tech) | 2602.06039 | 2026 | +6.2% over best fixed baseline; 51% token savings; converges in 2.6 rounds vs 5-round fixed budget |
| MetaGen | 2601.19290 | 2026 | Training-free role+topology co-adaptation at inference time; start minimal, grow via feedback |
| AgentOrchestra (TEA Protocol) | 2506.12508 | 2025 | 89.04% on GAIA Test; hierarchical + lifecycle-aware coordination |
| DEI / Committee (Salesforce) | 2408.07060 | 2024 | 27.3% → 55% on SWE-Bench Lite; framework diversity > model diversity |
| Multi-Agent Survey | 2501.06322 | 2025 | Taxonomy: actors, cooperation types, structures, strategies, coordination protocols |

### Four Canonical Topologies (AdaptOrch)

| Topology | Best For | DAG Signal |
|---|---|---|
| Parallel | Independent subtasks; high fan-out | Low coupling, high width |
| Sequential | Ordered pipelines; strict dependencies | Deep critical path, high coupling |
| Hierarchical | Complex sub-decomposable tasks | Nested DAG with sub-planners |
| Hybrid | Mixed dependency structure | Both parallel and sequential segments |

Routing algorithm: analyze task DAG in O(|V|+|E|) → output topology.

### Cross-Paper Findings (invariants)

1. As models converge (top-10 within 3 MMLU pts, Jan 2026), topology variance dominates model selection by Ω(1/ε²).
2. Dense/fully-connected topologies waste 28–73% of tokens — prunable with no accuracy loss.
3. Fixed topologies fail multi-round tasks — early rounds need dense exploration, late rounds sparse verification.
4. Self-MoA (same top model ×N) beats cross-model MoA by 6.6% — quality contamination outweighs diversity.
5. Framework diversity > model diversity for SWE tasks (DEI: 27.3% → 55%).
6. For structured operational tasks, SAS is categorically insufficient (1.7% vs 100% actionable rate).

---

## TOKEN OPTIMIZATION

### Prompt Caching

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| "Don't Break the Cache" (Lumer et al.) | 2601.06007 | 2026 | 41–80% API cost reduction; 13–31% TTFT improvement; 500+ sessions, 10K-token prompts |
| CacheBlend (Yao et al.) | 2405.16444 | 2024 | 2.2–3.3× TTFT reduction; 2.8–5× throughput; reuse KV cache regardless of position |
| KVFlow (Pan et al.) | 2507.07400 | 2025 | 1.83–2.19× speedup; Agent Step Graph guides eviction; overlapped KV prefetching |
| SnapKV (Li et al., NeurIPS 2024) | 2404.14469 | 2024 | 3.6× speed at 16K tokens; 8.2× memory; 380K context on single A100 |

Prompt caching rules (from 2601.06007):
- Static content (system prompt, tools, constraints) at top of context
- Dynamic content (task state, tool results) at bottom
- Exclude dynamic tool results from cached block
- Avoid dynamic function-calling formats
- Anthropic: 0.1× base price on cache reads (90% off); min prefix 1,024 tokens
- OpenAI: 90% discount on cached prefixes >1,024 tokens

### Context Compression

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| LLMLingua-2 (Microsoft, ACL 2024) | 2403.12968 | 2024 | 3–6× faster compress; 1.6–2.9× E2E latency reduction; 2×–5× compression ratio; <5% accuracy loss |
| xRAG (NeurIPS 2024) | 2405.13792 | 2024 | 3.53× FLOP reduction; >10% quality improvement vs prior compression; matches full-text RAG |
| RAG Compression Survey | 2409.13385 | 2024 | Taxonomy: extractive, abstractive, semantic filtering, embedding-based, hybrid |

### Token Budget Enforcement

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| TALE (Han et al.) | 2412.18547 | 2024 | Dynamic complexity-adjusted budget in prompt; large CoT reduction, ~2% perf drop |
| ThinkPrune (Hou et al., UCSB) | 2504.01296 | 2025 | RL with token limit; 50% reasoning length reduction on AIME24 at 2% perf drop |

### Speculative Decoding

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| EAGLE-2 (SafeAILab) | 2406.16858 | 2024 | 3.05–4.26× speedup; dynamic draft tree |
| EAGLE-3 (NeurIPS 2025) | 2503.01840 | 2025 | Up to 6.5× speedup; 1.38× batch throughput in SGLang; prod on AWS/GCP |
| SuffixDecoding (CMU/Snowflake, NeurIPS 2025) | 2411.04975 | 2024 | 5.3× on AgenticSQL; 2.5× on SWE-Bench; model-free, zero GPU overhead |

### Speculative Tool Execution

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| Speculative Tool Calls (Nichols et al.) | 2512.15834 | 2025 | 100s tok/s throughput improvement; begin tool exec before decoding finishes |
| PASTE (Sui et al.) | 2603.18897 | 2026 | 43.5% task completion time reduction; 1.8× lower tool latency |
| Speculative Actions (Ye et al.) | 2510.04371 | 2025 | 55% next-action prediction accuracy; 20% latency reduction |

### Tool Prompt Efficiency

| Paper | Venue | Year | Key Metric |
|---|---|---|---|
| Joint Tool Optimization (Bloomberg AI) | ACL Findings 2025 (2025.findings-acl.1149) | 2025 | Jointly optimizes agent instructions + tool descriptions; fewer LLM calls needed |

Insight: poorly written tool descriptions are a primary source of extra CoT inference steps.
Treat tool definitions as first-class optimization targets alongside system prompts.

---

## SKILL MANAGEMENT RESEARCH (2025-2026)

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| SkillRouter | 2603.22455 | 2026 | Full SKILL.md body critical; hiding it drops accuracy 31-44 pp. BM25 sufficient at <500 skills |
| ToolScope | 2510.20036 | 2026 | Auto-merge overlapping tools → 8-38% accuracy gain; sim>0.80 pairs are candidates |
| Toolken+ | 2410.12004 | 2024 | Reject option (no tool passes threshold → bare LLM fallback); immediate, no training |
| SkillComposer | 2606.32025 | 2026 | Skill composition as joint ordered-sequence prediction; +23 pp pass rate |
| SkillRevise | 2606.01139 | 2026 | Trace-conditioned revision raises skill success 36%→62%; revise before resurrect |
| SkillsVote | 2605.18401 | 2026 | Evidence-gated resurrection: only re-enable when active set fails on disabled skill's domain |
| SkillsBench | 2602.12670 | 2026 | Focused skills ≤3 modules beat large bundles by +16.6 pp; smaller model+skills matches larger |
| Agent Skills Survey | 2605.07358 | 2026 | Authoritative taxonomy: representation → acquisition → retrieval → evolution lifecycle |
| "Drop the Hierarchy" | 2603.28990 | 2026 | LLM-induced taxonomy beats curator-imposed; re-cluster monthly via LLM |

Skill quality composite score (Q-score):
  Q = 0.35*task_success + 0.25*user_correction_rate(inverted) + 0.20*routing_precision + 0.10*brevity + 0.10*recency
Track in: ~/.hermes/skill_telemetry.jsonl — user_correction_rate is single most predictive signal.

## CONTEXT COMPRESSION RESEARCH (2024-2026)

| Paper | arXiv | Year | Key Metric |
|---|---|---|---|
| LLMLingua-2 | 2403.12968 | 2024 | 2-5x compression, 3-6x faster, task-agnostic encoder; <5% accuracy loss |
| LongLLMLingua | 2310.06839 | 2024 | Query-aware compression; mutual info scoring; targets RAG chunk injection |
| Selective Context | 2310.06201 | 2023 | CPU-only, GPT-2 surprisal proxy; ~50% compression; lightweight first-pass |
| Self-Route | 2407.16833 | 2024 | LLM self-classifies retrieval need; matches LC perf at fraction of cost |
| A-MEM | 2502.12110 | 2025 | Zettelkasten-style autonomous cross-linking; outperforms MemGPT on 6 models |
| MemInsight | 2503.21760 | 2025 | Proactive importance tagging (domain, recency, score) at write time |
| Recursive Summarization | 2308.15022 | 2023 | Tiered rolling summaries (per-tool, per-session, cross-session) |

## ACTIONABLE SUMMARY FOR HERMES

1. **Topology before model** — when models are similar-capability, topology choice yields 12-23%
   improvement. Analyze task DAG structure first.

2. **Prune dense topologies** — never ship fully-connected N>3 agent graphs. Apply AgentPrune
   or DyTopo semantic routing. 28-73% token savings, no accuracy loss.

3. **Stage-dependent rewiring** — early rounds: dense (exploration). Late rounds: sparse
   (targeted verification). Don't lock topology at design time.

4. **Cache prefix discipline** — static at top, dynamic at bottom, tool results excluded.
   41-80% cost savings on agentic workloads. Free at Anthropic/OpenAI.

5. **Token budget in prompt** — inject explicit budget for reasoning steps. 50% length
   reduction at 2% perf cost is achievable for thinking-capable models.

6. **Self-MoA for ensembles** — query the same top model N times rather than mixing
   different models. +6.6% accuracy gain.

7. **Framework diversity for code** — for SWE tasks, use a committee of different agent
   frameworks (e.g. Aider + Claude Code + Codex), not multiple instances of one.

8. **Embed full SKILL.md bodies** — not just name+description for skill routing (SkillRouter).
   31-44 pp accuracy gain. BM25 over full bodies sufficient at <500 skills.

9. **Audit high-similarity skill pairs** — cosine sim > 0.80 = merger candidate (ToolScope).
   Named candidates: github-issues/github-operations, obsidian/obsidian-research-ingestion.

10. **Track user_correction_rate** — single most predictive skill quality signal (SkillsBench).
    Log to ~/.hermes/skill_telemetry.jsonl; weight 0.25 in Q-score composite.

11. **Dead-skill resurrection gate** — revise before resurrect (SkillRevise: 36%→62% success).
    Only re-enable when active skill set demonstrably fails on the disabled skill's domain.

12. **A-MEM enriched Graphiti writes** — pass domain-specific extraction instructions;
    autonomous cross-linking improves routing precision without schema changes.

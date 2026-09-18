# Agent Memory Systems: August 2026 Paper Sweep

Session: 2026-08-08 "AI Memory Architecture Optimization"
Source: session_search @session:default/20260808_231423_901b3c + delegation logs

All URLs: https://arxiv.org/abs/<ID>

---

## Memory Architecture Track

| ID | Title | Key metric | Hermes gap |
|----|-------|-----------|-----------|
| 2601.03236 | MAGMA: Multi-Graph Agentic Memory Architecture (ACL 2026, Jiang et al.) | SOTA LoCoMo + LongMemEval | session_search is monolithic; no causal/temporal graph separation |
| 2605.03675 | MEMTIER: Tiered Memory for Long-Running Agents (Sidik & Rokach) | +33pp LongMemEval-S (0.050→0.382), consumer GPU | No async episodic→semantic promotion daemon |
| 2606.24775 | Are We Ready For An Agent-Native Memory System? (Tsinghua/PKU, SIGMOD) | 12 systems × 11 datasets; no single arch dominates | No routing layer between memory types |
| 2606.25161 | TRUSTMEM: Trustworthy Memory Consolidation (Amazon) | -79.1% corruption, -50% hallucination, +12.14 F1 | No write verifier (coverage/preservation/faithfulness) |
| 2607.03228 | Organizational Memory for Agentic BPE (SAP, Kirchdorfer et al.) | Qualitative PoC | Skills are per-profile; no governed cross-agent curation |
| 2608.00122 | Shared Org Memory for Enterprise Coding (Dhanyamraju & Raghav) | Production deployed | No contributor-approval capture, no security gate on writes |
| 2605.21768 | Memory-R2: Fair Credit Assignment (LMU Munich/Siemens, Yan et al.) | Stable RL across 32-session horizons | Memory writing is heuristic; no RL credit across sessions |
| 2604.03295 | Scaling Teams or Scaling Time? LLMA-Mem (IIT/Cisco, Wu et al.) | Non-monotonic: small teams + memory > large teams w/o | Subagents have no cross-agent shared memory topology |
| 2607.00233 | Memory Architecture Drives Language Emergence (U. Alberta, Talebirad et al.) | Notebook agents: 0.867±0.023 coord accuracy; stateless agents collapse | No persistent shared convention notebooks |
| 2607.13591 | MemCon: MDP-Based Memory Routing (UCLA/MIT+) | +15.2 task success, 5-20% token reduction | Memory routing is heuristic, not a learned bandit policy |
| 2607.12893 | MemOps: Memory Lifecycle Benchmark | Structured REMEMBER/FORGET/UPDATE/REFLECT/COMPOSE traces | No lifecycle tags on memory writes |
| 2605.16045 | RecMem: Lazy Consolidation (CUHK, ACL 2026) | 87% token cost reduction | Nightly cron consolidates everything; should be recurrence-triggered |
| 2605.15701 | H-Mem: Hybrid Temporal Tree + KG | SOTA on 3 memory benchmarks | Hindsight uses flat vector search |
| 2606.00610 | MemGraphRAG: 3-Layer Multi-Agent Graph Memory (KDD 2026, XMU) | Conflict resolution during multi-agent graph construction | No multi-agent shared graph with conflict detection |

## Token Optimization Track

| ID | Title | Key metric |
|----|-------|-----------|
| 2604.21816 | Tool Attention: Dynamic Tool Gating + Lazy Schema Loading | Eliminates MCP/tools tax in scalable agentic workflows |
| 2605.26165 | Tool-Schema Compression for Agentic RAG Under Constrained Context | Constrained-context agentic RAG |
| 2606.10209 | Less Context, Better Agents: Efficient Context Engineering | Long-horizon tool-using LLM agents |
| 2606.17016 | TokenPilot: Cache-Efficient Context Management | LLM agents |
| 2607.06906 | The Harness Effect: Token Economics of Enterprise Agentic AI | Orchestration design shapes token spend |
| 2607.21503 | Agentic Context Management: Lifecycle + Architecture Problems | Lifecycle and architecture framing |
| 2607.21604 | AgentKVShift: Efficient KV Cache Reuse | Agentic memory systems |
| 2608.00902 | Practical Online KV Cache Compaction (Empirical Study) | LLM agents |
| 2608.01056 | Control Under Compression: Reliability Frontiers | 35% compression floor — below this, task reliability degrades |
| 2603.13017 | Structured Distillation for Personalized Agent Memory | 11x token reduction with retrieval preservation |
| 2601.06007 | Don't Break the Cache: Prompt Caching for Long-Horizon Agentic Tasks | Prompt caching evaluation |

## Retrieval Workflow Note

arXiv API (export.arxiv.org) timed out in the Aug 8 session for all queries.
Reliable fallback confirmed:
- Discovery: web_search(query="<topic> arXiv 2026")
- Extraction: web_extract(urls=["https://arxiv.org/abs/<ID>"]) — batches ≤5 URLs
- Full text: web_extract(urls=["https://arxiv.org/html/<ID>"])

## Delegation Cache Recovery

When subagents write JSON to /tmp, those files are cleared after session end.
Recover from:
  ~/.hermes/cache/delegation/subagent-summary-<N>-<timestamp>.txt  (final summaries — durable)
  ~/.hermes/cache/delegation/live/deleg_<id>/task-<N>.log          (full trace — durable)

grep for paper IDs:
  grep -oP '\d{4}\.\d{4,5}' ~/.hermes/cache/delegation/live/deleg_<id>/task-N.log | sort -u
  grep -oP '"(title|url)": "[^"]+"' task-N.log | sort -u

# AI Agent Research Taxonomy — Verified Citation Bank (August 2026)

Sweep conducted Aug 30, 2026. Sources: Semantic Scholar API, Papers With Code snippets, web search snippets, arXiv.gg, Luo et al. 2025 survey (arXiv:2503.21460), Wang et al. 2023 survey (arXiv:2308.11432), CoALA (arXiv:2309.02427), Awesome-Agent-Papers repo, AI Agent Index 2026 (arXiv:2602.17753).

Purpose: canonical reference for AI agent research categories relevant to Hermes-like systems (reasoning, memory, tool use, multi-agent, eval, evolution).

---

## Taxonomy (Luo et al. 2025 — most comprehensive 2025 framework)

Primary categories (Methodology axis):
  I.   Agent Construction: Profile Definition, Memory Mechanism, Planning Capability, Action Execution
  II.  Agent Collaboration: Centralized, Decentralized, Hybrid architectures
  III. Agent Evolution: Autonomous optimization, multi-agent co-evolution, external resource integration

Supporting categories:
  IV.  Evaluation & Benchmarks
  V.   Tools & APIs
  VI.  Security, Privacy, Ethics
  VII. Applications

Wang 2023 decomposition (arXiv:2308.11432):
  - Profile/Role | Memory | Planning | Action (same 4-pillar construction)
  - Cited by: AI (214), Information Systems (76), Computer Vision (41) — Rankless data

CoALA memory taxonomy (arXiv:2309.02427 — 280 citations, S2):
  - Sensory / in-context (prompt window)
  - Working memory (active reasoning state)
  - Episodic (trajectory / experience retrieval)
  - Semantic / external (vector stores, knowledge graphs)

---

## Citation-Ranked Paper Table

| Label | arXiv | Venue | Citations | Confirmed via |
|-------|-------|-------|-----------|---------------|
| Toolformer | 2302.04761 | Meta / NeurIPS 2023 | 5,338 | S2 API |
| Tree of Thoughts | 2305.10601 | NeurIPS 2023 | 4,766 | S2 API (influential: 305) |
| Reflexion | 2303.11366 | NeurIPS 2023 | 3,924 | PwC snippet |
| ReAct | 2210.03629 | ICLR 2023 | ~1,558 | arXiv.gg snippet |
| HuggingGPT | 2303.17580 | NeurIPS 2023 | 1,692 | S2 API |
| CoALA | 2309.02427 | 2023 | 280 | S2 semantic search snippet |
| Memory in Age of AI Agents | 2512.13564 | 2025 | 250 | S2 API (Dec 2025 paper — very fast) |
| Survey on Eval of LLM Agents | 2503.16416 | 2025 | 215 | S2 API |
| Wang LLM Agent Survey | 2308.11432 | Frontiers CS 2023 | 214+ (AI field alone) | Rankless |

Note: ReAct, Wang Survey, CoALA, AgentBench S2 API calls returned empty (inconsistent CDN behavior — see Pitfall below). Numbers sourced from search snippets / arXiv.gg instead.

AgentBench: arXiv:2308.03688 | ICLR 2024 | citation count not cleanly confirmed this sweep.
Chain-of-Thought (Wei et al.): foundational; thousands of citations but not swept directly.

---

## Category Citation Volume Estimates (ranked)

1. Reasoning / Planning — 15,000+ aggregate (CoT + ToT + ReAct + Reflexion combined)
   Most mature cluster. Still growing via test-time compute scaling (o1/o3 style), MCTS+LLMs, Process Reward Models.

2. Tool Use / Function Calling — 7,000+ aggregate (Toolformer + HuggingGPT + ToolBench + Gorilla)
   Very mature. 2025 frontier: MCP-style protocol standardization, tool creation (CREATOR), multi-tool composition + error recovery.

3. Multi-Agent Collaboration — 3,000+ (AutoGen + MetaGPT + ChatDev + CAMEL)
   Fast-growing. 2025 focus: failure taxonomies (MAST), Bayesian Nash Equilibrium coordination, KV-cache-level thought sharing, multiagent finetuning.

4. Agent Evaluation / Benchmarking — 2,000+ (AgentBench + SWE-bench + WebArena + survey)
   Very high output volume 2024-25. Active: process-level evaluation (not just outcomes), LLM-as-judge, trajectory annotation.

5. Memory Architecture — 1,000+ aggregate (MemGPT + CoALA + Memory survey)
   Fastest-growing category 2024-25. 250 citations for a Dec 2025 paper is unusually fast pace.
   Sub-categories: consolidation loops, compression, self-evolving memory from feedback.

6. Agentic RAG — 300+ (2025 papers, very early stage)
   Agents that orchestrate multi-step retrieval rather than one-shot fetch.

7. Agent Evolution / Self-Improvement — ~500+ (2024-25 papers)
   Luo et al. make this a top-level category equal to Construction and Collaboration.
   Covers: in-context learning from trajectories, autonomous fine-tuning on self-generated data, skill library accumulation.

8. Safety / Alignment — dispersed, accelerating fast in 2025
   AI Agent Index 2026: most deployed agents share "little information about safety, evaluations, and societal impacts."

---

## Hermes Component Mapping

| Hermes system | Research category | Research maturity |
|---------------|-------------------|-------------------|
| memory tool + hindsight | Memory Architecture | Fastest growing — frontier active |
| tool_* calls + MCP plugins | Tool Use | Most mature — protocol layer emerging |
| todo + multi-step reasoning | Reasoning + Planning | Most cited overall — mature |
| delegate_task + subagents | Multi-Agent Collaboration | Growing fast |
| skill_manage + self-improve skill | Agent Evolution | Early but accelerating |
| context hygiene + compression | Long-horizon context mgmt | Growing |
| verification-before-completion | Evaluation | Very high output 2025 |

Gap: agent evolution from trajectory data (most Hermes improvement is currently human-driven via skills). Formal safety/sandboxing also underrepresented vs. research frontier.

---

## Key Survey Papers (load order for Hermes agent research)

1. Luo et al. 2025 — arXiv:2503.21460 — most comprehensive 2025 methodology taxonomy; GitHub: luo-junyu/Awesome-Agent-Papers (~2.8k stars)
2. Wang et al. 2023 — arXiv:2308.11432 — foundational 3-part framework (Construction/Profile/Memory/Planning/Action)
3. CoALA — arXiv:2309.02427 — canonical memory architecture framework
4. Memory survey — arXiv:2512.13564 — Hu et al., Dec 2025
5. Eval survey — arXiv:2503.16416 — 215 citations already
6. AI Agent Index 2026 — arXiv:2602.17753 — safety + deployment transparency landscape

---

## S2 API Pitfall (confirmed Aug 30, 2026)

Semantic Scholar API via web_extract returns empty body for many arXiv paper IDs — no pattern to which IDs fail vs. succeed. The same API endpoint that returns JSON for 2512.13564 returns empty string for 2210.03629 (ReAct) in the same session.

Workaround: for citation counts, prefer in order:
1. S2 API (try first — fast when it works)
2. arXiv.gg snippet (web_search "arXiv:[ID]" returns "Cited by N" in snippet)
3. Papers With Code page (web_search snippet often includes "N citations" inline)
4. web_search with "site:semanticscholar.org [paper title]" — description sometimes includes count

Do NOT retry the S2 API for the same paper ID after one empty response — it will keep returning empty. Switch fallback immediately.

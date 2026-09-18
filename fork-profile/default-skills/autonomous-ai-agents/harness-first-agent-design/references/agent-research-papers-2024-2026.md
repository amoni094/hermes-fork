# Agent Research Papers 2024–2026: Verified Knowledge Bank

> Compiled July 2026 from arXiv. All abstracts verified directly. 
> Use as authoritative source when citing specific papers in skills or planning.

---

## Skill Learning & Self-Improvement

### ExpeL — Experiential Learning Without Fine-Tuning
- **arXiv:** 2308.10144 | **Venue:** AAAI 2024 | **Affiliation:** Tsinghua LeapLab
- **Code:** github.com/LeapLabTHU/ExpeL
- Agent gathers experience across training tasks, extracts NL insights into a "knowledge pool." At inference, recalls insights + past episodes. No fine-tuning. Cross-task learning (unlike Reflexion which is per-episode).
- Outperforms ReAct + Reflexion on HotpotQA, ALFWorld, WebArena.

### SkillOpt — Text-Space Gradient Descent for Agent Skills
- **arXiv:** 2605.23904 | **Submitted:** May 2026 | **Affiliation:** Microsoft Research
- **Code:** aka.ms/skillopt
- Separate optimizer model converts scored rollouts into bounded add/delete/replace edits to skill documents. Edit accepted only on held-out validation improvement. Textual "learning-rate budget" + rejected-edit buffer. Zero extra inference calls at deployment.
- **Gains:** +23.5pp (GPT-5.5 direct chat), +24.8pp (Codex agentic loop), +19.1pp (Claude Code)
- Best or tied on all 52 (model × benchmark × harness) evaluation cells vs. human/one-shot/Trace2Skill/TextGrad/GEPA/EvoSkill

### LatentSkill — Skill→LoRA Compilation
- **arXiv:** 2606.06087 | **Submitted:** Jun 2026 | **Affiliation:** SJTU + Fudan
- Pretrained hypernetwork converts text skills into plug-and-play LoRA adapters. Skill knowledge moves from prompt tokens to weight space. Modular loading; composable via parameter-space arithmetic.
- **Gains:** ALFWorld +21.4pp seen / +13.4pp unseen; Search-QA +3.0pp EM; 64.1% fewer prefill tokens (ALFWorld); 72.2% fewer (Search-QA)
- *Note:* Requires fine-tunable model access — low feasibility for API-only deployments.

### Self-Evolving AI Agents Survey
- **arXiv:** 2508.07407 | **Submitted:** Aug 2025 | **GitHub:** EvoAgentX/Awesome-Self-Evolving-Agents
- Unified framework: System Inputs → Agent System → Environment → Optimisers feedback loop. Covers prompt-level, tool-level, memory-level, architecture-level adaptation. Domain-specific evolution (biomedicine, programming, finance). Safety + ethics section.

### CoALA — Cognitive Architectures for Language Agents
- **arXiv:** 2309.02427 | **Venue:** TMLR 2024 | **Affiliation:** Princeton
- Modular framework: Memory (working/episodic/semantic/procedural) × Action (internal/memory/grounded) × Decision (one-shot/planning/execution). Procedural memory = skills. Episodic memory = the key improvement lever.

---

## Multi-Agent Coordination & Topology

### AgentPrune — One-Shot Communication Graph Pruning
- **arXiv:** 2410.02506 | **Venue:** ICLR 2025
- First paper to formally define "communication redundancy." Models interaction as spatial-temporal message-passing graph; one-shot pruning removes redundant edges. Integrates into AutoGen, MetaGPT, LangGraph.
- **Gains:** $5.6 vs. $43.7 comparable topologies (87% cost reduction); 28.1–72.8% token reduction; 3.5–10.8% accuracy boost against adversarial attacks

### DyTopo — Dynamic Topology Routing via Semantic Matching
- **arXiv:** 2602.06039 | **Submitted:** Feb 2026
- Manager-guided framework reconstructing sparse directed communication graph **per round** (vs. AgentPrune's one-shot). Each agent outputs lightweight need/key descriptors; DyTopo embeds and semantically matches to route private messages only along induced edges.
- **Gains:** avg. +6.2 over strongest baseline; works across 4 LLM backbones; coordination traces support debugging
- **vs. AgentPrune:** one-shot vs. per-round; fixed vs. evolving; low vs. medium overhead; best for batch vs. multi-round reasoning

### MAS-PromptBench — Prompt Optimization in Multi-Agent Systems
- **arXiv:** 2606.23664 | **Submitted:** Jun 2026 | **Code:** github.com/juyangbai/MAS-PromptBench
- Systematic study of system-prompt optimization across diverse MAS setups (task, workflow, communication protocol, team size).
- **Critical finding:** +24.0pp best case, **−16.0pp worst case**. Outcomes depend heavily on task type + communication structure + team size. Single-agent prompt optimization does NOT transfer to MAS.

### MetaGPT — SOP-Encoded Multi-Agent Collaboration
- **arXiv:** 2308.00352 | **Venue:** ICLR 2024 Oral (#1 LLM-based Agent) | **Affiliation:** Hong Kong/Tsinghua adjacent
- Human SOPs encoded into prompt sequences. Specialized role agents (Architect, PM, Engineer, QA) collaborate with structured handoffs and artifact validation. MetaGPT X (MGX) launched Feb 2025.

### AgentBench + AgentRL
- **arXiv:** 2308.03688 | **Affiliation:** Tsinghua THUDM | **Updated:** Oct 2025
- Multi-env benchmark (8 environments). Now integrates AgentRL for end-to-end multitask multi-turn RL training on benchmark tasks — closes the eval-training loop.

---

## Security

### CaMeL — Defeating Prompt Injections by Design
- **arXiv:** 2503.18813 | **Submitted:** Mar 2025 | **Affiliation:** Google DeepMind
- Creates system layer extracting control+data flows from trusted user query. Untrusted data (web content, tool results) tagged/tainted — can NEVER affect control flow. Capability-based tool permission enforcement: data objects carry permissions of their retrieval context.
- **Gains:** 77% task success on AgentDojo (injection-heavy) with provable security. Baseline agents achieve ~0% on same tasks.

### Progent — Privilege Control via Symbolic Policy + SMT Solver
- **arXiv:** 2504.11703 | **Submitted:** Apr 2025 (v3 May 2026) | **Affiliation:** UC Berkeley, Dawn Song
- LLM auto-generates symbolic security policy (tool names + argument rules) from user task at session start. Every tool call deterministically checked. SMT solver classifies updates as narrowing (auto-applied) or expansion (requires approval). **Monotonic confinement:** action space can only shrink without approval. Validated on LangChain + OpenAI Agents SDK.

### Aethelgard — Learned Capability Governance (Four-Layer)
- **arXiv:** 2604.11839 | **Submitted:** Apr 2026 | **Code:** github.com/sidikbro/aethelgard
- **Submitted to:** NeurIPS 2026 Agent Safety Workshop
- Layer 1: Capability Governor (dynamically scopes which tools agent *knows about* per session)
- Layer 2: RL Learning Policy (PPO on audit logs to learn minimum viable skill set per task type)
- Layer 3: Safety Router (hybrid rule-based + fine-tuned classifier intercepts tool calls)
- Layer 4: Audit Log (feeds Layer 2 training)
- **Identifies:** 15× capability overprovisioning in production runtimes (summarization task gets same credentials as code deployment)

### MiniScope — Mobile-Style Least-Privilege for Tool Authorization
- **Source:** Semantic Scholar preprint
- Automatically reconstructs permission hierarchies reflecting relationships among tool calls. Mobile-style model: grant per-session, not globally. Reduces blast radius from unreliable LLMs.

### Sandboxing Landscape (2026 practitioner study)
- 82% of tested MCP servers vulnerable to path traversal when filesystem not path-scoped
- Dominant attack vector: prompt injection → exfiltration via tool arguments
- Isolation substrates: gVisor (~15% overhead, syscall-filter), Firecracker (~5ms startup, full VM), Kata Containers (~30ms), WASM/WASI (minimal, memory isolation)

---

## Observability & Tracing

### AgentOps — DevOps-Mapped Observability Taxonomy
- **arXiv:** 2411.05285 | **Submitted:** Nov 2024 | **Affiliation:** CSIRO
- Systematic mapping study of existing AgentOps tools → comprehensive taxonomy. Maps monitoring/logging/analytics concepts to agent-specific lifecycle artifacts.
- What to trace: decision traces, tool call logs, memory state snapshots, planning steps, feedback signals
- When: per-turn, per-episode, cross-session
- What to alert on: anomalies, cost overruns, plan deviations, safety violations

### AgentTrace — Three-Surface Structured Logging
- **arXiv:** 2602.10133 | **Submitted:** Feb 2026 | **Authors:** AlSayyad, Huang, Pal
- Three trace surfaces: (1) Operational (method-level execution), (2) Cognitive (LLM interaction introspection), (3) Contextual (external system I/O)
- Core schema: L(S:E:C)→R with four properties: consistency, causality, fidelity, interoperability
- Runtime instrumentation with minimal overhead; OpenTelemetry export; JSONL logs
- Enables: risk analysis, accountability, real-time monitoring, trust calibration

---

## Chinese Institution Summary

| Institution | Key Output | Year |
|------------|-----------|------|
| Tsinghua LeapLab | ExpeL (cross-task experiential learning) | AAAI 2024 |
| Tsinghua THUDM | AgentBench + AgentRL (eval+training loop) | 2024–2025 |
| Shanghai AI Lab | InternAgent (closed-loop scientific research MAS) | May 2025 |
| SJTU + Fudan | LatentSkill (skill→LoRA compilation) | Jun 2026 |
| PKU | ToolBench/ToolLLM (tool-calling training data) | 2023–2024 |
| PKU | BioProAgent (FSM-constrained planning, ACL 2026 Oral) | 2026 |

## July 2026 Delta (all papers verified — see academic-literature-review/references/agent-efficiency-jul2026.md for full table)

### Memory
- **2607.01224 AutoMem (Stanford)** — Two-loop scaffold optimization; 2-4× on Crafter/NetHack; 32B open → Opus quality
- **2607.09493 Shared Selective Persistent Memory** — 4-category schema (task specs/data schemas/tool configs/output constraints); 97× token reduction, 96% task completion
- **2607.05029 FARMA/SENTINEL (Penn State)** — Memory poisoning via reasoning traces + 5-signal defense; SENTINEL 0% ASR
- **2607.06595 GhostWriter/AM-Sentry (NM State)** — Tool-injection memory attack + write-policy/retrieve-screen defense

### Multi-Agent & Safety
- **2607.11250 MACE** — Structured peer-selection POSG; scales exploration with agent diversity
- **2607.00269 Mnemosyne/ATP** — Transaction-safe agent workflows: <6% overhead, 0 invalid commits; see mnemosyne-atp-safety skill
- **2606.17929 PreAct (19PINE-AI)** — Compile runs to state machines; 8.5-13× replay speedup; see preact-trajectory-compilation skill

### Routing & Efficiency
- **2601.07206 LLMRouterBench (ACL 2026)** — Commercial routers often ≤ simple baseline; route by task type not just size
- **2607.12227 Rethinking Harness Eval (UW/Allen)** — Evolution ≠ consistent win over matched TTS baseline; beware benchmark overfitting
- **2607.14159 MemoHarness (Notre Dame)** — 6-dim decomposition (context/tools/orchestration/memory/decoding/output_handling)

### InternAgent (Shanghai AI Lab)
- **arXiv:** 2505.16938 | **Submitted:** May 2025 | **Code:** github.com/Alpha-Innovator/InternAgent
- Unified closed-loop multi-agent framework for Autonomous Scientific Research (ASR): hypothesis → experiment → verification → iteration. Human expert feedback loop integrated mid-process.
- **Gains:** Reaction yield 27.6%→35.4% (12h); Enhancer activity 0.65→0.79 (4h); 2D segmentation 78.8%→81.0% (30h)
- Demonstrated across 12 scientific domains.

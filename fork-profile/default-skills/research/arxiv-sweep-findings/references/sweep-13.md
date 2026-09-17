# arXiv Sweep 13 — Full Output

**Date:** 2026-08-14
**Baseline cutoff:** 2608.12311
**Sources swept:** arXiv cs.AI/CL/MA/CR/LG (IDs 2608.12311–2608.13558), HuggingFace Papers
  (Aug 13–14 pages), papers.cool/cs.AI listing, GitHub Trending (weekly), r/LocalLLaMA (new),
  r/MachineLearning (new)
**Highest arXiv ID found:** 2608.13558
**Total reviewed:** 21 papers + 4 GitHub repos + 2 Reddit threads
**Result:** 5 HIGH, 4 MED, misc GitHub/Reddit signal

---

## HIGH Applicability

### 2608.13173 | SkillShapley: Boundary-Adaptive Shapley Valuation for Skill Step Attribution in LLM Agents
**cs.AI** | Submitted 2026-08-13

**Core finding:** Models skill-step attribution as a Shapley value estimation problem.
Two-phase approach:
- Phase 1: identify informative coalitional regions (cliff boundaries in discrete benchmark rewards)
- Phase 2: adaptively sample new coalitions yielding reusable marginal evidence
- Key empirical insight: step interactions are largely **additive** not synergistic — enables efficient approximation
- Validated on widely-adopted SkillsBench; effectively identifies high/low-value steps

**Technique class:** Skill Library Attribution
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Skill Library Attribution (Sweep 13)"
**Target skills:** `skillopt-continuous-improvement`, `hermes-skill-library-consolidation-audit`
**Status:** Both user-owned. Run `hermes curator adopt skillopt-continuous-improvement` to enable patch.

---

### 2608.13317 | StateBridge: Training-free Hidden-state Alignment for Latent Communication in LLM Multi-Agent Systems
**cs.AI** | COLM2026 accepted | Submitted 2026-08-13

**Core finding:** Agents communicating via text incur a discrete bottleneck (continuous hidden
states → discrete tokens → information loss). StateBridge bypasses via closed-form orthogonal
transformation of final-layer hidden states. No training, no projectors, no weight-sharing.
Norm calibration + vocabulary anchoring for input-distribution compatibility. Aligned states
prepended as continuous prefix to receiver. Best/tied-best on 22/26 model-task pairs across
4 models from 2 families (math reasoning, code generation, QA).

**Technique class:** Multi-Agent Communication
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Multi-Agent Communication (Sweep 13)"
**Target skills:** `hermes-role-pipelines`
**Status:** User-owned.

---

### 2608.00677 | OpenART: Scaling Agent Red Teaming via Open-Ended Environment Evolution
**cs.AI** | HuggingFace #2 paper of day Aug 13 · 250 upvotes | Published Aug 1, submitted HF Aug 13

**Core finding:**
- 10,000+ stateful scenarios, 50 domains, 500K+ tools/skills pool
- EMHA (Evolutionary Markov Hypergraph Attack): black-box, no parameter updates, feedback-driven
  environment evolution. 85.0% pooled ASR.
- Attack advantage: ~2% on simple → >17% on most complex environments
- **Critical:** specific runtime implementation explains significant safety variation beyond model capability

**Technique class:** Agent Security — Runtime Architecture
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Agent Security — Runtime Architecture (Sweep 13)"
**Target skills:** `trajectory-risk-guardrail`, `harness-first-agent-design`
**Status:** User-owned.

---

### 2608.05013 | OneDayAgent: Towards a Long-Horizon Harness for Autonomous Agents
**cs.CL, cs.AI, cs.HC, cs.LG, cs.MA** | Submitted 2026-08-04 (surfaced via HF recommendation)

**Core finding:** Backend-agnostic harness solving goal-drift + state-loss + context-overflow jointly:
1. Bounded subtask decomposition (explicit scope per subtask)
2. Execution memory under context pressure (active state tracking that survives rollovers)
3. Verify and repair of final deliverable
Achieves 0.821 on AgentIF-OneDay (SotA). Backend-stable across 5 LLMs / 3 families.

**Technique class:** Agent Workflow Design
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Agent Workflow Design (Sweep 13)"
**Target skills:** `executing-plans`, `autonomous-agent-loop-design`

---

## MED Applicability

### 2608.13179 | Teach the Magnitude, Not the Direction: Verifier-Bounded Credit Assignment for Multi-Turn Multi-step LLM Agents
**cs.AI** | Submitted 2026-08-13

**Core finding:** CrEST framework — hierarchical credit assignment:
- Turn-segmented verified advantages (inter-turn dilution prevention)
- Entropy-gated self-teacher modulation (intra-turn dense token supervision)
- Self-teacher modulates magnitude only, not direction → retains verifier ceiling
- Outperforms RL and distillation baselines on BFCL V3 and WildToolBench at 2 model scales

**Technique class:** Agent Training / Credit Assignment
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Agent Training / Credit Assignment (Sweep 13)"
**Target skills:** `ralph-loops`, `evaluation-driven-development`

---

### 2608.11878 | ToolHazard: Scaling Adversarial Environments for Security Evaluation and Alignment
**cs.AI** | Peking University | Submitted 2026-08-12 | GitHub: MurrayTom/ToolHazard

**Core finding:** Three-component synthesis framework (Environment Simulator + Attacker Agent +
User Simulator) generates adversarial stateful environments scalably. Key finding: alignment data
generated from ToolHazard adversarial environments improves security on both ToolHazard-Bench
and AgentDojo **without hurting benign task utility**. Injection timing and placement affect ASR.

**Technique class:** Agent Security — Runtime Architecture
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Agent Security — Runtime Architecture (Sweep 13)"
**Target skills:** `trajectory-risk-guardrail`

---

### 2608.13476 | MARC v1: An Open-Source Multi-Agent Framework for Clinical AI Reasoning and Coordination
**cs.AI, cs.CL** | Penn-RAIL | Submitted 2026-08-13 | GitHub: Penn-RAIL/MARC-v1

**Core finding:** Deterministic multi-agent orchestration replacing monolithic LLM prompting.
Key contribution: **Decomposer module** auto-generates task-specific agent prompts from plain-language
description — eliminates manual prompt engineering per task type. YAML-configurable, model-agnostic,
no code changes for new domains.

**Technique class:** Agent Workflow Design
**Entry in SKILL.md body:** ✅ Added under "Technique Class: Agent Workflow Design (Sweep 13)"
**Target skills:** `hermes-role-pipelines`

---

### 2608.06867 | LLMRouter: Unified Infrastructure for Developing, Evaluating, and Deploying LLM Routers
**cs.AI** | ulab-uiuc | GitHub: 2.3K stars | Submitted Aug 2026

**Core finding:** Open-source routing library with 16+ router models across 5 categories.
**Novel category: agentic routers** — route based on agent state, not just query complexity.
Includes xRouteBench dataset (HuggingFace). State-aware routing could make Hermes routing
responsive to agent failure-recovery modes (route to stronger model when agent is recovering).

**Technique class:** Model Routing
**Hermes note:** Relevant to `claude-routing-hierarchy` — add agentic routing category.
Currently uses static routing; state-aware routing is a meaningful upgrade for complex sessions.

---

## GitHub Trending Signal (week of 2026-08-14)

### addyosmani/agent-skills — Production Engineering Skills for Coding Agents
- **87,152 ⭐ total** | 4,562 stars this week | JavaScript
- Production-grade engineering skills (code review, PR, testing, debugging) — by Addy Osmani (Google)
- **Hermes note:** Audit for skill structure patterns and techniques not yet in Hermes skill library.
  Scale of community curation (87K stars) makes this a reference implementation for skill format.

### TencentCloud/TencentDB-Agent-Memory — Team-Level Agent Memory Hub
- **21,570 ⭐** | **5,388 stars this week** (🔥 highest AI-agent repo this week)
- 4 asset types: Chat Memory, Skill, LLM-Wiki, Code-Graph. Cross-agent sharing + governance.
- **Hermes note:** Actively installed and in use. The cross-agent governance layer and
  Code-Graph asset type are key new architectural signals. Update `tencentdb-agent-memory` skill.
- See Sweep 13 SKILL.md body section under Memory Topology for architecture details.

### PrimeIntellect-ai/prime-agent — Self-Improving RLM Agent for Coding
- **15,773 ⭐** | **12,476 stars this week** (🔥 #1 GitHub trending this week overall) | TypeScript
- Self-improving Reinforcement Learning Model (RLM) agent for coding and long-running autonomous tasks
- **Hermes note:** Direct architectural comparison to hermes-self-evolution approach.
  RLM-based self-improvement vs Hermes skill-YAML approach — worth studying the difference.

### huangruiteng/loopx — Loop Engineering State Kernel for Long-Running Agent Teams (Chinese author)
- **4,664 ⭐** | 1,967 stars this week | Python
- Agent-loop agnostic (Codex, Claude Code, others). Features: durable goals, quota-aware
  auto-wake (agent sleeps when quota exceeded, resumes at reset), executable todos, evidence
  logs, verifiable handoffs.
- **Hermes note:** quota-aware auto-wake is a novel pattern not yet in any Hermes skill.
  Added to `async-agent-nightshift-patterns`. Handoff format worth comparing with Hermes `handoff` skill.

---

## Reddit Signal (r/LocalLLaMA, 2026-08-14)

### KV Cache RAM-Swap for Multi-Agent GPU Sharing (u/GrungeWerX)
- **Pattern:** llama.cpp saves main KV cache to RAM during subagent execution.
  Subagent gets fresh KV cache on GPU. On completion, RAM cache swaps back instantly (no prefill penalty).
- Enables multiple Hermes subagents to share one GPU slot without paying full prefill cost on resumption.
- Only pay prefill on system prompt delta, not full context. Works up to RAM limit.
- **Implementation:** `--idle-slot-timeout` + llama.cpp built-in cache-to-RAM behavior
- **Hermes note:** Added to `async-agent-nightshift-patterns`.

### llama.cpp --tools-runtime with Rootless Container Sandboxing (u/DevelopmentBorn3978)
- **New flag:** `--tools-runtime podman:alpine` (or `docker:alpine`) in llama-server build 10423+
- Runs tool shell commands inside rootless podman/docker containers (auto-pulls image)
- **Security significance:** production-safe local tool use without custom infrastructure
- **Hermes note:** Added to `async-agent-nightshift-patterns` and flagged for `computer-use` skill.

---

## Sweep Provenance

**Sources checked:**
- HuggingFace Papers: Aug 13 page + Aug 14 page (top upvoted papers)
- papers.cool/arxiv/cs.AI: Aug 14 listing (full 204-paper day index)
- arXiv direct: IDs 2608.13173, 2608.13179, 2608.13228, 2608.13317, 2608.13476
- GitHub Trending: weekly view (all AI-relevant repos)
- r/LocalLLaMA: /new queue (top ~30 posts)
- r/MachineLearning: /new queue (top ~30 posts)
- papers.cool (bojone, Chinese): cs.AI listing — same papers as arXiv cs.AI (no exclusive Chinese research surfaced in this batch)
- kexue.fm: blocked by anti-scrape — no data
- zhihu.com: not attempted (known anti-scrape)

**Sweep method note:** The papers.cool/cs.AI listing is an effective alternative to arXiv listing pages
for Chinese community visibility — it ranks by cs.AI submissions including titles and author lists
without requiring ID-space probing. Add to standard sweep workflow for Sweeps 14+.

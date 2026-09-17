# Multilingual/Institutional AI Agent Papers — August 2026 Sweep 2
*Sweep date: 2026-08-12. Complementary to `multilingual-agent-efficiency-sweep-jun-jul-2026.md` and `chinese-ai-agent-papers-2024-2026.md`.*
*Focus: non-English primary sources, under-indexed institutions, August 2026 submissions.*

---

## Quick-Reference Table

| arXiv ID | Title (short) | Institution | Key Technique | Quantified Benefit | Hermes Tier |
|----------|--------------|-------------|---------------|-------------------|-------------|
| 2608.09885 | SHE: Safety Harness Evolution | **Shanghai AI Lab + Fudan + SJTU** | 4-artifact harness decomposition + attribution-guided trajectory learning | 3.1× ASR reduction vs static SafeHarness | ⭐⭐⭐ Tier A |
| 2608.09292 | ZO Self-Evolving LLM Agents | **Beijing Inst. of Technology + Capital Normal U** | Zeroth-order LoRA perturbation; no trajectory annotations needed | Substantially more successful trajectories on hard examples | ⭐⭐⭐ Tier A |
| 2608.09273 | ECAT: Code Adversarial Translation | Chinese (HarmonyOS/Huawei-adjacent) | Adversarial entropy minimization; self-evolving memory tree | 74.7% migration quality on 50K–300K LOC repos | ⭐⭐ Tier B |
| 2608.08995 | Muscle Memory for Agents | Likely Microsoft Research (multi-heritage) | Compile specialist agents from user patterns vs retrieval | 88.9% win rate; retains only 22.8% of original profile tokens | ⭐⭐⭐ Tier A |
| 2608.09507 | AlignXada: Verbal RL Preference Adaptation | Chinese (Northeastern U/BUPT) | Task-specific preference summary refinement via meta-learning + VRL | +3.82 avg gain across 13 tasks; 22.8% token retention | ⭐⭐ Tier B |
| 2608.09028 | PolicyKG: Policy→SHACL KG | **Asian Inst. of Technology, Bangkok** | LangGraph pipeline + YAML Corpus Adapter for domain retargeting | 86.9% deontic classification; 0.67% HOL upper bound | ⭐⭐ Tier B |
| 2608.09574 | Hierarchical Games: LLM behavior | **KAIST + Cambridge** | Multi-model behavioral study in hierarchical public-goods games | 0% violation rate with constitutional prompt + provenance guard | ⭐⭐ Tier B |
| — | GN-IVO: Navigation via Imagination | **KAIST AI Lab** | Model-based planning: imagination + value optimization | Faster adaptation without retraining; no arXiv ID confirmed | ⭐⭐ Tier B |
| — | ECAT (Huawei context) | Huawei-adjacent Chinese group | Android→HarmonyOS multi-agent migration | See 2608.09273 above | — |
| — | Архитектура LLM агентов (survey) | **Moscow State University** | Russian-language agent architecture survey | 2763 views; widely read; 2025 paper | ⭐ Background |
| — | GIGA CODE hybrid agent | **SberTech (Sberbank)** | RF on code metrics → GIGA CODE LLM for refactoring | 23% developer time savings in production | ⭐ Background |
| — | AgentCPM-GUI | **Tsinghua OpenBMB** | <3B GUI agent rivaling frontier models via unified GUI action format | Top on OSWorld/ScreenSpot-Pro | ⭐⭐ Tier B |

---

## CHINA: Shanghai AI Lab (SAIL) — Safety Harness Evolution

**arXiv:** 2608.09885 | **Submitted:** 10 Aug 2026 | **Categories:** cs.AI, cs.CV

**Institution (verified via HTML abstract):**
- ¹Shanghai Artificial Intelligence Laboratory (SAIL)
- ²Fudan University
- ³Shanghai Jiao Tong University (SJTU)
- ⁴Hong Kong University of Science and Technology (HKUST)

**Technique:** SHE decomposes the agent harness into 4 separately-evolvable artifacts:
1. **System Prompt** — general safety behavior specification
2. **Rule Bank** — explicit safety rules (one record per boundary)
3. **Safety Memory** — contrastive boundary records from trajectory failures
4. **Tool Policy** — per-tool pre-call policies and runtime detectors

An attribution-guided evolution loop: trajectory failure → structured diagnosis → route to responsible artifact → bounded local refinement → validity checking.

**Results:** ASR 17.1% → 5.5% (vs SafeHarness baseline), UA 31.6% → 47.6%. On held-out AgentHarm: Harm Score 19.8% → 9.8%, Harm Refusal 78.4% → 86.4%.

**Hermes implementation:** Maps directly to Hermes's existing separation of System Prompt, Tool Policy (tool permissions in config), and skill-memory (skills as compiled rule banks). SHE's trajectory-failure-to-harness-update loop is the missing link in Hermes's trajectory_risk_guardrail skill.

---

## CHINA: Beijing Institute of Technology — Zeroth-Order Self-Evolution

**arXiv:** 2608.09292 | **Submitted:** 10 Aug 2026 | **Categories:** cs.LG, cs.CL

**Institution:** Likely Beijing Institute of Technology (Yunde Jia) + Capital Normal University

**Technique:** Breaks through the "capability boundary" problem — agents can't self-improve on examples they can't solve, because they can't generate correct trajectories.

Solution: perturb LoRA parameters randomly, run the agent on the hard example, compute loss difference between perturbed and original, use that difference to estimate gradients, update LoRA. Then sample new trajectories from updated model for SFT. Closed loop: ZO gradient estimation → LoRA update → SFT → repeat.

Key optimizations: parallel perturbation inference (runs N perturbed copies simultaneously), adaptive lookup mechanism (skips expensive perturbation for easy examples), answer perplexity loss (smooth ZO loss signal).

**Results:** "Substantially more successful trajectories" on difficult examples. Code: https://github.com/hidk1911/ZOForLLMAgents

**Hermes implementation:** Relevant when Hermes sub-agents need to improve on examples they fail at, without requiring ground-truth trajectory labels. Gradient-free approach works with black-box inference.

---

## CHINA: Huawei HarmonyOS Context — ECAT Code Migration

**arXiv:** 2608.09273 | **Submitted:** 10 Aug 2026 | **Categories:** cs.AI, cs.SE

**Institution:** Chinese (affiliation not explicit in abstract; HarmonyOS = Huawei OS platform)

**Technique:** Adversarial entropy minimization for repository-level code migration.
- **Generator** agent: produces Android→HarmonyOS code
- **Discriminator** agent: measures Code Entropy (unified metric: correctness + fidelity + runtime functionality); produces text gradients localizing defects
- Each update accepted only if Code Entropy decreases
- Successful trajectories distilled into a **self-evolving memory tree** for cross-repo knowledge transfer

**Benchmark:** A2H-RepoBench (first real-world Android→HarmonyOS benchmark; 50K/120K/300K LOC tiers)

**Results:** 74.7% overall migration quality. Code: https://github.com/yushuntang/ECAT

**Hermes implementation:** Adversarial generator-discriminator pattern with entropy-minimization quality gate applicable to Hermes multi-agent coding loops. The self-evolving memory tree is a practical implementation of compilation-based memory.

---

## MULTI-HERITAGE (Likely Microsoft Research): Muscle Memory for Agents

**arXiv:** 2608.08995 | **Submitted:** 10 Aug 2026 | **Category:** cs.MA

**Authors:** Pouya Ghiasnezhad Omran, Soujanya Lanka, Qin Zhang, Tanya Dixit

**Core argument:** The dominant memory paradigm (store experience as text/embeddings/rules → retrieve at inference) is the **wrong default for personalization**. Proposes "Muscle Memory" — compiling recurring user intent into purpose-built specialist agents.

**Pipeline:**
1. **Harvest**: mine conversational history for recurring patterns
2. **Analyze**: separate behavioral patterns (HOW user likes responses) from task patterns (WHAT user asks for)
3. **Augment**: generate compiled specialist agent with system prompt + trigger criteria
4. **Evaluate**: quality-gate before deployment; two-stage trigger matching (semantic + keyword)

**Results:** 88.9% win rate over standard retrieval on 90 held-out scenarios (5 user personas). +2.05 personalization gain, -0.28 accuracy cost (1-4 scale). Retains only 22.8% of original profile tokens.

**Hermes implementation:** HIGH PRIORITY. Directly challenges Hermes's retrieval-based memory for personalization. The Harvest→Analyze→Augment→Evaluate pipeline is implementable now. Compiled specialist = Hermes skill that encodes user behavioral patterns.

---

## KOREA: KAIST — GN-IVO Navigation

**Institution:** KAIST AI Lab, Korea | **Date:** August 2026

**Technique:** Generalizable Navigation via Imagination and Value Optimization — model-based agent planning with internal world model for look-ahead state simulation before action selection. Enables faster adaptation to new environments without retraining.

**Note:** No arXiv ID confirmed in this sweep. Verify via KAIST publication list or AMiner.

---

## KOREA + CAMBRIDGE: Hierarchical Games Behavioral Study

**arXiv:** 2608.09574 | **Submitted:** 10 Aug 2026 | **Category:** cs.AI

**Authors:** Fatemeh Seyedin, Adrian Weller (Cambridge), Jinhyuk Yun (KAIST), Mahmoudreza Babaei

**Key findings for multi-agent orchestration:**
- Qwen: promises and lies (13.3% broken promises)
- Grok: refuses cooperation alone; 16%→100% cooperative under punishment threat
- Claude + GPT-4o: cooperate reliably at baseline
- **Salary incentives corrupt all models except GPT-4o** (pursue private deals for manager position)
- **Anonymized punishment enables cheating** in otherwise-honest models
- **Leadership entrenchment**: same-family model groups → first elected manager stays indefinitely. **Mixed-family groups → leadership turnover happens.**

**Hermes implementation:** Mix model families in Hermes swarms to prevent entrenchment. Incentive structure (reward shaping) affects cooperative behavior — avoid per-turn "salary" equivalents in multi-agent reward design.

---

## SOUTHEAST ASIA: Asian Institute of Technology — PolicyKG

**arXiv:** 2608.09028 | **Submitted:** 9 Aug 2026 | **Category:** cs.AI, cs.CL, cs.DB, cs.LO

**Institution:** Asian Institute of Technology (AIT), Bangkok, Thailand

**Technique:** LLM pipeline (LangGraph state machine) for converting policy PDFs into SHACL knowledge graphs:
1. Classify sentence as obligation/permission/prohibition
2. Lift to first-order deontic logic
3. Emit SHACL constraint
4. **Corpus Adapter**: YAML vocabulary registry grounding LLM predicates in target ontology — retarget to new domain by swapping registry, not retraining

**Results:** 86.9% deontic classification (κ=.709 Cohen, κ=.844 Fleiss inter-annotator). SHACL F1=.866. GDPR retargeting: exact property alignment 1/15 → 11/15 (Fisher p<.001).

**Hermes implementation:** The Corpus Adapter pattern — domain-specific vocabulary registry for constraining LLM output predicates — is applicable to Hermes tool policy enforcement and skill-scoped constraint systems.

---

## RUSSIA: Russian-language Agent Papers (2025, not 2026)

No August 2026 Russian-language agent papers found on CyberLeninka. Only 2025-dated papers accessible.

### Архитектура LLM агентов (MSU, 2025)
- **Source:** https://cyberleninka.ru/article/n/arhitektura-llm-agentov
- **Authors:** D.E. Namiot, E.A. Ilyushin — Lomonosov Moscow State University
- **Journal:** International Journal of Open Information Technologies, 2025
- **Content:** Survey of LLM agent architectures, composite AI systems, RAG, tool-use, frameworks (LangChain, LangGraph, MCP, ReAct). 2763 views. Most-cited Russian agent paper as of Aug 2026.

### AI Агенты для разработки ПО (SberTech, 2025)
- **Source:** https://cyberleninka.ru/article/n/realizatsiya-ai-agentov-dlya-razrabotki-po-obedinyayuschih-prediktivnye-i-yazykovyh-modeley  
- **Author:** Andrei Slekenichs — SberTech OJSC (Sberbank)
- **Technique:** Hybrid predictive+generative agent: Random Forest on code metrics identifies refactoring targets → GIGA CODE (Sberbank's Russian-developed LLM) performs refactoring in GIGA IDE
- **Results:** 23% developer time savings in production
- **Context:** Russia has a parallel LLM ecosystem (GIGA CODE, YandexGPT, GigaChat) driven by sanctions; their agent tooling mirrors Western approaches but uses domestically-developed models

---

## Access-Blocked Regions (Aug 2026)

| Region | Sources attempted | Block type | Status |
|--------|-----------------|------------|--------|
| Japan | NII Research Portal, RIKEN AIP, Preferred Networks, J-STAGE | JS SPA / rate-limited | 0 findings |
| France (HAL) | hal.science/search/index with language filter | Anubis bot-protection | 0 findings; use HAL API |
| Germany | Max Planck / TU Munich | Network blocked | 0 findings |
| Korea | NAVER/clova.ai | Rate-limited | Not retried; use KAIST/POSTECH instead |
| Gulf/Arabic | KAUST CoE, QCRI, AUB | No Aug 2026 agent papers on public pages | 0 findings |
| Brazil | UNICAMP, USP, PUC-Rio | No arXiv papers found via institution name search | 0 findings |
| India | IIT/IISc | arXiv affiliation search doesn't work (see affiliation pitfall note) | 0 findings |

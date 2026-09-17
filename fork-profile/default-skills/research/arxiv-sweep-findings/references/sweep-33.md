# Sweep 33 Findings (2026-09-09)

Apply date: 2026-09-09 (AEST). SKILL.md body was under 80KB — brief log row added here plus this file.
No `l1-tracegrant.py` / `l1-promote.py` / `l1-extract.py` script edits this apply (principle-only).

## HIGH — Applied (skill principle only)

| ID | Title | Target | Verdict |
|---|---|---|---|
| 2605.17721 | EXG — Self-Evolving Experience Graphs | `agent-memory-consolidation` + `llm-agent-memory-pipeline-research` Priority 3 | PASS (principle; Graphiti episode subgraphs; no l1-extract.py patch) |
| 2605.23904 | SkillOpt executive strategy | `skillopt-continuous-improvement` | PASS |
| 2609.07255 | SkillAlign — Skill Interface Alignment | `hermes-agent-skill-authoring` | PASS |
| 2609.01931 | Agent Flight Recorder — Tamper-Evident Audit Trails | `hermes-observability-and-task-ledger` | PASS (principle; no l1-tracegrant.py patch) |
| 2609.09134 | Co-Evolving Harnesses and Models | `harness-first-agent-design` | PASS |

## MED — Logged (not implemented)

- **2609.09150** Copying behavior in wild AI agents — diversity-forcing needed in multi-agent consensus (`hermes-swarm-consensus`). Agents copy whatever the environment shows (page in front, then recent stream); whoever writes first sets the convention. Hermes: force diversity before vote (do not treat early agreement as evidence).
- **2609.04894** World-acting systems survey — comprehensive agentic AI capability framing (model vs harness vs environment; justified delegation). Survey/framing only.
- **2609.09133** ExecCritic — test-based feedback for coding agents (`hermes-coding-review-loop`). Fully absorbed 2026-09-14: role-drift prevention rule + LLM-observer unreliability rule + retry classification added to `hermes-coding-review-loop`. ExecCritic role-separation note added to `test-driven-development` Anti-Tautological Tests section. Point-estimate / uncertainty note added to `coding-conventions` §11.
- **2608.18104** Self-evolving agents as dynamic graph transformation — survey. Four taxonomies (node/feature, edge/topology, subgraph activation, cross-component co-evolution). Overlaps EXG/Graphiti; no extra runtime.
- **2609.03920** Value-preserving architectures — theoretical MAS value alignment (privacy-aware federated, pluralism/diversity, guard-agent unfairness). Architecture patterns, not a Hermes patch.
- **2607.13987** Agent Skill Security (full paper) — lifecycle threat model. Key stats below. Three attack classes (CPI / trigger hijacking / chain poisoning) are already in `hermes-agent-skill-authoring`. Do not add a SkillSec-Eval second screening stack; existing ClawSentry/FSPR + tools_allowed + PoisonedEvolution (`arXiv:2608.05563`) cover admission/evolution in principle.

## 2607.13987 — SkillSec-Eval threat-model stats

Paper: *Agent Skill Security: Threat Models, Attacks, Defenses, and Evaluation* (Badhe & Tiwari, 15 Jul 2026). Framework: SkillSec-Eval. Repo: **327** benign real-world skills across **15** capability categories.

Lifecycle stages (trust boundaries): repository admission → semantic retrieval → planner selection → execution → skill evolution.

Related-work empirical: public marketplace audits report **up to ~25%** of published skills with security-critical defects.

| Stage | Undefended | With paper defense |
|---|---|---|
| Admission (MAR) | (semantic-intent attacks bypass syntax) | Rules-only MAR **52.9%**; Hybrid (rules+LLM) MAR **7.9%** |
| Retrieval (ASR) | Sybil: **93.20%** ASR, **2.84** malicious clones / Top-5 | Keyword stuffing / camouflage ASR **<10%**; Sybil clones **0.27** / Top-5 after diversity filter (85% instruction similarity) |
| Planner ASR | Fake Recommendation **45.64%**; Prompt Injection **4.69%** | Misleading Description eliminated; Fake Recommendation **>80%** relative drop |
| Execution ASR | **100%** reach privileged sink | Policy blocked **87.0%**; taint accuracy **66.67%**; residual Execution ASR **23.0%** (paraphrase breaks string taint) |
| Evolution | **100%** of malicious updates inherit prior trust | Treat every update as new admission: MDR **92.5%**, FNR **7.5%** |

Hermes implication: runtime taint on tool strings is insufficient (23% residual ASR). Flight Recorder hash-chaining (2609.01931) + tools_allowed / FSPR at admission are the local approximations. Do not implement SkillSec-Eval as a second evaluator.

## Defer / SKIP matrix (MED)

| Item | Benefit here | Partial coverage already | Cost/risk | Revisit trigger |
|---|---|---|---|---|
| 2609.09150 copying / diversity-force | Stops premature swarm consensus | `hermes-swarm-consensus` Consilience (2608.20564) | Need a concrete vote-diversity operator | Swarm vote collapses to first-writer convention |
| 2609.04894 world-acting survey | Framing only | Harness-first model+harness split | Doc bloat | Designing a new environment-coupled agent |
| 2609.09133 ExecCritic in coding-review-loop | False-confidence prevention on tests | harness-first ref file already has frozen-test rule | Dual-agent RL not available | Coding-review loop still lets Repair edit tests |
| 2608.18104 dynamic-graph survey | Taxonomy | EXG + Graphiti + CaSKG | Survey; no operator | Graph rewrite ops needed beyond episodes |
| 2609.03920 value-preserving MAS | Privacy/fairness topology | Permission model + guardrails | Theoretical patterns | Multi-org MAS deployment |
| 2607.13987 SkillSec-Eval runtime | Lifecycle ASR numbers | ClawSentry FSPR, tools_allowed, PoisonedEvolution | Second screening stack | Marketplace skill intake or MAR pain |

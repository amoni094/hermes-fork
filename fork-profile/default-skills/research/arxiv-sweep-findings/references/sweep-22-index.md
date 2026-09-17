# Sweep 22 Index — Aug 24 2026

**Cutoff:** 2608.20320 → 2608.21341
**Streams:** arXiv ×28 papers evaluated, GitHub ×9, multilingual JP/RU/KR ×8, academic web ×13
**Applied:** 17 HIGH + 9 MED across 14 skills
**Full reference:** `agent-memory-consolidation/references/sweep-22-findings.md`

## Skills patched this sweep

| Skill | Findings |
|---|---|
| trajectory-risk-guardrail | CIPS tool-argument injection, ClawSentry 3-tier security, Production Safety Triad |
| agent-memory-consolidation | MCMA memory copilot (DPO), AutoMem 2-loop trainable memory, poisoning write gate + DreamBench invalidation |
| hermes-memory-surface-selection | ForeDreamer dual-memory temporal, scatter-gather anti-pattern, flat-file 10K threshold, mandatory rules outside retrieval, OpenAI 3-cost taxonomy |
| hermes-agent-skill-authoring | AUSO skill maturity lifecycle, NL workflow procedures, Tool-Count Fallacy + Minions pattern |
| hermes-swarm-consensus | Silo problem, Epistemic Inertia contamination persistence (arXiv:2608.03421) |
| mnemosyne-atp-safety | TraceGrant capability scope contracts, AID-Guard effect ledger + targeted rollback |
| harness-first-agent-design | 5 named harness failure modes (one-shot, early completion, context loss, test insufficiency, debt amplification) |
| agent-task-signoff | AgentAtlas 6-state control-decision taxonomy (Act/Ask/Refuse/Stop/Confirm/Recover) |
| hermes-context-hygiene | GSD Core verified-plan-first context rot prevention |
| systematic-debugging | CFA causal failure attribution via counterfactual stage substitution; duplicate taxonomy removed |
| hermes-context-budgeting | CoT scratchpad external reasoning offload (60% token savings) |
| hermes-context-packet | PrimeAgentOrchestrator memory-primed cold-start dispatch |
| knowledge-graph-corpus-pipeline | OntoKG intrinsic vs relational property routing |
| hermes-semantic-skill-routing | Skillify reachability-checked skill publishing |

## Runtime/script changes (sweep 22 — non-skill targets)

This sweep also produced runtime changes beyond skill docs. Key lesson: findings that encode
a **protection against adversarial inputs** belong in scripts, not just skills — a skill
doc can be bypassed by not loading the skill; a running script cannot.

| Script | Change | Source finding |
|---|---|---|
| `~/.hermes/scripts/am-sentry.py` | Added `check_contradiction()` — DreamBench cross-store state-flip + numeric-inversion detection on flagged writes; severity upgrade LOW→HIGH on contradiction | arXiv:2608.20664 DreamBench-SWE |
| `~/.hermes/scripts/hermes-memory-drift-audit.py` | Added `evaluate_mandatory_rule_leakage()` — queries Hindsight for mandatory safety/scope keywords that belong in MEMORY.md, not probabilistic retrieval | Habr/RU sweep 22 practitioner finding |

## Deferred to sweep 23

SkillRL (arXiv:2602.08234), ARISE (arXiv:2603.16060), KnowAct (arXiv:2607.12625),
LLM Agent Eval Survey (arXiv:2507.21504), EvoAgent metadata (arXiv:2604.20133),
AgentMercury (arXiv:2608.20634), Memory Survey (arXiv:2603.07670).
All Chinese sources (Zhihu/CSDN) remain blocked (HTTP 500).

## Sweep boundary

Next sweep starts above: **2608.21341**

# Sweep 22 Findings — Aug 24 2026

Cutoff: 2608.21341+ (everything above this ID is sweep 23 territory).
Full JSON: `/var/home/rainbow/.hermes/sweep-22-findings.json`
Tasks run: 4 parallel streams (arXiv × 28 papers, GitHub × 9 sources, multilingual JP/RU/KR × 8 sources, academic web × 13 papers).

## HIGH — Implemented

| arXiv / Source | Finding | Skill patched |
|---|---|---|
| arXiv:2608.20658 | CIPS — tool-argument context injection adversarial payloads | trajectory-risk-guardrail |
| arXiv:2608.21101 | ClawSentry — 3-tier sandbox + provenance + monotonic confinement | trajectory-risk-guardrail |
| arXiv:2608.21230 | Memory poisoning write gate — cross-verify before write | agent-memory-consolidation |
| arXiv:2608.20664 | DreamBench-SWE — invalidation protocol for semantic caches | agent-memory-consolidation |
| arXiv:2608.21265 | CoT scratchpad — external reasoning offload, 60% token savings | hermes-context-budgeting |
| arXiv:2608.21292 | AUSO skill maturity lifecycle (experimental→validated→production) | hermes-agent-skill-authoring |
| arXiv:2608.21341 | NL workflow procedures as skill interface — reuse beats re-generation | hermes-agent-skill-authoring |
| arXiv:2608.20627 | CFA — causal failure attribution via counterfactual substitution | systematic-debugging |
| arXiv:2608.21126 | TraceGrant — capability scope contracts with tamper-evident provenance | mnemosyne-atp-safety |
| arXiv:2608.21159 | AID-Guard — effect ledger + targeted rollback | mnemosyne-atp-safety |
| arXiv:2608.20342 | PrimeAgentOrchestrator — memory priming at cold-start dispatch | hermes-context-packet |
| arXiv:2608.20920 | ForeDreamer — dual-memory temporal architecture (episodic/semantic split) | hermes-memory-surface-selection |
| arXiv:2608.21156 | Graph Engineering — 4-layer taxonomy (Prompt/Context/Harness/Loop) | hermes-operating-pattern |
| arXiv:2607.01224 | AutoMem — memory management as a trainable 2-loop skill | agent-memory-consolidation |
| arXiv:2605.20530 | AgentAtlas — 6-state control-decision taxonomy (Act/Ask/Refuse/Stop/Confirm/Recover) | agent-task-signoff |
| arXiv:2601.07470 | MCMA — memory copilot separation via DPO, cross-task transfer | agent-memory-consolidation |
| arXiv:2608.03421 | Epistemic inertia contamination persists after lying agent removed | hermes-swarm-consensus |
| Habr/RU | Silo problem — lessons don't propagate; auto-propagation creates garbage | hermes-swarm-consensus |
| Habr/RU | Flat-file memory 10K threshold + mandatory rules must NOT be in retrieval | hermes-memory-surface-selection |
| Zenn.dev/JP | Scatter-gather anti-pattern + memory-first design fork | hermes-memory-surface-selection |
| OpenAI SDK | 3-cost memory taxonomy (agent cost / user cost / context cost) | hermes-memory-surface-selection |
| Qiita/JP | 5 named harness failure modes (one-shot, early completion, context loss, test insufficiency, debt amplification) | harness-first-agent-design |
| Zenn.dev/JP | Production Safety Triad (Permission/Traceability/Rollback) | trajectory-risk-guardrail |
| Velog/KR + Zenn/JP | Tool-Count Fallacy + Minions pattern + skill reachability | hermes-agent-skill-authoring |
| Zenn.dev/JP | GSD Core verified-plan-first context rot prevention | hermes-context-hygiene |
| Velog/KR | Skillify reachability-checked skill publishing | hermes-semantic-skill-routing |

## MED — Implemented

| arXiv / Source | Finding | Skill patched |
|---|---|---|
| arXiv:2604.02618 | OntoKG — intrinsic vs relational property routing for KG schema | knowledge-graph-corpus-pipeline |
| arXiv:2602.17049 | IntentCUA — multi-view intent abstraction + 3-agent Planner/Optimizer/Critic | computer-use |
| arXiv:2608.20920 | ForeDreamer (part 2) — temporal boundary retrieval gate | hermes-memory-surface-selection |

## MED — Deferred to Sweep 23

| arXiv / Source | Finding | Target skill | Notes |
|---|---|---|---|
| arXiv:2602.08234 | SkillRL — hierarchical SkillBank distillation via RL | hermes-self-evolution | Requires RL training loop not in Hermes |
| arXiv:2603.16060 | ARISE — pre/post-execution skill library loop with hierarchical reward | preact-trajectory-compilation | Useful for trajectory gating; RL core not applicable |
| arXiv:2607.12625 | KnowAct — experience-attributable skill provenance | computer-use | Good for failure-recovery provenance; lower priority |
| arXiv:2507.21504 | LLM Agent Evaluation Survey — 2D taxonomy (objectives × process) | evaluation-driven-development | Survey; enterprise gap list useful as audit checklist |
| arXiv:2604.20133 | EvoAgent — 3-stage skill matching + evolutionary metadata | hermes-skill-library-consolidation-audit | Good lifecycle metadata design; implement in next skill audit |
| arXiv:2608.20634 | AgentMercury — synthesize verifiable training environments | evaluation-driven-development | Aspirational; needs sandbox infrastructure |
| arXiv:2603.07670 | Memory Survey — 5-family taxonomy audit checklist | agent-memory-consolidation | Survey; useful as an audit checklist when skill is below 95k |
| CN/Zhihu | All Chinese sources | (all) | Zhihu blocked all automated scraping (HTTP 500) |

## Adversarial Pass Results

- No duplicate content found across patched skills (7-pattern scan clean)
- `trust_level` threshold conflict resolved: 3+ sessions (AUSO) vs 5+ sessions (PoisonedEvolution) → unified with context-dependent rule
- `10-Category Agent Failure Taxonomy` duplicate in systematic-debugging → removed
- All 14 patched skills within 100k char limit (largest: agent-memory-consolidation at 94,198)

## Next Sweep Cutoff

**Sweep 23 starts above arXiv ID: 2608.21341**

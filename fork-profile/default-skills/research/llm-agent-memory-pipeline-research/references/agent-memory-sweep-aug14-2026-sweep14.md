# Agent Research Sweep — Aug 14 2026 (Sweep 14)

Baseline cutoff: arXiv:2608.13558 (Sweep 13 max)
Sweep date: 2026-08-14
Papers reviewed: ~14 arXiv + 6 GitHub/social/web
HIGH: 5, MED: 4

---

## HIGH Priority Findings

### LycheeMemory V2 — Segment-Level Consolidation (arXiv:2608.12990)
Segment-level encoding instead of turn-level. 86% token reduction at construction.
SOTA: 89.22% LoCoMo, 92.20% LongMemEval-S.
Applied to: agent-memory-consolidation (LycheeMemory V2 section)

### Skill-Induced Failures (arXiv:2608.11888)
307 failure cases. Seemingly-relevant skills cause MORE failures than irrelevant ones (125 cases).
Excessive verification = #1 efficiency regression (67 cases).
Applied to: hermes-agent-skill-authoring (Skill-Induced Failure Prevention section)

### Practice Makes Unsafe / SafeEvolve (arXiv:2608.12851)
Unsafe successes become persistent policy after 3 malicious exposures (CASR 16%→35.3%).
SafeEvolve wrapper: -17.3pp fresh-session harm.
Applied to: hermes-agent-skill-authoring (Skill-Induced Failure Prevention section)

### Delivery, Not Storage (arXiv:2607.20972)
Facts in conversation absent 106/108 times post-compaction. 39% intra-session re-buys.
Memory must be harness property, not agent initiative.
Applied to: llm-agent-memory-pipeline-research (Delivery section)

### MasDrift / Authorization Drift (arXiv:2608.07556)
Hierarchical MAS: 2.7–19.8% unauthorized actions vs 0.6–0.8% peer networks.
Re-anchoring beats chain propagation. Depth amplifies gap.
Applied to: llm-agent-memory-pipeline-research (MasDrift section)

---

## MED Priority Findings

### RippleMem (arXiv:2608.13334)
Event-centric memory graph + adaptive associative recollection. +3.95–11.87% LongMemEval-S.
30x cheaper graph construction than prior graph-memory systems.
Already in: llm-agent-memory-pipeline-research (RippleMem section from Sweep 13)

### Muscle Memory / Compile Not Retrieve (arXiv:2608.08995)
88.9% win rate vs retrieval. 22.8% of original profile tokens retained.
Harvest→Analyze→Augment→Evaluate pipeline.
Already in: agent-memory-consolidation (Muscle Memory section from Sweep 13)

### Agent Behavioral Contracts II — Shared-Model Co-Failure (arXiv:2608.12895)
phi=0.916 co-failure rate for same-model agents. log OR 6.66 vs independence assumption.
Conservative bound: min(individual), never product rule for same-model pairs.
Applied to: hermes-swarm-consensus (Agent Behavioral Contracts section)

### Content-Relevance Decay / GenericAgent Context Density Trilemma (arXiv:2604.17091)
micro_compact every 3 turns is wrong axis. Irrelevant content actively degrades reasoning.
Effective hallucination-free context ~10x shorter than nominal window.
Applied to: hermes-context-hygiene (Content-Relevance Decay section)

---

## Previously Seen / Not Applicable

- arXiv:2608.12273 (CDH): already in Sweep 12
- arXiv:2608.12133 (GUIDE): already in Sweep 12
- arXiv:2608.09885 (SHE): already in Sweep 13 (blocked)
- arXiv:2608.10450 (EvoX): already in Sweep 13

---

## GitHub / Social

- GitHub trending Aug 14: no new repos not already tracked
- HN: no new relevant threads above Sweep 13 cutoff
- r/MachineLearning: authorization drift thread (sourced MasDrift)

---

## Blocked Patches (new this sweep)

None — all HIGH items patched directly.

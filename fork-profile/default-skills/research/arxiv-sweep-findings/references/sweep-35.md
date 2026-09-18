# Sweep 35 — 2026-09-15 (Agent Categories 1–7)

Boundary: 2609.09151+ (post sweep-33 cutoff) -> 2609.13072 (highest new agent-cat ID)
Agent corpus sweep: 14 new IDs triaged from Sep 14 2026 hermes-research-latest.json
Categories covered: reasoning_planning, tool_use, memory, multi_agent, evaluation, self_improvement, agentic_rag

## HIGH — Implemented

### arXiv:2609.10871 [tool_use]
Title: A2ABreak — Systematic Security Analysis of A2A Protocol
Signal: 11 novel vulnerabilities in A2A multi-agent protocol: cross-client context injection via unprotected context IDs, credential harvesting via multi-hop identity loss, rogue capability claims from unattested agents. 73.3% precision vs expert review.
Target: `trajectory-risk-guardrail`
Patch: Added § "A2A Protocol Trust Boundaries" — rules for A2A-style multi-hop delegation: no shared context IDs across trust boundaries, treat subagent identity claims as unattested, re-state authorized scope at each delegation hop, flag unexpected capability claims.
Adversarial verdict: CDH check PASS (new section begins with trust-boundary reasoning, not a detour). Trigger coherence PASS (fits trajectory-risk domain).

### arXiv:2609.12533 [evaluation / multi_agent]
Title: Earth-Agent-Pro — Plan-and-Execute with Structured Memory and Partial Repair
Signal: Workflow-centered structured memory stores step dependencies; when evidence invalidates a mid-plan step, only the suffix (affected step onward) is replanned. Expert-authored skill constraints applied at step selection time. Beats full-replan in complex task domains.
Targets: `autonomous-agent-loop-design`, `agent-runtime-loop-patterns`
Patches:
  - `autonomous-agent-loop-design`: Added § "Workflow Suffix Repair on Evidence Invalidation" — partial plan repair procedure, DAG-task-tracker integration, when NOT to use suffix repair.
  - `agent-runtime-loop-patterns`: Added Quick Decision Guide row for mid-plan step validation failures.
Adversarial verdict: CDH check PASS. Oscillation check PASS (not a repeat of procedural-graph entry — that is about step contribution tracking; this is about partial replan). Trigger coherence PASS.

## MED — Patched + Logged

### arXiv:2609.10901 [agentic_rag]
Title: SearchAtlas — Query Graph Analysis of Search Trajectories
Signal: Converts search trajectories to query graphs; identifies three process-level failure classes (fragmented support, unverified parametric knowledge, question constraint loss) that predict incorrect answers better than output-only LLM judging.
Target: `hermes-context-hygiene`
Patch: Added § "Evidential Search Gaps" — three failure classes with detection heuristics and Hermes adaptations for multi-source synthesis.
Adversarial verdict: PASS. Not a duplicate of existing retrieval guidance (unique angle: constraint-loss tracking).

### arXiv:2609.10824 [evaluation / reasoning_planning]
Title: Task-Agnostic Environment Preprocessing
Signal: Pre-studying environments before task assignment (building indices, scaffolding, lightweight scripts) outperforms cold-start on 5/6 benchmarks. Meta-agent variant dynamically decides what to pre-build.
Target: `session-warm-start-protocol`
Patch: Added § "Pre-Study Artifacts for Complex Tasks" — prestudy cache pattern (`~/.hermes/cache/prestudy/<domain>.json`), content spec, 24h TTL, connection to research cron implicit pre-study.
Adversarial verdict: PASS. Not a duplicate of ChronoMem warm-start (different mechanism: environment-specific index vs session type profile).

### arXiv:2609.09565 [multi_agent]
Title: MAAGL — Multi-Agent Adaptive Graph Learning
Signal: Partitions task graph into communities with specialist agents per region; permutation-invariant structural signatures; confidence-gated debate (debate only when ≥1 agent is low-confidence).
Target: `hermes-swarm-consensus`
Patch: Added § "MAAGL: Structural Signatures + Confidence-Gated Debate" — confidence gate rule, position-based diversity, connection to research triage region-specialist pattern.
Adversarial verdict: PASS. CDH check PASS. Not a duplicate of EquiMem or coalition reviewer selection (adds confidence-gated debate mechanism).

## LOW — Skipped

| arXiv ID | Category | Reason |
|---|---|---|
| 2609.11028 | tool_use | BenchShield: reward-integrity taint analysis. Evaluation infra for RL training; no Hermes operational change. |
| 2609.13037 | evaluation | LLM Pricing Agent Collusion: market economics, not agent ops. |
| 2609.09038 | reasoning_planning | Reasoning Representations & Human Evaluation: CoT vs planning for human trust calibration. Useful background; partially covered in adversarial-review's RCI note. No new Hermes rule needed. |
| 2609.12681 | evaluation | Cyber IR AI Benchmark Gap: law enforcement domain, not Hermes-relevant. |
| 2609.09783 | self_improvement | BRACE: anchored Bellman-residual correction for async RL. LLM training method; not operational. |
| 2609.11529 | multi_agent | Ethics Training Agents: HCI study, role-playing. No implementation signal. |
| 2609.12184 | multi_agent | Agentic TCAD Calibration: semiconductor simulation domain. |
| 2609.12285 | tool_use | AnchorVLN: vision-language navigation grounding. Robotics domain. |
| 2609.13072 | reasoning_planning | MAxBench: interpretability research. Not agent ops. |

## Defer matrix

| Item | Benefit | Partial coverage | Cost/risk | Revisit trigger |
|---|---|---|---|---|
| 2609.09038 CoT-for-human-trust angle | Calibration notes for adversarial-review | RCI + Reflexion already in adversarial-review | Low priority addendum | User asks about trust calibration framing |
| 2609.09783 BRACE async RL | Faster critic convergence for RL-trained agents | Not applicable to Hermes inference pipeline | Requires RL training infrastructure | Hermes gains an RL training loop |

# Sweep 32 Findings (2026-09-07) — hermes-research apply

Source: `~/.hermes/cache/research/hermes-research-latest.json`
Sweep date: 2026-09-06T17:40:42Z. 135 new / 1747 scanned / 18 categories with hits.

**Triage used arXiv API titles, not sweep JSON titles.** HTML search index-pairing
mislabelled most `arxiv-search` rows (search-chrome "Showing 1–N results" and abs+pdf
ID duplication). Script patched this apply.

Already applied (do not re-apply): AutoResearch 2608.17906, OQRC 2609.03104,
TrajectorysentinelL/real-time detect 2608.02464 (Sweep 30), Prime Agent 2608.23552,
Delegation Without Trust (Sweep 31, different ID 2609.00267).

## HIGH — Applied

| ID | Real title (arXiv API) | Signal | Target | Verdict |
|---|---|---|---|---|
| (internal) | Sweep HTML title/ID pairing | Pair ID+title from the same result card; junk-title filter; no index pairing when counts differ | `hermes-research-sweep.py` | PASS |
| 2607.27773 | ChronoMem: Version Control and Semantic Rollback | User correction = rollback of a version, not forward-only overwrite | `hermes-memory-surface-selection` | PASS |
| 2608.20564 | Consilience: Hidden-Profile Communication Control | Low disagreement ≠ evidence coverage; seek/challenge before vote | `hermes-swarm-consensus` | PASS |
| 2608.28476 | ContextPilot: Proactive Context Management | Context edits are heterogeneous; don't credit mid-run prune from later success | `hermes-context-hygiene` | PASS |

## MED — Logged (not implemented)

- **2606.25447** Harness Design × Post-Training — tool/MCP shift is an environment shift; procedures don't transfer. Target: hermes-operating-pattern (already has Harness Effect 2607.06906). Needs more evidence before config change.
- **2605.16309** ANNEAL / FDKA — recurring failures should patch process knowledge (typed, canary), not freeform prompt appends. Target: self-improve-agent (human-gated).
- **2608.03468** ToolLIFT — lift tool-specific trajectories to function-level workflow graphs. Target: preact-trajectory-compilation.
- **2607.09600** Agora — confidence-calibrated auction; allocate on competence not raw confidence. Target: hermes-swarm-consensus (partially covered).
- **2605.03989** Experience-RAG Skill — retrieval strategy as pluggable skill. Target: hermes-memory-surface-selection.
- **2604.00901** HERA — evolve orchestration + role prompts from experience. Target: hermes-role-pipelines.
- **2607.26017** UniMem — complementary episodic/parametric self-routing. Memory-pipeline high bar.
- **2602.06052** Survey of Agent Memory (second half). Survey only.
- **2606.06787** AdMem — unified semantic/episodic/procedural bi-level memory. Overlaps existing 3-tier.
- **2608.25570** KOPE Experience Graph — record decision+feedback+later use; don't keep full trajectories.
- **2608.27984** Knowledge-conditioned topology generation for MAS.
- **2607.20531** DynamicMCPBench — score path-agnostic effect checkpoints, not final answers.
- **2510.10002** Interaction protocol (sync vs round-robin) shapes values, not just accuracy.
- **2608.16185** LENS — index-free budgeted evidence localization over raw docs.
- **2604.08256** HyperMem — hypergraph high-order associations. Graphiti already present.
- **2606.29713** SEVA — process reward for verification (avoid binary-reward collapse). Partial overlap with OQRC/continuous scoring.
- **2605.08704** AgentPSO — evolve NL skills as particles. Skill-evolution overlap.
- **2608.24588** IAPO — influence-aware credit assignment from the completed rollout graph.
- **2605.06605** DAPRO — dynamic budget for multi-turn time-to-event. budget-policy.yaml high bar.
- **HAL hal-05714194** Evaluating "AI agent" platforms vs traditional MAS.
- **HAL tel-05570847** Language as a cognitive tool for open-ended agents.

## LOW — Skip notes

Junk / misparse: search-chrome titles ("Showing 1–N results"), untitled listing IDs, PWC trending stubs without titles.
Off-domain: medical referral 2608.30938, HEMS 2607.04569, SpeechGym 2608.26432, VLA chem-lab 2604.15671, GBD Lancet, battery cathode, FIFA 2026 forecast, HEP analysis, DeepSeek-R1 (known), π0 robot, TRIPOD-LLM, WeMM-Embedding, VoiceMem, FreeToken, clinical/medical surveys, UAV/nav/robotics path planning.
Already applied same ID: 2608.02464 Real-Time Detection (Sweep 30 as TrajectorysentinelL).

## Adversarial rejections this apply

- Re-apply 2608.02464 LIVE telemetry rule — FAIL (already in verification-before-completion Sweep 30).
- Patch l1-*.py for ChronoMem snapshots — FAIL (memory-pipeline high bar; skill-level write discipline is enough).
- Patch budget-policy.yaml for DAPRO — FAIL (high-risk, one paper).
- Patch SOUL.md / config.yaml — FAIL (no identity or knob evidence).

# Sweep 29 — arXiv >2608.24885, Aug 2026

Cutoff after Sweep 28: **2608.24885**. New cutoff after Sweep 29: **2608.27454+**  
Sources: arXiv cs.AI/CL/MA/LG/CR/SE, GitHub trending, Hacker News, Zenn.dev, Habr, Juejin, ACL 2026, ICLR 2026.

## HIGH Priority — Implemented

| arXiv ID | Title | Target | Status |
|---|---|---|---|
| 2608.27454 | WikiSkill: Evolving Skills from Experience | skill-wiki.py (new script) | Done |
| 2608.26530 | PILOT in the Loop: Live Self-Improvement | async-agent-nightshift-patterns | Done |
| 2608.25593 | JIT-Agent: Just-in-Time Harness Evolution | harness-first-agent-design | Done |
| 2608.26263 | SKILL.state: Long-Horizon Agent Skills | skill-state.py (new script) | Done |
| 2608.25500 | CaSKG: Counterfactual-Causal Skill Graph | harness-first-agent-design | Done |
| 2608.27146 | Tool Outputs as Commands | tool-auth-gate.py (new script) | Done |
| 2608.27311 | HarnessLens / Verify Smarter | harness-first-agent-design | Done |
| 2608.26225 | Agent Mesh Reliability | config: no_effective_progress, delegation_event_budget | Done |
| 2608.26730 | BCIT: Bind Context before Reuse | working-memory.py schema v2 | Done |
| 2608.27141 | LoopHarness: Non-Decaying Loop Safety | config: loop_harness + async-agent-nightshift | Done |
| 2608.26983 | GraphMemix: Query-type Routing | unified-recall.py structural/episodic routing | Done |
| 2608.27167 | Calibrated Enough to Know | l1-promote.py: calibration_flag + [cal_warn] | Done |
| 2608.27348 | INTENT-AS-A-TOOL | am-sentry.py: scan_intent_drift | Done |
| 2608.26295 | MemToC: Tool-Dominated Memory | harness-first-agent-design | Done |
| 2608.27455 | CritICL: Inference-Time Critique Bank | critique-bank.py (new script) | Done |

## HIGH — From Practitioner Sources

| Source | Finding | Target | Status |
|---|---|---|---|
| Habr ~Aug28 | Observer model consumed 243k tokens/action due to tail-20 including full Read/Grep dumps | config: observer_skip_list | Done |
| ACL 2026 Findings | Synapse: plan-from-memory pre-step (3-stage: retrieve→plan→execute) | working-memory.py: plan-from-memory subcommand | Done |
| ACL 2026 Findings | SGA-MCTS: slot-filling DAG for planner/executor split | config: planner_executor_split | Done |
| ACL 2026 Findings | How Memory Management Impacts: tag-not-drop for failed trajectories | l1-promote.py: quality_gate_flag | Done |
| ASI06 (ACL 2026) | Debug logs + backups as unguarded memory copies | am-sentry.py: scan_asi06_backup_exposure | Done |
| arXiv:2608.27427 | Persona vs Execution prompt split, untrusted-input != privilege | config: persona_execution_split | Done |
| arXiv:2608.27443 | NL permission policies compiled to 4-tuples | config: nl_permission_policies | Done |
| GitHub: JordyZomer/lemmalog | Datalog engine for LLM memory — bi-temporal, provenance+confidence, MCP server | Noted for future Hindsight write-path evaluation | Noted |

## MED Priority — Selected

| arXiv ID | Title | Target | Status |
|---|---|---|---|
| 2608.26696 | Five Primitives for Governing AI Agents | harness-first-agent-design | Done |
| 2608.26788 | Decoupling Planning and Control | harness-first-agent-design | Done |
| 2608.27086 | Contract-Centered Architecture | agent-task-signoff | Done |
| 2608.26867 | BekchiAI: Observability | config: harness_fingerprint | Done |
| 2608.26218 | Harness Fingerprint in Evals | config: harness_fingerprint | Done |
| 2608.26130 | First-Chunk Inclusion for Tool Outputs | focus_compress.py: first-chunk-not-tail rule | Done |
| 2608.27128 | TwinKV: KV Cache Repair | Noted (infra-level; no Hermes hook) | Noted |
| 2608.27338 | One Model Many Minds (MoRe) | Noted for future persona design | Noted |
| 2608.27260 | What Makes Good Agentic Data | harness-first-agent-design | Done |
| 2608.27102 | LAAF Governance Survey | harness-first-agent-design | Done |

## Implementation Pitfalls (Sweep 29)

1. **Config nesting bug**: Appending config sections at EOF silently nested them under `memory:` block. Required de-indenting and re-inserting at verified top-level position. Verification gate: `python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); [c[k] for k in NEW_KEYS]"` must pass after every batch.

2. **am-sentry.py aggregation wiring**: The `all_flags = ...` line must be found by exact variable name. Searching for newly added flag variables fails because they don't yet exist in the file.

3. **Tool verification script arg mismatch**: Initial test script used wrong args (`--content`, `--wiki-dir`, `--session`). Fixed by inspecting argparse structures directly. Always `python3 script.py --help` before writing assertions.

4. **Secondary subagent overlap**: The async secondary subagent (deleg_aa034254) returned some of the same papers already found in direct research. Triage step required before implementation to avoid double-patching.

## New Scripts Created

- `~/.hermes/scripts/skill-wiki.py` — WikiSkill upsert/show/prune (255 lines)
- `~/.hermes/scripts/skill-state.py` — SKILL.state init/step/show/complete/gc (301 lines)
- `~/.hermes/scripts/tool-auth-gate.py` — action induction vs runtime authorization (237 lines)
- `~/.hermes/scripts/critique-bank.py` — CritICL inference-time failure conditioning (199 lines)

## New Config Sections

`skill_wiki`, `skill_state`, `tool_auth`, `calibration_gate`, `loop_harness`, `observer_skip_list`, `first_chunk_rank`, `constraint_freshness`, `harness_fingerprint`, `critique_bank`, `tool_slo`, `durable_file_write_gate`, `nl_permission_policies`, `persona_execution_split`, `information_flow_control`

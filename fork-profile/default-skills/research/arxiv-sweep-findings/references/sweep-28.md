# Sweep 28 — Aug 26 2026

**Cutoff in:** 2608.23566 (exclusive). **New max seen:** 2608.24885.
**Papers triaged above cutoff:** ~80 unique IDs (cs.AI/MA/CL/LG/SE/IR + keyword API).
**185-article backlog:** still closed (Sweep 26); no residual HIGH unapplied from that set.

## Sources

- arXiv API (all:cs.* + keyword queries), direct PDF/abstract fetch
- HN Algolia (agent memory/harness/skill)
- GitHub search (agent-memory, skill-evolution, context-compression)
- Multilang: arXiv zh abstracts present in batch; no unique ZH-only HIGH beyond EN abstracts
- Web tool was broken mid-sweep (`web.search_backend: brave` not registered) → fixed to `brave-free`

## HIGH applied

| ID | Title | Surface |
|----|-------|---------|
| 2608.24569 | Constraint Weakening (must→maybe in handoffs) | `handoff`, `hermes-context-packet`, `focus_compress.py`, `constraint-binding-lint.py`, config `memory.handoff` |
| 2608.24358 | Handoff Tax (cross-model trajectory) | `handoff`, WM `handoff-export`, config `full_trajectory_on_model_switch: false` |
| 2608.24876 | Recuris WM vs Experiential Memory | `working-memory.py`, context-packet `working_memory_ref`, runtime-loop OODA+Recuris |
| 2608.24188 | Paritok intent-conditioned extractive compress | `focus_compress.py`, `l1-context-offload.py --intent`, config `compression.intent_conditioned_offload` |
| 2608.24368 | OODA-Tool state/action separation | `agent-runtime-loop-patterns` |
| 2608.24691 | Belief miscalibration at action time | `trajectory-risk-guardrail` |
| runtime | Brave provider name drift | `config.yaml` `web.search_backend: brave-free` (smoke search OK) |

## MED applied

| ID | Title | Surface |
|----|-------|---------|
| 2608.24777 | StepGuard step-level pre-exec | `trajectory-risk-guardrail` manual checklist |
| 2608.24509 | PeakBench resource-aware parallel tools | runtime-loop Quick Decision Guide |
| 2608.24804 / 2608.24747 | StarHarness / SkillForge | SkillZip → already covered by AutoSaddler + self-improve validation gates (no duplicate skill section) |
| 2608.24189 | MemUse natural integration eval | note only — Direct-QA still not primary Hermes memory KPI |

## SKIP / defer

| ID | Why |
|----|-----|
| 2608.24794 CAFE | Needs shared-parameter agent/critic RL — not API harness fit |
| 2608.24571 SMITH joint tool create/use | Weight-training; Hermes uses fixed tools |
| 2608.24275 RePolicy | RL policy invocation model — am-sentry remains honesty-first NL deny |
| 2608.24271 llmmas-otel | Interesting observability; install only if multi-agent SE debugging pain |
| 2608.24017 WebMCP-Phalanx | Browser trust architecture product-scale |
| 2608.24022 Attnlocate | Needs attention internals — not API-accessible |
| 2608.24069 Poisoning Agentic Alpha | Domain trading MAS; trust lessons already in MAIA/Interaction Tax |
| 2608.24060 scrydb | session_search already FTS5; no second SQLite IR stack |
| 2608.24764 AtlasNav | DCI corpus navigation — no large corpus agent product here yet |
| 2608.24361 AIG failure graphs | Partial via systematic-debugging CFA; full graph UI deferred |
| 2608.24306 DR citation blame | Research-report systems only |

## Runtime / config / scripts

1. `config.yaml`: `web.search_backend: brave` → `brave-free` (provider registry name).
2. `config.yaml` `memory.working_memory` + `memory.handoff` + `compression.intent_conditioned_offload`.
3. NEW `~/.hermes/scripts/working-memory.py` — session WM (goal/progress/constraints/skill-hint/handoff-export/failure localize).
4. NEW `~/.hermes/scripts/constraint-binding-lint.py` — detect must-softening in handoffs/packets.
5. `focus_compress.py` — extractive + binding-typed constraints.
6. `l1-context-offload.py` — `--intent` Paritok-lite cold summarize.

## Skills patched (SkillZip: no full procedure duplication)

- `handoff` — WM + constraints + Handoff Tax
- `hermes-context-packet` — binding objects + working_memory_ref
- `trajectory-risk-guardrail` — confidence gate ban + StepGuard checklist
- `agent-runtime-loop-patterns` — OODA + PeakBench/Recuris decision rows
- `arxiv-sweep-findings` — boundary log + this file

## Explicitly not built (benefit/cost)

| Item | Benefit | Cost | Revisit |
|------|---------|------|---------|
| Full Recuris meta-agent RSI loop | High long-horizon | High autonomous skill mutation risk | After WM adoption + failure_localizations volume |
| StarHarness proposer/hidden split training | High harness gains | Needs offline eval farm | Extend AutoSaddler batch only |
| MemSIF topical/event plane | (still deferred s27) | High store dupe | User arc-recall failures |
| Graphiti hard eviction | (s27) | Silent knowledge loss | Near 40k nodes |
| native StepGuard model | Better pre-exec | Train/host classifier | If HAZARD false-negatives logged |

## Adversarial notes

- Config rewrite via PyYAML dropped comments only; key set matched pre-update snapshot (verified).
- `brave_api_key` in yaml is legacy; live auth is `BRAVE_SEARCH_API_KEY` in `.env` — do not delete key until dual-read confirmed unused.
- Constraint objects must not be double-stored as prose in `current_state` (AgentPrune / SkillZip).
- WM is session-local cache — not a substitute for Hindsight durable facts.
- Do not auto-promote StarHarness/SkillForge as new skills; AutoSaddler already owns offline harness evolution.

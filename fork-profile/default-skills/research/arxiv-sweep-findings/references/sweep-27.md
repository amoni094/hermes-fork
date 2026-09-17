# Sweep 27 — Aug 25 2026

**Cutoff:** 2608.23566 (exclusive). **Papers above cutoff:** 0 (live arXiv max still 2608.23566).

## 185-article backlog

Closed in Sweep 26: 347 → 185 noisy titles → 16 HIGH; remaining HIGH already applied or SKIP.
No re-implementation of that first-pass count.

## Net-new sources (below cutoff, not previously applied)

| ID | Title | Decision |
|----|-------|----------|
| 2608.23041 | AutoSaddler: Automatic Harness Optimization from Failure Traces | HIGH — self-improve-agent offline harness loop |
| 2608.23541 | The Interaction Tax (multi-agent diversity erasure) | HIGH — dispatching-parallel-agents + autonomous-ai-agents |
| 2608.22808 | CatchBench PRE/LIVE/POST | HIGH — verification-before-completion (was SKIP as "benchmark only"; runtime audit states are useful) |
| 2608.23565 | ReWorld landmark bank | Already architecture-validated in sweep 24; no new code |
| 2608.23473 | MetaCaster | SKIP — time-series domain |
| 2608.23564 | SWE Refactor Bench | SKIP — benchmark only |
| 2608.23552 | Prime Agent | SKIP — no IPython kernel (sweep 26) |

GitHub/HN: Heimdall, claude-slim, OpenViking, locomo-recordari already absorbed in prior sweeps
(OpenViking L0/L1/L2 → hermes-context-budgeting; no new install).

## Runtime / config applied

1. `config.yaml` `memory.tier_thresholds.promote_thresholds` synced to code gates:
   stable 0.45 / volatile 0.30 / ephemeral 0.55; min_retention_promote 0.45.
2. Added config caps: `max_ephemeral_facts: 500`, `max_volatile_sessions: 20`,
   `graphiti_warn_nodes: 40000`, `graphiti_halt_nodes: 50000`.
3. `l1-promote.py`: module-level `VC_PROMOTE_THRESH` + `_load_promote_thresholds()` from config.
4. `memory-ttl-purge.py`: `_load_ttl_config()` for max_volatile_sessions; FAMA `gen_gap_days`
   on stale-reuse log events.
5. `unified-recall.py`: annotate recalled items with `gen_gap_days` for SEU/RDM consumers.
6. `l1-graphiti-write.py`: load warn/halt node caps from config.

## Skills applied

- `dispatching-parallel-agents` — Interaction Tax independent-proposal rule
- `autonomous-ai-agents` — Interaction Tax pointer (SkillZip: no full duplicate of procedure)
- `self-improve-agent` — AutoSaddler offline harness optimization
- `verification-before-completion` — CatchBench PRE/LIVE/POST catch table

## Explicitly not built — benefit/cost matrix (this stack)

"Out of scope" here means cost/risk or no current pain signal — **not** low paper quality.
Full triage procedure: `arxiv-sweep-findings` Maintenance Notes §8 (canonical; trajectory skill is user-owned).

| Item | Benefit here | Partial coverage | Cost/risk | Revisit trigger |
|------|--------------|------------------|-----------|-----------------|
| MemSIF topical/event plane | High if multi-session arcs get lost | Dual-Track CoreFact/ActiveFact facts only (not topical segments + event trajectories) | High: second store + recall merge + promote rules; easy Graphiti episode dupe | User reports arc-recall failures after Dual-Track is stable |
| Graphiti hard eviction | High *at* capacity cliff | warn@40k / halt@50k write stop only | Medium-high: wrong delete = silent knowledge loss | Live node count approaches warn; design then, not before |
| ToolGraph tool reranker | Medium if wrong tools keep winning | Map-Guided `enabled_toolsets` already scopes provision | Medium: ranker train/eval + new failure mode | Systematic wrong-tool selection *after* toolset scoping |
| micro_compact axis (relevance vs turns) | Medium token/$ if cache thrash or mid-task forget | `micro_compact` exists; axis may be wrong | Medium + regression-prone context bugs | Measured cache misses or forget-after-compact |
| Learned router | Low until misroutes are logged | Static `claude-routing-hierarchy` task-type table + cloud-only | High: labels, feedback loop, silent wrong model | Misroute log proves static table fails at volume |
| Policy compiler (NL→obligations) | High in principle for safety | am-sentry treats NL deny as unenforced (correct honesty) | Very high; half-done worse than explicit non-enforcement | Prefer concrete allowlists/tool gates — product-scale only |
| Prime Agent IPython kernel | High on notebook/ARC benches; low on CLI Hermes | N/A | High: second runtime model | Only if deliberately adding a notebook agent runtime |

Also not a gap: `last_retrieved_at` — lifecycle already has `last_accessed`.

## Adversarial notes

- CatchBench was SKIP in sweep 26 as "benchmark only"; PRE/LIVE/POST is a *method* reusable
  without the benchmark harness — elevated to HIGH here.
- Config previously disagreed with code (stable 0.35 vs 0.45); code was authoritative after
  sweep 24 but config still advertised old values — fixed.
- Interaction Tax must not restate Map-Guided toolset rules; orthogonal concerns.
- Deferred-item ranking is intentional: MemSIF topical and Graphiti eviction are the only
  high-benefit unfinished items; others wait on pain signals or are wrong architecture fit.

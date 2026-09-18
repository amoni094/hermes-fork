# Sweep 26 — Aug 25 2026

**Cutoff:** 2608.23566 (exclusive). **Highest live ID on arXiv new/recent:** 2608.23566. **Papers above cutoff:** 0.

## 185-article backlog (sweep 23, deleg_d802e67e task-0)

First-pass HTML/API filter: 347 candidates → 185 "relevant" titles. That list was truncated in the live log and was mostly off-topic (wildfire, fashion KG, ICS anomaly). The same subagent downselected to **36 assessed / 16 HIGH**. Sweep 23 already applied the real HIGH set (InjecMEM, Compaction Cliff, TRACE, SkillAlchemy, CASS, HERO, Scroll, context-mode, Zenn write-gate). Remaining HIGH from that 16:

| ID | Real title (verified abs) | Action |
|---|---|---|
| 2608.22751 | Risk-Aware Reranking for Agentic Tool Retrieval | Applied as one bullet: `enabled_toolsets` is retrieval-stage filtering. No ToolGraph reranker. |
| 2608.23023 | Most of the LLM routing gap is task type | SKIP — validates existing `claude-routing-hierarchy` static task-type table. Learned routers not justified. |
| 2608.23282 | NL policies → executable obligations (in-car) | SKIP — domain-specific; am-sentry already treats NL deny as unenforced. |
| 2608.22808 | CatchBench | SKIP — benchmark, no runtime hook. |
| 2608.23341 | DPIAgent (bug-repro tests) | SKIP — already covered by systematic-debugging + isolated worktrees. |
| 2608.23552 | Prime Agent | SKIP — architecture note already in sweep 23; no IPython kernel. |

Fake crash-dump IDs 2608.23567–23570 / HASTE 2608.20888 / RethinkSkill 2608.20777 stay tombstoned.

## New-source walk (this session)

- arXiv cs.AI/CL/MA/SE/CR recent + cs.AI/new: **no ID > 2608.23566**.
- GitHub/HN/multilang live subagents: API 401; used existing sweep-23 logs + verified abs pages instead of inventing titles.

## Runtime applied

- `memory-ttl-purge.py`: `MAX_VOLATILE_SESSIONS=20` (arXiv:2605.17625 Dual Process). Empty `session_id` fail-open.
- SkillZip: removed duplicate Map-Guided Harness block in `autonomous-ai-agents`.

## Explicitly not built

MemSIF topical/event layer, last_retrieved_at, Graphiti eviction, ToolGraph reranker, policy compiler, learned router, micro_compact axis change.

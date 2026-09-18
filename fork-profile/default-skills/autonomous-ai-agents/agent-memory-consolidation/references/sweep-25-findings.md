# Sweep 25 findings (recovery + MemSIF runtime)

Date: 2026-08-25
Session recovered: 20260825_215915_9f25a9 (stalled after LeanMem prose, before MemSIF)
Cutoff inherited: 2608.23566 (sweep 24)

## What this sweep is not

This is **not** a fresh arXiv walk past 2608.23566. The crashed session's
"synthesis" of sequential IDs 2608.23567–2608.23570 is **untrusted** and was
not implemented. Brave web_search is currently broken
(`no registered web search provider has that name`).

MemSIF IDs **2608.20444** (state-injection filter) and **2608.20112**
(salience framework) that landed in `agent-memory-consolidation/SKILL.md`
during the crash are **wrong**. The real paper is:

- arXiv:2608.01742 — *MemSIF: From Structured Interactions to Dual-Track
  Fact Memory for LLM Agents* (Luo, Xu, Yang; v2 5 Aug 2026)
- Verified: https://arxiv.org/abs/2608.01742
- Code: https://github.com/luoyufeihaha/MemSIF

## Implemented (runtime)

Paper-bank HIGH item, already catalogued, never wired as Dual-Track:

1. `l1-promote.py`
   - `classify_fact_track()`: CoreFact = `ns=profile` or type
     `preference`/`correction`; else ActiveFact
   - CoreFact bypasses RecMem recurrence gate (eager stage)
   - ActiveFact deferred until recurrence ≥ 2 **or** `access_count ≥ 3`
   - Pending ActiveFacts persist in `lifecycle.db` (`af:<sha16>`,
     `memory_status=pending`, `fact_track=active`)
   - Staging lines emit `[track=core|active]`
   - `fact_track` column + migration on `fact_lifecycle`

2. `unified-recall.py`
   - `search_pending_activefacts()` mixes pending ActiveFacts into recall
   - `record_query_access()` increments `access_count` / `last_accessed`
     on recalled `fact_text` matches (fail-open)
   - Promote-time defer no longer increments (that was fake demand)

3. `l1-graphiti-write.py`
   - Parses and strips `[track=core|active]`
   - Fail-open node-count check: warn at 40k, halt at 50k if `get_status` exposes a count

4. Drain: `promote_ripe_activefacts()` stages pending rows with
   `access_count >= 3` on each l1-promote run.

5. CraniMem cap: `MAX_EPHEMERAL_FACTS = 500`; `enforce_ephemeral_cap()`
   evicts oldest ephemeral rows before a new ephemeral write.

6. Removed leftover `pending_access_bump()` (cron fake-demand).

## Skill cleanup

`agent-memory-consolidation/SKILL.md` v1.9.1: Dual-Track MemSIF + real
PoisonedEvolution (2608.21230). Crash-dump sections tombstoned
(misattributed IDs including 20555/20666/20777/20888/20999/21003/21111/
21333/21444/19234/21555/22001/22444/22888/23333/23567–23570).
HASTE/ERL triggers removed.

## Not done (honest leftover)

- No new papers above 2608.23566 were extracted this session
- Structured Interaction Memory (Topical Segments + Event Trajectories)
  from MemSIF is **not** implemented — only Dual-Track Fact Memory
- Hindsight still has no PATCH API; access_count lives in `lifecycle.db`
- `last_retrieved_at` skipped — `last_accessed` already exists
- Graphiti 50k is warn/halt only, not eviction
- Other heading-only paper stubs in the skill were left (pre-crash bank)

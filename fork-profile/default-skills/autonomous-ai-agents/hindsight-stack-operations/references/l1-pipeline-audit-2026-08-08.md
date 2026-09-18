# L1 Pipeline Audit — 2026-08-08

Audit run by subagent at ~23:30 AEST. Read-only; no changes made.

## Status: All Green

### Hindsight Daemon

| Check | Result |
|---|---|
| Port 9177 | LISTEN — bound, healthy |
| Process | hindsight-api PID 377331, started ~22:20 AEST |
| PostgreSQL | Running (PID 104824 + 5 idle worker connections on :5432) |
| HTTP /health | `{"status":"healthy","database":"connected"}` |
| daemon.log | Clean startup 2026-08-08 18:12:45 UTC, migrations OK |

Note: `~/.hermes/logs/hindsight-embed.log` contains many historical failed-start entries
(embedding dimension mismatch, pg0 teardown races from earlier restarts). These are
**old artifacts** — the current daemon started clean at 18:12 UTC. Always check the
daemon.log timestamp, not just whether errors exist.

### Cron Jobs

| Job | ID | Last Run | Status | Next |
|---|---|---|---|---|
| l1-extract-periodic | ebe4fd06 | 2026-08-08T21:01 AEST | completed | 2026-08-09T00:01 |
| l1-promote-periodic | a0898914 | 2026-08-08T21:01 AEST | completed | 2026-08-09T00:01 |
| l1-hindsight-promote | e034d017 | 2026-08-08T22:16 AEST | completed | 2026-08-09T02:23 |

**One transient failure in recent history:**
- l1-hindsight-promote failed at 2026-08-08T18:00 AEST with `HTTP 429: Rate limit exceeded`
- Auto-recovered at next run (22:16 AEST) — no intervention needed

### Pipeline Output

- **Daily fact file today:** `~/.hermes/memory-facts/2026-08-08.md` — 41 lines, 3 session blocks
  - 03:30Z: cron pipeline instructions (2-turn cron session)
  - 08:00Z: Australian equity trading strategy (10 turns)
  - 11:01Z: Hermes v0.20.0 update session (10 turns)
- **Archive:** 26 dated files from 2026-07-09 to 2026-08-08 — pipeline running continuously
- **INDEX.md:** 8,520 bytes, last updated 2026-08-08 21:01 AEST

### l1-promote Dry-Run (2026-08-08 sessions)

```
32 facts assessed | 30 staged | 2 skipped
```

Skipped facts: ephemeral/single-interaction instructions (scored 0/3). Scoring logic working correctly.

### Staging.md State

- **Size:** 0 bytes (empty)
- **mtime:** 2026-08-08 22:23 AEST
- **Interpretation:** Correct post-flush state — l1-hindsight-promote ran at 22:16 and cleared it.
  The file exists but is empty. Next l1-promote run (~00:01 AEST Aug 9) will repopulate.

### Hindsight Bank Stats

```json
{
  "bank_id": "hermes",
  "total_nodes": 255,
  "total_links": 3960,
  "total_documents": 84,
  "nodes_by_fact_type": {"experience": 58, "observation": 112, "world": 85},
  "pending_operations": 0,
  "failed_operations": 0,
  "last_consolidated_at": "2026-08-08T03:41:49+00:00",
  "pending_consolidation": 0
}
```

All nodes carry `tags: ["l1"]` — L1 pipeline is the sole ingest source.

### Recall Query Results

Broad query `"tool quirk preference environment"` → 118 results.

Sample content in the bank:
- User preferences: skimmable note format, Shakespearean dialogue, institutional TV settings
- Environment facts: Hindsight/Anthropic/OpenAI config, rpm-ostree toolchain, Obsidian vault
- Tool/workflow facts: hermes-obsidian-sync, l1 pipeline Ollama→Anthropic migration, hindsight/__init__.py tracking
- System history: Ollama purge July 14, v0.20.0 update Aug 6, PEAD+ trading research

Most recent memories (by date): 2026-08-08T03:41 UTC (facts about daemon port 9177 behavior
from earlier-that-day troubleshooting session).

## Gaps / Notes

- The `hindsight` CLI binary is not on PATH — API queries must use `curl` against port 9177
- `hermes memory recall` is not a valid subcommand (only `setup`, `status`, `off`, `reset`)
- Recall endpoint requires `"query"` field (not `"text"`) — 422 if wrong field name used
- `hermes cron show/log` are not valid; use `hermes cron runs <id>` and `hermes cron history <id>`

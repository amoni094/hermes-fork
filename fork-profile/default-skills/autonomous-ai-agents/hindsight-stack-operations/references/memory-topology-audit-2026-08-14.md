# Memory & Knowledge Topology Audit — 2026-08-14

Full audit of: MEMORY.md, USER.md, Hindsight config, Graphiti config, l1 pipeline scripts,
hermes-memory-drift-audit.py, memory-staleness.py, hindsight-reembed.py, session-prune.sh,
session DB, and skill coverage for all three memory skills.

## CRITICAL

### C1 — sessions.db is 0 bytes
`~/.hermes/sessions.db` = 0 bytes (mtime 2026-08-12). This means `session_search` is
effectively broken — FTS5 has nothing to query. `state.db` (553MB, active) is the conversation
store; `sessions.db` is the FTS5 index. The prune cron operates against `state.db` only and
does not reinitialize `sessions.db`.

Also CRITICAL: ~5GB of malformed-backup blobs from the July 2026 DB corruption event still
in `~/.hermes/`:
- `state.db.broken.1782907798` (~1.2GB)
- `state.db.malformed-backup-20260701_*` (3× ~1.2GB + shm/wal)
`session-prune.sh` does not touch these.

## HIGH

### H1 — MEMORY.md §01 STALE (>30d)
`[factual] Routing is cloud-only. Ollama UNINSTALLED (2026-07-12)` — `memory-staleness.py`
flags newest date 33 days old (>30d threshold). Fact likely still accurate but needs a date
refresh or re-confirmation. 8/9 other sections are UNKNOWN (no dates embedded).

### H2 — Hindsight DB files not visible on disk
`~/.hermes/hindsight/` contains only `config.json` (4KB). Actual data is in pg0 Postgres.
DB growth cannot be checked with `du`. Must query bank stats API:
`curl -s http://127.0.0.1:9177/v1/default/banks/hermes/stats`

### H3 — drift-audit output is detection-only
`hermes-memory-drift-audit.py` runs daily (`no_agent=True`), writes to Obsidian vault +
stdout. No alert, no automated remediation. Missing Obsidian vault files → exits early,
staleness check skipped silently.

### H4 — l1-extract and l1-promote on identical 180m schedules
Race condition: if both fire simultaneously, l1-promote may process facts that l1-extract
just wrote in the same cycle, skipping some until the next. No dependency enforcement.

### H5 — MEMORY.md at 90% (1990/2200 chars)
~210 chars headroom. Next medium-complexity write risks silent failure. 8/9 sections
UNKNOWN date status. Eviction policy: manual only.

### H6 — USER.md at 96% (1537/1600 chars)
~63 chars headroom. Next user preference write will likely fail silently or require manual
pruning first. Largest candidate for eviction: PPOR/property section (~200 chars) if
property searching has concluded.

## MEDIUM

### M1 — Graphiti config OK; OpenAI key has two stores
`claude-haiku-4-5` correct. Entity/edge type schema rich and consistent. Gap: the OpenAI
key exists in both Graphiti's env (via OPENAI_API_KEY env var) and Hindsight's config.json
(HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY). Key rotation must update both.

### M2 — l1-graphiti-write.py handles empty staging.md correctly
`parse_staging` returns `[]` on size==0 or missing path → prints "nothing to write" → exits 0.
Script writes to Graphiti only (not Hindsight). "dual-write" label belongs to the cron job,
not the script.

### M3 — memory-staleness.py not a standalone cron
Only runs as subprocess of drift-audit. No independent cron, no file artifact.

### M4 — hindsight-reembed.py: hardcoded pg0 credentials
Connects via `host=127.0.0.1 port=5432 dbname=hindsight user=hindsight password=hindsight`.
If pg0 credentials change, script fails with psycopg2 auth error. Also auto-installs
psycopg2-binary and openai on import failure (may fail silently on immutable OS).
hindsight-stack-operations skill does document this script correctly in "Backfill re-embedding."

### M5 — session-prune.sh doesn't clean malformed-backup files (see C1)

### M6 — Skill contradiction: l1-promote.py described as writing to Hindsight directly
`agent-memory-consolidation` states "l1-promote.py writes surviving facts to Hindsight
via hindsight_retain()". This is wrong — l1-promote.py writes to staging.md only.
The `l1-hindsight-promote` cron reads staging.md and calls hindsight_retain. The MEMORY.md
entry "l1-graphiti-write.py dual-writes staging.md to both" also conflates script with cron.

### M7 — STALE_REFERENCE_RULES in drift-audit covers only 1 file / 1 pattern

## LOW

### L1 — Graphiti config-hermes.yaml lines 100-147 not reviewed (edge_type_map)
### L2 — hindsight-reembed.py double-run on summary counts (classify_section 3× per section)
### L3 — 8/9 MEMORY.md sections permanently UNKNOWN to staleness detector (no dates)

## Baseline numbers (2026-08-14)
- MEMORY.md: 1990/2200 chars (90%)
- USER.md: 1537/1600 chars (96%)
- state.db: 553MB (553MB WAL active + 64MB WAL file)
- sessions.db: 0 bytes (BROKEN)
- memory-facts/staging.md: 0 bytes (healthy — last flushed)
- memory-facts/ daily files: 2026-07-09 through 2026-07-17 (oldest visible)
- Hindsight pg0 bank baseline (from Aug-12 audit): ~6,654 total_nodes, ~257 docs, ~183,611 links

# System cohesion audit — 2026-08-25

## Fixed this pass
1. **Hindsight down** — FastMCP/mcp import break repaired; daemon healthy on :9177.
2. **Hindsight idle exit** — `idle_timeout` 300→0; systemd user unit `hindsight-api.service` enabled.
3. **claude-routing-hierarchy** — unquoted `Use when:` broke YAML parse → skill missing from name index (related_skills false dead-refs).
4. **hermes-memory-surface-selection** — residual active qmd/MemPalace routes removed (both DISABLED).
5. **pii-redaction** — dead `ocr-and-documents` related + ghost skill dir removed; `last30days` broken symlink removed.
6. **stalled-session-recovery / pii** — meta-only related_skills promoted to top-level where needed.
7. **skillspector** — 30 pending quarantine cleared (docs/URL FPs + trusted local scripts).
8. **sessions.db 0-byte** — legacy stub only; live FTS is `state.db` (`messages_fts`, 17k msgs). Stub renamed aside.
9. **Memory note** — brave search API live (HTTP 200); stale "no registered provider" note corrected.

## Topology (verified healthy)
| Layer | Status |
|-------|--------|
| MEMORY.md / USER.md | 1348 / 1569 chars (USER near cap) |
| session_search | state.db FTS OK |
| Hindsight | systemd active, /health healthy; banks hermes=118, hermes-default=366 nodes |
| Graphiti MCP | initialize 200; falkordb up |
| L1 cron | extract 180m / promote 220m / hindsight 240m / graphiti 240m — staggered OK |
| memory-ttl-purge | dry-run clean; thresholds load from config |
| promote thresholds | stable 0.45 / volatile 0.30 / ephemeral 0.55 (config↔code synced) |

## Cohesion map (handoffs)
```
session turns → state.db (session_search)
             → l1-extract (180m) → daily md
             → l1-promote (220m) → staging.md + lifecycle.db
             → l1-hindsight-promote (240m) → Hindsight retain
             → l1-graphiti-write / reconcile (240m) → Graphiti
             → memory-ttl-purge (03:00) → expire ephemeral/volatile
MEMORY.md/USER.md ← memory tool (manual durable only)
skills ← skill_manage (procedures); skillspector guard on write
```

## Left intentionally
- **Oversized skills** (hindsight-stack-operations, arxiv-sweep-findings, etc.) — extract-more is ongoing; no blind split this pass (break risk).
- **meta_only related_skills** on hub/bundled skills (godmode, apple-*, github-* hub) — low traffic; dead refs only on optional macOS/godmode.
- **web.search_backend=brave vs doctor "firecrawl"** — Brave API works; doctor may report extract path. Do not force remap without a failing hermes_web_search.
- **Firecrawl container up** but some /health paths 4xx — extract still reported OK by doctor.
- **USER.md 98%** — do not auto-trim without user preference.
- **Bi-temporal / MemSIF / Graphiti hard eviction** — still deferred (capacity + cost).

## Adversarial checks run
- YAML parse all SKILL.md: 0 broken
- Residual active qmd/MemPalace routes: 0
- Hindsight + Graphiti live handshakes
- session_search discover returns hits
- l1-promote thresholds match config after load
- skillspector pending_quarantine=0, quarantined=0
- No double hindsight process after systemd own

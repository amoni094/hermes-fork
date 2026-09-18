# Hermes cron pipeline map

Source of truth: `~/.hermes/cron/jobs.json` (32 jobs). Intervals do **not**
serialize data-dependent jobs; overlapping ticks are possible. Lockfile added
2026-09-09: `~/.hermes/.l1-extract-running` (extract holds; promote skips).

Pipeline (memory):

```
l1-extract-periodic (180m, l1-extract.py)
        writes ~/.hermes/memory-facts/YYYY-MM-DD.md
        |
        v
l1-promote-periodic (220m, l1-promote.py)   [skips if extract lock present]
        writes ~/.hermes/memory-facts/staging.md
        |
        v
l1-hindsight-promote (240m, agent)          [reads staging.md -> hindsight_retain]
        |
        v
l1-graphiti-periodic (240m, l1-graphiti-reconcile.py)
        retries failed Graphiti writes
        |
        v
g-memory-tier3-nightly (03:00, l1-gmemory-consolidation.py)
hypermem-promote (220m, l1-hypermem-promote.py)
```

Known ordering race: extract is *more frequent* than promote (180m vs 220m) but
ticks are independent, so promote can still overlap a long extract. Lockfile is
the guard. Interval-only fix would be extract shorter than promote *and* a
staggered `next_run_at` (already 220m vs 180m; not 210m).

`l1-hindsight-promote` is **not** `l1-promote.py`. It is an agent job
(`script: null`) that consumes `staging.md` after promote has scored facts.

Daily 1440m pair `hermes-mutation-gate-watch` / `hermes-memory-drift-audit` fire
~67s apart. They do **not** share an output file (gate scans evolution dirs +
stdout; drift writes vault `Hermes Memory Drift Audit.md`). Low race risk.

| job name | script | depends_on | interval | notes |
|---|---|---|---|---|
| firecrawl-watchdog | firecrawl_watchdog.sh | — | 10m | no_agent |
| news-diff-watchdog | news_diff_watchdog.py | — | 90m | no_agent |
| l1-extract-periodic | l1-extract.py | state.db recent turns | 180m | writes dated memory-facts; holds `.l1-extract-running` |
| l1-promote-periodic | l1-promote.py | l1-extract-periodic | 220m | scores facts → staging.md; skip if extract lock |
| hypermem-promote | l1-hypermem-promote.py | l1-promote-periodic / lifecycle.db | 220m | same next_run as promote-periodic (23:34:15) — watch lifecycle.db |
| hermes-chat-sync-4h | hermes-chat-sync-precheck.py | sessions + vault notes | 240m | agent after precheck |
| skillspector-guard | skillspector_guard_enforce.sh | — | 240m | no_agent |
| session-auto-prune | session-prune.sh | — | 240m | no_agent; clustered ~20:53 with L1 jobs |
| l1-hindsight-promote | *(agent)* | l1-promote-periodic (staging.md) | 240m | no script; hindsight_retain + graphiti register; next_run 4s after extract |
| l1-graphiti-periodic | l1-graphiti-reconcile.py | l1-hindsight-promote | 240m | retry failed Graphiti writes |
| hermes-platform-watchdog | hermes-platform-watchdog.sh | — | 720m | no_agent |
| hermes-mutation-gate-watch | hermes-mutation-gate-watch.sh | evolution output dirs | 1440m | no_agent; stdout only |
| hermes-memory-drift-audit | hermes-memory-drift-audit.py | MEMORY.md + vault notes | 1440m | no_agent; writes vault audit note (not shared with mutation-gate) |
| hermes-math-sweep | hermes-math-sweep.py | — | 0 1 * * 2 | last_status unknown |
| cs-research-weekly | cs-research-sweep.py | — | 0 2 * * 4 | last_status unknown |
| g-memory-tier3-nightly | l1-gmemory-consolidation.py | Hindsight + Graphiti | 0 3 * * * | Graphiti 406 fixed (SSE + Accept text/event-stream + mcp-session-id header); catch-up when host off overnight |
| omni-skill-quality-scan | omni_skill_scan.py | skill library | 0 3 * * 0 | catch-up pattern |
| state-wal-checkpoint | state-wal-checkpoint.py | state.db | 20 3 * * * | nightly; late when host off |
| memory-ttl-purge | memory-ttl-purge.py | memory-facts / lifecycle | 40 3 * * * | nightly; late when host off |
| concept-lattice-nightly | concept-lattice-index.py | — | 0 4 * * * | |
| se-gos-weekly | se-gos-graphiti-bridge.py | Graphiti | 0 5 * * 0 | last_status unknown |
| hermes-research-weekly | hermes-research-sweep.py | arXiv / cache | 0 6 * * 2 | writes `~/.hermes/cache/research/hermes-research-latest.json` |
| hermes-math-interpret | math-paper-interpreter.py | hermes-math-sweep | 30 6 * * 2 | |
| hermes-research-apply | *(agent)* | hermes-research-weekly | 0 7 * * 2 | see below |
| cs-research-interpret | cs-paper-interpreter.py | cs-research-weekly | 30 6 * * 4 | last_status unknown |
| skill-wiki-weekly | skill-wiki.py | skill library | 0 6 * * 0 | agent |
| pending-improvements-review | *(agent)* | — | 0 10 * * 0 | |
| desktop-sync-nightly | desktop-sync.sh | — | 0 10 * * * | |
| firewall-port-audit | firewall-port-audit.sh | — | 10 4 * * 1 | |
| obsidian-weekly-review | obsidian_weekly_review.sh | vault Reviews/ | 0 17 * * 5 | agent after scaffold; last fire catch-up +3h56m |
| skill-prune-audit | skill_prune_audit.py | — | 0 9 1 * * | monthly |
| cs-primers-quarterly | cs-primers-overnight.py | — | 0 3 1 */3 * | last_status unknown |

## hermes-research-apply (001715fd293f)

Agent job (`script: null`, `no_agent: false`). Cron `0 7 * * 2` (Tuesday 07:00),
one hour after `hermes-research-weekly` (`0 6 * * 2`).

Prompt: load `~/.hermes/cache/research/hermes-research-latest.json`; skip
silently if missing or older than 48h. Otherwise triage `new_papers_flat` into
HIGH/MED/LOW against 7 Hermes research categories; HIGH/MED get
`skill_manage` patches via `trajectory-research-synthesis-to-skills`; write
apply-report to `~/.hermes/cache/research/hermes-research-apply-latest.md`.

Skills: hermes-research, trajectory-research-synthesis-to-skills,
arxiv-sweep-findings, adversarial-review, verification-before-completion, spike.

Last run 2026-09-04 22:01 (catch-up from 07:00; +2h40m). `enabled_toolsets` is
null (full tool surface). Next: 2026-09-15T07:00.

## Coherence issues (not fixed here)

- Overnight cron (`0 3`, `20 3`, `40 3`) miss when the laptop is off; they
  catch up hours late (memory-ttl-purge, state-wal-checkpoint, g-memory).
- 240m cluster around 20:53: session-auto-prune, l1-graphiti, l1-extract,
  l1-hindsight-promote fire within ~25s. Extract vs hindsight-promote do not
  share files directly (dated md vs staging.md) but graphiti-reconcile vs
  hindsight-promote both touch Graphiti/staging.
- `hypermem-promote` and `l1-promote-periodic` share identical next_run_at.
- `g-memory-tier3-nightly` Graphiti 406 client bug fixed in reconstructed `l1-gmemory-consolidation.py` (Hindsight still required at runtime).
- Stale extract lock: if extract is SIGKILL'd, promote will skip until the
  lock file is removed. No TTL on the lock (by design of the requested guard).
- Original extract/promote **source** was destroyed by patch-tool 0-byte write
  on root-owned files. Wrappers load cpython-314 pyc. Promote pyc is older
  (2026-08-29) than the wiped Sep 7 source.

## Lockfile contract

| role | path | behavior |
|---|---|---|
| extract | `~/.hermes/.l1-extract-running` | `touch` at start of work; `unlink` in `finally` |
| promote | same path | if exists: print skip message, `sys.exit(0)` |

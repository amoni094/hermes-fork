---
name: hermes-fork
description: "Use when: working with the amoni094/hermes-fork private fork."
tags: [hermes, fork, compression, plugin]
related_skills:
  - hermes-lambda-tuner
  - hermes-agent
  - hermes-context-budgeting
---

# hermes-fork

Private fork of NousResearch/hermes-agent (`amoni094/hermes-fork`). Canonical narrative: clone `FORK_README.md` (SkillZip: explain once, reference many). Companion: skill `hermes-lambda-tuner`.

Canonical install: `~/.hermes/hermes-fork/` on branch `feature/adaptive-compression-plugin-api`. Venv at `~/.hermes/hermes-fork/venv/`. Terminal command: `hermes-fork` (wrapper at `~/.local/bin/hermes-fork`). Profile: `~/.hermes/profiles/fork/` (isolated from default). Wrapper passes `--profile fork` to the fork binary. Legacy worktree was `/tmp/hermes-fork-work` (ephemeral, do not use).

The fork binary uses `--profile fork` for isolation. Without it, hermes-fork boots with the default profile and sees the home dir instead of its own context. If the fork loses identity, check that the wrapper still passes `--profile fork`.

Pitfall: skill_manage refuses writes to skills in the default profile when the active
session is running as fork profile. Error: 'Skill X not found in active profile fork.
A skill by that name exists in profile default.' Fix: use the patch tool directly on
the absolute file path (~/.hermes/skills/<category>/<skill>/SKILL.md). This affects
all default-profile skills even when they were loaded and consulted in the fork session.
Skills at profiles/fork/skills/ can be written via skill_manage normally.

Latest commits (as of 2026-09-11, rebased onto main @ 036a20b3ca):
- `27afcecb28` spike(manifold): manifold-based span scoring analysis (math-007-manifold)
- `0848a5b497` feat(complexity): description MDL signal, zlib compression ratio (th-decomp2)
- `e7ef1db20b` test(arb): add ARB retry stamp tests
- `2e86944e70` spike(it-compress): R(D) per-session compression floor
- (+ 18 earlier fork commits) — 22 total on top of main
- 182 tests passing post-rebase
- 11 confirmed bugs resolved across 3 adversarial pass cycles

## Sync upstream

```bash
git fetch origin
git rebase origin/main
# resolve conflicts, then update the feature branch without clobbering a rewritten remote:
git push fork feature/adaptive-compression-plugin-api --force-with-lease
```

Do not `git push` to GitHub unless the user explicitly asks.

## Run tests (DaemonThreadPool skip)

Python 3.14 renamed `ThreadPoolExecutor._initializer`. `DaemonThreadPoolExecutor` in `tools/daemon_pool.py:53` still passes `_initializer`, so `TestWorkerTeardownOnCeiling` fails on 3.14. Deselect it; do not "fix" by rewriting the pool unless that is the task.

Fresh clone / no full install also lacks `acp` and sometimes `wcwidth`.

```bash
python -m pytest tests/agent/test_context_compressor.py tests/tools/test_plugin_guard.py -q \
  --ignore=tests/acp --ignore=tests/acp_adapter \
  --deselect tests/agent/test_compression_attempt_lifecycle.py::TestWorkerTeardownOnCeiling
```

Targeted compile after Python edits:

```bash
python -m py_compile agent/context_compressor.py hermes_cli/plugins.py \
  agent/turn_context.py plugins/user/lambda-tuner/__init__.py
```

## Four hook points

| Hook | Fires at session boundary | description |
|------|---------------------------|-------------|
| `on_session_start`    | Fires at session boundary | Set `ctx._session_id`, apply hint profile+intent, reset profile knobs via `bind_session_state` |
| `pre_llm_call`        | Every LLM call | Classify session type (turn 1 non-greeting or turn 3 lock); set compression profile + reasoning mode + complexity score |
| `pre_compress`        | Before every compression event | Reaffirm locked profile (guards `update_model()` resets); enable IB prune for code only; entropy-adaptive for unclassified large contexts |
| `on_session_finalize` | True session teardown (once per /new or exit, NOT per-turn) | Drop LRU/`_fired` entries so a long-lived gateway cannot grow forever |

`pre_compress` is a **plugin** hook. Do not confuse it with memory-provider `on_pre_compress()`.

Idle compaction does **not** invoke `pre_llm_call`.

## Predicates

`plugins/user/lambda-tuner/predicates.py` (re-exported from the plugin `__init__`):

| Export | Returns |
|--------|---------|
| `was_reclassified(sid)` | bool — True if session underwent entropy-decay reclassification (max once per session) |

Added 2026-09-11 (commit f9025e18cc). Previously only session_type/complexity exports existed.

`plugins/user/lambda-tuner/predicates.py` (re-exported from the plugin `__init__`):

| Export | Returns |
|--------|---------|
| `session_type(sid)` | `'research'` / `'code'` / `'mixed'` or `None` |
| `is_research_session(sid)` | bool |
| `is_code_session(sid)` | bool |
| `is_high_confidence(sid, threshold=0.8)` | bool |
| `session_complexity(sid)` | locked float or `None` |
| `turns_since_classification(sid, compressor=None)` | ChronoMem delta, or `-1` |

All fail-open (`False` / `None` / `-1`).

## Complexity scoring

`TaskComplexityScorer` (8-signal mean in `[0,1]`) runs on the classification-lock turn. High (`>0.7`) raises `protect_last_n` by 5 (cap 40); low (`<0.3`) lowers `proactive_prune_tokens` by 8000 (floor 8000). Reasoning mode: `>0.75` → `deep`, `<0.25` → `fast`, else `default` (`PluginContext.set_reasoning_mode`; query via `get_session_reasoning_mode`).

## ChronoMem / turn_clock (HIGH-7)

`ContextCompressor.bind_session_state` is the `/new` boundary. It resets `_turn_clock` to 0, clears entropy checkpoints, and zeroes `_last_compress_entropy` / `_last_compress_clock` so session 2 cannot inherit session 1's clock or skip-gate. Do not treat `turn_clock` as process-global.

## Profiles

Named keys on `ContextCompressor.COMPRESSION_PROFILES` plus entropy-adaptive:

| Profile | threshold_percent | protect_last_n | Intent |
|---------|-------------------|----------------|--------|
| `research` | 0.45 | 15 | Compress sooner; bulky tool_result dumps |
| `mixed` | 0.50 | 20 | Conservative default |
| `code` | 0.55 | 25 | Keep causal exec/read chains |
| `entropy-adaptive` | R(D) from message entropy | estimator | High entropy → sooner; fail-open to mixed |

Lower `threshold_percent` = earlier full compression. `proactive_prune_tokens` is a *later* cheap-prune floor (research 40k / mixed 32k / code 28k).

`protect_last_n` is a requested floor; token-budget tail cut still caps at `_MAX_TAIL_MESSAGE_FLOOR`.

Apply live:

```python
compressor.set_compression_profile("research", _source="lambda-tuner")
```

## Wrapper vs plugin

Use **`hermes-session`** when you need session-0 warm-up:

- patch `rr_scorer_lambda` before compressor init (research=0.55, code=0.2, mixed=0.4)
- force type: `hermes-session research|code|mixed|auto|entropy-adaptive` or `HERMES_SESSION_TYPE=...`

Rely on the **plugin alone** when:

- you are on this fork (`set_compression_profile` exists)
- N+1 lag on `rr_scorer_lambda` is acceptable
- live threshold/prune/protect_last_n from turn 1+ is enough

Vanilla Hermes has no live mutation path: always use the wrapper + hint file.

Plugin still writes `${HERMES_HOME}/cache/last-session-type.json` so the wrapper can warm the *next* session.

## Compaction Eval Results (v3, 2026-09-12, valid window-aware questions)

All 15 questions per domain drawn from the 500K-token eval window, literal-span gate verified.

RESEARCH DOMAIN (combined = recall/ratio*100):
  fork_research 43.3% combined=4.37 easy=50 med=50 hard=30 49K  <- wins combined
  lean          43.3% combined=4.11 easy=40 med=40 hard=50 52K  <- wins hard
  current       40.0% combined=3.88
  fork_code     36.7% combined=3.71
  fork_mixed    23.3% combined=2.33  <- worst on research

MIXED DOMAIN:
  fork_mixed    40.0% combined=3.65 easy=30 med=40 hard=50 54K  <- wins
  lean          33.3% combined=3.38
  fork_code     33.3% combined=3.09
  fork_research 23.3% combined=2.16 easy=10  <- worst on mixed

KEY FINDINGS:
- Domain specialisation confirmed and stable: fork_research wins research, fork_mixed wins mixed
- Cross-domain penalty is ~20 points — mismatched profile is worse than vanilla lean
- Classifier routing to correct profile is the next build; expected gain: research 4.37 + mixed 3.65 vs lean 4.11 + 3.38
- head_hit_rate fixed to 0.10 on research after ledger-before-prefix fix; mixed still 0.0 (ledger signals absent in that lineage)
- Ship bar: matching-domain combined >= 4.0, ratio <= 0.11, easy >= 40%, hard >= 40%

SHIP-GATE v3 (N=30, mismatched lineages — do not use for ship decisions):

Research lineage (cap window = 100% code; label is wrong):
  fork_research  41.7% combined=4.15  ← wins, but eval is unfair (cap window is code)
  classified     31.7% combined=3.07  ← correctly routes to fork_code; penalised by wrong label

Mixed lineage (cap window = 92% research; label is wrong):
  fork_mixed     31.7% combined=2.98  ← no arm clears bar; cap window is actually research
  classified     23.3% combined=2.20  ← correctly routes to fork_research; penalised by wrong label

Interpretation: fork_research winning on a code-content cap window suggests its policy generalises. Proper evaluation requires domain-matched lineages (ship-gate v4, in progress). Do not interpret classified-arm results until v4.

## Domain-matched lineage construction

The original eval lineages had a cap-window / domain-label mismatch. The 500K-token cap window is the *end* of the file, not a representative sample of the lineage label:

- research lineage (3882 msgs): cap window msgs 3145-3882 = 100% code (implementation sessions)
- mixed lineage (3036 msgs): cap window msgs 2621-3036 = 92% research (arXiv sweeps)

The classifier correctly identified these as code/research respectively, but was penalised because the lineage labels said otherwise. The bug was in eval design, not in `session_classifier`.

Fix: truncate lineages so the 500K-token cap window lands in the correct content type:

- research_v2: `research_msgs[:1400]` → cap window msgs 979-1400, R=4355 C=953, ratio 4.57x (strongly research)
- code_v2:     `research_msgs[1500:]` → cap window msgs 1645-2382, R=527 C=3060, ratio 0.17x (strongly code)
- mixed_v2:    `research_msgs[700:1700]` → cap window msgs 421-1000, R=1099 C=1223, ratio 0.47 (genuinely mixed)

To find the right truncation point for any lineage:
1. Scan in 300-msg chunks; record R/C signals per chunk
2. Use `find_cap_start(msgs, 500_000)` for the actual token-based cap start (not a 15% approximation, not `msgs[-N:]`)
3. Check R/C ratio of the cap window; adjust truncation until the ratio matches the desired domain

Ship-gate v4 COMPLETE (N=30, domain-matched):
- fork_mixed wins 2/3 domains (research_v2: 45% combined=5.10, code_v2: 38.3% combined=5.52) and ties on mixed_v2
- Domain-specific policies (fork_research, fork_code) lose on their own turf — they over-prune the other content type
- classified arm routes correctly (3/3 domains); gap to winner is policy quality, not routing failure
- SHIP DECISION: fork_mixed as recommended default. fork_research/fork_code are legacy/experimental.
- Results: /tmp/eval_v4/RESULTS.md. Commit: bcecd0ad1e.

Always verify the classifier's output on the actual cap window before interpreting classified-arm results. Emit `classifier_decision` / `classified_info` on every arm. Use `classified_oracle(<profile>)` to score the profile the classifier selected, not the lineage tag. Compare the classified arm against the domain-matched policy, not against the lineage label.

EVAL PROCESS LESSONS (critical):
- 500K cap takes last ~15% of a 3000+ msg lineage — always build questions from capped window, not full file
- literal-span gate must check capped window (simulate cap before validation)
- Bare-number regex harvests arXiv ID fragments; fix: 3-digit min + dot-adjacent skip + emit ctx line not bare number
- HEAD_HIT_CHARS=2000 too small (summary header ~1-2K before ledger); use 5000
- CI width at N=15 is ~40-44 pts; need N=30 for ship gate
- Before running eval, verify cap-window domain matches lineage label (R/C ratio check)
- Use `find_cap_start(msgs, cap_tokens)`, never `msgs[-N:]` or a percentage approximation

## SQLite WAL generation bug on the fork profile

The fork venv's `sqlite3` C extension is compiled against SQLite 3.53.1 (the version with the WAL-reset bug fixed), but at runtime it dynamically links to the **system** `libsqlite3.so.0` which may be an older vulnerable version (e.g. 3.51.2 on Fedora 44). `sqlite3.sqlite_version` reports the compile-time version, so `is_sqlite_wal_reset_vulnerable()` returns `False` even though the runtime library has the bug. WAL mode is enabled, and any gateway restart does a WAL-init TRUNCATE checkpoint that replaces the WAL/SHM inodes — leaving prior connections holding deleted FDs. This triggers `DeletedWalGenerationError`, sessions divert to `.jsonl`, and the gateway auto-restarts into the same condition.

Diagnose the mismatch:

```bash
# Compile-time version (what Python reports — may be wrong):
~/.hermes/hermes-fork/venv/bin/python3 -c "import sqlite3; print(sqlite3.sqlite_version)"

# Runtime version (what actually runs):
rpm -qi sqlite-libs | grep Version
# Or portable:
python3 -c "import ctypes; lib = ctypes.cdll.LoadLibrary('libsqlite3.so.0'); lib.sqlite3_libversion.restype = ctypes.c_char_p; print(lib.sqlite3_libversion())"
```

If runtime version < 3.52.0, the WAL-reset bug is present regardless of what `sqlite3.sqlite_version` reports.

Fix — switch the fork profile to DELETE journal mode (no WAL/SHM files, no inode-replacement risk):

```yaml
# ~/.hermes/profiles/fork/config.yaml
database:
  journal_mode: delete
```

Then, while no process holds the DB open, checkpoint and switch mode:

```python
import sqlite3
c = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
print(c.execute('PRAGMA integrity_check').fetchone())  # must be ('ok',)
c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
c.execute('PRAGMA journal_mode=DELETE')
c.close()
```

Pitfall: do NOT kill the gateway with `kill -TERM` to fix this — systemd auto-restarts it and the new process immediately re-triggers the condition. Use `systemctl --user stop hermes-gateway-fork.service` first, apply the DB + config fixes, then restart.

Pitfall: before removing retired-wal artifact directories, confirm every artifact's `change_counter` in `manifest.json` matches the live DB's change_counter (`PRAGMA schema_version` or the manifest field). Matching counters + `mode=copied` = safe to remove; a higher counter in the artifact means frames need inspection via `hermes --profile fork sessions recover --source <artifact>/state.db --inspect-only`.

## Wiring Sprint Procedure (closing architecture bottlenecks)

When closing named bottlenecks in ARCHITECTURE.md:

1. **Write script** — stdlib-only, `if __name__ == '__main__': main()` block, all cache writes guarded with `mkdir(parents=True, exist_ok=True)`.
2. **AST-validate immediately** — `python3 -c "import ast; ast.parse(open('script.py').read()); print('OK')"`.
3. **Check forward references** — if the script calls a function, find both def_lineno and call_lineno; assert def_lineno < call_lineno before committing.
4. **Add a real cron entry** — `{"kind": "cron", "expr": "..."}` not `{}`. Grep for `"schedule": {}` after every jobs.json write.
5. **Wire the live call site** — a function defined in script A but never imported by script B is dead code. Cross-grep the scripts dir for the function name and confirm at least one call site outside the definition file.
6. **Steer sibling subagents away from conflicting edits** — when a parent fixes a cron entry, steer the subagent that owns that section to skip the now-resolved step.
7. **Run the cold adversarial review AFTER all fixes land** — dispatch one cold subagent with no coaching; it reads every changed file fresh. Apply all confirmed HIGH findings before marking the sprint done.
8. **Update ARCHITECTURE.md bottleneck status** — only mark FULLY CLOSED when: script exists + cron fires + live call site confirmed + cold reviewer found no HIGH issues for that bottleneck.

### Dynamic import pattern (importlib.util)

When one Hermes script dynamically imports another at runtime:

```python
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('module_name', '/path/to/script.py')
assert _spec is not None   # spec_from_file_location returns Optional[ModuleSpec]
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
```

Do NOT use walrus operator in the exec_module call — Pyright flags it and it obfuscates ownership. Always assert spec is not None before module_from_spec. Wrap the entire block in `try/except Exception: pass` so import failure never crashes the caller (shadow pattern).

## Known open TODOs (do not close without a test)

- `context_compressor.py` line ~2826: `# TODO: consider lowering rearm if the new floor is more aggressive.`
  When a plugin calls `set_compression_profile` with a tighter `proactive_prune_tokens`, the rearm
  threshold is left intact on purpose (to avoid cache-break immediately). The result: the first proactive
  prune after a profile switch still fires at the OLD rearm point. If you tighten the floor significantly,
  add: `compressor._proactive_rearm = max(compressor._proactive_rearm, new_floor + 1)` in
  `set_compression_profile()`. Write a test before closing.

## Why-comments (do not delete without evidence)

- research `protect_last_n=15` not 25 — bulky dumps; 25 would shield stale tool_results
- `_MIN_SIGNAL=1` not 2 — 2 is too strict for short messages
- research lambda `0.55` not `0.7` — Phase-1 exec-state already holds web_extract
- `agent=` on `pre_llm_call` — prevents a global singleton (wrong session in gateway)
- `PluginManager._agent` is a weakref — allows GC of finished sessions

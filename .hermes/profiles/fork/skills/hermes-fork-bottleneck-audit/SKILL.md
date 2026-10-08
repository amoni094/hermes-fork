---
name: hermes-fork-bottleneck-audit
description: Use when finding hermes-fork bottlenecks. Recon + patch.
triggers:
  - fork scripts fail with NameError or ImportError
  - cron jobs hitting wrong profile or home directory
  - skill-router-index finding wrong number of skills
  - nested os.environ.get anti-pattern in scripts
  - state.db freelist bloat
category: autonomous-ai-agents
---

# Hermes Fork Bottleneck Audit

## Wave 17 Update (2026-10-07) — COMPLETE, 3 adversarial waves, 0 remaining H/M

### HERMES_HOME path-doubling pattern (systemic)
Cron jobs set HERMES_HOME to the fork profile root (/.../.hermes/profiles/fork), but many
fork scripts appended 'profiles/fork/' again, producing doubled paths. Pattern to detect:
    grep -r '_HERMES_HOME / .profiles/fork' profiles/fork/scripts/
Fix: compute _FORK_ROOT once at module top:
    _hh = str(_HERMES_HOME)
    _FORK_ROOT = _HERMES_HOME if ("profiles" in _hh and _hh.endswith("fork")) else _HERMES_HOME / "profiles/fork"
Then use _FORK_ROOT for all fork-specific paths. Affected scripts in Wave 17:
    graphiti-edge-health.py, skill-shadow-registry.py, execution-integrity-guard.py,
    mcp-auth-drift-check.py, catastrophic-forgetting-guard.py, session-resource-audit.py,
    fork-state-vacuum.py (7 total). Scan for new scripts each wave.
Also check for doubled logs tree: profiles/fork/profiles/fork/logs/ — migrate and delete.

### session-resource-audit false-positive patterns
- Perpetual scheduled cron jobs (no end_date/max_runs) are NOT unaudited resources — skip them.
  Only flag one-shot (run_once or schedule.kind=once) jobs without expiry.
- Missing expiry columns in tracegrant_grants schema means TTL policy not implemented yet —
  skip grant expiry flagging when no expiry column exists (_schema_has_expiry guard).
- Corrupt exec-integrity.jsonl entries (tool_name='t', no session_id, no call_id from 2026-09-22)
  were pre-existing; clean with filter: remove entries where len(tool_name)<=2 and no call_id/session_id.
- Replace datetime.utcnow() with datetime.now(timezone.utc) to suppress DeprecationWarning.
- Upstream merge: 20 commits from upstream-agent/main; 1 conflict (mem0 plugin deletion) resolved
- VACUUM state.db: 159MB -> 83MB, 75MB freelist eliminated
- 11 non-atomic write targets fixed (tmp+replace); 51 pre-existing Wave 16 spurious-paren bugs fixed
- Script compile: 348/348 CLEAN
- Fork skill index: 5 ghosts removed (44/44)
- Cron sandbox: 6 blocked jobs fixed (5 wrappers created in fork/scripts, 1 path corrected)
- se-gos-graphiti-bridge wrapper retargeted at hermes-scripts (skill path was deleted)
- memory-provenance.py NameError fixed (import os added)
- session-resource-audit no longer fails when tracegrant schema lacks expiry columns

## Wave 16 Update (2026-10-05)
- 6 new Wave 16 scripts added to hermes-scripts/
- 6 new skills: statecomp-compression-timing, ripple-mem-recall, bps-skill-budget, progress-mirage-verification, evograph-skill-health, cmtf-tool-filtering
- 5 new cron jobs (total: 57)
- 17 atomic-write fixes (bare write_text -> tmp+replace) across monitor scripts
- RippleMem graph seeded (39 nodes, 0 edges at low ALPHA=0.65 threshold)
- Skill index: 44 skills indexed
- ACCEPTED: delegate_task subagent spawn broken (ssl_guard) — investigate in fresh session

Use when finding and fixing bottlenecks in the fork profile scripts, crons, and skill routing.

## Quick Recon

```bash
# 1. Compile check (should be 0 failures)
python3 - <<'PY'
import pathlib, py_compile
for d in [pathlib.Path.home()/'.hermes/scripts', pathlib.Path.home()/'.hermes/profiles/fork/scripts']:
    for f in d.glob('*.py'):
        try: py_compile.compile(str(f), doraise=True)
        except Exception as e: print(f"FAIL: {f.name}: {e}")
print('Done')
PY

# 2. Cron wiring check
python3 - <<'PY'
import json, pathlib
jobs = json.loads((pathlib.Path.home()/'.hermes/profiles/fork/cron/jobs.json').read_text())
jobs = jobs if isinstance(jobs, list) else jobs.get('jobs', [])
for j in jobs:
    env = j.get('env', {})
    if not env.get('HERMES_PROFILE') or not env.get('HERMES_HOME'):
        print(f"BAD: {j.get('id','?')[:8]}: profile={env.get('HERMES_PROFILE','MISSING')} home={env.get('HERMES_HOME','MISSING')}")
print('Done')
PY
```

## Known Pitfalls (2026-09-28)

### HERMES_HOME must be root, not profile path
HERMES_HOME must ALWAYS be the hermes root (`~/.hermes`), never the profile path. When
HERMES_HOME already contains `/profiles/`, the path calculation in skill-router-index.py
doubles up: `~/.hermes/profiles/fork/profiles/fork/`.
Fix applied: `_true_hermes_base_sri` strips to the root if `/profiles/` detected.

### Nested os.environ.get pattern (~150 scripts)
Pattern: `Path(os.environ.get("HERMES_HOME", str(Path(os.environ.get("HERMES_HOME", str(...))))))`
This pattern nests up to 3-4 levels. Regex fails. Use a balanced-paren collapser:
- Find the outermost `Path(os.environ.get("HERMES_HOME",` call
- Walk chars counting parens to find the end
- Extract the innermost default value
- Replace whole expression with `Path(os.environ.get("HERMES_HOME", INNERMOST))`
Needs multiple passes for triple/quadruple nesting.

### Import alias: `import os as _os`
Scripts that do `import os as _os` but use bare `os.environ.get()` fail with NameError.
Fix: change to `import os`.

### Cron env wiring
All cron jobs MUST have both:
```json
"env": {"HERMES_PROFILE": "fork", "HERMES_HOME": "/var/home/rainbow/.hermes"}
```

### skill-router-index --build CLI guard
The skill-router-index.py prints a PAC-Bayes example unless `HERMES_CRON_BUILD=1` is set.
Cron jobs calling this script must include `HERMES_CRON_BUILD=1` in env.

### Fork skills use flat structure
Fork-specific skills: `~/.hermes/profiles/fork/skills/SKILL_NAME/SKILL.md`
NO category subdirs for fork skills.

### state.db freelist bloat
Default state.db can accumulate 87%+ free pages (~142MB waste).
Fix: `conn.execute('VACUUM')` on `~/.hermes/state.db`.
Check with `PRAGMA freelist_count`.

### Stale __pycache__ bytecode in fork/scripts/
Stale .pyc files can shadow corrected scripts. After edits:
```bash
find ~/.hermes/profiles/fork/scripts/__pycache__ -name '*.pyc' -delete
```

### Audit Scope: Always scan BOTH script dirs
When checking for missing/broken scripts:
- Main scripts: `~/.hermes/scripts/` (258 .py files)
- Fork scripts: `~/.hermes/profiles/fork/scripts/` (58 .py files)
Scanning only the main dir misses fork-specific scripts.

### Dead function detection: sys.exit(1) counts too
scripts can signal failure via `sys.exit(1)` not just `return 1`. Both patterns must
be checked when verifying that a gate function actually raises an error on failure.

### Wave 16 spurious-paren corruption (pre-existing)
51 files in ~/.hermes/scripts/ have a broken multi-line atomic-write pattern from Wave 16:
    _tmp_X.write_text(json.dumps({))
        "key": val,
    }, indent=2))
The extra )) after the { opens the outer write_text before the dict is complete.
Fix: remove the )) from the end of the `write_text(json.dumps({` line.
Detect: `grep -rn 'write_text(json.dumps({))' ~/.hermes/scripts/`
Fix script: fix_spurious_paren.py in scratch dir pattern.
After fixing, also check for remaining `_tmp_\w+\.(write_text)\(json\.dumps\(\{` lines
that still have unbalanced parens (paren-fixer may have added ) to already-broken lines).

### Skip *-alarm.json false positives
Alarm JSON filenames written by alarm-aggregator.py are never imported by name in
Python source. The glob `alarm-aggregator` writes matches `*-alarm.json`. Treating
unmatched alarm filenames as dead output is a confirmed false-positive class.

### Skill routing audit: check BOTH fork and default indexes
Fork index: `~/.hermes/profiles/fork/cache/skill-router-index.json`
Default index: `~/.hermes/cache/skill-router-index.json` (separate, may be stale)
The audit must diff indexed names against on-disk SKILL.md count for BOTH.

### related_skills must include hermes-fork-audit-pitfalls
Always load hermes-fork-audit-pitfalls alongside this skill to avoid re-discovering
alarm-file and fork/scripts false positives.

## Severity Classification

- CRITICAL: script import errors (NameError/ImportError) → immediate fix
- HIGH: cron wiring missing HERMES_PROFILE/HOME → fix all before next cron run
- MED: nested os.environ.get → functional but fragile
- LOW: skill index collision warnings (fork-priority first-seen handling is correct)

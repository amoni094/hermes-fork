---
name: hermes-fork-wiring-sprint
description: "Use when closing Hermes fork bottlenecks in a wiring sprint."
tags: [hermes, fork, wiring, architecture, scripts]
related_skills:
  - hermes-fork
  - hermes-system-audit
  - adversarial-review
---

# Hermes Fork Wiring Sprint

Procedure and confirmed pitfalls for closing architecture bottlenecks in the Hermes
fork profile. Bottleneck status lives in `~/.hermes/profiles/fork/ARCHITECTURE.md`.

Scripts: `~/.hermes/scripts/`
Cache: `~/.hermes/cache/`
Cron: `~/.hermes/cron/jobs.json`
Plugins: `~/.hermes/hermes-fork/plugins/user/`

## Closure Checklist (per bottleneck)

A bottleneck is FULLY CLOSED when ALL of these pass:

1. Script exists and AST-validates:
   `python3 -c "import ast; ast.parse(open('script.py').read()); print('OK')"`
2. Forward-reference check: def_lineno < call_lineno for every function called in `__main__` block.
3. Live call site exists in a DIFFERENT script (cross-grep confirms it fires):
   `grep -rn 'function_name' ~/.hermes/scripts/ | grep -v 'def function_name'`
4. Cron entry has a real schedule — not `{}`. Grep: `"schedule": {}` must return nothing.
5. Cold adversarial reviewer found no HIGH findings for this bottleneck.
6. ARCHITECTURE.md bottleneck row updated to FULLY CLOSED.

Do NOT update ARCHITECTURE.md to FULLY CLOSED until all 6 pass.

## Shadow Compliance Rules

All new code in existing scripts must be shadow-wrapped (`try/except Exception: pass`).
The shadow wrapper MUST NEVER:
- Call `sys.exit()` — terminates process before `finally` runs, leaks lock FDs
- Call `raise SystemExit` — same effect
- Reference an undefined name — NameError inside except propagates uncaught

For lockfile patterns, use a module-level bool flag + atexit release:

```python
import atexit, fcntl, os, sys
_LOCK_PATH = '/tmp/script-name.lock'
_LOCK_FD = None
_LOCK_HELD = False
try:
    _LOCK_FD = open(_LOCK_PATH, 'w')
    fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
    _LOCK_HELD = True
    atexit.register(lambda: (_LOCK_FD.close(), os.unlink(_LOCK_PATH)))
except BlockingIOError:
    print('[script-name] already running, skip', file=sys.stderr)

def main():
    if not _LOCK_HELD:
        return  # another instance is running
    # ... rest of main
```

Audit: `grep -n 'sys.exit' ~/.hermes/scripts/*.py | grep -v '#'`
All matches inside except blocks are violations — replace with `return`.

## Non-Atomic Write Pattern (Required for ALL state files)

Bare `path.write_text(json.dumps(data))` is NOT atomic. A crash between truncation
and final write leaves a zero-byte file, resetting all learned state.

Required pattern:
```python
_tmp = CACHE_PATH.with_suffix('.tmp')
_tmp.write_text(json.dumps(data, indent=2))
_tmp.rename(CACHE_PATH)  # POSIX rename — atomic within same filesystem
```

Applies to all shared state files:
- `routing-weights.json` — FTRL routing weights
- `trust-posterior.json` — Beta-Binomial trust posteriors
- `condorcet-thresholds.json` — calibration thresholds
- `adaptive-ttl-state.json` — MRAS adaptive TTL
- Any `*.json` in `~/.hermes/cache/` written by cron scripts
- `staging.md` — memory staging file

Audit: `grep -rn 'write_text(json.dumps' ~/.hermes/scripts/`
Every match must be preceded by a `.tmp` write + `.rename()` on the next lines.

## Closure Overclaim: Function Defined but Never Called

A subagent that writes script A cannot add a call site in script B it doesn't own.
The call site silently goes missing and ARCHITECTURE.md gets false FULLY CLOSED status.

Post-sprint call-site audit (run before any ARCHITECTURE.md update):
```bash
for fn in update_trust_posterior audit_tool_result _update_bandit_state route_with_weights; do
    count=$(grep -rn "$fn" ~/.hermes/scripts/ | grep -v "def $fn" | wc -l)
    echo "$fn call sites (ex def): $count"
done
```
Expected: >=1 per function. Zero = dead code = bottleneck still OPEN.

## Parallel Subagent Dispatch (bottleneck implementation)

When implementing 3+ bottlenecks simultaneously via delegate_task:

- Each subagent owns a disjoint set of files. Never assign the same file to two subagents.
- Pass explicit absolute file paths — subagents cannot see parent-session context.
- Steer sibling subagents to skip steps the parent has already resolved.
- Dispatch the cold adversarial reviewer AFTER all implementation subagents complete.
- Cold reviewer gets file paths only — no coaching, no problem-statement summary.

## Cron Entry Format

A cron job entry in `jobs.json` must have a real schedule or it silently never fires:

```json
{
    "id": "my-script-0001",
    "schedule": {"kind": "cron", "expr": "0 7 * * *"},
    "script": "my-script.py",
    "no_agent": true
}
```

`"schedule": {}` — missing `kind` or `expr` — is registered but never enqueued.
Grep after every jobs.json write: `grep '"schedule": {}' ~/.hermes/cron/jobs.json`

Always validate JSON after any programmatic write:
`python3 -c "import json; json.load(open('/var/home/rainbow/.hermes/cron/jobs.json')); print('OK')"`

## Dynamic Import Pattern (importlib.util)

When one script dynamically imports another at runtime:

```python
import importlib.util as _ilu
try:
    _spec = _ilu.spec_from_file_location(
        'memory_provenance',
        pathlib.Path('~/.hermes/scripts/memory-provenance.py').expanduser()
    )
    assert _spec is not None
    _mod = _ilu.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
except Exception:
    _mod = None  # fail-open: caller checks _mod before use
```

Call site resolution — use locals/globals to avoid UnboundLocalError if import failed:
```python
_mp_ref = locals().get('_mp') or globals().get('_mp')
if _mp_ref and hasattr(_mp_ref, 'update_trust_posterior'):
    _mp_ref.update_trust_posterior(source, reward)
```

## Post-Sprint Verification Script

Run before updating ARCHITECTURE.md or dispatching the cold reviewer:

```bash
# 1. AST check all scripts
for f in ~/.hermes/scripts/*.py; do
    python3 -c "import ast; ast.parse(open('$f').read())" && echo "OK: $(basename $f)" || echo "FAIL: $f"
done

# 2. Call-site audit
for fn in update_trust_posterior audit_tool_result _update_bandit_state route_with_weights; do
    count=$(grep -rn "$fn" ~/.hermes/scripts/ | grep -v "def $fn" | wc -l)
    echo "$fn call sites: $count"
done

# 3. Cron schedule check
grep '"schedule": {}' ~/.hermes/cron/jobs.json && echo 'BAD SCHEDULES FOUND' || echo 'OK'

# 4. Non-atomic write check
grep -rn 'write_text(json.dumps' ~/.hermes/scripts/ | grep -v '.tmp'

# 5. sys.exit in non-main code
grep -n 'sys.exit' ~/.hermes/scripts/*.py | grep -v '#'
```

All checks must return clean before dispatching the cold adversarial reviewer.

---
name: hermes-plugin-wiring-audit
description: "Use when auditing hermes-fork plugin wiring post-build."
---

# Hermes Plugin Wiring Audit

Use after building or modifying hermes-fork plugins, before declaring implementation
complete. The author cannot audit their own wiring — delegate cold.

## Procedure

### Step 1: Inline ad-hoc verification (parent, parallel)

Run immediately in execute_code while the cold subagent is dispatched. Catches compile
failures and obvious policy table issues without waiting for the delegation round-trip.
Also run the five wave-level bug patterns (see below) against all changed files
before the cold agent returns — these are fast to check and fix, so doing them inline
lets you apply patches and recompile before the cold agent finishes.

    from hermes_tools import terminal
    import importlib.util, py_compile, ast
    from pathlib import Path

    # Compile check
    for p in CHANGED_FILES:
        py_compile.compile(p, doraise=True)

    # Import check
    spec = importlib.util.spec_from_file_location('_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # raises ImportError/SyntaxError if broken

    # Policy table spot-checks (example for tool-auth-gate pattern)
    hook = mod._make_pre_tool_call_hook(ctx)
    assert hook('read_file', {'path': '/x'}) is None         # fast-path
    assert hook('write_file', {'path': '/etc/passwd'})['action'] == 'approve'  # escalate

### Step 2: Cold wiring subagent (delegate_task, background)

Dispatch in parallel with Step 1. Subagent context must include:
- List of changed files with their roles
- The eight checklist sections (A–H below)
- Explicit: AUDIT ONLY, do NOT fix anything
- Structured output: section letter, PASS/FAIL, findings with severity

Wiring checklist sections:

  A. COMPILE: py_compile + importlib load each changed .py
  B. POLICY CORRECTNESS: load module, run functional hook test cases
     covering every distinct code path (fast-path, escalation, hard-deny)
  C. BUDGET SEPARATION: each consumer has its own named budget file;
     no import of shared budget functions from other plugins
  D. SHADOW COMPLIANCE: post_llm_call returns None unconditionally;
     try/except wraps entire hook body (H-I7); reentrance sentinel present;
     no conversation_history.append/insert anywhere in hook
  E. GOVERNANCE LOG: ledger is a file not a dir; expected proposals present;
     `governance list` command exits 0
  F. DARK OUTPUT: list any JSONL written with no consumer (flag as INFO;
     acceptable for observability instruments, must be noted)
  G. CONFIG STATE: disabled-by-default plugins absent from plugins.enabled;
     shadow flags absent from config.yaml
  H. ARCHITECTURE.md: documented state matches actual code
  J. CALL-SITE ARGUMENT WIRING: any constant defined in a module (e.g. `DPI_TOKEN_BOUND = 512`, `FAIL_BOUND = 0.1`) but never passed as an argument to the function it gates is dead code. Grep all call sites of the gating function and confirm the constant appears as a kwarg. A constant defined at module level that is not referenced in any function call is a silent no-op — the gate runs with the function’s default, not the module-level value.

  K. CTX.GET_CONFIG NESTING: `ctx.get_config(key)` in hermes-fork reads `plugins.entries.<id>.settings.<key>` first, then `.config.<key>`, then returns None. Keys placed at the root of the plugin’s config.yaml entry (not under `.settings`) are never returned, so the hook silently uses its default (typically False/None). After enabling any plugin that uses `ctx.get_config`, verify the config.yaml entry has a `.settings` block with the expected keys nested inside it.

  Note: `PluginContext` has NO `.config` attribute — `getattr(ctx, 'config', {})` always returns `{}`. Plugins that walk `raw.get('plugins', {}).get('entries', ...).get('settings', {})` via this stub will silently use defaults for every config key. The correct call is `ctx.get_config(key, default)` per key. For nested keys like `thresholds.tool_result`, call `ctx.get_config('thresholds.tool_result', default)` only if PluginContext supports dotted paths (verify from source at `~/.hermes/hermes-agent/hermes/plugins/context.py`); otherwise call `ctx.get_config('thresholds', {})` then `.get('tool_result', default)` on the result.

  M. PLUGIN SCRIPT PATH RESOLUTION: plugins that reference companion scripts (e.g. `jev_verify_fn.py`) must resolve the scripts directory relative to the TRUE hermes root, not `HERMES_HOME`. When fork sessions set `HERMES_HOME=/var/home/rainbow/.hermes/profiles/fork`, a naive `Path(HERMES_HOME)/"scripts"` resolves to the profile's scripts dir, not `~/.hermes/scripts` where the shared scripts live. Correct pattern: strip the `profiles/<name>` pair if present:

      def _hermes_root() -> Path:
          hh = os.environ.get("HERMES_HOME", "").strip()
          base = Path(hh) if hh else Path.home() / ".hermes"
          if base.parent.name == "profiles":
              return base.parent.parent
          return base

      _SCRIPTS = _hermes_root() / "scripts"

  This is the same pattern used in `memory-ransac-gate`. Apply it to any plugin that references shared scripts under the global hermes install.

  L. CRON JOB COMPLETENESS — for each script-only cron job:
     - `no_agent: true` must be set (prevents agent pool spawn for script-only work).
     - Producer jobs must be scheduled strictly before their consumer jobs. A consumer that reads a DB written by a producer must run at least one schedule window after the producer; sharing the same cron time is a race. Default to: producer at HH:30, consumer at HH+1:00.
     - When adding a consumer job, verify a producer job exists and is scheduled in jobs.json. A consumer with no producer job writes an empty/stale DB every run.

     - *Null-script jobs*: jobs in jobs.json with script=None. These are silently skipped by the scheduler. Either delete them or assign a real implementation.
     - *Orphan writer*: a hermes-scripts/ file that writes a DB column (e.g. doob_strata) with no downstream consumer in any other script or plugin. Consumer must be shipped in the same wave as the writer.
     - *Uncalled gate*: a script named `*-gate.py` or `*-guard.py` that exits 0 with no callers — no cron job, no import, no subprocess call. Either wire a caller or document it as a library-only utility and rename accordingly.
     - *Core override*: when proposing a SQLite PRAGMA change (e.g. journal_mode=WAL), first grep hermes-fork source for that pragma. If the core sets it on open, the PRAGMA migration reverts on next agent startup and the fix is futile. The fix must patch the hermes-fork open call, not just run a one-time SQL command.

### Step 3: Triage findings

Only MEDIUM and above block release. LOW and INFO are logged but do not
stop implementation. CRITICAL and HIGH require immediate fix + re-audit
(spawn a second cold subagent for the affected sections only).

## Wave-Level Bug Patterns (check these first in every audit)

These patterns recur across waves and each produces a silent failure:

**Broken relative import stub** — a 35-byte plugin `__init__.py` containing only
`from .plugin import post_tool_call` with no `plugin.py` in the package directory
crashes on import with `ModuleNotFoundError`. The plugin is listed in `plugins.enabled`,
Hermes loads it, and swallows the ImportError — leaving the hook permanently absent
with no logged warning. Always `importlib.util.spec_from_file_location` + `exec_module`
to confirm every enabled plugin actually loads. A file smaller than ~200 bytes in a
plugin directory is almost always a broken stub.

**Symlink bypass via `os.path.abspath`** — any path-matching gate (governance-hard-block,
tool-auth-gate, cobra-guard) that uses `os.path.abspath` to normalise paths does NOT
resolve symlinks. A symlink at `/tmp/cfg -> /profiles/fork/config.yaml` passes every
check. Always use `os.path.realpath(os.path.abspath(p))` in `_norm_path`. Verify with
a test that creates a real symlink and confirms it is blocked.

**Tmp-rename bypass** — a path-matching pattern like `r"config\.yaml$"` blocks writes
to `config.yaml` but not `config.yaml.tmp`. The atomic write pattern (write to `.tmp`,
then `rename`) means the write_file call hits `.tmp` (unblocked) and the rename call
hits `config.yaml` via a terminal command that may only be partially scanned. Extend
every HIGH-risk path pattern with `(\.tmp)?$` — e.g. `r"(?i)config\.ya?ml(\.tmp)?$"`.

**UCB / bandit cold-start safety hole** — two distinct failure modes:

  a) Arms with `n=0` skip the check when the condition is `if n > 0 and p_fail > threshold`. Add an explicit `n=0` early-return path that allows exploration (return True), never falling through to stale-timestamp checks.

  b) Laplace smoothing with a tight `FAIL_BOUND` (e.g. 0.1) blocks clean cold-start arms: `(0+1)/(0+2) = 0.25 > 0.1` — arm blocked with zero failures. Do NOT use a fixed-threshold Laplace gate for low-sample arms. Correct heuristic for `n < UCB_MIN_SAMPLES`: block only if (majority-failing: `n >= 3 AND failures/n > 0.5`) OR (unanimous-failing: `n >= 1 AND failures == n`); otherwise return True. Stale-timestamp check applies only to `n >= UCB_MIN_SAMPLES`.

  Test matrix (9 cases): `(f=0,n=0,ts=None)→True`, `(0,1,recent)→True`, `(0,2,recent)→True`, `(1,1,recent)→False`, `(2,2,recent)→False`, `(9,9,recent)→False`, `(5,9,recent)→False`, `(1,2,recent)→True`, `(1,3,recent)→True`.

**Subprocess gate positional vs keyword args** — scripts that invoke a gate via `subprocess.run([PYTHON, GATE_SCRIPT, "--task", task, ...])` break when the gate uses argparse positional arguments (not `--task`). Check argparse definitions in gate scripts: positional means pass as `[PYTHON, GATE_SCRIPT, task, ...]`, not `[..., "--task", task, ...]`. Add fail-closed error handling: when the gate subprocess returns an unexpected exit code or produces no parseable JSON, return `{"decision": "DEFER", ...}` rather than raising or returning a commit. Filter for JSON lines with `l.strip().startswith("{")` to handle mixed stdout from gate scripts that also print diagnostics.

**Non-atomic JSON write in fork/scripts wrappers** — `path.write_text(json.dumps(...))`
is not atomic. On crash mid-write the file is truncated and unreadable, causing the
next consumer to exit with `JSONDecodeError`. Pattern: always write to `.tmp` first,
then `rename`: `_tmp = dest.with_suffix(".tmp"); _tmp.write_text(...); _tmp.rename(dest)`.
This applies to every script that produces a report JSON consumed by another script or plugin.

**Queue load non-list guard** — any script that reads a shared JSON queue file (e.g. `pending-fanout-queue.json`) must guard against valid JSON that is not a list (a dict or string from a corrupt write). Always: `loaded = json.loads(text); existing = loaded if isinstance(loaded, list) else []`. Without this, `for item in existing` iterates over dict keys and every downstream operation corrupts the queue silently.

**Encode+write bypass in security gates** — a chr()/fromhex()/b64decode()/bytes([])/eval()/exec()-based encode+write pattern bypasses any static token scan (no `config.yaml` literal appears in the code). The `_ENCODE_PATTERN` ⊔ `_WRITE_RENAME` deny must fire on BOTH `execute_code` AND `terminal` tool calls — `python -c 'bytes.fromhex(...).decode(); open(...)'` is an equally valid attack vector. Common gaps: `chr(0x63)` (hex literal, not decimal) misses `\bchr\s*\(\s*\d+\s*\)`; `''.join(chr(c) for c in [...])` misses because no decimal literal; `shutil.copy2`, `shutil.move`, `os.write`, `json.dump`, `os.system`, `os.symlink` absent from `_WRITE_RENAME`; `eval()`/`exec()` not in `_ENCODE_PATTERN`. Extend `_ENCODE_PATTERN` to match bare `chr\s*\(` (no `\d+` constraint). For the full catalogue of mode-class FPs, shell redirect anchoring rules, dynamic-mode chr() comma-anchoring, and fd-redirect patterns (2>, &>), see the `recursive-adversarial-hardening` skill item 19 — those rules are maintained there as the authoritative reference.

## Pitfalls

Pitfall: string-literal checks in verify scripts are brittle across Python quote styles. A check like `'GATE_SCRIPT, task, "--json-output"' not in src` fails if the source uses single quotes internally. Use regex or AST to check structural patterns in subprocess call lists; use source substring checks only for content that cannot vary by quoting style (e.g. flag names like `"--task"` that must be absent regardless of quote style).

Pitfall: regex path patterns double-escaped in raw strings silently match the wrong thing. `r"\\.hermes"` in a raw string produces the regex `\.hermes` which matches a literal backslash then any char, NOT `.hermes`. Always verify a compiled path regex against a real test path before shipping. Prefer non-raw strings for path patterns where dots must match literally: `re.compile(r"[.].hermes")` vs `re.compile(r"\\.hermes")`.

Pitfall: `exec(open('file').read())` without a write-mode open fires both ENCODE (`exec(`) and WRITE (`open(`) patterns — a false positive. Anchor the open-for-write pattern to write mode: `\bopen\s*\([^)]*['"]w` so `open('f')` and `open('f', 'r')` are excluded. Similarly, `str.replace('a','b')` fires a bare `\.replace\s*\(` WRITE pattern. Use `\bos\.replace\b` and `\bPath\.replace\b` with explicit prefix.

Pitfall: grep and raw string search produce false positives on comment-only references.
Always use AST parse to verify import presence or absence — never `'X' in src`.

    import ast
    tree = ast.parse(src)
    real_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            real_imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            real_imports.add(node.module)
    # Now: 'jev_verify_fn' in real_imports  (not: 'jev_verify_fn' in src)

A 'does NOT import X' assertion that fails on a file where X only appears in a
docstring is a bad test, not a real violation. Fix the test before filing a finding.

Pitfall: a 'does NOT reference budget file' check must exclude comments and
docstrings. Build the AST string-literal set or strip comments first.

Pitfall: the inline Step 1 check and the cold subagent Step 2 check can disagree
if one uses raw string search and the other uses AST. When they disagree, AST wins.

## skill_manage create — frontmatter constraints

The description field in SKILL.md frontmatter must be <= 57 chars. Longer values
fail with a truncation/validation error. Write description as a short trigger phrase;
put all detail in the SKILL.md body.

Example of the failure:
  description: "Use when implementing JEV/System One patterns in hermes-fork, ..."
  -> fails: 'Description is 266 c...'

Fix: shorten to <= 57 chars:
  description: "Use when designing JEV harness patterns."

## Wiring Audit vs Design Audit

Design audit (recursive-adversarial-hardening skill): runs on specs/proposals BEFORE
code is written. Catches architectural impossibilities, budget explosions, and
invariant violations at the design level.

Wiring audit (this skill): runs on built code AFTER implementation. Catches compile
errors, policy table gaps, shadow compliance failures, and config drift between
documentation and actual state.

Both are required. Design audit gates implementation; wiring audit gates deployment.

## Inventory Collection Before Dispatching Audit Subagent

Before dispatching the cold wiring subagent, collect the full inventory in execute_code so the subagent receives concrete paths and counts rather than globs it must resolve itself:

    jobs = json.loads((HERMES / "profiles/fork/cron/jobs.json").read_text())
    # jobs.json may be a dict with key 'jobs' or a bare list — normalise:
    actual_jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs

    plugin_dirs = [p.name for p in FORK_PLUGINS.iterdir() if p.is_dir()]
    enabled_plugins = cfg.get("plugins", {}).get("enabled", [])

Pass `len(actual_jobs)` and `enabled_plugins` explicitly in the subagent context string so the subagent can verify it checked all N jobs rather than stopping at a truncated subset.

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
     no conversation_history.append/insert anywhere in hook.
     For pre_tool_call specifically: a block dict MUST contain the key `"message"` (not `"reason"`). The dispatcher at `hermes_cli/plugins.py _get_pre_tool_call_directive_details` reads `result.get("message")` only — a dict with `{"action": "block", "reason": ...}` is silently ignored and the tool proceeds. Correct: `{"action": "block", "message": msg, "reason": msg}`. Verify by checking governance-hard-block and tool-auth-gate as reference implementations.

     Functional test for BLOCK: mock `v.check.return_value = "BLOCK"`, call the hook, assert `result["message"]` is a non-empty string. A test that only asserts `result["action"] == "block"` does NOT catch this bug.
  E. GOVERNANCE LOG: ledger is a file not a dir; expected proposals present;
     `governance list` command exits 0
  F. DARK OUTPUT: list any JSONL written with no consumer (flag as INFO;
     acceptable for observability instruments, must be noted)
  G. CONFIG STATE: disabled-by-default plugins absent from plugins.enabled;
     shadow flags absent from config.yaml
  H. ARCHITECTURE.md: documented state matches actual code.
     Every newly deployed plugin must appear in the 'Deployed Plugins (fork profile)' section of `~/.hermes/profiles/fork/ARCHITECTURE.md` with: hook name(s), behaviour summary, and any dark-output JSONL files it writes. Missing entries accumulate silently — check that ALL plugins in `config.yaml plugins.enabled` are documented, not just the one being audited.
  I. HOOK COMPLETENESS: for every hook the plugin intends to provide, verify that (a) `plugin.yaml provides_hooks` lists it, (b) `plugin.yaml hooks` lists it, and (c) `register()` calls `ctx.register_hook(hook_name, fn)` with the EXACT string. A hook that is provided in `provides_hooks` but not registered in `register()` is dead code — the plugin.yaml declaration is documentation only; only the `ctx.register_hook` call wires the hook. A hook added after plugin initial review (e.g. `transform_tool_result` added later) must be added to ALL THREE places or it will silently not fire.
  J. CALL-SITE ARGUMENT WIRING: any constant defined in a module (e.g. `DPI_TOKEN_BOUND = 512`, `FAIL_BOUND = 0.1`, `HHR_THRESHOLD = 0.35`) but never passed as an argument to the function it gates is dead code. When a module has BOTH a public constant (e.g. `HHR_THRESHOLD`) and a private alias (e.g. `_SPRT_H0_LOW = 0.35`) that is the actual value used by the function, the public constant is a dead alias — developer changes to it are silently ignored. Fix: make the private constant an alias for the public one: `_SPRT_H0_LOW = HHR_THRESHOLD`. Grep call sites with: `re.search(r'<fn_name>\([^)]*CONSTANT_NAME', src)` — zero matches = dead constant. Grep all call sites of the gating function and confirm the constant appears as a kwarg. A constant defined at module level that is not referenced in any function call is a silent no-op — the gate runs with the function’s default, not the module-level value.

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
     - **Missing argv = silent wrong behaviour**: a cron job entry with no `argv` field for a script that requires arguments runs with zero args. If `main()` calls `parser.error()` or `sys.exit(1)` when required args are absent, the job silently fails every run with no output file. Always add `argv` to the job entry. For scripts with log-based auto-detection mode, use `["--from-log"]`; for index-build scripts, use `["--build"]`.
     - **Inline-only scripts cannot be standalone cron jobs**: a script that requires live session data as file arguments (e.g. `--window FILE --new-chunk FILE`) exits 0 silently with no args (graceful no-op) but writes nothing — it cannot autonomously generate its own inputs from a cron schedule. These scripts are call-time tools, not periodic batch jobs. When one is registered as a cron job, it runs every interval and produces no output. Leave the job registration (it harms nothing — exits 0), but do not expect it to populate its output log; that log is populated only when the script is called inline during live session processing.
     - When adding a consumer job, verify a producer job exists and is scheduled in jobs.json. A consumer with no producer job writes an empty/stale DB every run.

     - *Null-script jobs*: jobs in jobs.json with script=None. These are silently skipped by the scheduler. Either delete them or assign a real implementation.
     - *Orphan writer*: a hermes-scripts/ file that writes a DB column (e.g. doob_strata) with no downstream consumer in any other script or plugin. Consumer must be shipped in the same wave as the writer.
     - *Uncalled gate*: a script named `*-gate.py` or `*-guard.py` that exits 0 with no callers — no cron job, no import, no subprocess call. Either wire a caller or document it as a library-only utility and rename accordingly.
     - *Core override*: when proposing a SQLite PRAGMA change (e.g. journal_mode=WAL), first grep hermes-fork source for that pragma. If the core sets it on open, the PRAGMA migration reverts on next agent startup and the fix is futile. The fix must patch the hermes-fork open call, not just run a one-time SQL command.
     - *Sandboxed job reading hermes-scripts/*: any sandboxed cron job whose wrapper calls `runpy.run_path(hermes_scripts_path)` will get `PermissionError` from landlock — `hermes-scripts/` is not bound in the openshell policy. Correct pattern: fork wrapper in `profiles/fork/scripts/` resolves the hermes-scripts target, and the cron job points directly at the fork wrapper (not the cron-sandboxed .sh). Spot-check: job `script` must be in `profiles/fork/scripts/`, not `profiles/fork/scripts/cron-sandboxed/` unless that .sh correctly binds hermes-scripts. See hermes-cron-sandbox-fixes → "Sandbox PermissionError" section.

  N. LOG FIELD SEMANTICS: for any boolean field in a plugin's dark-output JSONL, verify
     the value matches the field name's intuition. A field named `gated: true` that is set
     to `True` when the gate did NOT fire (i.e. compression proceeded unmodified) has
     inverted semantics — every downstream reader will misinterpret it. Rule: `gated`
     (or `blocked`, `fired`, `active`) should be `True` when the gate/block/event
     actually fired.

     However: `"gated": not (fire_full or fire_soft)` with an inline comment
     `# True = gate blocked, compression proceeds unmodified` is intentional — this
     encodes 'the gate is engaged / blocking', not 'compression fired'. Before flagging
     as inverted, check the accompanying comment and confirm the semantics are
     unambiguous to a downstream consumer. If the comment is absent or ambiguous, flag
     LOW and add a comment clarifying intended polarity. Do NOT require a rename unless
     the polarity is genuinely wrong after reading the comment.

  O. DUAL PLUGIN COPY SYNC: some plugins exist in TWO places — the live profile directory
     (`profiles/fork/plugins/<name>/`) AND the hermes-fork git repo's snapshot directory
     (`fork-profile/plugins/<name>/`). After any change to the live copy, verify the repo
     copy is synced before committing. A stale repo copy is LOW severity but confuses
     future sessions that clone the repo without the profile overlay. Sync command:

         cp /var/home/rainbow/.hermes/profiles/fork/plugins/<name>/__init__.py \
            /var/home/rainbow/.hermes/hermes-fork/fork-profile/plugins/<name>/__init__.py

     Check diff before committing: live and repo `__init__.py` must have equal line count
     and identical content (`python3 -c "assert open(live).read() == open(repo).read()"`).
     Commit the repo copy to hermes-fork separately (it's a different git repo) — this
     requires a pull-rebase if profiles/fork already pushed ahead: `git pull --rebase origin main && git push origin main`.

     Quick staleness check (run before each commit wave):

         import shutil
         live = PROFILE / 'plugins' / NAME / '__init__.py'
         repo = FORK / 'fork-profile' / 'plugins' / NAME / '__init__.py'
         if repo.exists() and live.read_text() != repo.read_text():
             shutil.copy2(live, repo)  # sync, then commit repo separately

  T. TOKEN-GATE VS TURN-GATE: when a plugin uses `turn_count` as the gate trigger,
     verify what the host ACTUALLY passes. On the `post_tool` overflow path,
     `fire_pre_compress` is called before `ContextCompressor.compress()` runs — at that
     point `agent._session_messages` is empty (messages for the current turn have not yet
     been appended), so turn_count=0 on every call. The depth gate never fires even at
     120k context tokens. Fix: add a `TOKEN_THRESHOLD` constant and gate on
     `context_tokens >= token_threshold` as a second condition:

         TOKEN_THRESHOLD = 100_000  # context_tokens is reliable on post_tool path

         def _check_gate(session_id, turn_count, conn, context_tokens=0):
             depth_threshold = _cfg_int("depth_threshold", TURN_THRESHOLD)
             token_threshold = _cfg_int("token_threshold", TOKEN_THRESHOLD)
             ...
             if turn_count >= depth_threshold or (context_tokens >= token_threshold > 0):
                 fire()

     Expose token_threshold in plugin.yaml settings and wire it through _cfg_int.
     Symptom of the missing token gate: JSONL log shows `context_tokens: 120000,
     turn_count: 0, skip: depth` on every compression call in a live session.

  U. HYSTERESIS STATE TYPE: when `_last_fire` stores bare int turn counts, hysteresis
     is broken for the token-gate path (turn_count=0 always). After firing,
     `_last_fire[sid] = 0`; on the next call `if last:` is falsy (0 is falsy), so
     hysteresis never applies — the gate fires on every compression call.
     Fix: store `(turn_count, timestamp)` tuples. Apply hysteresis in two modes:

         last_turns, last_ts = last_entry if isinstance(last_entry, tuple) else (last_entry, 0.0)
         elapsed = time.time() - last_ts if last_ts else float("inf")
         if turn_count > 0 and last_turns > 0:
             if (turn_count - last_turns) < HYSTERESIS_TURNS: return False, False
         else:  # token path or token→turn transition
             if elapsed < (HYSTERESIS_TURNS * 2): return False, False

     The else branch also covers the token→turn transition: after a token-triggered fire
     stores (0, ts), the next call with real turn_count=50 has last_turns=0, falls into
     the else branch, and is suppressed by the time check. Without this, the
     token→turn path re-fires immediately (last_turns=0 skips turn check; time check
     was gated on `turn_count==0` only in the naive version).

  V. LOGGED CONFIG VALUE MUST MATCH LIVE VALUE: when a plugin computes a live threshold
     via `_cfg_int('depth_threshold', TURN_THRESHOLD)` inside `_check_gate`, the JSONL
     log record must use the COMPUTED value, not the module constant. If pre_compress
     logs `"depth_threshold": TURN_THRESHOLD`, operator overrides via config.yaml are
     invisible in the log — the record always shows the hardcoded default. Fix: compute
     `depth_threshold = _cfg_int(...)` in pre_compress scope (not only inside
     _check_gate) so the same variable is available for both the _check_gate call and
     the log record. Pyright will catch the NameError if the variable is used in a
     return value but only defined inside a called function.

  P. HOOK-DATA CIRCUIT COMPLETENESS: for every plugin hook that READS from a data store
     (e.g. reads compaction_telemetry to compute HHR), verify there is a corresponding
     WRITER hook registered in the same plugin or in another enabled plugin that fires
     before the reader. A reader hook with no writer is permanently inactive — not a
     future-compat stub, an actual dead branch. Audit: for every SELECT on a table in a
     plugin's pre_compress/pre_tool_call/etc. handler, grep the full plugin corpus for
     INSERT INTO that table. Flag as HIGH if zero inserts found outside test fixtures.

     Activation pattern: register a second hook (`post_compaction`, `on_session_finalize`,
     etc.) in the same plugin's `register()` that writes the rows. Add both hook names to
     `plugin.yaml hooks:` and `provides_hooks:`. The writer must call
     `_ensure_<table>_schema()` (idempotent CREATE TABLE IF NOT EXISTS + index) before
     inserting — do not assume the schema exists from a prior call.

  Q. HHR THRESHOLD CALIBRATION: a head-hit-rate threshold of 0.10 requires the compressor
     to cut 90% of tokens before triggering — almost never fires in practice. The design
     intent is 0.35 (< 35% retained signals poor fidelity). After_tokens/before_tokens is
     the HHR ratio; check the module constant and confirm it matches the spec before
     shipping. Flag threshold values < 0.20 as suspicious and verify intent.

  R. AGENT HISTORY ATTRIBUTE EXHAUSTION: plugins that read the conversation history via
     `getattr(agent, 'conversation_history', None)` are broken against AIAgent, which
     stores messages as `_session_messages`. Audit: check every `_history(agent)` or
     equivalent helper. It must try (in order) `_session_messages`, `conversation_history`,
     `_messages`, returning the first non-empty list. A plugin that only reads
     `conversation_history` will always see `[]` on a live AIAgent — the gate appears
     to work in tests (mock has `conversation_history`) but never fires in production.
     The turn_count=always-0 bug is the canonical symptom.

  S. MESSAGES KWARG FORWARD-COMPAT SLOT: hooks that compute turn count or extract history
     should accept an optional `messages` kwarg so the host can pass a snapshot directly
     without the plugin having to reach into agent internals. Signature:
     `def pre_compress(agent=None, messages=None, **kw)`. When non-empty, `messages`
     takes priority over the agent attribute. This is a forward-compat slot — the host
     does not currently pass it, but the slot prevents a breaking signature change later.

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

**Unclassified-session bypass in transform_tool_result** — a plugin that gates
`transform_tool_result` on `session_type == "code"` (return early) and compresses
everything else will compress tool output during the opening turns of ANY session before
the classifier fires (session_type is `None`). This destroys diffs and stack traces that
appear early in code sessions. Correct gate: skip for `code`, `None`, and `unknown`;
compress only for `"research"` and `"mixed"` explicitly. Audit: check every
`transform_tool_result` implementation for the `None` case.

**Warm-start race in session-scoped state plugins** — a plugin that computes a
classification or score early in a session and only writes it at `on_session_finalize`
leaves the NEXT session unable to warm-start if the current session crashes before
finalize. Audit: for any plugin using `on_session_start` to load cached state and
`on_session_finalize` to persist it, verify there is ALSO a write at the point of first
classification/decision. The cron audit will produce a `cache/last-session-type.json`
(or similar) age alarm if the warm-start write is missing.

**Queue load non-list guard** — any script that reads a shared JSON queue file (e.g. `pending-fanout-queue.json`) must guard against valid JSON that is not a list (a dict or string from a corrupt write). Always: `loaded = json.loads(text); existing = loaded if isinstance(loaded, list) else []`. Without this, `for item in existing` iterates over dict keys and every downstream operation corrupts the queue silently.

**Encode+write bypass in security gates** — a chr()/fromhex()/b64decode()/bytes([])/eval()/exec()-based encode+write pattern bypasses any static token scan (no `config.yaml` literal appears in the code). The `_ENCODE_PATTERN` ⊔ `_WRITE_RENAME` deny must fire on BOTH `execute_code` AND `terminal` tool calls — `python -c 'bytes.fromhex(...).decode(); open(...)'` is an equally valid attack vector. Common gaps: `chr(0x63)` (hex literal, not decimal) misses `\bchr\s*\(\s*\d+\s*\)`; `''.join(chr(c) for c in [...])` misses because no decimal literal; `shutil.copy2`, `shutil.move`, `os.write`, `json.dump`, `os.system`, `os.symlink` absent from `_WRITE_RENAME`; `eval()`/`exec()` not in `_ENCODE_PATTERN`. Extend `_ENCODE_PATTERN` to match bare `chr\s*\(` (no `\d+` constraint). For the full catalogue of mode-class FPs, shell redirect anchoring rules, dynamic-mode chr() comma-anchoring, and fd-redirect patterns (2>, &>), see the `recursive-adversarial-hardening` skill item 19 — those rules are maintained there as the authoritative reference.

## Pitfalls

Pitfall: profile-config and main in the profiles/fork repo have unrelated git histories
(branched from different roots). `git merge profile-config` from main fails with
"no history in common". The correct merge path:

  1. First clear ALL tracked-modified and untracked-blocker files from the working tree.
     `git status --short` → commit tracked modifications with `git add -u && git commit`.
     Move untracked files that would be overwritten (`AGENTS.md`, `SOUL.md`, `.npmrc`)
     using `mv <file> /tmp/<stash>` — the git error message names them explicitly.
     The profiles/fork repo root is `/var/home/rainbow` (not the fork subdir) — files
     like `AGENTS.md` are at `/var/home/rainbow/AGENTS.md`, not inside the fork dir.
  2. `git checkout main`
  3. `git merge --allow-unrelated-histories --no-ff profile-config -m "merge msg"`
  4. Resolve add/add conflicts (usually skill-access-logger, skill-routing-nudge) with
     `git checkout --theirs -- <path>` then `git add -f <path>` (note `-f` required
     because root .gitignore ignores `.hermes/`).
  5. `git commit --no-edit && git push origin main`
  6. Restore stashed files with `mv /tmp/<stash> <original-path>`.
  7. `git checkout profile-config` to return to working branch.

  To sync a live plugin fix into the hermes-fork git repo (separate repo):
  cp the live __init__.py and plugin.yaml into
  `hermes-fork/fork-profile/plugins/<name>/`, then commit + push to hermes-fork main.

Pitfall: when initialising or first committing a profile-config branch, add a `.gitignore`
before staging any files: `printf '__pycache__/\n*.pyc\n*.pyo\n' >> .gitignore && git add
.gitignore`. Without it, the first commit captures compiled bytecode, test runner
pyc caches, and stale test directories that are hard to remove retroactively.

Pitfall: skill/script snippets that use `/usr/bin/python3` for scripts that import hermes packages will fail silently on Fedora where that binary is the system Python without hermes packages installed. Any diagnostic command, self-test, or verify script that imports `hermes_cli`, `hermes`, or agent code must use `scripts/hermes-python` from the hermes-fork directory. Reserve `/usr/bin/python3` for stdlib-only utilities. Audit: grep all skill snippets for `/usr/bin/python3` before shipping.

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

Pitfall: `pre_compress` (and similar hooks) legitimately place `t0 = time.monotonic()`
BEFORE the try/except block — this is correct design so the timer captures total elapsed
including exception paths. An inline checker that skips only the docstring (stmt[0]) and
then asserts stmt[1] is a Try node will false-positive on the timer assignment. Skip
both the docstring (ast.Expr with ast.Constant) AND any `t0 = time.monotonic()` Assign
before checking for the Try. Concretely:

    for stmt in node.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  # docstring
        if isinstance(stmt, ast.Assign) and 't0' in ast.unparse(stmt):
            continue  # timer init — intentionally before try
        if not isinstance(stmt, ast.Try):
            issues.append("[MEDIUM] hook not wrapped in try")
        break

Pitfall: `_history()` helpers that only try `getattr(agent, 'conversation_history', None)`
are silently broken against AIAgent — which stores its messages as `_session_messages`.
Any plugin that reads agent history must try ALL known attribute names in priority order:
`_session_messages`, `conversation_history`, `_messages`. Return the first non-empty
list found. A plugin that only checks `conversation_history` on a live AIAgent always
sees `[]` and never fires — this is the most common reason a gate appears to work in
tests (which use a mock with `conversation_history`) but never fires in production.

## skill_manage create — frontmatter constraints

The description field in SKILL.md frontmatter must be <= 57 chars. Longer values
fail with a truncation/validation error. Write description as a short trigger phrase;
put all detail in the SKILL.md body.

Example of the failure:
  description: "Use when implementing JEV/System One patterns in hermes-fork, ..."
  -> fails: 'Description is 266 c...'

Fix: shorten to <= 57 chars:
  description: "Use when designing JEV harness patterns."

## Cron-Script Wiring Audit (non-plugin scripts)

For scripts registered as no_agent cron jobs (not plugins), the checklist differs from the plugin checklist. Use this when auditing a wave of hermes-scripts/ + fork wrapper scripts:

**Checklist (run in execute_code, not via subagent, for fast iteration):**

1. **Compile**: `py_compile.compile(path, doraise=True)` for every script.
2. **Import load**: `importlib.util.spec_from_file_location` + `exec_module` on every script. Catches missing imports, NameErrors at module level.
3. **Atomic write**: every script that writes JSON must use `os.replace()` or `_atomic_write()`. Bare `path.write_text(json.dumps(...))` is non-atomic. Check with: `'os.replace' not in content and '_atomic_write' not in content`.
4. **Path resolution**: the `_root` computation must guard against double-nesting when `HERMES_HOME` already includes `profiles/fork`. Pattern: `if 'profiles' not in str(_base): _root = _base / 'profiles' / _prof else: _root = _base`.
5. **Cron registration**: diff `{s.stem for s in SCRIPTS.glob('*.py')}` against `{j['name'] for j in jobs}`. Missing names are unregistered scripts. `no_agent` must be `True` for all cron script jobs.
6. **Schedule format**: `j['schedule']` is a dict `{kind, minutes, display}`, not a bare string. Extract via `j['schedule']['minutes']`.
7. **Wrapper correctness**: each fork wrapper in `profiles/fork/scripts/` must (a) reference the correct script name in quotes, (b) use `_hermes_home()` for path resolution, (c) use `runpy.run_path`.
8. **Self-test isolation**: `self_test()` must not call `run()` without `dry_run=True`, and must not call `_atomic_write()` with the production `OUT` path directly.
9. **Silent failure**: scripts querying `lifecycle.db` must check `LIFECYCLE_DB.exists()` before connecting. Missing file → return empty result, not crash.
10. **Hard-core invariant**: for each script verify ONE key mathematical property in-process via `importlib` (not subprocess). See list in the Theory Implementation skill.
11. **Dependency chain**: map `OUT = CACHE / 'X.json'` (writers) and `CACHE / 'Y.json'` reads (consumers). Every consumer read must have either (a) a producer script in the same wave with an equal-or-higher cron frequency, or (b) a fallback default in the script body.

**Dispatch subagents split by domain group** (not all 26 at once). One subagent per 12–13 scripts keeps context tight enough for complete coverage of all 11 dimensions.

**Run fork regression check after wave**: `~/.hermes/profiles/fork/scripts/fork-regression-check.py` via the hermes Python binary (not `/usr/bin/python3` which lacks hermes packages).

## Wiring Audit vs Design Audit

Design audit (recursive-adversarial-hardening skill): runs on specs/proposals BEFORE
code is written. Catches architectural impossibilities, budget explosions, and
invariant violations at the design level.

Wiring audit (this skill): runs on built code AFTER implementation. Catches compile
errors, policy table gaps, shadow compliance failures, and config drift between
documentation and actual state.

Both are required. Design audit gates implementation; wiring audit gates deployment.

## Hindsight Bank Pre-Creation

The hindsight plugin resolves `bank_id_template = 'hermes-{profile}'` at startup. If the resolved bank (e.g. `hermes-fork`) does not exist in the Hindsight API, auto-retain calls fall back to `hermes-default`, mixing fork session memories with the default profile. The bank auto-creates on first retain but only if the auto-retain code path fires (requires a compaction event). Pre-create the bank at session setup or profile bootstrap:

    import urllib.request, json
    payload = json.dumps({"name": "hermes-fork", "mission": ""}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:9177/v1/default/banks/hermes-fork",
        data=payload, headers={"Content-Type": "application/json"}, method="PUT"
    )
    resp = urllib.request.urlopen(req, timeout=5)
    # 200 = created or already exists (idempotent)

Verify: `GET /v1/default/banks` → bank_id `hermes-fork` appears in list.

The `GET /v1/default/banks/<bank_id>` endpoint returns 405 (no GET by ID). Use `GET /v1/default/banks/<bank_id>/profile` or `GET /v1/default/banks/<bank_id>/stats` for per-bank queries.

## on_post_compaction Hook: Token Kwarg Names

When the Hermes runtime fires `post_compaction`, it passes token counts as `tokens_before` and `tokens_after` kwargs (not `before_tokens`/`after_tokens`). A naive INSERT that reads `kwargs.get('before_tokens')` returns None for every row. Probe order for maximum compatibility:

    before = (
        kwargs.get('tokens_before')
        or kwargs.get('context_tokens_before')
        or kwargs.get('before_tokens')
    )
    after = (
        kwargs.get('tokens_after')
        or kwargs.get('context_tokens_after')
        or kwargs.get('after_tokens')
    )

Symptom of wrong kwarg names: all `before_tokens` / `after_tokens` columns in `compaction_telemetry` are NULL; SPRT has no data and falls through to `(False, False)` on every call.

## Audit False-Positive Triage

Audit subagents frequently mis-classify findings as MEDIUM when the code is correct. Before applying any fix, verify inline:

- **block dict `message=` missing**: load module, grep all `return {` blocks for `"action".*"block"`, confirm `"message"` key is present. Do not trust a subagent assertion — the key is there in both tool-auth-gate and governance-hard-block reference implementations.
- **`gated` field inverted**: check the inline comment. `"gated": not (fire_full or fire_soft)` with `# True = gate blocked` is intentional. Only rename/revert if the comment is absent or the polarity is demonstrably wrong.
- **memory-query-router KeyError on missing weights**: check for `if _rw_path.exists() else {}` fallback — already present. Confirm before writing a fix.
- **jev-gate-nightly non-atomic write**: check whether the script writes any file at all (it may be stdout-only). Import the script and check for `write_text`/`os.replace`/`_atomic_write` references first.
- **prequential cron as HIGH**: the script exits 0 silently with no args — this is a graceful no-op, not an error exit. The fuser is fail-open on missing prequential log. Downgrade to INFO.

Rule: before filing any finding as MEDIUM+, grep or inspect the actual code path and confirm the failure mode is reachable at runtime. Cold subagents have high FP rate on wiring findings (~30-50%).

See `references/hindsight-api.md` for Hindsight API endpoint reference, bank pre-creation pattern, on_post_compaction token kwarg names, and audit false-positive triage notes.

## Inventory Collection Before Dispatching Audit Subagent

Before dispatching the cold wiring subagent, collect the full inventory in execute_code so the subagent receives concrete paths and counts rather than globs it must resolve itself:

    jobs = json.loads((HERMES / "profiles/fork/cron/jobs.json").read_text())
    # jobs.json may be a dict with key 'jobs' or a bare list — normalise:
    actual_jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs

    plugin_dirs = [p.name for p in FORK_PLUGINS.iterdir() if p.is_dir()]
    enabled_plugins = cfg.get("plugins", {}).get("enabled", [])

Pass `len(actual_jobs)` and `enabled_plugins` explicitly in the subagent context string so the subagent can verify it checked all N jobs rather than stopping at a truncated subset.

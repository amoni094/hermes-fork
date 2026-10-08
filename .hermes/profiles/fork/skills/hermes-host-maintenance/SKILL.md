---
name: hermes-host-maintenance
description: Use when recovering Hermes DB crashes, updating host OS, or pulling hermes-agent main.
tags: [hermes, maintenance, sqlite, rpm-ostree, system, git]
---

# Hermes Host Maintenance

Covers two recurring classes: (1) Hermes state.db recovery after crashes, and (2) OS-level system updates.

## 1. Hermes SQLite WAL Audit and Recovery

### Proactive WAL audit (run periodically or when startup feels slow)

Several Hermes DBs default to `delete` journal mode and must be manually migrated to WAL.
WAL allows concurrent readers and writers without blocking, which is the primary source of
lock-wait slowness when multiple Hermes operations hit a DB simultaneously.

Audit all known DBs across both profiles in one shot:
```python
import sqlite3

dbs = [
    # fork profile
    "~/.hermes/profiles/fork/state.db",
    "~/.hermes/profiles/fork/cron/executions.db",
    "~/.hermes/profiles/fork/cron/notepad.db",
    "~/.hermes/profiles/fork/memory-facts/lifecycle.db",
    "~/.hermes/profiles/fork/memory-facts/graphiti-state.db",
    "~/.hermes/profiles/fork/vault.db",
    "~/.hermes/profiles/fork/verification_evidence.db",
    # default profile
    "~/.hermes/state.db",
    "~/.hermes/memory.db",
    "~/.hermes/shared-state.db",
    "~/.hermes/kanban.db",
    "~/.hermes/hindsight.db",
    "~/.hermes/vault.db",
    "~/.hermes/verification_evidence.db",
    "~/.hermes/cron/executions.db",
    "~/.hermes/cron/notepad.db",
    "~/.hermes/memory-facts/lifecycle.db",
    "~/.hermes/memory-facts/graphiti-state.db",
    "~/.hermes/memory-facts/provenance.db",
    "~/.hermes/memory-facts/metacognitive.db",
    "~/.hermes/memory-facts/stability.db",
    "~/.hermes/memory-facts/calibration.db",
]
import os
for db in dbs:
    db = os.path.expanduser(db)
    try:
        con = sqlite3.connect(db)
        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
        if mode != "wal":
            new_mode = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            print(f"FIXED {db.split('/')[-1]:30s}: {mode} -> {new_mode}")
        con.close()
    except Exception as e:
        print(f"ERROR {db}: {e}")
```
Run this inside `execute_code`. Changes are persistent (stored in the DB file header).

**Pitfall — vault.db silently stays on `delete`:** Both `~/.hermes/profiles/fork/vault.db`
and `~/.hermes/vault.db` default to `delete` journal mode after creation. They are not
covered by any Hermes auto-WAL migration. Include them explicitly in every audit.

**Pitfall — memory-facts/ DBs revert:** `provenance.db`, `metacognitive.db`, `stability.db`,
`calibration.db` are re-created by their respective plugins and lose WAL mode on first
plugin-managed rotation. Re-run the audit after major Hermes updates.

### Crash recovery triage sequence

1. Locate all DB and WAL/SHM files:
   `find ~/.hermes -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' 2>/dev/null`

2. Check for retired-WAL archives Hermes may have auto-created on crash:
   `ls ~/.hermes/profiles/fork/state.db.retired-wal-*/`
   Read the `manifest.json` inside each -- it records trigger, PID, WAL bytes, and SHA256.

3. Verify integrity of the live DB (sqlite3 not on PATH; use Python):
   ```
   python3 -c "
   import sqlite3
   conn = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
   print(conn.execute('PRAGMA integrity_check;').fetchall()[:5])
   conn.close()
   "
   ```
   Expected: `[('ok',)]`

4. Check journal mode and force WAL checkpoint if a stale WAL/SHM pair is present:
   ```
   python3 -c "
   import sqlite3
   conn = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
   print('mode:', conn.execute('PRAGMA journal_mode;').fetchone())
   print('checkpoint:', conn.execute('PRAGMA wal_checkpoint(TRUNCATE);').fetchone())
   conn.close()
   "
   ```
   checkpoint result = (busy, log, checkpointed); busy=0 means success.

5. Spot-check key tables:
   ```
   python3 -c "
   import sqlite3
   conn = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
   for t in ['sessions', 'messages']:
       print(t, conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
   conn.close()
   "
   ```

6. Confirm the binary starts cleanly: `~/.local/bin/hermes-fork --help`

7. Check fork is current with upstream (run when user asks 'hermes checked?' or similar):
   ```
   cd ~/.hermes/hermes-fork && git fetch origin && git log HEAD..origin/main --oneline
   ```
   Empty output = fork is current. Any lines = commits to pull.

8. Update hermes-agent main (upstream source repo at `~/.hermes/hermes-agent`):
   ```
   cd ~/.hermes/hermes-agent && git fetch origin && git log HEAD..origin/main --oneline
   ```
   Empty = current. If new commits:
   a. Check for local modifications first: `git status --short`
   b. If clean: `git pull origin main`
   c. If dirty: stash, pull, reapply:
      ```
      git stash && git pull origin main && git stash pop
      ```
   d. If stash pop produces a conflict: inspect with `grep -n '<<<' <file>`, then resolve.
      Prefer `git checkout --theirs <file>` when upstream's version is cleaner (e.g. a unified
      rewrite of a block your stash split differently). Mark resolved with `git add <file>`.
      Drop the stash after confirming: `git stash drop`

9. Merge upstream into hermes-fork (amoni094/hermes-fork) — do this after every hermes update:
   ```
   cd ~/.hermes/hermes-fork
   git remote add upstream-agent https://github.com/NousResearch/hermes-agent.git  # one-time
   git fetch upstream-agent main --unshallow  # --unshallow once; bare fetch after
   git merge-base HEAD upstream-agent/main  # confirm shared ancestor exists
   git merge upstream-agent/main --no-edit
   ```
   Conflict resolution strategy:
   - AGENTS.md (any location): always `theirs` — no fork customizations, upstream owns docs
   - agent/context_compressor.py, hermes_cli/plugins.py, evals/compaction/*: `both_ours_first`
     (fork adds additive features — entropy estimator, ARB, session registry)
   - agent/agent_init.py, agent/conversation_loop.py, hermes_cli/env_loader.py, etc.: `theirs`
     (upstream refactored same code; fork has no custom changes)
   - cron/jobs.py: `ours` (fork has extended FIRE_CLAIM_TTL_SECONDS comment)
   - plugins/memory/hindsight/__init__.py (modify/delete): keep ours (hindsight is active)
   After resolving: `git add . && git commit && git push origin main`

10. Run adversarial audit after every merge — see Section 9 Step 3 for the full 4-check script
    (compile, cron wiring, hardcoded paths, non-atomic writes). Quick shorthand:
    ```
    cd ~/.hermes/hermes-fork && source venv/bin/activate && python3 << 'EOF'
    # ... paste Section 9 Step 3 script here ...
    EOF
    ```
    Always rsync fixed scripts to live profile after commit:
    ```
    rsync -a --checksum ~/.hermes/hermes-fork/fork-profile/scripts/ ~/.hermes/profiles/fork/scripts/
    find ~/.hermes/profiles/fork/scripts/__pycache__ -name '*.pyc' -delete
    ```

## 9. Merging hermes-agent main into hermes-fork

`hermes-fork` (amoni094/hermes-fork) IS a proper GitHub fork of NousResearch/hermes-agent.
Shared ancestor: b6b53c69a6ed49cb099cf1bfe76b5e6edd718e5a (confirmed 2026-10-05).
Fork is 123+ commits ahead of upstream. Standard merge strategy is correct.

### Full "update hermes" procedure

When the user says "update hermes" or "hermes update":

**Step 1 — Update hermes-agent source repo:**
```bash
cd ~/.hermes/hermes-agent
git fetch origin
git log HEAD..origin/main --oneline   # preview changes
git status --short                     # check for local mods
# If dirty:
git stash && git pull origin main && git stash pop
# If clean:
git pull origin main
pip install -e ".[all]" -q            # reinstall after update
```

**Step 2 — Merge upstream into hermes-fork:**
```bash
cd ~/.hermes/hermes-fork
git fetch upstream-agent main         # remote already added as upstream-agent
git log HEAD..upstream-agent/main --oneline  # preview
git tag backup/pre-merge-$(date +%Y%m%d-%H%M) HEAD  # safety backup — use %H%M to avoid collision on same-day re-runs
git merge upstream-agent/main --no-edit
```
If merge produces conflicts, resolve using this strategy:
- AGENTS.md (any location): `git checkout --theirs <file>` — upstream owns docs, no fork customizations
- Infrastructure files (agent_init, conversation_loop, env_loader, etc.): `git checkout --theirs <file>`
- Fork-additive files (context_compressor, chat_completion_helpers, plugins.py, evals/compaction): merge manually — keep fork additions (entropy estimator, ARB, session reasoning, eval arms). When upstream adds a new mixin to ContextCompressor's class signature (e.g. PreLlmSkipMixin), use upstream's full class definition line but preserve fork's additive inner classes above it.
- plugins/memory/hindsight/__init__.py: always keep ours (upstream deleted; fork uses it)
- After resolving: `git add . && git commit -m "merge: upstream hermes-agent main into fork"`

**Step 3 — Adversarial audit (run after every merge):**
```bash
cd ~/.hermes/hermes-fork && source venv/bin/activate && python3 << 'EOF'
import py_compile, json, re
from pathlib import Path
issues = []
all_py = [f for d in ['fork-profile/scripts','hermes-scripts']
          for f in Path(d).rglob('*.py') if '__pycache__' not in str(f)]
# 1. Compile
for f in all_py:
    try: py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e: issues.append(('HIGH', f.name, str(e)[:80]))
# 2. Cron wiring
data = json.loads((Path.home()/'.hermes/profiles/fork/cron/jobs.json').read_text())
for j in (data if isinstance(data,list) else data.get('jobs',[])):
    if 'HERMES_PROFILE' not in j.get('env',{}): issues.append(('MED',j.get('name'),'no HERMES_PROFILE'))
    # command field is ignored by the scheduler (only script/prompt/skills fire) — flag as dead
    if 'command' in j and not j.get('script'): issues.append(('HIGH',j.get('name'),'command field without script — job never fires'))
    # schedule must have kind in {cron,interval,once}; empty {} or wrong keys = silent skip
    sched = j.get('schedule',{})
    if not sched.get('kind') and j.get('enabled',True): issues.append(('HIGH',j.get('name'),f'schedule missing kind: {sched}'))
    if sched.get('kind')=='interval' and 'minutes' not in sched: issues.append(('HIGH',j.get('name'),f'interval schedule missing minutes: {sched}'))
    for p in j.get('command','').split():
        if p.endswith('.py') and p.startswith('/') and not Path(p).exists(): issues.append(('HIGH',j.get('name'),f'missing {p}'))
# 3. Hardcoded fork paths
exec_re = re.compile(r"(['"])(/var/home/[^'"]*profiles/fork[^'"]*)\1")
for f in all_py:
    for i,l in enumerate(f.read_text(errors='ignore').splitlines()):
        if l.strip() and not l.strip().startswith('#') and exec_re.search(l):
            issues.append(('MED', f.name, f'hardcoded path line {i+1}'))
# 4. Non-atomic JSON state writes
wt_re = re.compile(r'\.(write_text|write_bytes)\(json\.dumps')
atm_re = re.compile(r'_tmp_|\.with_suffix.*\.tmp|\.replace\(')
for f in all_py:
    src = f.read_text(errors='ignore'); lines = src.splitlines()
    for i,l in enumerate(lines):
        if wt_re.search(l) and not atm_re.search(l):
            if not atm_re.search(' '.join(lines[max(0,i-3):i+4])):
                issues.append(('MED', f.name, f'non-atomic write line {i+1}'))
H = [x for x in issues if x[0]=='HIGH']; M = [x for x in issues if x[0]=='MED']
print(f'{len(all_py)} files | {len(H)} HIGH | {len(M)} MED')
for s,f,d in issues: print(f'  [{s}] {f}: {d}')
if not issues: print('CLEAN')
EOF
```

Additional post-merge cron checks to run manually:
```bash
# Verify profile-scoped scripts scan BOTH default and profile skill trees
grep -n 'SKILLS_ROOT\|_skills_roots\|HERMES_PROFILE' \
~/.hermes/profiles/fork/scripts/omni_skill_scan.py | head -15
# Expect: _skills_roots list built from both hermes_home/skills and profiles/$HERMES_PROFILE/skills
# Expect: scanner loop iterates _skills_roots (not just SKILLS_ROOT)
# If missing: the fork-profile skill tree is silently excluded from scans
```

**Step 3b — Cron interpreter import gap check (run after every merge or env rebuild):**

Cron scripts run on the PM's managed Python 3.14 venv (`project_python(repo)`), NOT the
fork's in-tree 3.11 venv. Key absent packages: `pyyaml`, `pypdf`, `numpy`. Key present:
`ruamel.yaml`, `requests`. Use `ruamel.yaml` as the fallback when a script uses PyYAML.
Full procedure and scripts: `references/cron-interpreter-gap-check.md`.

Fix pattern for non-atomic writes:
```python
# Before: OUT_FILE.write_text(json.dumps(data, indent=2))
_tmp = OUT_FILE.with_suffix('.tmp')
_tmp.write_text(json.dumps(data, indent=2))
_tmp.replace(OUT_FILE)
```

**Step 4 — Sync to local profile and push:**
```bash
rsync -a --checksum ~/.hermes/hermes-fork/fork-profile/scripts/ ~/.hermes/profiles/fork/scripts/
rsync -a --checksum ~/.hermes/hermes-fork/hermes-scripts/ ~/.hermes/hermes-scripts/
find ~/.hermes/profiles/fork/scripts/__pycache__ -name '*.pyc' -delete
git push origin main
```

**Step 5 — Rebuild skill index:**
```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork HERMES_CRON_BUILD=1 \
  python3 ~/.hermes/profiles/fork/scripts/skill-router-index.py --build
```

**Step 6 — Verify launcher/PM Python version alignment (prevents ABI mismatch crashes):**
```bash
# Extract the shebang interpreter from the canonical launcher and get its Python version
CANONICAL=$(sed -n '1s/^#!//p' ~/.hermes/hermes-fork/.hermes/bin/hermes)
echo "Canonical launcher shebang interpreter: $CANONICAL"
$CANONICAL --version 2>&1

# Also check what the wrapper currently points at:
grep 'exec ' ~/.local/bin/hermes-fork

# The wrapper must call .hermes/bin/hermes, NOT venv/bin/hermes.
# If it calls venv/bin/hermes, fix it:
# cp ~/.hermes/hermes-fork/scripts/hermes-fork-wrapper.sh ~/.local/bin/hermes-fork
# chmod +x ~/.local/bin/hermes-fork
```
If the wrapper calls `venv/bin/hermes` → run the cp fix above and restart the gateway before testing.

**Step 7 — Smoke test after every update:**
```bash
hermes-fork -z 'say ok'
```
Do this immediately after any update. If it fails with "anthropic package is required",
run Section 10 diagnosis before anything else.

### Parallelism
Steps 1+2 (pip install and fork merge fetch/preview) are independent — run concurrently.
Steps 4+5 (rsync sync and skill index rebuild) are independent — run concurrently.

### Pitfalls
- Cron job `command` field is NOT executed by the Hermes scheduler — only `script`, `prompt`, and `skills` fields fire. A job with `command` only and no `script` silently never runs. Always use `script` for cron-launched Python files.
- Cron `schedule` requires `kind` in {`cron`, `interval`, `once`}. An empty `{}` or using wrong keys (`type` instead of `kind`, `seconds`/`interval_seconds` instead of `minutes`) causes the job to be skipped permanently with `next_run_at=null`. Correct interval schema: `{"kind": "interval", "minutes": N}`.
- Cron scripts run on the PM's managed Python (`project_python(repo)` → 3.14 managed venv), NOT the fork's in-tree venv (3.11). `pyyaml`, `pypdf`, and `numpy` are absent from the managed venv. Use `ruamel.yaml` (present) as the PyYAML fallback. Check all scheduled scripts for import gaps after every merge — see `references/cron-interpreter-gap-check.md`.
- When writing atomic file renames, the `import os` must be at the top of the file (or `import os as _alias` at the rename site). A typo like `import os2` at the rename site crashes every run silently since `os2` is not a real module. When patching or generating atomic-write patterns, verify the os import is present before the `.replace()` call.
- The first fetch of upstream-agent should use `--unshallow` if the repo was cloned shallow.
  Shallow fetch gives false 6k-conflict result (no shared history visible).
- `git fetch upstream-agent main --depth=1` gives wrong conflict count — always fetch without depth after the first time.
- Upstream remote already added as `upstream-agent` pointing to https://github.com/NousResearch/hermes-agent.git
- After post-update `pip install -e ".[all]"`, minimal or zero output is normal.
- Backup tag creation uses date +%Y%m%d — add -%H%M suffix to avoid 'tag already exists' on same-day re-runs.
- When tests fail after a merge, always verify the same failure exists on clean upstream (`cd ~/.hermes/hermes-agent && python3 -m pytest <test> ...`) before treating it as a regression. Home I/O guard failures and upstream CI infrastructure failures are pre-existing noise. Dependency incompatibility warnings from third-party packages (outlines, denuto, etc.) that were present before the update are noise, not failures — the install succeeded if exit code is 0.
- delegate_task subagent spawn may fail with `No module named 'agent.ssl_guard'` — run audits in-process via terminal heredoc instead.

### DB Pitfalls

- sqlite3 CLI is NOT installed on this host -- always use `python3 -c "import sqlite3; ..."` for DB inspection.
- **Rollback-journal lock blocks delegate_task:** When state.db is in `journal_mode=delete` (not WAL) and a crashed session left a dangling `.db-journal` file, any process trying to open the DB for writes (including delegate_task subagent spawns) will block indefinitely. The WAL pragma cannot be applied retroactively to a connection that already opened in delete mode. Fix: `hermes-fork config set database.journal_mode wal` then `hermes-fork gateway restart`. Current-session delegate_task calls will still fail until a fresh session is opened after the restart. Workaround: implement the work directly in `execute_code` using file-system writes instead of subagents.
- **Dangling `.db-journal` diagnosis:** `ls -la ~/.hermes/profiles/fork/state.db-journal` — if present and >0 bytes, a session crashed mid-write. After `hermes-fork gateway restart`, the new gateway rolls it back automatically. Confirm with `python3 -c "import sqlite3; conn=sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db'); print(conn.execute('PRAGMA journal_mode;').fetchone())"` — should return `('wal',)` if config was updated before restart.
- Retired-WAL archives (`state.db.retired-wal-<timestamp>-<pid>/`) are Hermes's own crash-safe backups, not blocking corruption. Each contains a full DB copy (~166 MB) plus uncommitted WAL frames. Safe to delete after confirming the live DB is healthy.
- The live DB having no `.db-wal` / `.db-shm` after a crash means Hermes already checkpointed on exit -- normal, not data loss.
- `PRAGMA wal_checkpoint(TRUNCATE)` returning `(0, 0, 0)` means nothing to checkpoint -- not an error.
- Fork profile path is `~/.hermes/profiles/fork/state.db`, NOT `~/.hermes/state.db` (default profile).

### Cleanup

After confirming health, prune retired-WAL archives to reclaim disk:
```
rm -rf ~/.hermes/profiles/fork/state.db.retired-wal-*/
```

## 13. Skill Knowledge Base Audit (periodic)

Periodically scan all skills for missing linked reference files (references/, templates/, scripts/ declared in SKILL.md but absent on disk). See `references/skill-reference-audit.md` for the full procedure, including the code-block false-positive pitfall and evaluation criteria for whether a missing file is worth implementing.

---

## 10. Post-Update "anthropic package is required" Failure

### What happened (2026-10-05)

After a Hermes update, the PM migrated the managed dependency environment from the old
3e0ccaf3 env (Python 3.14, no anthropic extra) to dcfbb29c (Python 3.14, all + anthropic).
But `~/.local/bin/hermes-fork` still called `hermes-fork/venv/bin/hermes` — the in-tree
venv launcher, which uses Python 3.11. `activate_dependencies()` replaced the 3.11 venv's
site-packages with the 3.14-compiled dcfbb29c ones. `pydantic_core` (a compiled C extension,
ABI-incompatible across minor versions) failed silently, causing `import anthropic` to throw
`No module named 'pydantic_core._pydantic_core'`. Hermes surfaces this as the misleading
"The 'anthropic' package is required" error.

### Diagnosis checklist

When you see "The 'anthropic' package is required":

1. Confirm the managed env actually has anthropic:
   ```
   hermes pm status | python3 -m json.tool | grep -E 'feature_list|outcome'
   find ~/.hermes/installs -path '*/site-packages/anthropic/__init__.py' -print
   ```
   If the find returns a path, the package IS installed. The error is ABI/launcher mismatch, not a missing package.

2. Check what the wrapper calls vs the canonical launcher:
   ```bash
   grep 'exec ' ~/.local/bin/hermes-fork
   # Must contain .hermes/bin/hermes, NOT venv/bin/hermes

   # What Python does the canonical launcher use?
   CANONICAL=$(sed -n '1s/^#!//p' ~/.hermes/hermes-fork/.hermes/bin/hermes)
   $CANONICAL --version 2>&1

   # What Python is the PM venv using?
   hermes-fork doctor | grep 'Python'
   ```
   If wrapper calls venv/bin/hermes → that's the problem (ABI mismatch after PM env migration).

3. Check the canonical launcher vs the wrapper target:
   ```
   cat ~/.hermes/hermes-fork/.hermes/bin/hermes   # should be the store Python (e.g. 3.14)
   cat ~/.local/bin/hermes-fork                    # should call .hermes/bin/hermes, not venv/bin/hermes
   ```

### Fix

Point the wrapper at the canonical launcher (store Python), not the in-tree venv:

```bash
# Before (broken): uses old venv/bin/hermes (Python 3.11)
# exec /var/home/rainbow/.hermes/hermes-fork/venv/bin/hermes --profile fork "$@"

# After (fixed): install versioned wrapper template from repo
cp ~/.hermes/hermes-fork/scripts/hermes-fork-wrapper.sh ~/.local/bin/hermes-fork
chmod +x ~/.local/bin/hermes-fork
# Verify the exec line:
grep 'exec ' ~/.local/bin/hermes-fork
hermes-fork gateway restart && sleep 4 && hermes-fork doctor | grep -E 'Python|venv staged'
```

### After `hermes pm install --extra anthropic` runs

The running gateway process has the OLD environment in-memory. A gateway restart is
necessary AND the restart must pick up the NEW facts.json. Sequence:

```bash
hermes pm install --extra anthropic     # installs; updates facts.json
hermes-fork gateway restart             # restart AFTER facts.json is updated
sleep 3
hermes-fork -z 'say ok'               # verify
```

If -z still fails after restart, the old gateway process may have started with a stale
environment. Check:
```bash
cat /proc/$(pgrep -f 'profile fork')/environ | tr '\0' '\n' | grep VIRTUAL_ENV
# Should point to dcfbb29c* not 3e0ccaf3*
```

### Why `hermes-fork -z` and the gateway use different environments

`hermes-fork -z` runs fully in-process (no gateway IPC). It spawns its own Python process
via the wrapper script. The gateway runs persistently with its own bootstrapped env.
If the wrapper's Python != the gateway's Python, they may stage different PM environments
and exhibit different behavior. Keep the wrapper pointing to the canonical launcher always.

### Misleading error message

The error `The 'anthropic' package is required for the Anthropic provider` is generated
by `pm.extras.ensure_import("anthropic")` when `import anthropic` raises ImportError.
The *actual* root cause is almost always a compiled extension ABI mismatch (pydantic_core,
jiter, etc.), not a missing package. Always run the diagnosis checklist above before
trying to reinstall.

---

## 11. Graphiti / Hindsight / FalkorDB Health Check

When the user asks "is graphiti/hindsight working?" or memory writes seem stale, run this sequence:

**Step 1 — Confirm graphiti MCP server process is running:**
```bash
pgrep -a -f graphiti | grep -v bash | head -5
```
Expect: two lines — a `uv run main.py` launcher and a Python process, both passing
`--config .../config-hermes.yaml --transport http --host 127.0.0.1 --port 8765`.

**Step 2 — Confirm MCP server is responding on port 8765:**
```bash
curl -v --max-time 3 http://127.0.0.1:8765/
```
Expect: `HTTP/1.1 404 Not Found` from uvicorn (the root path is unmapped; 404 means the
server is alive). Refused connection = server is down.

The actual MCP endpoint is `/mcp/`. It requires SSE transport:
```bash
curl -s --max-time 5 http://127.0.0.1:8765/mcp/ \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -X POST -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Step 3 — Confirm FalkorDB (graph DB backend) is running:**
```bash
ss -tlnp | grep 6379
podman ps | grep -E 'falkor|redis'
```
Expect: FalkorDB container named `falkordb` bound to `127.0.0.1:6379`.

**Pitfalls:**
- Graphiti uses **FalkorDB** (podman container, port 6379), NOT Neo4j. Do NOT check ports
  7474/7687 or `systemctl status neo4j` — Neo4j is unused and expected to be inactive/absent.
- The graphiti process runs detached (started at login or via systemd user unit); if it is
  missing, check `journalctl --user -u graphiti -n 30` or the startup script in
  `~/graphiti/mcp_server/`.
- Config lives at `~/graphiti/mcp_server/config/config-hermes.yaml` — LLM: claude-haiku-4-5,
  embedder: OpenAI text-embedding-3-small, DB: FalkorDB localhost:6379.
- `nc` is not installed; use `ss -tlnp | grep <port>` to probe ports.

---

## 12. Checking hermes-fork GitHub Issues / Comments

When the user asks about a comment or issue in hermes-fork:

```bash
# List all issues (including bot-created)
gh issue list -R amoni094/hermes-fork --state all --limit 10

# Read a specific issue and its comments
gh api repos/amoni094/hermes-fork/issues/1
gh api repos/amoni094/hermes-fork/issues/1/comments

# Check recent GitHub notifications (cross-repo)
gh api notifications --limit 10
```

### Pitfalls
- `web_extract` returns empty content for GitHub pages — use `gh` CLI or `gh api` instead.
- Browser tools require Camofox running on localhost:9377; if it is not running, fall back to `gh api`.
- The `install-e2e-red` label issue is auto-created by the `.github/workflows/install-e2e-red.yml`
  bot when the scheduled Install & Update E2E matrix fails. It rewrites itself after each run
  and self-closes on the first green run. It is NOT a human-filed bug and does NOT indicate a
  problem with fork code — ignore unless it stays open for more than a few days or contains
  a human comment.

---

## 3. Hermes Vault Management

### Updating a saved password

`hermes vault update` does not exist. The update workflow is remove + re-add:

1. Get the full handle (the list table truncates with `…` -- do not use the truncated form):
   ```
   cd ~/.hermes/hermes-agent && source venv/bin/activate && python3 -c "
   from agent.vault_store import get_vault_store
   for item in get_vault_store().list_items():
       print(f'id={item.id!r} label={item.label!r} origin={item.origin!r}')
   "
   ```

2. Remove the old entry:
   ```
   hermes vault rm <full-handle>
   ```

3. Re-add with the new password:
   ```
   hermes vault add
   ```
   Prompts for kind, label, identifier, origin, then a masked password field.

### Pitfalls

- `hermes vault list` shows truncated handles (e.g. `vault_2e23b…`). `hermes vault rm` requires the full handle -- always retrieve it via the Python method above.
- The vault DB is NOT a standard sqlite3 file with a `vault_items` table -- direct sqlite3 queries fail. Use `agent.vault_store.get_vault_store()` from within the hermes-agent venv.

---

## 2. System Updates (Fedora Atomic / rpm-ostree)

This host uses rpm-ostree (immutable Fedora). Standard update:
```
rpm-ostree upgrade
```
- 'No upgrade available.' = already on latest deployment, no reboot needed.
- If an upgrade IS staged, a reboot is required to apply it: `systemctl reboot`
- Flatpak apps update separately: `flatpak update -y`
- Full update pass (both layers):
  ```
  rpm-ostree upgrade && flatpak update -y
  ```
- If `flatpak update` exits with error but shows 'Updates complete.' above the error, it was a transient network drop mid-download. Re-run `flatpak update -y` after reboot — flatpak resumes from where it left off and only re-fetches the failed object.

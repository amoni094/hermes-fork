---
name: stalled-session-recovery
description: "Use when a Hermes session, subagent, or cron job stalled mid-task — diagnose and resume. Not for hung/zombie browser Chrome processes (use agent-browser-troubleshooting)."
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
  - another session may have stalled or crashed mid-task
  - delegated agent stopped without completing follow-up step
  - user asks to confirm and fix a stalled implementation session
  - cron job or subagent appears to have done partial work
  - session "dropped out" or "received signal" — user reports the terminal exited unexpectedly
  - continue a research/implementation sweep that was interrupted
metadata:
  hermes:
    tags: [session, recovery, stalled, agent, debugging]
    related_skills: [hermes-cron-and-agents, hermes-context-hygiene, verification-before-completion]
related_skills:
  - hermes-cron-and-agents
  - hermes-context-hygiene
  - claude-routing-hierarchy
  - agent-runtime-loop-patterns
  - hindsight-stack-operations
  - verification-before-completion
  - handoff
  - hermes-context-packet

---

# Stalled Session Recovery

## When to use

Use this when a parallel Hermes session, delegated subagent, or cron-fired agent stopped
mid-task without completing its final step (e.g. wrote a file then never ran tests, applied
patches then never committed, produced a plan then never executed it).

## Diagnosis procedure

1. Locate the session:
   ```
   session_search(query="<topic keywords>", sort="newest", limit=3)
   ```

   **Cross-profile sessions (hermes-fork, etc.):** `session_search` searches only the CURRENT profile's state.db. Sessions from another profile (e.g. `~/.hermes/profiles/fork/state.db`) will return 0 results regardless of query. The tool has no `profile=` parameter exposed. Use python3 + sqlite3 directly on the target profile's DB:
   ```python
   import sqlite3, datetime
   db_path = "/var/home/rainbow/.hermes/profiles/fork/state.db"  # adjust profile name
   conn = sqlite3.connect(db_path)
   cur = conn.cursor()
   cur.execute("""
       SELECT session_id, MIN(timestamp), MAX(timestamp), COUNT(*)
       FROM messages GROUP BY session_id ORDER BY MAX(timestamp) DESC LIMIT 10
   """)
   for r in cur.fetchall():
       s = datetime.datetime.fromtimestamp(r[1]).strftime('%Y-%m-%d %H:%M')
       e = datetime.datetime.fromtimestamp(r[2]).strftime('%Y-%m-%d %H:%M')
       print(r[0], s, '->', e, r[3], 'msgs')
   conn.close()
   ```
   Once you have the session_id, read the last N messages the same way:
   ```python
   cur.execute('SELECT id, role, substr(content,1,500) FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 15', (session_id,))
   ```
   To check if a fork profile session is currently active:
   ```bash
   cat ~/.hermes/profiles/fork/runtime/active_sessions.json
   tail -50 ~/.hermes/profiles/fork/logs/agent.log
   ```
   The active_sessions.json shows the live session ID + PID. The agent.log tail shows the last tool call and timestamp — if the last line is a completed tool result with no subsequent API call entry, the session is idle at a prompt, not stalled.

   **If session_search fails with `DeletedWalGenerationError`:** the tool cannot open state.db because a live process holds a deleted WAL inode. Bypass it entirely — open state.db read-only via sqlite3 in execute_code:
   ```python
   import sqlite3, datetime
   db_path = "/var/home/rainbow/.hermes/state.db"
   conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
   cur = conn.cursor()
   cur.execute("""
       SELECT s.id, COALESCE(s.title,'(untitled)'), min(m.timestamp), max(m.timestamp), count(m.id)
       FROM sessions s JOIN messages m ON m.session_id = s.id
       GROUP BY s.id ORDER BY max(m.timestamp) DESC LIMIT 20
   """)
   for r in cur.fetchall():
       print(datetime.datetime.fromtimestamp(r[3]).strftime('%H:%M'), r[4], 'msgs |', r[0], r[1][:60])
   conn.close()
   ```
   The WAL error does NOT mean the DB is corrupt — the file is readable. Do not restart the gateway just to unblock session_search; the sqlite3 bypass is faster and non-destructive.

   **If the session was just started (live, not yet flushed to DB):** it will not appear in state.db at all. Check running processes and agent.log instead:
   ```bash
   ps aux | grep hermes | grep -v grep  # find PID and pts/N
   grep 'turn_context\|Turn ended' ~/.hermes/logs/agent.log | tail -20  # find session ID
   ```

2. Scroll to its last message to find the exact stall point:
   ```
   session_search(session_id="<id>", around_message_id=<last_visible_id>, window=20)
   ```
   Use window=20 (not 5) to get enough context to assess what was in flight.

   **Spillover files:** session_search results > ~15KB are saved to disk instead of returned
   inline. When you see `Full output saved to: /var/home/rainbow/.hermes/cache/spillover/<id>.txt`,
   parse that file with execute_code (json.loads + iterate messages) — do NOT re-call
   session_search, the full result is already on disk.

3. Read `messages_after` in the result:
   - `messages_after: 0` — confirmed stall. Session ended at this exact tool call.
   - `messages_after: N` — session continued; scroll forward before concluding it stalled.

   When `messages_after: 0` lands on a `tool_calls` assistant message with NO subsequent `role: tool` result, the session died WHILE the tool was executing (e.g. a `terminal()` pytest run still in progress). The command may or may not have finished on the host. Do NOT assume the result was bad — verify the repo state independently (git log, file presence, test re-run) before re-doing any work.

4. Inspect the final tool result to determine what was completed:
   - `"verified": true` in a `write_file` result → file is on disk, do NOT re-write it.
   - `"lint": {"status": "ok"}` in a `patch` result → code change applied cleanly.
   - `"success": true` in a `skill_manage` result → skill was already patched.
   - No follow-up tool call after these → the next step (tests, commit, push) was skipped.

5. Resume from the next logical step in the current session. Do not repeat completed steps.

## Session appears stalled but actually completed

The most common false alarm: a session dispatched async subagents, the subagents completed, the parent wrote a skill/file, then stopped — waiting at a prompt. It looks stalled because no final reply appeared.

Disagnose by checking the delegation live transcripts and the agent.log:
```bash
# Check if delegation tasks all show status=completed
cat ~/.hermes/cache/delegation/live/<deleg_id>/manifest.json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); [print(i['index'], i.get('status','?')) for i in d['tasks']]; print('completed:', d.get('completed','NOT DONE'))"

# Find what the session did after receiving delegation results
grep '<session_id>' ~/.hermes/logs/agent.log | tail -10
# Look for: 'skill_manage completed' or 'write_file completed' as the last tool call,
# followed by NO 'Turn ended' line = session is alive, waiting at a prompt, not stalled.
```

If the last agent.log entry for the session is a tool completion with no subsequent `Turn ended` line, and the process is in `ep_poll` (check `/proc/<PID>/wchan`), the session is idle at its terminal prompt. The work is done. Verify the output artifact exists on disk before concluding anything needs fixing.

## Distinguishing a crash from a clean exit

**Signal 1 (SIGHUP) = clean session exit**, not a mid-task crash. When the user reports
"the session dropped" and the recovery meta-session shows `"received signal 1"` as its only
message, the prior session exited normally. Do not assume partial work.

The key question is: did the work session finish, or did the session die while working?

Check the work session's last message ID vs the recovery session:
- Work session ends with `messages_after: 0` at a completed tool result → session finished cleanly.
- Work session ends at a mid-tool-chain point with pending calls → session crashed mid-work.

## Memory Loss on Crash (SIGKILL / OOM / abrupt exit)

Hermes Hindsight has a 10s drain window on shutdown. A clean SIGTERM/SIGHUP drains it.
SIGKILL, OOM kill, or power loss skips the drain entirely.

Consequence: turns written to Hindsight buffer but not yet flushed are silently lost.
Same for in-flight async children — they are interrupted mid-run; their partial results
are NOT written to Hindsight or Graphiti automatically.

Recovery procedure for crash-path memory loss:
1. Check `~/.hermes/cache/delegation/live/<deleg_id>/task-*.log` for partial subagent output.
2. Check `~/.hermes/logs/agent.log` for the last turns before crash.
3. Re-run `hindsight_recall` + `mcp__graphiti__search_memory_facts` to see what was flushed.
4. Manually call `hindsight_retain` for any facts found in logs but absent from memory.
5. Do NOT expect completeness — assume last 1-3 turns before crash may be missing.

## Implicit Memory Conflict Recovery (arXiv:2605.06527 STALE)

Stale facts cause silent failures distinct from explicit stalls: the session runs fine but
acts on a premise-resistant memory (old fact retrieved + trusted despite a newer correction
existing in the same bank). Best retrieval model corrects only 55.2% of implicit conflicts;
don’t rely on recall alone for high-stakes acts.

Symptoms:
  - Agent cites a plausible-looking fact but action contradicts recent context
  - hindsight_recall returns two contradictory entries; agent uses the older one
  - Session uses a model name, path, or config value that was rotated in a prior session

Recovery procedure:
  1. Identify the stale premise: which fact drove the wrong action?
  2. Run hindsight_recall on that topic; look for newer contradicting entries
  3. If found: explicitly compare old vs new; state which applies and why before retrying
  4. Supersede the old entry: hindsight_retain with "SUPERSEDED by [new fact] as of [date]"
  5. Re-execute the action with the corrected fact

Premise resistance is worst for factual chains (A → B → C where A is stale).
See also: hermes-memory-surface-selection § Implicit Conflict for write-time gate.

Signal 1 (SIGHUP) patterns:
- Terminal closed, SSH dropped, or user closed the terminal emulator.
- Session completed its work, then a recovery meta-session started and also got SIGHUP.
- Either way, look at the WORK session's last message, not the recovery session's.

## Sweep / long-running research recovery

When the dropped session was a multi-source research sweep:

1. Check for a **per-sweep findings reference file** first. Well-structured sweeps write a
   findings doc (e.g. `agent-memory-consolidation/references/sweep-N-findings.md`) that is
   more reliable than re-parsing tool call chains. If it exists and lists a sweep boundary
   ("Next sweep starts above: 2608.23552"), the sweep completed.

2. Verify key on-disk artifacts independently — grep the patched scripts/skills for the
   finding's key terms. A grep hit confirming the patch text is stronger than a scroll showing
   `"success": true` (which could be from an earlier run).

3. Orphaned subagents: if the work session had delegate_task subagents still running when it
   dropped, those processes are dead. Their results are lost. Re-run the sweep from the
   confirmed cutoff rather than trying to recover orphaned agent output.

## Recovering Orphaned Subagents via DB Triage (sqlite3 state.db)

When a research/synthesis multi-agent run fails and you cannot tell which subagents ran
or what they produced, query state.db directly — do NOT re-run session_search in a loop.

```python
import sqlite3, json
db_path = "/var/home/rainbow/.hermes/state.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Find subagent sessions created in the same time window as the parent dispatch
cur.execute("""
    SELECT s.id, s.title, min(m.timestamp) as first_ts, count(m.id) as msg_count
    FROM sessions s
    JOIN messages m ON m.session_id = s.id
    WHERE m.timestamp > <parent_dispatch_unix_ts>
    GROUP BY s.id
    ORDER BY first_ts
    LIMIT 20
""")
rows = cur.fetchall()  # untitled sessions are subagents; named ones are continuations

# 2. For each subagent session, inspect message shapes
cur.execute("SELECT id, role, length(content) FROM messages WHERE session_id=? ORDER BY id", (sid,))
# Large tool results (>30K chars) = web extracts = research gathered
# Final role=assistant with small content = subagent's plan (not synthesis)
# No final assistant message = timed out mid-tool chain

# 3. Stage gathered research data to files for re-dispatch
cur.execute("SELECT id, content FROM messages WHERE session_id=? AND role='tool' AND length(content)>600 ORDER BY id", (sid,))
for mid, content in cur.fetchall():
    # Filter out the common 53K skill dump (length == 53552 = skills_list result)
    if len(content) == 53552:
        continue
    blocks.append(f"=== Source block {mid} ===\n{content[:12000]}\n")

conn.close()
```

Key observations:
- Sessions with only 1 message: spawned but never ran (process died at startup)
- Sessions with 8-10 messages ending on a `role=tool`: gathered data but context-timed out
- Sessions with a small final `role=assistant` message saying "next I'll...": reached turn limit
- Sessions with `role=assistant` prose summary: actually completed (rare for large runs)

Once you identify sessions with good research data (large tool content), extract it to
files in `~/.hermes/cache/<task>/` and re-dispatch synthesis agents with FILE PATHS in
the context — not inline data. This avoids the same context-timeout repeating.

See also: `references/sqlite3-subagent-triage-queries.md` for the complete reusable code.

## Diagnosing a Failed Synthesis Subagent (delegation live transcript)

When a synthesis/report subagent fails silently (output file never appears, no error surfaced), read its delegation live transcript BEFORE re-spawning with a changed prompt:

```bash
# Find the delegation ID from the task's deleg_ directory
ls -lt ~/.hermes/cache/delegation/live/ | head -10
tail -30 ~/.hermes/cache/delegation/live/<deleg_id>/task-0.log
```

Or via read_file for the last N lines:
```python
read_file(path="~/.hermes/cache/delegation/live/<deleg_id>/task-0.log", offset=<total_lines-30>, limit=30)
```

**What to look for in the transcript:**

- `final | status=interrupted exit_reason=interrupted` = context timeout. The agent ran out of turns/context before it could write. The last assistant message will typically say "I have enough data" or "writing now" with no subsequent tool call. This is the most common synthesis failure and is almost NEVER caused by the write mechanism.
- `final | status=error` = the agent hit a hard tool error and gave up.
- `final | status=completed` with output file missing = the agent used `terminal echo` (not write_file) and the shell truncated/corrupted the output — only then is the write mechanism suspect.

**Misdiagnosis risk:** It is tempting to blame the write tool when a synthesis agent fails repeatedly. Almost always the real cause is context timeout — the agent spent too many turns on research and hit the turn limit just before writing. Check `exit_reason` in the transcript first.

**Fix for context-timeout failures:** Re-spawn with:
1. More pre-digested context in the packet (summarized findings, not raw sources)
2. An explicit research cap: "do at most 2 rounds of searches then write"
3. A write-early instruction: "write a skeleton to the output file first, then fill gaps"
4. Consider splitting: one subagent researches and writes raw notes, a second synthesises from those notes

## Forcing a specific model on a resumed delegation (opus/non-default model)

`delegate_task` has no per-call model override. All children use `delegation.model` from
config.yaml. If you need to resume a stalled session with a stronger model (e.g. opus 4.8
for a complex audit that exhausted a weaker model), use this pattern:

```bash
# 1. Temporarily set delegation model
hermes config set delegation.model claude-opus-4-8
hermes config set delegation.provider anthropic

# 2. Dispatch the resume task (now runs on opus 4.8)
delegate_task(action='spawn', tasks=[{"goal": "...", "context": "..."}])

# 3. The audit/resume agent MUST restore delegation model on completion
# Include in the task's goal:
# "After completing your work, run:
#   hermes config set delegation.model grok-4.6
#   hermes config set delegation.provider xai"
```

**Why:** `hermes chat -m claude-opus-4-8 --oneshot` only works for single-turn queries
(no multi-tool-call agentic loops). For a full multi-step resume, delegation + config override
is the correct approach.

**Restore safety:** If the subagent crashes before restoring, re-run the restore commands
manually: `hermes config set delegation.model grok-4.6 && hermes config set delegation.provider xai`.
Always check `delegation.model` in config.yaml after any such override session.

## Retired-WAL generation error (gateway held deleted WAL inode)

Trigger: a live Hermes gateway process held a retired state.db-wal generation after its pathname was deleted or replaced. Hermes halts the process and writes artifact dirs:
`~/.hermes/[profiles/<name>/]state.db.retired-wal-<timestamp>-<pid>/`

Each dir contains `manifest.json` with `main.mode` = `copied` or `header_only`.

**Recovery procedure (main or any profile):**

1. Stop writers — kill the stuck PID (it's in the dir name and in `manifest.json`):
   ```bash
   kill <pid>
   # Do NOT delete state.db or its -wal/-shm sidecars
   ```

2. Read manifests — check `main.mode` and `main.header.change_counter`:
   ```bash
   cat ~/.hermes/[profiles/fork/]state.db.retired-wal-*/manifest.json
   ```
   - `header_only` → forensic only, no copied db to inspect; skip to step 4.
   - `copied` → real WAL frames; continue.

3. Compare live db vs newest artifact change_counter **before** deciding to merge:
   ```python
   import struct
   def cc(path):
       return struct.unpack('>I', open(path,'rb').read(100)[28:32])[0]
   live = cc('~/.hermes/[profiles/fork/]state.db')
   art  = cc('~/.hermes/[profiles/fork/]state.db.retired-wal-<ts>-<pid>/state.db')
   # live >= art AND no live WAL file → live db already has all frames, no merge needed
   ```
   Also check `main.header.page_count` in the manifest — equal counts confirm no frames missing.

4. If live db IS behind the artifact, inspect before merging:
   ```bash
   hermes sessions recover \
     --source ~/.hermes/[profiles/fork/]state.db.retired-wal-<ts>-<pid>/state.db \
     --inspect-only [--profile fork]
   # Verify: "recoverable": true, "errors": []
   # Then run without --inspect-only to apply.
   ```

5. Integrity check then restart the gateway:
   ```bash
   python3 -c "import sqlite3; c=sqlite3.connect('$HOME/.hermes/[profiles/fork/]state.db'); print(c.execute('PRAGMA integrity_check').fetchone())"
   systemctl --user restart hermes-gateway[- fork].service
   ```

When multiple retired-wal dirs exist: work newest-first (highest change_counter). If the live db matches the newest, older artifacts are already subsumed.

Unwritten messages diverted during the error land in:
- `~/.hermes/[profiles/<name>/]sessions/<session_id>.jsonl`
- `~/.hermes/[profiles/<name>/]pending_messages/pending-*.json`

**Root cause prevention:** the gateway must run as a systemd unit with `TimeoutStopSec` ≥ 70s so systemd does not SIGKILL it mid-drain. Check with:
```bash
systemctl --user show hermes-gateway.service --property=TimeoutStopUSec
# Should be 1min 10s. If not: hermes gateway install --force
```
For secondary profiles (e.g. fork), install a separate unit:
```bash
hermes --profile <name> gateway install --force --start-on-login
```
And set drain timeouts in that profile's `config.yaml`:
```yaml
agent:
  restart_drain_timeout: 25
  cron_drain_timeout: 30
database:
  wal_autocheckpoint: 500
  journal_size_limit: 16777216
```
Without this, the profile's gateway inherits `user@1000.service`'s 45s kill timeout.

## Hermes update stall: update ran but session died before result

Pattern (observed 2026-08-30): session ran `hermes update --yes --backup` as its final
tool call but died before the result was returned. The next session sees:
- No tool result for the update call (`messages_after: 0` on that message)
- The update may have actually completed — the updater runs in a subprocess

**Do NOT re-run the update blindly.** Check first:

```bash
cd ~/.hermes/hermes-agent
git log -1 --oneline           # HEAD should have advanced from pre-update SHA
git status --short --branch    # no 'behind' count = update succeeded
hermes update --check          # confirms up to date
```

If HEAD advanced and `--check` says "Already up to date": the update succeeded.
Complete the remaining post-update protocol steps the stalled session skipped:

1. Check for a dangling pre-update stash: `git stash list`
   - If a `pre-update-<timestamp>` stash exists, pop it: `git stash pop stash@{N}`
   - Verify the position carefully — the updater's own autostash is normally cleaned
     up on success, so `stash@{0}` should be your named pre-update stash
   - If the pop produces a conflict, surface it to the user — do not force-resolve
2. Run `hermes config migrate` — check for Added/Updated/Removed lines (not just optional keys)
3. Run `hermes doctor` — confirm no new failures vs pre-update baseline
4. Verify gateway is active: `systemctl --user is-active hermes-gateway.service`
5. If the hindsight plugin was the stashed modification, verify the embedding key
   forwarding survived: `grep -c "HINDSIGHT_API_EMBEDDINGS_" ~/.hermes/hermes-agent/plugins/memory/hindsight/__init__.py`
   should return > 0

If HEAD did NOT advance (still at pre-update SHA), the update did not complete.
Re-run: `hermes update --yes --backup` with timeout=600.

## Common stall patterns

### Auxiliary model rejecting a parameter (60s retry loops)

If `errors.log` shows a session running 600-900+ seconds past its normal ceiling,
check whether the compression or auxiliary model is rejecting a parameter:

```bash
grep -E 'reasoning_effort|422|retry|compression' ~/.hermes/logs/errors.log | tail -20
```

**Signature (2026-08-18 to 2026-08-29, 136 sessions):** `mistral-small` was set as
`auxiliary.compression` model. It rejected the `reasoning_effort` parameter with HTTP 422,
producing 60-second retry loops on every compression cycle. Sessions appeared to be running
(PID active, no crash) but made no forward progress.

**Fix:** `hermes config set auxiliary.compression.model claude-haiku-4-5@anthropic`
(or whichever model is current). Avoid models that reject Hermes's standard parameter set.

**Recovery for stalled sessions caused by this:** the session cannot be recovered — the
retry loop exhausts the session timeout and the session terminates. Diagnose from errors.log,
fix the config, then re-dispatch the task on a fresh session.

### Write-then-stop (artifact on disk, tests skipped)

Session writes a file or applies patches (verified: true, lint: ok), then stops before
running tests. The code is on disk. Just run the tests:
```
terminal(command="python /tmp/test_<name>.py")
```

## What to check before resuming

- Confirm the artifact exists at the expected path
- Confirm lint/syntax is clean (use stalled session's lint result, or re-run `python -m py_compile`)
- Identify the first uncompleted step from the session transcript
- Do not re-apply changes the stalled session already made (check `patch` diffs and `write_file`
  verified results in the scroll output)

## Pitfall: test failure after resumption — Python module-global default parameter trap

When a stalled session implemented all the code but tests fail in the resumed session,
check for this before concluding the code is wrong:

A function with `param: str = ""` does NOT pick up a module-level global even if you set
`mod.VAR = "value"` after import. Python evaluates defaults at definition time.

**Signal:** test sets `mod.X = "value"`, calls `mod.func()`, asserts result contains `"value"`,
gets `""` instead.

**Fix:** inside the function body, add: `if not param: param = MODULE_VAR`

This pattern appears whenever a "run-time state variable" (active session ID, current grant,
active model override) is intended to be inherited by functions as a fallback when no
explicit value is passed.

## Verification checklist

- [ ] `messages_after: 0` confirmed in session scroll
- [ ] Final tool results reviewed — completed steps identified
- [ ] Artifacts verified on disk before resuming
- [ ] Tests run and passing in the resumed session
- [ ] No duplicate patching of already-applied changes

## Sweep 29 Additions (Aug 2026)

### Checkpointed Control-Flow: Resume from Broken Node (Qiita JP, Aug 2026) ★ HIGH

Production pattern: LLM must return **answer + judgment_path + state** (not just the answer).
When a failure occurs, resume from the broken node — never restart from step 1.
Errors rendered as the same flow graph. Distinct from Handoff Tax/Constraint Weakening:
this is checkpointed control-flow, not compressed handoff.

**Hermes implementation via skill-state.py:**
```
skill-state.py init --session SID --skill SKILL_NAME --spec "task spec"
skill-state.py step --session SID --skill SKILL_NAME --observation "step N: broke here"
# On restart:
skill-state.py show --session SID --skill SKILL_NAME  # inject state into context
# Resume from last completed step, not from scratch
```

### DART-SD Breakpoint Annotation (arXiv:2608.18524) ★ HIGH

When stalled: localize the Critical Topological Breakpoint (CTB — exact step where
trajectory diverged from valid prefix). Annotate it in skill-state.py before exiting.
Next session: retrieve breakpoint + recovery pattern via unified-recall, resume from CTB.

Never replay full failed trajectory — error propagation is the dominant failure mode.

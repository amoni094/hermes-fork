---
name: hermes-session-hygiene
related_skills:
  - hermes-context-hygiene
  - hermes-context-budgeting
  - hermes-obsidian-sync
triggers:
  - Cleaning up inactive or stale Hermes sessions from the session database
  - User wants to delete specific inactive sessions without touching live ones
  - Distinguishing live sessions from stale open rows before deletion
  - Session count is high and old sessions need pruning
description: >
  Use when cleaning up inactive Hermes sessions safely by distinguishing live sessions from stale/open rows, deleting specific inactive sessions, and verifying the session store afterward.
version: 1.0.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, sessions, cleanup, sqlite, cli, hygiene]
---

# Hermes Session Hygiene

Use this when the user asks to clean up, prune, or inspect Hermes sessions, especially when `hermes sessions list` shows blank, inactive, or obviously stale entries.

This is a narrow session-cleanup skill. If the problem is broader context bloat inside the current live conversation, load `hermes-context-hygiene` instead. If you are deciding where prior continuity should be retrieved from, load `hermes-memory-surface-selection`.

## Triggers

- "clean up inactive sessions"
- "prune old Hermes sessions"
- "why do I have so many empty sessions?"
- "which sessions are still open?"
- "delete stale CLI/TUI sessions but keep the live one"
- "sessions are building up / accumulating over time"
- "DB is huge" / "state.db is large"
- inspecting why a daily prune cron left hundreds of sessions behind
- "a session stalled — continue its tasks" or "pick up where it left off" (see Session Archaeology below)
- "figure out what happened" / "why did this session stall" — diagnosis rather than resumption (see Diagnosing WHY a session stalled below)

## Session Archaeology: Recovering Stalled Session Work

When the user says "a session stalled — continue its tasks" or "pick up where it left off":

**READ THE SESSION BEFORE DELETING IT.** Once deleted, `session_search(session_id=...)` returns "session_id not found" with no recovery path.

The correct sequence:
1. Check open sessions via SQLite (`ended_at IS NULL`).
2. Call `session_search(session_id=<id>)` on the stalled session to read its full transcript.
3. Context compaction summaries embedded mid-transcript are especially rich — look for blocks starting with `[CONTEXT COMPACTION — REFERENCE ONLY]`. They contain: Completed Actions, Active State, Historical Pending User Asks, Historical Remaining Work, and Key Decisions.
4. If the user also wants the session deleted, delete it AFTER reading.
5. If the session is already gone: try `session_search(query="CONTEXT COMPACTION Historical Task Snapshot", sort="newest")` — compaction blocks are stored in message content and persist via FTS5 even after you can't look up by session_id directly.

**Conflict warning:** if the user asks "kill all inactive sessions" AND "continue its tasks" in the same request or back-to-back, these conflict. The session deleted first cannot be read. Warn the user before deletion when you detect this pattern (session has nonzero message_count and they've said something about stalled work).

### Reconstruction when the session itself was compacted mid-flight

When the stalled session's transcript contains a `[CONTEXT COMPACTION — REFERENCE ONLY]`
block as the last thing before the stall, the summary may be a deterministic fallback
(no LLM available at compaction time) — meaning "Completed Actions" and "Active State"
are unreliable. In that case, reconstruct ground truth from live state instead:

1. **Read delegation logs directly.** If agents were dispatched, their logs survive in
   `~/.hermes/cache/delegation/live/deleg_<id>/task-N.log`. Find the most recent
   `deleg_*` dirs with `ls -lt ~/.hermes/cache/delegation/live/ | head -10`. For each,
   extract the `final` lines to get status + summary without reading the whole log:
   ```bash
   grep -h "^[0-9].*final" ~/.hermes/cache/delegation/live/deleg_*/task-*.log
   ```
   If those show `status=completed`, the agents finished — check what their summaries say
   before assuming work is pending.

2. **Cross-check via grep before patching.** Before implementing any finding the
   compacted summary claims needs fixing, grep the live skill/script to confirm the fix
   isn't already there. Previous sessions often apply patches mid-run before compaction.
   A "D4: type tags not being set" finding from an audit agent may already be in the
   code; the compacted summary was just the pre-patch snapshot.

3. **Scroll the prior session to the last real turn.** Use
   `session_search(session_id=<id>)` to get first+last messages, then scroll with
   `around_message_id=<last_id>` to find exactly where work stopped — specifically which
   tool calls were in-flight vs which had returned results. This tells you whether the
   session died before or after action.

4. **Absence of evidence ≠ bug.** If an audit finding says "X is not being set" but the
   code is correct and the input data (e.g. `staging.md`) is empty, the code is
   untested, not broken. Don't add fixes for untested-but-correct code.

### Diagnosing WHY a session stalled (not just recovering it)

When the ask is "figure out what happened" / "why did this stall" rather than "continue it", the goal is root-cause, not resumption. Two techniques and a checklist that came out of a real dual-session diagnosis:

**Fallback when `session_search(around_message_id=...)` errors "not in session_id".** This happens when the message ID you have (e.g. from a truncated/compacted transcript reference) doesn't exist in that session — often because compaction renumbered or dropped it. Don't retry with guessed IDs. Go straight to SQLite for the session's tail:
```python
import sqlite3
conn = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
c = conn.cursor()
c.execute("SELECT id, role, tool_name, substr(content,1,300), timestamp FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 10", (session_id,))
for r in reversed(c.fetchall()):
    print(r)
```
This reads the actual last N rows regardless of ID gaps, and shows role/tool_name/content/timestamp — enough to see exactly where the transcript stops and why.

**Common stall root causes, cheapest-to-check first:**
1. **Unanswered `clarify()` prompt.** The agent asked a question (often after a blocked/denied command) and the user moved to a different session instead of answering. The transcript just ends on a `tool` row with `tool_name: clarify`. Not a crash — a pending decision.
2. **User denied/blocked a command mid-task.** Look for a tool result with `"error": "BLOCKED: User denied this command..."`. The agent's next move is usually a `clarify()` asking what to do instead (see #1) — check that it happened and wasn't itself abandoned.
3. **Conversation trails off with no error at all.** The last rows are ordinary tool calls (e.g. `search_files`, `terminal`) with no exception, no block, no clarify — the user simply context-switched to another session and never sent a final turn. This is normal multitasking, not a bug; don't over-diagnose it as an infra failure.
4. **Unrelated background-command errors in scrollback are red herrings.** A container/exec error or similar from an earlier diagnostic command in the same session is not automatically the cause of the stall — check whether it precedes the actual last user/assistant exchange or is just noise from an earlier unrelated step.

Report findings as "stalled on X, not resumed because Y" (pending clarify answer / abandoned mid-investigation / user switched away) rather than assuming infrastructure failure by default — most stalls are conversational, not systemic.

## Goals

1. Preserve the active session the user is currently using.
2. Remove stale open sessions with low or zero value.
3. Prefer explicit deletion of identified session IDs over broad pruning when recency matters.
4. Verify the result in both the CLI view and the SQLite session store.

## Workflow

1. Check Hermes session commands first.
   - Use `hermes sessions prune --help` to confirm broad-prune options.
   - Use `hermes sessions delete --help` to confirm targeted deletion syntax.

2. Inspect current session inventory.
   - Run `hermes sessions list` to see recent titles, last-active timestamps, and IDs.
   - Run `hermes sessions stats` to capture the before-state.

3. Distinguish live processes from stale session rows.
   - Check running Hermes processes separately; do not assume every open session row is still active.
   - The active CLI session usually appears as the newest open `cli` session.
   - Concrete cross-check: after pulling `ended_at IS NULL` rows from SQLite, run
     `ps aux | grep -i hermes | grep -v grep` and confirm none of the candidate
     stale IDs correspond to a still-running process. This matters especially for
     `source=subagent` rows — they can sit at `ended_at IS NULL` even after their
     parent task has finished, so the DB alone over-counts "open" sessions. A
     background job you started yourself (e.g. `hermes update` via
     `terminal(background=true)`) is a process, not a session row — don't confuse
     the two, and don't touch anything tied to it while it's still running.
   - **How to actually correlate a `ps aux` row to a session ID** (the ps output
     carries no session ID, so this isn't automatic): match each live
     `.../venv/bin/hermes` process's start time (the `STIME`/time column, or
     `ps -o pid,lstart,cmd -p <pid>` for exact seconds) against the `started_at`
     of open `cli` sessions. A live process launched at 16:38 lines up with a
     session `started_at` of 16:38:5x — that pairing is the live session; every
     other open `cli` row with no matching process start time is a genuine
     stale stub, safe to delete regardless of how recent its `last active`
     timestamp looks. Recency alone is not liveness — a stale row can still show
     "just now" if a tool call touched it moments ago without a process behind
     it.

4. Inspect the SQLite store when the CLI list is ambiguous.
   - Query `~/.hermes/state.db` table `sessions` for rows with `ended_at IS NULL`.
   - Review `id`, `source`, `started_at`, `title`, and `message_count`.
   - Stale candidates are often old `cli`/`tui` rows with `message_count = 0` or tiny counts and no active matching process.

5. Read borderline sessions before deleting.
   - If a session has a small nonzero message count, inspect it before deletion rather than guessing.
   - Keep sessions that are current, user-meaningful, or clearly tied to still-running work.

6. Delete explicitly by session ID — or bulk-close via Python when the list is large.
   - Use `echo y | hermes sessions delete <session_id>` for small counts (<10 sessions).
     **IMPORTANT: `hermes sessions delete` has NO `--yes` / `-y` flag.** It always prompts
     interactively. You MUST pipe `y` via stdin — `echo y | hermes sessions delete <id>` — or
     it will print "Cancelled" and do nothing. Do NOT use `--yes`; it is not a valid flag and
     will error.
   - For small batches via loop:
     ```bash
     for id in <id1> <id2> ...; do
       echo y | hermes sessions delete $id && echo "deleted $id" || echo "failed $id"
     done
     ```
   - For large counts (50–500+ sessions), use a self-draining while-loop with `--limit 500`. The DB often holds far more sessions than a single pass reveals — `list` pages results so sessions beyond the limit stay hidden until the prior batch is deleted. Loop until clean:
     ```bash
     CURRENT="<current_session_id>"
     while true; do
       IDS=$(hermes sessions list --limit 500 2>&1 | tail -n +3 | awk '{print $NF}' \
         | grep -E '^[0-9]{8}_[0-9]{6}_[a-f0-9]+$' | grep -v "$CURRENT")
       COUNT=$(echo "$IDS" | grep -c .)
       [ "$COUNT" -eq 0 ] && echo "CLEAN" && break
       echo "--- pass: $COUNT remaining ---"
       echo "$IDS" | while IFS= read -r sid; do
         echo y | hermes sessions delete "$sid" 2>/dev/null && echo "deleted $sid" || echo "FAILED $sid"
       done
     done
     ```
   - **Why the while-loop is required:** after deleting the first 500, the next page becomes visible. Real-world runs have seen 300+ sessions requiring 20+ passes to clear completely.
   - When `ended_at IS NULL` returns many rows (50+ stale cron sessions is common after long uptime), the shell loop above is preferred over raw SQLite; it is simpler and produces clean per-session confirmation output.
   - See `references/session-cleanup-checks.md` for the Python/SQLite bulk-close script (needed when CLI is unavailable or you need finer filtering).
   - Prefer explicit deletion over `prune --older-than` when the task is "inactive sessions" rather than "old ones".

7. VACUUM the database after bulk deletions.
   - SQLite does NOT reclaim file space on DELETE — rows are marked free but the file stays large.
   - **Preferred:** run `hermes sessions optimize` — it merges FTS5 indexes AND runs VACUUM in one step, and reports before/after DB size. Cleaner than calling sqlite3 directly.
   - Fallback if `optimize` is unavailable: `python3 -c "import sqlite3; c=sqlite3.connect('$HOME/.hermes/state.db'); c.execute('VACUUM'); c.close()"`.
   - Rule of thumb: if `du -sh ~/.hermes/state.db` is much larger than `hermes sessions stats` implies, a VACUUM is overdue.
   - In the `session-prune.sh` script, gate it on DB size (>300 MB) to keep cheap on small installs. See `references/session-prune-script.md` for the full script.
   - Real-world result: 129 sessions deleted → 513 MB → 301 MB (212 MB reclaimed) in a single `hermes sessions optimize` call.

8. Verify after deletion.
   - Recheck `hermes sessions stats`.
   - Requery `state.db` for remaining `ended_at IS NULL` rows.
   - Confirm that only the actual live current session remains, or explain any remaining cron/live sessions.

## Root Causes of Session Accumulation

Before jumping to cleanup, diagnose WHY sessions accumulated:

1. **Schedule drift / missed cron fire** — if `last_run_at` on the prune job is hours after the cron `expr` time (e.g. `0 3 * * *` but last ran at 10am), Hermes was not alive at the scheduled hour. The fix is to change to an interval schedule (`every 240m`) so any alive window catches up. A once-daily 3am job is a single point of failure.

2. **No VACUUM in prune script** — pruning removes rows but SQLite keeps the pages allocated. The DB file grows unboundedly even with perfect pruning. Always add a VACUUM step.

3. **LLM-driven cron jobs create `source=unknown` sessions, not `source=cron`** — this is the most common silent prune failure. When a cron job has `no_agent=false`, the agent sessions it spawns are tagged `source=unknown` in the DB. Prune scripts that only run `--source cron` silently miss all of them. **Always include a `--source unknown` pass** with short retention (1–2 days) in every prune script. Verify via:
   ```python
   python3 -c "
   import sqlite3
   db = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
   rows = db.execute('SELECT source, COUNT(*) FROM sessions GROUP BY source').fetchall()
   print(rows); db.close()
   "
   ```
   A large `unknown` count means the prune is silently missing cron-LLM sessions.

4. **High-frequency LLM cron jobs** — a job running every 60m creates 24 sessions/day. Obsidian sync, memory sync, and similar jobs rarely need sub-hour freshness. Prefer every 240m (4h) unless there's an explicit real-time requirement. To change: `cronjob(action='update', job_id=..., schedule='every 240m')`.

5. **Subagent sessions unscoped** — `hermes sessions prune --older-than 7` catches them, but adding an explicit `--source subagent --older-than 3` pass keeps the table tighter.

## Decision Rules

- Keep the current session, even if it is untitled or has `message_count = 0`.
- Treat cron sessions separately from CLI/TUI cleanup; they may still be valid if tied to active jobs.
- If a cron session is clearly stale and not still running, it can be deleted, but verify more carefully than for empty CLI/TUI rows.
- Empty untitled sessions are strong deletion candidates when they are not the current live session.

## Verification Checklist

- `hermes sessions list` still shows the current session.
- `hermes sessions stats` reflects a reduced total.
- SQLite `sessions` query shows only genuinely live open sessions.
- No claim of success without post-delete verification.

## Stateless-Compute / Persistent-Storage Agent Persistence Pattern (Latent Space, Sweep 16)

Observed in ChatGPT Work architecture (Latent Space, Aug 2026). Solves the always-on-VPS
vs. serverless tradeoff for long-running agent tasks.

**Pattern:** Separate agent compute (ephemeral, stateless) from agent state (persistent, durable).
- Each task runs on an isolated ephemeral VM/container
- Working directory is synced to persistent storage (not in-process memory)
- On resume/retry, a NEW VM restores the working directory from storage — compute identity
  changes but task state is continuous

**Why this matters for Hermes session hygiene:**
Long Hermes sessions accumulate state in two places: the conversation context (ephemeral,
compacted) and the filesystem (durable). The pattern makes explicit that filesystem artifacts
are the durable layer — not the conversation. Hygiene implication:

- Any artifact that must survive session restart or compaction should be written to disk,
  not kept in context: `~/.hermes/agent-workspace/`, canvas refs, checkpoint files
- Treat the context window as the compute layer (ephemeral, reconstructible from disk)
- Treat `~/.hermes/` subdirectories as the storage layer (durable, sync-able)

**Applied to Hermes cron jobs and long delegate_task pipelines:**
Write checkpoint files at each major stage (already in `hermes-role-pipelines`'s Handoff
Checkpointing section). The stateless-compute pattern is the architectural justification:
if the cron job or subagent fails mid-run, the checkpoint lets a fresh spawn resume from
the last completed stage without re-doing prior work. The new VM doesn't need the old
process — it just needs the checkpoint file.

**Resumable sessions checklist:**
1. Write artifacts to `~/.hermes/agent-workspace/<task_id>/` not to temp paths
2. Write a stage checkpoint after each major pipeline step
3. Never treat in-context state as durable — assume it will be lost
4. On resume: read checkpoint, verify artifact existence, start from last completed stage

## Pitfalls

- **SQLite `sqlite3` binary often absent on Fedora Atomic/Silverblue** — use `python3 -c "import sqlite3; ..."` instead of the `sqlite3` CLI. The python stdlib sqlite3 module is always present.
- Do not use age alone as the definition of inactive; a recent row can still be stale, and an older row may still matter.
- Do not delete the newest open CLI session just because it has zero messages; that is often the current shell session.
- Do not assume blank titles mean worthless sessions; inspect low-count sessions if there is any doubt.
- Do not stop after `hermes sessions list`; the SQLite store is the tie-breaker when open-session state is unclear.
- The correct subcommand is `hermes sessions` (PLURAL), not `hermes session` (singular). `hermes session kill <id>` and `hermes session delete <id>` do not exist — they both error with "invalid choice: 'session'". Always use `echo y | hermes sessions delete <id>` (pipe `y` for the confirmation prompt — there is no `--yes` flag). When in doubt, run `hermes sessions --help` first to confirm available subcommands.
- **`started_at` and `ended_at` are Unix epoch floats**, not ISO strings. Use `datetime.datetime.fromtimestamp(float(r['started_at']))` when querying; slicing `r['started_at'][:16]` will TypeError.
- **Pruning does not shrink the DB file** — always follow a big prune with VACUUM. A 1.1 GB DB with only 27k messages is a clear sign VACUUM has never run.
- **Prune scripts that only target `--source cron` are broken by design** — LLM-driven cron sessions land as `source=unknown`. Every prune script must include both: `hermes sessions prune --source cron --older-than 2 --yes` AND `hermes sessions prune --source unknown --older-than 2 --yes`. When auditing an existing prune script, check for the `unknown` line; if it's missing, add it.
- **Two separate prune scripts may exist** — `session-prune.sh` (runs every 4h) and `prune_sessions.sh` (runs daily at 2am) both need the `--source unknown` fix. If you patch one, always check the other.
- **Second `hermes sessions optimize` call reports 0 MB reclaimed** — this is expected and not an error. VACUUM only reclaims pages that weren't already compacted; running it twice in one cleanup pass is harmless but the second pass will always show 0.
- **`hermes sessions stats` DB size after optimize may report a tiny number** (e.g. 0.5 MB) even when `du -sh state.db` shows hundreds of MB. The stats command reports logical data size, not physical file size. Both are correct simultaneously; the VACUUM already ran.
- **Delete before read = unrecoverable.** If the user requests both "delete inactive sessions" and "continue the stalled session's work" in close sequence, read the stalled session transcript via `session_search(session_id=...)` BEFORE deleting. After deletion the session_id lookup returns "not found" immediately — there is no fallback. This bit us on 2026-07-04: session 20260704_200140_726f9e was deleted then reconstruction had to go through archaeology of older compaction summaries in related sessions.

## Stateless-Compute + Persistent-Storage Split (Latent Space, Aug 8 2026) — Sweep 16 MED

Pattern from ChatGPT's internal Work architecture: separate compute (stateless, ephemeral workers
that run tasks) from storage (persistent, queryable memory that survives worker death).

**Hermes analogue:**
- **Compute** = Hermes cron job agents (ephemeral, die when the job ends, no state)
- **Storage** = Hindsight + Graphiti (persistent, survives job restarts and crashes)

**Practical implication for session hygiene:**
Prune sessions aggressively (they are compute artifacts), but NEVER prune Hindsight or Graphiti
entries (they are storage). Session transcripts are expendable; promoted memory is not.

**When designing a new cron job:**
1. Decide upfront what the job's durable outputs are (Hindsight facts? Graphiti nodes?).
2. Ensure those outputs are written BEFORE the job can be interrupted.
3. The job's session transcript is a recovery artifact, not the primary output — treat it as such.

**For session pruning thresholds:**
Sessions older than the job's retry window are always safe to prune if their durable outputs
were promoted. Sessions with no Hindsight/Graphiti writes may contain unrecovered insights —
scan before pruning with `session_search(query="key finding decision")` on the session_id.

## References

- `references/session-cleanup-checks.md` — compact SQLite queries and deletion heuristics used during a real cleanup pass.
- `references/session-prune-script.md` — the recommended `session-prune.sh` with subagent pass + conditional VACUUM, and notes on the every-4h schedule.
## Reference files

- `references/sqlite-url-recall-pattern.md` — Session DB: Raw SQLite URL/Link Recall

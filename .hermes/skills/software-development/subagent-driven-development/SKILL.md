---
name: subagent-driven-development
depends_on: [plan, complexity-gated-planning, verification-before-completion]
provides: [multi-agent-implementation, delegated-development, context-packet-handoff]
related_skills:
  - dispatching-parallel-agents
  - hermes-agent-sync
  - hermes-role-pipelines
  - autonomous-agent-loop-design
  - verification-before-completion
  - workflow-map
  - hermes-acp-routing
  - complexity-gated-planning
  - requesting-code-review
triggers:
  - Implementing a larger coding task that should be split across focused Hermes subagents
  - Need compact context packets and explicit review/verification handoffs between agents
  - Multi-phase implementation: discovery → implement → review workers with parent verification
  - Task is too large or context-heavy for a single agent and should be delegated in phases
description: >
  Use when implementing larger tasks with focused Hermes subagents, compact context packets, and explicit review/verification handoffs.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, multi-agent, implementation, verification, review]
    related_skills: [workflow-map, hermes-role-pipelines, hermes-acp-routing, complexity-gated-planning, requesting-code-review, verification-before-completion]
---

# Subagent-Driven Development

Use this skill when a task is big enough, noisy enough, or separable enough that a fresh worker context will improve quality.

## Core Principle

Use subagents to reduce context overload and separate roles, not to add ceremony for its own sake.

## When to Use

Use this when one or more are true:
- the task naturally splits into discovery, implementation, and review
- the codebase area is large enough that one agent would drown in search output
- independent subtasks can run in parallel (**max 3 concurrent** per `delegate_task` batch; config: `delegation.max_concurrent_children`)
- you want a fresh reviewer that did not author the change
- the user explicitly asks for parallel agents or subagents

Avoid this when:
- the task is tiny and obvious
- the work depends on constant back-and-forth with the user
- the task is mostly a single shell command or one file edit
- there is no clean boundary between subtasks

Start by loading `workflow-map` and `complexity-gated-planning` to decide whether delegation is justified.

## Standard Role Split

Use the smallest split that fits the task.
Choose the collaboration pattern first, then the worker labels.

### Pattern A — Discovery -> Implement -> Verify
Harness mapping: Pipeline.
1. discovery worker
2. implementation worker
3. verification/review worker

### Pattern B — Parallel discovery -> single implementation -> review
Harness mapping: Fan-out / Fan-in -> Producer-Reviewer.
1. parallel discovery workers for independent surfaces
2. one implementation worker using their findings
3. one reviewer/final verifier

### Pattern C — Planner -> implementer -> reviewer
Harness mapping: Producer-Reviewer.
Use this when the shape of the change is unclear at the start.

### Pattern D — Parent supervisor with worker waves
Harness mapping: Supervisor.
Use this when new findings may change what should be edited next. The parent keeps the todo list and dispatches narrowly scoped waves instead of trying to pre-plan every child.

**Special case: Orchestrator subagent for multi-phase config/infrastructure work**
When a task spans 5+ phases (audit → implement → verify → export → push) with internal cross-phase dependencies, delegate to a single `role='orchestrator'` subagent instead of spawning sequential waves. The orchestrator owns all phases in one context, verifies intermediate outputs before moving forward, and commits locally with a structured message.

**However: the parent retains three critical hand-offs**
1. **Final durable documentation** — the orchestrator produces research; the parent writes the upgrade doc for human readers (narrative + rationale + categorization by risk). File: `docs/upgrade-pass-{DATE}.md`.
2. **Git push and conflict resolution** — the orchestrator commits locally; the parent handles `git pull --rebase` and any manual merge conflict resolution (e.g., choosing "ours" for mechanical overwrites).
3. **Verification of exported artifacts** — the parent checks that secrets are stripped (grep config for no api_key), scripts exist, docs are readable, and final push succeeded.

See `references/multi-phase-config-orchestration.md` for context packet template, durable pitfalls, model routing (prefer claude-fable-5 for 5+ phase coordination), hermes-specific export patterns, and verification checklist.
See `references/file-patch-unicode-escape-mismatch.md` for diagnosing and fixing patch/str.replace misses caused by literal `\uXXXX` escape sequences in files written by subagents.

### Pattern E — Conditional specialist dispatch
Harness mapping: Expert pool.
Use this when only some specialties are needed depending on what discovery finds; for example, spawn security only if secrets/auth are touched.

### Pattern F — Delegate an entire recursive convergence loop to one subagent
Harness mapping: Self-contained iterative worker (not parent-orchestrated passes).
Use this when the task IS a recursive fix-and-re-review loop (e.g. `adversarial-review`'s
"Recursive Fix-and-Re-Review Loop") and the loop can run to convergence without user input
mid-loop. Rather than the parent session issuing one `delegate_task` per pass, dispatch a
single background subagent with the entire loop as its goal, and require it to:
- load the governing skill(s) itself via `skill_view` (name it explicitly in the context —
  don't paste the skill body into the packet; the subagent has the same tool access you do)
- run passes until a named, checkable convergence criterion is met (e.g. "zero HIGH/MEDIUM
  findings in a full pass"), with an explicit cap (e.g. "stop and flag as structural if still
  finding MEDIUM after 6 passes" — matches the skill's own convergence guidance)
- keep every pass's findings-log VISIBLE IN THE DELIVERABLE FILE ITSELF (a dated "Adversarial
  Self-Review Log" section), not just performed silently — this is what makes a background
  subagent's self-reported convergence independently checkable rather than trust-only
- re-verify any citations/claims used across its own fix passes against the original source
  material before finalizing (citation drift/invention across iterative self-edits is a real
  failure mode — the subagent editing its own claims pass over pass can quietly alter a cited
  arXiv ID or regulation article without noticing)
- report back: pass count to convergence, final severity tally, and confirmation the
  citation-reverification step ran

This is a genuine one-subagent-does-the-whole-loop pattern, distinct from Pattern A/D — the
parent doesn't referee passes, it only verifies the finished artifact's visible pass log and
spot-checks a sample of citations before treating "converged" as true. Confirmed useful July
2026: a governance-framework gap-analysis critique, grounded in 6 prior research files, was
dispatched as one subagent with this exact loop and returned a converged, self-documenting
critique file without parent intervention between passes.

### Not supported directly — Hierarchical delegation
Harness includes hierarchical delegation, but Hermes children here cannot spawn further children. Flatten the tree into parent-managed waves.

## Compact Context Packet

Every worker prompt should include only:
- exact goal
- exact file paths or directories
- exact errors, failing commands, or acceptance criteria
- scope limits
- required output contract

Good output contract:
- changed files
- commands run
- pass/fail result
- unresolved risks

Do not dump the whole conversation. Do not pass irrelevant files.

## Hermes Delegation Pattern

Use `delegate_task` directly.

Single worker:
```python
delegate_task(
  goal="Implement the fix for the failing cache invalidation path.",
  context="Files: src/cache.py, tests/test_cache.py. Acceptance: failing test passes, no unrelated edits. Return changed files and exact test commands run.",
  toolsets=["terminal", "file"]
)
```

Parallel workers:
```python
delegate_task(tasks=[
  {
    "goal": "Inspect the auth middleware path and identify likely failure points.",
    "context": "Read-only. Return affected files, likely root cause, and any missing tests.",
    "toolsets": ["terminal", "file"]
  },
  {
    "goal": "Inspect the session persistence path and identify likely failure points.",
    "context": "Read-only. Return affected files, likely root cause, and any missing tests.",
    "toolsets": ["terminal", "file"]
  }
])
```

## Required Handoffs

### Before implementation

For L2+ tasks, run select-frameworks to determine reasoning gates for workers:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<implementation goal>" --level <L>
  ```
  Add the primary framework list to each worker's context packet.
  For long-horizon tasks: include lookahead invocation instructions in the worker goal file.
  For subtask-boundary tasks: include subplan-verify instructions at each handoff point.
- decide whether `isolated-workspace-preflight` is needed
- decide whether `test-driven-development` applies
- check local workspace or vault context first before spawning workers, so delegation starts from current project reality rather than a stale chat summary
- state the acceptance criteria in the worker context

## Delegation Boundary and Durability

Use ordinary subagents only for bounded work that can safely die with the current session.

- before delegation, inspect the local workspace/vault context and then pass a compact context packet, not a raw conversation dump
- if the work must outlive the current turn or session, prefer a durable mechanism such as background Hermes runs or cron instead of ordinary delegation
- long-lived work should leave an inspectable trail in `~/.hermes/logs/hermes-task-ledger.jsonl` so future sessions can recover state

### After implementation
- run `requesting-code-review` or at least the review depth chosen by `risk-based-review`
- use `verification-before-completion` before claiming success

## Recommended Review Model

The implementer should not be the final verifier for non-trivial work.

Preferred sequence:
1. implementation worker makes the change
2. reviewer worker checks diff, risks, and regressions
3. parent agent verifies any claimed side effects with direct tool calls

## Integration with Autonomous-Agent Skills

**hermes-role-pipelines:** Use when you want named specialist roles such as finder, debugger, coder, reviewer, tester, or security rather than generic worker labels.

**hermes-acp-routing:** Use when you want to route a narrow implementation task through a verified ACP-compatible external CLI. Prefer normal Hermes delegation unless ACP transport is known-good.

**workflow-map:** Use first to decide whether the task needs delegation at all.

## Anti-Patterns

Do not:
- spawn workers for trivial edits
- pass giant unfiltered context blobs
- trust a worker claim of success without verification
- let implementation and final verification collapse into the same fresh-context role on risky changes
- keep looping workers without tightening the scope after failures
- tell a subagent to "ask for approval before running the script" — there is no user present in a background delegation; the subagent will stall waiting for input that never comes. Either authorise the action in the goal, or split into a discovery subagent (returns the script) + parent runs it
- dispatch a subagent for a task that returns large inline output (multi-page visual audits, bulk research dumps) without controlling result size — the result lands atomically in the parent context window and can flood it (see Context Flood Prevention below)
- reference a skill by name in a subagent's context packet without checking whether it's enabled — a disabled skill makes `skill_view` return an error to the subagent, and without an explicit fallback instruction the subagent may silently invent values (brand colors, API params, config defaults) instead of reading the skill's files directly. If a task depends on a skill you know or suspect is disabled, tell the subagent in the context packet to read the skill's file(s) via `read_file`/`search_files` instead of relying on `skill_view`.

## Context Flood Prevention

Subagent results land as a single atomic message in the parent context. If the result is large (multi-page vision audits, bulk text extractions, long research summaries), the parent context window can overflow, causing the session to stall.

**Three controls — use whichever fits:**

1. **Write to file, return path.** Tell the subagent explicitly: "save your full findings to /tmp/result-TASKNAME.txt and return only the file path." The parent then reads the file in chunks with `read_file(offset=..., limit=...)` at its own pace. One short path line lands in context instead of 20KB.

2. **Scope subagents narrowly.** "Audit pages 1-3" x 3 subagents instead of "audit all 9 pages" in one. Each result is bounded and lands separately.

3. **Prefer `execute_code` for bounded multi-step work.** If the task is: read file → compute → write output (no mid-task reasoning gap needed), `execute_code` is better than `delegate_task`. Output is capped at 50KB and runs in a subprocess rather than a delegated context window.

## Special Pitfall: Recovering from a Crashed Parent Session (background delegate_task)

Background `delegate_task` subagents live and die with the parent session's process — despite running "in the background" for the current turn, they are NOT durable across a parent crash/restart. If the parent session is killed (crash, forced restart, `/new`) before a subagent finishes, that subagent's work is silently discarded: no error surfaces, no partial output, nothing written to disk. This is distinct from a subagent that is merely slow — a slow one eventually lands; a killed one never will, and nothing tells you which happened.

When resuming a session after a crash/restart where background `delegate_task` calls were in flight (signals: a preserved todo item still shows `in_progress`, or the transcript shows a "dispatched, N subagents running" tool result with no later consolidated result):

1. **Do not trust the todo list or the prior dispatch confirmation as evidence of completion.** A todo item surviving context compaction only means it was `in_progress` at capture time — it says nothing about whether the subagent actually finished.
2. **Verify against disk state directly**, not against memory of what was asked. Check file existence/mtime for every output path that was requested (`search_files`/`stat`), and check `ps aux` for orphaned processes that might indicate a subagent is still genuinely running rather than dead.
3. **Partial landing means partial loss, not partial progress.** If 1 of 3 parallel subagents wrote its output file and 2 didn't, the missing 2 were killed mid-run and produced nothing recoverable — there is no resumable state to continue from. Re-dispatch only the missing scopes as a fresh `delegate_task` call; do not re-run the scope that already completed and do not assume the dead ones got partway there.
4. **Tell the user plainly what was lost vs. kept** before re-dispatching, so they can decide whether the gap needs to be redone or is acceptable to skip.
5. **When re-dispatching, tell the redo subagent explicitly that a prior attempt was killed mid-run and produced no output** — this avoids the redo agent assuming partial credit exists somewhere or hedging its own completeness.

This bites hardest on multi-wave research/audit workflows (e.g. an adversarial critique built from several parallel research subagents writing separate files) where a single crash can silently erase most of a wave's work with zero visible error — the only tell is an output file that should exist and doesn't.

## Special Pitfall: Orchestrator Hand-Offs on Multi-Phase Work

When delegating a 5+ phase task to an orchestrator, the orchestrator commits locally but the parent must complete three hand-offs:

1. **The orchestrator does not write durable upgrade documentation.** After the orchestrator finishes, the parent should write `docs/upgrade-pass-{DATE}.md` with:
   - Narrative summary of what was changed and why
   - Categorization by risk (CRITICAL / HIGH / MEDIUM / LOW)
   - Specific commands for reproducibility (e.g., exact `hermes config set` calls)
   - What was skipped and why

   This is a parent responsibility because durable docs are read by humans months later and need narrative structure, not just checklist items.

2. **The orchestrator commits but cannot resolve git push conflicts.** After the orchestrator returns, the parent must:
   - Run `git pull --rebase` to bring in remote changes
   - Manually resolve any conflicts (e.g., `git checkout --ours` for mechanical overwrites)
   - Run `git rebase --continue` and `git push` to finish the push

   This is a parent responsibility because conflict resolution requires human judgment about which version is authoritative.

3. **The parent must verify exported artifacts.** After the orchestrator's push, the parent should verify:
   - Secrets are stripped from exported configs: `grep -i "api_key\|auth\|token" config.sanitized.yaml` should be quiet
   - New docs are present and readable
   - Git push succeeded: `git log --oneline -3` should show the upgrade commit reachable on origin

See `references/multi-phase-config-orchestration.md` for a full durable pitfall walkthrough with command examples.

## Minimum Safe Pattern

For any non-trivial delegated coding task:
1. compact context packet
2. implementation worker
3. independent review
4. direct verification by parent or final verifier

## Multi-phase config/infrastructure orchestration (from references/multi-phase-config-orchestration.md)

Use when delegating large-scale infrastructure/config upgrades spanning multiple sequential phases (audit → implementation → export → validation → push) to a single orchestrator subagent.

**Pattern structure**: orchestrator runs 5 phases serially, verifying outputs before moving on:
- Phase 1: Audit (read rules, check hooks) → Phase 2: Implementation → Phase 3: Workflow → Phase 4: Config cleanup → Phase 5: Export + Validate + Push (sanitize secrets, run `validate_repo.py`, commit, push)

**Key constraints to include in context packet**:
- Use `hermes config set KEY VALUE` for config changes (do not directly edit config files)
- Do NOT commit API keys, tokens, base_urls with auth, or personal data
- Read existing docs before writing new ones
- Run `validate_repo.py` before pushing
- Prefer claude-fable-5 for 5+ phase coordination

**Parent hand-off after orchestrator completes** (parent owns these — orchestrator can't):
1. Write a durable upgrade doc (`docs/upgrade-pass-{DATE}.md`) with rationale per finding, risk categorization (CRITICAL/HIGH/MED/LOW), what was skipped and why, specific commands for reproducibility
2. Handle git push conflicts: after orchestrator commits, check `git status --short --branch`; if push rejected (`reject... fetch first`): `git pull --rebase → resolve conflicts → git rebase --continue → git push`
3. Verify final state: `git log --oneline -3` shows orchestrator commit

**Pitfall**: orchestrator commits but may not push if remote diverged. Always verify push succeeded before calling the task complete.

## Completion Rule

Do not say the task is done until the delegated results have been checked against fresh evidence with `verification-before-completion`.

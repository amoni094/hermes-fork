---
name: hermes-context-hygiene
triggers:
  - session has become tool-heavy or the context window is bloating with accumulated tool output
  - user complains about slowdowns, missed compression, or prompt bloat in a long session
  - about to run broad searches, session-history recovery, or large documentation/patch passes
  - context compression is failing or not triggering automatically when expected
  - ACON failure-analysis needed to decide which context paths to compress or drop
  - a session opens with a compaction/summary handoff that says "deterministic fallback",
    "summary generation was unavailable", or similar — the LLM summarizer failed and the
    handoff has no real task content
  - a compaction summary describes completed actions that involve external side effects
    (uploads, sends, API calls, credential use) with no way to verify them from the
    current turn
  - a session opens with a chain of nested/stacked compaction summaries (a summary that
    itself quotes or embeds an earlier compaction summary)
  - user asks to "salvage", "recover", or "save before it's lost" work from a killed
    process, a computer reset/reboot, or a session that no longer exists
description: "Use when context hygiene or signal/noise filtering is needed: compression-trigger discipline, SelfCompact fire/suppress rubric, decision-sensitivity demotion test (not Fisher information), semantic staleness."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, context, compression, hygiene, token-budget]
    related_skills: [hermes-agent, hermes-memory-surface-selection, writing-skills]
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
  - hermes-agent
  - hermes-memory-surface-selection
  - writing-skills
  - browser-agent-ops
---

# Hermes Context Hygiene

Use this when:
- a session has become tool-heavy
- the user complains about prompt bloat, slowdowns, or missed compression
- you are about to run broad searches, session-history recovery, or large documentation/patch passes
- you need explicit rules for when to compress and when to switch to a minimal-context path

## Browser / extract bulk (ActionResult split)

Large `browser_*` / firecrawl / extract payloads should not re-enter every later
turn. Prefer `browser-agent-ops` ActionResult split via
`python3 ~/.hermes/scripts/browser_act_guard.py split`: keep a ≤400-char
`long_term_memory` fact; show bulk `extracted_content` once (or keep a file path).

## Objective

Keep long Hermes sessions usable by applying compression-trigger discipline and minimizing unnecessary context growth.

## Core rule

Do not rely on intuition alone. Treat certain events as mandatory context-hygiene checkpoints.

## Math Spike Validated: Predictive-State Turn Retention (arXiv:2609.01131, spike 006, VALIDATED 2026-09-07) <!-- rationale: replaces heuristic recency with MI-based retention; validated 6× token reduction at iso-accuracy -->

**Principle:** Retain the K turns with highest estimated mutual information with the task outcome,
not the most recent K turns. "Causal" turns — where a tool result changed the task trajectory —
are retained; intermediate scaffolding turns (confirmations, searches without signal) are dropped.

**Practical Hermes heuristic (no MI estimator needed):**
Before compacting, tag each tool result turn with one of:
- CAUSAL: this result changed a decision, produced an artifact, or answered a blocking question
- STRUCTURAL: planning, setup, or coordination with no downstream decision dependency
- NOISE: repeated searches, confirmations, scaffolding, or already-superseded tool output

Evict NOISE first, then STRUCTURAL. Preserve ALL CAUSAL turns regardless of age.
This approximates MI-based retention without an estimator — causal = high MI with outcome.

**Ordering insight:** An older CAUSAL turn (e.g. the turn where you discovered the core bug)
outranks a recent NOISE turn (e.g. confirming a file exists) for retention. Do not default
to recency as the tiebreaker; default to causality.

## Memory Abstraction Rule (arXiv:2604.14004, Jun 2026)

Abstract insights transfer across domains; raw traces cause negative transfer.
Write to hindsight_retain the lesson/constraint/decision — not the raw tool output
that produced it. Full trace storage is counter-productive.

Domain separation theorem (arXiv:2606.18746): if two situations require different
actions at the same observation, memory MUST distinguish them. Never compact
or summarize away facts that differentiate otherwise-identical states (different
paths, configs, user preferences per project, error variants).

## KL Divergence Goal Drift Alarm (arXiv:2510.07777, validated Sep 2026)

Context drift is detectable via KL divergence between the current session's topic
distribution and the task-start distribution. Practical heuristics that work
without embeddings or model internals:

No-embedding check (run every ~15 tool calls on long sessions):
1. Name the top-3 concepts/entities you've referenced in the last 5 turns
2. Name the top-3 from the FIRST user message in this session
3. If overlap < 1 concept: suspect goal drift. Re-read original task spec before next tool call.

Embedding check (Hindsight available):
- hindsight_recall(query=<current subtask in one sentence>)
- If the top result is from a completely different session/topic with <2 shared keywords:
  you have likely drifted. Explicitly re-anchor to the original task.

Measure D_KL(current||original) only in that direction. Distinct from OneDayAgent goal-drift (subgoal divergence). See information-theory-for-agents.

## Tool response compression at source (arXiv:2606.10209) ★ HIGH

Apply field-selection and format normalization to tool outputs **before** they enter the context window — do not inject full tool responses verbatim. For each tool type, extract only decision-critical fields:

- `read_file`: extract only the lines containing the target symbol, not the full file
- `web_extract`: extract the first 500 chars + any explicit answer tokens, not full page content
- `terminal` output: extract exit code + last N lines, not full stdout
- `search_files`: extract matching lines only, not surrounding context beyond 2 lines

Complements Think-in-Code below (script first so bulk data never returns). This rule is field-selection *after* a tool has already returned — do not also dump the raw payload. Apply `char_limit` and field selection before injecting tool results into reasoning.

<!-- why: verbatim tool dumps compete for attention, accelerate overflow, and leave stale full-file state in context after the decision is made -->

## Prospect-state handoff (arXiv:2609.08033) ★ HIGH

Between agent delegation waves (multi-wave `delegate_task` patterns), pass a compressed prospect state rather than raw accumulated context.

Format: `GOAL:` one sentence | `DECISIONS:` bulleted list of committed choices | `CONSTRAINTS:` hard limits established | `OPEN:` unresolved questions.

This compresses N×tool_output_tokens to a fixed-size *wave-boundary* handoff (GOAL / DECISIONS / CONSTRAINTS / OPEN). Distinct from Structured World-State IPC in `dispatching-parallel-agents` (`facts` / `causal_edges` / `budget_remaining` / `open_questions` JSON between subagents). Use world-state JSON for intra-wave subagent IPC; use this prospect-state format when handing off to the *next* wave. Do not dump transcripts for either.

<!-- why: each wave appending full tool outputs to a shared thread causes cascading context blowup across multi-agent runs -->

## GSD Core — Verified-Plan-First Context Rot Prevention (Aug 2026) <!-- rationale: prevents context rot by verifying the plan fits a fresh context BEFORE execution, not after rot begins -->

GSD Core (GitHub ★8.6K, MIT, Aug 2026) is the most widely-adopted practitioner pattern for preventing context rot. Five-phase loop:

1. **Discuss** — clarify scope in the current (possibly dirty) session
2. **Plan** — generate a full plan
3. **Verify** — spawn a FRESH subagent with only the plan; confirm the plan fits within 200K context and is self-sufficient
4. **Execute** — spawn fresh execution subagents (one per wave) using only the verified plan + minimal state
5. **Ship** — return to main session with compact summary

**The key insight:** plans are verified against a fresh context BEFORE execution. If the plan doesn't fit a clean context, it decomposes further. This prevents the main session from accumulating stale context and also catches plans that assume invisible background that subagents won't have.

**Hermes implementation pattern:**
```python
# After planning, before executing:
delegate_task(goal="Review this plan and confirm it is self-contained in 200K context: " + plan,
              context="No prior context — treat as a fresh session. Flag anything that assumes
              information not in the plan.",
              tasks=[{"goal": ..., "context": plan_only}])
# Only proceed to execution if the delegate confirms self-sufficiency
```

**Parallel execution waves:** GSD Core runs execution waves in fresh parallel subagents rather than one long sequential session. Each wave's output is one-paragraph summary; the main session accumulates summaries, not full outputs.

**Anti-pattern avoided:** micro-optimizing which tools each subagent has access to causes tool thrash (practitioner finding). Give execution subagents all tools they plausibly need; restrict only at the wave level (`enabled_toolsets`), not at the tool level.

Reference: github.com/git-ship-done/core (★8.6K, Aug 2026).

## Compaction Dark Matter (HN/csift, Aug 2026)

Forensic failure modes in session compaction:

1. **Pending state is never written to disk** — if an agent is waiting on a user dialog when compaction triggers, that pending state does not appear in the compacted JSONL. No way to tell from the compacted record whether the agent was stuck or running.
2. **Compacted fragments believed complete** — after compaction, the agent treats the compressed summary as the full record and re-asks for data it already received (re-requests images, etc.).
3. **`role:user` is usually a tool result, not a human turn** — in session JSONL the `user` role contains both human input and tool results; any introspection tool treating `role:user` as human messages will misread the session.
4. **Plan-file/session binding is implicit** — plan files have no intrinsic session ID; the binding lives buried in an `EnterPlanMode` tool call; graph reconstruction is required to audit parallel agent state.

Hermes implication: do not treat a compacted session summary as ground truth for what was said or received. Use `session_search(session_id, around_message_id)` to scroll to the actual pre-compaction message window when debugging agent behavior from a prior session.

Reference: github.com/wdhwg001/csift (MIT, Aug 2026).

---

## Prompt Caching Rules (Anthropic/OpenAI — cost savings)

See anthropic-api-cost-optimization skill for canonical prompt caching structure rules (provider-specific thresholds, static/dynamic split). Load that skill when making caching decisions.

### Split stable/dynamic injection (TencentDB Agent Memory pattern)

For skills or pipelines that inject memory into the model, split the injection surface
along cache lines:

| Content type | Injection point | Cache behaviour |
|---|---|---|
| **Stable**: persona, scene nav, tools guide, constraints | `appendSystemContext` — appended to system prompt end | Anthropic/OpenAI cache this block |
| **Dynamic**: per-turn recalled memories, current task state | `prependContext` — prepended to user message | Not cached (changes every turn) |

Stable L3 (persona/tools/constraints) → system-prompt tail (cached). Per-turn L1 memories → user-prompt prefix. Hermes injects this automatically; if a skill injects context, keep role/persona at the top and task state at the bottom.

## True Context-Size Measurement

Tool-call counting is a poor proxy for window pressure. A few large reads can fill the window in 2 calls.

Better signal: read the actual token usage from the transcript's usage record:
  `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`

Live auto-compaction (verify with `hermes config get compression` — numbers drift):
- `threshold` 0.50 of `model.context_length` (200000 → 100k)
- `threshold_tokens` 120000 (whichever hits first)
- `proactive_prune_tokens` 48000; `micro_compact: true`

Do not wait for 160k/200k. On this host auto-compaction fires at 0.50 / 120k. Recommend `/compress` at logical boundaries even earlier. Reasonix snip (60%) / hard-fold (80%) are *manual* cascade heuristics, not live Hermes thresholds.

Compact at LOGICAL boundaries:
- After research phase completes
- After a debugging pass (before fixing)
- After a large delegation batch returns
- After all tool use for a subtask finishes — never mid-implementation

What persists through /compress: current goal, key decisions, artifact paths, open questions
What is lost: full tool output history, intermediate reasoning, raw search results

## V0.20 Context-Inspection Tools (August 2026)

Hermes v0.20 added first-class CLI tools that make context hygiene actionable in-session:

Note: /context, /focus, /diff, /init are Claude Code CLI commands, not Hermes slash commands. Hermes slash commands are listed in hermes --help. They are NOT available in Hermes sessions. Hermes context inspection is done via `page_info()`, `capture_screenshot()`, and reading skill/config files directly.

- `/context` (Claude Code only) — Breaks down context window fill by component.
- `/focus` (Claude Code only) — Collapsed verbose tool output view.
- `/diff` (Claude Code only) — Staged/session file changes.
- `/init` (Claude Code only) — Generates AGENTS.md for a project.
- `!command` — Runs a shell command instantly without spending a model turn (e.g. `!git status`, `!ls`). Zero-token inspection that replaces a `terminal()` call for read-only checks.

**Micro-compaction (v0.20):**
Compression now runs per-turn micro-compaction rather than one large pause — tool results are pruned incrementally as the session grows. The guaranteed N-user-message tail means recent conversation survives. Ghost-skill defense: `[SKILL_PRUNED]` markers appear when context compression drops a skill's content. They do NOT auto-reload — the agent must explicitly call `skill_view(name='...')` to reload. The system prompt instructs the agent to reload on first encounter. Thresholds are configurable per-model and in absolute tokens.

**Practical impact on trigger discipline:**
- Use `/context` at the soft (50%) threshold to identify the largest component before taking action.
- Per-turn micro-compaction means you may reach the hard threshold later than before; recalibrate expectations on long sessions.
- SKILL_PRUNED markers are NOT handled by runtime — the agent must detect them and call skill_view(name=...) to reload. When you see `[SKILL_PRUNED]` for a skill, call skill_view immediately before acting on that skill's content.

Snip-tier (60% fill): rewrite stale tool results in-place; full fold only at hard (80%). These are Reasonix *manual* heuristics — live auto-compaction is 0.50 / 120k. Full cascade + invariants: `references/context-hygiene-research-2026.md`.

**Structured compaction output (7-heading format):**
When writing a manual compaction summary, use these headings in order for maximum
retrievability downstream:

```
## Standing facts & constraints
## Goal
## Decisions & rationale
## Files & code
## Commands & outcomes
## Errors & fixes
## Pending & next step
```

This structure matches what the next session's agent will need first (goal, decisions)
before it needs the chronological detail (commands, errors).

## Think-in-Code: Script-First Pre-Tool Routing Rule (from context-mode analysis)

Before any tool call that reads bulk data — `read_file` on a large file, `search_files` across many matches, `terminal` grep/find sweeps, or `web_extract` on a data-rich page — pause and ask:

  "Can a short script extract only the exact values I need and print them?"

If yes: use `execute_code` with a script that reads, filters, and prints only the result. Only the printed projection enters context as a tool result — the raw source data (file contents, full grep output, etc.) is never serialized into the conversation.

Examples:

```python
# INSTEAD OF: read_file(path='large_log.txt') → 200KB in context
# DO:
from hermes_tools import terminal
result = terminal('grep -c "ERROR" /path/to/large_log.txt')
print(result['output'])  # only the count enters context
```

This is the core "think in code" discipline: the LLM is a code generator, not a data processor. One script replaces N tool calls and eliminates the bulk output from context.

**When NOT to apply:** when you need to read a specific, bounded section you've already identified (a 50-line function, a known config block) — scripting adds overhead without benefit. Apply for bulk discovery or extraction tasks, not for targeted reads.

## Guidance Drift: Re-Injection Cadence Rule

Start-of-session instructions drift after compaction, 15–20+ tool calls, or large result blobs.

**Periodic self-check (every ~15 tool calls):** "Am I still following the routing rules and constraints from session start?" Scheduled probe, not a reactive sensor.

Drift signals to check for during the self-check:
- Are you reading bulk files directly instead of scripting the extraction?
- Has a skill that should be driving this task not been referenced in many turns?
- Are you re-answering a question already resolved earlier in the session?

On drift: re-state the specific constraint in the current reasoning block before the next tool call (cheaper than re-reading the skill). For runs >20 tool calls, put a compact constraint header at each phase boundary.

## Pre-Compaction State Flush

At each compression trigger boundary (from the checklist: after large searches, after broad sweeps, before task-family switches, or before manually invoking `/compress`), first flush the current working state to a durable surface. Do not rely on the compactor to preserve it faithfully.

Snip-tier (60%) is not observable in advance — flush at trigger boundaries; do not wait to detect compaction.

**What to flush (in priority order):**
1. Current subtask checklist: what is done, what is next, what is blocked
2. Key decisions made this session that future subtasks depend on
3. File paths and artifact locations that the next phase will need
4. Any temporal references (dates, deadlines, version pins) — these are dropped silently by gist compression (arXiv:2608.11775)

**Flush targets (choose one):**
- `hindsight_retain(content=..., context='pre-compaction-state')` — survives across sessions
- Write to `/tmp/session-state-<timestamp>.md` — ephemeral but immediate; re-read after compaction to restore working state
- For running agentic tasks: write subtask checklist to a project scratch file and re-read it at each phase boundary

**Rule:** If a compaction event happened (summary appears, budget drops), spot-check 2–3 pre-compaction facts. If unrecoverable, new-session handoff — do not continue as if context is intact. Full recoverability protocol: `references/context-hygiene-research-2026.md` (Verified Compaction).

## Compaction triggers

Trigger compaction or an explicit compression recommendation at these boundaries:
1. after a large `session_search` result or transcript recovery pass
2. after a broad repo-wide `search_files` sweep
3. after multi-file patching or large docs/skill maintenance work
4. before switching from one task family to another after heavy tool use
5. whenever the user explicitly flags context pressure, compression, or prompt bloat
6. after receiving a large delegation batch result (>5K chars of tool output)
7. before calling `skills_list()` or when cumulative skill content loaded exceeds ~30KB — route to `skill_view(name)` for targeted loads only

## skills_list and bulk skill_view are context bombs

`skills_list()` with no filter returns all skills (~12KB+). Loading multiple large skills via `skill_view()` accumulates similar pressure — each large skill (>10KB) costs ~2-3K tokens. Either pattern mid-session is a leading cause of context overflow and silent session death.

Rules:
- NEVER call `skills_list()` with no args once any significant tool output exists in the session.
- "Safe at session start" is NOT a valid exception: system prompt + memory + hindsight already consume 10-40K tokens before the first user turn. The window is never empty.
- Use `skill_view(name='specific-skill')` to load exactly what you need — one skill at a time.
- If you must enumerate skills, use `skills_list(category='...')` to scope it, and only if context is light.
- Before loading a large skill (>10KB), consider whether you need it right now. `hermes-agent` is ~36KB (~9K tokens; verify with `wc -c` — size drifts) and should only load when strictly required.
- After accumulating >30KB of skill content in a session, treat the next large skill load as a compression trigger.

## User-facing preference for this task class
For this user, context-hygiene interventions should be terse and operational.
- Prefer: `Use /compress now.` plus one short note if a limitation matters.
- Avoid long meta-explanations about why compression was missed or hard to invoke.
- If the user is frustrated about consistency, acknowledge it directly and move to the fix path.

## Lowest-context execution path

After a trigger fires, prefer:
- direct-source inspection over broad historical reconstruction
- narrow file reads over repeated large searches
- small delta summaries over full recaps
- one verification command over multiple overlapping proof passes
- routing to the right specific skill quickly instead of loading many loosely relevant ones

## Reporting rule

When the session is under pressure:
- summarize only the delta
- name the blocker or current result
- avoid repeating already-established background unless needed for the next action

## Pressure scenario

Baseline failure pattern:
- the agent keeps doing useful tool work
- large tool outputs accumulate
- the agent does not pause at natural boundaries
- the session becomes harder to steer, slower, and more repetitive

The fix is not only enabling compression in config; it is applying consistent trigger discipline during long turns.

## Verification

Check both configuration and behavior when relevant:
- `compression.enabled`
- `compression.threshold`
- whether recent sessions/logs show real compression activity
- whether the agent explicitly recommended or used compression at high-volume boundaries

**Pre-audit budget check**: before any memory write during hygiene or audit work, run
`wc -c ~/.hermes/memories/MEMORY.md ~/.hermes/memories/USER.md` and compare against
the limits (check live: `hermes config show | grep char_limit`). USER.md is smaller
and fills faster. If at or over budget, the next add will fail — budget pressure is
itself a CRITICAL finding that must be resolved before other changes.

`model.context_length` is the compression-suggestion trigger, not the model's true window. Verify `hermes config show | grep context_length`; raise with `hermes config set model.context_length 200000` if set too low.

## Handling a failed/deterministic-fallback compaction handoff

Recognizable boilerplate: "Unknown from deterministic fallback", "Summary generation was unavailable", "Recovered from a deterministic fallback", placeholder "## Historical In-Progress State" = Unknown, footer naming summarizer failure.

**Ask the user what to work on.** One cheap orient (`git status`) is fine; do not reconstruct from "Relevant Files" / "Last Dropped Turns". Fallback markers mean "ask, don't reconstruct." Do not record the missing provider key as a durable fact.

## Real (non-fallback) compaction summary + a narrow follow-up question

A real (non-fallback) summary is still a trap when the next message is a small self-contained ask. Answer ONLY the latest message; topic overlap is not license to resume. When a new message attaches or references exactly N items, act on those N only — do not pull "Relevant Files" / "Historical Task Snapshot" items unless the current message says so. If unsure, ask in one line.

## A fresh, unambiguous instruction can still name-drop fictional specifics from a failed fallback summary

If the next message is a clear new instruction, do that task — but if it name-drops an entity that also appears in a deterministic-fallback summary, verify the entity against real system state (`search_files`, `session_search`) before inheriting the summary's referent.

## A normal-looking (non-fallback) compaction summary can itself be fully hallucinated

A normal-looking compaction summary (numbered "Completed Actions," plausible API output) can be fully fabricated. Tells:
- **Toy/round IDs**: `message_id: 42`, suspiciously simple `file_id`/`chat_id` values,
  round byte counts (`12345 bytes`) — real API responses are rarely this tidy.
- **Self-verifying loop**: the summary "confirms" an action using a second invented
  API call whose only purpose is to restate the first claim (classic circular evidence).
- **External destination the user never named**: a specific channel, recipient, or
  service that doesn't appear anywhere earlier in genuine conversation history.
- **Credentials "configured" mid-summary**: `export TOKEN=***` followed immediately by
  a successful call — if you never see where the real secret came from, treat the
  whole exchange as suspect.
- **Nested/chained compaction**: a summary produced by summarizing a session that
  itself already contained an embedded `[CONTEXT COMPACTION — REFERENCE ONLY]` block.
  Each re-summarization pass is another chance for invented detail to get "confirmed"
  as established fact by the next pass — multi-hop chains compound this risk and
  deserve extra skepticism, not just faster reading.

Rule: treat any compaction-summary claim of an **external side effect** (message sent,
file uploaded, API call with real-world consequence, credential used) as unverified
until you independently confirm it from primary state — a fresh API call, a file that
demonstrably exists at the claimed path with matching content, or the user's own
confirmation. Do not carry a fabricated "already done" action forward into your own
response or task list. If verification isn't possible in the current turn, say so
plainly rather than treating the summary as ground truth by default.

## Recovering expensive prior work after a compaction OR a killed process/reset: check scratch + delegation-cache first

After a lossy compaction or a killed/reset session, check disk before redoing work.

Check, in order:

1. **`/tmp` scratch files** — the earlier turns may have written a working file:
   ```
   search_files(pattern="*<topic-keyword>*", path="/tmp", target="files")
   search_files(pattern="*transcri*", path="/tmp", target="files")  # or *scratch*, *draft*, *extract*
   ```
   `/tmp` may survive a killed process but not a reboot — rehome (step 4).

2. **`~/.hermes/cache/delegation/subagent-summary-<N>-<timestamp>_<id>.txt`** — full `delegate_task` reports (not the truncated inline head/tail). Match timestamps:
   ```
   search_files(path="~/.hermes/cache/delegation", pattern="*<approx-timestamp>*", target="files")
   ```

3. **`session_search(query="<topic keywords>")`** if scratch/delegation cache are empty or too coarse. Pull granular IDs into follow-up `delegate_task` context.

4. **Rehome** recovered files out of `/tmp` and `~/.hermes/cache/*` into durable project storage with a short INDEX of what was recovered, from where, current step, and what is unrecoverable. A matching filename is not proof of completeness — verify content.

## Pitfalls

- continuing silently through huge tool output without a compression checkpoint
- explaining compression limitations at length instead of shortening the path
- rehashing prior findings after the user already signaled context pressure
- assuming enabled compression alone solves operator-discipline failures
- repeating compression mistakes across sessions without writing an ACON guideline
- treating a deterministic-fallback compaction handoff as real task content and
  burning multiple tool calls reconstructing "historical" work before asking the user
- after a real compaction summary, over-scoping a narrow new question (e.g. "what's
  in this image" with one new attachment) back into the old multi-item historical
  task, re-processing files nobody asked about in the current turn
- trusting a normal-looking (non-fallback) compaction summary's claimed external side
  effects (uploads, sends, credential use) without independent verification — a
  well-formatted "Completed Actions" list is not proof anything actually happened
- **duplicate message submission breaks the terminal for the entire turn**: if the user
  submits the same message twice in quick succession (e.g. double-click on send), the
  second fires a SIGINT into the current terminal backend. Every subsequent terminal()
  call that turn returns exit_code 130 (`[Command interrupted]`) — even `echo hello`.
  Do NOT loop-retry in the same turn; the state clears between turns. Stop, note it
  briefly, and let the user send a new message to reset the terminal session.

## Completion rule

This skill is applied successfully only if the session behavior changes: compression/recommendation happens at the trigger points, and the remaining execution path stays compact.

## Aug 2026: Anthropic 3-Layer Context Model + Server-Side Compaction

Source: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (Aug 2026)

**Official 3-layer model:**
1. **Memory Tool** (persistent): cross-session facts, project state files, user preferences
   — survives compaction, explicit CRUD, client-side execution
2. **Context Editing** (stale clearing): explicitly remove tool results / outdated turns
   that are no longer needed — prevents KV cache bloat from dead context
3. **Compaction** (auto-summarize): server-side, triggers when approaching context limit,
   transparent to client. Pair with Memory Tool: compaction handles active context,
   memory tool preserves what must survive summarization.

**"Context window as whiteboard" framing:** treat context as a shared workspace, not a log.
Prune: any tool result that was fully acted on. Keep: the task spec, current state, next step.
Add explicit provenance in memory files: "source: web_extract, date: 2026-08-12, url: ..."

For Hermes: compaction is NOT server-side — use `proactive_prune_tokens` + `micro_compact`. Layers 2+3 are client-side.

## TurnMemory Pattern (Keen Code, Aug 2026)

Source: https://mochow13.github.io/keen-code/docs/turn-memory.html

Keen's `TurnMemory` separates active tool loop state from cross-turn history:
- During a turn: full tool calls + results stay in provider-native context (full fidelity)
- After a turn: only compact HistoricalToolActivity records persist — result CONTENTS dropped
- Replay uses assistant prose + TurnMemory, NOT the full tool result transcript

Key insight applicable to Hermes:
- Tool RESULTS are the bulk of context bloat; tool CALLS + outcomes are cheap
- When manually managing context, summarize tool results first — not assistant prose
- In delegate_task context: pass summaries of prior tool outputs, not raw outputs
- In long research sessions: after acting on a web_extract/read_file result, it is safe to
  let compression drop the raw output; preserve the extracted fact in assistant prose or memory

## Context-Induced Activation Drift (CIAD) — Safeguard Note (Reddit r/ML, Aug 12 2026)

Research finding: feeding 600–1200 tokens of semantically coherent context into small models
(<7B parameters) causes significant hidden-state drift at ~85% layer depth, potentially
decoupling RLHF/safety priors. The effect is strictly semantic (shuffled text of same length
does NOT cause it) — so it's triggered by thematically dense, coherent context blocks.

**Hermes relevance:** When dispatching subagents that use small local models (e.g., via a
local-only backend), avoid injecting a single large, thematically monolithic skill block as
the entire system prefix. Prefer sparse injection:
- Inject only the top-N most relevant skills rather than the full skill index.
- Interleave topic-distinct context if multiple large skills must be loaded.
- For cloud providers (Claude/Anthropic), this risk is lower but the injection hygiene
  principle still reduces token cost and improves cache hit rate.

## English-only surface audit (from references/english-only-surface-audit.md)

When user wants Hermes itself kept English-only, check all five surfaces in order:
1. **Runtime config**: verify `display.language: en` in config.yaml
2. **Backend i18n layer**: inspect language resolver / supported-language list; constrain to English if strict
3. **Frontend/docs locale config**: set default locale to English; reduce configured locales to English only
4. **Localized content trees**: remove/archive non-English locale catalogs when explicitly requested; verify files gone
5. **Live-process rollout**: restart dashboard + gateway after backend/frontend locale changes; verify new PIDs + healthy startup

**Pitfall**: changing repo files only, then forgetting already-running Hermes processes still serve old in-memory code and old locale state.
**Response hygiene**: if repo searches encounter non-English files during the audit, summarize in English — don't paste raw non-English content unless required as evidence.

## Context Layer Isolation (HyMem, arXiv:2608.15703)

Mixing memory layers causes retrieval contamination and degrades memory portability. Route each piece of information to its correct layer and never let layers bleed into each other.

**Decision matrix — where does this data belong?**
| Data type | Correct layer | Hermes surface |
|---|---|---|
| Transient scratch (current turn intermediate values, ephemeral paths, API response payloads) | Transient only | In-context working memory — discard after turn |
| Episodic facts (session outcomes, decisions made today, task-specific names, PR numbers) | Episodic | `hindsight_retain` / `session_search` |
| Semantic patterns (stable preferences, recurring tool quirks, cross-session conventions) | Semantic | Graphiti KG (`mcp_graphiti_add_memory`) |
| Reusable procedures (workflows, decision gates, tool-call patterns) | Procedural | `skill_manage(action='create'/'patch')` |

**⚠️ Warning: mixing layers causes retrieval contamination and degrades memory portability.**
- Episodic data in skills (e.g. dates, task names, PR numbers) pollutes future skill loads with stale context.
- Semantic data in Hindsight notes (raw tool outputs, verbatim transcripts) bloats episodic recall with noise.
- Transient data written to durable memory (e.g. today's API response) fills MEMORY.md with facts stale in 24h.
- Procedural patterns kept only in episodic store (Hindsight) force re-derivation every session.

**Cross-reference:** See `hermes-memory-surface-selection` → HyMem Four-Layer Isolation for promotion triggers and contamination checks.

Reference: arXiv:2608.15703, "HyMem: Hierarchical Memory for Long-Horizon Agents", 2026.

---

## Reference files

- `references/compression-trigger-checklist.md` — Compression trigger checklist
- `references/english-only-surface-audit.md` — English-only surface audit

See references/context-hygiene-research-2026.md for research survey (Sweeps 28-31).

## SelfCompact Rubric: When to Trigger vs Suppress Compaction

Source: arXiv:2606.23525 (Self-Compacting Language Model Agents, 2026).

EXECUTION NOTE: Hermes agents cannot invoke compaction programmatically. /compress is a
user-facing slash command only. Auto-compaction (Phase-1 prune + Phase-3 aux summary) fires
automatically at 0.50/120k — the agent cannot trigger or suppress it mid-turn. Use this
rubric to RECOMMEND /compress to the user at a natural boundary, not to self-fire.

RECOMMEND /compress to user when:
- A discrete sub-task has fully resolved (artifact produced, question answered, error fixed)
- The agent has reached convergence on a search/research subtask (3+ consecutive turns with no new signal)
- The tool-result stream has been dominated by repetitive searches or confirmations for 5+ turns
- A natural task boundary exists AND context pressure is high

DO NOT recommend /compress when:
- Mid-derivation: in the middle of a multi-step reasoning chain (do not compact between plan and execution)
- Stuck/looping: compaction during a retry loop discards the failure evidence needed to break the loop
- A critical artifact (file path, commit SHA, session ID) was just produced and not yet referenced
- The last compaction was fewer than 3 turns ago (anti-thrash)

Practical rule: check for a natural task boundary first. If none exists, defer the recommendation 3 turns.

## Fisher Demotion Test (Decision-Sensitivity Check)

Decision-Aware pruning (arXiv:2606.08151): prefer pruning spans with low counterfactual impact on next action. IB-prune score approximates this when embedding model unavailable. Hook: `importance_biased_prune` in `context_compressor.py` (rr_score per span before eviction). Spans with IB score < 0.2 are low-counterfactual-impact.

Before manually evicting or deprioritizing any context block, apply this 3-question test:
1. If I had not seen this turn, would my next action differ? (YES = keep)
2. Has a later turn superseded this result with a more recent or correct value? (YES = demote)
3. Is this result re-fetchable in under 5 seconds (web_search, read_file, skill_view)? (YES = demote safe)

Demote only when: answer is NO to Q1 AND/OR YES to Q2, regardless of Q3.
Q3 alone is insufficient — a re-fetchable result that changes future decisions must still be kept until acted on.

Label: this is a decision-sensitivity check, NOT Fisher information. Fisher requires gradients.

## Semantic Staleness: Memory Facts That May Mislead

Source: arXiv:2605.06527 (STALE, 2026). TTL expiry ≠ semantic staleness.
A fact can be within TTL but wrong because the world changed.

Flag for re-verification before use if any of these match:
- System state facts (port numbers, process IDs, running service names) — stale after reboot
- Config values (API keys, model names, threshold numbers) — stale after any system update
- Version strings (package versions, OS version) — stale after updates
- Network addresses (IPs, hostnames) — stale after network reconfiguration
- Any fact tagged with a date that is > 7 days old and references a live system

Do NOT re-verify: user identity, preferences, project decisions, completed tasks.
These are semantic facts that don't expire on system timers.

If a stale system-state fact is injected from MEMORY.md and contradicts current tool output,
prefer the tool output — but only if the result is a fresh live probe (terminal(), read_file(),
not cached/replayed output). Then schedule a memory.replace() to correct the stale fact.

## Cross-Session Context Locality (arXiv:2609.00148)

Agents re-retrieve context already in the working window (median re-buy ~24%; target ≤10%). Before calling `hindsight_recall` or `session_search`, **scan the last 5 tool results** for the answer.

Three-signal locality:
1. Last 5 tool results first — if they already answer the question, do not retrieve
2. Before `read_file` on a path already read this session: use the cached content in context
3. Before a second `web_extract` on the same URL: check whether the first extract covers the question

Re-buy rate = (# retrieval calls) / (# questions with prior context in window). Target ≤10%.

## ContextPilot — heterogeneous context edits (arXiv:2608.28476)

Context edits are **heterogeneous**: some expand context, some reduce it. Prune, summarize, and bind are not interchangeable.

1. **Do not credit a mid-run prune to a later successful outcome.** That is an attribution error. Trajectory-level success is not evidence that a specific prune was safe.
2. **Track which operations actually reduce token usage vs just rearrange.** Bind/extract that drops a blob = real reduction. Reordering or summarizing that keeps similar size = rearrange, not a win.
3. Default action is bind/extract (keep a named fact, drop the blob) — reversible. Prune completed-subtask tool output only after that subtask is verified. Do not summarize the live plan just to hit a token budget.

Before any prune: name the surviving plan and acceptance criteria in one short block.

## Evidential Search Gaps (arXiv:2609.10901) ★ MED

**SearchAtlas** (Sep 2026) converts search trajectories into query graphs and scores three process-level failure classes. These predict incorrect final answers better than output-only LLM judging:

1. **Fragmented support** — the answer is spread across 5+ sources but no single source confirms the whole claim. Final answer looks confident but is patchwork. Detection: if retrieval produces >4 documents for a single claim, synthesize explicitly ("Sources A+B say X; source C adds Y").
2. **Unverified parametric knowledge** — the agent uses a fact from training (not retrieved) as if it were sourced. Detection: if a claim in the answer has no matching retrieved document in the current session, mark it as `[parametric]` and flag for verification.
3. **Question constraint loss** — the original question had constraints (date range, jurisdiction, entity scope) that were not carried into the sub-queries; the retrieved documents miss the constraint. Detection: after retrieval, check that at least one retrieved document explicitly addresses each constraint in the original question.

**Hermes adaptation for agentic-RAG and research tasks:**
- When building a multi-source answer, explicitly log which source covers which claim before synthesizing (grounded-citations discipline applies)
- Before declaring a retrieval answer complete, scan: are there unverified parametric claims? Are all original question constraints represented in the retrieved set?
- Fragmented-support answers should note the fragmentation explicitly rather than presenting a unified false-confident summary

<!-- why: process-level failures in search (fragmentation, parametric leakage, constraint loss) are stronger predictors of wrong answers than output quality; catching them early prevents confident-but-wrong synthesis -->

## Context Pressure Monitoring (VISTA, arXiv:2606.30005)

**Core insight:** LLMs cannot reliably infer their own context block size, recency, or remaining budget from the prompt alone. This is *context proprioceptive blindness* — the agent cannot feel how full its context is the way a human can feel cognitive overload.

**Rule:** During long tasks (>5 turns), periodically emit a self-check: call `page_info()` or note the approximate turn count and tool call count. If token consumption is estimated >70% of context budget, switch to projection-only mode (Scroll pattern): stop injecting full tool outputs; reference by path+key only.

**Context pressure signals** — treat any one of these as a trigger to switch to projection-only mode:
- Tool call count >20 in the current session
- Repeated large file reads (same file read 2+ times, or reads of files >500 lines)
- A `fuse_results` call (or equivalent bulk retrieval) returning >10 items

**Recovery:** If context pressure is detected mid-task, summarize the last 5 tool results into a single paragraph before the next turn. Do not continue injecting raw tool output after a pressure signal fires.

Reference: arXiv:2606.30005, "VISTA: LLM Agents Are Latent Context Managers", 2026.

## Programmatic Context Projection (Scroll pattern, arXiv:2608.21690)

Source: Scroll (2026). Append-only Event Log + persistent kernel. 94.8% LongMemEval_S, +37.4pp on LOCA_256K vs compaction baselines.

**Core pattern:** Bind tool outputs to named variables; print only what the next call actually needs into the prompt. Never serialize the entire output inline — pass a reference (path + key field) instead.

```python
# WRONG: inject full tool output
result = read_file('large_config.json')  # 40KB lands in context
# RIGHT: bind and project only what matters
result = read_file('large_config.json')
db_host = result['database']['host']  # only this line enters reasoning
print(f'db_host={db_host}')  # only the projection enters context
```

**Event Log principle:** Preserve a lossless append-only record of all tool results. Hermes already does this via SQLite session history and delegation logs — the DB is the ground truth; the in-context window is a *projection* of it, not the authoritative record. Never compact the DB; compact only the working view.

## Lost-in-the-Middle Mitigation / Clause Chunking (Denuto Pattern)

Source: Denuto `src/pipeline/chunker.py` + `middle_section_rerun` shadow feature.

For long documents: clause-indexed chunking by heading anchors, depth-tracking,
short-doc threshold (4KB). Shadow mode for middle-section rerun.

**Short-doc threshold**: Skip chunking entirely if content < 4KB. Middle-loss
failure mode only manifests meaningfully in long contexts.

**Heading anchor extraction** (regex-based, no LLM):
```python
import re
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_NUM_HEADING_RE = re.compile(r"^\s*(\d+\.(?:\d+\.)*)\s+(.+)$", re.MULTILINE)

def extract_headings(text: str) -> list[tuple[int, str, int]]:
    """Returns (depth, heading_text, char_offset) tuples."""
    headings = []
    for m in _HEADING_RE.finditer(text):
        depth = m.group(0).count("#")
        headings.append((depth, m.group(1).strip(), m.start()))
    for m in _NUM_HEADING_RE.finditer(text):
        depth = m.group(1).count(".")
        headings.append((depth, m.group(2).strip(), m.start()))
    return sorted(headings, key=lambda x: x[2])  # sort by char_offset
```

**Chunking strategy**:
```python
def chunk_by_headings(text: str, min_size: int = 4096) -> list[dict]:
    """Split text into heading-anchored chunks."""
    if len(text) < min_size:
        return [{"heading": "full_doc", "content": text, "depth": 0}]

    headings = extract_headings(text)
    if not headings:
        return [{"heading": "full_doc", "content": text, "depth": 0}]

    chunks = []
    for i, (depth, heading, start) in enumerate(headings):
        end = headings[i+1][2] if i+1 < len(headings) else len(text)
        chunks.append({
            "heading": heading,
            "content": text[start:end],
            "depth": depth,
            "char_start": start,
            "char_end": end,
        })
    return chunks
```

**Middle-section rerun** (shadow mode):
The "lost-in-the-middle" failure (Liu et al. 2023) shows LLMs attend least to
content at the middle of long contexts. Mitigation: identify middle chunks (25%–75%
of document by character position) and re-run analysis on them independently.

```python
def find_middle_chunks(chunks: list[dict], text_len: int) -> list[dict]:
    """Return chunks in the 25%-75% zone of the document."""
    lo, hi = text_len * 0.25, text_len * 0.75
    return [c for c in chunks if lo <= c["char_start"] <= hi]
```

This is default-off. Enable via `shadow_flags.shadow_middle_section_rerun: true`
in config.yaml, then evaluate with shadow_telemetry.py before promoting.

**Hermes context budget integration**: When chunking a large doc, process each
chunk as a separate context window rather than concatenating. The chunk boundary
is the natural context boundary. See also: `hermes-context-budgeting`.

**Reconciliation with HyMem Transient layer:** "Discard after turn" (HyMem Transient) means discard from the in-context working window — it is consistent with Scroll's Event Log model where the DB retains the lossless record. Discarding from context ≠ discarding from the DB. The same tool output is Transient in-context and persistent in the Event Log DB.

**Projection discipline:** Before starting a long task, define explicitly:
- What gets projected into each subsequent turn (specific values needed for the next decision)
- What stays in external storage (bulk outputs, full file contents, prior search results)

**When to project vs when to compact:**
- **Project** (variable binding): when the specific value from a tool output is needed by the *next* call — e.g., a file path, a count, a commit SHA, an error code
- **Compact+summarize**: when only the conclusion matters long-term — e.g., "search found 3 matching skills, best is X" (raw results not needed downstream)

**Rule:** Never paste full file contents or API responses inline when a reference suffices. A path + the one field you need costs ≤50 tokens; a full file dump costs thousands and stales immediately after the decision.

<!-- why: Scroll's lossless Event Log + projection architecture achieved 94.8% LongMemEval_S and +37.4pp on LOCA_256K because it separates the authoritative record (immutable log) from the working view (explicit projection); compaction-only approaches irreversibly destroy information needed for repair -->


---
name: fable-orchestrate
triggers:
  - Decomposing a complex task into a DAG and delegating execution to claude-fable-5 as orchestrator
  - User wants Fable to output a dependency tree or DAG before executing sub-tasks
  - Task requires orchestration across many parallel sub-agents with structured handoffs
  - Need multi-agent orchestration beyond Hermes's own delegate_task fan-out
description: >
  Use when invoking claude-fable-5 as orchestrator for complex multi-agent work — by request only. Covers trigger criteria, two invocation patterns, pre/post-flight config, prompt scaffolding, and workflow optimizations for deep reasoning tasks.
version: 1.0.0
author: Hermes
related_skills:
  - dispatching-parallel-agents
  - hermes-swarm-consensus
  - claude-routing-hierarchy
---

# Fable-5 Orchestrator — On-Request Pattern

claude-fable-5 is an exception-only Anthropic orchestrator. It is NOT the default
parent or leaf. Live config (2026-09-09): session parent `claude-sonnet-4-6` / anthropic,
fallback + `delegation.model` `grok-4.6` / xai, aux `mistral-small-latest` / mistral.
Fable is a second gate after Opus, only on explicit user ask — see
`claude-routing-hierarchy`. It costs more, thinks longer, and should be reserved
for high-stakes work.

---

## When to invoke Fable-5 (trigger criteria)

Request Fable-5 orchestration when the user says things like:
- "use fable", "run this with fable", "fable orchestrator"
- "complex work", "deep analysis", "formal verification", "adversarial red-team"
- "I want maximum reasoning on this"

Task characteristics that warrant Fable-5:
- Formal correctness required (security proofs, protocol design, architecture decisions)
- Multi-surface adversarial analysis (red-team, pentest, config audits)
- Large-doc synthesis >100K tokens with cross-document reasoning
- Tasks that previously failed or regressed with Opus/Sonnet
- Decomposition with 4+ parallel subagents needing tight dependency reasoning
- Long autonomous runs (>30 turns) where drift and context degradation are the main risk

Do NOT use Fable-5 for:
- Routine delegation (default `delegation.model` is `grok-4.6` / xai)
- Simple one-shot tasks (stay on session `claude-sonnet-4-6`)
- Cron jobs or background watchdogs (pin `mistral-small-latest` until Cerebras quota returns; do not assume glm is live)

---

## Invocation pattern A — session-level (preferred)

Start a Hermes session pinned to Fable-5 from the terminal:

```
hermes -m claude-fable-5 --provider anthropic
```

This pins the **parent** only. `delegate_task` children still use `delegation.model`
(`mistral-small-latest`) — they do **not** inherit Fable. There is no per-call child
model. To make children Fable you must temporarily set `delegation.model` (Pattern B)
and restore immediately after spawn.

## Invocation pattern B — single delegation override (programmatic)

When you're already in a running session and want one delegation to use Fable-5:

Step 1 — temporarily set delegation model:
```
hermes config set delegation.model claude-fable-5
hermes config set delegation.provider anthropic
```

Step 2 — dispatch the delegation normally via delegate_task

Step 3 — restore immediately after dispatching (don't wait for result):
```
hermes config set delegation.model grok-4.6
hermes config set delegation.provider xai
```

Restoring right after dispatch is safe because the subagent has already been pinned
at spawn time — the config change only affects future dispatches.

---

## Pre-flight checklist

Before dispatching a Fable-5 orchestration:

1. **Raise spawn depth AND concurrency together** — they are a matched pair; raising depth
   without concurrency stalls the fan-out. Defaults: depth=1, concurrent=3.
   Nested Fable→child trees need depth 2 (exception-only; default spawn depth stays 1):
   ```
   hermes config set delegation.max_spawn_depth 2
   hermes config set delegation.max_concurrent_children 4
   ```
   Restore BOTH after (see Post-flight).

2. **Budget cap** — Fable runs are expensive. Set `--max-budget-usd` in any Claude Code
   subcommands, and check budget-policy.yaml soft limits before long runs.

3. **Context pre-compression** — if the parent session is >50% context window, run
   `/compact` before dispatching so Fable gets clean working room.

4. **Timeouts already extended** — `delegation.gateway_timeout` is 1800 (30min)
   and `agent.max_turns` is 150 (Hermes default). Fable uses extended thinking; these settings
   prevent premature kills. Note: `max_iterations` does not exist — the correct key is `agent.max_turns`.

---

## Prompt engineering for Fable-5

Fable-5 benefits from explicit reasoning scaffolds in the delegation context. Include:

- **Explicit depth cue**: add "use deep reasoning / ultrathink" when maximum correctness
  is needed — this triggers Fable's extended thinking mode.
- **Decomposition request**: ask Fable to output a DAG or dependency tree before executing.
  Fable is better than Opus at catching circular dependencies and hidden ordering constraints.
- **Adversarial frame**: for security/config audits, ask Fable to "assume an attacker
  with full read access to this config" — this activates a more paranoid reasoning mode.
- **Verification step**: ask Fable to self-verify its plan before executing each phase.
  Fable will catch its own errors at planning time rather than midway through execution.
- **Explicit output schema**: Fable produces more structured output when given a schema.
  Ask for a JSON summary at the end with keys: changes_made, risks_identified, items_deferred.

Example context additions for a Fable orchestration:

```
REASONING DEPTH: Use extended/ultrathink reasoning for the decomposition and verification
phases. Shallow analysis is not acceptable here.

DECOMPOSITION: Before executing, output a dependency DAG (text format) showing which
subtasks block which. Only proceed once the DAG is internally consistent.

ADVERSARIAL FRAME: Assume an adversary with read access to all files listed. Identify
attack vectors they would use before proposing defenses.

OUTPUT SCHEMA: End with a JSON block:
{
  "changes_made": [...],
  "risks_identified": [...],
  "items_deferred": [...],
  "confidence": "high|medium|low",
  "recommend_followup": true|false
}
```

---

## Post-flight

After a Fable run completes:

1. If spawn depth was raised: restore both depth and concurrency together:
   ```
   hermes config set delegation.max_spawn_depth 1
   hermes config set delegation.max_concurrent_children 3
   ```
2. If delegation.model was overridden: restore `grok-4.6` / `xai`
   (`hermes config set delegation.model grok-4.6` and
   `hermes config set delegation.provider xai`). Do not restore to Sonnet or Mistral.
3. Check the result's `confidence` and `items_deferred` fields — Fable will flag anything
   it couldn't fully resolve; those need a follow-up pass.
4. Commit any file changes to the hermes-config repo if they touch config/veto/hooks.

---

## Workflow: Fable parent, cheap leaves

The most cost-effective Fable pattern on this instance (parent Grok, cheap Mistral leaves;
Fable is exception-only):

```
Fable-5 (parent session, explicit user ask)
  └─ mistral-small-latest (ALL delegate_task children — no per-call model)
```

Do not draw a Fable→Sonnet-5→leaf tree. `delegate_task` has one `delegation.model`.
If you need Fable children, use Pattern B (temporary `delegation.model` override) and
restore to `mistral-small-latest` immediately after spawn.

Nested Fable→Opus→leaf trees need `max_spawn_depth 2` and are exception-only.
Default spawn depth stays 1.

---

## Pitfalls

- **Skill audit false positives from `.archive/`** — Fable's skill catalog scan reads from the Hermes skills index, which may include skills already moved to `.archive/`. These appear as `use_count=0, view_count=0` entries needing deletion, but they are already archived — deleting them again will error. Before acting on any "never-used skill" finding, confirm the skill is in the active skill tree, not `.archive/`:
  ```bash
  find ~/.hermes/skills -type d -name "<skill-name>"
  # If path contains .archive/, it's already handled — skip the deletion
  ```

- **Fable is slow** — extended thinking adds latency. Set realistic expectations (5-15min
  for complex orchestrations). Do not kill a Fable run because it appears stuck — check
  with `process(action='poll')` before cancelling.
- **Cost** — Fable costs significantly more per token than Opus. Always set a budget cap
  for long runs via `--max-budget-usd` in any embedded claude CLI calls.
- **Fable over-decomposes** — it will produce more subtasks than necessary for simple work.
  Use Opus for tasks that feel "complex but not formally hard". Reserve Fable for tasks
  where correctness is the primary constraint, not speed.
- **Don't run Fable from a nearly-full context** — it needs headroom to think. Compact first.
- **Spawn depth 2 is stateful — restore BOTH depth AND concurrency** — they are a matched pair.
  Restoring only depth while leaving `max_concurrent_children` at 4 causes unexpected fan-out on
  routine delegations. Always restore in one command chain:
  `hermes config set delegation.max_spawn_depth 1 && hermes config set delegation.max_concurrent_children 3`
- **Actual dispatched model may not be Fable** — in Pattern B, the config override must be confirmed
  written before delegate_task is called. Check the async result header (`Model:` line) to verify
  Fable-5 was actually dispatched. If `mistral-small-latest` (this instance's leaf default) appears instead,
  the config was set too late or the write didn't flush. Re-run with config already in place and
  verified before dispatch.
- **Fable catches its own bugs** — it will write ad-hoc verification tests if given scaffolding
  (e.g. asking for empirical verification of regex patterns, security rules, or config changes).
  When Fable says it caught a bug and fixed it, verify with fresh tool runs — the fix is likely
  real but do not trust self-report alone. Ask it to write a verification script, then execute
  the script yourself.
- **`hermes config get` is not a valid subcommand** — valid config subcommands are only:
  `show`, `edit`, `set`, `path`, `env-path`, `check`, `migrate`. To verify a config value was
  actually written after `hermes config set`, use:
  ```
  python3 -c "import yaml; d=yaml.safe_load(open('/var/home/rainbow/.hermes/config.yaml')); print(d.get('delegation', {}))"
  ```
  Do NOT chain `hermes config get` as a verification step — it always fails silently and
  makes the config appear unwritten when it actually succeeded.
- **Carry "already fixed" context across recursive audit passes** — when recursive
  self-improvement audits span context compression or multiple sessions, the orchestration
  prompt MUST include an explicit "WHAT PRIOR PASSES ALREADY FIXED" list. Without it,
  Fable will re-diagnose and re-fix already-resolved items, wasting tokens and risking
  regressions. Format as flat bullets with severity tag + one-line summary. Put it in
  the context= field of delegate_task (background info), not just the goal=.

- **Unattended subagents deadlock on terminal approval prompts — mandate patch/write_file for file edits.**
  Background delegate_task subagents run with no user present. If the task instructions tell
  the subagent to edit a file via `terminal` (e.g. `python-docx`, `sed`, a python script that
  writes to disk), the terminal call itself can trigger an approval/consent gate that nothing
  will ever answer — the subagent stalls, then reports back "blocked, awaiting your direction"
  having done zero editing, even though the analysis/review phase completed fine. This has
  happened twice in NAB-review-style tasks: the subagent did the hard analytical work (image
  transcription, adversarial review) correctly but never touched the file.
  Fix at the prompt-scaffolding stage, not after the fact: when a delegated task (Fable or
  a Mistral leaf) needs to modify a file, explicitly instruct it in the context/goal to use the
  `patch` tool (targeted find/replace) or `write_file` (full overwrite) for the actual edit,
  and reserve `terminal` only for read-only verification (e.g. `python3 -c "..."` to print
  paragraph counts, run a linter, or diff). Sample instruction to embed in delegation context:
  ```
  FILE EDITS: Use the patch tool (old_string/new_string) or write_file for any change to
  the deliverable. Do NOT use terminal to run python-docx/sed/awk scripts that write to disk —
  those calls can hit an unattended approval gate and stall permanently. terminal is fine for
  read-only checks only (counting paragraphs, verifying cross-references, running a linter).
  ```
  If a subagent nonetheless reports "blocked on terminal approval, awaiting direction" with the
  analysis complete, don't re-dispatch the same subagent — take its findings (already in the
  returned summary) and apply the fixes yourself via patch/write_file/python-docx-through-terminal
  from the parent session, where you can approve prompts interactively.

- **Don't delegate file-mutation-via-terminal to a backgrounded subagent — it can get stuck
  forever on an unresolvable approval prompt.** Subagents run detached from any interactive
  user, so if their task plan involves a terminal command that trips a consent/approval gate
  (backup copies, `python-docx` installs, in-place file edits via a script), the subagent
  reports the command was "blocked/denied" and stops mid-task waiting for a response that
  will never come — burning most of its budget with zero file changes made. This happened
  twice in one task chain (both dispatched Fable-5 subagents stalled on the same kind of
  terminal call while editing a .docx). Structure delegation to avoid this:
  1. Ask the subagent to do analysis/diagnosis ONLY (read files, compare against ground
     truth, list issues + fixes) and explicitly tell it NOT to attempt file mutation itself.
  2. Have the parent session apply the actual fixes after the subagent reports back, using
     `patch`/`write_file`/a short inline script via `terminal` in the parent's own (already
     consent-cleared) session — never re-delegate the mutation step to another backgrounded
     subagent.
  3. If a subagent's summary shows it stalled on a blocked terminal call mid-task, treat its
     analysis output as still usable (it's often complete) — read the findings and finish the
     mutation yourself rather than re-dispatching the same delegation and hoping the gate
     doesn't trip again.

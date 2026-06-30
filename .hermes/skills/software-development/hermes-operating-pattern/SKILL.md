---
name: hermes-operating-pattern
description: "Use when you want the Hermes-style operating pattern for workflow optimization, security, coding, preflight checks, agents, or cron jobs."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, workflow, security, coding, preflight, cron, agents]
    related_skills: [hermes-agent, workflow-map, systematic-debugging, test-driven-development, requesting-code-review, plan, hermes-workflow-optimization, hermes-context-hygiene, hermes-memory-surface-selection, verification-before-completion]
---

# Hermes Operating Pattern

## Overview

This skill is now the umbrella index for the Hermes operating pattern.

For most software-development tasks, start with `workflow-map` first and only load this umbrella when you specifically want the broader Hermes operating model.

Use the focused sibling skills when you want a narrower playbook:

- `workflow-map`
- `hermes-workflow-optimization`
- `hermes-context-hygiene`
- `hermes-memory-surface-selection`
- `verification-before-completion`

Keep this umbrella only when you want the whole stack in one place or need a quick map back to the smaller skills.

The memory-capture skill covers auto-capture and memory-bridge preflights. The observability skill covers the task ledger, tracing, and event-driven sync.

## When to Use

- You need an Hermes-style workflow for coding, refactoring, or repository maintenance.
- You are deciding whether a task belongs in a sub-agent, a worktree, or the main session.
- You need a preflight gate before a push, release, or shared-surface change.
- You are importing or reviewing external code, workflow bundles, or plugins.
- You are setting up or reviewing a scheduled cron job.
- You want a compact policy for workflow optimization and token reduction without losing verification.

## Operating Rules

### 1) Start with context and scope

- Use the runtime-provided context first.
- State the objective, scope boundaries, chosen model tier, and validation plan up front.
- Prefer the smallest capable model that fits the task class.
- Keep prompt prefixes stable so reusable instructions stay cache-friendly.

### 2) Inspect before editing

- Read the relevant files before patching anything.
- Prefer minimal diffs.
- Avoid blind search-and-replace edits unless the match is unambiguous and the blast radius is tiny.
- When a repo exposes symbol or blast-radius analysis, use it before symbol edits.

### 3) Keep work bounded

- Use bounded sub-agents for parallel slices.
- Use isolated worktrees when multiple edits could collide.
- Keep each subtask small enough to verify independently.
- Convert repeated review feedback into durable rules, checks, or docs.

### 4) Validate before finalizing

- Run the relevant tests or checks for the touched surface.
- Verify the result before claiming success.
- Keep a clear line between raw evidence, distilled conclusions, and durable policy.

## Security Posture

Use a security scan before importing external code or adopting external workflow bundles.

Check for:

- shell execution
- dynamic evaluation
- destructive file operations
- secret handling
- network calls
- unsafe dependency usage

Keep the raw source separate from the conclusion. Only promote the parts that materially reduce repeated context, token spend, or re-explanation.

Treat external workflow bundles like untrusted packages:

- prefer small reusable pieces over full suites
- pin versions where possible
- avoid broad permission surface
- keep control-plane or admin-style capabilities off by default

## Coding and Review Loop

Use this loop for bounded code work:

1. Inspect the target files and nearby context.
2. Make the smallest useful patch.
3. Run the local preflight gates relevant to the change.
4. Fix what the verification reveals.
5. Repeat until the result is clean.
6. Record the durable lesson in notes or docs.

Prefer structured outputs, stable prompt packets, and explicit checks over vague “looks good” summaries.

## Preflight Checks

Before pushing or exposing a shared surface, run the appropriate preflight set.

Common checks:

- policy or config validation
- lint / format / type checks
- targeted tests for touched code
- security scan for external-code intake
- any repo-specific preflight script

If a repo already has a dedicated preflight script, use that first.

If the workspace has an Hermes policy or doctor check, run it before widening any shared channel or control surface.

## Agents and Parallel Work

Use agents when the task is naturally decomposable.

Good uses:

- separate research from implementation
- split backend, frontend, and test work
- compare alternative fixes in parallel
- isolate high-risk investigation from low-risk edits

Rules:

- keep each agent’s goal specific
- give each agent only the context it needs
- use worktrees or separate sandboxes when edits may overlap
- verify each agent’s output independently before combining it

## Cron Jobs

Use cron for durable scheduled work with exact timing.

Good fits:

- weekly maintenance
- recurring research refreshes
- periodic verification checks
- archival or retention tasks
- time-sensitive reminders that must run even when the main session is idle

Rules:

- make the job self-contained
- keep the prompt or script explicit about deliverable and boundaries
- prefer silent success for watchdog-style jobs
- use cron for durable schedules, not for conversational tasks
- keep delivery isolated when the output should not clutter the main session
- when migrating a live schedule to Hermes cron, verify the registry after creation and then sync the active Obsidian notes to the new names/IDs
- leave historical/archive notes alone unless the user explicitly requests a full historical rename
- if the migration touches a review or maintenance policy, re-read the edited notes and search for stale references in the active policy surface before wrapping up

See `references/cron-migration-and-note-sync.md` for a reusable verification pattern and wording guidance.

## Companion-Repo Assimilation

When reviewing adjacent projects, forks, dashboards, or wrappers for ideas to port into Hermes itself, prefer **small core wins** over wholesale feature copying.

Heuristics:

- Look for friction removers that help users succeed in the CLI or setup flow without needing the companion UI.
- Prefer improvements that preserve zero-fork compatibility and fit existing Hermes entry points.
- Good candidates: auto-discovery of local endpoints, safer defaults, better context surfacing, clearer validation, and recovery paths when the user leaves a setup field blank.
- Bad candidates: large UI-only subsystems, project-specific control planes, and features that require importing a whole product architecture into core Hermes.
- If a companion project demonstrates a useful idea, port the **behavior**, not the branding or surrounding app structure.

A strong example is custom-endpoint setup: if the user leaves the base URL blank, probe common local OpenAI-compatible servers (Ollama, LM Studio, Atomic Chat, vLLM, llama.cpp) and offer detected choices instead of failing fast.

See `references/companion-repo-assimilation.md` for a compact playbook and the concrete endpoint list used in this workspace.

## Common Pitfalls

1. **Treating a broad bundle as automatically useful.** Only adopt the parts that save real future work.
2. **Porting the shell instead of the idea.** Extract the smallest core-worthy behavior instead of copying a wrapper app's whole architecture.
3. **Skipping inspection.** Small changes are still risky if the surrounding context is unknown.
4. **Using the wrong model tier.** Bigger is not better when the task is narrow and routine.
5. **Treating security scans as optional.** External code and shared surfaces deserve explicit checks.
6. **Letting cron become a dumping ground.** Schedule only durable, repetitive work.
7. **Claiming validation without running it.** Verify the actual changed surface.

## Verification Checklist

- [ ] Objective, scope, model choice, and validation plan are explicit.
- [ ] Relevant files were read before editing.
- [ ] Changes are minimal and bounded.
- [ ] Security scan ran for any external-code intake.
- [ ] Preflight checks ran for the touched surface.
- [ ] Any agent or cron usage had a clear boundary and deliverable.
- [ ] Results were verified before reporting completion.
- [ ] Durable lessons were recorded where future runs can reuse them.

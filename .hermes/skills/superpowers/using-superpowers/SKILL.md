---
name: using-superpowers
related_skills:
  - brainstorming
  - plan
  - using-git-worktrees
  - subagent-driven-development
  - test-driven-development
  - requesting-code-review
  - verification-before-completion
  - receiving-code-review
  - finishing-a-development-branch

triggers:
  - starting non-trivial implementation work
  - want to know which superpowers skill to load for a complex task
  - choosing between plan/spike/brainstorm/dispatch/execute workflows at the start of a large task
  - need to decide whether another Superpowers skill should be invoked before acting
description: Use when starting non-trivial implementation work, or when you need to decide whether another Superpowers skill should be invoked before acting.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [workflow, superpowers, planning, specs, subagents, tdd, bootstrap]
    related_skills: [brainstorming, plan, using-git-worktrees, subagent-driven-development, test-driven-development, requesting-code-review, verification-before-completion, receiving-code-review, finishing-a-development-branch]
---

# Using Superpowers

<SUBAGENT-STOP>
If you were dispatched only to execute a narrow subtask and the parent already chose the workflow, you do not need to restart the full Superpowers intake ceremony. Follow the assigned task unless another specific skill is clearly needed.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If there is even a small chance that a skill applies, load the skill before acting.

If a relevant skill exists, use it. Do not rationalize your way around it because the task looks simple, urgent, or familiar.
</EXTREMELY-IMPORTANT>

Hermes-native port of the core obra/superpowers workflow.

## Instruction priority

1. User instructions, workspace instructions, and repo instructions
2. Superpowers skills
3. Default behavior

User instructions win. Skills control how to execute, not whether to obey the user.

## Core rule

Do not jump straight to coding on non-trivial work.

## Workflow order

1. Check whether a process skill applies before responding or taking action.
2. If the problem is still open-ended, use `brainstorming` first.
3. Turn the chosen direction into a concrete plan with `plan`.
4. In git repos, prefer `using-git-worktrees` for non-trivial changes unless the user wants in-place edits.
5. Execute with `executing-plans` or `subagent-driven-development` as appropriate.
6. For behavioral changes, prefer `test-driven-development` unless the user explicitly approves an exception.
7. Before claiming the work is done, use `requesting-code-review` and `verification-before-completion`.
8. When review feedback arrives, use `receiving-code-review`.
9. When a branch is ready to wrap up, use `finishing-a-development-branch`.

## Hermes tool mapping

- invoke a skill -> `skill_view` or session `/skill`
- ask a true blocking question -> `clarify`
- create task checklist -> `todo`
- read/search files -> `read_file`, `search_files`
- edit files -> `patch`, `write_file`
- run verification -> `terminal`
- dispatch subagents -> `delegate_task`

More detail: `references/hermes-tool-mapping.md`

## Red flags

These thoughts usually mean you are skipping the workflow:

- "This is just a quick question."
- "I'll inspect files first and load skills later."
- "I remember what that skill says."
- "This task is too small for a skill."
- "I'll do one thing first, then get organized."

## Skill priority

When multiple skills might apply:

1. Process skills first (`brainstorming`, `systematic-debugging`)
2. Execution skills next (`plan`, `executing-plans`, `subagent-driven-development`)
3. Finish/review skills last (`requesting-code-review`, `receiving-code-review`, `verification-before-completion`, `finishing-a-development-branch`)

## Notes

This Hermes port intentionally reuses existing Hermes skills where they already match upstream Superpowers:

- `test-driven-development`
- `systematic-debugging`
- `requesting-code-review`
- `subagent-driven-development`
- `verification-before-completion`

See also:
- `references/hermes-tool-mapping.md`
- `references/porting-notes.md`
## Reference files

- `references/hermes-bootstrap-usage.md` — Hermes bootstrap usage for Superpowers

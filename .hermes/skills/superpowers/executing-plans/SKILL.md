---
name: executing-plans
related_skills:
  - plan
  - using-git-worktrees
  - finishing-a-development-branch
  - subagent-driven-development

triggers:
  - A written implementation plan already exists and needs to be executed step by step
  - User says 'execute the plan', 'run the plan', or 'implement per the plan'
  - Need to follow a .hermes/plans/ markdown plan with explicit verification at each step
  - Translating a completed plan document into sequential tool calls
description: Use when you already have a written implementation plan and want to execute it step by step with explicit verification.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [execution, planning, implementation, workflow]
    related_skills: [plan, using-git-worktrees, finishing-a-development-branch, subagent-driven-development]
---

# Executing Plans

Execute a reviewed plan, not an improvised one.

## Process

1. Read the plan fully.
2. Challenge any unclear or risky step before changing files.
3. Turn the plan into `todo` items.
4. Execute one verified step at a time.
5. If independent chunks exist and subagents are available, prefer `subagent-driven-development` over solo execution.
6. When all steps are done, use `verification-before-completion` and, in git repos, `finishing-a-development-branch`.

## Stop conditions

Stop and ask instead of guessing when:
- the plan is contradictory
- repo reality differs from the plan
- verification fails repeatedly
- a missing dependency or permission blocks trustworthy execution

## Rule

Do not silently rewrite the plan mid-flight. If the approach changes materially, return to `plan`.
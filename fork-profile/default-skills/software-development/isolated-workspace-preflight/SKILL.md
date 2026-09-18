---
name: isolated-workspace-preflight
triggers:
  - Making non-trivial code changes in a git repo and need worktree isolation
  - Deciding whether to use a git worktree before substantial implementation work begins
  - Verifying a clean baseline before starting a large branch or implementation
  - User asks 'should I use a worktree for this?' before a risky refactor
description: >
  Use when: Decide when to use Hermes worktree isolation for code changes, then verify a clean baseline before substantial implementation.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, worktree, isolation, preflight, safety]
    related_skills: [workflow-map, complexity-gated-planning, hermes-agent, subagent-driven-development, requesting-code-review, verification-before-completion]
related_skills:
  - verification-before-completion
  - plan
  - workflow-map
  - complexity-gated-planning
  - hermes-agent
  - subagent-driven-development
  - requesting-code-review
---

# Isolated Workspace Preflight

Use this skill before substantial code changes in a git repo when isolation may reduce risk.

Core rule: **default to isolation for code changes; opt out only for provably safe edits.**

The ecosystem has converged (Helmor, Orca, Superset, Sandcastle, Vibe Kanban, Lanes) on
worktree isolation as the non-negotiable baseline for parallel and agentic coding work.
Match that standard.

## When to strongly prefer isolation (DEFAULT path)

Use Hermes worktree mode or a git worktree for:
- ANY multi-file write task in a git repo
- ALL parallel agent dispatches
- risky refactors, migrations, or dependency changes
- subagent-driven-development (each agent gets its own branch)
- long-running work with many checkpoints
- unfamiliar codebases where you don't know the blast radius

If in doubt, isolate. The overhead is one `git worktree add` command.

## When isolation is usually unnecessary (OPT-OUT)

Skip only when:
- read-only inspection (no writes at all)
- provably single-file, trivially reversible, two-line patch
- non-git directories with no branch history to protect
- documentation-only with no code path impact

State explicitly when opting out and why.

## Step 1: Detect repo/isolation state

Check:
- are you in a git repo?
- are you already in an isolated workspace/worktree?
- does the user explicitly want in-place edits?
- are parallel agents likely?

If already isolated, do not create more isolation just for ceremony.

## Step 2: Decide and explain

Choose one of:
- `use isolation`
- `work in place`

State the reason briefly.

Good examples:
- "Using isolation because this is a multi-file refactor and parallel review may happen."
- "Working in place because this is a tiny read/write change in one file and no parallel edits are needed."

## Step 3: If using isolation

Prefer Hermes-native isolation:
- `hermes -w` for spawned agents
- existing harness-native worktree mechanisms if already provided

Avoid inventing extra nested isolation if the environment already created a worktree.

## Step 4: Verify baseline before heavy work

Before substantial implementation in the chosen workspace:
- inspect git status
- run the narrowest relevant baseline test/build if the project has one
- note pre-existing failures before continuing

Why:
- you need to distinguish new breakage from existing breakage

## Step 5: Carry the isolation decision forward

If you spawn workers or background Hermes sessions for code work, pass the isolation choice through consistently.
For parallel code-editing agents, default to isolated workspaces.

## Practical Hermes mapping

- Main session staying local: fine for small edits
- Spawned worker doing code changes: prefer `hermes -w`
- `delegate_task`: cannot directly toggle CLI worktree mode, so compensate with narrower task scope and careful file verification

## Report format

Before implementing, be explicit:
- Repo state: git / non-git
- Isolation decision: yes / no
- Reason: one sentence
- Baseline check: command or inspection used

## Pitfalls

- forcing worktrees for tiny changes
- skipping baseline checks before major edits
- forgetting that multiple workers editing one checkout can conflict
- assuming isolation exists without checking
- treating worktree creation as success without verifying the workspace is usable
- running config-mutating CLIs from inside a scratch clone or evaluation checkout without checking their config root behavior first; some tools persist local `config/` files relative to the current working directory, which pollutes the repo and creates false positives during evaluation

## Scratch-evaluation hygiene

When cloning a repo only to evaluate or trial-install it:
- keep the clone in a scratch area
- prefer installing into a dedicated venv or user-local path rather than the repo itself
- run baseline checks from the repo, but run persistent config commands from a neutral directory like `$HOME` unless the tool explicitly documents project-local config as intended
- after any installer/config step, check `git status --short` in the scratch clone to catch accidental repo-local state writes before you conclude the evaluation is clean

This matters for CLIs that auto-create local config directories based on the current working directory. A successful command can still leave misleading untracked files in the evaluation clone.

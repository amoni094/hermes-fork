---
name: finishing-a-development-branch
related_skills:
  - using-git-worktrees
  - requesting-code-review
  - verification-before-completion
  - github-operations

triggers:
  - implementation is complete on a git branch and needs to be verified and shipped
  - user says 'finish the branch', 'ready to merge', 'create PR', or 'open pull request' after coding work is done
  - need to present merge/PR/keep/discard options after branch work completes
  - worktree cleanup is needed after a branch is merged or abandoned
description: Use when implementation is complete on a git branch and you need to verify, present next-step options, and clean up correctly.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, merge, pr, completion, cleanup]
    related_skills: [using-git-worktrees, requesting-code-review, verification-before-completion, github-operations]
---

# Finishing a Development Branch

Before offering merge or PR choices, verify the work actually passes its gates.

## Required order

1. Run the relevant tests/build/lint now.
2. Inspect repo state: branch, worktree, diff, staged vs unstaged.
3. Determine whether this is a normal checkout or a worktree.
4. Present clear next-step options.
5. Execute only the option the user chose.
6. Clean up worktrees only when the chosen path truly allows it.

## Menu to present

- merge locally
- push/create PR
- keep branch as-is
- discard work

For destructive discard, require explicit confirmation.

## Safety rules

- never merge with failing verification
- never delete a branch before its worktree is safely removed or no longer needed
- never remove a harness-owned or user-owned workspace just because it is a worktree
- do not force-push unless the user explicitly asked

## Verification

Report the exact proof command(s) and current branch/worktree path.
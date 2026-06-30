---
name: using-git-worktrees
description: Use when making non-trivial changes in a git repository and you want isolation from the user's main checkout.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, worktree, isolation, branches]
    related_skills: [using-superpowers, isolated-workspace-preflight, finishing-a-development-branch]
---

# Using Git Worktrees

Prefer isolated work for larger or risky repo changes.

## Default policy

If the task touches a git repo and is more than a tiny edit, create or use an isolated branch/worktree unless the user explicitly wants in-place edits.

## Hermes workflow

1. Check repo state first: `git status`, current branch, existing worktrees.
2. If an existing task-specific branch/worktree already matches the job, reuse it.
3. Otherwise create a new branch/worktree under a predictable local path such as `.worktrees/<branch>` when safe for the repo.
4. Do the work inside that path.
5. Keep the main checkout clean.

## Do not use when

- the directory is not a git repo
- the user explicitly wants a minimal in-place edit
- the change is trivial and the cost of isolation outweighs the benefit

## Verification

Confirm the worktree path, branch name, and `git status` before editing.

See also `isolated-workspace-preflight` for the heavier repo-specific decision process.
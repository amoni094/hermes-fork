---
name: split-ci-workflow-change-and-draft-pr
triggers:
  - a mixed CI/workflow/docs change needs to be split into separate PRs
  - CI pipeline change is bundled with feature code and must be separated
  - creating a draft PR that contains only infrastructure or workflow changes
  - a single commit accidentally mixed examples, docs, and live CI workflow changes
description: Use when a mixed CI/workflow/docs change needs to be split into scoped git commits, verified locally, drafted as a PR, and optionally saved as reusable process knowledge.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, github, ci, workflows, docs, verification, skills]
related_skills:
  - github-operations
  - github-issue-to-pr
  - scoped-pr-fix-and-verification
---

# Split CI workflow change and draft PR

Use this after a combined repo-maintenance change has already been made and you need to turn it into a clean reviewable series.

## When to use
- A single commit accidentally mixed examples, docs, and live CI workflow changes.
- A user asks to split one broad change into smaller commits.
- The branch adds or hardens GitHub Actions / GitLab CI workflows and you need a PR description grounded in real verification.

## Workflow

1. Load the relevant verification / GitHub workflow skills if available.
2. Inspect the current commit and working tree.
   - `git show --stat --name-only --format=fuller <commit>`
   - `git status --short --branch`
3. If you need to split the most recent commit, rewrite locally.
   - `git reset --soft HEAD~1`
   - IMPORTANT: follow immediately with `git reset` to unstage everything before making scoped commits.
   - Pitfall: a soft reset leaves the entire index staged; if you skip `git reset`, the first new commit may absorb every file.
4. Stage and commit exact path groups sequentially, not in parallel.
   - Example grouping:
     - reusable examples under `examples/workflows`
     - docs/nav/GitLab bundle under `docs/`, `mkdocs.yml`, `contrib/workflows`
     - live GitHub workflows under `.github/workflows`
5. Verify after the rewrite.
   - `git log --oneline --decorate -N`
   - `git status --short --branch`
   - if workflows/templates changed, parse edited YAML locally with PyYAML / `yaml.safe_load`
   - read back key workflow files to confirm hardened inputs are actually consumed downstream
   - run `toolbox run ouroboros qa <workflow-or-pr-file>` as an optional final QA pass on the edited workflow YAML or drafted PR body
   - if Ouroboros is unauthenticated or unavailable, record that as an optional QA skip rather than blocking the git/CI verification path
6. Draft a PR description with:
   - summary
   - commit breakdown
   - verification actually run
   - limits of verification
   - follow-ups
7. If the procedure proved reusable, save it as a skill and read it back once.

## Rules
- Do not try to create multiple git commits in parallel.
- After any `git reset --soft`, assume the index is still fully staged until proven otherwise.
- When splitting CI/workflow changes, keep examples/docs/live workflows in separate commits when feasible.
- In the PR description, distinguish local syntax/content verification from true hosted-CI execution.
- For workflow hardening changes, explicitly verify that cleaned `GITHUB_ENV` values are what later steps use.

## Verification checklist
- history shows the intended scoped commits in order
- working tree is clean
- YAML parses successfully
- PR description reflects actual commit SHAs and real checks run

## Pressure scenario caught in real use
A parallel commit attempt after a soft reset can silently collapse the split because the full index remains staged. The safe recovery is: reset soft one commit back, run plain `git reset`, then restage exact path groups and commit sequentially.

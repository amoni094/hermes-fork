---
name: github-pr-followup-automation
description: "Create a PR, report its identifier, and optionally set up recurring follow-up checks with cron-driven fix/verify/push loops."
version: 1.0.0
author: Hermes Agent
license: MIT
created_by: agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, Cron, Automation, Verification]
    related_skills: [github-pr-workflow, verification-before-completion, hermes-agent]
---

# GitHub PR Follow-up Automation

Use this when the user wants more than a one-time PR open/push workflow — especially when they want you to keep watching a PR for comments, requested changes, or CI results and respond over time.

## When to trigger

- The user asks to create/open a PR and also wants the PR number or URL.
- The user asks you to check back later for PR comments, review requests, or CI failures.
- The user wants a recurring loop: inspect PR state, fix issues, rerun checks, commit, and push.
- The user asks to stop, cancel, pause, or remove a PR watch job.

## Core workflow

1. Confirm the branch is pushed and clean enough to open a PR.
2. Create the PR with `gh pr create` when `gh` is authenticated.
3. Immediately report the PR number and URL back to the user.
4. If ongoing follow-up is requested, create a cron job with a self-contained prompt that:
   - inspects PR reviews/comments/checks
   - fixes only actionable PR-related issues
   - reruns the relevant verification commands
   - commits and pushes any fixes
   - reports either exact changes/evidence or a precise "no action needed" result
5. If the user later asks to cancel the watch, use `cronjob list` first, then remove the exact job id.

## Cron prompt requirements

The cron prompt should be explicit and self-contained because cron jobs do not inherit chat context.

Include:
- repo path
- branch name
- PR number
- what to inspect (`gh pr view`, comments, reviews, checks)
- allowed scope (do not broaden beyond PR issues)
- exact verification commands to rerun after changes
- required output when nothing is actionable

## Reporting requirements

Always include:
- PR number
- PR URL
- if a watch job was created: job name, job id, cadence, and delivery target

This prevents a common gap where the automation exists but the user cannot refer to it precisely later.

## Repeat/cadence guidance

Prefer a bounded repeat count for recurring PR maintenance unless the user explicitly asks for an indefinite watch and the environment policy allows it. A bounded repeat window keeps the automation inspectable and easy to stop.

If using Hermes cron for recurring PR maintenance:
- schedule at the requested cadence (`every 30m`, etc.)
- prefer delivery back to the originating conversation unless the user requests otherwise
- do not attempt recursive cron creation from inside the cron run

## Verification after fixes

After any PR-follow-up change, rerun the narrowest relevant checks before committing/pushing. Reuse the same verified commands that proved the feature initially, unless the comment/CI failure requires broader coverage.

## Clean follow-up PR branching

When the follow-up work happens after an earlier PR was already merged, do not assume the old feature branch is still the right PR head.

Before `gh pr create` for a follow-up PR:
- inspect the branch ancestry against the intended base (`git fetch origin main`, `git diff --stat origin/main...HEAD`, `git log --oneline origin/main..HEAD`)
- if the branch carries historical merged commits, produces an unexpectedly huge PR diff, or `gh pr diff`/GitHub returns an oversized diff error (for example HTTP 406 `PullRequest.diff too_large`), stop and create a clean replacement branch from the base branch
- cherry-pick only the follow-up commits onto that clean branch, rerun verification, then open the PR from the clean branch instead
- if a noisy/superseded PR was already opened from the old branch, open the clean replacement PR and close the superseded one with a short pointer comment

This prevents a common follow-up PR failure mode where GitHub shows old branch history instead of just the new fixes.

## Pitfalls

- Do not open a follow-up PR from an old feature branch without checking its diff against the base branch first; merged history can make the PR unusably large.
- Do not keep a superseded noisy PR open once a clean replacement PR exists.
- Do not open the PR and forget to tell the user the PR number.
- Do not create a watch job without telling the user the job id; they need it for later cancellation.
- Do not make the cron prompt vague; missing repo/branch/verification details makes the job unreliable.
- Do not let the watch job widen scope beyond PR comments/check failures.
- Do not remove a cron job by guessing; list jobs first, then remove the exact id.

## Reference

See `references/pr-watch-prompt.md` for a reusable prompt structure for cron-based PR follow-up jobs.
See `references/clean-followup-pr-branching.md` for a concise recipe to replace a noisy follow-up PR with a clean branch off the base.

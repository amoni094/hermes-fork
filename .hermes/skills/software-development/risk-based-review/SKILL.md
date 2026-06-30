---
name: risk-based-review
description: "Choose review depth based on change risk: self-check for low risk, reviewer for medium risk, and reviewer plus final verifier for high risk."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [review, risk, delegation, verification, quality]
    related_skills: [workflow-map, requesting-code-review, verification-before-completion, plan, subagent-driven-development]
---

# Risk-Based Review

Use this skill after implementation and before finalizing, committing, or merging when you need to decide how much review is warranted.

Core rule: review depth should scale with risk, not habit.

## Step 1: Score the change

Assess these factors:
- External side effects: deploys, messages, writes to third-party services
- Security/auth impact: secrets, permissions, identity, network exposure
- Data risk: migrations, deletes, irreversible updates, billing, user data
- Concurrency/state risk: queues, caches, retries, background jobs
- Breadth: many files, many subsystems, or large diff
- Novelty: unfamiliar codepath or unclear requirements
- User visibility: output sent to users/customers, dashboards, alerts
- Delegation: substantial work performed by subagents or background workers

### Repository-type calibration for security reviews

Before judging risk or recommending hardening, classify the artifact:
- app/service/infrastructure repo
- automation/plugin/tooling repo
- content/skills/reference repo

Do not review every repository as if it were a production service. Calibrate the review target first.

For content/skills/reference repos, treat these as primary hardening surfaces:
- CI/CD workflows and token permissions
- validators, indexers, and other repository-maintenance scripts
- helper scripts shipped for users to execute
- unsafe defaults in examples or automation (`verify=False`, fixed world-readable temp paths, `shell=True`, `curl | sh`, mutable `latest` tags)

When reviewing a hardening pass on a content/skills/reference repo, explicitly check for over-hardening before you celebrate a clean guardrail run:
- did a validator or checker gain a new dependency that CI/workflows do not install?
- did the checker become too permissive and start hiding real findings behind broad string checks or loose heuristics?
- did secure-by-default changes remove discoverability for the opt-in escape hatch (env var, CLI flag, help text)?
- did the cleanup change detection semantics or educational intent rather than just fixing unsafe defaults?
- if warnings reached zero, confirm that happened because the implementation improved or the checker became more precise — not because the rule was silently weakened

Do not treat the subject matter itself as the flaw. In offensive-security or security-research repositories, commands and examples may be intentionally powerful. Flag the accidental risk boundary instead:
- unsafe defaults
- hidden side effects
- missing confirmation/dry-run gates
- over-broad automation permissions
- weak validation that lets malformed or misleading content through

## Step 2: Choose depth

### Depth 0 — Inline verification only
Use when:
- small, local, reversible change
- no external side effects
- low security/data risk
- easy to verify directly

Required actions:
- self-check
- run targeted verification
- use `verification-before-completion`

### Depth 1 — One independent reviewer
Use when any of these are true:
- 2+ files changed
- logic changed in a meaningful way
- moderate user impact
- unfamiliar codepath
- delegated implementation work needs a fresh set of eyes

Required actions:
- run your own verification
- dispatch one reviewer subagent with compact context
- fix important findings before finalizing

### Depth 2 — Reviewer plus final verifier
Use when any of these are true:
- auth/security-sensitive changes
- production-facing automation
- migrations or destructive operations
- background jobs / workflow orchestration
- changes with ambiguous requirements or high blast radius

Required actions:
- reviewer subagent checks logic/risk
- implement fixes
- final verifier independently checks the resulting artifact or behavior

### Depth 3 — Multi-role review
Use only for high-risk or multi-part work:
- spec or requirements review
- code review
- final verification

This should be selective, not the default.

## Reviewer prompt shape

Pass only what the reviewer needs:
- what changed
- what it is supposed to do
- files or diff to inspect
- risk areas to focus on
- exact output format requested

Do not dump your whole conversation. Fresh context is the point.

## Final verifier role

The final verifier is not another code reviewer. The verifier proves that the end result works by:
- reading files back
- running tests/build/health checks
- comparing output to requirements
- checking external side effects or returned IDs/statuses where applicable

## Escalation heuristics

Default upward when:
- you are tempted to say "probably"
- you used multiple agents
- you changed auth, permissions, or money/data flows
- verification is indirect or expensive
- failure would be embarrassing or hard to undo

Default downward when:
- change is tiny and locally provable
- no delegation was used
- no one but the current user is affected

## Output guidance

When reporting status, include:
- chosen review depth
- why that depth was chosen
- what evidence closed the loop

Example:
- "Used review depth 2 because the change touched auth and background job behavior. Verified by targeted tests plus an independent reviewer and a final readback/health check."

## Pitfalls

- using expensive multi-agent review for trivial edits
- skipping review because the diff is small even when the blast radius is high
- mistaking a reviewer summary for verification
- giving reviewers the whole chat instead of a compact task packet

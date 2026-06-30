---
name: workflow-map
description: "Choose the right Hermes development workflow skill based on task risk, complexity, and verification needs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [workflow, planning, verification, review, isolation, triage]
    related_skills: [complexity-gated-planning, isolated-workspace-preflight, test-driven-development, requesting-code-review, risk-based-review, verification-before-completion, subagent-driven-development, hermes-role-pipelines, hermes-acp-routing]
---

# Workflow Map

Use this skill to choose which development workflow skills to load for a task instead of applying the same process every time.

## Core Principle

Scale ceremony to complexity and risk, but never skip fresh verification before claiming success.

## Decision Order

### 1. Complexity

Start with `complexity-gated-planning`.

Use it to decide whether the task should be:
- direct execution
- a lightweight checklist
- a formal written plan

### 2. Workspace isolation

If the task touches many files, risky repo state, long-running parallel work, or uncertain changes, load `isolated-workspace-preflight`.

Use it to decide whether to work in Hermes worktree mode or another isolated workspace before editing.

### 3. Implementation discipline

If you are changing behavior, fixing a bug, or refactoring code, load `test-driven-development` unless the user explicitly approves an exception.

### 4. Review depth

Before commit, push, merge, or ship decisions, load `risk-based-review`.

Use it to choose whether the change needs:
- only a self-check
- one independent reviewer
- reviewer plus separate final verifier

### 5. Pre-commit verification

If code changed, load `requesting-code-review` to run the review pipeline that checks diffs, regressions, lint/type signals, and reviewer findings.

### 6. Final completion gate

Before saying any version of:
- done
- fixed
- passes
- verified
- safe to merge
- ready to ship

load `verification-before-completion` and make sure the evidence is fresh, relevant, and sufficient.

## Autonomous-Agent Extensions

When a task benefits from explicit worker roles or transport choices, extend the base workflow with these autonomous-agent skills:

**subagent-driven-development:** Use when the task should be split into discovery, implementation, and review workers with compact context packets.

**hermes-role-pipelines:** Use when you want named specialist roles such as finder, debugger, coder, reviewer, tester, or security.

**hermes-acp-routing:** Use when you want to route a narrow worker task through a verified ACP-compatible external CLI, with Hermes delegation as the default fallback.

Use these as overlays on top of the core workflow, not as replacements for planning, review, or final verification.

## Security Skill Routing

All security tools are opt-in escalations from the grep scan in `requesting-code-review`.

| Situation | Load |
|-----------|------|
| Secrets / env vars / credentials | `secret-hygiene` |
| Full static analysis (patterns, rules) | `semgrep` |
| Interprocedural taint / data flow | `codeql` (needs codeql CLI) |
| OWASP Top 10 / agentic AI threats (ASI01-06) | `owasp-security` |
| Verify a finding is real before acting | `fp-check` |
| Parse SARIF output from any scanner | `sarif-parsing` |
| GitHub Actions AI prompt injection | `agentic-actions-auditor` |
| Over-hardening / usability regressions | `security-hardening-balance-review` |
| Adversarial pass on agent/runtime code | `security-hardening-code-review` |

Default posture: grep scan only. Escalate to semgrep for medium-risk changes; escalate to codeql for high-risk or security-focused work.

## Recommended Paths

### Small, low-risk change
- `complexity-gated-planning`
- optional direct execution
- `risk-based-review`
- `verification-before-completion`

### Normal feature or bug fix
- `complexity-gated-planning`
- `test-driven-development`
- `requesting-code-review`
- `verification-before-completion`

### Risky or cross-cutting change
- `complexity-gated-planning`
- `isolated-workspace-preflight`
- `test-driven-development`
- `risk-based-review`
- `requesting-code-review`
- `verification-before-completion`

### Delegated multi-agent implementation
- `complexity-gated-planning`
- `subagent-driven-development`
- optional `hermes-role-pipelines`
- optional `hermes-acp-routing`
- `risk-based-review`
- `requesting-code-review`
- `verification-before-completion`

### Planning-only request
- `complexity-gated-planning`
- `plan`
- include explicit verification steps in the written plan

## Anti-Patterns

Do not:
- force full planning for trivial work
- skip isolation when repo state is risky
- skip tests just because the fix looks obvious
- use the same review depth for every change
- claim completion from stale evidence or from a delegated agent summary alone

## Minimum Safe Rule

Even when the task is simple, do not skip the final evidence check. The lightweight path still ends with `verification-before-completion`.

---
name: hermes-role-pipelines
description: Multi-agent role pipeline patterns adapted from the opencode-hermes-multiagent role catalog for Hermes delegate_task.
version: 1.0.0
author: Hermes
---

# Hermes Role Pipelines

Use this when a task benefits from explicit specialist roles rather than a single worker.

If the task is only broadly about autonomous/multi-agent orchestration and the right specialist workflow is not yet obvious, load `autonomous-ai-agents` first, then route here when the concrete need is role and pattern selection.

Installed source catalog:
- `/var/home/rainbow/.hermes/integrations/opencode-hermes-multiagent/agent/subagents/`

## Recommended Hermes mapping

Research:
- finder -> fast file scout
- analyst -> dependency/risk analysis
- researcher -> external docs

Planning:
- architect -> solution shape
- planner -> task decomposition

Implementation:
- coder -> new code
- editor -> safe edits
- fixer -> bug fix
- refactorer -> structure cleanup

Quality:
- reviewer -> review findings
- tester -> focused tests
- security -> auth/secrets/data review
- debugger -> root cause analysis

Infrastructure:
- devops -> CI/CD, containers, deployment
- optimizer -> performance

## Architecture patterns adapted from Harness

Harness adds a useful layer above role names: choose the collaboration shape first, then assign roles.
In Hermes, adapt the six patterns like this:

1. Pipeline
- Use when later work depends strongly on earlier outputs.
- Hermes shape: serial `delegate_task` waves or parent-led phases.
- Good fits: analyze -> design -> implement -> verify.

2. Fan-out / Fan-in
- Use when several independent investigations can run in parallel and then be merged.
- Hermes shape: one `delegate_task(tasks=[...])` batch for discovery, then a parent synthesis pass, then one implementation worker.
- Good fits: code review across security/perf/architecture; multi-source research; cross-surface bug triage.

3. Expert pool
- Use when only some specialties are needed depending on what is found.
- Hermes shape: parent routes narrowly scoped one-off tasks to the right role instead of spawning a standing team.
- Good fits: call security only if auth/tokens appear; call devops only if CI/container paths are touched.

4. Producer-Reviewer
- Use when one worker should create and a separate worker should critique.
- Hermes shape: implementer child -> reviewer child -> parent verification.
- Good fits: code generation, documentation, migration plans.

5. Supervisor
- Use when the parent must dynamically assign work as findings arrive.
- Hermes shape: parent stays active, updates todo state, dispatches narrow workers in waves.
- Good fits: large refactors, multi-file migrations, staged debugging.

6. Hierarchical delegation
- Harness supports this conceptually, but Hermes has max spawn depth 1 for this user.
- Hermes adaptation: flatten into parent-orchestrated waves; do not expect child agents to spawn grandchildren.
- Good fits: convert would-be trees into pipeline or supervisor patterns.

## Pattern chooser

Prefer:
- Fan-out / Fan-in for independent read-only discovery
- Producer-Reviewer for non-trivial code changes
- Supervisor for dynamic multi-batch work
- Pipeline when outputs are naturally sequential
- Expert pool when most specialists are conditional

Avoid planning for hierarchical delegation here unless the runtime nesting limit changes.

## Example pipelines

Bug fix, unknown cause:
- Pattern: Fan-out / Fan-in -> Producer-Reviewer
1. finder
2. debugger
3. fixer
4. reviewer
5. tester

Feature with security impact:
- Pattern: Pipeline with expert-pool branches
1. finder
2. analyst
3. researcher
4. architect
5. planner
6. coder
7. reviewer
8. security
9. tester

Large migration with changing hotspots:
- Pattern: Supervisor
1. architect
2. planner
3. editor/refactorer wave 1
4. reviewer
5. editor/refactorer wave 2 if needed
6. tester

## Hermes execution pattern

Use parallel delegation for independent discovery, then a second wave for implementation and review.
Keep each subtask self-contained and pass compact context packets only.
Choose the architecture pattern before choosing the role names.

### Eliminating the synthesise-then-implement rework cycle

When fan-out agents produce changes that must be merged (not just read), load
`hermes-agent-sync` and use the Structured Findings Contract. Agents write typed
JSON action payloads (patch / file_append / config_set / git_commit / observation)
to `~/.hermes/agent-workspace/*.finding.json`. The parent runs
`apply-findings.py` once — no manual synthesis, idempotent re-runs safe.

Load `hermes-agent-sync` whenever:
- 2+ parallel agents touch the same files/config
- You want deterministic merge rather than prose synthesis
- You need reliable idempotency (re-dispatch safety)

When converting these collaboration shapes into reusable workflow generators or Seed scaffolds, use `references/workflow-family-seed-mapping.md` for the canonical five-family taxonomy, normalized seed styles, default-to-pipeline rule, and verification expectations.

## Local note

The upstream role catalog was designed for OpenCode AI, and Harness was designed for Claude Code agent teams.
In Hermes, treat both as design references only: map the roles into `delegate_task` goals, keep orchestration in the parent, and adapt any team/hierarchical pattern to Hermes's actual delegation constraints.

If someone tries to load `autonomous-ai-agents` expecting this skill directly, prefer the router skill first and then load `hermes-role-pipelines` explicitly.

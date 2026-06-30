---
name: autonomous-ai-agents
description: "Use when the task is about Hermes/Ouroboros multi-agent workflows and you need a router skill that points to the right specialized child skill."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, delegation, orchestration, hermes, ouroboros, routing]
    related_skills: [autonomous-agent-loop-design, hermes-agent, hermes-role-pipelines, hermes-acp-routing, auto, help, ouroboros-setup-and-health-check]
---

# Autonomous AI Agents

This is an umbrella/router skill for the `autonomous-ai-agents` skill family.

Use this skill when:
- the user asks generally about autonomous agents, agent swarms, Hermes orchestration, Ouroboros workflows, or multi-agent patterns
- you are not yet sure which specialized child skill to load
- a previous attempt tried to load `autonomous-ai-agents` directly and failed because only the child skills existed

Core rule:
- Do not stop here if a child skill clearly matches.
- After loading this skill, immediately load the most relevant child skill(s) below.

## Fast routing

### Hermes-native orchestration
Load `hermes-agent` when the task is about:
- Hermes CLI behavior
- delegation limits and capabilities
- subagents vs spawned Hermes processes
- toolsets, profiles, cron, gateway, MCP, or core Hermes features

### Role-based multi-agent pipelines
Load `hermes-role-pipelines` when the task is about:
- choosing specialist roles
- pipeline vs fan-out/fan-in vs supervisor patterns
- mapping a team/squad idea onto Hermes `delegate_task`

### External ACP-backed delegation
Load `hermes-acp-routing` when the task is about:
- routing work through Codex ACP or another verified ACP-compatible CLI
- deciding between native Hermes delegation and ACP execution

### Autonomous loop design and agent patterns
Load `autonomous-agent-loop-design` when the task is about:
- designing a cron job or background agent task that runs unattended
- making an agent improve or explore something autonomously
- setting up measurable objectives and eval infrastructure
- learning from Karpathy autoresearch patterns (nanochat, numeric objectives, cheap surrogates, reference-driven context)
- patterns: eval-as-infrastructure, uninterrupted duration for optimization, reference code beats instructions

### General delegated implementation work
Load `subagent-driven-development` when the task is about:
- splitting a coding task into discovery / implement / review workers
- keeping parent verification separate from child claims

### Claude tiering for Hermes delegation

Default to a strong planner and cheaper doers:
- Orchestrator: strongest reasoning Claude available, usually Opus-class
- Workers/sub-agents: balanced Claude, usually Sonnet-class
- Tiny leaf helpers: Haiku-class only for narrow, mechanical, low-risk tasks

See `references/claude-routing-matrix.md` for a compact routing matrix, example Hermes config, and escalation rules.

### Ouroboros usage and command selection
Load `help` when the task is about:
- what Ouroboros commands exist
- which Ouroboros command/skill should be used
- high-level Ouroboros capability discovery

### Ouroboros install/health/troubleshooting
Load `ouroboros-setup-and-health-check` when the task is about:
- installation state
- backend health
- plugin inventory
- command failures or setup drift

### Direct Ouroboros workflow execution
Load one of these when the user already knows the intended action:
- `auto` for automatic end-to-end convergence
- `seed` for seed generation
- `run` for execution
- `evaluate` for verification
- `status` for drift/session status
- `resume-session` for reconnecting to in-flight sessions
- `ralph` or `evolve` for longer-running iterative/evolutionary loops
- `pm` for PRD / PM-style requirement work
- `publish` for turning seeds into GitHub issues
- `qa` for general artifact QA verdicts
- `cancel` for stuck executions
- `update` for upgrading Ouroboros
- `brownfield` for repo-default scanning and brownfield workflow setup
- `config` for settings GUI / model-agent configuration
- `tutorial` or `welcome` for onboarding

## Practical selection heuristics

If the user says:
- "Should Hermes use subagents here?" -> load `hermes-agent` and `hermes-role-pipelines`
- "What is the best multi-agent pattern for this task?" -> load `hermes-role-pipelines`
- "Use Codex/ACP for the worker" -> load `hermes-acp-routing`
- How do I use Ouroboros for this? -> load `help`
- Ouroboros is broken / not found / not running -> load `ouroboros-setup-and-health-check`
- Take this vague idea to execution -> load `auto`
- Design a cron job / autonomous task / background loop -> load `autonomous-agent-loop-design`
- How do I make this run unattended? -> load `autonomous-agent-loop-design`

## Important clarification

`autonomous-ai-agents` is both:
- a category/namespace containing many skills, and
- this umbrella skill, created so direct loads of `autonomous-ai-agents` succeed.

If a direct load of `autonomous-ai-agents` ever fails again, verify that this umbrella skill still exists and that skills were reloaded.

## Completion rule

This skill is successful only if it routes to a more specific child skill when one is applicable. It is not the final destination for most tasks.

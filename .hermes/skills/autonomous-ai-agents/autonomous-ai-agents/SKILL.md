---
name: autonomous-ai-agents
triggers:
  - user asks generally about autonomous agents, Hermes orchestration, or Ouroboros workflows without specifying a sub-skill
  - you are unsure which specialized agent skill to load and need a routing decision
  - user asks about agent swarm design, multi-agent patterns, or orchestration architecture
  - routing to a child skill is needed (hermes-agent, hermes-role-pipelines, hermes-acp-routing, autonomous-agent-loop-design, etc.)
  - direct load of `autonomous-ai-agents` was attempted and failed because only child skills existed
description: "Use when the task is about Hermes/Ouroboros multi-agent workflows and you need a router to the right child skill. Not for actually dispatching parallel workers (use dispatching-parallel-agents)."
version: 1.1.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, delegation, orchestration, hermes, ouroboros, routing]
    related_skills: [autonomous-agent-loop-design, hermes-agent, hermes-role-pipelines, hermes-acp-routing, trajectory-risk-guardrail, mnemosyne-atp-safety, hermes-swarm-consensus, async-agent-nightshift-patterns, agent-task-signoff, agent-browser-troubleshooting, agent-runtime-stack-debugging, verification-before-completion, ouroboros-setup-and-health-check]
related_skills:
  - autonomous-agent-loop-design
  - hermes-agent
  - hermes-role-pipelines
  - hermes-acp-routing
  - trajectory-risk-guardrail
  - mnemosyne-atp-safety
  - hermes-swarm-consensus
  - async-agent-nightshift-patterns
  - agent-task-signoff
  - agent-browser-troubleshooting
  - agent-runtime-stack-debugging
  - verification-before-completion
  - ouroboros-setup-and-health-check
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
- pipeline vs fan-out/fan-in vs supervisor vs speaker-selected group patterns
- mapping a team/squad idea onto Hermes `delegate_task`
- AutoGen-style speaker selection (who talks next during a run) or conversation-driven task decomposition
- flattening nested AutoGen chats into parent-orchestrated waves (depth-1)

Do **not** load `hermes-role-pipelines` for post-fan-out verdict conflicts — that is `hermes-swarm-consensus`. GroupChat is turn-taking; swarm-consensus is fan-in arbitration.

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
- multi-phase config/infrastructure upgrades (audit → implement → export → validate → push) using a single orchestrator subagent
- see `subagent-driven-development#references/multi-phase-config-orchestration.md` for context packet template and verification checklist

### Claude vs live Hermes routing

Aspirational Claude split (Opus planner / Sonnet workers / Haiku extractors) is
**not** this instance. Live map is `claude-routing-hierarchy`: session parent
`claude-sonnet-4-6` / anthropic, fallback + `delegation.model` `grok-4.6` / xai,
aux leaves `mistral-small-latest`. Do not follow `references/claude-routing-matrix.md`
as if it were current — that file is a dated snapshot plus a pointer.

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

### Agent safety, risk, and multi-agent trust
Load `trajectory-risk-guardrail` when the task is about:
- pre-flight risk assessment before multi-step tool chains with side effects
- checking whether a planned sequence is safe before running it
- any plan involving file writes, network calls, process execution, or external state mutation

Load `mnemosyne-atp-safety` when the task is about:
- admission control for individual tool calls inside an agent loop
- rollback and checkpoint logic for multi-step agentic workflows
- ATP commit/deny/hold decisions, or dependency-guided rollback provenance

Load `hermes-swarm-consensus` when the task is about:
- aggregating verdicts from multiple agent/judge instances
- preventing mode-collapse in homogeneous agent panels
- ColluSkill / DEAR echo-chamber / first-mover bias resistance in multi-agent evaluation

Load `async-agent-nightshift-patterns` when the task is about:
- deny-by-default unattended agent safety (agents running without a human present)
- sandboxing, tool-scope minimization, or budget caps for overnight/unattended runs

## Map-Guided Harness Escalation (arXiv:2608.17433, Aug 2026) <!-- why: reduces token cost 48% by starting minimal and escalating only on self-check failure, not by always providing full toolset -->

Task-Aware Harness Provisioning: full toolset exposure is not universally optimal. Agents given full harness do NOT always outperform agents given task-specific minimal harness — accuracy is domain-dependent and follows a Pareto frontier, not a universal optimum.

**Map-guided escalation algorithm:**
1. Classify the task type (read-only research / write-bounded implementation / system-level execution)
2. Start with a minimal task-specific toolset (not full toolset)
3. Proceed with the minimal harness unless a structural inability appears (tool error, missing evidence required by `output_contract`). Do not escalate on a yes/no self-check or self-assessed confidence.
4. Escalate to a larger harness only after a structural inability, not a self-reported "I cannot".

## WRITE OWNERSHIP

This umbrella routes only. It does not write skills, memory, or promotions.

- `runtime-skill-synthesis` owns: crystallize/merge/promote.
- `self-improve-agent` owns: human-gated skill proposals.
- `skillopt-continuous-improvement` owns: score/diagnose only (no writes).
- `agent-memory-consolidation` owns: hindsight/memory only.
- `autonomous-ai-agents`: route only, no writes.

**Enforcement:** while this skill is the only agent skill loaded, do not call `skill_manage`,
`memory()`, `hindsight_retain`, or promotion scripts. If a write is required, load the owner
skill first and follow that skill. A router that writes is a contract violation, not a shortcut.

**Hermes `delegate_task` application:**
- Always specify `enabled_toolsets` on every delegate_task call — do not rely on full default toolset
- Minimal defaults per task class:
  - Research/read-only: `["web", "file"]`
  - Code implementation: `["terminal", "file"]`
  - Reporting/writing: `["file"]`
  - Cross-domain: `["web", "terminal", "file"]`
- Only include `delegation` in toolsets if the task genuinely needs sub-delegation
- `memory` and `session_search` should be explicitly added when needed, not defaulted
- This is the correct implementation of MasDrift mitigation (Sweep 14): scope at EVERY delegation level
- Risk-aware retrieval (arXiv:2608.22751): do not expose `computer-use`, `delegation`, or payment/credential tools unless the task needs them — retrieval-stage filtering beats post-execution safety. <!-- why: tool retrieval is a pre-execution safety boundary -->

**Key finding:** "harness provisioning follows a domain-dependent accuracy-cost Pareto frontier rather than a universal optimum" — the right toolset depends on task class, not on maximizing coverage.

**Toolformer add-on (Schick et al., arXiv:2302.04761):** skills already get predicted-utility routing (`hermes-semantic-skill-routing`). Tools do not — `enabled_toolsets` loads a whole set. Keep the map-guided minimum, then apply a second gate before adding a toolset: the speaker's output contract must require evidence that tool produces, and that evidence must not already be in context. Idle tools steal routing attention. Procedure lives in `hermes-role-pipelines` → `references/autogen-toolformer-patterns.md`.

## Interaction Tax (arXiv:2608.23541) ★ HIGH <!-- why: peer full-solution exchange erases multi-agent diversity within one round -->

Different model families find structurally different solutions; feeding complete peer outputs
into siblings collapses that diversity in one round. That cost is the **interaction tax**.

**Rules (also in `dispatching-parallel-agents`):**
1. Dispatch workers with isolated contexts. Do not inject peer full solutions into sibling `context=` mid-batch.
2. Collect independent proposals first (findings JSON / short verdicts / ranked options).
3. Bounded synthesis at the parent (or one synthesizer leaf) — not iterative full-solution debate between peers.
4. If a second round is needed, pass deltas / disagreements / open questions, not the prior peer transcript.
5. Same-model panels already co-fail (phi≈0.9); full-solution exchange makes that worse.

**Anti-pattern:** chain A→B where B's `context=` is A's full answer "so B can improve it" on pass 1.
Map-guided minimal toolsets still apply per worker — interaction tax is orthogonal to toolset scope.

## HASTE — UNTRUSTED ID (arXiv:2608.20888)
Crash-dump attribution. 2608.20888 is not HASTE. Do not implement a 4-tier hierarchy from this ID. Existing category/`tier` layout is enough.

## AMD Skill Tier Distillation (arXiv:2608.07169)
Keep AMD's 3-tier memory injection. Do not pair it with HASTE 2608.20888 (untrusted ID).

**Hermes mapping:**
- **Proactive**: `hermes-memory-surface-selection`
- **Reactive**: `agent-memory-consolidation`
- **Skill**: `hermes-agent-skill-authoring`

Distill a procedure only if it occurred 3+ times across distinct sessions, had positive outcomes, and is not already a skill. No HASTE level mapping.

## RethinkSkill — UNTRUSTED ID (arXiv:2608.20777)
Crash-dump attribution. 2608.20777 is Tree-of-Concerns, not skill refinement. Use `adversarial-review` if needed; do not invent a RethinkSkill loop from this ID.

## PoisonedEvolution — Memory Poisoning in Self-Improving Agents (arXiv:2608.21230, Aug 2026) ★ HIGH <!-- rationale: memory poisoning defense -->

**PoisonedEvolution** is a memory poisoning attack on self-improving agents.

**Defense:**
- Cross-verification before write (see Memory Poisoning Write Gate)
- Write-path filtering: reject memories that:
  - Contain sensitive data (PII, passwords, API keys)
  - Make absolute claims without evidence
  - Introduce new entities without context
- Use `hermes-skillspector-guard-maintenance` to scan for poisoned skills
- Set `trust_level: experimental` on auto-patched skills and review after 5+ distinct sessions
- Never auto-promote a skill to `trust_level: production` without at least one recorded failure and a patch applied from that failure

## Skill improvement — ROUTER ONLY

For skill improvement, load self-improve-agent (human-gated patches) or runtime-skill-synthesis (staged crystallization). Do not patch skills from the umbrella.

Do not call `skill_manage` from this skill. Do not "update immediately" from this router. TRACE / SkillAlchemy / EvoAgent procedures live in those child skills, not here.

## Practical selection heuristics

If the user says:
- "Should Hermes use subagents here?" -> load `hermes-agent` and `hermes-role-pipelines`
- "What is the best multi-agent pattern for this task?" -> load `hermes-role-pipelines`
- "Who should speak next / GroupChat / speaker selection?" -> load `hermes-role-pipelines` (AutoGen speaker-selected group; not swarm-consensus)
- "Decompose the task via conversation / nested agent chat?" -> load `hermes-role-pipelines` + `hermes-context-packet`
- "Use Codex/ACP for the worker" -> load `hermes-acp-routing`
- "Is this plan safe to run?" -> load `trajectory-risk-guardrail`
- "How do I prevent bad tool calls in a loop?" -> load `mnemosyne-atp-safety`
- "How do I get a reliable verdict from multiple agents?" -> load `hermes-swarm-consensus`
- "Task complete — produce a sign-off table / evidence log" -> load `agent-task-signoff`
- "Parallel agents returned results that need structured synthesis" -> load `agent-task-signoff`
- "Browser / headless Chrome is stuck or zombie" -> load `agent-browser-troubleshooting`
- "Plugin, dispatcher, or runtime stack is failing" -> load `agent-runtime-stack-debugging`
- How do I use Ouroboros for this? -> load `ouroboros-setup-and-health-check`
- Ouroboros is broken / not found / not running -> load `ouroboros-setup-and-health-check`
- Design a cron job / autonomous task / background loop -> load `autonomous-agent-loop-design`
- How do I make this run unattended safely? -> load `async-agent-nightshift-patterns`

## Important clarification

`autonomous-ai-agents` is both:
- a category/namespace containing many skills, and
- this umbrella skill, created so direct loads of `autonomous-ai-agents` succeed.

If a direct load of `autonomous-ai-agents` ever fails again, verify that this umbrella skill still exists and that skills were reloaded.

## Completion rule

This skill is successful only if it routes to a more specific child skill when one is applicable. It is not the final destination for most tasks.

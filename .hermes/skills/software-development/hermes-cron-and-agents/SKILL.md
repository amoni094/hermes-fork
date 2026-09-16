---
name: hermes-cron-and-agents
triggers:
  - need Hermes guidance for bounded sub-agent cron jobs with clear deliverables
  - scheduling a cron job that spawns or delegates work to sub-agents
  - configuring agent-driven automation that must run on a schedule when the main session is idle
  - splitting a task into parallel slices that can each be verified independently
description: "Use when you need the Hermes guidance for bounded sub-agents, isolated worktrees, or durable cron jobs with clear deliverables."
version: 1.1.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, agents, subagents, worktrees, cron, scheduling]
    related_skills: [hermes-agent, hermes-operating-pattern, hermes-coding-review-loop, hermes-observability-and-task-ledger, trajectory-risk-guardrail, preact-trajectory-compilation]
related_skills:
  - verification-before-completion
  - plan
  - hermes-agent
  - hermes-operating-pattern
  - hermes-coding-review-loop
  - hermes-observability-and-task-ledger
  - trajectory-risk-guardrail
  - preact-trajectory-compilation
---

# Hermes Cron and Agents

## Overview

Use this skill when the task is naturally decomposable or needs durable scheduling.

Bounded sub-agents are for parallel slices that can be verified independently. Cron jobs are for work that must run on a schedule even when the main session is idle.

## When to Use

- You can split research, implementation, or verification into separate slices.
- You need a bounded sub-agent with a narrow objective.
- You need isolated worktrees or separate sandboxes for parallel edits.
- You want a recurring job for maintenance, verification, research refreshes, or retention work.

## Agent Rules

- Give each agent only the context it needs.
- Keep each goal specific and small.
- Use worktrees or isolated sandboxes when edits could overlap.
- Verify each agent’s output independently before combining results.
- Pandora k-sizing (math-005): reviewer/worker fan-out follows `dispatching-parallel-agents` § Pandora Dispatch Sizing — low variance → fixed k=3; high variance → threshold until confidence>0.85 (cap k=5); unknown → k=3.

## Critical config: session_stall_timeout (add to config.yaml)

Root cause from production (2026-08-30): parent sessions killed before parallel research
agents complete. Research agents need 12-18 min; default timeout was 300s. Agents appeared
to stall; they were being SIGTERM'd.

Fix: set in ~/.hermes/config.yaml:
  session_stall_timeout: 1800   # was 300; match gateway_timeout
  gateway_timeout: 1800

Rule: session_stall_timeout MUST be >= longest expected delegate_task child runtime.
  Research agents: 1800 (30 min). Quick tool agents: 600 (10 min).
  Never set session_stall_timeout < gateway_timeout.

Verify: grep -E 'session_stall_timeout|gateway_timeout' ~/.hermes/config.yaml

## S9 — Cron silent stall pattern

A cron job can exit 0 and produce output but perform no useful work ("successfully stalling").
Or it never finishes, so the next tick fires while the current run is still live (overlap).

Signals:
  - Job logs show no state change between ticks
  - Job output is shorter/vaguer than prior runs
  - next tick fires before previous completes (no overlap guard)

Recovery:
  1. Kill overlapping live run before starting the next tick (add overlap guard)
  2. Resume from clean checkpoint (not contaminated context from failed run)
  3. Add explicit terminal state declaration at end of prompt: "DONE: <what was accomplished>"
  4. Add output hash check: if output hash == previous run hash, treat as S9 stall

Prevention:
  - Set continuity: false for stateless cron jobs (no residual context bleed)
  - Set continuity: true only when the job explicitly needs its own prior output
  - Always include an explicit success criterion in cron prompt
  - monitor: script pattern (hermes cronjob) for hash-change gating is natural overlap guard

## Cron Rules

- Make the job self-contained.
- Always verify delegate_task children completed before combining results.
  Use delegate_task(action='list') to check status; steer or stop stalled children.
  Do not stop based on time alone — check if transcript is advancing (S5 stall rule).
- Keep the schedule, prompt, and deliverable explicit.
- Use cron for durable scheduled work, not conversational back-and-forth.
- Prefer silent success for watchdog-style jobs.
- Keep delivery isolated when the output should not clutter the main session.
- Use the task ledger when the platform exposes one so long-lived work stays visible.
- Prefer event-driven sync over cron when file changes can be observed directly.

## Subagent Stall Detection (Spike O, arXiv:2608.25992 ProgRouter)

Detect subagent stalls using tool-call signatures, not time alone. Productive iteration
looks like same-tool-DIFFERENT-ARGS (e.g., 5x web_search with different queries). True
stalls look like same-tool-SAME-ARGS (e.g., 3x web_search("same query")).

Stall heuristic: if a child's live transcript shows the same tool name AND same argument
values 3+ times consecutively, the child is stuck — steer or stop it.

Heuristic check via transcript tail:
  tail -30 /path/to/task.log | grep '"tool_name"' | sort | uniq -c | sort -rn
  If any tool+args pair appears 3+: STALL. Run delegate_task(action='steer', ...)
  with message: "You appear stuck in a loop calling <tool>(<args>). Change approach:
  try a different tool or different arguments, or synthesize from what you have."

Do NOT trigger stall detection on same-tool-different-args patterns:
  web_search("query A"), web_search("query B"), web_search("query C") = productive
  web_search("same query") x3 = stall

Logging gap (pending Spike O): add completion_status field to cobra-outcomes.jsonl
so that subagent completion rate becomes trackable.

## Common Pitfalls

1. Spawning an agent for a task that is not actually decomposable.
2. Giving a child too much context and turning it into a duplicate parent.
3. Using cron for a one-off conversational reminder.
4. Scheduling a job without a clear output shape or verification path.

## Verification Checklist

For L2+ cron tasks that dispatch agents with side effects, run select-frameworks
before writing the agent goal file to determine which reasoning gates to include:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<agent goal>" --level <L>
  ```
  If lookahead is in primary: include lookahead invocation in the goal file before HAZARD actions.
  If subplan-verify is in primary: include it at phase boundaries in the goal file.

- [ ] The task is decomposed only where it helps.
- [ ] Each agent goal is narrow and specific.
- [ ] Cron jobs are self-contained and durable.
- [ ] Delivery stays isolated when needed.
- [ ] Independent verification happens before combining results.

## Adaptive Retry Budgeting for delegate_task (arXiv:2608.25403, Sep 2026)

Retry Amplification Factor (RAF): naive retries under correlated failure reduce overall success
from 55.4% to 41.5% vs no-retry. Multi-tier retry stacks (parent retries + child retries +
tool-level retries) produce cascading failure amplification.

**Rules for delegate_task:**
- Never retry a child task more than 2 times for the same failure type
- Apply jitter (randomised delay) to avoid synchronised thundering-herd retries across parallel children
- Classify failure before retrying: transient (network blip, timeout) = retry OK;
  correlated/systemic (provider down, rate limit, config error) = do NOT retry, escalate
- For SYSTEMIC_BLAST class failures: halt all children immediately, do not retry any
- After 2 failed retries: report failure to parent with the failure class, do not loop

**ARB config — UNIMPLEMENTED in Hermes runtime (config.yaml block is commented out):**
The block below is operator guidance; the Hermes runtime does not yet read `delegation.retry_policy`.
Real live knob is `agent.api_max_retries` (currently 5 — higher than the ARB-recommended 2).
TODO: wire retry_policy into delegate_task failure classification to make this live.
```yaml
# delegation.retry_policy:  # commented out — runtime does not read; apply as operator discipline
#   max_retries: 2
#   base_delay_seconds: 10
#   backoff_multiplier: 2.0
#   jitter: true
#   retry_on: [transient, timeout]
#   no_retry_on: [auth, fatal, systemic]
```

**Pitfall:** the most dangerous retry pattern is the silent re-dispatch — a parent that sees
a child stall and spawns an identical replacement without checking whether the first child
actually failed. Verify child status with `delegate_task(action='list')` before re-dispatching.
Duplicate children writing to the same cache/output file = L0 concurrency anomaly (last write wins).

## Aug 2026: Anthropic Task Budgets API (for Opus 5 / Fable 5)

Source: https://platform.claude.com/docs/en/build-with-claude/task-budgets

For models that support extended thinking (claude-opus-5, claude-fable-5), you can set
a token budget for how long the model "thinks" before responding:

```python
response = client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000   # thinking tokens <= budget_tokens < max_tokens
    },
    messages=[...]
)
```

Key rules:
- budget_tokens must be less than max_tokens
- Applies only to models with extended thinking support (Opus 5, Fable 5; NOT Sonnet 5)
- "Advisory" — model may use fewer if task doesn't need it
- Setting budget too low on hard tasks hurts quality more than setting it too high hurts cost
- For Hermes delegate_task: this requires custom API calls, not standard hermes config; use
  anthropic-agent-api-patterns skill for the full implementation pattern

**Effort levels** (simpler alternative, Sonnet 5 + Opus 5):
Set `effort: low | medium | high (default) | xhigh | max` instead of explicit token budget.
Effort is preferred for most cases — let the model decide token allocation within the level.

## Cron job toolset scoping (`enabled_toolsets`)

Always set `enabled_toolsets` on cron jobs to limit which tool groups load. This cuts input token overhead significantly (each unneeded toolset adds ~2000 tokens).

Common toolset names: `web`, `terminal`, `file`, `delegation`, `memory`, `computer-use`.

Examples:
- Watchdog/alerting job that runs a script: `["terminal"]`
- News/research aggregation: `["web", "file"]`
- Agent fan-out orchestration: `["delegation", "file"]`
- Memory pipeline: `["terminal", "file", "memory"]`

Omit `enabled_toolsets` only for fully general jobs where you genuinely don't know which tools will be needed. Default (all tools) adds ~15k tokens/session — always scope it.

## Average Reward MDP for Cron Job Scheduling (Puterman Ch 8)

**Theory:** For recurring, indefinitely-running tasks, the correct optimality criterion is the long-run average reward (gain g), not discounted cumulative reward. The average-reward MDP optimal policy maximizes the time-average reward per step, not a discounted sum. Applying discount factor γ < 1 to a recurring task artificially devalues future runs.

**Hermes rules:**
- Cron job scheduling = undiscounted average-reward MDP: evaluate cron job configurations by their long-run average quality per run, not by a discounted sum that treats near-term runs as more important.
- Do NOT apply γ < 1 discounting when comparing cron policies (e.g. "run daily at 2am" vs "run weekly on Sunday") — each policy's value is its steady-state average quality.
- For bounded, one-shot agentic tasks, discounted reward (γ < 1) is appropriate. For recurring cron jobs, use undiscounted average reward.

**Citation:** Martin Puterman — *Markov Decision Processes* (2nd ed.), Ch 8 (Average Reward MDPs — gain, bias, and relative value functions).

## Content-Addressed Cron Skip Gate (OxyMake pattern, arXiv:2606.20989) — C2

Before executing a cron job, compute a content-addressed run ID (already done by run-header.py):
  run_id = sha256(script_content + config_hash + skill_hashes)[:16]

If the run_id matches the previous successful run's ID AND that run completed within the current TTL period (e.g., the job runs daily and last ran 20h ago), SKIP this execution and reuse the last result.

Why: if neither the script, config, nor skills changed, rerunning produces the same output. Content-addressing makes this provably safe (not a stale-cache guess).

Implementation: run-header.py already emits run_id and logs to ~/.hermes/logs/run-headers.jsonl. Gate logic:
  1. Before cron execute: call run-header.py to get current run_id
  2. Grep run-headers.jsonl for the same run_id within the TTL window
  3. If match: log "SKIP: content-identical to <ts>" and exit 0
  4. If no match: proceed normally

Do NOT apply to: jobs with external side effects (Graphiti writes, email), jobs that consume live data (news scrapes, API prices), or jobs with continuity:true (their output is their own prior output).

Apply to: pure analysis jobs (paper interpreter, skill audit), research sweeps where cutoff ID didn't change, benchmark-fingerprint-check.

<!-- why: research sweeps over unchanged corpora re-ran 3/5 times with identical output (2026-09-08 corpus audit); content-gating would have saved those runs without risk -->


## Parallel Agent Rate Isolation — Token Bucket Pattern (estudy noisy-neighbor, S5)

Parallel delegate_task children can exhaust API rate limits, starving siblings (noisy-neighbor problem). This is the multi-tenant LLM platform failure mode described in estudy's token-bucket rate-limiting section.

Pattern — Token Bucket for parallel agents:
- Each child's effective API call rate: cap at 60 RPM with burst of 5 (same as nous_rate_guard.py aux limits)
- Stagger strategy: when launching more than 5 parallel children, set max_concurrent=5 and stagger launches by 2 seconds

Rule: when N > 5 parallel children, do NOT launch all at once. Stagger to avoid:
  - Thundering-herd at rate limit boundary (all children hit the cap simultaneously)
  - Priority inversion (first-launched child consumes burst capacity, blocking all others)

Config today: delegation.max_concurrent_children controls parallelism; no per-child rate cap exists in Hermes runtime. Apply staggering as operator discipline in the delegate_task goal file:
  "Note: this is child N of M. Wait N*2 seconds before making your first API call to stagger load."

Feedback control analogy (Astrom-Murray): token bucket = discrete integrator with a saturation nonlinearity. Burst capacity = integrator headroom. Staggered launch = phase-offset to prevent synchronised saturation.

<!-- why: in research sweeps with 8-10 parallel children, API 429 errors cascaded across all children simultaneously because all hit the rate limit at the same turn; staggering by 2s prevented this -->


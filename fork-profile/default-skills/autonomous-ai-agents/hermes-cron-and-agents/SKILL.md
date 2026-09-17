---
name: hermes-cron-and-agents
triggers:
  - Scheduling recurring Hermes tasks with cron
  - Running bounded subagents from cron jobs
  - Orchestrating periodic background agents
  - delegate_task from a cron context
description: >
  Use when you need the Hermes guidance for bounded sub-agent delegation from cron, including
  rate isolation, token budgets, and failure handling for scheduled jobs.
version: 1.0.0
author: Hermes
# NOTE: A more complete version (v1.1.1, 276 lines) exists in software-development/hermes-cron-and-agents.
# This version (autonomous-ai-agents/hermes-cron-and-agents) is a legacy stub — prefer the SD version.
# GATE GAP: two versions exist with same name; the SD version should be canonical.
related_skills:
  - dispatching-parallel-agents
  - hermes-acp-routing
  - hermes-observability-and-task-ledger
  - async-agent-nightshift-patterns
---

# Hermes Cron and Agents

Use this skill when scheduling Hermes subagent work with cron, or when a cron job needs to launch delegate_task children.

## Cron basics

Hermes cron jobs live at `~/.hermes/profiles/<profile>/cron/`. Each job is a YAML file:

```yaml
name: nightly-sweep
schedule: "0 2 * * *"   # 2 AM daily
command: hermes run --task "run the nightly research sweep"
timeout_s: 3600
notify: on_failure
```

- `hermes cron list` — list scheduled jobs
- `hermes cron add <file>` — register a job
- `hermes cron remove <name>` — deregister

## Bounded subagent pattern (from cron)

```python
delegate_task(
  goal="Run the nightly sweep and write results to ~/.hermes/cache/sweep-YYYYMMDD.json",
  context="No interactive auth. Read-only tools only. Abort after 50 tool calls.",
  toolsets=["file", "terminal"],
  max_tool_calls=50,
  timeout_s=1800
)
```

Rules:
- Always set `timeout_s` — cron jobs must not run forever
- Always set `max_tool_calls` — prevents runaway agents
- Use `notify: on_failure` so failures surface without polling
- Log outcomes to `~/.hermes/logs/<job-name>.jsonl`

## Token budget per job

Cap prompt tokens per cron delegate to ~50k to prevent cost blowout on scheduled jobs. Pass only the minimum context needed; do not re-inject the full conversation history.

## Failure handling

- On failure: write a sentinel file `~/.hermes/cache/<job-name>.failed` with timestamp and error
- On success: delete any existing `.failed` sentinel
- Downstream jobs can gate on sentinel absence before proceeding

## Parallel Agent Rate Isolation

Parallel `delegate_task` children can exhaust API rate limits, starving siblings — the **noisy neighbor problem**.

**Pattern:** Cap each child at **60 RPM** with a burst of **5**, matching `nous_rate_guard.py` aux limits.

**Rule:** When launching **more than 5 parallel children**, enforce:
- `max_concurrent = 5` — only 5 children active at any moment
- Stagger launches by **2 seconds** between each child start to prevent synchronized burst spikes

```python
import time

tasks = [...]  # N tasks, N > 5

MAX_CONCURRENT = 5
STAGGER_S = 2.0

for i, task in enumerate(tasks):
    if i >= MAX_CONCURRENT:
        # Wait for a slot — implement a semaphore or poll active count
        pass
    delegate_task(tasks=[task])
    if i < len(tasks) - 1:
        time.sleep(STAGGER_S)
```

**Why:** The Hermes rate guard allows 60 RPM per aux process. When 6+ children fire simultaneously, their combined burst saturates the limit, causing 429 errors that cascade and extend total wall-clock time beyond sequential execution.

**Monitoring:** If any child returns a rate-limit error (429 / `RateLimitError`), pause all pending launches for 10 seconds before resuming. Log rate-limit events to `~/.hermes/logs/rate-limit-events.jsonl`.

## Guardrails

- No interactive auth in cron context — pre-authenticate all services before scheduling
- Cron agents run as non-user persona — see MCP Gateway Auth Pattern in hermes-acp-routing
- Always verify side effects before marking a cron job successful
- Rotate log files when they exceed 10 MB

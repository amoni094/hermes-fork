---
name: budget-aware-cron-adaptation
description: >
  Use when a cron job backlog exceeds budget or cron jobs consistently miss windows.
  Applies stochastic gradient scheduling: estimate job utility vs runtime cost empirically,
  then dynamically reschedule or shed low-utility jobs to stay within a token/time budget.
triggers:
  - cron jobs failing due to time budget exceeded
  - adaptive cron scheduling needed
  - cron backlog audit reveals low-utility recurring jobs
  - scheduler budget enforcement
  - cron-budget-guard.py reporting violations
category: research
---

# Budget-Aware Cron Adaptation

## Theory

From arXiv 2609.10201 (Nakamura et al., 2026): "Online Job Scheduling with Utility Budgets"
applies a stochastic gradient framework to job schedulers: each job has an estimated utility
`u_j` and a cost `c_j` (runtime, tokens, or composite). The scheduler maximizes `sum(u_j)`
subject to `sum(c_j) <= B` (budget) using an online bandit update.

Key insight: utility is not static. A job that was important two weeks ago may now be stale.
Track empirical "action rate" (how often a cron job's output triggers a follow-on action) as
the utility proxy.

**Bandit update**: `u_j(t+1) = u_j(t) * decay + reward(j, t) * (1 - decay)`
where `reward = 1` if the job's output was acted on, `0` otherwise.

## Hermes Application

Target: `~/.hermes/scripts/cron-budget-guard.py` (already exists).

### Step 1: Track action rate per job

After each cron run, the cron-budget-guard.py script should check if the job's output
triggered any downstream work (hindsight_retain call, skill update, etc.). Log:
```json
{"job_id": "abc123", "ts": 1234567, "ran": true, "acted": false, "cost_s": 12.4}
```

### Step 2: Compute utility score

```python
DECAY = 0.95

def update_utility(u_prev, acted: bool) -> float:
    reward = 1.0 if acted else 0.0
    return u_prev * DECAY + reward * (1 - DECAY)
```

### Step 3: Budget enforcement

Sort jobs by `utility / cost` ratio descending. Disable jobs below utility threshold:
```python
UTILITY_FLOOR = 0.1  # job disabled if utility drops below this
BUDGET_TOKENS_PER_HOUR = 50_000

running_budget = BUDGET_TOKENS_PER_HOUR
for job in sorted(jobs, key=lambda j: -(j['utility'] / j['cost_tokens'])):
    if job['utility'] < UTILITY_FLOOR:
        disable_job(job)
    elif running_budget >= job['cost_tokens']:
        schedule_job(job)
        running_budget -= job['cost_tokens']
    else:
        defer_job(job)  # try next window
```

### Step 4: Integration with cron-budget-guard.py

Add `--adapt` flag to cron-budget-guard.py that:
1. Reads the action-rate log
2. Updates utility scores for all jobs
3. Writes back updated `enabled` state to jobs.json

## Configuration

```yaml
# In config.yaml under cron:
budget_adaptation:
  enabled: true
  decay: 0.95
  utility_floor: 0.1
  budget_tokens_per_hour: 50000
  action_log: ~/.hermes/cache/cron-action-log.jsonl
```

## Pitfalls

- NEVER disable jobs with `utility_floor_exempt: true` in their job definition (safety jobs)
- Track action rate, not just runtime success: a job that always exits 0 but whose output is
  never used has zero utility
- Budget window should match your cron cadence (hourly for hourly jobs)
- Decay of 0.95 means ~20 runs to halve the effect of a one-time spike

## References

- arXiv 2609.10201: Online Job Scheduling with Utility Budgets (Nakamura et al., 2026)
- cron-budget-guard.py: existing budget enforcement script
- hermes-cron-and-agents skill: cron job lifecycle overview

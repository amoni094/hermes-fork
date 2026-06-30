---
name: autonomous-agent-loop-design
description: Design autonomous agent loops that can run unattended and self-improve — measurable objectives, cheap surrogates, reference-driven context, and eval-as-infrastructure patterns from Karpathy's autoresearch work on nanochat.
triggers:
  - designing a cron job or background agent task
  - delegating a long-running optimization or research task
  - asking an agent to improve, refactor, or explore something autonomously
  - setting up Ouroboros evolve loop
  - "how do I make this run unattended"
related_skills:
  - autonomous-ai-agents
  - hermes-role-pipelines
  - auto
  - evolve
---

# Autonomous Agent Loop Design

Patterns extracted from Karpathy's autoresearch work on nanochat (Mar 2026), where an agent ran unattended for 2 days, found 20 improvements a human missed, and cut GPT-2 training time from 2.02h to 1.80h (then 1.65h in round 2).

## The 5 Principles

### 1. Define a numeric objective before launching

The agent worked because CORE score is a number. Without a concrete metric, an agent optimizes vibes.

Before delegating any optimization/research task, ask:
- What number goes up (or down) when this succeeds?
- Is that number computable from within the agent's environment?
- What is the current baseline?

If you can't answer these, the task is not ready for autonomous execution. Write the eval first.

Good: "run pytest, report pass rate" / "measure p95 latency before and after" / "count lint errors"
Bad: "make this better" / "clean this up" / "improve quality"

### 2. Use a cheap surrogate, not the full target

Karpathy ran autoresearch on d12 (tiny model, fast) before applying findings to d24/d26.

For agent tasks in Hermes:
- Run the agent on one file before all files
- Run on one day of data before a month
- Run on a small dataset/subset before the full thing
- Run one iteration of a loop before scheduling it daily

Promote to full scope only after the surrogate validates the approach. This catches prompt bugs, broken tool calls, and wrong assumptions cheaply.

### 3. References beat instructions

Round 2 was more productive because Karpathy gave the agent a reference repo (modded-nanogpt) to draw from. The agent found combinations of ideas it couldn't have generated from the problem statement alone.

When writing prompts for subagents or cron jobs:
- Point at real code files, not described behavior
- Link to a reference implementation or prior working example
- For skills: a concrete reference file beats prose explanation of the same concept
- Use `context_from` in cron jobs to chain outputs — job A collects, job B reasons over it

### 4. Uninterrupted duration finds what sessions miss

The 2-day run found 20 things months of manual work missed. Interactive sessions with a human present and steering are often the wrong tool for optimization tasks.

Use background execution (cron, Ouroboros evolve, delegate_task) when:
- The search space is large (many hyperparameters, many files, many approaches)
- Each trial takes minutes, not seconds
- You want to come back to results, not watch them happen

The Ouroboros `evolve` loop is the primary tool for this in Hermes. It is underutilized relative to what this pattern suggests.

### 5. Eval is infrastructure, not an afterthought

The reason autoresearch could run autonomously: eval was runnable scripts in the repo (`tasks/arc.py`, `tasks/mmlu.py` etc.), not docs or manual checks.

An agent cannot close its own feedback loop without executable eval. Before delegating:
- Does the codebase have tests the agent can run?
- If not, write minimal test coverage first — even 3-5 targeted tests beats zero
- The agent's loop is: change -> run eval -> accept/reject. Without step 2, it's just change -> hope.

## Repo-Level Skills Pattern

Karpathy keeps `.claude/skills/read-arxiv-paper` inside the nanochat repo. Any agent working in that directory gets domain-relevant skills automatically via workdir context.

For projects you work on heavily:
```
<project-root>/
  .claude/
    skills/
      project-context/
        SKILL.md   # architecture, conventions, key files, gotchas
      eval-guide/
        SKILL.md   # how to run tests, what metrics matter, baseline numbers
```

Pass `workdir=<project-root>` when creating cron jobs or delegate_task calls against that project. The agent gets the skills without you having to repeat context.

## Quick Checklist Before Launching an Autonomous Task

- [ ] Numeric objective defined and computable
- [ ] Baseline measured
- [ ] Tested on surrogate/subset first
- [ ] Reference material attached (files, prior examples, related code)
- [ ] Eval is runnable (not just describable)
- [ ] Duration and budget set (max iterations, max cost, stop condition)

## References

- `references/nanochat-autoresearch-patterns.md` — Karpathy's nanochat loop (Mar 2026): concrete repo structure, agent loop shape, critical success factors, and what-not-to-do pitfalls. Start here for a real working example.

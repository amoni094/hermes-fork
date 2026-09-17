---
name: dispatching-parallel-agents
triggers:
  - Dispatching multiple independent tasks to parallel agents
  - Running fan-out investigations across several subagents simultaneously
  - Coordinating parallel workstreams and merging results
description: >
  Use when multiple independent investigations or implementations can run concurrently.
  Fan out with delegate_task, collect results, then reconcile.
version: 1.0.0
author: Hermes
related_skills:
  - hermes-acp-routing
  - hermes-cron-and-agents
  - hermes-swarm-consensus
  - verification-before-completion
---

# Dispatching Parallel Agents

Use this skill when you have N independent subtasks that do not depend on each other's output and can run concurrently to save wall-clock time.

## When to fan out

- 3 or more independent research or implementation subtasks
- Multiple file regions that need parallel inspection
- Different candidate solutions to compare
- Separate services or repos that need simultaneous changes

## Core pattern

```python
delegate_task(tasks=[
  {
    "goal": "Investigate X",
    "context": "Relevant files, constraints, output contract.",
    "toolsets": ["file", "terminal"]
  },
  {
    "goal": "Investigate Y",
    "context": "Relevant files, constraints, output contract.",
    "toolsets": ["file", "terminal"]
  },
  {
    "goal": "Investigate Z",
    "context": "Relevant files, constraints, output contract.",
    "toolsets": ["file", "terminal"]
  }
])
```

## Compact context packet (per child)

Always pass:
1. Exact file paths or repo URLs
2. Exact command or error to reproduce
3. Acceptance criteria (what done looks like)
4. Scope constraints (what NOT to touch)
5. Output contract: what the child must return (files, findings, pass/fail)

Keep context minimal — children share no state, so don't dump the full conversation.

## Large repo audit → subagent dispatch pattern

When tasked with auditing a large codebase for ideas/improvements and implementing them:

1. **Read key files in the parent session first** (do not delegate blind). Batch-read the highest-signal files: AGENTS.md / CLAUDE.md, top-level architecture docs, 8-12 core source files covering the main subsystems. Use `execute_code` with parallel `read_file` calls for efficiency.
2. **Synthesise the findings in the parent** — extract the concrete patterns, architectural decisions, and implementation details worth porting. This synthesis is the core value; the subagent just executes it.
3. **Dispatch one comprehensive subagent** with the full synthesised spec. The spec should:
   - List each pattern with exact source details (file paths, excerpts, design rationale)
   - Tier improvements by value (Tier 1 / Tier 2)
   - Include cross-check instructions (corpus references, theoretical foundations)
   - Specify the adversarial pass and coherence audit to run after implementation
4. The subagent does all skill_manage writes, patches, and verification in one pass.

Pitfall: dispatching the subagent before reading the repo yourself produces a vague spec the subagent fills with guesswork. Read first, distill, then delegate the execution.

## Reconciliation

After collecting results:
- Prefer the child whose output satisfies acceptance criteria with fewest side effects
- Load `hermes-swarm-consensus` when multiple subagent verdicts conflict on a DECISION (not when verdicts are all action-oriented). Do not use swarm-consensus to resolve tool-call conflicts between executors — that is a coordinator role.
- Run `verification-before-completion` before reporting success to the parent

## Rate isolation

See **Parallel Agent Rate Isolation** section below. Cap at 5 concurrent children; stagger by 2 s when launching more than 5.

## Cross-Agent Routing Artifacts

After any sequence of **3 or more tool calls** that subsequently passes `verification-before-completion`, append a routing artifact to `~/.hermes/cache/routing-artifacts.jsonl`:

```json
{
  "ts": "2026-09-15T00:00:00Z",
  "agent_id": "<session_id or delegate label>",
  "trigger_pattern": "<concise description of what triggered this tool sequence>",
  "tool_sequence": ["tool_a", "tool_b", "tool_c"],
  "outcome_score": 1.0
}
```

**Schema fields:**
- `ts` — ISO-8601 UTC timestamp of the artifact write
- `agent_id` — session ID or delegate label of the agent that ran the sequence
- `trigger_pattern` — concise natural-language description of the task pattern that triggered the sequence (used for cosine-similarity matching)
- `tool_sequence` — ordered list of tool names called
- `outcome_score` — float 0–1; 1.0 = fully verified, 0.5 = partial, 0.0 = failed

**Inheritance rule:** Future agents whose trigger pattern has cosine similarity ≥ 0.75 with a stored artifact's `trigger_pattern` MAY inherit the stored `tool_sequence` as a warm-start suggestion before cold-starting their own planning. Do not blindly execute inherited sequences — treat them as a prior, not a mandate.

**Append-only.** Never modify or delete existing entries; rotate the file when it exceeds 10 MB.

```python
import json, time, pathlib

def append_routing_artifact(agent_id, trigger_pattern, tool_sequence, outcome_score=1.0):
    path = pathlib.Path.home() / ".hermes/cache/routing-artifacts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "agent_id": agent_id,
        "trigger_pattern": trigger_pattern,
        "tool_sequence": tool_sequence,
        "outcome_score": outcome_score,
    }
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

## Guardrails

- Never launch unbounded fan-outs — always know the exact task count before dispatching
- **Purge template markers before dispatching** — `delegate_task` validates all goal and context strings for unexpanded placeholders like `{THRESH_PATH}`, `{VAR}`, or `<REPLACE_ME>` and rejects the entire batch if any are found. When building goal strings from templates or code snippets, substitute every variable before passing to delegate_task. This is especially common when copying code blocks from a skill or plan that use format-string syntax: replace `{variable}` with its concrete value, or escape it with `{{variable}}` if it is meant as a literal Python format string inside the goal text. The rejection aborts ALL tasks in the batch, not just the one with the marker.
  <!-- why: delegate_task validation runs before any subagent starts; one unexpanded marker aborts every task in the batch including the correct ones -->
- Each child must have a clear output contract so reconciliation is mechanical
- Abort and diagnose if more than half of children return errors
- Do not let children write to the same file without a merge plan

**Anti-conformity seeding:** when dispatching agents for adversarial review or consensus, give each agent a different seed perspective (e.g., one looks for performance regressions, one looks for security issues, one looks for dead code). Identical seeds + no cross-referencing = independent opinions. Cross-referencing without diverse seeds = conformity risk. (See `hermes-swarm-consensus` § Blind Conformity Guard for the underlying mechanism.)

## Role-Boundary Enforcement (arXiv:2609.09133 ExecCritic)

Each delegate_task invocation must include a role declaration (Your role is [executor|planner|reviewer]) with explicit You may NOT boundary actions. If a reviewer subagent output contains code changes, or an executor output contains strategic re-scoping, apply 0.5x trust weight in synthesis and route through a coordinator check before applying.

## Dual-Gap Budget Allocation (Luenberger Ch 7.7)

Lagrangian dual certificate for parallel agent budget: if two subagents are allocated equal budget but one returns in 30% of its budget while the other uses 100%, the allocation is dual-suboptimal. Reallocate budget from surplus agent to bottleneck until marginal values equalise.

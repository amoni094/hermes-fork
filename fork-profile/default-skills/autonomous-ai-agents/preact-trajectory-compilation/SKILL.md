---
name: preact-trajectory-compilation
depends_on: [autonomous-agent-loop-design]
provides: [compiled-trajectory, replay-state-machine, deterministic-replay]
description: >
  Use when: Compile successful agent task runs into deterministic state machines for 8.5-13x replay speedup without per-step LLM calls. Based on PreAct (arXiv:2606.17929).
tags: [agent-efficiency, replay, state-machine, cost-reduction]
related_skills: [hermes-context-hygiene, hermes-cron-and-agents, autonomous-agent-loop-design]
triggers:
  - A recurring agent task runs successfully and should be compiled into a deterministic replay state machine
  - User asks to speed up or reduce cost on a task the agent has already solved once
  - Designing a cron job or nightshift loop where LLM overhead per step should be minimised

# Disambiguation: preact vs trajectory-risk-guardrail
# preact = POST-success efficiency (task already worked; compile for replay)
# trajectory-risk = PRE-execution safety (task about to run; scan for hazards)
# If the task has never run or involves novel inputs: load trajectory-risk-guardrail FIRST.
---

# PreAct: Trajectory Compilation for Agent Replay

**Research basis:** PreAct (arXiv:2606.17929, 19PINE-AI team, Korea)
**Key benefit:** 8.5–13x speedup on repeated tasks. Zero per-step LLM cost on replays.

## When to use

After a task succeeds, compile the trajectory for replay IF the task was L2+ AND
select-frameworks was used during execution. Include the frameworks used in the compiled trajectory
so future replay agents load the correct reasoning gates:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<original task>" --level <L>
  ```
  Store the primary framework list in the compiled trajectory metadata.

- A Hermes task runs repeatedly on the same or structurally identical inputs (e.g. daily briefings, CI health checks, standard repo audits, file processing pipelines)
- The task completed successfully at least once with a clear, stable tool-call sequence
- The sequence is deterministic: same inputs → same tool calls → same outputs
- NOT suitable when: task requires reasoning about novel inputs, branching logic is heavy, tool outputs are non-deterministic

## Core concept

Instead of calling an LLM for every tool step on repeat tasks, compile a successful run into a lightweight state machine:

1. **Record** a successful agent run (tool calls, inputs, decision points)
2. **Abstract** the trajectory into a state machine: states = verification checkpoints, transitions = tool calls
3. **Verify** screen/environment state at each transition before proceeding
4. **Replay** deterministically without LLM calls
5. **Fallback** to full LLM agent on unexpected state detection

## Implementation pattern

### Step 1: Annotate a successful run

After a task completes successfully, extract the canonical sequence:

```python
# preact_record.py — capture canonical trajectory
TASK_ID = "daily-briefing-v1"
trajectory = [
    {"step": 1, "tool": "web_search", "args": {"query": "..."}, "verify": "result.count > 0"},
    {"step": 2, "tool": "write_file", "args": {"path": "~/...", "content": "..."}, "verify": "file_exists"},
    # ...
]
# Save to ~/.hermes/preact/{TASK_ID}.json
```

### Step 2: Define state verification guards

Each transition has a VERIFY guard — a lightweight check that the environment matches expectation. Guards should be:
- Fast (no LLM call)
- Specific enough to detect unexpected state
- Not so strict they fire on benign variation

```python
GUARDS = {
    "web_search_done": lambda r: len(r.get("results", [])) > 0,
    "file_written": lambda path: os.path.exists(path),
    "no_error": lambda r: "error" not in str(r).lower(),
}
```

### Step 3: Replay executor

```python
def replay_task(task_id: str, inputs: dict) -> dict:
    """Execute compiled trajectory without LLM. Falls back on guard failure."""
    with open(f"~/.hermes/preact/{task_id}.json") as f:
        trajectory = json.load(f)

    for step in trajectory:
        result = call_tool(step["tool"], {**step["args"], **inputs})
        guard = GUARDS.get(step.get("verify"))
        if guard and not guard(result):
            # Unexpected state — fall back to full LLM agent
            return fallback_to_agent(task_id, inputs, step["step"], result)
    return {"status": "ok", "replayed": True}
```

### Step 4: Cron scheduling for compiled tasks

When a task is compiled, schedule it without agent overhead:

```bash
# Only use no_agent=True if output is purely stdout-driven
# Otherwise use a thin wrapper that calls the compiled replay
hermes cron create --schedule "0 8 * * *" \
  --prompt "Execute preact replay for task daily-briefing-v1"
```

## DART-SD — Diamond-Topology Self-Distillation of Tool-Call Trajectories (arXiv:2608.18524, Sweep 20) <!-- why: single-trajectory exemplar retrieval misses global structure; diamond topology captures both local turn context and cross-session trajectory shape -->

Standard few-shot exemplar retrieval picks the most similar past trajectory flat. Diamond-topology retrieval structures past trajectories as a diamond graph: each node is a (state, tool-call) pair; edges capture both local sequential flow and global trajectory-level similarity. Retrieval walks the diamond to find exemplars that match BOTH the current turn context AND the overall session trajectory shape.

Hermes implementation: before compiling a trajectory into a skill, store successful multi-turn tool-call trajectories in Graphiti as execution exemplar nodes with edges encoding: (a) sequential tool-call order, (b) state delta after each call, (c) cross-trajectory structural similarity. At inference, retrieve the topology-matching exemplar rather than the string-similar one. This improves tool sequencing quality, especially for tasks with non-linear recovery paths.

Key result: topology-aware retrieval outperforms flat similarity on multi-turn tool-calling benchmarks by reducing invalid tool-call sequences by 31%.

## TMI — Task Model Induction from Execution Traces (arXiv:2608.20319, Sweep 20) <!-- why: unconstrained traces contain recoverable latent task structure; induction outperforms retrospective summarization -->

Task Model Induction (TMI, Aug 2026): induces hierarchical task models (goals → subtasks → actions) from raw execution traces. 0.974 inter-annotator agreement on task recovery. Outperforms both retrospective LLM summarization and direct human labelling for latent structure recovery.

Key insight: task structure is latent in traces — it must be induced, not described by the agent mid-run. Agents that self-describe their task structure during execution produce noisier, self-serving models than those induced post-hoc.

Hermes application for trajectory compilation:
1. After collecting a set of successful trajectories for a task type, run a TMI-style induction pass before distilling into skills:
   - Level 1: what is the terminal goal of these trajectories? (induced from final tool-call patterns, not agent's stated goal)
   - Level 2: what are the recoverable subtask boundaries? (look for state-change events: file writes, API calls that change external state, decision points with branching)
   - Level 3: what atomic action sequences appear in ≥60% of successful traces? (these become skill steps)
2. Hierarchical model: skill = L3 action sequences + L2 subtask gates + L1 goal statement
3. Discard trajectories where L1 goal can't be induced (they describe different tasks, not the same task done differently)

This extends the existing `preact` pattern: instead of compiling the first successful trajectory into a skill, collect 3+ before running TMI induction to get structure that generalises.

## ToolLIFT — function-level workflow graphs (arXiv:2608.03468)

Do not treat a tool-specific call sequence as the reusable artifact. After a multi-tool trajectory completes, **lift** it to a function-level workflow graph, then store that graph as a template beside the PreAct state machine.

- **Nodes** = tool *classes* (`search`, `extract`, `read`, `write`, `verify`, `delegate`) — not concrete tool names or frozen args
- **Edges** = data dependencies (output of A is input of B)
- Replay binds classes back to current tools. A renamed tool does not invalidate the graph.

After Step 1 (annotate), emit `~/.hermes/preact/{TASK_ID}.workflow.json`:

```json
{
  "task_id": "daily-briefing-v1",
  "nodes": [
    {"id": "n1", "class": "search"},
    {"id": "n2", "class": "extract"},
    {"id": "n3", "class": "write"},
    {"id": "n4", "class": "verify"}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "dep": "hit_list"},
    {"from": "n2", "to": "n3", "dep": "facts"},
    {"from": "n3", "to": "n4", "dep": "artifact_path"}
  ]
}
```

Skip lift for single-tool trajectories. Do not store raw arg blobs on nodes — those belong in the parameterized PreAct replay, not the abstract graph.

## Pitfalls

- **Over-compiling**: Don't compile tasks with significant conditional logic. The state machine will trigger false fallbacks.
- **Input variability**: If the task takes variable user inputs, parameterize those in the trajectory — don't hardcode.
- **Tool version drift**: Compiled trajectories may become stale if tool APIs change. Version-pin critical tool schemas.
- **Guard sensitivity**: Guards too strict → frequent unnecessary fallbacks (wastes no savings). Guards too loose → guard misses bad state (corrupted output). Start with coarse guards, tighten over runs.
- **False economy on short tasks**: If the task is only 3-5 tool calls, compilation overhead may not pay off. Target tasks with 10+ steps.

## Verification

After implementing a compiled task:
```bash
# Run once in dry-run mode with verbose logging
python3 replay_task.py --task-id daily-briefing-v1 --dry-run --verbose
# Compare output structure to recorded baseline
# Verify fallback fires correctly by injecting a bad state
```

## Cost model

Approximate savings per run:
- Typical task: 15 LLM calls × ~800 tokens each = 12,000 tokens/run
- Compiled replay: 0 LLM calls = 0 tokens/run
- At $3/1M tokens: ~$0.036/run saved → 100 runs/month = $3.60/month saved
- Break-even on 2-3 successful recordings

## References

- PreAct: arXiv:2606.17929 (19PINE-AI, Korea, surfaced July 2026)
- Related: Mnemosyne/ATP (arXiv:2607.00269) for safety guarantees on compiled workflows
- See also: hermes-cron-and-agents skill for scheduling patterns

## Playbook Debrief → Draft Pattern (Denuto Pattern)

Source: Denuto `src/playbook_loop/` (debrief.py, diff.py, version.py).

Pattern for capturing agent task outcomes and proposing skill improvements.

### 1. Capture debrief after task completion

```python
# What happened vs what was expected
debrief = {
    "task_id": "run_abc",
    "outcome": "partial",     # success | partial | failed
    "deviations": [           # per-expectation gaps
        {
            "policy_reference": "skill:ralph-loops §Round-Trip Validation",
            "observed": "validation step was skipped — no critical findings check",
            "proposed_text": "Add: assert no critical findings before break",
        }
    ],
}
```

### 2. Diff debrief against current skill

```python
import difflib

def diff_skill_section(pinned: str, proposed: str, section: str) -> str:
    lines_a = pinned.splitlines(keepends=True)
    lines_b = proposed.splitlines(keepends=True)
    return "".join(difflib.unified_diff(lines_a, lines_b,
        fromfile=f"pinned/{section}", tofile=f"proposed/{section}"))
```

### 3. Propose draft — NEVER mutate the live skill directly

```python
def bump_minor(version: str) -> str:
    """Pure function. '1.0' → '1.1'. No side effects."""
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)
```

**Key invariant**: proposal ≠ live skill. Create a proposal via `improvement_governance.py`,
apply only after risk classification (LOW → auto-approve, MEDIUM/HIGH → human review).

### 4. Hermes integration

```bash
# After a task run with deviations found:
python ~/.hermes/scripts/improvement_governance.py propose \
  --change-type skill_body \
  --target ralph-loops \
  --description "Debrief: validation step skipped in loop" \
  --evidence "session $(hermes session current)"
# LOW risk → auto-approved → apply via skill_manage patch
# MEDIUM/HIGH → surface to user
```

See also: `hermes-improvement-governance`, `preact-trajectory-compilation`, `ralph-loops`.

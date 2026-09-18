---
name: hermes-context-packet
triggers:
  - About to spawn a Hermes subagent via delegate_task and need a compact context packet
  - Need the canonical JSON schema for passing context to a subagent
  - Assembling a structured context packet before every delegate_task call
  - Preventing 'what is that?' responses from subagents by giving them complete upfront context
description: >
  Use when: Canonical compact JSON context-packet schema and assembler for spawning Hermes subagents. Use before every delegate_task call to eliminate oversized ad-hoc context and cut fan-out token cost.
version: 1.0.0
author: Hermes
tags: [multi-agent, delegation, context, token-budget, subagent]
related_skills: [hermes-role-pipelines, hermes-agent-sync, hermes-swarm-consensus]
---

# Hermes Context Packet

A single canonical shape for the `context` you pass into `delegate_task`. Replaces
free-form prose dumps (which bloat token cost and leak irrelevant state) with a
compact, predictable JSON packet.

## When to use

Before **every** `delegate_task` call. Assemble a context packet first, then pass
it as the task `context`. This is mandatory for fan-out batches where the same
packet shape is reused across many parallel agents — small per-packet savings
multiply across the swarm.

## Schema (`hermes-context-packet/v1`)

```json
{
  "schema": "hermes-context-packet/v1",
  "objective": "string — the single concrete goal for this agent",
  "scope_paths": ["list of files/dirs the agent may read or modify"],
  "constraints": [
    {
      "text": "hard rule",
      "binding": "must",
      "authority": "user|policy|safety",
      "fallback": "what to do if blocked",
      "consequence_if_ignored": "execution consequence"
    }
  ],
  "working_memory_ref": "optional path or session id for ~/.hermes/cache/working-memory/",
  "prior_findings_refs": ["list of file paths to previous agent outputs"],
  "output_contract": "string — exact expected output format/shape",
  "current_state": {"object with key live config/metrics/state needed for context"},
  "new_since_last_pass": ["list of upstream changes, blockers, or underdone areas from prior passes"],
  "budget": {
    "max_tool_calls": 30,
    "max_turns": 8
  }
}
```

Bare string constraints are legacy. Prefer objects with `binding` so handoff/compaction
cannot silently weaken must→maybe (arXiv:2608.24569). For long-horizon parents, keep
task progress in Working Memory (`working-memory.py`) and put only the skill-relevant
slice into the packet (Recuris arXiv:2608.24876).

### Field meanings

| field | source | notes |
|-------|--------|----------|
| objective | the user request, narrowed to this agent | one goal, not a list |
| scope_paths | files/dirs currently being worked on | keep tight — least privilege |
| constraints | memory, config, project conventions | hard rules only |
| prior_findings_refs | paths to previous agent outputs | paths, not inlined content |
| current_state | live config values, metrics, or environment state | assemble with live queries; saves agent rediscovery time |
| new_since_last_pass | upstream changes, gaps from prior passes, new threats | clarifies what the agent should prioritize over routine baseline |
| output_contract | the task requirements / downstream merge step | e.g. write a hermes-finding/v2 file |
| budget | complexity estimate | caps runaway agents |

## How to assemble

1. **objective** — extract from the user request; reduce to the single concrete
   goal this specific agent owns. If you can't state it in one sentence, the task
   is too broad — split it.
2. **scope_paths** — the files/dirs being worked on. Pass paths, never inlined
   file bodies; the agent reads them itself with least-privilege scope.
3. **constraints** — pull hard rules from durable memory, `hermes config`, and
   project conventions (style, security, "do not touch X").
4. **prior_findings_refs** — list paths to previous agent outputs under
   `~/.hermes/agent-workspace/` (e.g. `*.finding.json`). Reference, don't inline.
5. **current_state** — critical: query the actual live state before dispatch
   (config values, veto rule counts, delegation settings, etc.). Use `hermes config show`,
   grep counts, git log, or live Python interrogation to populate this. Saves the agent
   from re-discovering state that is already known and stable; agents working on multi-pass
   upgrades or iterative refinement particularly benefit from baseline values.
6. **new_since_last_pass** — list what changed upstream or what gaps/blockers emerged
   since the prior pass. This helps the agent prioritize — it knows to focus on new areas
   rather than re-certifying existing work. For iterative tasks, this clarifies the delta.
7. **output_contract** — derive from task requirements and the downstream merge
   step. When results must be merged, point at the `hermes-agent-sync` findings
   contract.
8. **budget** — set `max_tool_calls` / `max_turns` from a quick complexity
   estimate so a stuck agent fails fast instead of burning tokens.

## PrimeAgentOrchestrator — Memory-Primed Cold-Start Pattern (arXiv:2608.20342, Aug 2026) <!-- rationale: subagents start cold with no session context; priming from Hindsight/Graphiti at dispatch time avoids costly rediscovery -->

PrimeAgentOrchestrator solves the cold-start problem for LLM subagents: newly spawned agents
have no task-relevant context and must either rediscover it (expensive) or fail (wrong). The
paper formalises a **retrieval policy** that selects and compresses task-relevant context from
persistent memory at dispatch time — before the agent starts executing.

**Hermes context packet extension — add `memory_prime` field:**

```json
{
  "schema": "hermes-context-packet/v1",
  "objective": "...",
  "memory_prime": {
    "hindsight_recall_queries": ["query 1 relevant to this task", "query 2"],
    "graphiti_entities": ["entity name 1", "entity name 2"],
    "session_search_queries": ["past session keyword 1"],
    "max_facts_to_inject": 5
  }
}
```

**Assembly procedure (add to "How to assemble" step 5):**

Before dispatching, retrieve and inject the top-5 most relevant facts into the context packet directly. Don't make the subagent do the retrieval — it's more reliable and cheaper to prime at dispatch time:

```python
# Before delegate_task, prime with relevant memory:
relevant_facts = []

# 1. Hindsight recall for task-relevant facts
for query in memory_prime["hindsight_recall_queries"]:
    results = hindsight_recall(query=query)
    relevant_facts.extend(results[:2])  # top 2 per query

# 2. Graphiti entity lookup for structural knowledge
for entity in memory_prime["graphiti_entities"]:
    facts = mcp_graphiti_search_memory_facts(query=entity, num_results=2)
    relevant_facts.extend(facts)

# 3. Inject top 5 into current_state
context_packet["current_state"]["memory_primed_facts"] = relevant_facts[:5]
```

**When to use memory priming:**
- Subagent is working in a domain where Hermes has prior knowledge (tool quirks, environment facts, user preferences)
- Subagent task requires knowledge that would take 3+ tool calls to rediscover
- Fan-out with multiple agents doing similar tasks — prime all with the same base facts, differentiate by task

**When NOT to prime:**
- Truly novel tasks with no prior session context
- Read-only research tasks where fresh discovery is the goal
- When Hindsight recall returns empty or low-confidence results (better to not inject wrong facts than no facts)

**Scoring policy (from PrimeAgentOrchestrator):** rank candidate facts by (recency × task_similarity × importance). In Hermes terms: prefer recent Hindsight entries, prefer entries whose content overlaps with the task's key entities, prefer entries marked with `volatility_class: stable`. Inject only the top 5 — beyond that, diminishing returns and context bloat.

Reference: arXiv:2608.20342, "PrimeAgentOrchestrator: Memory-Primed Agent Spawning for Personal AI Instances", Aug 2026.

## MiniScope: formal permission hierarchy reconstruction (arXiv 2512.11147, UC Berkeley)

The minimal-permission tool set pattern above is heuristic. MiniScope formalizes it with
a rigorous security model at 1-6% latency overhead.

### Core mechanism: reconstructed permission hierarchies
MiniScope analyzes which tool calls are reachable from a given task and reconstructs a
"permission graph" — a DAG where edges represent tool call dependencies (calling tool A
requires capability B). This is more precise than static profiles because:
- A task requiring `read_file` + `web_search` does NOT need `terminal` even if the role
  profile includes it
- Dependencies between tools are captured (e.g. `browser_click` requires a prior
  `browser_navigate` session — they share a session ID dependency)
- Mobile-style runtime permission model: capabilities are granted just-in-time per
  task scope, not statically at agent spawn

### Practical Hermes application:
In the context packet's `constraints` field, use task-derived (not role-derived) scoping:
```json
{
  "tools_allowed": ["<derive from the task steps, not from a role profile>"],
  "permission_rationale": "task requires X → needs tool Y; no path to tool Z"
}
```

Checklist before spawning a subagent:
1. List the concrete steps the subagent will take
2. For each step, identify the exact tool needed
3. Check if any tool in the list enables a privilege escalation path (e.g. terminal can
   call anything; prefer read_file + write_file over terminal for file ops)
4. Add only those tools to `constraints.tools_allowed`

### Permission hierarchy patterns (from MiniScope Table 2):
| Task type | Minimum tools | Often mistakenly included |
|-----------|--------------|--------------------------|
| Research / summarize | web_search, web_extract | terminal, write_file |
| File editing | read_file, patch | terminal, web_search |
| Code execution | terminal (scoped workdir) | browser_*, memory |
| Crawling | firecrawl, web_extract | terminal, write_file |
| Code review | read_file, search_files | terminal, patch |

## Minimal-permission tool sets per subagent type

Inspired by awesome-claude-code-subagents (154+ Claude Code subagent definitions): each
subagent gets only the tools it actually needs, not the full tool catalog. Smaller tool
sets reduce instruction tokens and prevent the agent from taking out-of-scope actions.

Apply this when building a context packet: decide which tool categories the subagent
actually requires and state them explicitly in `constraints`.

Standard subagent tool profiles:

| Subagent type | Allowed tools | Deny explicitly |
|---|---|---|
| Research/analysis | web_search, web_extract, read_file, search_files | terminal, write_file, patch |
| Verification/QA | read_file, search_files, terminal (read-only cmds) | web_extract, write_file |
| Implementation | read_file, write_file, patch, terminal, search_files | web_search (scope creep risk) |
| Crawl/data-extract | web_search, web_extract, write_file | terminal, patch |
| Code-review | read_file, search_files | write_file, terminal, web_search |

In the context packet, add to `constraints`:
```json
{
  "constraints": [
    "Use ONLY these tools: web_search, web_extract, read_file, search_files",
    "Do NOT call terminal, write_file, or patch — out of scope for this agent",
    "If a needed action is outside these tools, note it in output but do not attempt it"
  ]
}
```

Why this matters:
- Implementation agents that also have web_search will drift to research instead of coding
- Verification agents that have write_file will make unreviewed changes
- Crawl agents that have terminal may spawn subprocesses or install packages
- Minimal permission = predictable scope = easier to review and debug the agent's work

## Token budget hint (TALE pattern, ACL 2025)

Add an explicit token budget hint to the objective when the task is bounded or
routine. This reduces unnecessary CoT verbosity by 30-40% without accuracy loss
(Token-Budget-Aware LLM Reasoning, arXiv:2412.18547).

Pattern: append `"Target response: ~N tokens. Prioritize signal over completeness."`
to the objective string for any agent where brevity > exhaustiveness.

- Research/exploration agents: ~2000 token target (detailed but bounded)
- Verification/smoke-test agents: ~500 token target (pass/fail + evidence)
- Summary/synthesis agents: ~1000 token target (structured, no padding)

Skip for: open-ended creative tasks, complex multi-step implementations, or tasks
where incomplete output would require a redo (false economy).

## AgentPrune: prune before fan-out (ICLR 2025)

Before dispatching a batch of agents with the same base context, apply one-shot
pruning on shared context elements:
- Remove any content from `current_state` that every agent will ignore
- Remove any constraints that don't apply to this specific agent's scope
- Remove `prior_findings_refs` paths the agent cannot act on
- Deduplicate any repeated facts between `constraints` and `current_state`

This mirrors AgentPrune (arXiv:2410.02506): spatial-temporal graph pruning of
communication redundancy. Applied here as: prune the packet to each agent's actual
scope before dispatch, not after arrival.

Rule: if you have N agents in a fan-out and the shared context is K chars, each
1% reduction saves N×K/100 chars. On a 5-agent fan-out with 4000-char packets,
removing 20% of irrelevant shared context saves ~4000 tokens total.

## Size check — the 2000-token rule

If the assembled packet exceeds **2000 tokens** (rough: >8000 chars):

1. First, trim `prior_findings_refs` from full content/long paths to
   **summaries only** — replace inlined or verbose refs with a one-line gist plus
   the path. The agent fetches detail on demand.
2. If still over budget, tighten `constraints` to hard rules only and narrow
   `scope_paths`.

Never pad a packet "just in case" — every extra token is paid once per agent in a
fan-out.

## Integration

- `hermes-role-pipelines` — assemble a context packet before each delegate in any
  pipeline/fan-out pattern.
- `hermes-agent-sync` — point `output_contract` at the structured findings
  contract when outputs must be merged.
- `hermes-swarm-consensus` — consistent packets make conflicting agent verdicts
  directly comparable during reduction.
- `handoff` + `working-memory.py` — on model/session switches, pass WM handoff-export
  + binding-typed constraints rather than full trajectories (Handoff Tax 2608.24358).
- Lint packets/handoffs: `python3 ~/.hermes/scripts/constraint-binding-lint.py <file>`

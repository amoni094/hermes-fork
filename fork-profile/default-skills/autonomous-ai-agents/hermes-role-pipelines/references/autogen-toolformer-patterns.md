# AutoGen speaker selection + Toolformer tool gating

Source papers: AutoGen (Wu et al., Microsoft, arXiv:2308.08155); Toolformer (Schick et al., Meta, arXiv:2302.04761).
Use this file when the parent is coordinating multiple specialist roles and must decide *who acts next* or *whether a tool/toolset is worth loading*.

Do not load this for post-fan-out verdict conflicts — that is `hermes-swarm-consensus`.

## AutoGen ≠ swarm-consensus

| | AutoGen GroupChat | Hermes swarm-consensus |
|---|---|---|
| When | During the work | After independent fan-out |
| Question | Who speaks next? | Which conflicting verdict wins? |
| State | Shared conversation; sequential turns | Blind ballots; no peer transcripts |
| Hermes owner | Parent as GroupChatManager | Deterministic reducer + optional arbiter |

GroupChat is turn-taking orchestration. Swarm-consensus is fan-in arbitration. Do not broadcast sibling reasoning during GroupChat turns if the next step is a consensus vote — that recreates DEAR echo chambers.

## Pattern: parent-as-GroupChatManager (speaker selection)

Hermes `delegation.max_spawn_depth` is 1. Children cannot talk to each other. The parent *is* the manager.

Loop (max 6 turns, then replan or ask-human):

1. **Select speaker** with a *role-play* prompt, not a task-only prompt.
   AutoGen's pilot (12 tasks): role-play speaker selection beat task-based selection (GPT-4: 11/12 vs 8/12 successes; fewer LLM calls). The selector must see role names + last artifact type + remaining objective — not a dump of the user request alone.
2. **Ask that speaker only.** One `delegate_task` leaf. Never fan-out the whole roster on a GroupChat turn.
3. **Do not broadcast the full reply.** Keep the transcript on the parent. The next speaker gets a compact `hermes-context-packet`:
   - `objective` = this speaker's next concrete action
   - `prior_findings_refs` = path to the last speaker's artifact (not the prose)
   - `new_since_last_pass` = what changed this turn
   - `output_contract` = typed handoff (`what_done`, `evidence`, `files_changed`, `unresolved_issues`)
     Note: do NOT include a numeric `confidence` field — use `unresolved_issues` for uncertainty (see Verification-Gated Escalation in SKILL.md).
4. **Terminate** when the last speaker emits a complete handoff with empty `unresolved_issues`, or when two consecutive speakers add no new evidence.

Role-play selector (parent, inline — do not spawn a selector child):

```
Roles: <name: one-line capability>... 
Last speaker: <role> produced <artifact type>.
Remaining objective: <one sentence>.
Pick exactly one next speaker whose capability is required NOW.
If none is required, return TERMINATE.
```

Allowed next-speaker policies:
- **role-play (default)** — AutoGen A5; use this
- **round-robin** — only for homogeneous critique rounds with Verbalized Sampling
- **task-listed** — only when the DAG is already frozen (then this is a Pipeline, not GroupChat)

Never use round-robin for mixed specialist work. Never let the last speaker pick the next speaker (first-mover lock-in).

### When to use GroupChat vs existing patterns

- Use **GroupChat / speaker selection** when the next role depends on the last artifact (code → critic → executor → critic…) and a static pipeline would over-dispatch idle specialists.
- Use **Fan-out / Fan-in** when investigations are independent (no shared conversation needed).
- Use **Pipeline** when the stage order is known before any work starts.
- Use **Supervisor** when the parent assigns *new* work items from a backlog; GroupChat assigns *who talks about the same work item*.
- Use **Expert pool** when most specialists are conditional *and* you will skip GroupChat entirely (one-shot dispatch).

AssistantAgent + UserProxyAgent pair maps to: LLM leaf (no `terminal`) + parent executing tools. Do not give the writer `terminal` if the parent/UserProxy will run the commands — AutoGen's split is the point (writer proposes, proxy executes).

## Pattern: task decomposition via conversation

AutoGen insight: complex tasks partition through dialogue, not a one-shot plan. Hermes equivalent:

1. Parent (or one planner leaf) produces a *provisional* DAG of 2–5 nodes. Stop. Do not pre-expand every possible expert.
2. After each completed node, the parent re-opens the conversation: keep / split / drop remaining nodes given the new artifact.
3. Nested AutoGen chats (agent holds outer chat, spawns inner chat) map to **serial parent waves**, not child-spawned `delegate_task`. Inner chat = new context packet, same parent, different speaker set.
4. Context-passing contract for nested/serial waves — this *is* the missing skill surface; use `hermes-context-packet` plus:
   - Pass **output artifacts**, never the inner transcript
   - Inner wave does not inherit the outer wave's toolset; set `enabled_toolsets` per wave
   - Inner wave does not inherit sibling findings except via `prior_findings_refs`
   - If the inner objective cannot be stated in one sentence, it is not nested — it is a new pipeline

Completion criterion: every DAG node is either done (handoff with evidence), dropped (one-line reason), or blocked (`ask-human`). No silent leftover nodes.

## Toolformer tool-gating (tools, not skills)

Toolformer keeps an API call only when `L_no_call - L_with_result ≥ τ` — the call must reduce next-token loss vs doing nothing *and* vs calling with an empty result. Humans are a bad oracle for this; the model's own future-token utility is the filter.

Hermes gap: `hermes-semantic-skill-routing` does predicted-utility selection for **skills**. `enabled_toolsets` still loads **every tool in a toolset**. There is no Toolformer-style filter at tool granularity.

Approximate the filter without logprobs:

1. **Spawn gate (toolset):** start with the map-guided minimum in `autonomous-ai-agents`. Add a toolset only if the next speaker's objective names a need that toolset uniquely covers. Research → `web`+`file`; code → `terminal`+`file`; critique → `file` only.
2. **Turn gate (tool):** before calling a tool, ask: *would the next decision be worse without this result?* If the parent can already complete the next tokens/handoff, skip the call. This is the Toolformer empty-result check: a call whose result you will ignore is a net loss.
3. **Escalate, don't preload:** if the leaf self-checks "cannot complete with current tools", add one toolset and retry once. Do not open with the union of all possible toolsets.
4. **Never put `delegation` on a GroupChat leaf** (depth-1). Never put `computer-use` or credential tools on a speaker that is only reading/critiquing.

Utility heuristic (parent, no extra model call):

```
Need this toolset? yes only if:
- the speaker's output_contract requires evidence this tool produces, AND
- that evidence is not already in prior_findings_refs / current_state
```

If both fail, omit the toolset. Idle tools are not free — they steal routing attention (ratel tool-overload; Toolformer: unused APIs still cost if present at decision time).

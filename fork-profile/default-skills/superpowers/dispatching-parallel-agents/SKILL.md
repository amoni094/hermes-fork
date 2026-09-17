---
name: dispatching-parallel-agents
related_skills:
  - using-superpowers
  - subagent-driven-development
  - autonomous-ai-agents
  - hermes-swarm-consensus
  - merge-reconciler
  - adversarial-review

depends_on: [using-superpowers]
provides: [fan-out-delegation, parallel-tasks, independent-workstreams]
triggers:
  - multiple independent investigations or workstreams that can run concurrently with no shared mutable state
  - user wants to parallelize research or implementation across 3+ subtasks with no inter-dependencies
  - fan-out delegation pattern needed (different failing tests, separate subsystems, independent research tracks)
  - user wants to parallelize verification work across isolated problem domains
description: Use when multiple independent investigations or implementation tasks can be delegated concurrently (fan-out, no shared mutable state). Not for choosing which multi-agent skill applies (use autonomous-ai-agents as router).
version: 1.0.2
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subagents, delegation, parallelism, orchestration]
    related_skills: [using-superpowers, subagent-driven-development, autonomous-ai-agents, hermes-swarm-consensus, merge-reconciler, adversarial-review]
---

# Dispatching Parallel Agents

Use one subagent per independent problem domain.

If the task is broadly about multi-agent orchestration and it is not yet clear which specialized agent/orchestration skill applies, load `autonomous-ai-agents` first as the router skill, then follow it to the right child skill.

## Good fit

- different failing test files with unrelated causes
- separate subsystems
- independent research tracks
- parallelizable verification work

## Bad fit

- shared mutable state
- overlapping file edits without coordination
- tasks that require the full parent context

## Worker Pool Sizing

Token budget acts as a queue capacity: when all agent slots are full, new tasks queue until a slot frees. Prioritise by expected value (highest-value task first). For same-turn bootstrap searches/extractions run in parallel, cap at 2 concurrent web_search/web_extract calls. This <30s path is where overloading causes non-linear slowdown. This cap does NOT apply to delegate_task children with expected runtime >30s — those are independent workers and should be parallelized freely.

## Lagrangian Budget Rebalancing (Luenberger Ch 7.7–8 — Dual Decomposition)

For N parallel subagents with a shared token/time budget B and per-subagent cost c_i:

**Optimality certificate (weak duality):** an allocation (c_1,...,c_N) with Σc_i = B is optimal iff each subagent's marginal output value equals the shadow price λ. Observable proxy: completion_fraction_i = actual_tokens_used_i / allocated_budget_i.

**Rebalancing rule (no new infrastructure required):**
```
if any agent has completion_fraction < 0.5 AND another has completion_fraction > 0.95:
    # dual gap detected: allocation is suboptimal
    surplus = allocated_budget[fast_agent] - actual_used[fast_agent]
    reallocate: reduce fast_agent budget by min(surplus, 0.3 * allocated_budget[slow_agent])
    add to slow_agent budget
```

**When to apply:** only when the same-type subagents (similar task complexity) show ≥2× difference in completion fraction. Do NOT rebalance heterogeneous tasks (research vs implementation have different natural completion fractions).

**Dual infeasibility signal:** if a subagent consistently overruns its budget (completion_fraction > 1.0), the primal problem is infeasible — the task complexity exceeds the budget constraint. Do not keep reallocating; instead decompose the task further or reduce scope.

**Composability with Pandora sizing:** Pandora Dispatch Sizing (math-005) determines k* (how many agents to dispatch). This rule operates AFTER dispatch to rebalance within a fixed k — they are complementary.

## Pandora Dispatch Sizing (math-005) — SPIKE_PARTIAL

Spike result: fixed k=3 beats greedy when reviewer quality variance is low. Live T/q measurement needed before fixed k can be set. Do not apply fixed k=3 or p-threshold rules until variance is measured per reviewer pool. Status: SPIKE_PARTIAL — blocked on live reviewer accuracy ledger. Revisit trigger: cobra-outcome-logger has labeled reviewer-accuracy data.

## Role-Boundary Declaration (arXiv:2609.03111 Role Drift + arXiv:2609.09133 ExecCritic, Sweeps 31+33)

Role drift in hierarchical MAS compounds with delegation depth. Empirical: executor agents begin making strategic decisions, reviewers begin proposing fixes — causing compounding errors and reduced trust in synthesis.

**Mandatory role declaration in every delegate_task goal:**
```
Your role is [executor | planner | reviewer].
You MAY: [specific permitted action types for this role].
You MAY NOT: [boundary actions — the actions of the OTHER roles].
```

**Role-specific boundary actions (enforce in synthesis, not just prompt):**
- **executor** MAY NOT: change task scope, reject the overall approach, skip steps
- **planner** MAY NOT: execute tool calls that modify state, write final output directly
- **reviewer** MAY NOT: propose code changes, modify files, re-scope the task

**Boundary violation detection (lightweight synthesis check):**
```
if role == 'reviewer' and output contains code_diffs:
    trust_weight = 0.5  # boundary violation — reviewer proposed changes
    route_through_coordinator_before_applying()
if role == 'executor' and output contains scope_change_language:
    trust_weight = 0.5  # executor re-scoping without authorisation
    flag_for_parent_review()
```

**Depth amplification:** at delegation depth ≥ 2 (subagent dispatching further subagents), re-state role boundaries explicitly in the sub-delegation goal. Role drift compounds with depth — do not assume the original role constraint propagates automatically.

**LLM observer caveat (ExecCritic, Sweep 33):** do not use an LLM-as-judge in the same context window to detect role drift — same-window observer ranking agreement is only Spearman 0.40. Use the structural boundary violation check above (code_diffs / scope_change_language) which is deterministic.

## Hermes process

1. Partition the work into independent domains.

## Hermes process

1. Partition the work into independent domains.
   **Optional but valuable when the decomposition itself is non-obvious** (6+ parallel
   clusters, genuinely ambiguous topic boundaries, or the user explicitly asked for an
   escalated orchestrator): before dispatching, get a critique of your proposed cluster
   list from a stronger model — don't just dispatch your first-draft split. `delegate_task`
   has no per-task model override in this environment (children use `delegation.model`,
   currently whatever `delegation.model` is set to — they do **not** inherit the parent session model);
   the way to get an Opus-tier decomposition check without pinning every worker to
   Opus is a one-shot `terminal` call to a separately-invoked `hermes chat` process, e.g.
   `hermes chat -q "critique this decomposition: <list clusters>. What's missing, what's
   redundant, what should be added?" -m <escalation model from claude-routing-hierarchy> --provider anthropic -Q`. This
   matches `claude-routing-hierarchy`'s escalation policy (escalate the decomposition/
   reconciliation step only, not the whole pipeline) — keep every dispatched worker on the
   default leaf, spend the escalated call only on the plan review. Confirmed useful July
   2026: a 6-cluster research-topic split got a critique flagging 3 missing comparator
   regimes and a redundant pairing between two clusters before dispatch, which would have
   otherwise required a second dispatch round to catch after the fact. The subprocess call
   also prints a benign trailing stack trace to stderr on exit (`Exception ignored in:
   <coroutine object MCPServerTask.run ...>` / `RuntimeError: Event loop is closed`) —
   cosmetic asyncio-teardown noise, not a failure; ignore it.
2. Give each subagent a self-contained goal, context, constraints, and expected output.
   State the expected **output artifact type** explicitly (e.g. JSON findings, diff,
   summary paragraph) — this enables downstream routing without hardcoded pipelines.
3. Launch them in a single `delegate_task(tasks=[...])` batch when possible. **Simultaneously run 2–4 targeted bootstrap searches or extractions in the same turn** — these confirm key anchors (papers, GitHub repos, tool versions, key facts) before the subagents return. This guards against the subagents returning empty-handed on the most important leads, and gives the orchestrator independently-verified anchors to use during synthesis. Don't wait for subagents to do all the discovery; use the dispatch turn productively. Confirmed July 2026 (neurosymbolic AI research): dispatching 3 subagents + running 2 web_searches + 2 arXiv web_extracts in the same turn confirmed 3 key papers independently before any subagent completed.
4. On results: pass only the **output artifact** to downstream stages, not the full subagent transcript. If a downstream stage needs context, attach a compact context packet — not a raw conversation dump.
   **Result size control:** if a subagent's output will be large (multi-page vision audits, bulk research), tell it to write findings to a file (e.g. `/tmp/result-TASKNAME.txt`) and return only the path. The parent reads with `read_file(offset=..., limit=...)` in chunks. This prevents the result landing as a large atomic message that overflows the parent context window.
5. **Cross-agent integration gap (CRITICAL):** When one agent produces a build artifact
   and another produces research findings, the build agent cannot see the research agent's
   results — they have isolated contexts. After both complete, the orchestrator MUST:
   - Read all research outputs
   - Identify findings the build agent couldn't have known (new data, proxy caveats, key differentiators)
   - Patch those findings into the build artifact directly before declaring done

   Common failure mode: build agent produces a technically correct artifact missing the
   most important domain finding, because it only had the spec. The research agent returns
   the key result, but it sits unintegrated in a separate file. Only the orchestrator can
   close this gap — it is not automatic.

6. Before synthesising fan-out results, score each output 1–3 (not useful / partial /
   essential). Weight or exclude scores below 1.5 from synthesis.
   **Adversarial verification of subagent claims:** subagents often use proxy heuristics
   (grep, count, pattern-match) to reach structural conclusions. These produce false
   positives that look authoritative. Before acting on a finding like "15 files have broken X"
   or "N% of Y are misconfigured", verify by direct inspection (parse the actual structure,
   read the actual files) rather than trusting the reported count. See adversarial-review
   for the concrete structural-parse pattern.
   **When multiple subagents reach conflicting *epistemic* verdicts** (e.g. they disagree on facts or confidence, not on which action to take), load `hermes-swarm-consensus`.
   For cross-agent contradictions on factual outputs, load `merge-reconciler`.
7. Independently verify any claimed side effects before reporting success.
8. After results arrive, record a topology note in `~/.hermes/agent-workspace/topology-memory.md`
   using the Preserve / Modify / Avoid format defined in `hermes-role-pipelines`.

## Pitfall: template marker injection in goal/context strings

The `delegate_task` renderer detects two families of unexpanded template markers and refuses to dispatch if it finds one:

**Angle-bracket placeholders** (e.g. `<Full Title>`, `<slug>`, `<NN>`) — two distinct sources:
- *Forgotten template field* (copying from a skill/doc): `Task 0 goal contains an unexpanded template marker ('<Full Title>'). Substitute the real value before calling delegate_task.`
- *Pseudocode notation* — angle-brackets used to denote a slot in inline Python-style pseudocode inside the goal/context string, e.g. `session_type: <classified type>`. The renderer treats these identically to template fields and refuses. Error: `Task 0 goal contains an unexpanded template marker ('<classified type>').`

  **Fix for pseudocode notation:** Replace `<classified type>` with a concrete example value (e.g. `'research'`) or a description string (e.g. `"the session_type string (e.g. 'research', 'code', 'mixed')"`). Never use angle-bracket syntax for slots inside goal/context strings — they fire the same guard regardless of intent.
- Always scan goal/context strings for any `<Word>` patterns before dispatching. Substitute every one with its real value or a concrete example.

**Curly-brace placeholders** (e.g. `{variable}`, `${HOME}`) — fires when:
- The goal or context contains Python f-string literals (e.g. `f'/proc/{pid}/stat'`)
- Shell variable references (e.g. `${HOME}`, `${CONTAINER}`)
- Any curly-brace syntax from code examples, config snippets, or JSON inline in the prompt
- Error: `Task 0 goal contains an unexpanded template marker ('{variable}'). Substitute the real value before calling delegate_task.`

Workarounds (in order of preference):
1. Write the goal/context as a file (`write_file('/tmp/task-goal.txt', content)`) and reference it as context: `"Read the goal from /tmp/task-goal.txt"`. Best for code-heavy context.
2. Build the string in `execute_code` with explicit escaping (double braces: `{{` and `}}` for literal braces) and pass the result to `delegate_task`.
3. For short snippets: replace all `{` with `(` and `}` with `)` in code examples inside the prompt, with a note that it's pseudocode.

Never hand-compute curly-brace counts — write a check:
```python
import re
if re.search(r'\{\w+\}', goal_text):
    raise ValueError("goal contains template markers; escape or file-offload before dispatch")
```

## Interaction Tax — Independent Proposals Before Full Exchange (arXiv:2608.23541) ★ HIGH <!-- why: full-solution exchange collapses multi-model diversity within one round; independent proposals preserve the reason you spawned multiple agents -->

Different model families find structurally different solutions, but when agents read each
other's *complete* outputs their proposals converge within one round — erasing the diversity
that justified multi-agent dispatch. That cost is the **interaction tax**.

**Hermes rule for parallel `delegate_task`:**
1. Dispatch workers with **isolated contexts** (default). Do not inject peer full solutions
   into sibling `context=` fields mid-batch.
2. Collect **independent proposals** first (findings JSON / short verdicts / ranked options).
3. Only then run a **bounded synthesis** step (parent or one synthesizer leaf) that sees
   the proposal set — not iterative full-solution debate between peers.
4. If a second round is needed, pass **deltas / disagreements / open questions**, not the
   entire prior peer transcript.
5. Same-model panels already co-fail (phi≈0.9); full-solution exchange makes that worse.
   Prefer model diversity OR independent sampling + parent merge over peer-to-peer critique loops.

**Anti-pattern:** chain A→B where B's `context=` is A's full answer "so B can improve it"
on the first pass. That burns the diversity budget immediately.

## Reasoning Type Selection Before Dispatch

For L2+ tasks, run select-frameworks before writing task goal files. The output determines which reasoning gates each subagent should invoke:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<overall fan-out goal>" --level <L>
  ```
  Include the primary framework list in each subagent context packet so workers apply the right gates.

After fan-out, if subagents return conflicting *action* verdicts (PROCEED vs BLOCK)
on the same gated step, run conflict-resolve first. Do NOT also send that pair
into hermes-swarm-consensus — that skill is for multi-agent *epistemic* disagreement
(what is true), not for framework action-verdict conflicts. Swarm-consensus may
mention conflict-resolve as a pre-wire; that is one-way, not a circular call.
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py conflict-resolve \
    --framework-a lookahead --framework-b boundary-check \
    --verdict-a '<agent-A verdict json>' --verdict-b '<agent-B verdict json>' \
    --task "<question>"
  ```
  Then, only if agents disagree on facts/confidence (not action gates), apply
  hermes-swarm-consensus. Route: action-verdict → conflict-resolve; epistemic → swarm.

## NP-Completeness and Approximation in Task Assignment (CLRS Ch 34)

**Theory:** Task lane assignment is a set-partition problem (NP-hard, CLRS Ch 34 — Partition Problem reduces to Subset Sum, both NP-complete). Optimal assignment across heterogeneous agent lanes cannot be computed efficiently for N > ~20 tasks.

**Hermes rules:**
- Use greedy earliest-deadline-first (EDF) as a 2-approximation: assign each task to the lane with the earliest current completion time. This guarantees at most 2× the optimal makespan.
- Do NOT attempt exhaustive optimal assignment; the combinatorial explosion outweighs any gain for N > 10 tasks.
- For homogeneous lanes (same task type, similar complexity), EDF degrades to round-robin — acceptable and O(N).

**Citation:** Cormen, Leiserson, Rivest, Stein — *Introduction to Algorithms* (4th ed.), Ch 34 (NP-Completeness); Ch 16 (Greedy Algorithms — activity selection as EDF base).

## Theory-Grounded Dispatch Allocation (cross-reference)

For formal grounding of allocation decisions: Luenberger projection theorem (closest-skill assignment), Lagrangian shadow-price token budgeting, and separability pre-check are in luenberger-vector-space-optimization. Kreyszig operator-norm routing stability (load top-2 on routing ambiguity) is in kreyszig-functional-analysis. Load those skills when the task requires formal allocation bounds, not just heuristics.

## Node Prompt Contract (from OMH ultrawork discipline — mandatory for implementation lanes)

Every implementation lane prompt must contain these five markers in order (this extends the general Prompt pattern section below with mandatory structure for multi-agent implementation work):

1. TASK: one imperative assignment
2. DELIVERABLE: the exact artifact or result
3. SCOPE: exact read/write file boundaries and forbidden changes
4. VERIFY: the literal command or action plus one binary pass/fail observable
5. STOP WHEN: the observable state that ends the lane

Missing markers, vague scopes, or non-binary verification are definition defects — fix before dispatch. For general research or single-agent tasks, the lighter Prompt pattern section below is sufficient.

Shape selection before dispatch:
- One owner: work coupled by a shared invariant or inseparable edit boundary
- Ordered dependency edges: separable work whose downstream unit cannot start until named producers finish
- Dependency-ready parallel frontier: independent units with disjoint write scopes

One unit owns a deliverable end to end, including its proof. Never split implementation and tests for the same files across concurrent owners.

## File-Ownership Map Before Dispatch (mandatory for implementation waves)

Before dispatching any batch where agents write to files, build an explicit ownership map:

```python
from collections import defaultdict
ownership = {
    "Agent-A": ["scripts/foo.py", "skills/skill-a/SKILL.md"],
    "Agent-B": ["scripts/bar.py", "scripts/baz.py"],
    "Agent-C": ["config.yaml", "skills/skill-b/SKILL.md"],
}
count = defaultdict(list)
for agent, files in ownership.items():
    for f in files:
        count[f].append(agent)
conflicts = {k: v for k, v in count.items() if len(v) > 1}
if conflicts:
    raise ValueError(f"FILE CONFLICTS before dispatch: {conflicts}")
```

Assign each file to exactly ONE agent. If two findings both need the same file,
merge both into a single agent's scope — do not dispatch them separately.
Do this check BEFORE writing goal files or dispatching; fixing it after dispatch
requires steer/stop, which is lossy.

## Concurrent same-.py file patch conflict (parallel implementation waves)

**Steer-to-read-first pattern (for in-flight same-file conflicts):**
If two agents are writing to the same .py script and the conflict is detected mid-flight,
steer the LATER agent immediately via `delegate_task(action='steer', ...)`:

  'Read CURRENT state of <script.py> before writing — another agent has already patched it.
   Use the patch tool for targeted edits only, not full-file rewrite.'

Send the steer as soon as the conflict appears in the live transcript. By the time the
agent finishes its first write, the overwrite may already have happened.

When multiple implementation agents target the SAME Python script with DIFFERENT
patches (e.g. one adds retrieval_value to l1-extract.py, another adds hash-chain
to l1-extract.py), the second agent patches OVER what the first wrote. Unlike the
SKILL.md conflict above (which produces incoherent interleaving), same-file .py
patches that don't touch the same function typically succeed but whichever runs
second silently loses the first agent's changes if it does a full-file rewrite,
or produces a double-patched mess if both use targeted patch().

Prevention:
- Before dispatching implementation batches, map each Finding → Target File →
  Agent and confirm no file appears in two agents' scopes.
- If two findings target the same file, merge both into a single agent's scope.
- If batches are already dispatched and overlap is detected, use
  `delegate_task(action='steer', message='skip <filename>, already being patched
  by another agent')` to redirect the second agent.

This is distinct from the SKILL.md interleaving case: SKILL.md conflicts produce
corrupt merged content; same-.py conflicts produce silent overwrites where the
first agent's changes disappear. Both require exclusive per-file ownership.

## Concurrent same-SKILL.md patch conflict (parallel skill synthesis)

**Pre-dispatch scope conflict check (mandatory before any skill-patch fan-out):**
Build a cluster→target-skill map and scan for duplicates before dispatching:

```python
from collections import defaultdict
cluster_targets = {
    "SA-0": ["skill-a", "skill-b"],
    "SA-1": ["skill-b", "skill-c"],  # skill-b conflict!
}
count = defaultdict(list)
for agent, skills in cluster_targets.items():
    for skill in skills:
        count[skill].append(agent)
conflicts = {k: v for k, v in count.items() if len(v) > 1}
if conflicts:
    raise ValueError(f"SCOPE CONFLICTS — merge before dispatch: {conflicts}")
```

Do NOT try to steer mid-flight; by the time a conflict is detected from a live log the
second agent has already begun patching.

**Post-dispatch detection (if conflicts slipped through):** After all agents complete,
check each conflicted skill for `###` subsections under an unexpected `##` parent.
This is the canonical signature of concurrent-write interleave: one agent's section
became a nested child of the other's instead of a peer. Promote the misplaced section
from `###` to `##` to restore correct peer hierarchy.

When multiple synthesis subagents are each tasked with patching the SAME skill file
(e.g., two agents assigned overlapping clusters both update `agent-memory-consolidation`),
the result is not a merge — it is incoherent interleaving. The second agent's `skill_manage
patch` operates on what the first agent left, producing: duplicate section headers, conflicting
instructions in adjacent paragraphs ("distill into a skill file" vs "do not auto-patch skills"),
and mismatched version numbers.

This is categorically different from the output-file write-timing pitfall below. That one is
about last-writer-wins on fresh content. This one produces content that is BOTH writers' changes
simultaneously, incoherently merged.

**Observed Aug 2026:** Agents A and F were both assigned to patch `agent-memory-consolidation`.
A patched it first (v1.10.1). F read the skill, then patched over A's changes (nominal v1.10.0).
Result: duplicate MemSIF sections, contradictory AMD guidance, two conflicting `context=` uses,
and empty stub headings that one agent added and the other ignored. An adversarial review agent
found 3 CRITICALs and 2 MAJORs in the merged result.

**Prevention:**
- Assign each skill to AT MOST ONE synthesis agent. If two clusters have findings for the same
  skill, merge those findings into a single agent's scope before dispatch.
- Alternatively: use the gather-then-synthesize pattern — gather agents write raw findings to
  separate files; one reconciling agent reads all findings and writes a single coherent patch.
- When assigning 5+ agents that all touch the skill library, pre-map cluster → target skills
  and verify no skill appears in two agents' scopes before dispatching.

**Recovery pattern when it happens:**
1. Read the corrupted skill in full
2. Identify which sections came from which agent (usually visible by content theme)
3. Dispatch ONE repair agent with: full adversarial report + the corrupted skill + explicit
   instruction to produce ONE coherent version (not to re-patch, but to rewrite the affected sections)
4. Verify the repair with a second adversarial read before considering it done

## Write-timing conflict pitfall (parallel writes to shared files)

When multiple subagents write to the same file (e.g. a shared findings.md or blackboard),
the last writer wins and earlier results are silently overwritten. Use `hermes-agent-sync`
for structured parallel-write patterns: typed JSON findings + blackboard apply step that
merges results idempotently rather than overwriting.

When the orchestrator dispatches subagents AND also writes to files in the same turn,
both sets of writes can land on the same files in unpredictable order. Observed Jul 2026:

- Orchestrator dispatched 3 subagents (memory, workflows, skills files)
- Orchestrator also wrote its own versions of those files in the same turn
- Subagents completed later and overwrote the orchestrator's files
- Git commit then captured the subagents' versions (longer, richer content)
- The orchestrator's writes were silently clobbered, producing a confusing file-size discrepancy

**Rule:** If you dispatch subagents to write file X, do NOT also write file X yourself in the
same turn. Pick one author per file: either the subagent writes it, or the orchestrator writes it.

**Pattern when you want orchestrator + subagent content in the same file:**
- Subagents write their sections to separate files (e.g. `memory-draft.md`, `workflows-draft.md`)
- Orchestrator merges after all subagents return
- Never let two writers target the same path concurrently

## Reasoning-model proxy timeout (deep-reasoning models on large tasks)

Deep-reasoning models (for example grok-4.6) hold an idle thinking phase before emitting the
first content token. If this exceeds the upstream proxy's idle timeout (typically 120s for
first byte), the session produces no SSE events and fails with `[Errno 32] Broken pipe`
or `Codex stream produced no SSE events for 120s after first byte`.

**Pattern:** fails on tasks with broad scope (10+ sub-topics, 3+ source types, 30+ tool
calls). Each worker independently times out — all 3 fail in the same batch.

Mitigation in priority order:
1. **Before re-dispatching a failed spike, check if it is pure computation.** If yes,
   run it directly in `execute_code` — same Python code, no delegation overhead, no
   stream-stall risk. This is almost always faster and always more reliable.
   A task that failed 2+ times with `Codex stream produced no SSE events` is a strong
   signal the task is too narrow/mechanical for a reasoning model: run it locally.
   **Do not re-dispatch a stalled spike a third time.** Two stall failures on the same
   task means the task shape is incompatible with the reasoning model's idle phase; every
   subsequent re-dispatch will stall for the same reason. Convert to execute_code instead.
2. **Do not delegate large research surveys to deep-reasoning workers.** Use execute_code
   with batched web_search + web_extract calls directly — faster, zero delegation overhead,
   same quality for structured research with clear sub-topic lists.
3. If delegation is needed, cap each task to a single domain (≤5 sub-topics) and increase
   `stale_timeout_seconds` on that provider/model in config (example key shape:
   `providers.<provider>.models.<model>.stale_timeout_seconds: 900`).
4. Route research sub-tasks to a non-reasoning `delegation.model`; reserve a reasoning
   model only for tasks that require deep synthesis.

**Rule of thumb:** if the task fits in a well-structured execute_code Python script (batched
searches, extractions, a write_file at the end), do it directly. Delegate only when the task
requires genuine multi-turn tool-call reasoning that cannot be scripted.

## Loop-cap and retry pitfalls

Two distinct failure modes produce thin or empty subagent output files:

| Signal | Loop cap | Context exhaustion |
|--------|----------|--------------------|
| api_calls | <15 | >15 |
| todos status | incomplete | complete |
| log endpoint | mid-research, no write_file | after todos done, no write_file |
| cause | repeated same query hits guardrail | ran out of tokens before final write |
| fix | add "at most 2 attempts per topic, vary queries" | add "CRITICAL: write file before stopping" |

### Check-before-retry (mandatory)

Before dispatching a retry, always run:
```
terminal("wc -l /tmp/<output-file>.md")
```
A batch result may be delivered before a subagent's late `write_file` completes. The output
file may already exist and be complete by the time you check. Retrying without checking produces
a redundant shorter version that can overwrite the richer original.

### Loop-cap retry prompt additions

When a subagent hits a loop cap, add ALL THREE of the following to the retry prompt:
1. "For each topic, make at most 2 web_search attempts with different queries, then move
   on. If results are off-topic, change query immediately or skip and note [SEARCH FAILED].
   Do NOT retry the same query twice in a row."
2. "Total tool calls budget: 30 max."
3. "CRITICAL OUTPUT STEP: After all research, write the output file using write_file.
   Then confirm: terminal('ls -la /tmp/<output-file>.md'). Do not stop before this step."

### Non-English query garbage returns

Arabic, Korean, Polish, and some Eastern European queries against general search providers
frequently return weather data, medical results, or completely unrelated content.

- Do NOT retry the native-language query; switch immediately to English-language equivalent
- Most non-English academic papers are indexed in English anyway
- Note [SEARCH FAILED - off-topic results] and move on
- Allocate at most 2 total attempts (1 native-language, 1 English fallback)

### web_search provider not inherited (from references/subagent-web-search-pitfalls.md)

Subagents do **not** inherit the parent's `web_search` provider. If parent uses `brave` / `brave-free`, child `web_search()` can fail with "no registered web search provider has that name", retry until `same_tool_failure_halt`, and return empty (~80s wasted).

Put this in every research subagent context: on first provider-not-registered failure, do **not** retry web_search more than twice — switch immediately to SearXNG:

```python
import subprocess, json
r = subprocess.run(
    ['curl', '-s',
     'http://localhost:8888/search?q=YOUR+QUERY+HERE&format=json&engines=braveapi,bing'],
    capture_output=True, text=True)
results = json.loads(r.stdout).get('results', [])
```

URL-encode queries (spaces → `+`). Port 8888. Diagnose "stalled" research by checking `~/.hermes/cache/delegation/live/deleg_<id>/task-*.log`: `status=completed` means parent is waiting on delivery; `I stopped retrying` means loop-cap empty return; no final line means still running or crashed.

## Recovering subagent output after /tmp is cleared

Subagents commonly write results to /tmp files. Those files are lost after a reboot or
new session. If you need to reconstruct what a past delegation batch produced:

1. Find the delegation batch ID from session_search — look for `deleg_<id>` in tool call args.
2. Check `~/.hermes/cache/delegation/` for two artifact types:
   - `subagent-summary-<N>-<timestamp>.txt` — the subagent's final summary (preserved)
   - `live/deleg_<id>/task-<N>.log` — the full tool+assistant trace (also preserved)
3. Grep the logs for arXiv IDs, URLs, or titles to reconstruct paper/link lists:
   ```
   grep -oP '"(title|url)": "[^"]+"' ~/.hermes/cache/delegation/live/deleg_<id>/task-N.log | sort -u
   grep -oP '\d{4}\.\d{4,5}' ~/.hermes/cache/delegation/live/deleg_<id>/task-N.log | sort -u
   ```
4. The subagent-summary files survive across sessions and contain the final synthesized
   output — read those first; fall back to the live log only for detail not in the summary.

   **Critical: log tails are unreliable — large execute_code outputs are truncated (Aug 2026).**
   The `.log` files store `execute_code` tool results with a `(+NNNN chars)` truncation marker
   when output exceeds the log buffer. Reading the last 1500–3000 chars of a log will miss the
   full structured report. Always read the `subagent-summary-N-<timestamp>.txt` file for the
   final report; use the log only for intermediate step tracing. The summary files are at
   `~/.hermes/cache/delegation/subagent-summary-N-<timestamp>.txt` — one level above `live/`,
   NOT inside it. Find them with:
   ```python
   import glob
   glob.glob('/var/home/rainbow/.hermes/cache/delegation/subagent-summary-*-<timestamp>*.txt')
   ```
   The timestamp in the filename matches the delegation batch start time from the manifest.

Pitfall: `/tmp` JSON output files from subagent write_file calls are gone after session end.
The delegation cache is the durable fallback. Always check there before re-dispatching.

## Specialist Compilation vs. General Dispatch (arXiv:2608.08995, Aug 2026)

Recurring parallel subtask patterns should be *compiled* into purpose-built specialist
prompts rather than re-decomposed from scratch each time (Muscle Memory for Agents).

Signal: when you dispatch the same task shape 3+ times (e.g., "search arXiv for papers
on topic X", "review SKILL.md for Y", "verify Z in N files"), crystallize that into a
reusable subagent prompt template or a dedicated skill rather than re-prompting ad hoc.

The 4-phase compile pipeline:
1. Harvest — identify recurring intent in past delegate_task calls via session_search
2. Analyze — separate task pattern (what) from behavioral pattern (how the user wants it)
3. Augment — write a skill/template with two-stage trigger matching (topic + output-shape)
4. Evaluate — hold out 3 test scenarios; fire the specialist; verify it wins vs. ad hoc

This applies to dispatch templates too: if you write nearly identical child prompts for
a fan-out, factor the shared structure into a template once and vary only the parameters.
Empirical: 88.9% win rate when a compiled specialist fires vs. generic orchestration.

## Prompt pattern

Each child prompt should include:
- exact scope
- relevant files/errors
- hard constraints
- expected return format
- required language/tone if non-default

**Control-data flow separation (arXiv:2609.00621):** Keep execution-critical **control** as typed, validated objects — output schema, role bounds, tool allowlist, stop/timeout, `enabled_toolsets` — not in the same prose blob as task **data** (what to research/build/review). Prompt edits and peer summaries may rewrite language; they must not be able to rewrite protocol. Put control in a labeled block or JSON contract the child cannot silently drop. Entangling them lets a content tweak corrupt routing/format/termination.

<!-- why: control vs data entanglement in child prompts raises novel-task failure when any later summary or optimizer touches the prompt -->

**Skill-script coverage discipline (Aug 2026):** When a subagent task involves a loaded
skill that has `scripts/` support files (e.g. the `arxiv` skill's `search_arxiv.py` or
`ai_research_search.py`), verify the subagent prompt explicitly names those scripts. "Use
the arxiv skill" is ambiguous — a subagent will often use `web_extract(arxiv.org/abs/ID)`
directly (id-based fetch, which works) without running the keyword-discovery scripts.
These are distinct capabilities: id-fetch requires knowing the paper ID; keyword-discovery
requires running the skill's scripts against search_query endpoints. When keyword discovery
is the goal, name the script path explicitly: `python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py`.
The user surfaced this gap in session Aug 12 2026 by asking "did you include sources from
the arxiv skill?" — the subagents had used the correct fetch path but skipped keyword
discovery because the prompt said "use the skill" without specifying which mode.

For implementation-heavy parallel work, prefer `subagent-driven-development`.
For role-selection or orchestration-pattern questions, prefer `autonomous-ai-agents` followed by `hermes-role-pipelines`.

## Research-gather vs synthesis split (large multi-source research tasks)

When subagents must gather data from many sources AND synthesize it, they frequently
timeout after gathering — large tool results fill context before the synthesis write.
Symptom: subagent sessions end with a small "next I'll synthesize" message and no output.
Repeating the same instructions repeats the same failure.

Fix: split into two explicit phases.

Phase 1 — Gather (subagents write raw data to files, not to return value):
- Each gather agent: read N sources, write raw content to `~/.hermes/cache/<task>/cluster-N.txt`
- Final return value: ONE line — "Gathered N sources, wrote to <path> (X bytes)"
- No synthesis, no summary — just data capture

Phase 2 — Synthesize (fresh subagents read files, produce findings only):
- Each synthesis agent: read_file(<path>), do NO additional searches, write findings
- Prompt explicitly caps context use: "read the file at <path> ONLY; do not do web searches"
- Write-first instruction: "write a skeleton summary first, then fill gaps in a second pass"

Parent verification between phases:
```python
import os
for f in cluster_files:
    sz = os.path.getsize(f)
    assert sz > 10000, f"Gather incomplete for {f}: only {sz} bytes"
```

Alternate entry: if prior subagent sessions already gathered data and timed out before
synthesizing, their research data is in state.db (not lost). Extract it with execute_code
+ sqlite3 before re-dispatching. See stalled-session-recovery § Recovering Orphaned
Subagents via DB Triage for the extraction pattern.

## Large corpus synthesis pattern (from references/large-corpus-synthesis-pattern.md)

When synthesizing 50+ episodes, 30+ papers, or any corpus that overflows context:
1. **Partition by semantic arc, not by count**: historical/diagnostic arc, technical/theoretical arc, constructive/proposal arc, responses/critics arc. Arc partitions let each subagent build internal coherence naturally vs arbitrary N-episode chunks
2. **Dispatch 3 subagents in parallel** — each gets: its URL/source list, exact output schema, explicit call-out for sections needing special depth, expected artifact (JSON/concatenated summaries)
3. **CRITICAL — Read full output files before synthesizing**: subagent outputs are truncated in parent context. Every time a subagent finishes: look for `Full subagent output saved to: /path/file.txt`, call `read_file(path=..., limit=2000)`, page with `offset` for files > ~44KB. **Do not synthesize from the inline truncated result** — the middle is cut and is typically the theoretical core
4. Run adversarial pass on the **synthesis** (not subagent outputs); then run a second adversarial pass after integrating external critique (the integration itself introduces new failure modes)

## Backend verification (from references/backend-verification.md)

When verifying which search backend a subagent actually used:
- SerpAPI results always include `"position": N` (Google organic rank); DuckDuckGo/ddgs results never do
- Check delegation logs: `grep -c '"position"' ~/.hermes/cache/delegation/live/${DELEG_ID}/task-N.log`
- `pos ≈ calls` → SerpAPI confirmed (1–2 gap is normal for CyberLeninka/J-STAGE hits); `pos = 0` → ddgs fallback
- Full confirmation requires: (1) `hermes config get web` → `search_backend: serpapi`, (2) config mtime before dispatch, (3) `grep -c SERPAPI ~/.hermes/.env` non-zero

### Branch context not inherited by subagents (fork/worktree workflows)

Subagents do NOT inherit the parent's current git branch. A subagent spawned while the
parent is on a feature branch will find itself on `main` (or detached HEAD at the default
branch tip) unless the branch is explicitly stated in the task context.

**Symptom:** Subagents make file edits but the test suite or live behavior reflects the
wrong code; git log in parent shows commits on the wrong branch; steer mid-flight needed.

**Rule:** When dispatching subagents that write files in a git repo:
1. Always include the branch name and working directory in `context=`:
   ```
   Working directory: /path/to/repo
   Branch: feature/my-feature-branch (verify with: git checkout feature/my-feature-branch)
   All edits must land on this branch — run git branch --show-current first.
   ```
2. Tell the subagent to verify the branch as its FIRST action before any reads or writes.
3. If you detect a branch mismatch mid-flight (from live transcript logs), steer immediately:
   `delegate_task(action='steer', message='IMPORTANT: You are on the wrong branch. Run: cd /path/to/repo && git checkout <branch> before making any changes.')`

**Prevention cost is zero** (5 extra lines in context); recovery cost is non-trivial (steer
mid-flight is lossy if edits already landed on the wrong branch).

## Subagent config write blocked by security guard

Hermes security guard refuses `patch` and `skill_manage` writes to `~/.hermes/config.yaml`
in subagent context. This fires silently: the subagent receives a refusal error and may
spend turns retrying.

Pattern when this applies:
- Subagent is tasked with both implementing a feature AND wiring it into config.yaml
- The security guard fires after implementation is complete, blocking the config step

Correct workflow:
1. Steer the blocked subagent immediately: `delegate_task(action='steer', message='config.yaml edits are blocked by security guard in subagent context. Skip all config.yaml patches. Write required config changes to /tmp/config-patches-<task>.txt as a Python script that applies them, then surface them as OPEN_ISSUES in your result file.')` 
2. The subagent writes a staging file + surfaces OPEN_ISSUES
3. Parent session applies config changes via `terminal()` with a heredoc Python script:
   ```python
   python3 - <<'EOF'
   import pathlib, yaml
   cfg = pathlib.Path('~/.hermes/config.yaml').expanduser()
   text = cfg.read_text()
   # targeted string replacements
   text = text.replace('old_value', 'new_value')
   cfg.write_text(text)
   import yaml; yaml.safe_load(text)  # validate
   print('OK')
   EOF
   ```
4. Verify the config write with `yaml.safe_load` before reporting it applied.

Steer early: once a subagent is stuck on config retries it burns budget. Steer as soon as
you see `Refusing to write to Hermes config file` in the live transcript.

When the adversarial/reviewer agent must wait for peer implementation agents to finish,
give it a bounded polling loop rather than a fixed sleep or hard-coded start time:

```bash
i=0
while [ ! -f /tmp/agent-a-result.txt ] || [ ! -f /tmp/agent-b-result.txt ]; do
  sleep 10; i=$((i+1))
  [ $i -ge 90 ] && echo "Timeout after 15m — reviewing available" && break
done
```

Cap at 90 iterations (15 minutes). After the cap: review whatever files exist, note
which peer results were missing. Give the reviewer WRITE access to all implementation
files so it can self-repair found bugs without dispatching another wave.

Naming convention: peer agents write `/tmp/agent-<letter>-result.txt`; reviewer polls
for all of them before starting. This makes the synchronization point explicit and
audit-friendly.

### Optimizer + adversarial reviewer must be sequential, not concurrent (HIGH pitfall)

## Recursive Improvement Until Saturation

For tasks requiring exhaustive multi-pass improvement (fork optimization, skill library overhaul,
architecture refactors), use the saturation loop:

```
CYCLE N:
  1. Dispatch parallel domain implementation agents (independent file ownership per agent)
  2. Wait for all to complete and commit
  3. Compile-check + test suite run (must pass before adversarial step)
  4. Fix any regressions immediately (parent session, not re-dispatch)
  5. Dispatch cold adversarial reviewer (no prior context about what was implemented)
  6. Triage findings: CRITICAL/HIGH get fixed this cycle; MEDIUM/LOW deferred to next
  7. Apply fixes, compile-check, test, commit, push
  8. STOP when adversarial reviewer says SATURATING (< 2 confirmed HIGH+ issues)
     Hard cap: 5 cycles regardless
```

**Saturation signal:** The adversarial reviewer should be instructed to emit `SATURATING`
explicitly when fewer than 2 confirmed HIGH+ bugs are found. This prevents infinite loops
when findings degrade to style-only or speculative issues.

**Domain partitioning discipline across cycles:**
- Cycle 1: foundational/core architecture (new capabilities, hook wiring, API)
- Cycle 2: integration completeness (hint file propagation, session lifecycle, MDL)
- Cycle 3: correctness proofs (formula math, floor guarantees, edge cases, session-boundary resets)
- Cycle 4+: tooling/predicates/instrumentation/doc parity
- Each cycle's domains must NOT touch files owned by concurrent sibling agents
- If a cycle's adversarial pass finds only MEDIUM/LOW issues and emits SATURATING, apply all mediums in the parent session (not a new subagent) and close. Re-dispatching a full cycle for MEDIUM-only cleanup wastes a round-trip.

**Per-cycle implementation agent count:** 3–4 parallel agents is the sweet spot. More than 4
requires a file-ownership conflict check (see File-Ownership Map section above) that itself
costs 5–10 minutes.

**Adversarial context isolation:** The cold reviewer must receive NO summary of what was
implemented — only the diff command and the attack vectors. Any preamble about "we added X"
bias the reviewer toward confirming rather than finding. Concrete phrasing: "Read the code
yourself. Read EVERY changed file vs upstream (git diff BASE..HEAD)."

**Post-cycle skill extraction:** After each SATURATING verdict, extract proven patterns to
the skill library before closing the session — the recursive loop itself generates the
highest-signal procedural learning.

When an optimizer agent and a cold adversarial reviewer run in parallel, the adversarial
agent reads the pre-optimization commit. It produces confirmed findings for bugs the
optimizer has already fixed — inflating the real bug count and forcing a full re-triage
pass to filter stale findings from live ones.

**Correct pattern:** optimizer commits (or writes to /tmp files) first; adversarial reviewer
dispatches AFTER, given the post-optimization commit SHA or file paths explicitly:
```
# In adversarial reviewer context:
git -C /tmp/fork-work checkout <POST-OPTIMIZATION-SHA>
# then run review against that state
```

If you need a tight deadline and must run both concurrently, give the adversarial agent the
expected post-optimization target paths (not HEAD) and instruct it to poll until those files
exist before reading:
```bash
while [ "$(git -C /tmp/fork-work log --oneline | head -1)" != "<expected commit prefix>*" ]; do
  sleep 15
done
```
Cap the poll at 30 iterations. Prefer sequential dispatch when possible — concurrent optimizer+reviewer
saves wall-clock time but doubles reconciliation work.

<!-- why: stale-snapshot findings look confirmed because the old code really has the bug;
only post-fix state can produce a meaningful false_positive verdict -->

### Long-running evals inside subagents hit 900s wall (CRITICAL pitfall)

Subagents have a hard 900-second timeout. Compaction policy evals with 6 arms × 30
questions × 3 domains take 60–120 min. Dispatching an eval run as a delegate_task
child guarantees a timeout mid-run, losing all partial results.

Correct pattern for any bounded job expected to run >15 minutes:
1. Build all inputs (question sets, lineage files) inside the subagent or parent —
   this is fast (~5 min) and safe within the timeout.
2. Launch the actual eval as a background terminal process from the PARENT session:
   ```python
   terminal(
     command="cd /repo && python evals/runner.py --policies a,b,c >> /tmp/eval.log 2>&1",
     background=True,
     notify=True   # fires when process exits; parent picks up results in next turn
   )
   ```
3. Parent receives the notify event, reads /tmp/eval.log or scorecard.json, reports results.

Anti-pattern: a subagent that builds questions AND runs the eval will always timeout before
the eval completes. Split: subagent builds inputs, parent runs eval in background terminal.

Signal that a subagent is about to timeout on an eval: log shows question generation
complete but eval loop only partially through arms. Steer immediately or stop the agent
and run the eval directly in the parent session.

### Adversarial agent timeout from blocking poll (CRITICAL pitfall)

Using `process_manage(action='wait', timeout=120s)` in a loop to poll for sibling files
burns the adversarial agent's entire 900s budget in blocked wait cycles, leaving no time
to do the actual review. Observed: agent spent 6 of 7 minutes waiting, then timed out
before writing its results file.

Do NOT use `process_manage wait` for cross-agent synchronization inside a subagent — it is
a blocking call, and the 900s subagent timeout applies to wall-clock time including waits.

Instead, do productive work during the poll:
1. Spin the poll loop with `terminal("sleep 10")` (non-blocking; kill it quickly)
2. While polling: read the IMPLEMENTATION FILES DIRECTLY (they exist before result files do)
   and start building the AST-parse + --help regression scaffold
3. Begin the review as soon as source files are non-empty, even before result files land
4. Only gate the full findings write on all result files being present

Concrete pattern:
```bash
# Non-blocking check, no process_manage wait
ls /tmp/agent-a-result.txt /tmp/agent-b-result.txt 2>/dev/null | wc -l
# If < 2: do productive preparatory work, then re-check in 10s
```

If the orchestrator can verify file contents directly (all source files already exist and
AST-parse cleanly), skip the result-file wait entirely and just verify the artifacts.
Result files are progress reports; the real deliverable is the source files.

## Recursive Research Until Saturation

When deep research must be exhaustive, dispatch a researcher with round-based
saturation discipline:

  Round 1: Broad sweep across all target topics (web_search + web_extract)
  Round 2: Deep dive on IMPLEMENTABLE findings (extract full methodology)
  Round 3+: Citation chase from top findings (search cited papers)
  Stop: when a full round yields 0 new IMPLEMENTABLE techniques
  Hard cap: 8 rounds maximum

For each IMPLEMENTABLE finding, require a structured record:
  PAPER / TECHNIQUE / INPUTS / OUTPUTS / INTEGRATION_TARGET / PRIORITY / EFFORT
  (LOW=prompt-only / MEDIUM=1-2 days script / HIGH=architectural)

Write to output file after EVERY round (not just at end) — ensures partial findings
survive if the agent times out mid-run.

Final output must include: SATURATION REACHED marker + total count + priority buckets.

Note: multi-wave iterative literature sweeps with convergence detection belong in
execute_code (Python loop), not delegation. Delegate only when each round requires
genuine branching decisions ("read this paper, decide which 3 of 20 cited papers to
follow"). Sequential queries with a fixed topic list: use execute_code.

## Reference files

- `references/backend-verification.md` — Verifying Which Search Backend a Subagent Used
- `references/compaction-eval-methodology.md` — Compaction eval question validity rules, signal-type tagging, combined score metric, session-type matching results, and top improvement targets
- `references/large-corpus-synthesis-pattern.md` — Large Corpus Synthesis Pattern
- `references/subagent-web-search-pitfalls.md` — Subagent web_search provider not inherited; SearXNG fallback; stalled-delegation diagnosis
- See references/subagent-web-search-pitfalls.md for Brave API rate limit mitigation under parallel fan-out.

## Research Paper Experiment Dispatch

When dispatching parallel subagents to run spike experiments sourced from research papers:

0. **Pure-computation spikes belong in execute_code, not subagents.** If a spike is pure
   Python — file I/O, string analysis, numpy/faiss benchmarks, graph traversal, sequential
   testing — run it directly in `execute_code`. Delegating to a subagent adds 3–7 min of
   dispatch overhead plus Codex stream-stall risk, for zero benefit over a local Python block.
   Delegate only when the spike requires genuine multi-turn tool reasoning (e.g. iterative
   web_search + synthesis + decision) that cannot be scripted in one Python block.

   **Iterative web research (multi-wave literature sweeps) also belongs in execute_code.**
   Run query → collect IDs → fetch abstracts → classify → repeat-until-convergence as a
   Python loop in execute_code. Benefits over delegation: no stream-stall risk, full
   parent visibility into intermediate state, convergence detection (loop until delta=0)
   that subagents cannot self-report, no per-wave dispatch overhead.
   Confirmed Sep 2026: 9-wave metacognition convergence sweep ran in ~15 min via
   execute_code; equivalent subagent delegation estimated 45-90 min with stall risk.
   Delegate research only when it requires genuine branching decisions at each step
   ("read this paper, decide which 3 of 20 cited papers to follow") — not sequential loops.

1. **Cluster before dispatching.** A sweep producing 50 spike candidates is not 50 experiments.
   Group by shared mechanism (all peer-scoring variants → one canonical experiment, all
   context-compression papers → one experiment). Target 5–10 experiments per sweep regardless
   of paper count.

2. **Fetch abstracts before subagents run.** Without full abstract text, subagents have
   no content to reason about and produce SKIP or trivial results. Use web_extract on arXiv
   abstract pages for all selected papers in the parent turn before dispatching. The abstract
   fetch is cheap (seconds) and eliminates the need for subagents to do their own retrieval.

3. **Supply the full Given/When/Then in the task context.** Each child task must include:
   - Paper abstract (fetched by parent)
   - Given/When/Then from the interpreter output
   - Hermes component targeted
   - Spike output path (`~/.hermes/cache/research/spikes/<id>/`)
   - Requirement: self-contained synthetic simulation (no running Hermes dependency)

4. **Dispatch only after the parent holds abstracts + contracts.** Do not fan out children that still need to `web_extract` their own papers.

5. **Spike output format:** one dir per experiment containing `README.md` (verdict +
   key numbers) and `sim.py` (standalone Python simulation on synthetic Hermes-representative
   data). The README closes with VALIDATED / PARTIAL / INVALIDATED.

6. **Data-format mismatch invalidates the run, not the technique.** When a spike fires no
   rules (e.g. Self-GC fold/mask/prune never triggering on delegation live logs), diagnose
   whether the input format is the bottleneck before writing INVALIDATED. Live .log files
   truncate tool results before GC rules can fire; sequential testing runs on summary counts
   not raw outputs; etc. The correct verdict is INVALIDATED-on-data-format with a concrete
   note on what input format is needed and when to retry — not unconditional INVALIDATED
   that discards a sound methodology. Concrete: Self-GC rules require full session JSON
   (not truncated live logs) — retry against ~/.hermes/cache/sessions/ when available.

7. **Sequential testing (SPRT) stops on the wrong tail event.** SPRT stops early when the
   rate exceeds H1 — but high-value rare events cluster in the tail and are missed.
   (Concrete: SPRT H1 stop at paper 14/144 misses all 5 math OPTIMIZATION findings at
   indices 113–119.) Use anytime-valid bounds only as anomaly DETECTORS for skip-rate
   spikes, never as early-stop gates on rare-but-high-value events.

## Sweep 31 Additions (Sep 2026)

### Role Drift Detection in Hierarchical MAS (arXiv:2609.03111) ★ MED

Empirical study of 8 hierarchical MAS: roles assigned at task start drift over time as agents
reinterpret their scope. Drift signatures:
1. Executor-role agents begin making strategic decisions
2. Coordinator-role agents begin executing low-level tool calls
3. Verifier-role agents begin proposing fixes instead of flagging issues

**Hermes pattern:**
- Each `delegate_task` subagent goal must include a role declaration: "Your role is
  [executor|planner|reviewer]. You may [actions]. You may NOT [boundary actions]."
- If a subagent output shows boundary violations (e.g. a reviewer proposing code changes),
  treat output with reduced trust weight and re-route through coordinator.
- Pair with MasDrift scope restriction: `enabled_toolsets` at delegation level is the
  enforcement mechanism; role declaration is the behavioral signal.

## Sweep 29 Additions (Aug 2026)

### Structured World-State IPC — not transcript dumps (ICLR 2026 MALGAI) ★ HIGH
Pass structured world-state JSON between subagents, not prose summaries:
`{"facts": [...], "causal_edges": [...], "budget_remaining": {...}, "open_questions": [...]}`
Use `hermes-context-packet` skill to formalize. Agents read/write the world-state.

### Capability Cards not CoT Dumps (ICLR 2026 Team of Thoughts) ★ HIGH
Each subagent returns `{"result": ..., "confidence": 0.8, "evidence": [...], "open_questions": []}`.
Orchestrator picks specialist by synthesis quality (past performance), not model size.
Require `subagent-output-contract` skill. Never re-run specialists that returned high-confidence cards.

### Uncoordinated Shared Literature (arXiv:2608.23691) ★ MED
No central orchestrator; shared literature; agents work independently on same problem.
5/12 novel AlphaEvolve constructions via pure uncoordination. Best for creative/exploratory tasks.
**Do not apply this to production implementation or review batches** — those stay isolated-context + parent merge (Interaction Tax). Sharing a literature dump across implementation workers is the interaction-tax anti-pattern.

## Prospect-State Propagation (arXiv:2609.08033) ★ HIGH

PspMAS **decouples** each agent's micro-state: a compact **prospect** (decision-critical traces that preserve heterogeneity) vs a rich **semantic** state (LLM reasoning / tool traces). Naive compression that dumps or shares full semantic traces homogenizes workers and blows parent context.

**Hermes mapping (not "summarize the thread"):**
- Between waves, pass prospect only: task goal, decisions made, constraints, open questions, **and unresolved disagreements** (do not collapse peer diversity — Interaction Tax).
- Do **not** pass raw tool outputs or full sibling transcripts as the next `context=`.
- Prospect is **not** control: stop conditions, output schema, and tool bounds stay in the typed control block (2609.00621) and must not be summarized away.

Handoff *shape* for prospect lives in `hermes-context-hygiene` (GOAL / DECISIONS / CONSTRAINTS / OPEN). Do not substitute that prose for a JSON control contract.

**Compose with Sweep 29 handoffs — pick by what is shared, do not emit all four:**
| Shared object | Format |
|---|---|
| Protocol / schema / stop | Control block (2609.00621) — typed, not summarizable |
| Wave-to-wave decisions | Prospect (this section) |
| Worker return | Capability card (`subagent-output-contract`) |
| Mutable shared facts | World-state packet (`hermes-context-packet`) |

<!-- why: treating prospect as generic compression drops heterogeneity and can rewrite control; paper is a two-state split -->

## Cross-Agent Routing Artifacts (Typed Federated Artifacts, arXiv:2609.06815) — S3

When parallel agents solve similar tasks, capture their tool-routing decisions as typed artifacts. Future agents with matching trigger patterns can inherit the routing before cold-starting — reducing first-turn exploration cost.

File: ~/.hermes/cache/routing-artifacts.jsonl
Schema (one JSON object per line, append-only):
  {"ts": "ISO8601", "agent_id": "session_id:task_id", "trigger_pattern": "...", "tool_sequence": ["tool1", "tool2", ...], "outcome_score": 0.0-1.0, "task_type": "research|code|mixed"}

When to capture: after any 3+ tool-call sequence that passes verification-before-completion, append a routing artifact.

When to consume: before dispatching a parallel task, read the last 50 routing artifacts and check if any trigger_pattern cosine similarity to the current task description exceeds 0.75. If yes, prepend the tool_sequence as a suggested tool order in the child's goal prompt.

Cache management: keep last 500 artifacts (FIFO evict). Artifacts older than 30d are stale (domain and model routing change). No PII in trigger_pattern — strip session-specific entity names.

Example consumption in delegate_task goal:
  "Suggested tool order from prior similar tasks: [web_search, read_file, execute_code]. You may deviate if the task demands it."

This is the typed federated artifact pattern: agents share routing knowledge as structured typed data without sharing raw context (privacy-preserving, cross-session).

<!-- why: each parallel child currently cold-starts with no knowledge of what tool sequences work; artifact inheritance converges effective routing ~2x faster in repeated task domains -->

## Anti-Conformity Seeding (DEAR, arXiv:2608.03648)

When dispatching agents for adversarial review, consensus, or any HIGH-stakes multi-agent decision, seed each agent with a distinct investigative perspective before launching:

- Assign each agent a different failure mode to look for (e.g. one looks for performance regressions, one for security issues, one for dead code, one for logic errors)
- Do NOT give all agents the same framing or the same reference reasoning — identical seeds + no cross-referencing = independent opinions; cross-referencing without diverse seeds = conformity risk
- If ≥2/3 agents return the same verdict at round 1, check whether they cited each other's reasoning; if yes, treat as potential conformity not consensus, and require at least one agent to argue the opposite in round 2
- Never accept a round-1 unanimous HIGH-stakes verdict without verifying each agent produced independent reasoning (unique reasoning paths, not just identical conclusions)

Reference: arXiv:2608.03648, DEAR (Debate Relationship Regulation), EMNLP 2026.

## Role-Boundary Enforcement (arXiv:2609.09133 ExecCritic)

Each delegate_task invocation must include a role declaration (Your role is [executor|planner|reviewer]) with explicit You may NOT boundary actions. If a reviewer subagent output contains code changes, or an executor output contains strategic re-scoping, apply 0.5x trust weight in synthesis and route through a coordinator check before applying.

## Dual-Gap Budget Allocation (Luenberger Ch 7.7)

Lagrangian dual certificate for parallel agent budget: if two subagents are allocated equal budget but one returns in 30% of its budget while the other uses 100%, the allocation is dual-suboptimal. Reallocate budget from surplus agent to bottleneck until marginal values equalise.


---
version: 1.2.0
name: mnemosyne-atp-safety
description: >
  Use when: Agentic Transaction Processing (ATP) — wrap any LLM agent's tool calls with constraint-checked admission control. Prevents corrupted workflow state with <6% overhead. Based on Mnemosyne (arXiv:2607.00269).
tags: [agent-safety, workflow-integrity, tool-use, transaction-safety]
depends_on: [autonomous-agent-loop-design]
provides: [mnemosyne-atp-safety, rollback-plan, provenance-edges, commit-guard]
related_skills: [autonomous-agent-loop-design, verification-before-completion, preact-trajectory-compilation, graphiti-mcp-setup]
triggers:
  - Agent is about to execute a sequence of irreversible tool calls (file writes, API mutations, deployments)
  - Task needs constraint-checked admission control to prevent corrupted workflow state
  - Designing an autonomous loop with tool calls that must be wrapped in a safety harness
---

# Mnemosyne ATP: Agentic Transaction Processing

**Research basis:** Mnemosyne (Chang et al., Jul 2026, arXiv:2607.00269)
Code: github.com/eyuchang/Mnemosyne
**Key benefit:** <6% overhead; ~10× fewer repair operations; zero invalid commits in pilots

## What it solves

LLM agents can generate workflow actions that:
- Violate cross-step constraints (e.g. deploy before test passes)
- Create inconsistent state (e.g. write to a file after marking it deleted)
- Create hard-to-undo partial commits (e.g. 3 of 5 DB migrations applied)

ATP treats LLM-generated actions as **untrusted proposals** that are admitted only if they
pass a deterministic executable constraint set C. It provides:
1. Append-only transition log (audit trail, never destructive)
2. Effective-state projection (what state WOULD we be in if we admit this?)
3. Dependency-safe compensation (local repair without global recompute)
4. Active commitment records (what has been committed vs. proposed)

Four safety properties proved in the paper:
- **Consistency**: committed state always satisfies all constraints in C
- **Progress**: valid proposals are eventually admitted
- **Compensation soundness**: repair operations produce a consistent state
- **Termination**: the admission loop terminates

## When to use

Use ATP whenever an agent executes **irreversible or hard-to-undo actions**:
- Database migrations or schema changes
- File system mutations (deletes, renames across directories)
- External API calls (payments, emails, webhooks — can't undo)
- Multi-step deployment pipelines
- Code commits and PR submissions

Do NOT use for purely read-only workflows — overhead not justified.

## Implementation pattern

## Step 1: Define your constraint set C

Before defining constraints, run select-frameworks to determine which reasoning gates apply.
Use `$HERMES_HOME` (default `~/.hermes`) — never hardcode another user's home:
  ```
  python3 ${HERMES_HOME:-$HOME/.hermes}/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<ATP-guarded task>"
  ```
  If lookahead is in primary: add terminal-risk constraint (exit 1+ blocks irreversible commit).
  If boundary-check is in primary: add action-completeness constraint to the constraint set.

  boundary-check as ATP constraint:
  ```python
  import os
  from pathlib import Path
  _H = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
  ("action_in_scope",
   lambda action, state: subprocess.run(
     ["python3", str(_H / "scripts" / "metacognitive-harness.py"), "boundary-check",
      "--task", state["goal"], "--action", action["name"]],
     capture_output=True).returncode == 0,
   "Action out of scope or incomplete: prerequisite is boundary-check exit 0")
  ```

  lookahead as ATP constraint (before HAZARD-tier actions):
  ```python
  ("terminal_risk_low",
   lambda action, state: action.get("tier") != "HAZARD" or subprocess.run(
     ["python3", str(_H / "scripts" / "working-memory.py"), "lookahead",
      "--task", state["goal"], "--next-action", action["name"],
      "--steps-remaining", str(state.get("steps_remaining", 1))],
     capture_output=True).returncode == 0,
   "Terminal risk too high for HAZARD action: lookahead must exit 0 (LOW risk)")
  ```

Constraints are ordered rules that any proposed action must satisfy:

```python
CONSTRAINTS = [
    # Format: (rule_name, check_function)
    ("no_delete_without_backup",
     lambda action, state: action["type"] != "delete_file"
         or state.get(f"{action['path']}_backed_up")),
    ("tests_pass_before_deploy",
     lambda action, state: action["type"] != "deploy"
         or state.get("tests_pass")),
    ("no_write_to_deleted",
     lambda action, state: action["type"] != "write_file"
         or action["path"] not in state.get("deleted_files", set())),
]
```

### Step 2: ATP admission gate

```python
class ATPGate:
    def __init__(self, constraints):
        self._constraints = constraints
        self._log = []          # append-only transition log
        self._state = {}        # effective committed state
        self._proposed = []     # proposed but not yet committed
        self._provenance = []   # memory-to-action provenance edges (arXiv:2608.10502)
        self._action_counter = 0

    def record_memory_read(self, memory_id: str, source: str = "unknown") -> str:
        """Record a memory fact read before the next propose(). Returns provenance edge ID."""
        edge_id = f"mem-{len(self._provenance):04d}"
        self._provenance.append({
            "edge_id": edge_id,
            "memory_id": memory_id,
            "source": source,          # "hindsight" | "graphiti" | "session_search" | "memory_md"
            "action_id": None,         # filled in on next propose()
            "committed": False,
        })
        return edge_id

    def propose(self, action: dict) -> dict:
        """Evaluate a proposed action. Returns {'admitted': bool, 'reason': str}"""
        self._action_counter += 1
        action_id = f"act-{self._action_counter:04d}"
        action["_action_id"] = action_id  # stamp action with ID for rollback reference

        projected_state = {**self._state}
        # Apply the action to the projected state first
        projected_state = self._project(projected_state, action)
        # Check all constraints against the PROJECTED state (what state would look like after admission)
        for rule_name, check_fn in self._constraints:
            try:
                if not check_fn(action, projected_state):
                    return {
                        "admitted": False,
                        "reason": f"Rejected by constraint: {rule_name}",
                        "action": action,
                    }
            except Exception as e:
                return {"admitted": False, "reason": f"Unevaluable constraint {rule_name}: {e}"}

        # Link pending memory reads to this action (provenance edges)
        for edge in self._provenance:
            if edge["action_id"] is None:
                edge["action_id"] = action_id

        # Admit the action
        self._proposed.append(action)
        self._log.append({"type": "propose", "action": action, "action_id": action_id})
        return {"admitted": True, "action": action, "action_id": action_id}

    def commit(self, action: dict) -> None:
        """Commit an admitted action to the effective state."""
        self._state = self._project(self._state, action)
        action_id = action.get("_action_id", "unknown")
        self._log.append({"type": "commit", "action": action, "action_id": action_id})
        # Mark provenance edges for this action as committed
        for edge in self._provenance:
            if edge["action_id"] == action_id:
                edge["committed"] = True
        if action in self._proposed:
            self._proposed.remove(action)

    def get_provenance_edges(self, memory_id: str = None) -> list[dict]:
        """Return provenance edges, optionally filtered by memory_id."""
        if memory_id is None:
            return list(self._provenance)
        return [e for e in self._provenance if e["memory_id"] == memory_id]

    def mark_memory_stale(self, memory_id: str) -> list[str]:
        """Mark memory stale; return action_ids that used it (selective replay, not full trace)."""
        stale_action_ids = []
        for edge in self._provenance:
            if edge["memory_id"] == memory_id:
                edge["stale"] = True
                if edge["action_id"] and edge["action_id"] not in stale_action_ids:
                    stale_action_ids.append(edge["action_id"])
        self._log.append({
            "type": "memory_stale",
            "memory_id": memory_id,
            "affected_actions": stale_action_ids,
        })
        return stale_action_ids

    def _project(self, state: dict, action: dict) -> dict:
        """Apply action effects to a state dict. Override for your domain."""
        new_state = {**state}
        if action.get("type") == "set_flag":
            new_state[action["flag"]] = action["value"]
        elif action.get("type") == "delete_file":
            new_state.setdefault("deleted_files", set()).add(action["path"])
        elif action.get("type") == "run_tests":
            new_state["tests_pass"] = action.get("result", False)
        return new_state

    def compensate(self, from_step: int) -> list[dict]:
        """Return minimal compensation actions to restore consistency from a failure."""
        # Minimal: roll back uncommitted proposals
        compensations = [{"type": "rollback", "action": a} for a in reversed(self._proposed)]
        self._proposed.clear()
        return compensations
```

### Step 3: Wrap your agent loop

```python
gate = ATPGate(CONSTRAINTS)

for step in agent_plan:
    proposed_action = llm.generate_next_action(step)
    result = gate.propose(proposed_action)

    if not result["admitted"]:
        proposed_action = llm.revise(proposed_action, result["reason"])
        result = gate.propose(proposed_action)

    if result["admitted"]:
        admitted = result["action"]  # stamped admitted action, never the rejected draft
        execute(admitted)
        gate.commit(admitted)
```

## Hermes-specific patterns

### Pattern A: Tool call filter

Before calling any irreversible Hermes tool (terminal, write_file, etc.), pass the
proposed call through a lightweight constraint check:

```python
IRREVERSIBLE_TOOLS = {"terminal", "write_file"}
DEPLOY_GATE_CONSTRAINT = lambda tool, args, state: (
    tool != "terminal"
    or "deploy" not in args.get("command", "")
    or state.get("tests_passed")
)
```

### Pattern B: Cron job safety

For autonomous cron jobs that modify external state, add a pre-flight ATP check
before the job runs to confirm preconditions. Store state in Graphiti.

### Pattern C: Multi-step file operations

When a workflow involves multiple file mutations (rename, replace, update references),
use ATP to ensure each mutation is consistent before the next begins.

### Pattern D: Memory provenance edges + selective rollback (arXiv:2608.10502)

When an action is informed by a recalled memory fact (Graphiti, Hindsight, session_search),
call `record_memory_read()` before `propose()`. If the fact is later stale or PSE-contaminated,
`mark_memory_stale(memory_id)` returns the action_ids to selectively replay — not the full trace.
Low-trust facts (`source_type=external`, weight=0.4) that get promoted are the highest-risk
candidates for `mark_memory_stale()`.

Load information-flow-control before any EXTERNAL-tainted write in an ATP transaction.

## TraceGrant + AID-Guard — Capability Scope Contracts + Effect Ledger (arXiv:2608.21126 + 2608.21159, Aug 2026)

### TraceGrant — IMPLEMENTED in l1 memory pipeline (Aug 2026)

The l1 memory pipeline (l1-promote.py, l1-graphiti-write.py, l1-graphiti-reconcile.py) now
enforces TraceGrant namespace policy at write time. Key files:

- `~/.hermes/scripts/l1-tracegrant.py` — shared policy module (source of truth)
- `~/.hermes/memory-facts/lifecycle.db` — `tracegrant_grants` table + `grant_id` on `fact_lifecycle`

Policy enforced:
  internal  → profile, event, record   (full access)
  agent     → event, record            (no user identity writes)
  cron      → event, record
  external  → record only              (never profile)

Audit: `python3 ~/.hermes/scripts/l1-promote.py --tracegrant-audit`

### TraceGrant — Capability Manifests for Subagents (arXiv:2608.21126)

TraceGrant binds each tool call to a declared scope contract (data sources, output channels, effect categories).

**Hermes:** put `capability_scope` in the delegate_task context packet. Distinct from `enabled_toolsets`
(availability) — this is a declared contract the subagent self-reports against for scope-violation audit.

```python
# In delegate_task context field:
context = """
capability_scope:
  data_sources: [web_search, web_extract, session_search]
  output_channels: [read-only — no write_file, no terminal writes, no skill_manage]
  effect_categories: [research, read-only]

You must not call any tool outside the declared capability_scope.
If a task step requires a tool outside scope, return a SCOPE_EXCEEDED result
rather than calling the tool.
"""
```

**Provenance:** require `tool_calls_made: [...]` in subagent output; parent checks it against capability_scope.

### AID-Guard — Stateful Effect Ledger (arXiv:2608.21159)

AID-Guard maintains a running ledger of all external state modifications made by an agent,
with lifecycle tracking and revocation support. The ledger enables **targeted rollback** when
task scope changes or expires.

**Effect ledger pattern for ATP-wrapped tasks:**

```python
# Extend ATPGate to track external effects:
# (add to ATPGate.__init__)
self._effect_ledger = []   # list of {effect_id, tool, target, timestamp, reversible, undo_cmd}

def record_effect(self, tool: str, target: str, undo_cmd: str = None) -> str:
    """
    Record an external state modification BEFORE executing it.
    Returns effect_id for future revocation.

    Call BEFORE executing any irreversible tool call:
        effect_id = gate.record_effect("write_file", "/path/to/file", "rm /path/to/file")
        write_file("/path/to/file", content)
        gate.commit_effect(effect_id)
    """
    effect_id = f"eff-{len(self._effect_ledger):04d}"
    self._effect_ledger.append({
        "effect_id": effect_id,
        "tool": tool,
        "target": target,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "reversible": undo_cmd is not None,
        "undo_cmd": undo_cmd,
        "committed": False,
    })
    return effect_id

def commit_effect(self, effect_id: str):
    for eff in self._effect_ledger:
        if eff["effect_id"] == effect_id:
            eff["committed"] = True

def revoke_scope(self, after_effect_id: str = None) -> list[str]:
    """
    Revoke all effects after a given effect_id (or all if None).
    Returns the undo_cmd list to execute in reverse order.
    """
    ledger = self._effect_ledger if after_effect_id is None else [
        e for e in self._effect_ledger
        if e["effect_id"] >= after_effect_id
    ]
    undo_cmds = [e["undo_cmd"] for e in reversed(ledger) if e["committed"] and e["undo_cmd"]]
    return undo_cmds

def get_effect_ledger(self) -> list[dict]:
    return list(self._effect_ledger)
```

**Usage pattern — task scope change mid-run:**
```python
# Task scope changed (e.g. user cancelled the task after 3 write_file calls):
undo_sequence = gate.revoke_scope()
for cmd in undo_sequence:
    terminal(cmd)  # execute undo commands in reverse order
```

Register undo **before** execution — do not improvise rollback under failure pressure.
Minimum viable ledger without ATPGate: `{tool, target, undo}` before each irreversible call.

## Action Safety Tier Classification

Two-tier admission vocabulary (google/skills, 2026). Classify before choosing ATP, Guardian, or neither.

| Tier | What it covers | Admission rule |
|---|---|---|
| **Tier R** (read-only) | Inspect, validate, diff, compare, render — zero side effects | No confirmation needed; execute immediately |
| **Tier M** (mutating / costly) | LLM calls, API writes, file mutations, deploys, external sends — incurs cost or has side effects | Require explicit confirmation (yes/no) once per session mode |

**Tier R examples:** `read_file`, `search_files`, `browser_snapshot`, `session_search`, `hermes cron list`.
**Tier M examples:** mutating `terminal`, `write_file`, `patch`, cron create/remove, external APIs, email.
**Classification rule:** when in doubt, Tier M.

**Integration with ATP gate:** Tier R actions bypass `ATPGate.propose()` entirely.
Tier M actions go through `propose()` + all active constraints. High-risk Tier M actions
(irreversible, external-facing) additionally go through the Guardian LLM call
(see `references/atp-safety-research-2026.md`). Three-layer funnel:

```python
def dispatch_action(action: dict, gate: ATPGate, session_transcript: str) -> bool:
    tier = classify_tier(action)  # "R" or "M"
    if tier == "R":
        return True  # no admission control needed
    result = gate.propose(action)
    if not result["admitted"]:
        return False
    if is_high_risk(action):  # irreversible / external-facing
        return guardian_gate(session_transcript, action)
    return True
```

## Causal Justifications in Safety Constraints (Anthropic "Teaching Why", May 2026)

Source: https://www.anthropic.com/research/teaching-claude-why

Replace imperative rules with causal justifications — models generalize "why"; rules break at distribution boundaries.

Before: "Don't delete files outside the workspace."
After: "Don't delete files outside the workspace because those files cannot be recovered, and the user has not granted permission to modify content outside the task scope — loss would be irreversible and unexpected."

Apply this pattern to all safety-related instructions in:
- The Hermes system prompt safety section
- trajectory-risk-guardrail skill pitfalls
- Any skill with `irreversible` or `destructive` actions in its procedure

## Pitfalls

- **Unevaluable constraint must raise, not silently pass.** If `check_fn` cannot evaluate
  (missing state key, exception), treat as rejected — never return True. Silent passes let
  invalid actions through. `ATPGate.propose()` already wraps each check in try/except.
  (Semantica PolicyEngine: unevaluable rules raise instead of silently passing.)
- **Constraint set completeness**: ATP only catches what you define in C. Missing a constraint
  means invalid commits can still happen. Start with your riskiest actions.
- **State projection fidelity**: `_project()` must accurately model what the action does to
  state. Inaccurate projection → false admits or false rejections.
- **Compensation completeness**: Compensation must produce a valid state, not just undo.
  If step 3 of 5 fails, compensating by undoing 3 may not restore consistency if 1+2 had side effects.
- **Don't use for idempotent actions**: Read-only, retryable, or reversible actions don't need ATP.
  Apply the overhead only where it matters.

## Self-Healing Failure Taxonomy — RETRY_LOOP Guard (arXiv:2606.01416)

Typed recovery beats retry-only. Evidence: **98.8% task success** with 5-class recovery vs **94.5% retry-only**.

| Class | Recovery |
|---|---|
| TOOL_TIMEOUT | Exponential backoff retry (max 2 retries); each retry must alter call context (increase timeout param, add jitter marker) so it does not trigger RETRY_LOOP detection. Same-args TOOL_TIMEOUT retries count toward RETRY_LOOP. |
| MALFORMED_ARGS | Schema repair prompt + re-invoke with corrected args |
| STALE_CONTEXT | Summarize + reconstruct context before retry |
| CONTRADICTORY_EVIDENCE | HITL or second-opinion subagent |
| RETRY_LOOP | Detect same-tool + same-args >= 3 calls (including timeout retries with unchanged args); break by: (1) identifying underlying cause, (2) trying alternative approach or tool, (3) escalating to HITL if alternatives exhausted. |

**RETRY_LOOP guard:** if the agent calls the same tool with the same arguments 3+ times in a row, this is a RETRY_LOOP failure class. Break by: (1) identifying the underlying cause, (2) trying an alternative approach or tool, (3) escalating to HITL if alternatives exhausted. Do not keep retrying the identical call.

## GPM — Governed Persistent Memory: Fail-Closed Release (arXiv:2608.12476, Sweep 15) ★ HIGH

Retrieval alone must not let contradictory, superseded, retracted, deleted, or stale
records support an outgoing claim. Five executable clauses:

1. **Ledger integrity** — every state transition is appended, never overwritten
2. **Source binding** — admitted fact permanently bound to admission source (anti-spoofing)
3. **Conflict isolation** — contradictory facts isolated; neither supports claims until resolved
4. **Non-revival** — retracted/deleted records CANNOT re-enter the active view
5. **Exact claim closure** — claims close over a fresh verified view at one HEAD; no stale caches

**Benchmark:** GPM-ReleaseBench 3,600 cases — naive select-store-retrieve unmatched on 50% of violations.

**Hermes ATP integration — fail-closed additions:**

```python
# Add to ATPGate.__init__:
self._retracted = set()    # retraction ledger — non-revivable
self._conflicted = set()   # conflict-isolated memory_ids

def retract_memory(self, memory_id: str):
    """Non-revival: retracted records can never be re-admitted."""
    self._retracted.add(memory_id)
    self._log.append({"type": "retract", "memory_id": memory_id})

def isolate_conflict(self, memory_id_a: str, memory_id_b: str):
    """Conflict isolation: neither fact supports claims until resolved."""
    self._conflicted.update({memory_id_a, memory_id_b})
    self._log.append({"type": "conflict_isolate", "ids": [memory_id_a, memory_id_b]})

def source_bound_admit(self, fact: dict, source: str) -> bool:
    """Source binding: source is permanent and immutable after admission."""
    if fact.get("memory_id") in self._retracted:
        return False   # non-revival enforcement
    if fact.get("memory_id") in self._conflicted:
        return False   # conflict isolation
    fact["_source"] = source   # bind source permanently
    fact["_source_locked"] = True
    return True
```

**Hermes memory pipeline implications:**
- When `l1-promote.py` writes a fact to Hindsight, record the source_session_id as the
  permanent source binding — never allow a later session to reclassify the source
- When `contradiction_check()` finds a CONTRADICTS verdict: **isolate both facts** in
  conflict partition, not just mark the old one superseded — neither supports claims until
  explicitly resolved
- Retracted facts from `mark_memory_stale()` must be persisted to a retraction ledger
  (append to `~/.hermes/memory-facts/retractions.log`) — non-revival cannot be enforced
  without a durable ledger

**Pitfall:** Non-revival is the hardest property to enforce. A new l1-extract run that
finds the same fact independently can re-admit a retracted fact with a new memory_id.
Mitigation: before any Hindsight write, check the retraction ledger for semantic near-matches
(cosine > 0.92) — don't just check for matching memory_ids. <!-- why: prevents implicit revival of retracted facts through re-extraction -->

## Substrate authority divergence (arXiv:2609.08472) ★ HIGH

In multi-agent systems, harness state, workspace state, and registry state can diverge silently. Before any ATP-wrapped transaction commits: verify that all three substrates agree on the resource state. If they disagree, **fail closed** — do not proceed until divergence is resolved.

Divergence cases (three substrates: harness belief, workspace/disk, external registry):
1. Workspace file was modified by another agent between the read and the commit
2. Registry revoked permission between authorization check and action execution
3. Harness state (what the agent believes) disagrees with workspace or registry even when file content looks unchanged

Do not infer authority from file content alone. Pair with `trajectory-risk-guardrail` cross-substrate authority check (pre-flight); this rule is the commit-time gate. TRG decides whether the trajectory is authorized; ATP fails closed at commit if the three substrates have diverged since that pre-flight.

<!-- why: silent harness/workspace/registry split lets ATP commit a mutation that the registry no longer authorizes, or overwrite another agent's intervening write -->

See `references/atp-safety-research-2026.md` for safety research survey (Sweeps 12-29).

## Church-Rosser Confluence for ATP Transaction Ordering (Thompson Ch 3)

**Theory:** The Church-Rosser property (confluence) states that if a term can be reduced by two different reduction sequences, both sequences eventually reach the same normal form. Equivalently: reduction order does not affect the final result.

**Hermes rules:**
- ATP transaction ordering is safe when operations are confluent: two different execution orders applied to the same initial state must reach the same final state.
- Before declaring two ATP execution orders equivalent, verify confluence: does applying operation A then B yield the same result as B then A? If not, the operations do NOT commute — order matters and only one order is correct.
- Non-confluent operations (reads that affect writes, writes to shared state) must be serialized; do not treat them as order-independent.

**Citation:** Simon Thompson — *Type Theory and Functional Programming*, Ch 3 (The Lambda Calculus — Church-Rosser theorem); also Church & Rosser (1936).

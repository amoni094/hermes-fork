---
name: agent-task-signoff
related_skills:
  - verification-before-completion
  - self-improve-agent
  - subagent-driven-development

depends_on: [verification-before-completion]
provides: [signoff-table, completion-evidence, residual-risk-log]
description: >
  Use when producing a structured, evidence-backed sign-off table at the end of a multi-component task or agentic run. Replaces prose "done" claims with per-component status plus commit/artifact handles and residual risks. Adapted from cs249r_book's autonomous agent audit protocol.
version: 1.0.0
author: Hermes Agent (adapted from harvard-edge/cs249r_book)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [signoff, verification, completion, multi-agent, evidence]
    related_skills: [verification-before-completion, self-improve-agent, subagent-driven-development]
triggers:
  - "produce a sign-off table"
  - "structured sign-off for this task"
  - "sign off on this run"
  - "per-component status"
  - "done artifact"
  - multiple subagents returned results that need structured synthesis and sign-off
  - a multi-phase task is complete and needs verification evidence logged
  - parallel agent run concluded and summary evidence is needed
---

# Agent Task Sign-Off

Use this at the end of any multi-component task (parallel agents, multi-file changes,
audit passes, staged rollouts) instead of a prose "done" claim.

<!-- metacognition wiring: see adaptive-agent-reasoning skill -->
Before signing off, run verify-gated completion check:
  python3 ~/.hermes/scripts/working-memory.py verify-gate --session SESSION
exit 2 = constraint gap; do not claim done. See adaptive-agent-reasoning skill for full completion protocol.


## When to Use

- After parallel subagents return and you're synthesizing results
- After a multi-phase audit (research → plan → implement → verify)
- Before closing out a long session with multiple deliverables
- Whenever verification-before-completion would require tracking several independent proofs

## AgentAtlas 6-State Control-Decision Taxonomy (arXiv:2605.20530, Aug 2026) <!-- rationale: outcome-only leaderboards hide systematic failure modes; this taxonomy provides ready-made categories for evidence-backed sign-off and post-mortems -->

AgentAtlas introduces a **six-state control-decision taxonomy** audited across 15 agent benchmarks, and a trajectory-failure vocabulary with primary error source and downstream impact. Key finding: removing explicit label menu causes mapped label agreement to change substantially, and axis choice flips model rankings — outcome-only evaluation is insufficient.

**Six control-decision states** (verify each in sign-off):

| State | Meaning | Sign-off check |
|---|---|---|
| **Act** | Agent executes the intended action | Did the action complete and produce verifiable output? |
| **Ask** | Agent requests clarification before acting | Was clarification genuinely needed, or was it avoidable escalation? |
| **Refuse** | Agent declines the action as out-of-scope or unsafe | Was the refusal correct, or did the agent refuse when it should have acted? |
| **Stop** | Agent terminates the run as complete | Was the stopping criterion met, or was it premature closure? |
| **Confirm** | Agent requests human confirmation before an irreversible action | Was confirmation triggered on the right conditions (irreversibility, ambiguity)? |
| **Recover** | Agent detects a failure and attempts self-correction | Did recovery succeed? Was the original failure cause addressed? |

**Trajectory-failure vocabulary** (add to failure-scan row):
- Primary error source: input/context / model reasoning / tool execution / coordination
- Downstream impact: contained (single step) / cascade (propagated) / silent (undetected)

**Sign-off usage:** for any run where control-decision states other than Act occurred, add an "Atlas audit" row to the sign-off table:

| Component | Atlas States Triggered | Correct? | Notes |
|---|---|---|---|
| `<task phase>` | Act / Ask / Refuse / Stop / Confirm / Recover | YES/NO | `<explanation if NO>` |

A run where Refuse was triggered but the task is marked complete must explain why the refused action was not needed.

Reference: arXiv:2605.20530, "AgentAtlas: Beyond Outcome Leaderboards for LLM Agents", Aug 2026.

## 3-Layer Dogfooding Failure Taxonomy (arXiv:2608.09939, Aug 2026)

Before completing signoff, scan for these 10 failure types:
1. Misidentified user intent (did I address what was actually asked?)
2. Premature closure (did I stop before the task was fully done?)
3. Incomplete subtask execution (did every delegated subtask produce verified output?)
4. Hallucinated capability claim (did I claim success without evidence?)
5. Over-escalation (did I ask the user unnecessarily for decisions I could make?)
6. Under-escalation (did I skip a human check the stakes required?)
7. Memory retrieval miss (did I fail to check relevant prior session context?)
8. Tool misapplication (did I use the right tool for each action?)
9. Context window forgetting (did I lose track of earlier constraints or files?)
10. Policy/constraint violation (did I stay within stated scope and permissions?)

Add a "failure-scan" row to the signoff table: list any triggered failure types with their mitigations.

## 5-Level MAS Error Taxonomy + Attribution Problem (CyberLeninka/RU, 2026)

Popov & Popov (MIREA Russian University of Technology): best known attribution method achieves only **53.5% accuracy at agent level** and **14.2% at step level**. Attribution is largely unsolved — sign-off must be conservative about claiming causal attribution.

**5-Level Error Taxonomy:**
1. Input/context errors — malformed or missing information entering an agent
2. Reasoning errors — incorrect inference within a single agent step
3. Tool execution errors — incorrect tool call or wrong arguments
4. Inter-agent communication errors — misinterpretation of another agent's output
5. Emergent/cascade errors — agent A's error causes agent B to fail silently (hardest; cannot be attributed)

**3 Audit Strategies:**
1. Causal graph tracing (counterfactual interventions)
2. Shapley-value attribution (MACIE framework — quantifies each agent's contribution to failure)
3. Checkpoint-based replay (intermediate snapshots to narrow search space)

**Enriched inter-agent interface**: pass reliability metadata alongside results (confidence, error flags, source agent ID) — not just the result value. Level-5 cascade errors may not surface until a downstream consumer fails. Sign-off must check for independent verifiability of each subagent's output, not just aggregate success.

---

## Sign-Off Table Format

Before populating the sign-off table, run boundary-check to confirm all declared actions are complete and in-scope:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check \
    --task "<declared task goal>" --action "<final action taken>" \
    --prior-actions '["<a1>","<a2>","..."]'
  ```
  Exit 0: proceed to sign-off. Exit 1: mark incomplete items in table. Exit 2: OVER_ACTION. Exit 3: SCOPE_CREEP — flag in residual-risk column.

For L2+ tasks, verify the reasoning type used was appropriate:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<task>" --level <L>
  ```
  If frameworks used differ from what select-frameworks would recommend, note as process risk in sign-off.

Produce this table once before declaring the task complete:

| Component | Status | Evidence Handle | Residual Risk |
|-----------|--------|----------------|---------------|
| `<name>` | PASS / PASS WITH FIXES / DEFERRED / BLOCKED | `<commit SHA, path, URL, or command output>` | `<risk or "none">` |

Status definitions:
- **PASS** — completed and verified, evidence attached
- **PASS WITH FIXES** — completed with deviations, deviations documented
- **DEFERRED** — intentionally left for a later session, reason recorded
- **BLOCKED** — cannot proceed, blocker named and unresolved
- **SKIPPED** — explicitly out of scope, reason recorded

## Rules

1. Every row must have an evidence handle — no bare status claims.
2. PASS rows: evidence must be a verifiable artifact (path, SHA, URL, command + output snippet).
3. DEFERRED rows: must name what decision or resource is missing.
4. BLOCKED rows: must name the blocking condition and whether it is recoverable.
5. Residual risks must be concrete ("none" is only valid for PASS rows with complete coverage).
6. Do not collapse multiple components into one row to hide partial completion.

## Example

| Component | Status | Evidence Handle | Residual Risk |
|-----------|--------|----------------|---------------|
| Auth module tests | PASS | `pytest tests/auth/ -q` → 14 passed | none |
| Config schema update | PASS WITH FIXES | `~/.hermes/config.yaml` line 42: added `approvals.mode` | old installs missing key — migration note added |
| Dashboard integration | DEFERRED | Blocked on API token from user | Token needed before wiring live data |
| Legacy adapter cleanup | SKIPPED | Out of scope per task brief | Tech debt remains; track in issue |

## Action-Trace as Auditable Unit (arXiv:2608.11110, Sweep 11)

Cross-lingual policy retention study (2.38M rollouts, 8 models, 41 languages): agents produce
consistent final-answer accuracy across languages but substantially divergent action sequences.
**Final answers are NOT a reliable auditable artifact — action traces are.**

**Hermes implication for sign-off:**
- Every sign-off evidence handle must include the sequence of tool calls made, not just the output
- Format: `[tool_1 → tool_2 → tool_3] → output: <handle>`
- When the same task is run across multiple sessions/models, compare action sequences (not outputs) to verify policy consistency
- Skill triggers should use semantic embedding comparison over keyword matching to ensure language-invariant routing

**Updated sign-off table format:**

| Component | Status | Action Trace | Evidence Handle | Residual Risk |
|-----------|--------|--------------|----------------|---------------|
| `<name>` | PASS / PASS WITH FIXES / DEFERRED / BLOCKED | `[tool_1 → tool_2 → ...]` | `<commit SHA, path, URL>` | `<risk or "none">` |

Action trace column is REQUIRED for any PASS or PASS WITH FIXES row in a multi-agent run.
For single-step completions, a one-element trace is acceptable: `[skill_manage]`.

**Note:** For simple single-session tasks, the original 4-column format (without Action Trace) is sufficient.
Use the 5-column format (with Action Trace) for multi-agent runs or cross-language/cross-model tasks where policy consistency must be verified.

## Pitfalls

- Listing components without evidence handles (just saying "done" per row)
- Using PASS for work that was only locally tested but not verified in the target environment
- Collapsing several risky changes into one "infrastructure" row
- Omitting DEFERRED rows because they feel like failures — DEFERRED is honest, not shameful
- Using "none" for residual risk when the change touches shared state, config, or external APIs
- Omitting the action trace column for multi-agent or multi-step autonomous runs where policy drift is possible

## Action-Trace as Auditable Unit (Sweep 11 — MED)

Source: "Agent Behavioral Contracts" pattern (Sweep 11). The action trace — not the final output —
is the correct unit of audit for autonomous agents. Final output can look correct while the
intermediate action sequence violated policy.

**Hermes implementation:**
For any signoff row in the 5-column table, the "Evidence Handle" field MUST link to either:
1. A specific session message ID where the action was observed (from session_search), OR
2. A tool output (file diff, test result, terminal output) that proves the action occurred correctly.

"Observed in session" or "completed successfully" without a handle is NOT acceptable evidence.

**Extended signoff format for agentic traces:**
When reviewing an autonomous run (cron job, subagent, multi-step loop), add a sixth column:
`| Action Trace | <session_id>:<msg_id range> or <log_file>:<line range> |`
This makes the audit recoverable even after session compaction.

**Why this matters (arXiv:2608.12895 co-failure finding):**
Same-model multi-agent runs have phi=0.916 co-failure correlation — if the plan was wrong,
all agents executing it will fail in the same direction. The action trace is the only way to
detect systematic bias vs random errors across agent runs.

## Agent Reliability Evaluation Gap (arXiv:2507.21504, KDD '25) <!-- why: task success is an insufficient signoff criterion — reliability under failure is the missing dimension -->

LLM Agent Evaluation Survey (SAP Labs, KDD '25) identifies a systematic gap in agent evaluation:
most benchmarks measure task success but NOT agent reliability. Reliability = behavior under
partial information, error, and retry conditions.

**Three reliability dimensions to verify in sign-off (not just task success):**

1. **Retry/error recovery**: if a tool call failed mid-task, was the error handled gracefully or did the run halt? Sign-off must verify the retry path worked, not just the happy path.
2. **Graceful degradation**: when the task couldn't be completed fully, did the agent return a partial result with clear scope, or declare false success? Sign-off evidence must show what was NOT completed, not only what was.
3. **Partial information behavior**: did the agent proceed correctly when key inputs were missing, or did it hallucinate/assume? Multi-agent runs must document what information was assumed vs. explicitly provided.

**Add to sign-off table — reliability row:**

| Component | Status | Reliability Check | Notes |
|---|---|---|---|
| Error recovery | PASS / FAIL / N/A | Were tool errors retried with explicit backoff? | |
| Graceful degradation | PASS / FAIL / N/A | Does partial output acknowledge its scope? | |
| Partial info handling | PASS / FAIL / N/A | Were assumptions made explicit? | |

For simple single-agent tasks where no errors occurred: mark all three N/A.
For multi-agent or long-running autonomous tasks: the reliability row is REQUIRED.

Reference: arXiv:2507.21504, "Evaluation and Benchmarking of LLM Agents: A Survey", KDD '25.

## Relationship to Other Skills

- Run verification-before-completion BEFORE filling in this table — evidence handles come from that step.
- Run self-improve-agent AFTER this table is complete, using the DEFERRED/BLOCKED rows as input.
- For parallel agent runs, use hermes-agent-sync to collect typed JSON findings before building this table.

## Sweep 30 Additions (Aug 2026)

### Framework Bugs v4: Root Cause Distribution (arXiv:2602.21806, updated Aug 2026) ★ HIGH <!-- why: sign-off QA checklist was missing the dominant actual bug categories from empirical study of 2,823 agent episodes across 3 frameworks -->

Largest empirical study of agent framework bugs to date (updated Aug 2026). **76% of bugs = Incorrect Functionality** (not crashes). Root cause distribution:

| Root Cause | Share | Sign-off check |
|---|---|---|
| API misuse / contract violation | 31% | Did every tool call use the documented argument schema? Check one call per unique tool used. |
| Config / environment mismatch | 22% | Does the agent's assumed config match the actual runtime config? Spot-check one key assumption. |
| Parsing / serialization error | 18% | Are all structured outputs (JSON, YAML, schemas) validated at the boundary, not assumed well-formed? |
| Execution trace divergence | 14% | Does the agent’s internal plan match the actual sequence of tool calls made? |
| Reasoning / logic error | 9% | Standard sign-off catches this; no new check needed. |
| Other | 6% | — |

**Add to sign-off table — framework-bug row (required for any agentic run using 2+ distinct tools or 2+ sequential tool calls of any type):**

| Check | Status | Evidence |
|---|---|---|
## Coverage Audit for Silent Omissions (Denuto Pattern)

Source: Denuto `src/pipeline/coverage_audit.py`

After any multi-section analysis, verify that every top-level section has ≥1 finding.
Silent sections signal the agent skipped or missed content (the "lost-in-the-middle" failure mode).

**Rule**: Only fires when there are ≥10 top-level items. Short docs are skipped (signal:noise too low).

```python
def coverage_audit(sections: list[str], findings: list[dict]) -> list[str]:
    """
    Returns list of section names with zero findings.
    sections: top-level section names from the analyzed document
    findings: list of finding dicts with 'section' or 'clause' field
    """
    if len(sections) < 10:
        return []  # Short doc — skip audit
    covered = {f.get("section") or f.get("clause") for f in findings}
    return [s for s in sections if s not in covered]

# silent_sections → emit as soft "potential_issues" in sign-off
silent = coverage_audit(doc_sections, all_findings)
if silent:
    for s in silent:
        print(f"[COVERAGE GAP] Section '{s}' has no findings — possible silent omission")
```

**Add to sign-off checklist** (required for multi-section analyses):

| Check | Status | Evidence |
|---|---|---|
| Coverage audit | PASS / FAIL | Count sections with zero findings; list if any |
| API contract | PASS / FAIL | List one tool call + args verified against schema |
| Config match | PASS / FAIL | State assumed config value + verification command |
| Serialization boundary | PASS / FAIL | State where structured output was validated |
| Trace fidelity | PASS / FAIL | Planned steps vs. actual tool call sequence |

For simple single-tool tasks: mark all four N/A with a one-line justification.

Reference: arXiv:2602.21806, "A Study of Agent Framework Bugs", v4 Aug 2026.

## Sweep 29 Additions (Aug 2026)

### Governed Pass: Don't Self-Certify (github:Framework-Drift/governed-pass) ★ HIGH
1. Hash-lock the task contract at start — agent cannot change scope mid-run.
2. Agreement ≠ independence: reviewers sharing a spec find the same bugs.
3. Closed disposition vocabulary — decisions must be named (pass/repair/escalate), not free-form.
4. Heterogeneous adversarial review — use different model families (~$6.25 cross-model review, positive ROI).
5. Never self-certify: the agent that performed the task cannot be the final reviewer.

### AgentJudgeBench: Score Traces not just Outcomes (arXiv:2608.26623) ★ MED
Outcome-only scoring misses process failures. Score: tool selection appropriateness,
context management decisions, handoff quality, and irreversible action justification.

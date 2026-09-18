---
name: subagent-output-contract
description: Use when task has JSON output contract. Emit only JSON.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - A delegated task brief includes an OUTPUT CONTRACT section specifying a JSON Schema
  - Subagent receives task instructions ending with a machine-validated JSON response requirement
  - A prior response was rejected by an output contract validator
  - Task context includes "Your FINAL response must be a single JSON object"
metadata:
  hermes:
    tags: [delegation, subagent, output-contract, json, validation, schema]
    related_skills: [subagent-driven-development, agent-task-signoff, verification-before-completion]
ssl_scheduling:
  triggers:
    - Task brief contains OUTPUT CONTRACT with a JSON Schema
    - Response was rejected by output contract validator
  preconditions:
    - Task brief specifies a required JSON response schema
    - Work implementation is complete
  estimated_steps: 3
ssl_structural:
  tools_used: [terminal, read_file, search_files]
  subtasks:
    - Verify work state with read-only tool calls
    - Construct JSON object matching schema fields and types
    - Emit ONLY the JSON as the entire final response
ssl_logical:
  side_effects:
    - No side effects — governs response format only
  resources:
    - Task brief / output contract schema
  risk_level: low
related_skills:
  - verification-before-completion
  - plan
  - subagent-driven-development
  - agent-task-signoff
---

# Subagent Output Contract Compliance

Use this when a task specifies an OUTPUT CONTRACT requiring a JSON response.

## The Rule

When a task brief contains an OUTPUT CONTRACT section with a JSON Schema, the subagent's **entire final response** is ONLY the JSON object. Nothing before it, nothing after it.

```
# CORRECT — bare JSON, nothing else:
{"files_created": ["~/.hermes/scripts/foo.py"], "skills_patched": ["systematic-debugging"]}

# WRONG — prose before or after the JSON:
Here is the result of the task...
{"files_created": [...]}
The work is complete.
```

## Why This Fails

Any prose before the JSON causes an immediate parse error at character 0.

**Confirmed failure mode (Aug 2026):** Subagent completed all work correctly (5 SSL skill patches, template, validator — all PASS), then returned prose with embedded JSON. Validator rejected it. Work was correct; format was wrong.

## Workflow

1. **Read the output contract schema** — identify all `required` fields and their types.
2. **Verify the work state** with read-only calls (`terminal`, `read_file`, `search_files`) to confirm what was actually done. Do NOT rely on memory of prior tool calls.
3. **Populate field values** from verified state — not from assumptions or prior session memory.
4. **Emit ONLY the JSON** — no preamble, no summary, no sign-off, no "Here is the result".

## Recovery

If a retry prompt arrives with a JSON validator rejection:
1. Do NOT add prose to explain the fix.
2. Run verification checks (step 2 above) to confirm current state.
3. Return ONLY the corrected JSON object.

## Relationship to Sign-Off Skills

The `agent-task-signoff` sign-off table and narrative summaries are incompatible with a strict JSON output contract. The contract overrides all sign-off conventions. Sign-off tables are for sessions WITHOUT a strict output contract.

## Field Type Pitfalls

- `items: {type: string}` — every array element must be a string, not a nested object.
- `required: [...]` — those fields must be present even if empty (`[]` not omitted).
- `type: string` — a string, not an object or array.

Mental validation checklist before emitting:
- All `required` fields present?
- Array fields are arrays (not strings)?
- String fields are strings (not arrays)?
- Top-level value is an object (not an array or string)?

## GUIDE Pattern: Schema Validation on Receipt (arXiv:2608.12133, Sweep 12)

GUIDE multi-agent system uses schema-validated inter-agent contracts — each agent validates
its inputs before processing (not just validates its outputs before returning). 3,896 rules
processed, 96% task success with receipt validation in the paper's 6-agent system, 71.4% auto-approved with explicit HITL threshold (28.6%).

**Receipt vs produce:** Schema validation MUST happen on RECEIPT of the result — when the spawning agent first reads the returned result — not only at the point where the subagent produces output. Produce-time validation is necessary but not sufficient; receipt validation catches malformed results before they pollute downstream logic. <!-- why: prevents parent agents from merging unvalidated subagent JSON into later tool calls -->

**HITL escalation threshold (declare per task class in the skill / brief):** e.g. "if human review is consistently required for a task type (paper observed 28.6% HITL rate as a reference point, not a Hermes SLA), escalate: the task design itself is flawed, not individual outputs. No per-task-class HITL counter exists in Hermes yet - track manually during task development." Do not only escalate individual bad outputs — a high HITL rate is a design defect. <!-- why: prevents silent retry loops when the contract itself is underspecified -->

**Receiving-agent validation (add this to any agent that consumes another agent's output):**

```python
# WRONG — trust the subagent's output implicitly
result = delegate_task(goal="...", output_schema={...})
use_result(result)

# RIGHT — validate on receipt before using
result = delegate_task(goal="...", output_schema={...})
if not validate_schema(result):
    raise ValueError(f"Received malformed output: {result}")
use_result(result)
```

**Explicit HITL threshold declaration:**
- Define per task class the failure modes that require human escalation
- Don't silently default to "retry with the same subagent" for errors above the threshold
- When a subagent returns partial output (some fields valid, some null/missing), classify: is this a recoverable schema error or a task failure requiring escalation?

**Pattern for Hermes delegate_task:**
When receiving a subagent result with an `output_schema`, validate before using:
1. All required fields present?
2. Types match declared schema?
3. Values are internally consistent (e.g. evidence_handle exists for PASS rows)?
If validation fails → retry once. If second retry fails → ESCALATE to user, don't silently use malformed result.

Source: HN community (mh-, Aug 2025), confirmed by Anthropic structured-output docs.

Named fields act as implicit chain-of-thought scaffolding — more and more specific fields
force reasoning before output, reducing hallucination without explicit CoT prompts.

```json
// WORSE — single blob, higher hallucination risk
{"suggestion": "..."}

// BETTER — decomposed; model reasons through each field in sequence
{"reasoning": "...", "concise_suggestion": "..."}
```

When designing output schemas for subagents:
- Add `description` to every property — enforces intent and acts as inline CoT
- Avoid count-keeping formats (line numbers in diffs, character offsets) — use stable anchors instead
- Prefer ISO 8601 dates, enums, booleans over open strings wherever values are enumerable
- Use `anyOf`/`enum` over `type: string` for constrained value spaces

This is description-level poka-yoke: make the wrong output structurally difficult, not just discouraged.

## Schema Validation on Receipt, Not Just Output (arXiv:2608.11503) ★ HIGH — Sweep 12

Source: "Schema-Gated Subagent Orchestration". Key finding: subagents that produce schema-valid
JSON at the point of output still produce invalid data after the parent deserialises and merges
results — because the schema wasn't re-validated on receipt with the full merged context.

**The failure mode:**
1. Subagent A outputs `{"status": "done", "count": 3}` — valid against schema.
2. Parent merges A's result with B's result: `{"status": "done", "count": 3, "items": [...]}`.
3. Parent passes merged dict downstream without re-validating — `items` may violate the
   original schema's `additionalProperties: false` constraint.

**Fix — validate twice:**
```python
import jsonschema

# On subagent output (already done via output_schema):
jsonschema.validate(raw_result, SUBAGENT_SCHEMA)

# On receipt after merge/transform (NEW — add this):
jsonschema.validate(merged_result, PARENT_SCHEMA)
```

**Hermes implementation:**
When `delegate_task(tasks=[...])` returns results, always validate each result dict against
the task's `output_schema` before using it — don't trust that `schema_valid: true` in the
result metadata means the data survived post-processing intact.

For parent-level merging, define a `MERGED_SCHEMA` separately from the per-task schema and
validate the final merged structure before passing to downstream tools.

**Pitfall:** `schema_valid: true` in the delegate_task result only confirms the subagent's
raw output matched the schema at emit time. Any transform, merge, or dict access after that
point is unvalidated. Treat `schema_valid` as a receipt stamp, not a validity guarantee.

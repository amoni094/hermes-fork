---
name: symbolic-context-offload
triggers:
  - session has heavy tool output and context is bloating
  - need to preserve full traceability while reducing context size
  - long agentic task with many search/read/patch operations accumulating
  - want to inspect what the agent did in a tool-heavy session
  - canvas or mermaid offload or l1 extract or symbolic memory
description: >
  Use when: Locally-implemented TencentDB-style symbolic short-term memory: offload verbose tool output to disk, keep a Mermaid canvas in context. Also covers L1 atomic fact extraction via Anthropic API (claude-haiku-4-5). No local LLM deps.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [context, memory, mermaid, offload, l1-extraction, local, evidence-dossier]
    related_skills: [hermes-context-hygiene, hermes-memory-surface-selection, tencentdb-agent-memory, hermes-context-budgeting]
related_skills:
  - verification-before-completion
  - plan
  - hermes-context-hygiene
  - hermes-memory-surface-selection
  - tencentdb-agent-memory
  - hermes-context-budgeting
---

# Symbolic Context Offload (Local)

Local reimplementation of the TencentDB Agent Memory short-term offload pattern.
Two standalone Python scripts using Anthropic API (no local LLM required).

## Scripts

Both at ~/.hermes/scripts/:

- canvas-offload.py   — Mermaid canvas builder (offload tool output, build graph)
- l1-extract.py       — Atomic fact extractor (reads state.db, calls Anthropic claude-haiku-4-5)

Canvas stored at: ~/.hermes/canvas/<session_id>/canvas.md
Refs stored at:   ~/.hermes/canvas/<session_id>/refs/<node_id>.md
Facts stored at:  ~/.hermes/memory-facts/YYYY-MM-DD.md

---

## 1. Mermaid Canvas Offload

### When to use
- Active session has accumulated large tool outputs (search results, file reads, patch diffs)
- You need full traceability (can't use /compress — it's irreversible)
- Long agentic loop where you want the agent to reason over a graph not raw logs

### How it works

```
Verbose tool output -> offload to refs/<node_id>.md
                    -> extract key state into Mermaid graph node
Agent context       <- compact Mermaid canvas (hundreds of tokens, not thousands)
Agent recall        -> python3 canvas-offload.py --recall <node_id>  (full raw text)
```

### Usage

Offload a tool output blob:
```bash
echo "<tool output>" | python3 ~/.hermes/scripts/canvas-offload.py \
  --session <session_id> \
  --label "search:timeout-bug"

# Link to previous node:
echo "<tool output>" | python3 ~/.hermes/scripts/canvas-offload.py \
  --session <session_id> \
  --label "fix:add-timeout" \
  --rel "resolved" \
  --after <previous_node_id>
```

View current canvas:
```bash
python3 ~/.hermes/scripts/canvas-offload.py --session <session_id> --show
```

Recall raw detail for a node:
```bash
python3 ~/.hermes/scripts/canvas-offload.py --session <session_id> --recall <node_id>
```

List all sessions with a canvas:
```bash
python3 ~/.hermes/scripts/canvas-offload.py --list
```

Rebuild canvas from refs on disk:
```bash
python3 ~/.hermes/scripts/canvas-offload.py --session <session_id> --rebuild
```

---

## 2. L1 Atomic Fact Extraction

### When to use (L1 Facts)
- After a long session (5+ turns), extract durable facts before the session ends
- Run periodically via cron to build up a cross-session knowledge base
- Supplement Hindsight memory with a white-box readable file

### Requirements
- ANTHROPIC_API_KEY set in ~/.hermes/.env (used by l1-extract.py and l1-promote.py)
- ~/.hermes/state.db (Hermes session database)

### Commands (L1 Facts)
```bash
python3 ~/.hermes/scripts/l1-extract.py --dry-run --turns 6
```

Extract from most recent session:
```bash
python3 ~/.hermes/scripts/l1-extract.py --turns 6
```

Extract from a specific session:
```bash
python3 ~/.hermes/scripts/l1-extract.py --session 20260709_162948 --turns 8
```

View today's facts:
```bash
python3 ~/.hermes/scripts/l1-extract.py --show
```

## Automated pipeline (crons scheduled)

Three cron jobs were set up for the full pipeline. Current status:

| Job ID | Name | Schedule | What it does | Status |
|--------|------|----------|--------------|----|
| ebe4fd06d379 | l1-extract-periodic | every 3h | Runs l1-extract.py: extracts facts from recent session turns → memory-facts/YYYY-MM-DD.md | Active |
| a08989147b29 | l1-promote-periodic | every 3h | Runs l1-promote.py: scores facts → staging.md | **ACTIVE** (claude-haiku-4-5 via Anthropic API) |
| e034d0179aa9 | l1-hindsight-promote | every 4h | Agent cron: reads staging.md, calls hindsight_retain for each fact, clears staging.md | Active (but no input without promote step) |

l1-promote.py uses Anthropic API (claude-haiku-4-5) natively — no Ollama dependency. The cron job (a08989147b29) is active and healthy.
`hindsight_retain` directly for facts worth keeping.

Pipeline timing (when working): extract → (up to 3h) → score → (up to 4h) → Hindsight. Total lag ≤ 7h.

Check cron status: `hermes cron list --all`
Check staging queue: `python3 ~/.hermes/scripts/l1-promote.py --show`



---

## Relationship to "Think in Code" discipline

Canvas offload and evidence dossier handle outputs that have already been produced. The
"think-in-code" rule (hermes-context-hygiene) is the earlier intervention: avoid producing
bulk output in the first place by scripting the extraction. The two patterns compose:

1. FIRST: script the extraction (execute_code) — only the printed result enters context
2. IF bulk output still accumulates: canvas-offload to refs/<node_id>.md; keep graph in context
3. IF delegating multi-scout research: evidence dossier (write to /tmp/evidence/, pass gist+path)

Apply the relevant technique for your scenario — they address different situations, not a sequential fallback chain:
- Think-in-code (step 1): apply IN-SESSION, before bulk reads, to prevent accumulation
- Canvas offload (step 2): apply IN-SESSION, after bulk output has accumulated
- Evidence dossier (step 3): apply when DELEGATING research scouts, regardless of in-session state

They can also compose: scouts use evidence dossier, and the parent agent can canvas-offload the returned gist+path nodes.

## Pitfalls

- **Ollama is uninstalled (2026-07-12), l1-promote.py is RESOLVED**: l1-promote.py was
  updated to use Anthropic claude-haiku-4-5 natively. Both l1-extract.py and l1-promote.py
  now use Anthropic API exclusively. Do NOT attempt to reinstall Ollama.

- Session ID format: state.db uses full session IDs (e.g. 20260709_162948_30c474),
  not the prefix shown in hermes sessions list. The script supports prefix matching.

- Canvas is not automatically injected into context: you must explicitly show/recall.
  This is intentional — injection is the agent's responsibility.

## Layer integration

This skill connects to the broader Hermes memory stack. Routing authority: **hermes-memory-surface-selection**.

### Full data flow

See **hermes-memory-surface-selection** for the canonical stack diagram. Summary for this layer:

```
tool outputs → canvas-offload.py → refs/<node_id>.md + canvas.md (in-session)
session turns → l1-extract.py → memory-facts/YYYY-MM-DD.md (periodic)
             → l1-promote.py (claude-haiku-4-5 via Anthropic API) → staging.md (facts ≥2/3)
             → l1-hindsight-promote cron → hindsight_retain → Hindsight
```

### Promoting l1 facts to Hindsight

Automated: l1-promote.py + l1-hindsight-promote cron handle this. For manual promotion:
```python
hindsight_retain(content="<fact>", context="l1-extract", tags=["l1"])
```
Promote only facts scoring ≥2 on Recency/Utility/Uniqueness. Facts repeated across 2+ sessions graduate to durable memory via the `memory` tool.

### Canvas → session_search connection

Canvas refs at `~/.hermes/canvas/<session_id>/refs/`. Not indexed by Hindsight or Graphiti — ephemeral traceability only. Recovery: `canvas-offload.py --recall <node_id>`.

---




## Evidence Dossier Pattern (Compound Engineering, 2026)

A related but distinct technique from canvas offloading: when dispatching research scouts,
have each scout write verbatim evidence files to scratch storage rather than returning bulk
content inline. The orchestrator carries only a gist + path.

This is the difference between:
- Scout returns 40KB of raw search results → orchestrator context bloats
- Scout writes results to `/tmp/evidence/<node_id>.md` → orchestrator gets gist + path

### How to apply

When delegating research subtasks:

```python
# Instead of: delegate_task(goal="research X, return full findings")
# Do:
delegate_task(
    goal="research X. Write verbatim evidence (quotes, source links) to /tmp/evidence/X.md. Return only: 3-sentence gist + path.",
    context="evidence_path=/tmp/evidence/X.md"
)
```

The orchestrator then reads `/tmp/evidence/X.md` selectively — only when it needs specific
supporting detail, not by default.

**Key rule:** the orchestrator should never receive more than a gist from a scout unless
it explicitly retrieves the dossier. "Pass paths, not content" is the invariant.

**Axis-decomposed scouts:** for multi-axis research (e.g. security + performance + API contract),
each axis gets its own scout and its own evidence file. The orchestrator reads each file
independently, only pulling in the axes that are relevant to the current decision.

**When it beats canvas-offload:** canvas-offload is for in-session tool-output compression;
evidence dossier is for delegation context management. They compose — scouts write dossiers,
parent agent can also offload those paths to a canvas node for further compression.

## Comparison to /compress

| Aspect           | /compress          | canvas-offload         | evidence-dossier       |
|------------------|--------------------|-----------------------|------------------------|
| Traceability     | Lossy (summary)    | Lossless (refs/node_id)| Lossless (paths on disk)|
| Token cost       | One-time reduction | Per offload call       | Per delegation         |
| Agent visibility | Summary in context | Graph in context       | Gist + path in context |
| Debugging        | Hard               | Open refs/<node_id>.md | Read evidence file     |
| Use case         | Clean task breaks  | Long agentic loops     | Multi-scout delegation |

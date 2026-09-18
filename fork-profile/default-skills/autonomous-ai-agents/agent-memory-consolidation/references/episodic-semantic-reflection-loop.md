# Episodic → semantic reflection loop (Hermes)

Operational procedure for this skill. Papers: Generative Agents (Park 2023),
ExpeL (Zhao 2024), ReasoningBank-style trajectory banks, LeanMem (arXiv:2608.20320),
MemSIF Dual-Track (arXiv:2608.01742). Do not invent a second scoring stack or a
second MemSIF state machine — this is the agent-side loop; runtime promotion
still lives in `l1-promote.py` / `unified-recall.py`.

## Store map (keep these separate)

| Store | Kind | What belongs | What does not |
|---|---|---|---|
| Current context / compaction summary | working | live task state | durable facts |
| `session_search` (`state.db` FTS) | episodic | raw turns, tool traces | distilled rules |
| Capture JSONL inbox (`~/.hermes/logs/hermes-memory-capture.jsonl`) | episodic mid-term | claim-named session extracts | MEMORY.md dumps |
| Hindsight `context=event` or `record` | episodic | one fact-cluster or verbatim artifact | whole-session blobs |
| Hindsight `context=heuristic` / `profile` | semantic | transferable lessons, stable prefs | transcripts |
| `memory` tool / MEMORY.md (~2200 chars) / USER.md (~1600) | semantic (budgeted) | CoreFacts: prefs, corrections, standing constraints | event logs |
| Graphiti triplets | semantic relational | person–project–decision, tool–pattern–outcome | prose dumps |

Episodic = session-level, reconstructable, allowed to decay.
Semantic = cross-session distilled, promoted only after scoring + gates.

## When to trigger a reflection loop

Run the loop (do not wait for the user to say "consolidate") when **any** of:

1. **Task boundary** — a complex task finishes (success **or** failure).
2. **Pre-compact** — before compression eats the richest transcript. Live knobs:
   `compression.threshold=0.35`, `threshold_tokens=120000`, `protect_last_n=32`,
   micro-compact every 4 turns. If you are about to lose tool traces, retain first.
3. **Semantic shift** — the session topic changed (new project, new failure class).
   Flush the *previous* topic's candidates before starting the new one.
4. **Recurrence** — same entity/action/outcome appeared in ≥2 sessions (LeanMem).
5. **User ask** — "consolidate memory", "what should graduate", ReasoningBank / reflection.
6. **Child-agent return** — `delegate_task` / subagent finished with a durable lesson.
7. **Idle debt** — ≥3 sessions since last promotion pass (spot-check via `session_search`).

Skip: short/low-signal chats, already-promoted facts, secrets/PII, unverified web claims.

Completion criterion: every trigger above either ran the 7 steps or was explicitly skipped with a reason.

## Importance score (two formulas, do not mix)

**Retrieval ranking (Park 2023, Step 2 of SKILL.md):** sum after 0–1 scale.
`score = recency + importance + relevance` with `recency = 0.5 ** (hours/24)`.
Capture-time importance is integer 1–10, stored in `tags`.

**Semantic promotion gate (this loop):** product so a zero blocks write:

```
promote = recency × importance × relevance    # each factor in [0, 1]
```

| Factor | 1.0 | 0.5 | 0.0 |
|---|---|---|---|
| **recency** | happened this session / still true now | days–weeks old, still plausible | expired (old version, closed PR, "today only") |
| **importance** | user correction, standing preference, would change future action | useful but local | trivia, small talk, one-off |
| **relevance** | will be queried again (other sessions, other tasks) | maybe | tied to this transcript only |

Optional extras (do not replace the product):
- LeanMem: `consolidation_score = recurrence_count × importance` — still require recency and relevance > 0.
- Decay when ranking retrieval (ScrubJay-style): `value × exp(-π · age / τ)` — prefs π≈0.1, tool/config π≈0.5, versions/ports π≈0.9.

**Promote threshold:** `score ≥ 0.25` **and** (CoreFact **or** recurrence ≥ 2 **or** access_count ≥ 3).
Below that: keep episodic only (session_search / Hindsight `event`).

## ReasoningBank: log success AND failure

Do not bank only wins. A failure trace that names the wrong turn is higher-value than a success transcript.

For each candidate trajectory, write **one** Hindsight retain (not a session dump):

```
hindsight_retain(
  content="TRAJECTORY | outcome=success|failure | task=<one line> | what-worked-or-broke=<causal turn> | heuristic=When <trigger>, <action> because <reason>",
  context="trajectory-success"  # or trajectory-failure
)
```

Rules:
- Heuristic form only: `When [trigger], [action] because [reason].` Never "First I did X then Y".
- Pair a failure with the nearest later success on the same task class when you have both.
- Skill distillation (AMD skill tier) is separate: 3+ verified successes, no failures unaccounted for → `self-improve-agent` / `hermes-agent-skill-authoring`. This loop does not auto-patch skills.

## How to use hindsight_retain for semantic promotion

1. **Spot-check first** (`hindsight_recall` on the claim). Skip if already present. Atomix: tool-return ≠ settlement — a crash can duplicate retains.
2. **One topic per call.** Group by topic, not by wall-clock. Never one retain for a whole session.
3. **Tag `context`:**
   - `profile` — stable preference/correction (CoreFact; also consider `memory` tool if budget allows)
   - `event` — episodic fact cluster (ActiveFact; stays mid-term)
   - `record` — verbatim immutable (error text, API body)
   - `heuristic` — distilled semantic lesson (this is the promotion write)
   - `trajectory-success` / `trajectory-failure` — ReasoningBank traces
4. **Promote path:** episodic `event` → (score + LeanMem/MemSIF gate) → `hindsight_retain(..., context="heuristic")` → optional `hindsight_reflect` if several related events need a synthesis. Do **not** stuff MEMORY.md with event logs.
5. **Relations:** after a heuristic retain, add Graphiti triplets for new entity links (`mcp__graphiti__add_triplet`). Hindsight ≠ graph traversal.
6. **Poison gate:** 3 similar recalls; contradiction → human; new detail with 1 source → stage, do not promote.

Completion criterion: every promoted item has a Hindsight id/ack, a `context` tag, a score, and is **not** a raw transcript.

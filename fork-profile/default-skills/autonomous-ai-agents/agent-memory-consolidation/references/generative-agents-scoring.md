# Generative Agents scoring model → Hermes

Source: Park et al. 2023, *Generative Agents: Interactive Simulacra of Human Behavior*, arXiv:2304.03442, §4.
Procedure lives in `agent-memory-consolidation` SKILL.md (Step 2 + Reflective abstraction).
This file is the mapping and the gap list — do not duplicate the prompts here.

## Paper architecture

Memory stream = list of objects, each with natural-language description, creation timestamp, last-access timestamp. Three types, all retrieved together:

- **observations** — raw perceived events (leaves)
- **reflections** — higher-level inferences; may cite observations or other reflections (tree)
- **plans** — future action sequences (location + start + duration); written back into the stream

Retrieval (Park 4.1) is a **weighted SUM**, not a product. Each component is min-max scaled to [0, 1]; all α = 1 in the paper:

```
score = α_recency * recency + α_importance * importance + α_relevance * relevance
```

- **Recency**: exponential decay over hours since last **access** (paper decay 0.995 per sandbox hour). Hermes wall-clock proxy: `0.5 ** (hours / 24)` (~1-day half-life).
- **Importance**: LLM integer 1–10 at **creation time**. Mundane (breakfast) → low; poignant (breakup, college acceptance) → high. Example: cleaning room = 2, asking crush out = 8.
- **Relevance**: cosine similarity between memory embedding and query embedding.

A product of the three (sometimes cited in secondary write-ups) is **not** the paper formula. Product over-penalizes any near-zero component.

Reflection (Park 4.2) fires when the **sum of importance scores of latest events > 150** (~2–3 reflections per Smallville day). Procedure: 100 most recent records → 3 salient questions → retrieve per question → 5 cited insights → store as reflections.

Planning (Park 4.3) is top-down from a day sketch, recursively decomposed, then stored in the stream. Agents may replan on reaction.

Ablation: full architecture > no-reflection > no-reflection-or-planning. Each of observation, reflection, and planning contributes to believability.

## Hermes surface map

| Park component | Hermes surface | Fit |
|---|---|---|
| Memory stream | `hindsight_*` (semantic) + `session_search` (episodic/recency) | Split stream, not one DB |
| Observation write | `hindsight_retain(content, context, tags, occurred_at)` | No first-class importance field |
| Importance | `tags=["importance:N"]` only | **context= stores store-kind, not importance** |
| Relevance | `hindsight_recall(query)` embedding similarity | Present |
| Recency decay | `session_search(sort="newest")` only; no exp decay in Hindsight | **Missing** |
| Reflection | `hindsight_reflect(query)` | Present, **not auto-triggered** |
| Plans | none as a memory type | **Missing** |
| Obsidian live-sync | curated human rollup (`hermes-obsidian-sync`) | Not the memory stream |
| Graphiti | relational triplets, not the Park stream | Complementary |
| Durable MEMORY.md | 2200-char agent-facing notes | Not the stream |

`hindsight_retain` does **not** accept `importance`, `volatility_class`, or `valid_from`. Do not invent tool args. Store the 1–10 score in `tags` only (e.g. `tags=["importance:8"]`). The `context=` field stores store-kind (`event`, `heuristic`, `reflexion-failure`, `trajectory-success`, etc.) — never an importance blob.

## Gaps this skill closes vs remaining runtime gaps

Closed in this skill (procedural, agent-side):

1. Capture-time 1–10 importance prompt before every `hindsight_retain`
2. Reflection trigger: `ga_importance_sum >= 150` **or** `ga_retain_count >= 8`
3. Plan generation from reflections, retained as `ga-plan`
4. Local re-rank after `hindsight_recall` using recency + importance + relevance **sum**

Still missing in Hermes runtime (do not fake them):

1. Exponential recency decay inside `hindsight_recall` (last-**access** timestamp, not just `occurred_at`)
2. First-class `importance` argument on `hindsight_retain`
3. Automatic reflection cron that sums importance without this skill loaded
4. Plan objects as a typed Hindsight memory unit

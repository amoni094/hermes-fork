# Task Quality Log — Schema and Policy Iteration Procedure

Derived from: Puterman (MDP policy iteration on legal routes), Pearl (confounding;
observational ≠ interventional), Hastie/ESL (bias-variance, selection vs assessment,
curse of dimensionality), Jaynes (p-values are not posteriors; ordinal scores are
not interval), Boyd (do not optimize a nonconvex ratio), CLRS (greedy cheapest
feasible). Wald SPRT is a CONDITIONAL milestone, not current policy.

Purpose: accumulate labeled tasks per LEGAL ROUTE to run offline policy iteration.
Without this data, routing changes optimize intuition, not cost-per-completed-task.

---

## Log file location

~/.hermes/logs/routing-quality.jsonl  (append-only, one JSON object per line)

---

## Schema (one record per completed task)

The decision unit is a **route**, not a lone model. A Sonnet parent with Grok
workers is one route. Grok as session parent is illegal (stalls).

```json
{
  "ts": "2026-09-14T11:30:00+10:00",
  "task_id": "uuid-or-short-slug",
  "session_id": "hermes session ID if available",

  "task_type": "research_synthesis | tool_agentic | code_edit | math | extract | reasoning_ambiguous | long_context | adversarial",
  "intended_route": "sonnet_parent | sonnet_parent+grok_workers | opus_dedicated | devstral_dedicated | magistral_dedicated | sol_dedicated | luna_dedicated | aux_mistral",
  "actual_route": "sonnet_parent | sonnet_parent+grok_workers | opus_dedicated | devstral_dedicated | magistral_dedicated | sol_dedicated | luna_dedicated | aux_mistral",
  "route_reason": "parent_default | dedicated_session | delegation | aux_wired",
  "assignment_mode": "parent_default | dedicated_session | wired_aux | delegation | user_override | stall_escape | provider_fallback",

  "difficulty": 1,
  "difficulty_rated_at": "task_start",

  "quality": 4,
  "quality_source": "user",
  "completed": true,
  "stall_class": null,

  "input_tokens": 0,
  "output_tokens": 0,
  "cost_usd": 0.0,

  "notes": ""
}
```

Field rules:

- `difficulty` is about the TASK, not route performance. Rate at task start,
  before seeing output. If `difficulty_rated_at` is missing or `task_end`,
  exclude the row from policy iteration (Pearl: post-treatment).
- `intended_route` = what the table said. `actual_route` = what ran.
  If they differ, `assignment_mode` must not be `parent_default`.
- Table-following (usable as an observational route-performance estimate):
  `assignment_mode` in {parent_default, wired_aux, dedicated_session, delegation}.
  Exclude from PI: user_override, stall_escape, provider_fallback.
  This is NOT P(quality | do(route)). Causal claims need randomized assignment
  or a stated, tested ignorability assumption. None exists yet.
- `stall_class` is post-treatment. Do not condition on it when comparing routes.
- `quality` is ordinal 1–5. Do not divide it by cost.
- `quality_source`: `user` | `independent_family` | `same_session`.
  DPI (Shannon/MacKay): a score computed from the same output by the same parent
  cannot add information about route quality. Exclude `same_session` from PI.
  `independent_family` = Sol/Luna dedicated session rating another route's output.
  Prefer `user`. Missing quality_source fails `accept_line` (not in QSRC enum) and is
  dropped before PI — it is NOT reclassified as `same_session`; the prose note about
  same_session treatment is for lines that explicitly carry that value, not for missing fields.

Legal route mask (Puterman action space = executable legal routes only):

| task_type            | legal routes                                              |
|----------------------|-----------------------------------------------------------|
| tool_agentic         | sonnet_parent+grok_workers                                |
| research_synthesis   | sonnet_parent, sonnet_parent+grok_workers                 |
| code_edit            | sonnet_parent, sonnet_parent+grok_workers, devstral_dedicated |
| math                 | magistral_dedicated, sonnet_parent, sonnet_parent+grok_workers |
| extract              | aux_mistral                                               |
| reasoning_ambiguous  | sonnet_parent                                             |
| long_context         | opus_dedicated, sonnet_parent                             |
| adversarial          | sol_dedicated, luna_dedicated                             |

Illegal (never propose, never log as table-following success of a legal action):
- grok_parent / dedicated Grok session (Grok is workers only)
- mid-session switch, per-child model, magistral/devstral as delegation.model
- haiku as a chat parent (compression/vision only)

---

## How to log (manual, ~30 seconds)

Rate difficulty BEFORE starting. After the task completes, append one line.

Skip logging when value of information is zero (MacKay Ch 36: an observation has
value only if it can change the action):

- mechanical extract/title/triage unless it stalled
- any cell already at n=100 table-following rows
- any Stage A cell that is already feasible, cheapest among feasible legal
  routes for that task_type, AND holdout_n >= 10 (further rows cannot change
  the table under the adopt rule)

```bash
cat >> ~/.hermes/logs/routing-quality.jsonl << 'EOF'
{"ts":"2026-09-14T12:00:00+10:00","task_id":"research-sweep-001","task_type":"research_synthesis","intended_route":"sonnet_parent+grok_workers","actual_route":"sonnet_parent+grok_workers","route_reason":"delegation","assignment_mode":"delegation","difficulty":2,"difficulty_rated_at":"task_start","quality":4,"quality_source":"user","completed":true,"stall_class":null,"input_tokens":45000,"output_tokens":3200,"cost_usd":0.37,"notes":"arxiv sweep, 8 papers"}
EOF
```

---

## Coverage gates (Hastie curse of dimensionality)

8 task types × 3 difficulties × 8 routes is more cells than a solo workload
will fill. Do not add routing dimensions the data cannot support.

- **Stage A** (required before ANY table change): N >= 20 completed,
  table-following rows per `(task_type, actual_route)`. Pool difficulty.
  Flag pooled estimates as possibly confounded by difficulty mix.
- **Stage B** (required before a difficulty-specific row): N >= 20 completed,
  table-following rows per `(task_type, difficulty, actual_route)`.
- Until Stage B, do not add difficulty as a routing dimension.

Coverage code must use the same cell as the decision it authorizes.

```python
import json, pathlib
from collections import Counter
log = pathlib.Path("~/.hermes/logs/routing-quality.jsonl").expanduser()
records = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]

TABLE_FOLLOWING = {"parent_default", "wired_aux", "dedicated_session", "delegation"}

def table_following(r):
    return (
        r.get("completed")
        and r.get("difficulty_rated_at") == "task_start"
        and r.get("assignment_mode") in TABLE_FOLLOWING
        and r.get("quality_source") in {"user", "independent_family"}
    )

stage_a = Counter((r["task_type"], r["actual_route"]) for r in records if table_following(r))
stage_b = Counter((r["task_type"], r["difficulty"], r["actual_route"]) for r in records if table_following(r))
print("Stage A N>=20:", {k: n for k, n in stage_a.items() if n >= 20})
print("Stage B N>=20:", {k: n for k, n in stage_b.items() if n >= 20})
```

Closed enums (Thompson: parse, don't validate). Drop the line if any enum is unknown.
Do not coerce; do not include in PI.

```python
TASK_TYPES = {"research_synthesis","tool_agentic","code_edit","math","extract",
              "reasoning_ambiguous","long_context","adversarial"}
ROUTES = {"sonnet_parent","sonnet_parent+grok_workers","opus_dedicated",
          "devstral_dedicated","magistral_dedicated","sol_dedicated",
          "luna_dedicated","aux_mistral"}
ASSIGN = {"parent_default","dedicated_session","wired_aux","delegation",
          "user_override","stall_escape","provider_fallback"}
QSRC = {"user","independent_family","same_session"}

def accept_line(r):
    return (
        r.get("task_type") in TASK_TYPES
        and r.get("intended_route") in ROUTES
        and r.get("actual_route") in ROUTES
        and r.get("assignment_mode") in ASSIGN
        and r.get("quality_source") in QSRC
        and r.get("difficulty") in (1, 2, 3)
        and r.get("quality") in (1, 2, 3, 4, 5)
        and r.get("difficulty_rated_at") in ("task_start", "task_end")
    )
```

---

## Policy iteration — cheapest-adequate (not quality/cost)

State = `(task_type)` at Stage A, or `(task_type, difficulty)` at Stage B.
Action = legal route for that state.

Adequacy is Bernoulli: z = 1 if quality >= 3 AND completed else 0.

Feasibility uses the **Wilson 95% lower bound**, not the point estimate:

```
feasible iff n >= 20 AND wilson_lower(k, n, 0.95) >= 0.80
```

Cost is mean `cost_usd` over **every attempted row in the cell**, including
failures, stalls, and retries. Do not drop failed rows from the cost mean
(that credits cheap crashes).

Lexicographic choice (CLRS greedy cheapest-feasible; Boyd: quality/cost
ratio is retired):

1. Among feasible legal routes, pick minimum mean cost.
2. If none are feasible, keep the current table row (do not switch to a
   cheaper failing route). Optionally note the route with highest Wilson
   lower bound as a candidate for more logging, not as a live change.

### 1-SE rule (executable)

Let p_cur, n_cur be current-route adequacy point estimate and count on the
**training split**. SE_cur = sqrt(p_cur*(1-p_cur)/n_cur) if n_cur >= 20 else
undefined (no change).

Adopt candidate C over current only if ALL hold:

- C is legal for the task_type
- C is feasible (Wilson lower >= 0.80, n>=20)
- mean_cost(C) < mean_cost(current)  # all attempts
- p_C >= p_cur - SE_cur              # not worse than 1 SE of current point estimate
- Holdout test below passes

Prefer fewer table changes. If C equals current, no-op.

### Holdout (Hastie: selection vs assessment)

Do not shuffle (sessions are time-correlated). Split each compared route
time-ordered.

Adopt only if:

- holdout_n >= 10 for current AND for candidate
- holdout windows overlap in calendar time (both routes observed in the
  same period; otherwise the comparison is a period effect)
- holdout Wilson lower bound of candidate >= 0.80, OR candidate holdout
  adequacy >= current holdout adequacy

If N < 30 for either route, you cannot have 20 train + 10 holdout. Do not
adopt; keep logging.

```python
import math

ADEQUATE, FLOOR, Z95 = 3, 0.80, 1.96

def wilson_lower(k, n, z=Z95):
    if n <= 0:
        return 0.0
    p = k / n
    den = 1 + z*z/n
    centre = p + z*z/(2*n)
    margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)
    return (centre - margin) / den

def cell_stats(rows):
    n = len(rows)
    k = sum(1 for r in rows if r.get("completed") and r.get("quality", 0) >= ADEQUATE)
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    mean_cost = sum(costs)/len(costs) if costs else None
    p = k/n if n else 0.0
    se = math.sqrt(p*(1-p)/n) if n else None
    return {"n": n, "k": k, "p": p, "se": se,
            "wilson_lo": wilson_lower(k, n), "mean_cost": mean_cost}

def feasible(stats):
    return stats["n"] >= 20 and stats["wilson_lo"] >= FLOOR

def cheapest_adequate(candidate_stats):
    ok = {r: s for r, s in candidate_stats.items()
          if feasible(s) and s["mean_cost"] is not None}
    if not ok:
        return None  # keep current table row
    return min(ok, key=lambda r: ok[r]["mean_cost"])
```

Do not implement `reward = quality / cost_usd`. That estimator is retired.

---

## Stop logging a cell (current policy — not SPRT)

Per `(task_type, actual_route)` cell, stop prompting to log when n >= 100
table-following rows. Continue other cells. One full cell does not stop the
campaign (tail task types would never get data).

Do not use a t-test p-value, or any p-value, as a routing decision
(Jaynes / MacKay: p-values are not posterior probabilities).

---

## Milestone targets

- Week 1-2: log 5 tasks/day across >= 3 task types; difficulty at start;
  assignment_mode + actual_route filled. Skip mechanical extract unless stalled.
- Week 3-4: Stage A check; if a cell hits N=20, compute Wilson/cost vs current
  row. Do not adopt until holdout_n >= 10 on overlapping windows.
- Month 2: first full Stage A pass. Update a table row only if holdout agrees
  and the action is a legal route.
- Month 3: evaluate whether a RouteLLM-class learned router is worth building
  (needs N >= 200 labeled table-following tasks, balanced across types). Do not
  train on user_override / stall_escape / provider_fallback / task_end-difficulty.

---

## Future milestones (CONDITIONAL — not current routing rules)

1. RouteLLM-class router — blocked on labeled quality data (see Month 3).
2. Wald SPRT as a stopping rule — blocked on a dependence-calibrated test of
   H0: p = 0.80−δ vs H1: p = 0.80+δ, plus continued drift samples after stop.
   α=0.05 / β=0.20 / A=16 / B≈0.21 numbers must not be used as if observations
   were iid Bernoulli. Truncation at N=100 remains even if SPRT is later adopted.
3. Stage B difficulty-specific routes — blocked on 20 obs per
   (task_type, difficulty, actual_route) cell.
4. CRE Stage 2 trained QE classifier — blocked on 50+ labels per task type;
   LLM self-score is not a substitute.
5. Randomized route assignment for a causal (do-calculus) estimate — blocked
   on an explicit experiment. Observational PI is association among
   table-following rows only.
6. MacKay VoI auto-skip — once a cell hits n=100, stop prompting to log it.
   Manual skip rule above is the current stand-in.

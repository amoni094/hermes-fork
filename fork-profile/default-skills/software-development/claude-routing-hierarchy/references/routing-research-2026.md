# Routing Research Findings — 2026

## Cluster-Route-Escalate: Two-Stage Cascade for Cost-Aware LLM Serving (arXiv 2606.27457)

Practical cascade architecture that achieves 97-99% of the strongest model's accuracy at
significantly lower cost (TPOT reduced). Relevant for internalizing into the routing policy
and for any external pipeline work using multiple providers.

### Stage 1 — Cluster + Route
- Cluster incoming queries by content/difficulty (k-means or ModernBERT embeddings)
- Assign each cluster to its most cost-effective adequate model offline
- Set interpretable budget hyperparameter (cost-per-query cap) tuned offline on labeled data
- Uses only task-correctness labels, no per-query difficulty score needed

### Stage 2 — Quality-Estimation Cascade
- A lightweight QE classifier (ModernBERT, ~48 queries/s at 0.52ms/output-token overhead)
  judges whether Stage 1 output is good enough
- If low-confidence → escalate to a stronger model for that query only
- QE classifier adapts to model pool changes without manual reconfiguration

### Key Insight for Hermes Routing
Combine with the task-type routing dimension (see LLMRouterBench below). Step 1 is task-type
clustering (already partially done in the escalation policy via task keywords). Step 2 is the
missing piece: a post-generation quality check before returning a result, routing only
failed/uncertain outputs to a higher tier. Currently Hermes does not have this QE gate — it's a
forward-looking improvement requiring a small classifier or LLM-as-judge call to validate before
returning to the user.

**Current practical approximation:** CRE Stage 2 requires a trained classifier. Without one,
escalation must use deterministic rules only: fact inversion, schema/test failure, or task type
known to fail on Sonnet (see legal-routes table in SKILL.md). LLM self-scoring is not a valid
approximation — same-window confidence ratings have Spearman ~0.40 agreement with ground truth.
A trained QE classifier becomes viable once the task-quality log (references/quality-log-schema.md)
accumulates 50+ labeled examples per task type.

---

## LLMRouterBench Corrective Findings (arXiv:2601.07206, ACL 2026)

Research: 400K+ instances, 21 datasets, 33 models, 10 baselines. Shanghai AI Lab.

### Key Corrective Findings
1. Commercial routers often fail to beat a simple baseline under fair evaluation.
2. Larger ensembles show diminishing returns vs. careful model curation. Two well-chosen models > three poorly-matched ones.
3. Backbone embedding model choice has minimal impact on routing quality.
4. Main gap = model-recall failure: a model reliably failing specific query types. Characterize what sonnet fails at, route hard by task type.
5. Latency-aware routing is as valuable as accuracy-aware routing for interactive tasks.

### Hermes Implication
Current routing implicitly applies model-recall logic but it's undocumented. When a task type
fails repeatedly with sonnet, escalate by TASK TYPE not just by context length. The routing
decision is a session-start / dedicated-session table: (task type × context length) → model.
Not a per-call router.

---

## Corpus-derived offline procedures (2026-09-14)

Not a commercial router. Legal routes only.

- Cheapest-adequate policy improvement (CLRS greedy; Boyd: no quality/cost ratio).
- Two-stage coverage (Hastie curse): Stage A = (task_type, actual_route); Stage B adds difficulty.
- Pearl assignment_mode: exclude user_override / stall_escape / provider_fallback from PI.
- Stop logging a cell at N=100. Wald SPRT is CONDITIONAL (rows are not iid). Not a t-test p-value.
- Handoff weakest-precondition before dedicated sessions (Huth-Ryan).

See references/quality-log-schema.md.

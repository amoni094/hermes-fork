# Corpus Mining Waves — Routing Skill

Records of math/CS corpus applicability passes against claude-routing-hierarchy.
Each wave: books mined -> findings extracted -> adopted -> killed by adversarial -> net.

---

## Wave 1 (2026-09-14, subagent grok-4.6)

Books mined: jaynes-probability, puterman-mdp, wald-sequential-analysis, hastie-esl,
it-derived-algorithms, information-theory-for-agents, li-vitanyi-kolmogorov, clrs-algorithms,
pearl-causality

Findings extracted: 8
Adopted: 5
Killed by adversarial (Sol): 3

Net adoptions (survived Sol pass):

1. Legal route mask in schema (Puterman action space correctness)
   Artifact: quality-log-schema.md — legal route mask table added
   Sol verdict: SOLID (after fix: Grok dedicated row removed, stall_escape excluded)

2. Cheapest-adequate lexicographic policy (CLRS greedy; Boyd ratio retired)
   Artifact: quality-log-schema.md — PI procedure rewritten to Wilson/lexicographic
   Sol verdict: SOLID (after fix: cost mean over all attempts including failures)

3. Handoff weakest-precondition (Huth-Ryan {P} new_session {Q})
   Artifact: SKILL.md — four-field P gate on dedicated sessions
   Sol verdict: SOLID (after wave 2 fix: P is minimum, not maximum; extra context allowed)

4. Two-stage coverage gate (Hastie curse of dimensionality)
   Artifact: quality-log-schema.md — Stage A / Stage B gates
   Sol verdict: SOLID

5. Quality_source + DPI exclusion of same_session (Shannon/MacKay)
   Artifact: quality-log-schema.md — quality_source field, accept_line filter
   Sol verdict: WEAK -> fixed (missing ≠ same_session; accept_line drops before PI)

Killed by adversarial:
- SPRT as routing stop rule: NOT iid Bernoulli; session correlation invalidates α/β/A/B.
  Moved to CONDITIONAL milestone (future, needs dependence-calibrated test).
- Quality/cost ratio: nonconvex (Boyd). Retired. Replaced with lexicographic cheapest-feasible.
- Grok dedicated session as a legal route: illegal (Grok-as-parent stalls). Removed.

---

## Wave 2 (2026-09-14, subagent grok-4.6)

Books mined: shannon-1948, mackay-itila, cover-thomas-eit (partial), huth-ryan-logic,
thompson-type-theory, information-theory-for-agents (re-read)

Findings extracted: 5
Adopted: 4
Killed/downgraded by adversarial (Sol): 1

Net adoptions:

1. Worker/dedicated channel cap (Shannon DPI: parent transcript dump is not extra info once P written)
   Artifact: SKILL.md — explicit rule: do not paste parent transcript/traces into worker prompts

2. quality_source field (DPI operationalized)
   Artifact: quality-log-schema.md — same_session excluded from PI

3. Handoff P clarified as minimum not maximum (Huth-Ryan correction, Wave 2 Sol fix)
   Artifact: SKILL.md — "Additional context may be included beyond P"

4. Closed enum validation (Thompson type theory: parse, don't validate)
   Artifact: quality-log-schema.md — accept_line drops unknown enum values, does not coerce

Killed/downgraded by adversarial:
- MacKay VoI auto-skip: moved to CONDITIONAL (future milestone 6 in schema)

---

## Wave 3 (2026-09-14, parent agent claude-sonnet-4-6)

Books mined: boyd-convex-optimization, milewski-category-theory, gallager-itrc,
cover-thomas-eit (full), hermes-math-sweep-findings, hermes-cs-sweep-findings, arxiv-sweep-findings

7-step chain applied to each. Findings below ADOPT threshold:

- Boyd: quality/cost ratio retired in Wave 1. Lexicographic already implemented. SKIP.
- Milewski: routing table validated as pure function (sum type, no illegal inhabitants).
  Structural validation, not a new rule. SKIP.
- Gallager: cutoff rate R_0 analog = 900s/40s = 22-child saturation bound. Already
  implicit in 10-child stall guard. No new rule. SKIP.
- Cover-Thomas: DPI and Fano already implemented. Waterfilling analog: allocate more
  parallel workers to high-entropy (ambiguous) tasks. Not implementable without per-call
  routing. SKIP (illegal route).
- Sweep findings: no routing-applicable findings not already captured.

Net adoptions: 0

---

## Saturation signal

Wave 3 net = 0. Two consecutive sub-threshold results not yet reached (Wave 2 net = 4,
Wave 3 net = 0). However, the remaining corpus (gallager, cover-thomas full IT books)
produces only structural validations, not new implementable rules. Saturation declared on
domain exhaustion: remaining books are deep channel-coding theory with no Hermes routing
analog that survives the disanalogy stress test (routing is a discrete classification problem,
not a continuous channel with additive noise).

---

## Remaining CONDITIONAL items (need data before implementation)

1. RouteLLM-class learned router — needs N >= 200 labeled table-following tasks.
2. Wald SPRT stopping rule — needs dependence-calibrated test (sessions not iid Bernoulli).
3. Stage B difficulty-specific routes — needs 20 obs per (task_type, difficulty, route) cell.
4. CRE Stage 2 QE classifier — needs 50+ labels per task type.
5. Randomized route assignment for causal estimate — needs explicit experiment.
6. MacKay VoI auto-skip — manual skip rule is current stand-in.

---

Last updated: 2026-09-14

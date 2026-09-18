# Apply Protocol — Full Hermes System Surface

Research findings can land on ANY part of the Hermes system, not just skills.
For each HIGH-tier paper, identify every affected target and update all of them.

## Batch Abstract Triage (run before full chain on large paper sets)

When evaluating >10 new papers, do NOT run the full 7-step chain on every candidate.
Run a rapid triage pass first using abstracts to reduce the set:

  CHAIN  — plausible ALGORITHM/HEURISTIC with a visible Step 2 object/operation match.
            Fetch full text; run full chain from Step 0.
  REVIEW — possible HEURISTIC or borderline; abstract unclear.
            Fetch full text; run full chain from Step 0.
  SKIP   — clear THEOREM, EMPIRICAL, pure framework, or no structural mapping.
            Log SKIP, do not fetch full text.

Triage verdicts are NOT binding — the full chain overrides.
Do NOT implement from a triage-only verdict.

Fast SKIP signals from abstracts:
  - Primary verb: “prove,” “show that,” “establish,” “derive” → THEOREM → SKIP
  - Primary verb: “evaluate,” “benchmark,” “compare” with no new method → EMPIRICAL → SKIP
  - Requires fine-tuning / gradients / logits / model internals → Step 3 gate fires → SKIP
  - No concrete procedure (numbered steps, pseudocode, formula) → likely SKIP
  - Only shared vocabulary with Hermes ("agent", "memory", "context") with no structural mapping → SKIP

## Target Map

  Skills           skill_manage(action='patch', name='...')
  Runtime scripts  patch() or write_file() on ~/.hermes/scripts/*.py
  Config           patch() on ~/.hermes/config.yaml (or profile-level config)
  Memory pipeline  patch() on ~/.hermes/scripts/l1-*.py  [adversarial review required]
  Hooks            patch() on ~/.hermes/hooks/*.py
  Cron             terminal('hermes cron ...') for schedule changes or new watchdog jobs
  SOUL.md          patch() on ~/.hermes/SOUL.md  [very high bar: second model cross-review first]

Apply report: ~/.hermes/cache/research/hermes-research-apply-latest.md
Format per finding: paper -> signal extracted -> targets patched -> adversarial verdict

## Cross-Review Gate (AutoResearch, arXiv:2608.17906)

Before implementing any HIGH finding that touches scripts, config, or SOUL.md:
  1. Extract the concrete implementation claim from the abstract.
  2. Route to an adversarial model: 'Does this justify this specific change? What breaks?'
  3. Apply only if the adversarial model confirms net-positive and the scope is correct.

Rationale: the apply agent has high motivation to act; a cold independent model catches
cases where the paper's claim is narrower than the proposed system change.

## Confidence Bounds — OQRC (arXiv:2609.03104)

Occupancy-based Quantile Risk Control gives tighter finite-sample bounds than standard
conformal prediction for the same coverage guarantee. Use when a verification step
relies on empirical pass rates rather than formal proofs:
  coverage = 1 - alpha, where alpha = desired failure rate
  Required sample size is smaller than conformal prediction at equal guarantee.
  Prefer OQRC-style bounds over 'run N times and check pass rate' heuristics.

## Blocked Patches (user-owned skills)

If skill_manage patches are refused (user-owned / pinned / bundled), record blocked
findings in the apply report and note 'hermes curator adopt <skill-name>' for the
user to action. Do not skip the finding or silently drop it.

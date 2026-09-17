# Math Corpus Gaps: Fields Not Yet Ingested

Mapped against Hermes runtime objects (context compaction, skill routing, metacognition,
embedding retrieval, halting/stopping, memory decay, agent contracts). Updated when
corpus changes. Use this before buying or sourcing a new math text.

## Existing corpus (~/books/ + ingested skills)

| Field | Book | Status |
|---|---|---|
| Information Theory | Shannon 1948, MacKay ITILA, Cover & Thomas, Gallager, Li & Vitanyi, Lin & Costello | Ingested |
| Algorithms | CLRS | In ~/books |
| Category Theory | Mac Lane CWM, Milewski CTFP | In ~/books |
| Causal Inference | Pearl *Causality* (errata 37pp only — full book paywall) | In ~/books |
| Control Theory | Åström & Murray, Khalil *Nonlinear Systems* 3rd ed (767pp) | Ingested (Khalil: Sep 2026) |
| Dynamical Systems | Strogatz | In ~/books |
| Logic | Huth-Ryan, Harrison, Thompson *TTFP* (378pp) | In ~/books |
| Convex Optimization | Boyd & Vandenberghe (714pp), Luenberger (342pp), Peyre & Cuturi *Computational OT* (209pp), Villani *OT: Old and New* (969pp) | Ingested (OT: Sep 2026) |
| Probability | Jaynes (95pp draft only), Billingsley (608pp), Grimmett & Stirzaker *Probability and Random Processes* 4th ed (682pp) | Ingested (G&S: Sep 2026) |
| Statistics | ESL, Berger, DeGroot (498pp), Wald *Sequential Analysis* (222pp OCR) | Ingested (Wald: Sep 2026) |
| MDP / Sequential Decisions | Puterman *Markov Decision Processes* (666pp) | In ~/books |
| Functional Analysis | Kreyszig (703pp), Royden & Fitzpatrick *Real Analysis* 4th ed (516pp) | Ingested (Royden: Sep 2026) |
| Topology | Hatcher *Algebraic Topology* (560pp) | Ingested (Sep 2026) — NEW FIELD |
| Cryptography | Katz & Lindell *Introduction to Modern Cryptography* (649pp) | Ingested (Sep 2026) — NEW FIELD |
| Theory of Computation | Sipser *Introduction to the Theory of Computation* 3rd ed (482pp) | Ingested (Sep 2026) — was Tier-2 gap |
| Real Analysis / Measure Theory | Royden & Fitzpatrick *Real Analysis* 4th ed (516pp) | In ~/books |
| Topology | Hatcher *Algebraic Topology* (560pp) | In ~/books |
| Cryptography | Katz & Lindell *Introduction to Modern Cryptography* (649pp) | In ~/books |
| Computational Complexity | Sipser *Introduction to the Theory of Computation* 3rd ed (482pp) | In ~/books |

## Implemented waves (book-corpus → Hermes scripts)

### Wave 1–2 (prior session)
- Spikes S, T: entropy fields, calibration_log
- Skills patched: ralph-loops, trajectory-risk-guardrail, hermes-skillspector-guard-maintenance, hermes-swarm-consensus

### Wave 3 — Jaynes / Pearl / Åström / Li-Vitanyi
Scripts patched:
- metacognitive-harness.py: Laplace (s+1)/(n+2), log-odds blend (_to_db/_from_db), dB retry (_accumulate_evidence), OBS/DO causal tagging, compound prob, Occam specificity
- working-memory.py: hysteresis frame-switch, complementary filter [α=0.3], loop-variant tracking
- loop-pid.py: PID with anti-windup clamp (new)
- rr_compaction_spike.py: NCD/ΔZ demotion, compression quality report
- occam-skill-ranker.py: specificity field (new)

### Wave 4 — Boyd / Berger / ESL (15 proposals, adversarial KILL rate = 12/15)
Survivor weakenings applied to:
- loop-pid.py: gap-check and line-search relabeled as general cost-gap/step-acceptance utilities (false Boyd/Armijo docstrings corrected)
- metacognitive-harness.py: aic-rank help text corrected (penalized-error-ranking, not AIC/Cp); minimax-regret kept as-is (sound math regardless of infra)
- New scripts: skill-bootstrap.py, skill-admissibility.py, skill-stacking.py

### Wave 5 — Thompson / Puterman / Kreyszig / Luenberger / Billingsley / DeGroot
Patched:
- validate-skill-ssl.py: output_family optional linting (THOMPSON-1 weakened), ssl_logical.invariants linting (THOMPSON-6 weakened), forall-without-checker WARN not FAIL (THOMPSON-8 weakened)
- working-memory.py: variant-declare subcommand with nat_lt/lex_nat/finset_card orders; undeclared-variant changed from HALT to WARN+CONTINUE (critic-directed fix)
- [Puterman/Kreyszig batch implementing]: discounted evidence, VI/span stop, Banach contraction test, op-norm ranker, Hilbert residual gate, norm-blend scoring — IN FLIGHT

## Gaps — Tier 1 (highest structural fit to Hermes objects)

### Markov Chains (stochastic processes)
- **Norris, *Markov Chains*** — statslab.cam.ac.uk hosts selected sections only; NOT freely available. Buy from Cambridge UP (~£35).

## Gaps — Tier 2 (medium fit)

### Graph Theory
— **Diestel, *Graph Theory*** — immediate Graphiti application; website has chapter HTML previews only; full PDF ~€30 eBook at diestel-graph-theory.com.
- **West, *Introduction to Graph Theory*** — more accessible alternative.

### Nonparametric Statistics
— **Wasserman, *All of Nonparametric Statistics*** — calibration gaps (FOK/JOL without parametric model). ~270pp. Not freely available.

## Gaps — Tier 3 (theoretical grounding, slower payoff)

### Philosophy of Mind / Enactivism
- **Thompson, *Mind in Life***; **Clark, *Being There***; **Varela, Thompson & Rosch, *The Embodied Mind*** — Relevance Realization source texts. Only needed if RR transfer work resumes.

## Priority acquisition order

1. **Norris *Markov Chains*** — highest Hermes payoff (freshness, saturation modeling); buy Cambridge UP
2. **Diestel *Graph Theory*** — immediate Graphiti application; ~€30 eBook
3. **Wasserman *All of Nonparametric Statistics*** — calibration gaps

## Adversarial review kill-rate benchmarks (for calibrating future waves)

Boyd/Berger/ESL batch: 12 KILL / 3 WEAKEN / 0 KEEP out of 15 proposals.
Thompson TTFP batch: 5 KILL / 3 WEAKEN / 0 KEEP out of 8 proposals.

Common kill patterns:
- Infrastructure does not exist (loss table, session folds, derivation JSON, dispatch hook)
- 'Caller supplies the math' stubs: implementation takes the formal quantity as argument, does not compute it
- Vocabulary abuse: optimization names glued onto non-optimization objects
- Requires runtime hook that Hermes dispatch does not expose (ssl_* fields never read at runtime)
- Missing infra makes a whole chain collapse: BERGER-3 killed because BERGER-1 (loss table) killed first

Expected KEEP rate for a mature book corpus: ~1-3 per 8-15 proposals from a single book.
Saturation signal: falling KEEP rate across consecutive waves, not zero proposals.

---
name: hermes-math-research
description: 'Use when running the Hermes math sweep (categories 8-51). Not for querying past math verdicts (use hermes-math-sweep-findings). Not for core agent cats 1-7 (use hermes-research).'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [research, arxiv, math, theory, primers, sweep, pipeline]
    related_skills:
      - hermes-research
      - hermes-math-sweep-findings
      - arxiv-sweep-findings
      - hermes-cs-research
      - trajectory-research-synthesis-to-skills
      - spike
      - math-cs-applicability-reasoning
      - transfer-applicability-chain
triggers:
  - hermes math research
  - math sweep
  - run math papers
  - mathematical foundations sweep
  - math primers
  - math-paper-interpreter
  - run math research pipeline
  - hermes-math-sweep.py
  - math cron sweep
  - math categories research
  - NOT for core agent paper sweep (use hermes-research)
  - NOT for math findings bank (use hermes-math-sweep-findings)
  - NOT for CS/systems papers (use hermes-cs-research)
related_skills:
  - hermes-research
  - hermes-math-sweep-findings
  - arxiv-sweep-findings
  - hermes-cs-research
  - trajectory-research-synthesis-to-skills
  - spike
  - math-cs-applicability-reasoning
---

# Hermes Math Research

Math sweep pipeline: mathematical and theoretical foundations for LLM agents (categories
8-51). Runs separately from the core agent sweep, with its own seen-papers cache and
interpreter layer. NOT for core agent categories 1-7 (use hermes-research). NOT for CS
systems/engineering (use hermes-cs-research). NOT for past findings (use hermes-math-sweep-findings).

## Model Routing

Use **deepseek-v4-pro** (via `deepseek` provider) for long-horizon math synthesis tasks:

  Eligible: paper summarisation, applicability analysis, idea-to-script mapping,
  category sweeps where output is text/JSON (no execute_code/terminal loops).
  Command: `hermes chat -m deepseek-v4-pro --provider deepseek -q "..."`

  NOT eligible: math-paper-interpreter.py runs (uses hermes-fork venv + execute_code),
  multi-turn agentic tool chains — reasoning_content 400 bug in multi-turn tool calls.

  Fallback: grok-4.6 (delegate_task default) when DeepSeek is unavailable or rate-limited.
  Avoid Beijing peak hours (09:00-12:00, 14:00-18:00 CST) — 2x pricing surge.
  Non-think mode only (do not pass reasoning param).

## Math Categories (44 total, groups 8-51)

See hermes-research-sweep.py CATEGORIES dict for full arXiv query lists.

CLASSICAL MATHEMATICS (8-31)
  8.  Group Theory / Applied Algebra
  9.  Category Theory / Applied CT
  10. Information Theory / Rate-Distortion / Kolmogorov / IB
  11. Algebraic Topology / TDA
  12. Stochastic Processes / Causal Inference
  13. Game Theory / Mechanism Design / Social Choice
  14. Spectral Graph Theory
  15. Online Learning / Regret Minimisation
  16. Dynamical Systems / Fixed-Point / Bifurcation / Morse
  17. Formal Verification / Model Checking / Temporal Logic
  18. Description Logics / Computability / Domain Theory / Proof Complexity
  19. Information Geometry / Optimal Transport
  20. Combinatorics / Approximation Theory
  21. Generalization Theory (Concentration / PAC / PAC-Bayes / Empirical Processes)
  22. Verifiable Computation / ZK-Proofs / Interactive Proofs / Coding Theory
  23. Singular Learning Theory / Algebraic Geometry
  24. Formal Language Theory / Automata
  25. Multi-Agent Systems Theory (Queuing / Scheduling / Distributed / Comm Complexity)
  26. Computational Geometry
  27. Lattice Theory / Order Theory
  28. Convex Analysis
  29. Descriptive Complexity / Circuit Complexity
  30. Robust / Nonparametric Statistics
  31. Classical Graph Theory (Flows / Matching)

COMPUTATIONAL MATH / ML FOUNDATIONS (32-44)
  32. Randomized Algorithms / Streaming / Persistent Data Structures
  33. Compressed Sensing / Matrix Completion / Tensor Decompositions
  34. Neural Network Theory (NTK / Expressivity / Random Matrix)
  35. Geometric Deep Learning / Lie Groups / Equivariant NNs
  36. LLM Theory (ICL / CoT / Emergence / Scaling Laws / Attention)
  37. RLHF Theory
  38. Agent Adaptation Theory (Meta / Continual / Curriculum / Multi-Task / Imitation)
  39. RL Theory Comprehensive (PAC-MDP / Safe / Hierarchical / Inverse / Model-Based)
  40. Representation Learning Theory / Mechanistic Interpretability
  41. Uncertainty Quantification / Active Learning / Algorithmic Fairness
  42. Mixture of Experts Theory
  43. Federated Learning Theory
  44. Diffusion Processes / SDEs

SPECIALIZED (45-51)
  45. Monte Carlo Methods / MCMC
  46. Numerical Optimization Theory
  47. Fourier / Harmonic Analysis
  48. Time Series Analysis
  49. Mean Field Theory / Large Deviations
  50. Quantum Computing / Quantum Information
  51. Random Graphs

NEW THEORY CATEGORIES (52-59, added 2026-09-15)
  52. Measure Theory / Ergodic Theory — agent memory as measure; stationary distributions of agent states; mixing time
  53. Nonlinear Control Theory / Lyapunov / CLF — stability certificates for autonomous retry loops; CBF-based planning
  54. Optimal Transport / Wasserstein Geometry — KG embedding drift detection; memory consolidation as distribution merging
  55. Tropical Geometry / Max-Plus Algebra — min-cost skill graph routing as tropical shortest path
  56. Wavelet / Time-Frequency Analysis — multi-resolution context compression; non-stationary agent trajectory analysis
  57. Complexity Theory / Oracle Computability — hardness bounds for planning; query complexity of in-context learning
  58. Ring / Module Theory — structured scoring algebra for memory fusion; module homomorphisms for format-invariant retrieval
  59. Number Theory / Cryptography — ZKP-based tool-output attestation; hash-chain provenance; homomorphic skill evaluation

## Scripts

### hermes-math-sweep.py
Runs the core sweep restricted to math categories 8-51. Separate seen-papers cache.
Suppresses arxiv listing pages for math.*/stat.* (too noisy) - keyword queries only.

```bash
python3 ~/.hermes/scripts/hermes-math-sweep.py [--dry-run] [--limit N]
```

Outputs:
  ~/.hermes/cache/research/hermes-math-sweep-latest.json
  ~/.hermes/cache/research/hermes-math-sweep-filtered.json
  ~/.hermes/cache/research/seen_papers_math.json  (separate from main seen_papers.json)

### math-prefetch-abstracts.py
Pre-populates the sweep JSON with titles + abstracts using 8 concurrent threads.
Run this BEFORE math-paper-interpreter.py — the interpreter's --fetch-abstracts flag
is sequential (75 papers × ~8s = 600s) and times out; concurrent prefetch takes ~60s.

```bash
python3 ~/.hermes/scripts/math-prefetch-abstracts.py [--limit N] [--workers 8]
# Enriches hermes-math-sweep-latest.json in-place; safe to re-run.
```

Outputs: updates hermes-math-sweep-latest.json with title + abstract fields.

### math-paper-interpreter.py
Takes sweep JSON, filters to math categories, reads abstracts, produces OPTIMIZATION /
SPIKE / SKIP verdicts per paper.

```bash
# Step 1: populate abstracts concurrently (required before interpreter):
python3 ~/.hermes/scripts/math-prefetch-abstracts.py [--limit N] [--workers 8]

# Step 2: run interpreter (reads pre-populated abstracts, no fetch needed):
python3 ~/.hermes/scripts/math-paper-interpreter.py [--dry-run] [--limit N] [--input PATH]
# DO NOT pass --fetch-abstracts standalone — sequential fetch times out at >20 papers
```

Pitfall: make the seen-cache write UNCONDITIONAL (outside any `if results:` guard). All-SKIP batches must advance the seen window or the same dead papers re-screen on every run forever. The write belongs at the `if not args.dry_run:` level, not nested inside `if results:`.

Pitfall: flush the ideas queue AT the budget-guard break point, not only at normal completion. Ideas accumulate in `generated_ideas[]` during the loop; a budget-guard exit that only breaks without writing loses all Stage 3 output silently.

Pitfall: DO NOT use --fetch-abstracts when running the interpreter standalone. The
--fetch-abstracts flag fetches abstracts sequentially with a 0.8s sleep between each
call — 75 papers = ~600s wall-clock, which exceeds both the terminal() default 300s
timeout and the cron budget. The flag exists only for internal pipeline use and causes
EXIT:124 (SIGALRM) when the session timeout fires.

Correct standalone workflow: run math-prefetch-abstracts.py FIRST (8 concurrent workers,
~60s for 75 papers), THEN run the interpreter — it reads pre-populated abstracts from
the sweep JSON without any network fetch.

Background: hermes-math-sweep.py writes new_papers_flat to disk at end of Step 1
(sweep), BEFORE Step 2 (abstract fetch). The saved JSON has no titles or abstracts —
just arXiv IDs. Interpreter fast-skip gate fires on every paper that lacks a title/
abstract, producing 100% SKIP / 0 findings even from a healthy batch.

### Three-Stage Interpreter Pipeline (wired since Sep 2026)

The interpreter uses three stages. Stage 1 and 2 gate for direct applicability; Stage 3 generates implementable ideas from theorems that pass Stage 1 but fail Stage 2.

**Stage 3 — Theorem-to-Implementation Ideation (full-chain SKIPs only)**

When a paper reaches Stage 2 full-chain but returns SKIP (no direct component match), Stage 3 fires a separate haiku call asking: "given this theorem's mathematical structure, what concrete Hermes artifact could embody it?" This is distinct from SPIKE — a SPIKE maps to an existing component gap; a Stage 3 GENERATED_IDEA invents a new artifact seeded solely by the theorem's form.

Key distinction: Stage 3 does NOT fire on pre-filter (Stage 1) hard SKIPs — only on papers that passed Stage 1 MAYBE but were ruled out in Stage 2. Pre-filter hard SKIPs are genuinely irrelevant; Stage 2 SKIPs may still have extractable mathematical structure.

Output: `~/.hermes/cache/research/math-ideas-queue.json` (append-deduped by hermes_artifact name).
Each idea: math_structure, hermes_artifact, artifact_type, implementation_sketch, hermes_benefit, source metadata.

Budget-guard flush: ideas are written at the budget guard break point (270s), not just at normal completion. Without this, budget-guard exits (EXIT:124) silently discard all generated ideas.

**Stage 1 + Stage 2 details:**

The interpreter uses a two-stage gate to avoid spending the budget on full-chain calls:

  Stage 1 (pre-filter): haiku with max_tokens=5, timeout=10s, prompt asking MAYBE/SKIP.
    ~0.8s/paper. Papers not containing "MAYBE" in the response are immediately skipped.
  Stage 2 (full chain): haiku with max_tokens=600, timeout=20s, full structured output.
    ~10-17s/paper. Only runs on Stage 1 MAYBEs (~4-5% of papers).

Expected rates for 75 papers: ~60s Stage 1 + 3-5 × 10-17s Stage 2 = ~100-120s total.
If a 75-paper run hits exactly 300s wall-clock, the culprit is terminal() default timeout
(300s), NOT the API — Stage 1 is fast enough. Add `timeout=350` to terminal() calls.

Pitfall: the progress counter (every 5 papers to stderr) is bypassed by `continue`
statements inside the loop body. To diagnose where the loop stalls, add _loop_start =
time.time() BEFORE the loop and print elapsed time in the progress report. Also
initialise _loop_start before the for-loop or NameError fires on the first continue.


the sweep file shows papers with empty title fields, this is the cause — not a filter
calibration problem. Verify with:
  python3 -c "import json; d=json.load(open('~/.hermes/cache/research/hermes-math-sweep-latest.json'.replace('~', '/var/home/rainbow'))); print(d['new_papers_flat'][0])"

Outputs:
  ~/.hermes/cache/research/math-interpretation-latest.json  (all verdicts)
  ~/.hermes/cache/research/math-spike-queue.json            (SPIKE + OPTIMIZATION pending review)
  ~/.hermes/cache/research/math-ideas-queue.json            (Stage 3 generated ideas, append-deduped)

### math-primers-overnight.py
Generates or refreshes primer files for each math category.

```bash
python3 ~/.hermes/scripts/math-primers-overnight.py [--category KEY] [--force]
```

Primers: ~/.hermes/cache/research/primers/<category_key>.txt
Index:   ~/.hermes/cache/research/primers/INDEX.txt

New primers to generate (categories 52-59, not yet created — run math-primers-overnight.py --category <key>):
  measure_theory_ergodic, nonlinear_control, optimal_transport_geometry, tropical_geometry,
  harmonic_analysis_wavelets, complexity_theory_agent, abstract_algebra_rings, number_theory_cryptography

Existing primers (Sep 2026): agent_adaptation_theory, agentic_rag, algebraic_topology,
category_theory, combinatorics_approx, computational_geometry, convex_analysis,
descriptive_complexity, diffusion_processes, dynamical_systems, eval_uncertainty_fairness,
evaluation, federated_learning_theory, formal_verification_agent, fourier_harmonic,
game_theory, generalization_theory, geometric_dl, graph_flows_matching, group_theory,
information_geometry, information_theory, lattice_order_theory, llm_emergence_theory,
logic_semantics_agent, mean_field_large_dev, memory, moe_theory, monte_carlo_methods,
multi_agent, multiagent_systems_theory, neural_theory, numerical_optimization,
online_learning, quantum_computing, random_graphs, randomized_data_structs,
reasoning_planning, representation_interp, rlhf_theory, rl_theory_comprehensive,
robust_stats, self_improvement, singular_learning_theory, sparse_lowrank,
spectral_graph_theory, stochastic_causal, time_series_analysis, tool_use, verifiability

## Systematic Object-Type Mismatch Pre-Filter (2026-09-10 calibration)

From the Sep 2026 inverted-approach wave (81 papers, 9 targeted areas, 0 CHAIN): Hermes object types do not match the load-bearing structure of most current math corpus ALGORITHM papers. Apply this pre-filter before running the chain:

| Math object | Hermes analogue | Transfer verdict |
|---|---|---|
| Vector/set streams | Token sequences | MISMATCH — fixed-dim vectors != variable-length strings |
| Preemptive single-machine scheduling | Parallel async delegate_task | MISMATCH — Hermes is parallel+async |
| Cardinal payoff scores | Categorical string verdicts | MISMATCH — robust aggregation requires numeric scores |
| Dual virtual cache with hit/miss bit | Single context stream | MISMATCH — caching theory needs paired virtual occupancy |
| Static closed image corpus (CBIR) | Text-trace retrieval | MISMATCH — visual manifold != text kNN |
| Known finite-support reward distributions | Unbounded string outputs | MISMATCH — stochastic search needs known V_i |

If a paper's load-bearing structure maps to a MISMATCH row, SKIP at Step 2 without running Steps 3-6. Record the mismatch type. Further sweeps should target: lossy compression of variable-length token sequences with semantic distortion metrics; Bayesian categorical updating with unknown class count; aggregation of ordinal label strings without cardinal scores.

## Math Paper Interpretation Layer

Three verdict types:

  OPTIMIZATION - math sharpens an existing heuristic/threshold/policy.
  SPIKE        - math describes a structure Hermes doesn't exploit yet; needs experiment.
  SKIP         - no plausible Hermes analogue after honest assessment.

## Authoritative Interpretation Chain

math-paper-interpreter.py produces first-pass verdicts from abstracts only.
These are non-final. The chain (Steps 0–5 + manual Step 6) is the authoritative
verdict source and requires full paper text. Treat interpreter output as a queue
filler and filter only, not a final applicability decision.

All manual or agent-assisted interpretation of math papers runs the chain subject
to the trigger criteria below (not all papers require chain; see criteria):

  skill_view(name='math-cs-applicability-reasoning')

This skill is the authoritative source for OPTIMIZATION/SPIKE/SKIP verdicts.
Do NOT produce verdicts from the summary rules below alone — they are an
orientation guide only. Trigger criteria govern when to run the chain:
  - Script output is OPTIMIZATION or SPIKE -> always run chain before actioning.
  - Script output is SKIP but abstract mentions a concrete algorithm applicable
    to a named Hermes component -> run chain.
  - Script output is SKIP with no reviewer doubt -> do not run chain.
  - Pure math categories unlikely to produce ALGORITHM/HEURISTIC (math.AG,
    math.GN, math.NT, math.LO): skip chain unless the paper has explicit
    computational or algorithmic sections. Most SKIP at Step 1.

If cron ran without --fetch-abstracts: re-run interpreter with --fetch-abstracts
for any paper in the SPIKE/OPTIMIZATION queue before running the chain manually.
Full text is required (abstract-only = DEFER).
  - Step 0: neutral claim (forbidden vocabulary anchoring)
  - Step 1: abstraction level (THEOREM/ALGORITHM/HEURISTIC/FRAMEWORK/EMPIRICAL)
  - Step 3: feasibility gate (10 gates; run BEFORE Step 2 — see chain skill for full list)
  - Step 2: structural analogy + mandatory disanalogy (COMPONENT_MAP)
  - Step 4: measurability gate (existing metric required, not invented)
  - Step 5: desirability scoring
  - Step 6: asymmetric critic pass (cold session recommended for OPTIMIZATION)
  - Deterministic verdict formula

NOTE on step ordering: Steps are numbered by schema position, NOT execution order.
Execution order is: 0 → 1 → 3 → 2 → 4 → 5 → 6 (feasibility gate runs before structural analogy).

Access requirement: full paper text needed for Steps 0-3. Abstract-only = DEFER.

### Interpretation Orientation (complement to the chain, not a substitute)

1. Ask "what existing Hermes component has analogous structure?" first.
   The chain's Step 2 COMPONENT_MAP (closed object/operation taxonomy of 18 Hermes
   runtime components, defined in math-cs-applicability-reasoning) is the authoritative
   list. math-paper-interpreter.py may have its own simplified mapping table —
   treat that as a subset only.

2. OPTIMIZATION: need a concrete replacement formula or bound, not just "this improves X".
   Write the current heuristic and what the paper substitutes.
   Chain Step 4 requires naming an existing Hermes metric. Step 5 requires an
   estimated delta grounded in paper numbers (for des=2, same metric/same task setting).

3. SPIKE: must specify:
   - Given: which Hermes component currently uses flat/heuristic methods
   - When: which mathematical structure from the paper we apply
   - Then: a measurable improvement (latency, quality score, resource usage)
   Output to ~/.hermes/research/spikes/.
   Chain produces SPIKE when feasibility=1 or when a HEURISTIC has no named Hermes
   tunable parameter yet (spike is to find/confirm the parameter).

4. Workflow: run interpreter -> review SPIKE/OPTIMIZATION queue -> run chain (full
   text required; see Authoritative Interpretation Chain above) -> confirm with user
   -> run spike experiment (if SPIKE; see spike skill for experiment protocol) ->
   VALIDATED (spike confirms applicability): patch target ->
   INVALIDATED (spike disconfirms): log to hermes-math-sweep-findings.
   For any OPTIMIZATION verdict from the chain, run adversarial-review before patching.
   adversarial-review object: the proposed implementation (target component, current
   behavior, intended change, affected surface) — not the chain reasoning itself.

5. Low confidence + no citations = SKIP. Don't stretch.
   Chain Step 6 asymmetric critic can downgrade in two ways:
     OPTIMIZATION -> SPIKE (primary contribution transfer test fails)
     SPIKE -> SKIP (intuitive principle already implicit in Hermes, no new procedure)
   It cannot upgrade. See chain Step 6 for the full downgrade checklist.

### Feasibility Gate — Infrastructure-Buildable Rule (standing user preference)

The feasibility gate ABSOLUTE blockers are narrow. Do NOT fire SKIP for:
  - Iterative algorithms (implement as a Python loop)
  - State accumulation over time (implement as SQLite or JSON file updated each cron run)
  - Scoring functions or reward signals (implement as a Python function)
  - Graph or eigenvalue computation (implement with numpy/scipy)
  - Bandit state tracking (implement as JSON, reset-able per session)
  - Discrete structures, scheduling policies, priority functions

Only fire SKIP for genuinely irreducible blockers:
  (a) Gradient computation / backpropagation / weight updates
  (b) Direct model weight or activation access
  (c) Continuous per-turn training signal (not a cron-periodic update)

Rationale: "Hermes can build infrastructure for anything" is the standing user preference. Prompts that include "discrete state space", "iterative training", or "requires a scoring function" as SKIP criteria systematically discard valid Track B papers. The distinction is between what Hermes *is* (prompt-only) and what Hermes *can build* (anything in Python/SQLite/numpy/cron).

### Two-Track Evaluation Model

Every paper is evaluated on TWO tracks, not one:

Track A — IMPROVEMENT: Does the paper improve an existing Hermes component?
  Target format in results: any existing script/skill name
  Verdict: OPTIMIZATION (if heuristic/algorithm fits directly)

Track B — NEW CAPABILITY: Does the paper enable a capability Hermes does not yet have?
  Target format in results: "new: <short capability name>"
  Verdict: SPIKE (prototype needed before committing)
  Examples of valid new capabilities:
    - new: formal plan verification (pre-execution action-sequence checker)
    - new: causal error attribution (post-mortem session causal graph)
    - new: optimal stopping for subagent fan-out (commit threshold)
    - new: calibrated uncertainty over retrieved facts (confidence intervals)
    - new: online convex optimisation for adaptive per-turn hyperparameters
    - new: ZK-attestation for tool outputs (verifiable tool-call proofs)
    - new: CBF constraint layer for irreversible-action prevention
    - new: Wasserstein memory drift alarm
    - new: wavelet multi-resolution context compressor
    - new: query-complexity certificate for skill-router

Pre-filter (Stage 1, max_tokens=5) passes MAYBE for EITHER track.
Full chain (Stage 2) runs Step 2b after Step 2 to check Track B if no existing component matched.

### Math -> Hermes Component Map (summary)

  algebraic_topology       -> skill library redundancy (TDA on embeddings)
  information_geometry     -> embedding space retrieval curvature, routing geometry
  online_learning          -> adaptive model routing (bandit), skill success tracking
  game_theory              -> multi-agent coordination, adversarial review design
  spectral_graph_theory    -> skill dependency graph health metrics
  stochastic_causal        -> memory write decisions, tool side-effect modeling
  generalization_theory    -> agent eval confidence bounds (PAC-Bayes, conformal)
  formal_language_automata -> structured output grammars, tool-call FSM modeling
  information_theory       -> context compression ratio, skill selection entropy
  convex_analysis          -> agent optimization objectives, loss landscape assumptions
  combinatorics_approx     -> context packing (bin-packing), token budget optimization
  random_graphs            -> knowledge graph robustness, skill library growth modeling
  measure_theory_ergodic   -> memory retention guarantees; ergodic session-independent recall; agent state stationarity
  nonlinear_control        -> Lyapunov-safe retry escalation; CBF-based planning constraints; loop-pid.py upgrade path
  optimal_transport_geometry -> KG embedding drift (Wasserstein distance); memory merge as Wasserstein barycenter; Sinkhorn skill routing
  tropical_geometry        -> skill-graph min-cost routing as tropical shortest path; idempotent planning semiring
  harmonic_analysis_wavelets -> multi-resolution context compression; wavelet-domain token stream analysis
  complexity_theory_agent  -> hardness of agent planning; query complexity of skill retrieval; oracle tool models
  abstract_algebra_rings   -> ring-based memory score fusion; polynomial query expansion; graded retrieval algebra
  number_theory_cryptography -> ZKP tool-output attestation; hash-chain integrity (l1-tracegrant.py); homomorphic skill evaluation
  dynamical_systems        -> agent loop fixed-point detection, context compression stability
  monte_carlo_methods      -> agent belief estimation, memory consolidation sampling
  numerical_optimization   -> skill scoring function optimization, fine-tuning convergence
  rl_theory_comprehensive  -> safe action bounds, PAC-MDP for cron agents
  category_theory          -> memory pipeline composition, skill routing as functor
  multiagent_systems_theory -> cron job scheduling theory, delegate queue modeling
  mean_field_large_dev     -> failure rate estimation for large agent fleets
  (full map: COMPONENT_MAP in math-cs-applicability-reasoning, Step 2)

## Generated Ideas → Implemented Scripts (2026-09-15)

Stage 3 ideation produced 42 math + 20 CS ideas. Top tier implemented as runnable scripts.
All scripts require `/usr/bin/python3` (system Python with numpy 2.4.6 + scipy 1.18.1).
The hermes-fork venv has NO pip and NO numpy — never run these with the venv python.

Run pattern:
  /usr/bin/python3 ~/.hermes/scripts/<script>.py [--dry-run]

Implemented scripts (all verified running, Sep 2026):
  circuit-trajectory-scorer.py      — mines 553 sessions, 1253 circuits, freq × outcome score
  session-stability-monitor.py      — Lyapunov V_t over tool embeddings + KL; writes stability.db
  frequency-stability-monitor.py    — Lyapunov energy over routing scores + memory entropy
  duality-gap-monitor.py            — primal/dual gap certificate; fired real alarm at 69% gap
  uncertainty-calibration-monitor.py — calibration error per skill from session logs
  cascade-error-budget-allocator.py  — branching-process verification budget by cascade bound
  retrieval-saturation-monitor.py    — detects hindsight_recall over-retrieval (already firing)
  consensus-convergence-monitor.py   — JS divergence between session tool distributions

All write to ~/.hermes/cache/ and ~/.hermes/memory-facts/stability.db.
Alarm files: stability-alarm.json, freq-stability-alarm.json, duality-alarm.json,
             calibration-alarm.json, cascade-risk.json, retrieval-saturation-alarm.json,
             consensus-alarm.json

Remaining high-value ideas not yet implemented (from math-ideas-queue.json):
  soft_bellman_skill_router.py, entropy-fidelity-stability-monitor.py,
  regime-transition-monitor.py, sybil_risk_monitor.py, factor_attribution_skill.py

## Cron Integration

  cron name: hermes-math-sweep       — Tuesdays 01:00 (cc67685ee9bd)
  script:    hermes-math-sweep.py
  no_agent:  true (pure Python)
  deliver:   local
  frequency: weekly (Tuesdays)

  cron name: hermes-math-interpret   — Tuesdays 06:30 (see hermes cron list)
  script:    math-paper-interpreter.py
  no_agent:  true (pure Python)
  input:     hermes-math-sweep-latest.json (SWEEP_LATEST patched 2026-09-09)
  deliver:   local
  frequency: weekly (Tuesdays, 5.5h after sweep)

## Handoff

These steps assume the Authoritative Interpretation Chain has already been run
(see 'Math Paper Interpretation Layer' section above). Do not route to findings
banks without first running the chain for OPTIMIZATION and SPIKE verdicts.

- OPTIMIZATION: before writing any patch, run adversarial-review on the proposed
  change (target component, current behavior, intended new behavior). Review object
  is the implementation plan, not a patch — no patch exists yet at this stage.
  After review, log to hermes-math-sweep-findings. Do NOT skip adversarial-review.
- SPIKE: -> hermes-math-sweep-findings (pending). VALIDATED spikes ->
  trajectory-research-synthesis-to-skills for skill patches (adversarial-review
  applies before the resulting patch is finalized).
  VALIDATED/INVALIDATED: see 'spike' skill for the experiment process.
- SKIP/DEFER: log to hermes-math-sweep-findings with reason.
  DEFER (abstract-only): re-run interpreter with --fetch-abstracts for papers in
  SPIKE/OPTIMIZATION queue, then re-run chain. Log DEFER with 'requeue' note, not final.
  DEFER (config inaccessible): re-evaluate when config is readable.
- Non-math agent findings -> arxiv-sweep-findings

## Skill Write Ownership (Class H safety)

  hermes-math-research -> read/routing only, no skill_manage writes
  trajectory-research-synthesis-to-skills -> owns all skill_manage writes

Never call skill_manage directly from this skill.

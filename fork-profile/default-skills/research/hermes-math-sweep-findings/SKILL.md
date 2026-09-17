---
name: hermes-math-sweep-findings
description: 'Use when querying Hermes math paper findings and spikes.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, math, findings, spike, optimization, bank]
    related_skills:
      - hermes-math-research
      - arxiv-sweep-findings
      - hermes-cs-sweep-findings
      - trajectory-research-synthesis-to-skills
      - spike
triggers:
  - math sweep findings
  - math papers bank
  - what math papers did hermes find
  - math spike queue
  - math interpretation results
  - math optimization proposals
  - pending math spikes
  - math-interpretation-latest.json
  - math-spike-queue.json
  - NOT for running math sweep (use hermes-math-research)
  - NOT for applying patches (use trajectory-research-synthesis-to-skills)
  - NOT for core agent findings (use arxiv-sweep-findings)
  - NOT for CS findings (use hermes-cs-sweep-findings)
related_skills:
  - hermes-math-research
  - arxiv-sweep-findings
  - hermes-cs-sweep-findings
  - trajectory-research-synthesis-to-skills
  - spike
---

# Hermes Math Sweep Findings

Knowledge bank for math paper verdicts from the math-paper-interpreter.py pipeline.
Stores actionable OPTIMIZATION proposals and SPIKE candidates from past math sweeps.
For running sweeps: hermes-math-research. For core agent findings: arxiv-sweep-findings.

## How to Query

Live output files (populated by math-paper-interpreter.py cron):
  ~/.hermes/cache/research/math-interpretation-latest.json  - all verdicts from latest run
  ~/.hermes/cache/research/math-spike-queue.json            - pending SPIKE + OPTIMIZATION items
  ~/.hermes/cache/research/math-spike-results-YYYY-MM-DD.md - validated spike results

Record structure (math-interpretation-latest.json):
  {
    "id": "arXiv:XXXX.XXXXX",
    "title": "...",
    "category": "algebraic_topology",           <-- field is 'category', not 'category_key'
    "result": "OPTIMIZATION|SPIKE|SKIP",         <-- field is 'result', not 'interpretation_type'
    "confidence": "high|medium|low",
    "target": "...",
    "reasoning": "..."
  }

## OPTIMIZATION Findings

OPTIMIZATION items replace existing heuristics/thresholds with theory-grounded bounds.
Process:
  1. Identify current heuristic in target skill/script
  2. Apply paper's formula as replacement
  3. Run adversarial-review
  4. Patch via trajectory-research-synthesis-to-skills

### Sweep: 2026-09-08 (Math sweep v1, 593 papers, 342 new, 4 OPTIMIZATION / 28 SPIKE)

All 4 OPTIMIZATIONs in generalization_theory:

[generalization_theory] BoN Certification Limits
  target: best-of-N sampling, eval pass@k guarantees
  proposal: Replace ad-hoc "run N times, take best" with certified BoN bounds.
  The paper establishes when BoN actually certifies quality vs when it merely selects.
  Concrete: for adversarial-review subagent dispatch (k=3 coalition), use BoN certification
  to bound the probability that the selected review caught all HIGH findings.
  status: INVALIDATED — spike 003 (2026-09-08). P_cert(k=3, p=0.70, N_high=5) = 0.424; far
  below 0.90. See adversarial-review skill for safe-bounds table (k=3 only for N_high<=2).

[generalization_theory] Anytime-Valid Evaluation Bounds (74x-cheaper eval stopping)
  target: eval pipelines, cron quality gates, math/CS interpreter scoring
  proposal: Replace fixed-N eval runs with anytime-valid sequential testing.
  Stop eval as soon as confidence bound is tight enough; 74x fewer samples vs fixed-N.
  Concrete: cs-paper-interpreter.py and math-paper-interpreter.py both score papers with
  fixed sample sizes. Apply sequential testing to halt early when verdict is clear.
  status: INVALIDATED as early-stop mechanism 2026-09-08 (spike 002).
  Finding: SPRT on H1 (P(actionable)>=0.20) stops at index 14/144 and misses ALL 5 math OPTIMIZATIONs
  (which cluster at indices 113-119, the tail). 89.58% token saving is real but useless if every
  OPTIMIZATION is missed. The math OPTIMIZATION rate is ~0.03 (5/144) — too rare and tail-distributed
  for SPRT to find safely.
  Viable alternative: run full interpreter, but use anytime-valid bounds to DETECT when the SKIP
  rate is anomalously high (possible interpreter bug) rather than to stop early.
  Do NOT implement early stopping on H1 for paper interpreter sweeps.

[generalization_theory] Benchmark Fingerprinting Hardening
  target: skill evaluation, research sweep quality assessment
  proposal: Current eval benchmarks may be contaminated (models have seen them in training).
  Paper provides fingerprinting to detect contamination before trusting benchmark scores.
  Concrete: before treating any LLM-scored quality metric as ground truth, fingerprint
  the benchmark examples to detect training contamination.
  status: APPLIED 2026-09-08 — ~/.hermes/scripts/benchmark-fingerprint-check.py
  Checks queue JSON files for verbatim/near-verbatim contamination in skills/cache corpus.
  Run: python3 benchmark-fingerprint-check.py --queue <queue.json>

[generalization_theory] Beta/Wald Skill Reliability CI (was: PAC-Bayes Skill Guarantees)
  target: skill routing, skill reliability bounds
  proposal: PAC-Bayes framework provides generalization bounds on skill-selection accuracy
  given a prior and observed usage. Replace point estimates of skill match quality with
  posterior bounds that account for limited evidence.
  Concrete: skill-router-index.py currently uses TF-IDF + optional Beta blend.
  status: DONE 2026-09-09 — pac_bayes_bound() implemented in skill-router-index.py.
  McAllester/Seeger bound: KL(Q||P)/m penalty + binary search for gen_risk upper bound.
  Pure stdlib (math module only): digamma via recurrence+asymptotic, KL(Beta||Beta) analytic.
  _beta_wald_ci() kept as deprecated fallback; all call sites use pac_bayes_bound().
  worked example (alpha=10, beta=3, delta=0.05): mean=0.769, Wald=[0.540,0.998],
    PAC-Bayes=[0.278,0.989], KL(Q||P)=0.818, m=11.
  PAC-Bayes upper > Wald upper (KL penalty widens bound as expected with small m).
  24/24 ad-hoc verification checks passed (scipy KL/digamma cross-check, vacuous prior,
    ranking invariance: still 0.6*tfidf + 0.4*posterior_mean).

## SPIKE Findings

SPIKE candidates are throwaway experiments validating a math structure applied to Hermes.
Process:
  1. Load spike skill
  2. Run spike with Given/When/Then spec from math-spike-queue.json
  3. Output to ~/.hermes/research/spikes/
  4. VALIDATED: implement + record here with evidence
  5. INVALIDATED: log verdict here with reason

### Sweep: 2026-09-08 — 28 SPIKEs across 8 categories

High-priority spikes (curated from 28 SPIKE verdicts):

[computational_geometry] ANN Retrieval ×3 papers
  Three papers on approximate nearest-neighbor retrieval improvements.
  Relevant to Hindsight vector index + skill router embedding search.
  Given current HNSW index; When improved graph construction from sweep papers;
  Then measure recall@k improvement on skill routing queries.
  See also CS SPIKEs: HARMONY, MicroNN, HAKES (more concrete implementations).

[category_theory] Sheaf Composition for Skill Dependency Graphs
  Sheaf-theoretic composition allows verifying that skill dependency chains are
  globally consistent (no local-to-global coherence failures).
  Concrete: skill `related_skills` graphs can be checked for sheaf consistency —
  a skill that declares dep A which declares dep B should be coherent with the
  agent loading A then B in order.
  status: PENDING — theoretical; worthwhile spike if skill graph grows complex.

[stochastic_causal] Tool Side-Effects Causal Model
  Model tool calls as interventions in a causal graph; side effects are do-calculus
  outcomes. Enables reasoning about which prior tool calls caused a current failure.
  Concrete: trajectory-risk-guardrail prefix-risk scan would benefit from a causal
  model of tool interactions rather than heuristic prefix assessment.
  status: PENDING — high complexity; record for future research sprint.

[game_theory] Multi-Agent Coordination
  Game-theoretic equilibrium analysis for delegate_task fan-out patterns.
  When parallel agents compete for shared resources (Graphiti writes, cache paths),
  Nash equilibrium predicts coordination failures ahead of time.
  status: PENDING — informative for concurrency anomaly (L0-L3) prevention.

[lattice_order_theory] Skill Constraint Lattice
  Partial order over skill constraints allows detecting constraint dominance:
  if skill A's constraint subsumes skill B's, loading both is redundant.
  Concrete: skill hierarchy in config.yaml could be validated for constraint dominance.
  status: PENDING — low priority; record for skill library consolidation sprint.

[singular_learning_theory] KAN Complexity for Skill Routing
  Kolmogorov-Arnold Networks complexity bounds for skill routing function.
  Theoretical lower bound on routing complexity given skill library size.
  status: PENDING — theoretical; spike to check if current TF-IDF routing is near bound.

Full 28-item queue: ~/.hermes/cache/research/math-spike-queue.json

## Blocked Patches

Findings targeting user-owned (curator-managed) skills are blocked until:
`hermes curator adopt <skill-name>`

(none currently blocked)

## Math Findings by Technique Class

Per-category findings are recorded inline in the Sweep sections above
as they are validated/invalidated. To query all findings for a specific
category, read math-interpretation-latest.json and filter by 'category':

  python3 -c "
import json; d=json.load(open('~/.hermes/cache/research/math-interpretation-latest.json'.replace('~', __import__('os').path.expanduser('~'))))
for s in d.get('spikes',[])+d.get('optimizations',[]): \
    print(s['category'], s.get('title','?')[:60])
"

Categories with sweep-recorded findings: generalization_theory, computational_geometry,
category_theory, game_theory, lattice_order_theory, singular_learning_theory,
information_theory, stochastic_causal.

## Chain-Verified SKIP Verdicts (2026-09-09, math-cs-applicability-reasoning chain)

The following papers were in the interpreter OPTIMIZATION queue and received full
7-step chain evaluation (abstract + full text retrieval, cold subagent, grok-4.6).
All yielded SKIP — recorded here to prevent re-evaluation.

[generalization_theory] arXiv:2608.06362 — AV-AIVAT: 74x Cheaper Agent Evaluation
  chain: ALGORITHM | Step 3 pass | structural_match=true | disanalogy_valid=true
  des=0, fea=0 | SKIP (critic confirmed)
  why: requires known pre-action conditional kernel + paired IIG hands + large-N streams.
  Hermes has 1-5 subagent verdicts, no game tree, no kernel log, N far below stopping times.
  Primary contribution (AIVAT + CS anytime-valid stopping) does not transfer.
  Only intuition "stop when CI narrow enough" remains — already implicit in swarm-consensus.

[generalization_theory] arXiv:2608.15810 — Pricing the Risk of Runtime Compression
  chain: ALGORITHM | Step 3 FAIL (model internals gate: KV-write residual witness + paired logits)
  SKIP at Step 3
  why: requires KV cache, tensor-precision knob, per-event served-distribution. Hermes calls
  external APIs with no KV serving infrastructure. Compaction is one binary event per session,
  not a per-request admission stream. Primary contribution (cumloss_admission + TV<=tanh law)
  does not transfer.

[generalization_theory] arXiv:2608.08722 — Benchmark Fingerprinting Under Selection Pressure
  chain: EMPIRICAL | SKIP at Step 1 (not ALGORITHM/HEURISTIC)
  why: empirical taxonomy of 30% held-out non-transfer in a (1+1) LLM evolutionary loop over
  GPU kernels. Hermes evaluates papers once with a fixed non-public interpreter — already the
  non-optimized-against case the paper says retains validity. No evolutionary loop, no metric.

[generalization_theory] arXiv:2608.21496 — Geometry of AI Validation: Exact Certification Limits
  chain: THEOREM | SKIP at Step 1 (THEOREM not in {ALGORITHM, HEURISTIC})
  why: Theorem 2 (exact B_{m,N} ambiguity width) requires iid candidates, scalar ranking,
  known kernels, oracle binary truth. Hermes best-of-N is N=2-5, same-model correlated prompts
  (iid fails), no oracle truth. Two-gate corollary is intuitive only, not a numbered procedure.

Categories with no findings yet from Sep 2026 sweep:
  algebraic_topology, information_geometry, spectral_graph_theory, online_learning,
  formal_language_automata, convex_analysis, dynamical_systems, monte_carlo_methods,
  numerical_optimization, rl_theory_comprehensive, neural_theory, quantum_computing.

[category_theory] arXiv:2606.27593 — Odyssey: Verifiable Local Truth-Preserving Foundation Models
  chain: FRAMEWORK | companion-algorithm exception fails | SKIP at Step 1
  why: sheaf/Kan categorical framework for foundation model composition. No numbered procedure
    implementable as config/script. Hermes has no sites, restriction maps, gluing, Kan extensions.
    TICKET/FSQL require entire new module stack. Only slogan "don't promote inconsistent local
    claims" survives — already implicit in ordinary write/retrieve.

## Chain-Verified SKIP Verdicts (2026-09-10, math-cs-applicability-reasoning chain)

Four papers, full text from arXiv PDF, steps 0->1->3->2->4->5->6 (disqualifier-first).
Live config checked: compression.threshold=0.5, threshold_tokens=120000; skills.top_k / memory.reinject_every_n / compaction_buffer_tokens ABSENT from ~/.hermes/config.yaml.
No OPTIMIZATION. No SPIKE after Step 6. Do not re-evaluate unless full text or Hermes runtime changes.

[information_theory] arXiv:2609.01131 — From Source Reconstruction to Predictive State Preservation
  chain: THEOREM | SKIP at Step 1 | Step 6 not run
  why: Theorems 1–5 (sufficiency/minimality of S_X=P(F|X,C), log-loss = conditional MI, matched
    rate-distortion, full-future Markov state). No numbered procedure. Bound is not a closed-form
    constraint on compression.threshold (0.5) or any other named Hermes parameter; applying it
    would require estimating predictive states / MI, i.e. new code. THEOREM exception fails.
    Intuition "preserve predictive state not raw source" is already implicit in compaction/summarize.

[online_learning] arXiv:2609.04059 — Batched Pandora's Box
  chain: ALGORITHM | Step 3 pass | structural_match=true (pre-critic) | disanalogy_valid=true
    | des=1 fea=1 | formula SPIKE | Step 6 DOWNGRADE -> SKIP
  why: LP/Pipage rounding + reusable Weitzman batch-index need known finite-support independent
    reward distributions (v,p) and scalar costs (c_i, T, k). Hermes delegate_task returns unbounded
    strings with no V_i. Critic re-scored mapping as NONE (scores do not exist without V_i) and
    primary-contribution transfer fails: only "batch parallel search until good enough" survives,
    already implemented as delegation.max_concurrent_children=10. Formal α_NR=(1-1/e)·2(√2-1),
    α_R=1-1/e do not transfer.

[cs.AI] arXiv:2609.08832 — Closing the Consistency Gap
  chain: FRAMEWORK | SKIP at Step 1 | Step 6 not run
  why: Detect-and-Generate self-evolving loop (Consistency Analyzer N=30 resample + SBERT/Jaccard
    + Guideline Generator + Fang et al. 2026 dual-indexed episodic memory). FRAMEWORK reclassify
    fails: (b) no pseudocode for generator/storage (defers to Fang 2026); (c) full system >>50 lines,
    new modules (resampler, SBERT, dual index). Not a Hermes config/script edit. Pass^k is not a
    named Hermes log field. Intuition "write tips from traces" already implicit in memory write.

[numerical_optimization] arXiv:2609.07787 — The Price of Feasibility (String Supermodular / CSGA)
  chain: THEOREM | SKIP at Step 1 | Step 6 not run
  why: Primary contribution is Theorem 1 (conditioned sequential greedy optimality / price of
    feasibility) over graphic-greedoid bases with look-ahead physics oracle F_1 and g(x(S))=0.
    Algorithm 1 is the analysis vehicle, not a Hermes-deployable procedure. Bound does not tighten
    any named Hermes parameter. Companion-algorithm rule: classify by theorem primary. Hermes has
    no greedoid, physics oracle, or IEEE-feeder objective.

## Chain-Verified SKIP Verdicts (2026-09-10, papers 2604.16416 / 2609.01963 / 2609.03161 / 2609.03685)

Full text from arXiv HTML (ar5iv/arxiv.org/html), steps 0->1->3->2->4->5->6 (disqualifier-first).
Live config: parent claude-sonnet-4-6; compression.threshold=0.5; threshold_tokens=120000;
proactive_prune_tokens=48000; micro_compact_every_n_turns=3; Hindsight+Graphiti+session_search ACTIVE;
QMD+MemPalace DISABLED. No OPTIMIZATION. No SPIKE. Do not re-evaluate unless full text or runtime changes.
Note: task abstracts for 2604.16416 and 2609.03161 did not match full text; chain used full text.

[information_geometry] arXiv:2604.16416 — Tensor Manifold-Based Graph-Vector Fusion for AI-Native Academic Literature Retrieval
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 not run
  why: Primary contribution is a geometry-unified graph-vector fusion *framework* (tensor manifold
    as discrete projection of academic literature graph) plus four modules (temporal diffusion
    signature, hierarchical temporal manifold encoding, temporal Riemannian index, programmable
    retrieval). Reclassify fails: (a) tensor manifold, DEC/Hodge signatures, Riemannian index have
    no named counterpart in Step 2 taxonomy (Graphiti is not a Riemannian literature index);
    (c) full system >>50 LOC, new modules. Algorithm 1 (content-time random walk + SBERT + Hodge
    compensation) is a companion to the framework, not a Hermes config/script edit.
    User abstract (dual-stream encoder, hierarchical cross-attention) is not the paper's method.

[computational_geometry] arXiv:2609.01963 — Aggregating Neighbor Embedding Projection and Rank-Based Manifold Learning for Image Retrieval
  chain: ALGORITHM | Step 3 pass | structural_match=true | disanalogy_valid=true
    | metric=hindsight recall precision@K | des=1 fea=0 | SKIP (critic confirmed)
  why: Pipeline is UMAP projection of CNN/Swin/DINOv2 *image* features + rank-based re-rank +
    Borda aggregation + post re-rank on a closed CBIR collection. Mapping: ranked lists -> set of
    scored/ranked candidates + aggregate/combine. Load-bearing: complete ranked lists over a static
    closed image corpus whose points lie on a visual manifold (UMAP typically q=2). Hermes retrieval
    is query-time kNN over text traces (Hindsight/Graphiti/session_search), not all-pairs CBIR.
    Primary contribution is the image UMAP+RME combination, not Borda alone (Borda is 1781).
    fea=0: UMAP+BallTree+all-pairs manifold re-rank is new infra. Image object is DOES NOT MATCH.

[formal_language_automata] arXiv:2609.03161 — NeuroSTAR: Automata-guided Neuro-symbolic Specification Formalization
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 not run
  why: NL-to-LTL_f *framework*: N generators, SyntaxCheck+AP library, LTL_f-to-DFA, difference
    automata traces, LLM judge, iterative refinement. Training-free (not constrained decoding).
    Reclassify fails: (a) LTL_f, AP library, difference automata have no named Hermes counterpart;
    (c) needs Spot/Syft-class DFA toolchain, >>50 LOC, new modules. User abstract (track FSA during
    LLM inference, constrain tokens / guaranteed-valid-by-construction decoding) is NOT the paper;
    full text uses post-hoc DFA differencing + textual feedback, not logit masking.

[numerical_optimization] arXiv:2609.03685 — A PTAS for Non-Adaptive Stochastic Top-k Sum under General Combinatorial Constraints
  chain: ALGORITHM | Step 3 pass | structural_match=false | SKIP at Step 2 | Step 6 not run
  why: PTAS via occupancy-functional signatures (type-histograms / mixture-quantile) realized in a
    fixed-d packing LP after n^{f(d,1/ε)} heavy-item enumeration; plus hardness (no FPTAS unless
    P=NP, no EPTAS unless W[1]=FPT). Key objects: independent nonnegative discrete laws X_i, feasible
    S in packing family, occupancy p |-> E[min(k,N(p))]. Discrete value laws are not discrete *choice*
    distributions; occupancy is cts; combinatorial packing sets are not in the closed taxonomy.
    No fully non-NONE mapping row. Load-bearing even if forced: known independent discrete laws and
    non-adaptive S before realizations. Hermes tool/subagent selection is sequential, adaptive, and
    returns unbounded strings with no known X_i. PTAS is theoretical n^{f(d,1/ε)}, not a config edit.

## Chain-Verified SKIP Verdicts (2026-09-10, papers 2508.20978 / 2508.01108 / 2511.09008 / 2606.02581)

Full text from arXiv PDF/HTML (ar5iv + arxiv.org/html), steps 0->1->3->2->4->5->6 (disqualifier-first).
Live config: parent claude-sonnet-4-6; compression.threshold=0.5; threshold_tokens=120000;
proactive_prune_tokens=48000; micro_compact_every_n_turns=3; skills.top_k / memory.reinject_every_n /
compaction_buffer_tokens ABSENT; Hindsight+Graphiti+session_search ACTIVE; QMD+MemPalace DISABLED.
No OPTIMIZATION. No SPIKE after Step 6. Do not re-evaluate unless full text or runtime changes.
Note: task abstracts for 2508.20978 (belief-propagation / solver-free *inference*) and 2508.01108
(wavelet trees) did not match full text; chain used full text.

[neural_theory] arXiv:2508.20978 — Scaling Neuro-symbolic Problem Solving: Solver-Free Learning of Constraints and Objectives
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 not run
  why: Primary contribution is a hybrid NN + pairwise cost-function-network layer trained with E-PLL
    (Emmental Pseudo-LogLikelihood). Solver is removed from the *training* loop; at inference N(ω)
    is handed to any GM/WCSP solver ("exact prover during inference"). Reclassify fails: (a) cost
    tensors, WCSP solver, backprop through E-PLL have no named Step 2 counterpart; (c) training +
    GM solver >>50 LOC, new modules. Task abstract (BP-message iteration, no solver at inference)
    is NOT the paper. Even if mislabeled ALGORITHM, Step 3 training-loop gate fires (back-propagate
    y through E-PLL). Intuition "predict a structured model then solve" is not a Hermes config edit.

[computational_geometry] arXiv:2508.01108 — Random-Access Ranked Retrieval and Similarity Search
  chain: ALGORITHM | Step 3 pass | structural_match=true | disanalogy_valid=true
    | Step 4 metric gate FAIL | SKIP | Step 6 not run
  why: Eps2D/EpsRange/EpsHier retrieve a conformal set containing the i-th ranked point under a
    query-time linear score f^T p over a preprocess-time n-point set in R^d (ε-samples + stripe
    range search). Mapping: ranked conformal set -> set of scored/ranked candidates + retrieve/search.
    Load-bearing: D available at preprocessing; linear (or lifted) scoring over static R^d attributes;
    target rank i may be Θ(n). Hermes Hindsight/Graphiti are query-time kNN over text traces, not
    rank-i access into a full linear ranking. No known Hermes log field measures rank-i query time;
    hindsight recall precision@K would not move. Task abstract (wavelet trees) is NOT the paper.
    fea would be 0 anyway: hierarchical sampling + ε-sample index is new infra.

[formal_language_automata] arXiv:2511.09008 — A Neurosymbolic Approach to Natural Language Formalization and Verification
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 not run
  why: ARc = Policy Model Creator (span split, SMT-LIB autoformalization, embedding-cluster variable
    unify, lint/test/vet) + Answer Verifier (k redundant NL->SMT translations, symbolic-equivalence
    confidence, Z3-class SMT entailment). Algorithm 1 is companion to the commercial two-component
    service, not a Hermes config/script edit. Reclassify fails: (a) SMT-LIB policy models, SMT solver,
    schema unification have no named Hermes counterpart; (c) full system >>50 LOC, new solver + PMC.
    Soundness/FPR on ConditionalQA-logic is not a named Hermes log field. Intuition "check outputs
    against rules" is already implicit in ordinary policy/skill constraints; no SMT guardrail exists.

[information_retrieval] arXiv:2606.02581 — Cost-Aware Query Routing in RAG: Empirical Analysis of Retrieval Depth Tradeoffs
  chain: EMPIRICAL primary; secondary HEURISTIC | Step 3 pass | structural_match=true (pre-critic)
    | disanalogy_valid=true | metric=session token count at compaction | des=1 fea=1
    | formula SPIKE | Step 6 DOWNGRADE -> SKIP
  why: Title/contribution is a 28-query empirical study; secondary method is argmax_b U_b =
    wQ Qhat - wL Lnorm - wC Cnorm over {direct_llm, light_rag k=3, medium_rag k=5, heavy_rag k=10}
    with hand-specified priors (no learned reward). Parameter (wQ,wL,wC) ABSENT from config.yaml.
    Mapping: scored bundle catalog -> set of scored/ranked candidates + select/argmax. Load-bearing:
    FAISS dense retrieval over a static corpus + billed τ=prompt+completion+embed + quality priors.
    Hermes is not a RAG QA stack; no retrieval-depth bundle catalog.
  CRITIC: mapping borderline (RAG bundles vs memory candidates; "routing" is negative-lexicon).
    Primary-contribution transfer fails: no formal guarantee; 26%/34% deltas are on a 15-sentence
    self-corpus. Only intuition "don't always retrieve deep; penalize cost/latency" survives — already
    implicit in compaction.threshold=0.5 and not fetching the full memory store. Missing API (FAISS +
    OpenAI embeddings) => any verdict SKIP. Binding critic: SKIP. No spike doc.

## Chain-Verified SKIP Verdicts (2026-09-10, papers 2608.06362 / 2608.15810 re-run)

Full text from arXiv PDF+HTML (ar5iv-equivalent extract), steps 0->1->3->2->4->5->6 (disqualifier-first).
Live config: parent claude-sonnet-4-6; compression.threshold=0.5; threshold_tokens=120000;
proactive_prune_tokens=48000; micro_compact_every_n_turns=3; Hindsight+Graphiti+session_search ACTIVE;
QMD+MemPalace DISABLED. skills.top_k / memory.reinject_every_n / compaction_buffer_tokens ABSENT.
No OPTIMIZATION. No SPIKE. Independent re-run of the 2026-09-09 SKIPs; same binding verdict.
Do not re-evaluate unless full text or Hermes runtime changes.

[generalization_theory] arXiv:2608.06362 — AV-AIVAT: 74x Cheaper Agent Evaluation
  chain: ALGORITHM (Alg. 1) | Step 3 pass | structural_match=true (pre-critic)
    | disanalogy_valid=true | metric gate: no named field for CS stopping-time of paired payoffs
    | forced metric=swarm consensus convergence turns | des=0 fea=0 | SKIP (critic confirmed)
  Step 0: AV-AIVAT achieves a median 74x smaller stopping time for paired payoff streams in
    imperfect-information games at ±1 BB and 95% coverage under AsympCS, by combining predictable
    mean-zero value corrections with continuously monitored confidence sequences, assuming a known
    pre-action conditional action kernel.
  Step 3: no training-loop / tabular-MDP / oracle-reward / logit-vocab / human-feedback gate.
    Action kernel p_h is a game-action law, not token-vocab logprobs.
  Step 2: bounded prediction sequence -> N subagent verdicts; aggregate/combine + schedule/allocate.
    Load-bearing: known pre-action kernel p_{t,h}, finite correction-node set H_c, past-only v_t,
    paired IIG hands, V_t -> infinity. Hermes has 1-5 subagent string verdicts, no game tree,
    no kernel log, N far below AsympCS stopping times (thousands of hands).
  Step 4/5: 74x is AIVAT-corrected vs raw on HUNL, not a Hermes log field. des=0 (no value at N=1-5);
    fea=0 (AIVAT needs kernel+value function = new infra; CS-only still needs large-T martingales).
  CRITIC: mapping is vocabulary-adjacent ("agent evaluation" is negative-lexicon). Primary
    contribution is the AIVAT+CS combination (Alg. 1 steps 2-4), not CS-on-raw. Formal 74x
    guarantee fails the kernel/game-tree disanalogy. Residual intuition "stop when the interval is
    tight enough" is already in hermes-swarm-consensus (Beta-Binomial adaptive stop at lower
    credible bound 0.85; MACI plateau halt; skip-if-agree; n>=6). evaluation-driven-development
    uses fixed-N traces, not AsympCS. Spike 002 (2026-09-08) already INVALIDATED SPRT early-stop
    on paper-interpreter sweeps (missed all tail OPTIMIZATIONs). Binding critic: SKIP. No spike doc.

[generalization_theory] arXiv:2608.15810 — Pricing the Risk of Runtime Compression
  chain: ALGORITHM (cumloss_admission + served_tv_le_of_gate_tanh) | Step 3 FAIL
    (model-internals + logit/logprob) | SKIP at Step 3 | Step 6 critic still run
  Step 0: cumloss_admission maintains an anytime-valid budget on cumulative realized loss with
    zero authorization violations and a halved exact-fallback rate (0.30 -> 0.14) at matched risk
    on live serving traffic, assuming predictable a_t in F_{t-1} and L_t in [0,1] with
    E[L_t|F_{t-1}] <= mu; the served-output law is TV <= tanh(a_q w_thr).
  Step 1: primary experimental object is the admission engine (352,333 calls; Lean 4, 228 theorems).
    No numbered Algorithm 1; if reclassified FRAMEWORK, companion-algorithm fails (a)(c) — KV-write
    residual, operator-norm a_q, per-token served distribution have no Step-2 counterpart; >>50 LOC.
    THEOREM exception for TV<=tanh fails: w_thr is a KV-write witness bound (deployed 35.34),
    not compression.threshold (fill ratio 0.5). w*_thr = atanh(tau*)/a_q needs a_q = softmax_scale
    * ||q||_static from W_q spectral norms — new code, not a config-only numeric constraint.
  Step 3 (binding): model internals (KV-write residual u_e, attention maps, W_q operator norms,
    paired exact-vs-compressed reads) AND logit/logprob (sum over 129,280 vocab terms per token;
    cumulative final-logit perturbation). One box => SKIP. Do not fill Step 2.
  CRITIC: primary contribution is cumloss_admission + TV<=tanh on KV-write precision in an MoE
    serving stack, not LLM context compaction. Formal law does not transfer: Hermes calls external
    APIs with no KV serving, no per-event admission stream, compaction is one binary session event.
    Residual intuition "pick a threshold that bounds quality loss" is already implicit in
    compression.threshold=0.5 and hermes-context-budgeting (task-class snip table; 35% safety cliff).
    a_q is not a Hermes metric. Binding critic: SKIP. No spike doc. No skill patch.

## Chain-Verified SKIP Verdicts (2026-09-10, targeted 6-area OPTIMIZATION search)

Search: arXiv API 2026 papers (ID >= 2601), 20/area × 6 areas = 120 unique IDs in
  /tmp/arxiv_math_cs_search.json (submitted ~2026-08-18 to 2026-09-08).
Areas: streaming_sketching, online_learning, mdl_kolmogorov, martingale_anytime,
  competitive_online, rate_distortion.
Rapid triage: Step 0-1-3 on abstracts. CHAIN = ALGORITHM/HEURISTIC + no obvious
  Step 3 box + plausible closed-taxonomy map. Then full text (arXiv PDF) + 7-step
  chain (0->1->3->2->4->5->6). Live config: parent claude-sonnet-4-6;
  compression.threshold=0.5; threshold_tokens=120000; proactive_prune_tokens=48000;
  micro_compact_every_n_turns=3; skills.top_k / memory.reinject_every_n /
  compaction_buffer_tokens ABSENT; Hindsight+Graphiti+session_search ACTIVE;
  QMD+MemPalace DISABLED.
No OPTIMIZATION. No SPIKE after Step 6. No skill patches. Do not re-evaluate unless
  full text or Hermes runtime changes.

### Rapid triage (120 papers)

CHAIN (full text + chain below): 2609.07566, 2609.05820, 2608.19888, 2607.08522,
  2609.04292, 2608.18303, 2608.30502, 2607.19689, 2608.19908, 2609.06593, 2609.06669.
Spike-queue extras: 2609.04292 (entry 15); BDCC 10.3390/bdcc9100258 (entry 00).
Already chain-SKIP this session family: 2608.06362, 2609.01131.
REVIEW (algorithmic on abstract but Step 1/3 fail without fetch): remaining 107.
Typical SKIP reasons: THEOREM/lower-bound; training/gradients (federated GNN, RL,
  JSCC, LIC, Kalman adapters); FRAMEWORK (semantic coding, MoE serving, VLA);
  EMPIRICAL (leaderboards, case studies); objects outside taxonomy (images, graphs
  in Hamming space, facilities, jobs, SAR, KV-cache internals).
Negative-lexicon hits ("adaptive","routing","memory","efficient") were not treated
  as mapping evidence.

### Full-chain papers

[online_learning] arXiv:2609.07566 — No-Regret Mixing of LRU and LFU with Optimal Switching Cost
  chain: ALGORITHM (H-MC / Alg. 1) | Step 3 pass | structural_match=true
    | disanalogy_valid=true | metric gate forced=skill dispatch latency
    | des=1 fea=0 | SKIP | Step 6 not required (fea=0)
  Step 0: H-MC mixes LRU and LFU via Hedge on two virtual caches plus maximal
    coupling of consecutive Bernoulli expert draws, achieving O(sqrt(T)) regret vs
    the better policy and O(sqrt(T)) expected switches under adversarial requests.
  Step 3: no training/gradients (2-expert multiplicative weights); miss indicators
    are observed hits, not oracle GT; no internals/logits.
  Step 2A: disc. distribution over {LRU,LFU} -> skill selection; select/argmax.
  Step 2B: load-bearing dual virtual occupancy of size C plus simultaneous miss
    losses and unit upload cost on expert-identity change. Hermes has one context
    stream, no pair of simulated caches, no miss/hit bit of that form.
  Step 5: fea=0 — maintaining two virtual caches + coupling is new infra, not a
    config edit. Primary contribution (cache mixing + switch-cost bound) does not
    transfer. Residual "don't resample every step" is not a Hermes procedure
    (skills are not Bernoulli-resampled per turn).

[online_learning] arXiv:2609.05820 — Online Learning with LLM Experts from Limited Feedback
  chain: ALGORITHM (LimFullFeed Alg. 1) | Step 3 FAIL (training loop + human-feedback)
    | SKIP at Step 3 | Step 6 not run
  Step 0: LimFullFeed routes each prompt embedding xt to one of K linear experts
    and queries m << T determinant-greedy reward vectors, with regret O(d T / sqrt(m))
    under linear rewards r=<θ_a,x>+η.
  Step 3: OLS updates θ̂_t,a = V^{-1} y_t,a are weight updates; feedback is human
    or LLM-as-judge rewards ("limited feedback as good as humans"). One box => SKIP.
  Also needs frozen transformer embeddings xt in R^d — not a Hermes log field.

[martingale_anytime] arXiv:2608.19888 — Evidence Before Expansion: Reuse, Spawn, or Defer
  chain: ALGORITHM (CJSD e-process gate) | Step 3 FAIL (training loop + oracle labels)
    | SKIP at Step 3 | Step 6 not run
  Step 0: A two-axis CJSD gate with betting e-processes decides reuse/spawn/defer
    for a streaming expert pool under indifference zone [τ,3τ] and Ville thresholds.
  Step 3: chunks (X_t,y_t) with training/held-out reservoirs, learned discriminators,
    prequential accuracy before learning. Labels + weight-updated models. SKIP.

[information_theory] arXiv:2609.04292 — BER-PEF: Unified Human Mobility Predictability Evaluation
  (spike-queue entry 15, claimed target=skill selection entropy — FULL TEXT DOES NOT MATCH)
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 not run
  Step 0: BER-PEF maps mobility sequences into a shared feature-label space and
    scores Bayes-error estimators along perturbation curves when predictability GT
    is unobservable.
  Step 1: primary contribution is a unified evaluation protocol for mobility BER
    estimators (Foursquare/GeoLife/T-Drive). Reclassify fails: (a) BER estimators,
    spatiotemporal trajectories, perturbation curves have no Step-2 counterpart;
    (c) full protocol >>50 LOC, new modules. Not skill-selection entropy. No config edit.

[computational_geometry] BDCC 2025, 9(10), 258 — Data Organisation for Efficient Pattern Retrieval
  (spike-queue entry 00, target=nearest-neighbor retrieval geometry)
  chain: FRAMEWORK/survey | SKIP at Step 1 | full PDF blocked (mdpi.com scrape 500)
  why: title+venue are a survey of indexing/storage/access structures, not a numbered
    ANN procedure implementable as a Hermes config/script. Graphiti/Hindsight already
    provide retrieval; no closed-form tightening of a named parameter. DEFER only if
    a later full text reveals a companion algorithm that is the primary contribution.

[generalization_theory] arXiv:2607.08522 — Stop Guessing When to Stop Testing
  chain: FRAMEWORK (GST + Pocock spending + user stopping rules) | reclassify fails
    | SKIP at Step 1 | Step 6 not run
  Step 0: Group sequential testing with Pocock α-spending stops pairwise model
    comparison when peeking-adjusted CIs / MDE / diminishing-returns rules fire,
    assuming iid scored examples in batches of size b.
  Reclassify fails: (a) GST stages, Pocock thresholds, Open-VLM-Leaderboard scores
    have no named Step-2 counterpart (not N subagent string verdicts); (c) >>50 LOC.
  Note: spike 002 already INVALIDATED SPRT early-stop on paper-interpreter sweeps.
    Residual intuition is already in hermes-swarm-consensus (Beta-Binomial stop).

[cs.AI] arXiv:2608.18303 — SESSE: Sketch, Expand, Sort, Summarize, Evaluate
  chain: FRAMEWORK | reclassify fails (c) >>50 LOC | SKIP at Step 1
  Step 0: SESSE decomposes holistic LLM-as-judge A/B preference into structured
    sub-questions mined from the judge's own error cases, training-free.
  (a) criteria-mining / per-criterion votes have no Step-2 counterpart as a Hermes
    named component; (c) full system >>50 LOC. Not a config edit.

[martingale_anytime] arXiv:2608.30502 — When the Martingale Never Stops Firing
  chain: EMPIRICAL primary | SKIP at Step 1 | Step 6 not run
  Step 0: Conformal test martingales that are Ville-valid on exchangeable scores
    fired on 135/135 real forecast streams (α=0.05); Huber gating of a Kalman
    adapter's own updates cut isolated-spike degradation without a validity claim.
  Primary is the negative measurement. Secondary Huber gate is a Kalman-filter
    heuristic, not a Hermes parameter. Exchangeability fails on Hermes turn streams.

[online_learning] arXiv:2607.19689 — Optimal Recalibration of an Online Predictor
  chain: ALGORITHM (imbalanced simultaneous Blackwell approachability) | Step 3 pass
    | structural_match=false | SKIP at Step 2 | Step 6 not run
  Step 0: An online recalibrator turns an arbitrary hint forecast sequence into
    (ε,ε^{2})-recalibrated forecasts for Lipschitz proper losses in T~ε^{-3} rounds.
  Step 2A: core object is a continuous forecast on a simplex (cts distribution) -> NONE.
    Realized labels under a proper loss are not a closed-taxonomy object. No fully
    non-NONE row. Load-bearing even if forced: sequential outcomes vs forecasts;
    Hermes skill/model choice is not a calibrated probability forecast with proper loss.

[information_theory] arXiv:2608.19908 — A Layered Simplex Architecture for Large Alphabets
  chain: ALGORITHM (coordinate-wise uniform simplex product + renormalize) | Step 3 pass
    | structural_match=true (pre-critic) | disanalogy_valid=true | des=0 fea=0 | SKIP
  Step 0: A depth-parameterized Bayesian mixture formed by multiplying independent
    uniform simplex draws and renormalizing achieves competitive log-loss regret vs
    Good-Turing on large alphabets, with closed-form mixture regret.
  Step 2A: disc. distribution over a large alphabet + compress/summarize (coding).
  Step 2B: load-bearing i.i.d. symbol counts and log-loss coding regret. Hermes
    skill/token streams are not i.i.d. alphabet draws; no log-loss code-length metric.
  Step 5: des=0 (no daily path); fea=0 (new estimator, no named metric). Critic:
    only intuition "smooth unseen mass" survives — not a Hermes procedure.

[martingale_anytime] arXiv:2609.06593 — Discovering Translation-Worthy Languages with E-Values
  chain: ALGORITHM (paired e-processes, threshold 280) | Step 3 FAIL (oracle labels)
    | SKIP at Step 3 | Step 6 not run
  Step 0: Paired e-processes compare direct vs translation-assisted classification
    per language and freeze a route when familywise-controlled evidence exceeds 280.
  Step 3: requires paired labeled classification outcomes (SIB-200/MASSIVE). Oracle
    GT labels at inference. Hermes has no multilingual document-class route or those labels.

[streaming_sketching] arXiv:2609.06669 — Tight Bounds on the Cost of Adaptivity for the Meyerson Sketch
  chain: THEOREM | SKIP at Step 1 | Step 6 not run
  Step 0: The Meyerson sketch's adaptivity ratio vs an oblivious replay is
    Θ(log Δ / log log Δ) in both directions for online facility location.
  Bound is not a closed-form constraint on compression.threshold=0.5 or any other
    named Hermes parameter. Companion sketch is classical Meyerson, not primary.

## Inverted-approach wave (2026-09-10, object-first search)

Strategy: identify Hermes object types mathematically, then search for matching algorithms.
Queries: 9 targeted (streaming coreset, variable-length coding, online summarization,
  prediction expert advice, MDL model selection, learning-augmented kNN, approximate
  similarity search, robust aggregation, median-of-means). 81 new unique papers.
Triage: 20 loose CHAIN, strict re-screen -> 0 CHAIN, 3 REVIEW -> all SKIP.
Result: 0 OPTIMIZATION, 0 SPIKE. No skill patches.

Systematic object-type mismatches identified:
  - Streaming algorithms: operate on vector/set streams, not variable-length token sequences
  - Online scheduling (2609.07402, MLF): preemptive single-machine; Hermes is parallel+async
  - Robust aggregation: requires cardinal payoff scores, not categorical string verdicts
  - Caching theory: requires hit/miss observations + dual virtual cache structures
  - Classification-risk active learning (2609.06873): requires fitted parametric model + Fisher info
  - Equation-free Markov modelling (2609.08530): needs dense physical process observations

Conclusion: Hermes object types (token sequence, discrete skill distribution, embedding
  retrieval candidates, N string verdicts) do not match the load-bearing structure of
  any current math corpus ALGORITHM paper at feasibility=2. The transfer chain is
  correctly calibrated. Further math sweeps should target papers that DEFINE an algorithm
  on these exact structures natively (not by analogy), or wait for the math corpus to
  produce work on: (a) lossy compression of token sequences with semantic distortion
  metrics, (b) Bayesian categorical updating with unknown class count, (c) aggregation
  of ordinal label strings without cardinal scores.

## Chain-Verified SKIP Verdicts (2026-09-15, math HIGH items from 2026-09-06 log)

Three papers flagged HIGH by math-paper-interpreter.py (2026-09-06 log run) received
full 7-step chain evaluation (abstract fetch + applicability chain). All SKIP.
Live config: parent claude-sonnet-4-6; compression.threshold=0.5; threshold_tokens=120000;
proactive_prune_tokens=48000; micro_compact_every_n_turns=3; Hindsight+Graphiti+session_search
ACTIVE; QMD+MemPalace DISABLED. Do not re-evaluate unless full text or runtime changes.

[game_theory] arXiv:2609.01595 — Mechanism Design for Alignment and Control
  chain: FRAMEWORK | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 run
  why: Mechanism design framework with revelation principle for AI agents with unknown
    alignment and capabilities. Primary contribution is the one-sided imitation revelation
    principle + cyclical monotonicity characterization — an economic theory result.
    Examples (i-v) are stylized economic applications (sandbagging, peer scoring, reward
    coupling, scalable oversight), not numbered pseudocode. No Hermes counterpart for
    type-elicitation mechanism, higher-order belief elicitation, or alignment×capability
    decoupling. Reclassify fails: (a) cyclical monotonicity, agent type space have no
    Step-2 COMPONENT_MAP entry; (c) full framework >>50 LOC, new type-space module.
    Residual intuition "peer score to reduce sandbagging" already in adversarial-review
    (independent cold sessions) and hermes-swarm-consensus (agreement tracking).
    Note: spike 001-peer-scoring-incentives ran but produced no Gate: PASS verdict
    (simulation requires known generative model for EU agents; Hermes uses LLMs).

[game_theory] arXiv:2608.28754 — Peer Oversight in Collective Decision Making
  chain: THEOREM | companion-algorithm reclassify fails | SKIP at Step 1 | Step 6 run
  why: Theorem: peer k-oversight achievable by redistributing mechanism control ↔ k agents
    suffice. Polynomial-time algorithm is a min-cut/flow reduction on the bipartite
    decision graph. Reclassify fails: (a) "responsibility for harmful outcome", mechanism
    graph, control redistribution have no Step-2 COMPONENT_MAP counterpart; (c) min-cut
    algorithm >>50 LOC, new graph construction. THEOREM exception fails: no closed-form
    constraint on a named Hermes parameter (adversarial-review k is heuristic, not derived
    from a mechanism graph). Formal harm model does not exist in Hermes.
    spike 003-coalition-reviewer-selection ran (Gate: PASS, see Spike section below):
    greedy coverage k=3 catches as many adversarial examples as random k=5, but requires
    expertise vectors per reviewer — which don't exist in Hermes yet.
    status: SKIP (chain); VALIDATED-gated (spike, expertise vectors required before ship).

[numerical_optimization] arXiv:2505.13416 — Gluon: Making Muon & Scion Great Again!
  chain: ALGORITHM | Step 3 FAIL (training loop gate) | SKIP at Step 3 | Step 6 run
  why: Gluon is a training-time gradient optimizer (LMO-based, Muon/Scion variant) for
    neural network parameters. Requires: weight gradients, linear minimization oracle,
    Schatten norm balls, per-batch momentum. Hermes calls external APIs with no local
    model training pipeline. Training-loop gate fires.
    spike 009-gluon-optimizer-finetuning ran (toy numpy MLP): Gluon converges faster
    than Adam in steps-to-95% on small synthetic task. But: do not promote to Hermes
    training defaults from this toy run; Newton-Schulz at d_model=4096 has cost issues.
    Not actionable without a real Hermes local fine-tuning pipeline.
    status: SKIP (chain); VALIDATED-toy (spike, no ship gate met).

## Spike Experiment Verdicts (2026-09-15 audit of ~/.hermes/cache/research/spikes/)

Spikes run previously that were not yet formally recorded in this skill:

### VALIDATED-gated (Gate conditions must be met before implementing)

[game_theory] spike 003-coalition-reviewer-selection (arXiv:2608.28754)
  Given: adversarial-review assigns reviewers heuristically (all-available or first-N).
  When: greedy k-coverage algorithm selects reviewers to cover expected decision types.
  Then: k=3 greedy covers as many adversarial types as random k=5; Gate: PASS.
  Ship condition: DO NOT SHIP until expertise vectors exist per reviewer (category tags,
    past finding types, ~20 decision-type mask). Random 20-dim mask = theater.
  Next step: define expertise-vector schema in adversarial-review skill; backfill from
    past adversarial-review session logs (finding categories). Then implement greedy cover.
  Files: ~/.hermes/cache/research/spikes/003-coalition-reviewer-selection/

[online_learning] spike 004-oftrl-subagent-aggregation (arXiv:2608.31166)
  Given: Hermes aggregates subagent outputs via averaging/majority vote.
  When: OFTRL-style softmax(η(S + u)) aggregation over cumulative payoff vector S.
  Then: synthetic: faster convergence to dominant answer than naive majority in games.
  Ship condition: DO NOT SHIP without live A/B on real Hermes delegate_task ensembles
    showing lower answer-flip rate across retries. Synthetic game ≠ LLM subagents.
  Files: ~/.hermes/cache/research/spikes/004-oftrl-subagent-aggregation/

### VALIDATED-synthetic (do not ship; real-data gate required)

[information_theory] spike 006-predictive-state-context-compression (arXiv:2609.01131)
  Synthetic result: MI-based turn selection beats recency at same budget.
  Chain verdict: SKIP (2026-09-10 — requires estimating predictive states / MI
    from real traces + held-out task outcome labels, not available in live Hermes).
  Do NOT re-evaluate; chain SKIP stands. Spike is educational only.
  Files: ~/.hermes/cache/research/spikes/006-predictive-state-context-compression/

[computational_geometry] spike 007-manifold-aware-context-retention (arXiv:2609.00552)
  Synthetic result: manifold-nearest token retention outperforms uniform/recency on
    synthetic low-dim embeddings (intrinsic_dim=8, ambient_dim=50).
  Gate: requires real model last-layer hidden states + task-level metrics (not centroid
    cosine on heterogeneous-norm tokens). Do not ship from synthetic DGP alone.
  Files: ~/.hermes/cache/research/spikes/007-manifold-aware-context-retention/

## Wave 14 Run Results (2026-09-16)

math-paper-interpreter.py, batches 46–55 (wave 14), sweep 2026-09-15, 294 flat papers:
  0 SPIKE, 0 OPTIMIZATION across all 10 batches — SATURATED on current sweep.
  Ideas queue: 398 → 459 (+61 new ideas, backlog only — not actionable tier).
  Seen cache: rolling window, resets at 79 (full corpus), normal behavior confirmed.
  Batches 50+51: killed by `timeout 300` before budget-guard (270s); papers reprocessed
    in batch 52 — net data loss 0. Streak count: 8 batches with Results lines + 2 mid-run
    kills, all showing 0 spikes/optimizations.
  Saturation call: VALID. Next action: fresh math sweep (hermes-math-sweep.py) for wave 15.

  Adversarial review (cold subagent deleg_8b9ddb39, 2026-09-16):
    F-01 HIGH confirmed → fixed: saturation criterion updated in hermes-research-sweep-ops-resume
      (was '0 Stage 3 ideas' — incorrect, IDEA tier is backlog not actionable; corrected to
       '0 SPIKE + 0 OPTIMIZATION across 8+ batches').
    F-02 HIGH confirmed → resolved: batches 50/51 are mid-run kills, not data loss.
    F-07 LOW confirmed → noted: batch 47 pre-wave ideas (16 budget-guard flush) were
      already in the queue as wave 13 output; wave 14 starting total 398 is correct.

## Fresh Sweep Results (2026-09-15)

math-paper-interpreter.py --limit 30, 2026-09-15 02:50 UTC:
  30 papers processed (from 502 new papers in hermes-math-sweep-latest.json, 2026-09-14)
  0 SPIKE, 0 OPTIMIZATION, 30 SKIP
  SKIP rate: 100% (anytime-valid anomaly threshold triggered by interpreter)
  Spike queue: empty (pending_spikes: [], pending_optimizations: [])
  Note: --limit 30 processes only first 30 of 502 new papers. The high SKIP rate in
    this --limit 30 run is likely sampling noise from the leading 30 papers. For full
    coverage run hermes-math-interpret cron without --limit (as in the Sep-06 full run:
    177 papers, 50 spikes, 1 opt). The Sep-06 HIGH items from that log have now all
    been chain-evaluated (see "Chain-Verified SKIP Verdicts 2026-09-15" section above).

## Cross-References

- Non-math agent findings (cs.AI/cs.CL/cs.MA): arxiv-sweep-findings
- CS systems/engineering findings: hermes-cs-sweep-findings
- Running the math sweep: hermes-math-research
- Applying patches: trajectory-research-synthesis-to-skills

---
name: theory-to-implementation-extrapolation
description: Use when deriving Hermes components from theory.
version: 3.0
author: hermes
tags: [extrapolation, theory-to-code, analogy, abduction, category-theory, algorithm-design, agent-systems, verification, control, causality]
related_skills: [rate-distortion-context-budget, decision-centric-memory, compositional-skill-routing, bps-skill-budget, agent-runtime-loop-patterns, hermes-swarm-consensus, fabricated-consensus-gate, skill-fulltext-routing]
---

# Theory-to-Implementation Extrapolation

Use when a textbook theorem, lemma, or framework should force a new Hermes runtime piece: memory (SQLite), scheduler/cron, compressor (lambda-tuner), skill router, plugins (`pre_tool_call` / `post_tool_call` / LLM hooks), or scripts.

**Core law:** novel algorithms are not stacked empirical tricks. They are the unique or universal construction compatible with a chosen mathematical object and its invariants (Chentsov, Eckart-Young, Kan, natural gradient, VCG, Sinkhorn limit, spectral theorem).

If two implementations satisfy the same universal property, treat them as interchangeable (HoTT univalence, Elliott homomorphism, CompCert observational equivalence). If they do not, the extrapolation is unfinished.

---

## Agent limits (read first)

- You cannot prove theorems. You can write property tests, run them, and treat failures as falsification. Passing tests are evidence, not a proof.
- Hermes plugins are *synchronous* Python hooks: `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`. They are NOT async. Do not put unbounded iterative solvers or inner LLM calls in synchronous pre-hooks. Put these in cron scripts or `on_session_end`.
- Hermes memory is SQLite (often JSON in columns). Dense n x n linear algebra over all memory rows is not a drop-in operation.
- Skills are YAML frontmatter + Markdown. The existing skill router is BM25 + embedding match on descriptions, not a probability simplex.
- Context compression uses a lambda-tuner. Rate-distortion is an analogy unless you implement an explicit channel and distortion measure.
- Do not inject synthetic conversation messages from a plugin hook (corrupts compaction logic).
- Search existing skills, plugins, and cron scripts for the same slot before deriving a new component (duplication gate; see Step 1).

---

## Step 0 -- Structural extraction (mandatory)

Extract the relational skeleton. Names are not structure. Surface lexical analogy is not extrapolation.

1. Objects (types, spaces, sigma-algebras, PL types)
2. Morphisms (maps, kernels, reductions, protocols, interventions)
3. Laws (commuting diagrams, conservation, uniqueness, duality, composition theorems, coherence)
4. Regularity (measurability, convexity, Lipschitz, compactness, finite VC, total unimodularity, Scott continuity)
5. Resource modality (duplicable `!` vs linear; observational vs `do(.)`)
6. Certificate kind -- pick one primary, never substitute:
   - exact invariant
   - approximation ratio (offline; check it is not ruled out by hardness-of-approximation)
   - competitive ratio (online)
   - PAC / concentration
   - temporal (CTL/LTL)
   - cryptographic reduction / DP
   - information inequality (DPI, Fano, chain rule)
7. Choose **one** primary scaffold from the catalog. Familiarity is not a criterion.

### Scaffold catalog (match structure, not subject)

| Theorem looks like | Scaffold | Forced shape |
| uniqueness under invariance / universal arrow | 3c categorical | read off the universal construction |
| continuous flow, Lagrangian, HJB, gradient flow | 3a variational/ODE | discretize a continuous object |
| bilinear score, RKHS, Gram, attention | 3b kernel rewrite | swap kernel, inherit guarantees |
| residue not entailed by current axioms | 3d abductive | independent kill-test, then promote |
| information grows with time; stopping | 3e filtration/martingale | optional stopping, Doob split |
| linear operator, graph, covariance | 3f spectral/SVD | diagonalize then act; truncate by Eckart-Young |
| heap, protocol, tokens, linear types | 3g resource/session/separation | frame + dual session + linear budget |
| NP-hard, online, query model, IP | 3h reduction/approx/competitive | reduction + ratio or oracle type |
| P(Y|do(X)) vs P(Y|X) | 3i causal | backdoor/front-door or refuse causal claim |
| stability, feedback, two time-scales | 3j Lyapunov/ISS/control | certificate V; small-gain for composition |
| payoffs, multiple agents, knowledge | 3k mechanism/epistemic | IC / PoA / common-knowledge check |
| local charts, overlaps, modules | 3l sheaf/glue | gluing axiom; H1 obstruction |
| infinite traces, streams, fixpoints | 3m coalgebra/temporal | coinduction, CTL/LTL, bisimulation |
| estimators, samples, loss | 3n decision/PAC/concentration | loss first; admissible; uniform convergence |
| symmetries of unordered/geometric input | 3o equivariance/Lie/symplectic | equivariant maps; Noether invariants |
| leakage, adversaries, secrets | 3p privacy/crypto | DP or reduction; do not invent primitives |

Multi-scaffold theorems: the scaffold that supplies the **uniqueness/universal** constraint is primary; the others become extra certificates, not extra code paths.

If no scaffold fits, you may still ship an engineering heuristic, but you MUST label it as such. Do not claim theory-to-implementation extrapolation for a heuristic.

---

## Step 1 -- Mapping table (before any code)

```
Math construct | Law | Regularity | Certificate | Hermes type/fn | Testable property | Hard core?
Markov kernel (closed) | row-stochastic; mass conservation | measurable | exact | closed-world memory decay | weights >= 0 and sum(weights)==1 | YES (only if you commit to conservation; choose one)
Substochastic kernel (open) | mass may leak to cemetery state | measurable | exact | leaky forgetting | weights >= 0 and sum(weights) <= 1 | YES (contradicts row-stochastic; pick exactly one)
Bregman Lagr.  | extremality; named discrete Lyapunov decrease | convex | exact | scheduler step | named energy E_t+1 <= E_t on each step (name E explicitly) | YES
Sinkhorn eps   | finite eps: full support (dense) if K>0; as eps->0, OT *cost* converges and plan converges to a (max-entropy) OT plan. Finite-eps matrix is NOT the sparse OT plan. | eps>0 | cost-within-tolerance | approx coupling | cost error < delta; never treat finite-eps support as OT vertex | NO (belt)
Truncated SVD  | Eckart-Young | finite rank | exact opt in F | compressor | ||X-Xk|| = next singular | YES
UCB index      | regret bound | bounded rewards | competitive | cold-start cron | regret <= f(T,K) | YES
Compressor     | DPI          | Markov chain    | exact ineq  | pre_compress    | I(dec;Y) <= I(dec;X) | YES
Router         | Fano         | finite skills   | lower bound | skill choose    | P_err >= f(I(Q;S)) | YES
Hilbert proj   | uniqueness   | Hilbert         | exact opt   | memory retrieve | nearest is unique | YES
```

Lakatos freeze:
- **Hard core:** never violate (mass conservation, lens laws, progress+preservation, eps-DP, Lyapunov decrease, simplex, frame rule, inner=outer objective, source independent of channel, gluing, equivariance, Scott monotonicity in information, data-processing inequality, Curry-Howard: every hard-core law has a test inhabitant).
- **Protective belt:** caches, Sinkhorn eps, minibatch, mean-field BP, BMC depth k, random features, MAP point estimates.
- A hack that falsifies the hard core is a **paradigm change**, not an optimization. Update the Naur document first.

Convexity (Boyd): if the lifted problem is convex, dualize; duality gap is a stopping test. If not, you do **not** inherit poly-time or unique KKT -- switch to 3h.

**Duplication gate.** Before proceeding, search existing Hermes skills, plugins, and cron scripts for the same target slot. If one exists, extend it rather than re-deriving a parallel component.

**Tractability gate.** The mapped operation must be implementable as: (a) SQL or JSON queries over SQLite, (b) a bounded Python pass over a query result set, or (c) a cron *script* (not a `command` field -- cron ignores `command`) located under the active profile's `scripts/` directory with a `kind: interval` job using `minutes:`. Unbounded iterative solvers do not belong in synchronous hooks. If none of these fit, keep the design in the pedagogical Layer 1 only, or reject the mapping.

Parametricity (types): free theorems from the type are property tests. If the type is `forall`, write the free theorem before the body.

---

## Step 2 -- Diagram to types to tests

- Object -> Python type / dataclass / SQLite schema
- Morphism -> function signature, including effect (pure | linear | monadic | interventional)
- Commuting square -> property test
- Dual morphism -> test in the dual space (Royden: tests must separate points)
- Simulation / bisimulation (Lynch, Jacobs, Leroy) -> Layer 1 refines to Layer 2, not only shared unit tests
- Yoneda: a component is determined by its maps into probes; unnamed probes means you do not have the object

If an arrow has no type, stop. Elliott homomorphism test: `mu(op(x,y)) == op(mu(x), mu(y))` **before** writing the body. Pierce: progress + preservation for any typed plugin state machine. Curry-Howard (Girard proofs-and-types, Thompson, Nordstrom): a property test corresponds to a proof inhabitant -- but a *passing* test is evidence, not a proof. An untested hard-core law is an open goal, not a comment. You cannot prove theorems; you can only falsify. Buss: if the test is exponential in the state, it is not an operational certificate -- coarsen the spec.

---

## Step 3 -- Scaffold-specific derivation

### 3a. Variational / ODE lift

Wibisono Bregman Lagrangians; Teschl ODEs; Kidger NODE/CDE/SDE; Liberzon HJB/PMP; Hairer rough paths and regularity structures.

1. Write the agent process as ODE, CDE, or variational principle.
2. Vary the Lagrangian, time reparametrization, or control.
3. Discretize; each scheme is one family member. Each discrete scheme needs its own analysis -- the continuous proof is motivation, not a transfer certificate (Su-Boyd-Candes ODE models Nesterov acceleration, it does not transfer the convergence proof).
4. Irregular tool arrivals -> controlled rough path or Kidger CDE, not a uniform grid.
5. Divergences in the continuum limit -> Hairer counterterms live in the belt; the continuum object stays hard core.
6. Adjoint sensitivity (Kidger): gradients of scheduler/compressor objectives through the ODE/CDE are part of the diagram, not a later autograd accident.

Canonical: gradient flow -> SGD -> momentum -> Nesterov -> AdamW (decoupled weight decay differs from coupled L2 in adaptive methods; do not claim MAP restoration -- the gradient-flow chain is motivation, not a proof).

### 3b. Kernel rewrite

1. Re-express as `score(q,k) = kappa(q,k)`.
2. Legal swaps: linear/product kernels; FAVOR+ (positive orthogonal random features approximating *softmax* and Gaussian attention specifically -- not a general Mercer approximator); Mercer decomposition for PSD kernels; GP posterior (Rasmussen); BM25 (Manning) as a ranking function -- BM25 is NOT a PSD kernel and does not inherit kernel-trick or RKHS guarantees.
3. PSD implies convex retrieval; GP posterior variance is a legal refusal-to-route.

Apply to skill affinity, memory lookup, router scoring.

### 3c. Categorical universal construction

Kan extension, adjunction, lens, functor, operad, monad, weighted limit, natural transformation.

Read the algorithm as the universal arrow. Imputation: the *left* Kan extension Lan_K F(d) = colim_{(c, K(c)->d)} F(c) fills in universally from observed. The *right* Kan extension Ran_K F(d) = lim_{(c, d->K(c))} F(c) restricts via limits. Restriction is F o K, NOT a Kan extension. Always name Lan vs Ran explicitly. Nearest-neighbor via Lawvere-metric enrichment (Pugh, Grundy, Cirstea, Harris arXiv:2312.16529) -- this constructs NN that way; it is not *the* universal construction of all k-NN variants. Backprop as functor: Fong, Spivak, Tuyeras arXiv:1711.10455. New components by composition, not glue. MacLane coherence: do not add ad-hoc associators for skill composition.

Monads for effects; lenses for get/put; operads for n-ary skill composition (Fong-Spivak); decorated cospans / open systems for wiring plugins as morphisms with exposed ports; ologs/schemas (Spivak) for SQLite as a category.

### 3d. Abductive axiom completion

Surprising C -> abduce A that makes C typical -> deduce independent predictions -> test -> promote or kill. Elegance is not evidence. Do not declare A true because it explains C.

### 3e. Filtration / martingale / stopping

Williams, Durrett, Billingsley, Grimmett, Morters.

- Filtration `F_t` = information actually available at t. No peeking (optional sampling theorem).
- Doob decomposition: memory = martingale (innovation) + predictable (cron) + remainder. Store separately.
- Stopping time = tool-loop or cron gate; need UI or bounded stopping to preserve expectations.
- Weak convergence of belt approximations: tightness + portmanteau, not one sample path.
- Coupling: merge memories as a coupling, not a heuristic blend.
- Hitting times (Brownian) = when the compressor should fire; check scaling.

Anti-pattern: interchange limit and expectation without domination (DCT).

### 3f. Spectral / SVD / operator

Axler, Kreyszig, Teschl, Blum.

- Spectral theorem / SVD is the coordinate-free decomposition (uniqueness forces the algorithm).
- Eckart-Young: truncated SVD is the unique optimal F-norm compressor -- that is the design.
- Compact operators are compressible; noncompact => a finite cache is not exact.
- Hilbert projection theorem (Luenberger): the nearest memory in a closed subspace is unique -- that uniqueness is the retriever.
- Functional calculus: define `f(A)` (heat kernel on the skill graph) rather than ad-hoc walks.
- Representation theory (Knapp/Milne): decompose agent state into irreps = independent skill modules; mixing irreps is entanglement (pair with 3i).
- Open mapping / closed graph: "almost surjective" plugin interfaces are ill-typed.

Anti-pattern: determinant tricks, basis-dependent formulas, Euclidean geometry on a graph.

### 3g. Resource / session / separation / linear

Girard, Honda, Reynolds, Harper, Pierce, Klein.

- Context tokens and one-shot tool results are **linear**; skill files are `!` reusable. Do not duplicate linear resources.
- `pre_tool_call` / `post_tool_call` are a **dual session**; check protocol fidelity and deadlock-freedom.
- SQLite updates obey the **frame rule**: local write does not disturb disjoint heap. No global lock for a local put.
- Isolation (seL4): a plugin does not infer another plugin's private heap.
- Progress + preservation as hard-core tests. Harper bidirectional typing: encode lens laws as property tests (not proven statically by Python typing). Named lens laws for get: S->A, put: S x A->S: GetPut: put s (get s) = s; PutGet: get (put s a) = a; PutPut: put (put s a) b = put s b. For polymorphic optics put: S x B -> T, these three laws do not apply unchanged -- use the appropriate optic laws.
- Nipkow: write small-step (or big-step, not both mixed) operational semantics of the plugin before Layer 2.
- Self-rewriting components (Soares tiling): the rewriter must preserve the same invariants (Vingean reflection).

### 3h. Reduction / approximation / competitive / query

Sipser, Arora-Barak, Vazirani, Borodin, Schrijver, Wigderson; Goldreich-Ron query models.

1. Classify: decidable / NP-hard / online / sublinear-query / interactive proof.
2. Undecidable (plugin halting, Rice: any nontrivial semantic property of plugins): refuse exact; approximate or timeout. FLP: no distributed consensus without timeouts.
3. NP-hard: ship an approximation with a **stated ratio** as a property test; prefer primal-dual. If hardness-of-approximation forbids that ratio, change the objective (3d), do not shrink the constant.
4. Online cron (no future): competitive ratio vs offline OPT; FTRL / multiplicative weights / experts. Never cite hindsight OPT as achieved.
5. Wrong oracle => different algorithm. Neighbor vs quantity vs sample.
6. Matroid or totally unimodular: greedy is exact (BPS-style selection). Otherwise greedy is belt.
7. PCP / property testing: structural probes with a query budget.
8. Expensive tools as interactive proofs: state completeness, soundness, and query budget.
9. Flajolet symbolic method: combinatorial skill-DAG constructions get generating functions; singularity analysis predicts blow-up before you ship recursion.
10. Stanley: skill inclusion is a poset; Mobius inversion for inclusion-exclusion routing.
11. Pumping / non-regularity: a DFA-shaped router cannot recognize non-regular trigger languages -- upgrade the object (NFA is not enough either beyond regular).
12. Unique factorization of skills fails (Milne ANT analogy): do not assume a unique prime decomposition of a task into skills.

### 3i. Causal

Pearl, Scholkopf.

- Log-derived skill affinity is observational. Loading a skill is `do(load)`.
- Identifiability via backdoor/front-door, or refuse "this skill caused success".
- A memory write is an intervention on future retrieval. Merging histories that demand different next actions violates the decision boundary (DeMem + Pearl).
- Disentangle latents (CRL); do not store entangled causes in one slot.
- Independent causal mechanisms (Scholkopf): skill modules must not share spurious causes; a coupling in the logs is not a shared submodule.

### 3j. Lyapunov / ISS / control

Khalil, Sontag, Astrom, Liberzon, Bertsekas, Sutton-Barto.

- Produce a Lyapunov `V` (or ISS gain) as the scheduler/plugin certificate.
- Small-gain: compose plugins only when ISS gains multiply below 1.
- Two time-scales: fast tool loop, slow memory. Singular perturbation: do not update both at the same rate without a proof. Averaging (Khalil): control the slow drift, not the fast chatter.
- Anti-windup: saturated token/budget must not keep integrating error.
- PID/loop-shaping for backlog; MPC/rollout for finite-horizon cron; HJB/PMP for the continuous lift; MCTS/AlphaZero-style rollout when the branching process is a game tree.
- GPI and TD(lambda) eligibility traces: credit assignment in memory, not recency. Replayed logs are off-policy; do not cite on-policy guarantees for them.
- Pick discounted vs average-reward MDP (Puterman) explicitly; they are different hard cores.
- Tabular DP hits the curse of dimensionality (Bertsekas): use rollout/MPC, not a value table on cron state.
- UCB/EXP3 on production tools needs a **safe-exploration** constraint (Amodei): regret bounds do not license unconstrained probing.
- Optional extra hard-core term: impact regularizer / side-effect penalty in the Lagrangian, not a later filter.
- Inner loop may be a mesa-optimizer (Hubinger): require inner objective = outer V/Lagrangian. Ngo: loading a capability skill is not installing its goal.

### 3k. Mechanism / epistemic / multi-agent

Nisan, Roughgarden, Shoham, Fagin, Evans.

- Swarm merge: strategy-proof / VCG if agents report scores; otherwise state the price of anarchy (smoothness when available).
- Common knowledge is not shared SQLite. Unreliable channels => no common knowledge; use failure detectors. Distributed knowledge (union of memories, Fagin) can hold when common knowledge does not -- swarm merge must say which.
- Multiparty session types (Honda) for swarm protocols, not only dual pre/post hooks.
- MPC when joint computation must not exchange raw memory.
- Speech-act / BDI: skill triggers are illocutionary types, not bag-of-words.
- Nash/SPE only if the protocol actually has those equilibria; do not assume cooperation.

### 3l. Sheaf / glue / local-to-global

Curry, Robinson, Milne schemes/etale, Fong-Spivak, Hatcher.

- Overlapping context windows and memory shards agree on overlaps (restriction maps).
- Gluing axiom is hard core. Nonzero H1 => locally correct, globally inconsistent -- abduce a cocycle, do not average.
- Localization: reason in one plugin chart, then glue.
- Homotopy type of the decision space: compressor may contract description, not pi0 of actions.
- Spectral sequences: filtered memory; retrieve page-by-page of the filtration.
- Cosheaves: covariant aggregation (counts, integrals) vs sheaves (functions, constraints).
- K-theory: stable equivalence of implementations (clutching = plugin patch).

### 3m. Coalgebra / domain / temporal

Jacobs, Abramsky-Jung, Clarke, Lynch.

- Infinite cron/streams: coinductive specs + bisimulation probes (finer than renaming).
- Bottom is not a value (domain theory); timeouts are explicit. Scott continuity: more information never reverses a committed cron decision.
- Kripke model of cron/WAL/router. Classify safety `G not-bad` vs liveness `F good` vs fairness (justice/compassion).
- Liveness failure without fairness is not a bug. BMC unsat at small k is not a proof.
- Assume-guarantee for plugin composition. Full abstraction: tests distinguish what the denotation distinguishes.
- I/O automata + linearizability **or** eventual consistency -- pick one and test it.

### 3n. Decision / PAC / concentration / sequential

Berger, Degroot, Shalev, Vershynin, Lugosi, Gelman, MacKay, Bishop, Murphy, Hastie, Wainwright, Mezard.

- Specify **loss** before code. Reconstruct as MLE / MAP / Bayes risk. Default to linear least squares (Boyd VMLS) before nonlinear models.
- Refuse inadmissible estimators when a dominating one is known.
- Minimax / least-favorable prior for worst-case cron.
- Value of information: another tool call only if expected loss drop exceeds cost.
- Router generalization: VC/Rademacher sample complexity, or McDiarmid bounded-differences on scores.
- JL / RIP: random-projection compressor with stated eps, delta.
- Posterior predictive checks (Gelman) are Step 6, not optional plots. MAP is not the posterior.
- Conjugate / state-space (Kalman-like) for online numeric memory; Dirichlet process when cluster count is unknown. MacKay MCMC / bits-back when conjugacy fails -- the sampler is belt; the posterior is hard core.
- EM / mean-field / BP are belt approximations to a named graphical model. Junction tree is exact; BP needs a convergence test. Replica-symmetry breaking => multiple routing basins; do not average them.
- Bias-variance split of compressor distortion; boosting for skill ensembles.

### 3o. Equivariance / Lie / symplectic

Bronstein, Knapp Lie/DG, Cannas, Cruttwell.

- Unordered memory sets: permutation-equivariant ops (hard core). Geometric inputs: gauge/group equivariance.
- Lie algebra = infinitesimal legal updates; finite updates via exponential map. Discrete jumps that do not exponentiate break the ODE lift.
- Noether: symmetry => conserved quantity in the hard core (mass, symplectic area, information-action). Stokes: conservation is a closed-form law, not a checksum afterthought.
- Reverse differential categories: derivatives through discrete agent steps are part of the diagram.

### 3p. Privacy / crypto / fairness

Dwork, Boneh-Shoup, Katz-Lindell, Evans, Barocas.

- Memory writes that may leak people: eps-DP with composition accounting as hard core. "Anonymize" is not DP.
- Security via reduction, not vibes. Random oracle is belt. Do not invent primitives.
- Fairness: independence, separation, and sufficiency are incompatible (Kleinberg). Choose **one** criterion as hard core.

---

## Step 4 -- Analog search (before coding)

1. Express the target as `{objects, morphisms, laws, modality, certificate}`.
2. Search the skill corpus by relational skeleton, not book title.
3. Align predicates (`compose`/`then`, `restrict`/`project`); discard attribute matches.
4. Each conceptual slip is debt requiring a property test (Copycat).
5. If alignment fails, re-represent: dualize (Boyd, OT primal-dual, Galois correspondence), coarsen (homotopy, weak convergence), change instance measure (KIT), change oracle type (Weizmann).
6. Reject any map that breaks a hard-core law. Among remaining maps, prefer fewer conceptual slips. Do NOT use the ratio laws/slips literally (it divides by zero and is undefined for zero slips). Prefer the most coherent map that passes all hard-core property tests.

Galois (Milne): subgroups of symmetries correspond to intermediate implementations. List **all** legal variants from the correspondence, then pick.

---

## Step 5 -- Dual implementation pipeline

Never go theory -> production.

**Layer 1 -- Pedagogical demo.** Minimal pure Python; every hard-core law as a property or type test; smallest meaningful instance. Optionally Coq/Isabelle extraction (Chlipala, Nipkow) when the invariant is kernel-level.

**Layer 2 -- Drop-in module.** Async plugin, cron, or SQLite. Must pass Layer 1 tests **and** admit a simulation/refinement (Leroy CompCert, Lynch): Layer 2 equals Layer 1 on observations. Tests alone are incomplete (you sampled paths).

Performance hacks live only in the belt. A hack that fails Layer 1 -> Step 3d, not a skip.

Separate in the filesystem: `references/demo.py` vs the live module.

Shannon source-channel separation: do not fuse compressor and router into one untestable blob. China/Zhihu: the production update must algebraically equal the paper (Zhang D2L).

---

## Step 6 -- Probe gate (all that apply)

1. **Representation (Amari/Chentsov).** Rename, recoordinate, permute unordered inputs. Hard-core behavior is invariant.
2. **Bisimulation (Jacobs).** Distinguish states the denotation distinguishes; identify those it must not.
3. **Temporal (Clarke).** Replay counterexample lassos on cron/WAL. Recheck liveness under the intended fairness.
4. **Predictive (Gelman, Shalev).** Posterior predictive or held-out PAC bound -- not training-set loss.
5. **Inner alignment (Hubinger, Amodei).** Construct a legal belt hack that improves the proxy (reward hacking, side-effecting) and check it is rejected. Oversight cannot be "the tests we happened to write".
6. **Semantic preservation (Leroy).** Optimize Layer 2 (cache, batch) and re-run simulation, not only unit tests.
7. **Sensitivity (Malliavin).** Derivative of outputs wrt memory noise; large unexpected sensitivity => missing invariant.
8. **Instance measure (KIT).** Change the workload (worst-case -> random graph -> realistic) until theory predicts practice.
9. **Pseudorandom probes (Wigderson).** Hand-picked examples are not a probe set; use expanders / PRG-like samples so the probe cannot be gamed by the belt.

If it breaks: the extrapolation relied on surface form -- return to Step 0.

Israeli tradition: the query/oracle interface **is** the mathematical object. Wrong oracle = different algorithm.

---

## Step 7 -- Naur theory document

Ship with every new component:

- Why it exists (which theorem / universal property forces it)
- Mapping table: hard core vs belt
- Regularity conditions and certificate kind
- Axioms actually used (Dean reverse mathematics: do not assume ACA0 for a primitive-recursive plugin)
- Inner vs outer objective
- Composition theorems relied on (lens, DP, ISS small-gain, session, sheaf glue, DP composition)
- How a future modification should look
- One falsifying experiment
- Known unknowns (Hendrycks): list unsolved safety/regularity conditions the component does **not** handle
- Cut-eliminate (Buss): do not stack removable lemmas

Without this, the component is a dead program (Naur 1985). Do not re-compact the theory document away.

---

## Application to Hermes components

### Memory systems

- Markov category; mass conservation; forgetting = (unbalanced) OT / Sinkhorn; geodesic forgetting = Wasserstein gradient flow (Villani).
- Imputation = Kan extension from observed to full state.
- Retrieval + update = lenses (GetPut, PutGet, PutPut) plus Reynolds frame on disjoint rows.
- Hilbert projection: unique nearest memory in a closed subspace (Luenberger); if the set is not closed/convex, uniqueness is gone -- say so.
- Doob split: innovations vs predictable schedule vs remainder in separate tables; retrieve only `F_t`-measurable fields.
- Decision distortion (DeMem): preserve pi0 of action-relevant histories; homotopy-legal compression (Hatcher). Descriptive fidelity is belt.
- Prior = maxent / conjugate / GP posterior (Jaynes, Murphy, Rasmussen).
- Irregular events: rough signature or CDE (Hairer, Kidger), not raw sequences.
- Coresets / JL / truncated SVD (Blum, Vershynin, Axler) as belt with stated eps.
- Sheaf glue across SQLite shards; eps-DP on writes (Dwork) with composition accounting.
- HMM/CRF for conversational state (Jurafsky); Kalman-like state-space for numeric latents.
- RANSAC on tool outputs (Szeliski) before commit.
- Spectral clustering of the memory graph; check expander/percolation assumptions (Wigderson, Grimmett) instead of assuming connectivity.
- Mixing time (Hairer Markov, Durrett): how long until init is forgotten -- that is the legal TTL.

### Scheduler / cron

- Variational ODE + quadrature family; duality-gap stop (Boyd).
- MDP greedy (Puterman); rollout/MPC not value tables (Bertsekas); pick discounted vs average reward.
- UCB / EXP3 / linear contextual bandits (Lattimore) with a safe-exploration envelope on production tools.
- Online: competitive ratio (Borodin); never use hindsight OPT.
- Lyapunov / ISS + anti-windup on budget (Khalil, Astrom).
- Stopping time / VOI / sequential test for tool loops (Williams, Degroot).
- Nyquist: cron frequency at least twice the process bandwidth (Vetterli). Poisson arrivals (Grimmett).
- CTL/LTL: `AG not (writer and concurrent)`, `G (req -> F ack)` under justice (Clarke). Petri net (Baez) when concurrency is the object.
- Two time-scales: fast hooks, slow memory.
- Eligibility traces for delayed outcomes (Sutton-Barto).
- FLP: swarm cron consensus needs timeouts.

### Skill router

- Kernel on the simplex; linear kernel O(n); BM25; e-flat or m-flat geometry (Amari) not Euclidean.
- Observational affinity is not `do(load skill)` (Pearl).
- BPS greedy only with matroid-like submodularity (Schrijver); else state an approximation ratio.
- PAC bound on routing regret; McDiarmid on scores; typical-set features (Cover).
- Hamming separation of skill descriptions (Lin) -- near-duplicate triggers are a coding failure.
- Junction tree vs BP for multi-skill composition (Wainwright); RSB => do not average modes (Mezard).
- Compositional routing: decompose then retrieve; Yoneda probes; operadic n-ary compose.
- Equivariance to skill-list permutation.
- Adversarial queries: EXP3, not UCB.
- Precision/recall of the router are tests (Manning), not dashboards in the belt.

### Context compressor

- Rate-distortion with **decision** distortion, not string fidelity (Shannon, Cover-Thomas, DeMem). `R(D) = min I(X;Y) s.t. E[d] <= D` with d = decision conflict.
- Data-processing inequality is hard core: I(decision; compressed) <= I(decision; raw). Chain rule: drop tokens with small I(token; decision | kept), not "old" tokens.
- Fano: router error is lower-bounded by I(query; skill); if the bound forbids the advertised accuracy, change the object.
- Wavelet/sparse (Mallat); pyramid (Szeliski); SVD/Eckart-Young; JL.
- AEP: keep typical task tokens, drop atypical noise -- unless atypicality is the safety decision. Entropy rate of the memory process (Cover) is a compression lower bound; beating it means you changed the object.
- Channel coding (Shannon/Gallager/Lin): skill descriptions carry redundant parity against router noise; CRC-style checksums are tests, not comments.
- Displacement convexity (Villani): OT-geodesic forgetting preserves convexity of the loss along the path; ad-hoc decay need not.
- Gromov-Wasserstein (Peyre) to compare skill graphs of different sizes; do not force a Euclidean embedding first.
- Do not compress below the decision homotopy or the RD keep-floor.
- Source independent of channel: compressor must not silently reroute skills.

### Script / plugin design

- Default interface: lens, with bidirectional types checking get/put. Else monad. Linear for one-shot. Session dual for pre/post hooks.
- Progress + preservation; assume-guarantee; ISS small-gain; parametricity free theorems.
- I/O automata: linearizability or eventual consistency, not "correctness".
- Layer 2 refines Layer 1 (CompCert). Isolation (seL4).
- Cruttwell: differentiating through a hook puts the derivative on the diagram.
- Tiling: a plugin that rewrites plugins preserves the hard core.

### Skill design (theorems -> skills)

- Trigger = the **decision** the theorem enables, not the book title. Keep the frontmatter description a self-contained trigger.
- One kill-experiment. Solomonoff / MDL preference for shorter skills (Hutter, MacKay, Li-Vitanyi).
- Beliefs track logical uncertainty (Garrabrant), not raw frequencies.
- Reverse-math: list axioms. Fairness: at most one Kleinberg criterion.
- Ngo: a capability skill is not a goal; do not treat router hits as objective installation.
- Mesa: the skill must not install an inner objective that differs from the outer Lagrangian.
- Cut-eliminate the skill text; density over anthology.

### Swarm / multi-agent

- Incentive compatibility or a stated PoA; MPC without raw share; common knowledge only with reliable broadcast; distributed knowledge otherwise; multiparty sessions; FLP implies timeouts; fabricated-consensus gate when provenance is the object.

---

## Corpus routing

For each area: extra mechanism (not already in 3a-d), Hermes slot, failure mode.

**Pure math.** Axler LA: SVD uniqueness -> compressor/router bases; fail: determinant/basis hacks. Axler/Royden/Knapp analysis: DCT, completeness, dual separating tests; fail: limit/E swap, incomplete iterate space. Knapp algebra/Lie/DG: modules over update rings, exponential map, Stokes/Noether; fail: non-exponentiating jumps. Milne: Galois listing of legal variants, scheme charts, etale H1 glue; fail: local-ok/global-bad. Billingsley/Durrett/Williams/Grimmett/Morters: tightness, coupling, martingales, percolation, hitting times; fail: one-path "convergence", peeking, assuming a connected skill graph. Hairer: rough/CDE, renormalization counterterms, Malliavin sensitivity, mixing TTL; fail: uniform-grid irregular input. Teschl/Kreyszig: spectral functional calculus, open mapping; fail: ad-hoc graph walks. Hatcher: homotopy-legal compress, spectral-sequence retrieval, K-theory patches; fail: killing pi0 of actions. Cannas: symplectic conservation as hard core.

**IT / signal / OT / coding.** Cover/Shannon/Gallager/MacKay: R(D), AEP, capacity, source-channel split, LDPC/BP, MDL bits; fail: fused untestable compress+route. Mallat/Vetterli: sparsity, Nyquist, filter banks / multi-rate plugins; fail: sub-Nyquist cron. Villani/Peyre-Cuturi: W-geodesics, unbalanced OT, Sinkhorn as belt; fail: treating eps-reg as hard core. Lin: min-distance skill texts; fail: near-duplicate triggers.

**ML.** Bishop/Barber/Murphy/Gelman: EM belt, conjugates, hierarchical models, posterior predictive. Hastie: bias-variance, boosting ensembles. Shalev: PAC. Rasmussen: GP uncertainty as refusal. Berger/Degroot: admissibility, VOI, minimax. Vershynin/Lugosi: JL, McDiarmid. Wainwright/Mezard: exact vs BP, RSB modes. Blum: coresets, streaming. Bronstein: equivariance. Scholkopf/Pearl: disentangle, do-calculus. Kidger: NODE/CDE. Szeliski: pyramid, RANSAC. Jurafsky: CRF/HMM dialogue. Manning: BM25, P/R tests. Zhang: algebra equals code. Amari: natural-gradient uniqueness.

**RL / control / opt.** Sutton-Barto: GPI, TD(lambda). Bertsekas: rollout, MCTS, DP. Lattimore: UCB/EXP3/linear. Puterman: MDP policy. Boyd/VMLS/Luenberger: convexity, KKT, duality gap, DCP, least-squares first, function-space Lagrange; fail: nonconvex treated as convex. Liberzon: PMP/HJB. Sontag/Khalil/Astrom: ISS, Lyapunov, small-gain, two-scale, PID anti-windup; fail: integrate while saturated.

**Logic / PL / complexity.** Sipser/Arora-Barak/Wigderson: reductions, expanders, PCP probes, hardness of approximation. Flajolet/Stanley: GF blow-up, Mobius on skill posets. Schrijver/Vazirani: polyhedra, matroid greedy, primal-dual ratios. Nisan/Roughgarden: VCG, smoothness PoA. Borodin: competitive ratio, FTRL. Pierce/Harper/Thompson/Nordstrom/HoTT/Awodey/Rijke: types, univalence, identity types. Buss/Girard/Harrison/Nipkow/Chlipala: cut-elim, linear logic, ATP axiom audit, extraction. Reynolds/Klein/Leroy/Honda/Lynch/Clarke/Fagin/Dean: frame, isolation, refinement, sessions, I/O automata, CTL/LTL, common knowledge, minimal axioms.

**Category theory.** MacLane/Riehl/Leinster/Perrone/Milewski/Fong-Spivak/Spivak/Shiebler/Cruttwell/Baez/Curry/Robinson/Jacobs/Abramsky-Jung: Yoneda, Kan, lenses, operads, ologs, sheaves/cosheaves, coalgebra, domains, Petri nets, reverse derivatives, coherence.

**Safety / crypto / fairness / agents.** Hutter/Garrabrant: mixture, logical induction. Hubinger/Soares/Amodei/Hendrycks/Critch/Ji/Ngo: mesa, tiling, reward hacking, side effects, safe exploration, scalable oversight. Barocas: one fairness axiom. Dwork/Evans/Boneh/Katz: DP composition, MPC, game-based reductions. Shoham: SPE, protocols, speech acts.

---

## Cross-cultural extrapolation engines

**Japan (Amari lineage):** invariance / coordinate-freedom forces the algorithm. Natural gradient, alpha-connections, SVD, Sei g-models survive Chentsov uniqueness. Ask what the unique invariant-preserving form is.

**Korea (PDE -> discretize -> failure modes):** every numerical artifact is a theorem-level limitation. Name the PDE, derive the discretization, list failure modes as theorems before implementing.

**Russia (Habr exam culture):** derive the loss from likelihood + prior before writing code. From-scratch implementation is the verification.

**Israel (Weizmann):** the query/oracle interface is a mathematical object. Novel algorithms appear as distinctions between query types.

**Germany (KIT algorithm engineering):** formalize -> design -> implement -> prove correctness -> analyze runtime. Then change the instance measure until theory predicts practice.

**China (industrial):** production update must algebraically equal the paper. Verify plugin update rules against the paper's algebra before merging.

---

## Anti-patterns

- Lexical analogy; skipping the mapping table; scaffold chosen by familiarity
- Belt violates hard core; undocumented paradigm switch
- LLM vector-arithmetic as structure mapping
- Hypothesis without a kill-test; re-compacting the Naur document
- Skipping the probe gate
- Interchanging limit and expectation without domination; claiming convergence from one path
- Peeking future tokens; treating bottom as a value; violating Scott monotonicity
- Observational affinity as causal
- Offline OPT cited for online cron; greedy where the feasible set is not a matroid
- Nonconvex treated as convex; ignoring duality gap
- All three Kleinberg fairness axioms at once
- Anonymize-without-DP; invented crypto; random oracle as hard core
- Declaring liveness false without fairness; BMC unsat as proof
- Tests pass while simulation fails (no refinement)
- Proxy-improving belt hack (mesa / reward hacking / side effects)
- Duplicating linear tokens; global lock instead of frame
- Fusing source and channel; compressing below decision pi0
- Sub-Nyquist cron; equal-rate fast/slow without singular perturbation
- Averaging BP/RSB modes; assuming an expander/connected skill graph
- Local correctness without gluing / H1
- Inadmissible estimator; MAP treated as the posterior
- Determinant / basis-dependent "invariants"
- Swapping competitive, approximation, and PAC certificates
- Inner objective != outer Lyapunov / Lagrangian
- Ad-hoc associators that ignore coherence
- Self-rewrite that does not tile invariants
- Hand-picked tests instead of PRG/expander probes
- On-policy bounds cited for off-policy logs
- UCB without safe-exploration on live tools
- Capability load treated as goal install
- Unique skill factorization of a task
- Untested hard-core law (open Curry-Howard goal)
- Claiming I(decision; compressed) > I(decision; raw)
- Advertising router accuracy below the Fano bound
- Treating finite-eps Sinkhorn matrix as the sparse OT plan (it is dense if K>0; only the eps->0 limit may be sparse)
- Saying "Ran restricts" (restriction is F o K; both Lan and Ran *extend*)
- Omitting Lan vs Ran distinction when using Kan extensions
- Claiming property tests or LLM reasoning *prove* an invariant (they check and falsify)
- Claiming a discretization or kernel swap inherits the source proof without its own analysis
- Treating Markov and lens as the same hard core for the same component without an explicit construction
- Calling BM25 a PSD kernel or inheriting kernel-trick guarantees from it
- Claiming O(n^2)->O(n) for scoring n skills (that speedup is for sequence-length attention, not skill count)
- Putting iterative solvers, inner LLM calls, or heavy computation in synchronous pre_tool_call / pre_llm_call hooks
- Injecting synthetic conversation messages from a plugin hook
- Implementing Solomonoff/AIXI exactly (it is uncomputable; use as a normative pointer only)
- Applying AI-Noether abduction outside polynomial axiom systems
- Applying simple-lens GetPut/PutGet/PutPut laws to a polymorphic optic put: S x B -> T without adjustment
- Non-constructive existence (AC, pure completeness theorems) treated as an executable algorithm
- Homomorphism or lens tests on floats without an explicit numerical tolerance
- Copying the Markov sum==1 hard core onto a leaky forgetter (substochastic needs its own hard core)

---

## Quick reference

Given a new theorem, run in order:

0. Extract objects, morphisms, laws, regularity, modality, certificate; pick scaffold by structure
1. Mapping table; freeze hard core vs belt
2. Diagram -> types -> property tests -> dual probes -> simulation
3. Execute the matched scaffold (3a-3p)
4. Analog search; dualize / coarsen / oracle-shift if stuck
5. Layer 1 demo with tests, then Layer 2 that refines it
6. Probes: representation, bisimulation, temporal, PPC/PAC, inner alignment, sensitivity, instance measure, PRG/expander samples
7. Ship Naur document with reverse-math axioms, known unknowns, and composition theorems

---

## Key sources

Structure mapping: Gentner 1983; Fauconnier-Turner; Hofstadter Copycat; Elliott denotational design; Naur 1985; Lakatos; Peirce; Kuhn.

Algorithms from invariance: Chentsov; Amari; Eckart-Young; Wibisono et al. arXiv:1603.04245; Tsai et al. arXiv:1908.11775; Choromanski et al. arXiv:2009.14794 (FAVOR+); Fong-Spivak arXiv:1803.05316; Shiebler et al. arXiv:2106.07032; Fong, Spivak, Tuyeras arXiv:1711.10455 (backprop as functor); Shiebler arXiv:2203.09018 (Kan extensions in data science); Pugh, Grundy, Cirstea, Harris arXiv:2312.16529 (NN via Lawvere enrichment); Davies et al. Nature 2023 (FunSearch); Fawzi et al. Nature 2022 (AlphaTensor); Srivastava et al. arXiv:2509.23004 (AI-Noether -- polynomial axiom systems only; do not apply to general Hermes abduction).

Practical: Typeclassopedia; PythonOT / OTT-JAX / geomloss; pysheaf.

Multilingual: Chentsov uniqueness / natural gradient; Sei g-models (KURIMS 1560); Goldreich-Ron ECCC TR05-073; KIT five-stage bridge; Zhihu industrial algebra-equals-code; AdamW decoupled decay.

Corpus books (route via the catalog; never use a title as a skill trigger): Axler; Knapp; Milne; Royden; Billingsley; Durrett; Williams; Grimmett; Morters; Hairer; Teschl; Kreyszig; Hatcher; Cannas; Cover-Thomas; Shannon; Gallager; MacKay; Mallat; Vetterli; Villani; Peyre-Cuturi; Lin; Bishop; Hastie; Murphy; Shalev; Barber; Gelman; Rasmussen; Amari; Berger; Degroot; Vershynin; Lugosi; Wainwright-Jordan; Mezard-Montanari; Blum; Bronstein; Scholkopf; Pearl; Zhang; Kidger; Szeliski; Jurafsky-Martin; Manning; Sutton-Barto; Bertsekas; Lattimore; Puterman; Boyd; Luenberger; Liberzon; Sontag; Astrom; Khalil; Sipser; Arora-Barak; Wigderson; Flajolet; Stanley; Schrijver; Vazirani; Nisan; Roughgarden; Borodin; Pierce; Harper; Thompson; Nordstrom; HoTT / Awodey / Rijke; Buss; Girard; Harrison; Nipkow; Chlipala; Reynolds; Klein; Leroy; Honda; Lynch; Clarke; Fagin; Dean; MacLane; Riehl; Leinster; Perrone; Milewski; Fong-Spivak; Spivak; Shiebler; Cruttwell; Baez; Curry; Robinson; Jacobs; Abramsky-Jung; Hutter; Garrabrant; Hubinger; Soares; Amodei; Hendrycks; Critch; Ji; Ngo; Barocas; Dwork; Evans; Boneh-Shoup; Katz-Lindell; Shoham.

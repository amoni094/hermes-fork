# Theory-to-Skill Mining: Converting Book Knowledge to Coding Rules

Procedure for extracting actionable coding rules from theoretical book knowledge bases.

## The Core Filter

A theoretical result justifies a skill patch only if it produces one of:
- A decision procedure: "do X when condition Y holds"
- A falsifiable check: "test Z to verify correctness"
- A failure mode with a named mechanism: "bug class B occurs when assumption A is violated"

Pure mathematical statements (existence proofs, asymptotic bounds without operational consequence) are not worth adding to coding skills.

## What Each Book Domain Yields

### Algorithms (CLRS)
- Loop invariants as documented correctness artifacts (not style)
- Amortized analysis for data structure code review (dynamic arrays, heaps, union-find)
- Master Theorem before profiling recursive performance issues
- Invariant-based test structure: verify initialization, one iteration, termination

### Category Theory (Milewski)
- Composition law: a function requiring caller context to be correct is not composable
- Functor laws: .map()/.filter() chains must be side-effect-free and structure-preserving
- Monad laws: chained operations (Promise.then, flatMap, Result) must satisfy associativity
- ADTs / sum types: prefer discriminated unions over null-checks and boolean flags
- Kleisli pipeline testing: test each monadic step in isolation before testing composition

### Type Theory (Thompson)
- Curry-Howard: type signatures are theorems; narrow types over runtime checks
- Parse-don't-validate: constructors are validators; invalid states should not be constructible
- Totality: partial functions (crash on some inputs) are defects; use Option/Result
- Structural induction for debugging recursion: bug lives in base case XOR inductive step

### Causality (Pearl)
- Observation vs intervention: correlation with bug != disabling X prevents bug
- Confounding: fix resolves in test but not production -> suspect unobserved confounder
- Collider bias: filtering logs to error states manufactures false causal links
- Counterfactual tests: for each fix, write the test that fails without the fix
- Causal DAGs for concurrency: race conditions = cycles or missing ordering edges in causal DAG

### Sequential Analysis (Wald)
- SPRT optimal stopping for property-based tests: stop on likelihood ratio threshold
- Type I/II framing: flaky tests = high false positive rate; coverage gaps = high false negative rate
- Bisection bound: git bisect or binary search debugging should take log2(N) steps; more = exploring
- Explicit stopping criteria before any retry/backoff loop: unbounded sequential procedures have unbounded expected cost

### Statistical Learning (ESL / Hastie)
- Bias-variance diagnosis before tuning: high train error = bias; high train/test gap = variance
- Regularizer selection: L2 = Gaussian prior (smooth), L1 = Laplace prior (sparse); match to domain
- CV harness as mandatory for ML test suites: training-set evaluation is tautological
- Curse of dimensionality in debugging: test data often low-dimensional, production high-dimensional
- Bootstrap confidence intervals over point estimates for stochastic metrics

### Convex Optimization (Boyd & Vandenberghe)
- Convexity check before custom optimizer: non-convex objective + convex solver = silent bug
- Step size from Lipschitz constant: learning rate must be <= 1/L; derive L before setting it
- Optimizer failure modes: (a) non-convex objective, (b) step size too large, (c) ill-conditioned Hessian
- Duality gap as convergence certificate: non-zero gap = solution not optimal
- KKT condition tests: verify KKT at reported solution, not just that objective decreased

### Markov Decision Processes (Puterman)
- Markov property in agent loops: decision function depending on unbounded history violates MDP formulation
- Convergence check: value iteration requires gamma < 1; policy iteration always converges for finite MDPs
- Reward shaping validity: shaped reward F(s,a,s') = gamma*Phi(s') - Phi(s) preserves optimal policy; arbitrary bonuses do not
- Finite vs infinite horizon: finite horizon requires time-indexed value functions; mixing is a design defect
- Bellman optimality as test criterion for planning code

### Probability Theory (Jaynes)
- Probability axiom compliance: confidence scores must be non-negative and sum to 1 over exhaustive events
- Maximum entropy prior selection: uniform when nothing known, Gaussian when only mean/variance known
- Bayesian debugging: prior over bug locations, update on each observation; skipping to confident diagnosis = degenerate prior
- Calibration tests: predicted probability p should match empirical frequency p; use ECE or reliability diagram
- Heuristic scoring systems without probabilistic derivation are uncalibrated; acknowledge or replace

### Logic in Computer Science (Huth & Ryan)
- Hoare triples as docstring standard: {P} function {Q} for any function with complex state
- Weakest precondition for debugging: compute wp backwards from failing postcondition = minimal reproduction case
- LTL safety vs liveness: concurrent/async code needs both; different verification strategies apply
- State explosion as complexity signal: if enumerating reachable states explodes, simplify the concurrency model first

### Information Theory (Shannon, Cover & Thomas, Gallager, MacKay, Li-Vitanyi)
- MDL abstraction test: extract abstraction only if L(interface) + L(code|interface) < L(code alone)
- DPI and abstraction layers: each layer can only reduce information available to callers
- Equivocation and naming: reader uncertainty about a name's intent lower-bounds the misuse rate
- Logical depth (Bennett): high-abstraction, heavily-indirected code hides complexity, does not remove it
- Comments and redundancy: comment the why not the what -- the what has zero mutual information given the code
- Decision-theoretic test value (MacKay): a test has value only if it can change the action
- AEP / typical inputs: property-based tests cover typical set efficiently; hand-crafted examples hit rare boundary points
- Channel-capacity readability (Gallager): reviewer should decode intent from structure alone, without author explanation

## Dispatch Pattern for Multiple Books

When mining multiple books in parallel:
1. One subagent per book (not per domain cluster -- depth matters more than breadth per agent)
2. Each subagent: extract text with pdftotext, read key chapters, apply specific patches with skill_manage
3. Include in each subagent goal: explicit list of improvements to look for, exact patch target paths, instruction to cite the chapter/section
4. Up to 10 parallel subagents is feasible; they write to different skill sections and don't conflict
5. Report format: skill created (yes/no), patches applied (list), failures (list)

## Vocabulary Abuse Check (Critical)

Before applying any mathematically-named rule to a coding skill, verify the code's inputs match the mathematical object the term describes:
- 'Lipschitz contraction' requires a ratio of metric deltas (not a learning rate)
- 'Span seminorm' requires a value function on a state space (not a PID error range)
- 'Bayesian update' requires a proper probability distribution (not a score)
- 'Functor' requires preservation of identity and composition (not just a .map() call)

If the input doesn't match the object, restate as a plain heuristic -- drop the mathematical name. ~30-50% of book-derived proposals fail this check (same rate as arXiv sweep proposals).

---
name: boyd-convex-optimization
description: "Use when implementing gradient descent or convex solvers."
related_skills:
  - coding-conventions
  - systematic-debugging
  - test-driven-development
---

# Boyd & Vandenberghe — Convex Optimization (CUP 2004; 7th printing 2009)

Knowledge base from Boyd & Vandenberghe *Convex Optimization*. Use when implementing gradient descent, numerical solvers, loss functions, or reasoning about convergence guarantees and numerical stability in optimization code.

Source: `/var/home/rainbow/books/optimization/boyd-vandenberghe-convex-optimization.pdf`.
Notation: ≽ / ≼ are PSD / NSD; ≻ / ≺ are PD / ND. Domain of f is `dom f`. Optimal value `p⋆`; dual optimal value `d⋆`.

The full benefits of convex optimization only come when the problem is **known ahead of time to be convex**. Running a convex solver on an unrecognized nonconvex objective is a silent correctness bug, not a performance issue.


## Model Routing

Convex problem formulation, KKT conditions, duality proofs: magistral-small-latest (mistral) or deepseek-v4-pro non-think (no tools). Implementation (cvxpy, scipy.optimize): grok-4.6 workers via delegate_task.


## Convexity — definition and checking

A set C is convex if `x, y ∈ C` and `θ ∈ [0,1]` imply `θx + (1-θ)y ∈ C`.

A function f is convex if `dom f` is convex and for all `x, y ∈ dom f` and `θ ∈ [0,1]`:

```
f(θx + (1-θ)y) ≤ θ f(x) + (1-θ) f(y)
```

A convex optimization problem has a convex objective and convex inequality constraints (equality constraints must be affine).

**Restriction to a line.** f is convex iff for every `x` and direction `v`, `g(t) = f(x + t v)` is convex on its domain. Check convexity in 1-D first.

**First-order (differentiable).** f convex iff `dom f` convex and

```
f(y) ≥ f(x) + ∇f(x)^T (y - x)     for all x, y ∈ dom f
```

The first-order Taylor expansion is a **global underestimator**. Consequence: `∇f(x) = 0` ⇒ `x` is a **global** minimizer.

**Second-order (twice differentiable).** f convex iff `dom f` convex and Hessian PSD everywhere on the domain:

```
∇2 f(x) ≽ 0     for all x ∈ dom f
```

On R this is `f''(x) ≥ 0`. `∇2 f(x) ≻ 0` everywhere ⇒ strictly convex, but the converse fails (`x^4` is strictly convex with `f''(0)=0`). Quadratic `(1/2) x^T P x + q^T x + r` is convex iff `P ≽ 0`, strictly convex iff `P ≻ 0`.

**Do not drop convexity of the domain.** `f(x)=1/x^2` on `{x ≠ 0}` has `f''>0` everywhere on its domain but is **not** convex.

**Standard convex examples (verify via Hessian or the defining inequality):** `e^{ax}`; `x^a` on R++ for `a≥1` or `a≤0`; `|x|^p` for `p≥1`; `-log x`; `x log x`; every norm; `max{x_i}`; `x^2/y` on `y>0`; `log ∑ e^{x_i}`.

**Operations that preserve convexity:** nonnegative weighted sum, composition with an affine map, pointwise maximum/supremum, composition `h(g(x))` when h is convex and nondecreasing (or nonincreasing if g is concave).

**Code check before a custom optimizer.** For a scalar objective, confirm `f'' ≥ 0` on the domain (or Hessian eigenvalues ≥ 0). For a vector objective, confirm Hessian PSD (Cholesky without pivoting succeeds iff PD; PSD needs a rank-revealing test). If the check fails, do not feed the problem to a convex solver.

## Strong convexity

On a sublevel set S, f is strongly convex with modulus `m > 0` if

```
∇2 f(x) ≽ m I     for all x ∈ S
```

Then for `x, y ∈ S`:

```
f(y) ≥ f(x) + ∇f(x)^T (y-x) + (m/2) ||y-x||_2^2
```

Consequences:

- Unique minimizer `x⋆`.
- Suboptimality from gradient size: `p⋆ ≥ f(x) - (1/(2m)) ||∇f(x)||_2^2`, so `||∇f(x)||_2 ≤ √(2m ε)` ⇒ `f(x)-p⋆ ≤ ε`.
- Distance to optimum: `||x - x⋆||_2 ≤ (2/m) ||∇f(x)||_2`.

If also `∇2 f(x) ≼ M I` on S, then `m I ≼ ∇2 f ≼ M I` and `κ = M/m` bounds the Hessian condition number. Gradient method iteration count grows like `κ`. Oscillation / crawling along a valley is usually this, not a coding typo.

## Lipschitz gradients and step size

`∇2 f ≼ M I` on S ⇔ `∇f` is Lipschitz with constant `L = M`:

```
||∇f(x) - ∇f(y)|| ≤ L ||x - y||
```

Quadratic upper bound:

```
f(y) ≤ f(x) + ∇f(x)^T (y-x) + (L/2) ||y-x||_2^2
```

**Fixed-step gradient descent** `x := x - t ∇f(x)` is safe only for `0 < t ≤ 1/L`. Boyd's analysis: exact line search on this bound is minimized at `t = 1/M = 1/L`. Backtracking (Armijo) with `α ∈ (0, 1/2)` is guaranteed to accept some `t ≥ min{1, β/M}`.

**Do not pick a learning rate without a bound on L.** If L is unknown, use backtracking line search (typical `α ∈ [0.01, 0.3]`, `β ∈ [0.1, 0.8]`) rather than a magic constant. If the objective leaves `dom f` (logs, barriers, `x^2/y`), shrink `t` until the trial point is in the domain **before** checking Armijo.

Stopping criterion (Boyd): `||∇f(x)||_2 ≤ η`, justified by the strong-convexity bound (9.9)–(9.10). "Objective decreased" is not a certificate of optimality.

## Gradient descent convergence

Algorithm: `Δx := -∇f(x)`, choose `t` by exact or backtracking line search, `x := x + t Δx`.

Under `m I ≼ ∇2 f ≼ M I` on the relevant sublevel set:

- Exact line search: `f(x^{(k)}) - p⋆ ≤ (1 - m/M)^k (f(x^{(0)}) - p⋆)` — linear (geometric) convergence. Iterations to ε-accuracy scale as `(M/m) log((f0-p⋆)/ε)`.
- Backtracking: same form with `c = 1 - min{2mα, 2βα m/M}`.
- Quadratic example `f = (1/2)(x_1^2 + γ x_2^2)`: error contracts by `|(γ-1)/(γ+1)|^2` each step. `γ=1` solves in one step; `γ ≫ 1` or `γ ≪ 1` crawls. This is conditioning, not a bug in the update.

Newton (`Δx_nt = -(∇2 f)^{-1} ∇f`) is affine-invariant and far less sensitive to `κ`. Prefer Newton / quasi-Newton when the Hessian (or a PSD approximation) is available and n is modest. Solve the Newton system by **Cholesky**, not a dense inverse: `H = L L^T`, forward/back substitution. Newton decrement `λ^2 = ∇f^T H^{-1} ∇f`; stop when `λ^2 / 2 ≤ ε`.

## Duality

Lagrangian `L(x, λ, ν) = f_0(x) + ∑ λi f_i(x) + ∑ νi h_i(x)`, `λ ≥ 0`.
Dual function `g(λ, ν) = inf_x L`. Dual problem: maximize `g` over `λ ≥ 0`.

**Weak duality** always: `d⋆ ≤ p⋆`, even if the primal is nonconvex. Optimal duality gap `p⋆ - d⋆ ≥ 0`.

For a primal-dual feasible pair `(x, (λ, ν))`, the **duality gap** is `f_0(x) - g(λ, ν)`. It is a **convergence certificate**: gap 0 ⇒ both points are optimal. A nonzero gap means the reported `x` is not certified optimal (either not optimal, or strong duality failed).

**Strong duality** (`d⋆ = p⋆`) holds for convex problems under a constraint qualification. **Slater:** exists `x ∈ relint D` with `f_i(x) < 0` and `Ax = b`. Affine inequalities need not be strict. Slater also implies the dual optimum is attained when `d⋆ > -∞`.

**Code:** constrained solvers should report the duality gap (or a computable upper bound on it). Do not treat "feasible + objective dropped" as done.

## KKT conditions

For differentiable problems with strong duality, any primal-dual optimal pair satisfies (Boyd 5.49):

1. Primal feasibility: `f_i(x⋆) ≤ 0`, `h_i(x⋆) = 0`
2. Dual feasibility: `λ⋆ ≥ 0`
3. Complementary slackness: `λ⋆_i f_i(x⋆) = 0`
4. Stationarity: `∇f_0(x⋆) + ∑ λ⋆_i ∇f_i(x⋆) + ∑ ν⋆_i ∇h_i(x⋆) = 0`

If the problem is convex (`f_i` convex, `h_i` affine), KKT is **sufficient**: any point satisfying the four conditions is primal and dual optimal with zero duality gap. With Slater, KKT is necessary and sufficient.

Equality-constrained convex quadratic `(1/2)x^T P x + q^T x` s.t. `Ax=b` (`P ≽ 0`) has KKT system

```
[ P  A^T ] [ x ]   [ -q ]
[ A   0  ] [ ν ] = [  b ]
```

Solve this KKT system; do not run unconstrained GD on a penalty and call it done.

**Tests for optimization code must check KKT residuals (or unconstrained stationarity `∇f ≈ 0`) at the reported solution, not merely that the objective decreased.** A decreasing objective that violates KKT is not a valid solution.

## Numerical stability

- **Never form `A^{-1}`.** Solve `Ax=b`. For PSD/PD Hessians use Cholesky (`LL^T`); failure of Cholesky is a useful diagnostic that H is not PD (nonconvexity, roundoff, or an iterate that left the domain).
- Generic dense solve is ~n³. Fine for n of a few hundred; exploit sparsity / structure beyond that (Boyd App. C).
- Ill-conditioned Hessian (`M/m` large): GD oscillates or stalls; Newton still works if the Newton system is solved stably. Rescale variables / precondition when `κ` is huge.
- Line search: precompute affine images (`Ax+b`, `AΔx`) once per direction; do not refactor from scratch at every trial `t`.
- Domain: log, log-det, `x^2/y`, barriers are `+∞` outside `dom f`. A NaN/Inf in f or ∇f is usually an iterate that left the domain, not a math library bug. Pull `t` back onto the domain first.
- Newton decrement `λ^2/2` is the right residual for Newton; `||∇f||` is the right residual for gradient methods under strong convexity. Do not mix them.

## Debugging a failing optimizer (three failure modes)

When the iterate does not converge or oscillates, check in this order:

1. **Is the objective actually convex on the domain being used?** Hessian PSD / `f''≥0`. If not, a convex method has no global guarantee; "almost convex" still fails.
2. **Is the step size too large?** For GD, `t > 1/L` violates the quadratic upper bound and typically diverges or oscillates. Bound L or backtrack.
3. **Conditioning?** `M/m` large ⇒ slow linear rate even with a correct step. Look at Hessian eigenvalues, feature scales, and sublevel-set eccentricity. Fix scaling or switch to Newton / a first-order method with preconditioning.

## Chapter map (when you need more than this file)

| Part | Ch | Topic |
|------|----|--------|
| I Theory | 2 | Convex sets |
| | 3 | Convex functions (FOC/SOC, conjugates, quasiconvex) |
| | 4 | Convex problems (LP, QP, GP, SOCP, SDP) |
| | 5 | Duality, Slater, KKT |
| II Applications | 6–8 | Approximation, statistical estimation, geometric problems |
| III Algorithms | 9 | Unconstrained: descent, GD, Newton, self-concordance |
| | 10 | Equality-constrained Newton |
| | 11 | Interior-point / barrier / primal-dual |
| Appendices | A–C | Analysis, two quadratics, numerical linear algebra |

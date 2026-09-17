# Ch 4 Divide-and-Conquer and recurrences

## Methods

- **Substitution (4.3):** guess the form, prove by induction, absorb lower-order terms. Watch the induction base and the exact inequality direction.
- **Recursion tree (4.4):** cost per level × number of levels. Merge-sort tree is the prototype.
- **Master method (4.5):** cookbook for T(n) = a T(n/b) + f(n).
- **Akra-Bazzi (4.7):** uneven subproblem sizes.

## Theorem 4.1 (Master theorem)

Watershed W = n^{log_b a}. Driving function f(n) is divide+combine.

1. f polynomially smaller than W (factor n^ε) → T = Θ(W). Cost grows toward the leaves.
2. f = Θ(W lg^k n) → T = Θ(W lg^{k+1} n). Levels roughly equal. Usual k=0: T = Θ(W lg n).
3. f polynomially larger than W *and* regularity a f(n/b) ≤ c f(n), c<1 → T = Θ(f). Root dominates.

Floors/ceilings on n/b do not change the Θ result. Polynomial separation is mandatory: T(n)=4T(n/2)+n^{1.99} is still case 1 (W=n², ε=0.01).

If the recurrence is not a master recurrence, do not force it — use 4.3/4.4.

## Coding implication

When a recursive implementation is slow, write the recurrence and classify it *before* attaching a profiler. A T(n)=2T(n−1)+Θ(1) blow-up will not be fixed by micro-optimizing the base case.

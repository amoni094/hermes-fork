# Ch 3 Characterizing Running Times

## Informal (3.1) and formal (3.2)

O, Ω, Θ are *sets of functions*. Writing f(n) = O(g(n)) means membership. Definitions require positive constants c, n₀ such that the inequality holds for all n ≥ n₀.

Example: 4n² + 100n + 500 = O(n²) (many (c,n₀) pairs work). n³ − 100n² is *not* O(n²): after dividing by n² you need n − 100 ≤ c for all large n — impossible.

**Theorem 3.1:** f = Θ(g) iff f = O(g) and f = Ω(g).

## Precision rules (3.2)

- Insertion sort *worst case* is Θ(n²); *best case* is Θ(n). You may say the running time is O(n²) (all cases). You may **not** say the running time is Θ(n²) without “worst-case.”
- Merge sort is Θ(n lg n) in all cases — no qualifier needed.
- Prefer the simplest tight bound: 3n² + 20n is Θ(n²), not O(n³) and not Θ(3n²+20n).
- “An O(n lg n) algorithm is faster than an O(n²) algorithm” is invalid: O is only an upper bound.

Asymptotic notation in equations stands for unnamed functions. Chaining 2n²+3n+1 = 2n²+Θ(n) = Θ(n²) is interpreted equation-by-equation (right-hand side is coarser).

O(1) needs context for which variable → ∞.

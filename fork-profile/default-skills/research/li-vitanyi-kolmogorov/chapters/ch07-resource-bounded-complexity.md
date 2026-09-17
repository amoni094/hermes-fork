# Chapter 7: Resource-Bounded Complexity

## Core Idea

Unrestricted C and K ignore time and space: a shortest program may run for Ackermann-many steps. Resource-bounded Kolmogorov complexity asks for the shortest program that produces x within a given time or space bound. This connects algorithmic information theory to computational complexity (P, NP, PSPACE), language compression, Levin’s universal search, time-limited universal distributions, and Bennett’s logical depth — the amount of “interesting organized structure” in an object.

## Key Concepts

- Time-bounded complexity C^t(x): min { l(p) : U(p) = x in at most t(l(x)) steps } (and analogously K^t, space-bounded C^s). Precise definitions vary by machine model; Li–Vitányi flag that prefix vs self-delimiting may diverge once time bounds are imposed (Example 7.1.1).
- Hierarchy theorems: slightly more time yields strictly more strings with short descriptions; depth definitions must not use raw runtime of x* alone.
- Language compression: given a language L, how well can membership strings be compressed with time-bounded decompressors. Hartmanis–Hempel-style results: space-bounded C characterizes complexity classes.
- Instance complexity: ic^t(x : L) is the length of the shortest program that correctly decides membership of x in L (and may be wrong or slow on other instances). Captures “this instance is easy even if the language is hard.”
- Levin’s Kt complexity: Kt(x) = min { l(p) + log t : U(p) = x in t steps }. Combines program size and log-time; equivalently Kt(x) = log age(x) where age is the first time a dovetailing universal search prints x.
- Universal search (Levin search): dovetail all programs p, allocating time 2^{−l(p)} fraction (or run p for t steps when l(p) + log t is the budget). Finds a witness in time O(t* 2^{l(p*)}) if p* is a shortest-fast program. Optimal up to a constant factor among inversion algorithms.
- Time-limited universal distributions m^t: mixture of time-t semimeasures; average-case complexity under m^t relates to worst-case (Levin’s idea that NP-average is as hard as NP-worst under the universal distribution).
- Logical depth (Bennett): a string is deep if it has a short program that requires a long time to run (organized complexity), as opposed to incompressible noise (shallow and complex) or trivial strings (shallow and simple). Formalized via algorithmic probability mass that appears only after d steps.

## Frameworks and Methods

- Resource-bounded invariance: only within a class of simulators with similar overhead. Polynomial-time simulation is enough for P vs NP-style statements; linear-time is not model-invariant.
- Compression of languages: if every x ∈ L ∩ {0,1}^n has C^{poly}(x) ≤ s(n), then L is compressible to s(n) bits with poly-time decompression — a uniform analogue of circuit size.
- Instance complexity vs language complexity: L is easy on instance x if a short, fast program decides x (possibly by hard-wiring x). Hard languages still have easy instances; random instances of hard languages have high instance complexity.
- Levin search as optimal inversion: to invert a polynomial-time function f (find x with f(x) = y), run universal search; time is O(2^{K^{t}(x|y)} t(x)).
- Logical depth via QU: QU(x) = sum_{U(p)=x} 2^{−l(p)}. Depth d within significance b means that a (1 − 2^{−b}) fraction of this mass comes from programs that need at least d steps. This avoids the instability of “runtime of the shortest program” (Attempt 1) and of “counting programs of length K+b equally” (Attempt 2).

## Key Results and Theorems

- Simulation overhead: a universal TM simulates t steps of T_n in t log t (or t) depending on model; resource-bounded invariance therefore carries extra log factors.
- Language compression theorems (§7.2): sets in DTIME(t) / DSPACE(s) have time/space-bounded descriptions of length n − Θ(log t) or similar; converse directions reconstruct the language from the compressor.
- Computational complexity connections (§7.3):
  - If SAT instances were highly time-bounded compressible, collapse phenomena follow.
  - Most strings are incompressible even with exponential time (counting still applies inside a time bound if the bound is total recursive and the enumerator cannot outrun it for all x).
  - Random (incompressible) oracles separate classes in the usual ways; resource-bounded C is the language of those oracles.
- Instance complexity (§7.4): ic(x : L) ≤ C(x) + O(1) always (hard-wire x and a bit); for random x, instance complexity of a hard L tracks the decision problem’s hardness. “If all instances have low instance complexity, the language is easy.”
- Kt properties: Kt(x) ≥ C(x), Kt(x) ≤ l(x) + 2 log l(x) + O(1) with linear time. Kt is not subadditive in a trivial way: there exist x, y of length n with Kt(x) > n^2, Kt(y|x) > n^2, yet Kt(xy) ≤ n + O(log n) (fast concatenation vs slow factors).
- Universal search optimality: for any algorithm A inverting f in time t_A(y), Levin search inverts in time O(t_A(y) 2^{K(A)}). The constant is exponential in the description of A, which is why Levin search is optimal-in-theory, unused-in-practice without extra structure.
- Time-bounded coding: −log m^t(x) ≈ K^t(x) with more slop than the unbounded coding theorem.
- Logical depth: random strings are shallow (the identity program is short-running relative to significance); computable regular strings like 0^n are shallow; the output of a long-running short program (e.g. 2^{2^n} in unary, or a busy-beaver value encoded carefully) is deep. Depth is stable under the QU-mass definition, not under raw runtime of x*.

## Algorithms and Techniques

1. Levin search (inversion of f):
   - For t = 1, 2, 4, …:
     for all p with l(p) + log t ≤ budget:
       run U(p) for t steps; if f(output) = y, return output.
   - Equivalent: allocate to each p a fraction 2^{−l(p)} of time.
2. Time-bounded compressor: dovetail programs but kill those exceeding t(n); output shortest survivor that prints x.
3. Instance-complexity upper bound: program “if input = x then return L(x) else loop/wrong.” Length C(x) + 1 + O(1), time O(n).
4. Depth diagnostic: approximate QU from below with a time cutoff d; if most mass appears only after huge d, x is deep.
5. Extractor-based almost-shortest programs (exercises, 2017 Bauwens): with randomness one can produce programs of length C(x) + polylog without using more than poly time, even though mapping (x, C(x)) to a shortest program requires noncomputable time in the worst case.

## Anti-patterns

- Using unbounded C to make computational-complexity claims: C can hide 2^{2^n} simulation. Always state the time bound.
- Defining depth as “runtime of x*”: hierarchy theorems make this unstable (Attempt 1). A few extra bits can crash the runtime.
- Treating Levin search as a practical SAT solver: the 2^{K(A)} factor includes the constant of your clever algorithm as a program, but the naive enumeration also runs, and the overhead is enormous.
- Assuming prefix = self-delimiting under time bounds: open in the book’s account; do not silently transfer time-bounded theorems between the two models.
- Claiming resource-bounded C is invariant up to O(1): simulation overheads are O(log t) or more; polynomial equivalence is the realistic invariance.
- Confusing deep with incompressible: incompressible strings are shallow (print literally). Depth is organized complexity, not randomness.

## Key Takeaways

1. Resource bounds reconnect Kolmogorov complexity to P, NP, and average-case complexity.
2. Kt and Levin search are the right “size + log time” compromise; they make universal search optimal up to a constant factor.
3. Logical depth measures buried computation, not entropy: noise is shallow, crystals are shallow, evolved/computed structure is deep.
4. Instance complexity explains why hard problems have easy instances.
5. Unbounded theory (Ch 2–5) is the limit of resource-bounded theory as t → ∞; many identities acquire extra log t slop on the way.

## Connects To

- Ch 2–3: unbounded C, K are the t = ∞ case; invariance is cleaner there.
- Ch 4: time-limited m^t is the resource-bounded universal prior.
- Ch 6: incompressibility lower bounds on TM time are the “external” use of C; this chapter makes C itself time-aware.
- Ch 8: reversible computation and thermodynamic cost relate to logical depth and erasure.

---
name: li-vitanyi-kolmogorov
description: "Knowledge base from 'An Introduction to Kolmogorov Complexity and Its Applications' by Li and Vitanyi (4th ed, 2019). Use when applying algorithmic information theory, Kolmogorov complexity, MDL principle, Solomonoff induction, or incompressibility arguments."
related_skills:
  - shannon-1948
  - mackay-itila
  - information-theory-for-agents
---

# Li–Vitányi Kolmogorov Complexity

Source: Ming Li and Paul Vitányi, *An Introduction to Kolmogorov Complexity and Its Applications*, 4th ed., Springer 2019. Notation in this skill is the book's: **C** = plain complexity, **K** = prefix complexity. Do not use authors who write K for plain C.

Supporting files: [glossary.md](glossary.md) · [patterns.md](patterns.md) · [cheatsheet.md](cheatsheet.md) · [chapters/](chapters/)


## Model Routing

Proof checking, Kolmogorov complexity reference lookup (no tool calls): deepseek-v4-pro non-think session. No coding tail expected for most queries.


## Core Frameworks

### 1. Complexity as shortest effective description

The information in an individual object x is the length of a shortest program that prints x on a fixed universal Turing machine U. Effectiveness (partial computability) is required: among all partial functions there is no additively optimal description method, but among partial computable functions there is. That is the invariance theorem.

- Plain: `C(x) = min { ℓ(p) : U(p) = x }`, `C(x|y)` with y on an auxiliary tape.
- Prefix: `K(x)` same on a prefix (self-delimiting) machine, domain prefix-free.
- Invariance: for any other machine φ, `C(x) ≤ C_φ(x) + c_φ` (c_φ independent of x). Same for K. All “reasonable” programming languages therefore agree up to O(1).
- Upper bounds: exhibit a program. Lower bounds: counting (at most 2^{n−c} short programs) or incompressibility contradiction.
- C and K are upper semicomputable and not computable (halting problem). Berry’s paradox becomes Gödel: a short sound theory cannot prove incompressibility of long random strings.

Use C for first-cut incompressibility. Use K whenever you concatenate descriptions, mix probabilities, or need a chain rule.

### 2. Why prefix complexity exists

Plain programs cannot be concatenated without a length header, so

`C(x,y) ≤ C(x)+C(y)+2 log min(C(x),C(y))+O(1)`

and the log is necessary. Prefix programs *are* a prefix code, Kraft applies (`∑ 2^{−K(x)} ≤ 1`), and

`K(x,y) ≤ K(x)+K(y)+O(1)`.

Exact Shannon analogue (symmetry of information):

`K(x,y) = K(x) + K(y | x, K(x)) + O(1)`

i.e. condition on a shortest program x*, not on x. Naive `K(y|x)` fails by `Ω(log K(x))` because of complexity-of-complexity. Mutual information `I(x;y) = K(x)+K(y)−K(x,y)` is then symmetric to O(1).

Relation: `K(x) = C(x)+Θ(log C(x))` typically. For “≥ n−O(log n)” statements they are interchangeable.

Chaitin’s Ω = `∑_{U(p)↓} 2^{−ℓ(p)}` is a concrete Martin-Löf random real whose first n bits decide all haltings of programs of length ≤ n.

### 3. Algorithmic probability and the coding theorem

Three a priori distributions coincide up to Θ(1):

- universal lower-semicomputable discrete semimeasure `m(x)` (mixture `∑_j 2^{−K(j)} P_j(x)`);
- Solomonoff–Levin `Q_U(x) = ∑_{U(p)=x} 2^{−ℓ(p)}`;
- algorithmic probability `2^{−K(x)}`.

**Coding theorem:** `−log m(x) = K(x) + O(1)`. Conditional form: `−log m(x|y) = K(x|y)+O(1)`.

This is Occam as a measure: simple P get weight `2^{−K(P)}`. The class of *computable* measures has no universal element; lower semicomputability is the maximal effective class that does. Continuous analogue M on `{0,1}^∞` is what sequential prediction uses. Never write the coding theorem with C: `∑ 2^{−C(x)}` diverges.

Expectation bridge to Shannon: for computable P, `H(P) ≤ ∑ P K ≤ H(P)+K(P)+O(1)`. Entropy is expected Kolmogorov complexity.

### 4. Induction: Solomonoff, MDL, structure function

- **Epicurus:** keep all hypotheses consistent with data.
- **Occam:** weight hypothesis H by `2^{−K(H)}`.
- **Bayes:** update.

**Solomonoff:** mixture `M = ∑_μ 2^{−K(μ)} μ`; predict `M(xb)/M(x)`. If the source is computable μ, summed squared prediction error is `O(K(μ))`. Incomputable; approximate from below.

**MDL:** `H* = argmin_H [L(H)+L(D|H)]`. Ideal: `K(H)+K(D|H)`. Two-part is mandatory — one-part `K(D)` overfits. Ideal MDL ≈ MAP with prior m on hypotheses for which D is typical.

**Structure function** `h_x(i)` = min log|S| over finite S ∋ x with `K(S)≤i`. The elbow `i + h_x(i) ≈ K(x)` is Kolmogorov’s sufficient statistic: a short model in which x is typical (randomness deficiency `log|S|−K(x|S) = O(1)`). Nonprobabilistic statistics on an individual sample.

### 5. Incompressibility method

On a par with pigeonhole and the probabilistic method, but yields *almost-all* (and usually average-case) in the language of one object:

1. Let x be incompressible in the class (exists by counting).
2. If property P failed, a short decoder would reconstruct x from the failure witness.
3. Contradiction.

Applications: TM time (crossing sequences), sorting average-case, random graphs, routing, LCS, CFL recognition, communication complexity, circuit size, constructive LLL. Art of the method = designing the decoder. Noneffective: you do not exhibit x.

### 6. Resource bounds, search, depth

Unbounded C/K hide non-elementary runtimes.

- `C^t`, `K^t`: shortest program running in time t.
- **Levin `Kt(x) = min{ℓ(p)+log t}`**. Universal search allocates time `2^{−ℓ(p)}` to p and inverts poly-time f in `O(2^{K(A)} t_A)` — optimal up to a constant, unused in the raw form.
- **Instance complexity:** hardness of *this* input for language L.
- **Logical depth (Bennett):** time at which most of the `Q_U`-mass for x appears. Incompressible noise is *shallow*; so is `0^n`. Deep = short program, long runtime (organized structure). Do not define depth as runtime of x* (unstable under +O(1) bits).

### 7. Distance, similarity, physics

- **Universal information distance** `E1(x,y) = max{K(x|y), K(y|x)}` minorizes every admissible distance (upper semicomputable, Kraft density) up to O(1). Triangle inequality up to a log.
- **NID** `e(x,y) = E1 / max{K(x),K(y)}` — universal similarity metric.
- **NCD** replaces K by a real compressor. Heuristic; quality = compressor normality.
- Reversible computation: only *erasure* must dissipate `kT ln 2` (Landauer). Bennett uncomputing cleans garbage. Maxwell’s demon pays when erasing the record; algorithmic entropy K(microstate) vs log|Γ|.
- Quantum K: several inequivalent definitions; no single canonical analogue.

### Practical rules of thumb

1. Additive O(1) is machine-dependent, string-independent. Terms in n or log n are not O(1).
2. Need concatenation, Kraft, probability, or chain rule → K not C.
3. Need a prior → m or M, never a “uniform over all TMs.”
4. Need a computable method → two-part MDL / NCD; state that it is not ideal K.
5. Need a proof about typical objects → incompressibility; condition on every parameter the decoder uses.
6. Need time → Kt / Levin search / depth; unbounded C is the t→∞ limit.
7. Similarity without features → NID theoretically, NCD experimentally.

## Chapter Index

| Ch | File | Contents |
|----|------|----------|
| 1 | [chapters/ch01-preliminaries.md](chapters/ch01-preliminaries.md) | Effective description, Berry/Gödel, primes, computability, Kraft, Shannon toolkit |
| 2 | [chapters/ch02-algorithmic-complexity.md](chapters/ch02-algorithmic-complexity.md) | C(x), invariance, incompressibility counting, failure of subadditivity |
| 3 | [chapters/ch03-algorithmic-prefix-complexity.md](chapters/ch03-algorithmic-prefix-complexity.md) | K(x), subadditivity, symmetry of information, Ω, complexity of complexity |
| 4 | [chapters/ch04-algorithmic-probability.md](chapters/ch04-algorithmic-probability.md) | m, Q_U, coding theorem, continuous M |
| 5 | [chapters/ch05-inductive-reasoning.md](chapters/ch05-inductive-reasoning.md) | Solomonoff, PAC/Occam, MDL, structure function |
| 6 | [chapters/ch06-incompressibility-method.md](chapters/ch06-incompressibility-method.md) | Proof technique; graphs, sorting, TM, circuits, LLL |
| 7 | [chapters/ch07-resource-bounded-complexity.md](chapters/ch07-resource-bounded-complexity.md) | C^t, Kt, Levin search, instance complexity, logical depth |
| 8 | [chapters/ch08-physics-information-computation.md](chapters/ch08-physics-information-computation.md) | Entropy vs K, reversible computing, E1/NID/NCD, thermodynamics, quantum K |

## Topic Index

| Topic | Ch |
|---|---|
| Additive constants / reference U | 2, 3, 3.9 |
| Algorithmic probability, m, M, Q_U | 4 |
| Average-case analysis | 4, 6, 7 |
| Berry paradox, Gödel | 1 |
| Chain rule / symmetry of information | 3, 8 |
| Circuit / communication complexity | 6 |
| Coding theorem | 4 |
| Conditional complexity C(x\|y), K(x\|y) | 2, 3 |
| Denoising, rate-distortion | 5, 8 |
| Halting problem, Ω | 1, 3 |
| Incompressibility method | 1, 2, 6 |
| Information distance, NID, NCD | 8 |
| Invariance theorem | 2, 3 |
| Kraft inequality, prefix codes | 1, 3 |
| Levin search, Kt | 7 |
| Logical depth | 7 |
| Martin-Löf randomness | 2, 3 |
| MDL, two-part codes | 5 |
| Occam, Epicurus, Bayes | 5 |
| PAC, simple distributions | 5 |
| Plain vs prefix (C vs K) | 2, 3 |
| Quantum Kolmogorov complexity | 8 |
| Random graphs, combinatorics | 6 |
| Reversible computation, Landauer | 8 |
| Solomonoff induction | 4, 5 |
| Structure function, sufficient statistic | 5 |
| Subadditivity failure for C | 2 |
| Thermodynamics, Szilard, entropy | 8 |
| Time-bounded complexity | 7 |
| Universal prior | 4, 5 |
| Universal TM | 1, 2 |

## When to load what

- Definitions, inequalities, decision rules: [cheatsheet.md](cheatsheet.md)
- Named terms: [glossary.md](glossary.md)
- How to prove / which method: [patterns.md](patterns.md)
- Pedagogical development and hypotheses of a chapter: the chapter file

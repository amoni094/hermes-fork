# Patterns and Proof Techniques — Li and Vitányi

When / How / Trade-offs. Use with chapter files for statements.

## Incompressibility method

- When: lower bounds, almost-all claims, average-case of deterministic algorithms, combinatorics, random graphs, communication/circuit lower bounds.
- How: (1) Pick x with C(x | parameters) ≥ log |class| − c, existence by counting. (2) Assume ¬P(x). (3) Build a decoder that reconstructs x from a short witness of ¬P plus parameters. (4) Contradiction. High-probability: compressible exceptions have measure < 2^{−c+O(1)}.
- Trade-offs: noneffective (no example exhibited). Decoder must not leak unpaid parameters. Concatenation of descriptions needs prefix codes or a 2 log penalty. Uniform/m-probability, not an arbitrary P concentrated on 0^n.
- See: Ch 6; previews in Ch 1 (Gödel, primes).

## Invariance / exhibit-a-program

- When: any upper bound on C or K.
- How: write any TM (or prefix TM) that maps a short p to x; invariance adds only c_φ. Identity TM gives C(x) ≤ ℓ(x)+O(1).
- Trade-offs: constants depend on the reference U and are usually left implicit. Resource-bounded version pays simulation overhead, not O(1).

## Counting lower bounds

- When: “most strings satisfy C(x) ≥ n−c.”
- How: ≤ 2^{n−c+1} programs of length < n−c.
- Trade-offs: gives density, not a named string. For K, count prefix programs; Kraft already implies sum 2^{−K} ≤ 1 so fewer short x.

## Coding theorem conversion

- When: switch between probabilities and description lengths.
- How: −log m(x) = K(x)+O(1); −log P(x) ≥ K(x)−K(P)+O(1) for lower-semicomputable P. Shannon–Fano: ℓ(E(x)) ≤ −log P(x)+2.
- Trade-offs: C cannot replace K (2^{−C} is not a semimeasure). Discrete m vs continuous M differ by length terms. O(1) becomes a Θ multiplicative factor on probabilities.

## Symmetry of information / chain rule

- When: split joint descriptions; information distance; “what does x know about y.”
- How: K(x,y) = K(x)+K(y|x*)+O(1) with x* a shortest program for x. Mutual information I(x;y)=K(x)+K(y)−K(x,y) is symmetric to O(1).
- Trade-offs: naive K(x,y)=K(x)+K(y|x) fails by Ω(log K(x)) (complexity of complexity). Plain C has an extra log and is not symmetric to O(1).

## Two-part codes / MDL

- When: model selection, hypothesis identification, denoising, clustering.
- How: minimize K(H)+K(D|H) (ideal) or L(H)+L(D|H) (practical). Equivalent to MAP with prior m when D is typical for H.
- Trade-offs: one-part K(D) overfits (H can be D). Choice of hypothesis class is part of the method. Ideal K is incomputable; NML/BIC/gzip are not guaranteed Solomonoff-optimal.

## Solomonoff mixture

- When: sequential prediction with unknown computable source.
- How: M = sum_μ 2^{−K(μ)} μ; predict M(xb)/M(x). Sum of squared prediction errors ≤ O(K(μ)).
- Trade-offs: incomputable. Use M not m for next-bit prediction. Finite-time approximations are one-sided (lower-semicomputable).

## Structure function / typicality

- When: individual-sample statistics without a sampling model; sufficient statistics; “is this noise.”
- How: h_x(i) = min {log |S| : x∈S, K(S)≤i}. Elbow i+h_x(i)≈K(x) is the algorithmic sufficient statistic. Deficiency log|S|−K(x|S) measures atypicality.
- Trade-offs: noncomputable. Interpreting h_x as a likelihood requires putting the uniform distribution on S.

## Kraft–Chaitin machine construction

- When: you have desired program lengths (or weights) and need a prefix machine realizing them.
- How: if sum 2^{−n_i} ≤ 1 and the n_i are r.e., there exist prefix-free p_i with ℓ(p_i)=n_i.
- Trade-offs: constructive but the programs may be slow. Time-bounded analogue is strictly harder.

## Levin search / Kt

- When: invert a poly-time function; “optimal search.”
- How: allocate time 2^{−ℓ(p)} to each program (or minimize ℓ(p)+log t). Time O(2^{K(A)} t_A).
- Trade-offs: theoretically optimal, practically swamped by the 2^{K(A)} factor and by running all bad p. Not a substitute for SAT heuristics.

## Logical depth vs randomness

- When: distinguish noise, trivial regularity, and “organized” objects.
- How: use Q_U-mass arrival time, not runtime of x*. Random strings and 0^n are shallow; outputs of long short programs are deep.
- Trade-offs: unstable if defined from x* runtime alone (hierarchy). Significance parameter b is part of the definition.

## Universal distance / NID / NCD

- When: similarity without features; clustering heterogeneous objects.
- How: E1 = max{K(x|y),K(y|x)} minorizes admissible distances. NID normalizes by max{K(x),K(y)}. NCD replaces K by a compressor C: (C(xy)−min{C(x),C(y)})/max{C(x),C(y)}.
- Trade-offs: E1 incomputable. NCD quality = compressor normality (C(xx)≈C(x), C(xy)≈C(yx)). gzip fails on large or already-compressed data. Use E1 not the sum E4.

## Reversible simulation

- When: energy, thermodynamics, information distance via reversible programs.
- How: save history, copy output, uncompute. Landauer: only erasure costs kT ln 2.
- Trade-offs: time/space pebble-game tradeoffs (t^{1+ε} time, s log t space typical). Reversible K equals max of the two conditionals (E1) up to logs.

## Expectation identities (Shannon ↔ Kolmogorov)

- When: translating ensemble theorems to individual-object theorems.
- How: E_P[K(X)] = H(P)+K(P)+O(1) for computable P; typical x have K(x) ≈ −log P(x).
- Trade-offs: needs P computable (or lower semicomputable). Atypical compressible microstates are the thermodynamic exceptions (Szilard).

## Anti-pattern checklist

- C-subadditivity without 2 log.
- Chain rule without x*.
- Coding theorem with C.
- Computable universal measure.
- Proving a named long string incompressible.
- NCD = NID.
- Depth = runtime of shortest program.
- Shannon H as information in one message.
- Levin search as a practical algorithm without domain structure.
- Resource-bounded invariance up to O(1).

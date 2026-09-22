# Ch 7 — Algebraic Techniques

Fingerprinting: map a large object to a short random image so that distinct objects collide with tiny probability. Comparison of fingerprints is cheap.

## Freivalds' technique (Ch 7.1)

Verify `A B = C` for `n×n` matrices over a field. Draw random `r ∈ {0,1}^n` (or `F^n`). Compute `A(Br)` and `Cr`. If `AB ≠ C`, `P[(AB−C)r = 0] ≤ 1/2`. Repeat to amplify. Time `O(n²)` vs `O(n^ω)` multiply.

## Polynomial identities (Ch 7.2)

**Schwartz–Zippel.** Let `p ∈ F[x_1,…,x_n]` have total degree `d`, `p ≢ 0`. If each `x_i` is drawn independently from finite `S ⊆ F`,

`P[p(x)=0] ≤ d / |S|`.

Verify an algebraic identity by evaluating at a random point. One-sided Monte Carlo.

## Perfect matchings (Ch 7.3)

Tutte / Edmonds matrix: determinant is a polynomial that is identically zero iff no perfect matching. Schwartz–Zippel ⇒ randomised matching test in `RNC` (parallel: Ch 12.4).

**Theorem 7.3** (bipartite case): the Edmonds matrix of a bipartite graph is nonsingular (as a polynomial) iff a perfect matching exists.

## String equality (Ch 7.4)

Alice holds `x ∈ {0,1}^n`, Bob `y`. Fingerprint `x(r) = ∑ x_i r^i mod p` for random prime `p` and random `r`, or interpret as a polynomial over a field. `P[x(r)=y(r) | x≠y] ≤ n/|F|`. Communication `O(log n + log |F|)`.

## Pattern matching (Ch 7.6)

Karp–Rabin: rolling fingerprint of the pattern and of each text window. Expected time linear; false matches have probability `O((n−m+1) m / p)` and can be verified.

## Interactive proofs and PCP (Ch 7.7–7.8)

IP: randomised verifier, unbounded prover. `IP = PSPACE` (later Shamir; book covers the definition and quadratic-residuosity style protocols).

PCP: NP has probabilistically checkable proofs — verifier reads `O(log n)` random bits and `O(1)` proof bits. Efficient proof verification is the complexity-theoretic payoff of fingerprinting + polynomial identities.

## Comparison of fingerprinting techniques (Ch 7.5)

| Method | Collision source | Typical bound |
|---|---|---|
| Modular / polynomial | Schwartz–Zippel | `deg / |F|` |
| Freivalds vector | kernel of a nonzero matrix | `≤ 1/2` over `{0,1}` |
| Prime modulus | number of unlucky primes | `O(n / (p / ln p))` |

## Hermes

- Compare two large artefacts (session dumps, skill files, embeddings stored as strings) via fingerprints, not bytewise, when a small false-match probability is acceptable.
- Verify a claimed matrix/identity cheaply with Freivalds before an expensive multiply.

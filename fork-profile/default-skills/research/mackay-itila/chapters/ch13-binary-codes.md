# Chapter 13: Binary Codes

## Core Idea
Classical coding theory maximizes Hamming distance (sphere packing). Shannon’s goal is typical-set packing under a noise *distribution*. The two coincide only loosely: perfect codes are beautiful and mostly useless, random linear codes have good typical distance, and concatenating Hamming codes does not reach capacity. Do not win sphere-packing prizes and think you have solved telecommunication.

## Frameworks Introduced
- **Hamming metric**: d(x,x') = number of differing coordinates. BSC-ML decoder = nearest codeword in Hamming distance.
- **Minimum distance d_min**: corrects t=⌊(d_min−1)/2⌋ errors *in the worst case*. Shannon cares about typical t≈Nf errors, not worst-case t.
- **Sphere-packing (Hamming) bound**: 2^K sum_{i=0}^t C(N,i) ≤ 2^N. Equality ⇔ perfect code.
- **Gilbert–Varshamov / random linear codes**: a random H gives d_min growing linearly with N with high probability — “very good” codes exist (Ch 14).
- **Weight enumerator A(w)**: number of codewords of weight w. Union bound on error uses A(w), not just d_min.
- **Dual code**: C⊥ = {z : z·x=0 ∀x∈C}. H is a generator for C⊥.

## Key Concepts
- **Perfect codes**: Hamming codes, Golay (23,12,7), trivial repetition of odd length. Almost nothing else (Tietäväinen–van Lint).
- **Berlekamp’s bats**: a pictorial argument that high-distance sphere packings still leave typical noise uncorrected or waste space — distance is the wrong objective.
- **Concatenation of Hamming codes**: iterated Hamming constructions improve d but rate collapses or decoding complexity/error floors disappoint relative to C.
- **Union bound**: P(error) ≤ sum_{w=d}^{N} A(w) P(noise closer to a weight-w word).
- **ML vs bounded-distance decoding**: bounded-distance (correct only t < d/2) refuses typical error patterns of weight Nf > t even when they are uniquely nearest.

## Key Equations
- d_min = min_{x≠x' in C} d(x,x')
- Hamming bound: 2^{N−K} ≥ sum_{i=0}^t C(N,i)
- Singleton bound: d ≤ N−K+1 (MDS)
- Plotkin / Elias bounds (sphere packing refinements)
- Random linear: E[A(w)] = C(N,w) 2^{−M}
- Union bound P_e ≤ sum_w A(w) p_w

## Algorithms and Techniques
**Estimate d_min of a random linear code**
1. For each w, expected number of weight-w codewords is C(N,w)/2^M.
2. Smallest w with expectation ≪ 1 is the typical d_min.
3. For rate R=K/N, M=(1−R)N, this w/N satisfies H2(w/N)=1−R (GV distance).

**Do not decode by minimum distance alone**
1. Prefer full ML / APP (Ch 25–26, 47).
2. If you must use bounded distance, know you are leaving Shannon performance on the table whenever Nf > t.

## Mental Models
- Worst-case t-error-correction is a combinatorial sport; typical-noise correction is communication.
- Perfect codes fill space with spheres — but BSC noise of weight Nf sits in a *thin shell*, not a small ball around 0. Spheres of radius t≪Nf do not cover the shell; spheres of radius Nf overlap massively.
- Duality: good high-rate codes have duals that are good low-rate codes; weight enumerators are related by MacWilliams identities.

## Worked Example
Hamming (7,4): t=1, 2^4 (1+7)=2^7, perfect. For N=7, f=0.1, typical errors≈0.7, so t=1 is matched — one reason Hamming looks decent at small N. For Hamming (2^m−1, 2^m−1−m), t=1 fixed, Nf→∞: it corrects a vanishing fraction of typical errors. Rate → 1, but it is not a capacity-achieving family.

Random linear N=100, R=1/2, M=50. GV: H2(δ)=1/2 ⇒ δ≈0.11. Typical d_min≈11. BSC(f=0.05) has typical 5 flips < 11/2, so ML would usually work; bounded-distance with t=5 is tight. At f=0.1 typical 10 flips, d_min/2=5.5, bounded-distance fails even if ML (union bound with whole A(w)) might still succeed some of the time.

## Anti-patterns
- **Designing codes to maximize d_min as the primary goal**.
- **Declaring a code “capacity-relevant” because it is perfect**.
- **Bounded-distance decoding of long Hamming/BCH codes on a BSC with Nf > t**.
- **Ignoring the weight enumerator**: two codes with the same d_min can have wildly different P_e because of A(d_min).

## Key Takeaways
1. Hamming distance is the right ML metric *for the BSC*, but maximizing d_min is not Shannon’s problem.
2. Perfect codes essentially do not exist at large N.
3. Random linear codes have good typical distance (GV).
4. Always look at A(w) and typical error weight Nf.
5. Duality and concatenation are useful tools, not automatic capacity achievers.

## Connects To
- **Ch 10**: Shannon vs sphere packing.
- **Ch 14**: existence of very good linear codes, made short.
- **Ch 25–26**: efficient ML/APP on structured graphs, not brute-force nearest neighbour.
- **Ch 47**: sparse random H — random-linear goodness *plus* decodability.

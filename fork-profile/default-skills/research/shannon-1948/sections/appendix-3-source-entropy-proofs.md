# Appendix 3: Proofs of Theorems 3–6

## Core Idea
Typical long sequences from an ergodic Markoff source have probability ≈ 2^{−HN}; block entropy GN and conditional entropy FN both decrease to H.

## Key Concepts
- **p(B)**: probability of an N-block B.
- **GN = −(1/N) ∑ p(B) log p(B)**: entropy per symbol of N-grams.
- **FN**: conditional entropy of the next symbol given N−1 predecessors — entropy of the N-th order approximation.

## Key Results
**Theorem 3 (AEP).** For any ε,δ > 0 and N large, sequences of length N split into (i) a set of total probability < ε and (ii) the rest, all satisfying |(log p^{−1})/N − H| < δ.

Sketch: for an ergodic source the frequency of each state and each transition converges (probability 1) to the ensemble values. Then (1/N) log p^{−1} → ∑ Pi p_i(j) (−log p_i(j)) = H.

**Theorem 4.** n(q) = number of most probable N-sequences needed to accumulate probability q. Then lim (log n(q))/N = H for q ≠ 0,1.

Sketch: typical sequences each have p ≈ 2^{−HN}; it takes about q · 2^{HN} of them to make probability q, so log n(q) ∼ HN.

**Theorem 5.** GN is monotonic decreasing and lim GN = H.

**Theorem 6.** FN is monotonic decreasing; FN = N GN − (N−1) G_{N−1}; GN = (1/N) ∑_{n=1}^N Fn; FN ≤ GN; lim FN = H.

These identify H both as an internal-state average (Sec 7) and as an observable of block statistics.

## Key Equations
- (1/N) log p(B)^{−1} → H  (probability 1 on typical B)
- lim (log n(q))/N = H
- FN = N GN − (N−1) G_{N−1}
- GN = (1/N) ∑ Fn → H,  FN → H

## Significance
The AEP is the discrete geometry behind Theorems 9 and 11: “treat the long sequences as though there were just 2^{HN} of them, each with probability 2^{−HN}.”

## Connects To
- Sec 7: statements.
- Sec 9, 13: typical-set coding.
- Sec 21: continuous volume form lim (log V_n(q))/n = H′.

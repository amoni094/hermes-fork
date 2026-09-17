# Section 7: The Entropy of an Information Source

## Core Idea
For a finite-state source, entropy per symbol is the average of the per-state choice entropies. Long typical sequences behave as if there were just 2^{HN} of them, each of probability 2^{−HN}. Relative entropy and redundancy quantify compressibility; English is estimated at about 50% redundant.

## Key Concepts
- **Entropy of the source per symbol**: for each state i, Hi = −∑_j p_i(j) log p_i(j); then H = ∑_i Pi Hi = −∑_{i,j} Pi p_i(j) log p_i(j).
- **Entropy per second**: H' = ∑_i fi Hi = m H, where fi is the average frequency of state i (per second) and m is the average number of symbols per second. Base 2 ⇒ bits per symbol or per second.
- **Independent symbols**: H = −∑ pi log pi. A long message of N symbols has probability p ≈ ∏ pi^{pi N}, so log p ≈ −N H, or H ≈ (1/N) log(1/p) for a typical long sequence.
- **Relative entropy**: entropy of the source divided by the maximum it could have on the same symbols. “This is the maximum compression possible when we encode into the same alphabet.”
- **Redundancy**: 1 − relative entropy. English, “not considering statistical structure over greater distances than about eight letters, is roughly 50%.” “When we write English half of what we write is determined by the structure of the language and half is chosen freely.”
- **GN vs FN**: GN is entropy per symbol of N-blocks; FN is conditional entropy of the next symbol given N−1 predecessors (entropy of the N-th order approximation). FN is the better approximation; if no influence beyond N symbols, FN = H.

## Key Results
**Theorem 3** (AEP). Given any ε>0 and δ>0, there is N0 such that sequences of length N ≥ N0 fall into two classes: (1) a set of total probability < ε; (2) the remainder, all satisfying | (log p^{−1})/N − H | < δ. “We are almost certain to have (log p^{−1})/N very close to H when N is large.”

**Theorem 4.** Arrange sequences of length N by decreasing probability; n(q) = number needed, starting from the most probable, to accumulate probability q. Then lim_{N→∞} log n(q) / N = H when q ≠ 0,1. Interpretation: bits per symbol to specify a sequence among the most probable ones totaling probability q is H, independent of q (not 0 or 1). “For most purposes [one may] treat the long sequences as though there were just 2^{HN} of them, each with a probability 2^{−HN}.”

**Theorem 5.** GN = −(1/N) ∑_i p(Bi) log p(Bi) (sum over N-symbol sequences) is monotonic decreasing and lim GN = H.

**Theorem 6.** FN = −∑ p(Bi, Sj) log p_{Bi}(Sj) is monotonic decreasing; FN = N GN − (N−1) G_{N−1}; GN = (1/N) ∑_{n=1}^N Fn; FN ≤ GN; lim FN = H.

Proofs: Appendix 3.

**English redundancy.** Three methods all near 50%: (i) entropy of the approximations; (ii) delete a fraction of letters and see if a reader can restore them — if 50% can be restored, redundancy > 50%; (iii) known cryptographic results. Extremes: Basic English (850-word vocabulary, very high redundancy, expands under translation) vs Joyce’s *Finnegans Wake* (enlarged vocabulary, alleged compression of semantic content). Crossword puzzles: redundancy 0 ⇒ any array is a crossword; too high ⇒ too many constraints. If constraints are “chaotic and random,” large 2-D crosswords are just possible at 50% redundancy; 33% would allow 3-D crosswords.

## Key Equations
- H = −∑_{i,j} Pi p_i(j) log p_i(j)
- H' = m H
- typical: p ≈ 2^{−HN}, about 2^{HN} typical sequences
- GN → H, FN → H, FN ≤ GN
- relative entropy = H / log |alphabet|
- redundancy = 1 − relative entropy

## Significance
Theorems 3–4 are the asymptotic equipartition property; they turn entropy into a counting rate for typical sequences and thereby into a coding rate. Theorems 5–6 show H is an observable of the letter statistics, not an internal-state artifact. The 50% English figure and the crossword argument are Shannon’s famous empirical claims.

## Connects To
- Sec 9: Theorem 9 encodes the typical set of size 2^{(H+η)N} into channel sequences of duration ~ HN/C.
- Sec 13: the same typical-set geometry in three copies (inputs, outputs, conditional fans).
- Appendix 3: mixed-source step-function version of Theorem 4.

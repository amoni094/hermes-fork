# Section 2: The Discrete Source of Information

## Core Idea
Channel capacity is the growth rate of possible signals. The source question is how much information (bits per second) a given source produces, and how statistical knowledge of the source reduces the required channel capacity by proper encoding.

## Key Concepts
- **Discrete source as stochastic process**: the source generates the message symbol by symbol; successive symbols are chosen according to probabilities that may depend on preceding choices. “A physical system, or a mathematical model of a system which produces such a sequence of symbols governed by a set of probabilities, is known as a stochastic process.” Conversely any stochastic process producing a discrete sequence from a finite set is a discrete source.
- **Why statistics save capacity**: English is not completely random — E is more frequent than Q, TH more than XP. Telegraphy already uses a short symbol (dot) for E and long sequences for Q, X, Z. Commercial codes encode common words as 4–5 letter groups; standardized greeting telegrams encode sentences as short number sequences.
- **Source types**: (1) natural written languages; (2) quantized continuous sources (PCM speech, quantized television); (3) abstractly defined stochastic processes.

## Key Results
**Independence vs dependence.**
- (A) Five letters A–E, each p = 0.2, independent.
- (B) Same letters, probabilities 0.4, 0.1, 0.2, 0.2, 0.1, independent.
- (C) First-order dependence: transition probabilities p_i(j) = Prob(letter i followed by j), equivalently digram probabilities p(i,j). Relations:

p(i) = ∑_j p(i,j) = ∑_j p(j,i) = ∑_j p(j) p_j(i)

p(i,j) = p(i) p_i(j)

∑_j p_i(j) = ∑_i p(i) = ∑_{i,j} p(i,j) = 1

Trigram structure needs p(i,j,k) or p_{ij}(k). The general n-gram case needs p(i1…in) or p_{i1…i_{n−1}}(in).

- (D) Word-level sources: finite vocabulary with word probabilities, optional word-to-word transitions. Finite-length words reduce to an n-gram letter process, but the word description may be simpler.

**Approximations to a natural language.**
- Zero-order: letters independent and equiprobable.
- First-order: letters independent with natural frequencies (English E ≈ 0.12, W ≈ 0.02).
- Second-order: digram structure via p_i(j).
- Third-order: trigram structure.

These artificial languages are for constructing examples and for approximating natural language by a series of simple processes.

## Key Equations
- p(i,j) = p(i) p_i(j)
- p(i) = ∑_j p(i) p_i(j)  (consistency / stationarity of letter frequencies)

## Significance
The source is not a deterministic message but a probability law on sequences. All later entropy definitions (H per symbol, H' per second, GN, FN) are functionals of this law. Encoding savings exist only because the source is not the maximum-entropy process on its alphabet.

## Connects To
- Sec 3: concrete English approximations that make the hierarchy visible.
- Sec 4–5: Markoff graph and ergodicity so that sequence averages equal ensemble averages.
- Sec 6–7: entropy of the process.
- Sec 9–10: how much channel C is necessary and sufficient for a source of entropy H.

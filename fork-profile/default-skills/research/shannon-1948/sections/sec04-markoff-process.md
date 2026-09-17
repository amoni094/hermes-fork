# Section 4: Graphical Representation of a Markoff Process

## Core Idea
The stochastic processes of Sec 2 are discrete Markoff processes. Shannon represents a source as a finite-state graph: states hold the “residue of influence” from preceding letters; each transition emits a letter.

## Key Concepts
- **Discrete Markoff process**: finite states S1,…,Sn and transition probabilities p_i(j) = probability of going from Si to Sj. Reference: Fréchet on chain events with finitely many states.
- **Information source from a Markoff process**: “assume that a letter is produced for each transition from one state to another. The states will correspond to the ‘residue of influence’ from preceding letters.”
- **Graph**: junction points = states; each line carries a probability and the letter produced. Fig. 3 = independent letters (example B: one state). Fig. 4 = first-order letter dependence (example C: as many states as letters). A trigram source has at most n² states (possible preceding pairs). Fig. 5 = word-structure source (example D); S is the space symbol.

## Key Results
- Independent letters → one state (memoryless).
- Dependence on the last letter → n states.
- Dependence on the last k letters → at most n^k states.
- Word sources are still finite-state if the vocabulary is finite.

The same linear-graph language already used for channel constraints (Sec 1, Fig. 2) now describes sources. The duality is deliberate: a constrained channel is a set of allowed paths; a source is a probability assignment on those paths.

## Key Equations
- p_i(j): transition probability Si → Sj
- Letter emitted as a function of the transition (not merely of the destination state)

## Significance
Finite-state Markoff sources are the setting for entropy per symbol H = ∑ Pi Hi, for ergodicity criteria (Sec 5), and for the max-entropy assignment that saturates channel capacity (Theorem 8). Modern HMM/language-model graphs are this picture.

## Connects To
- Sec 1: channel constraint graphs are the same objects without probabilities (or with max-entropy probabilities).
- Sec 5: graph connectivity and circuit-length gcd determine ergodicity vs mixed vs periodic sources.
- Sec 7: H = −∑_{i,j} Pi p_i(j) log p_i(j)
- Theorem 8 / Appendix 4: the unique (up to the graph) probability assignment achieving C.

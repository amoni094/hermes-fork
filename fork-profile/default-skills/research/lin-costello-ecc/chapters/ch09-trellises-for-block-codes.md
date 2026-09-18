# Chapter 9: Trellises for Linear Block Codes

## Core Idea
Every linear block code has a trellis: a time-indexed graph of encoder states whose paths are exactly the codewords. Once you have a compact trellis, Viterbi/MAP (Ch 12, 14) become block-code decoders. Complexity is governed by state dimension, sectionalization, and parallel structure — not by 2^k brute force.

## Key Concepts
- **Finite-state machine model**: as bits (or sections) of a codeword are revealed, the partial syndrome / information-span is the state. A path from the unique start state to the unique end state is a codeword.
- **Bit-level trellis**: n time indices, one bit per branch. Binary linear (n,k) code: at depth i the state space is a linear space whose dimension s_i satisfies s_i ≤ min(i, n−i, k, n−k).
- **State labeling**: two conventions — span of past information bits (generator view) or remaining parity-check constraints (H view). Forney’s compact trellis uses the *minimal* state space at each depth.
- **Minimal trellis**: unique (up to labeling) bit-level trellis with the fewest states at every depth; obtained from a trellis-oriented (min-span) generator matrix.
- **State complexity profile**: {s_0,…,s_n}, s_0=s_n=0. Peak state complexity S = max 2^{s_i} dominates Viterbi cost.
- **Branch complexity**: number of edges; often the better predictor of ACS work.
- **Sectionalization**: group ℓ consecutive bits into one trellis section. Fewer depths, larger branch alphabets; can reduce time and enable parallel ACS.
- **Parallel decomposition**: trellis is a union of isomorphic subtrellises (cosets). Decode subtrellises in parallel, then pick the best.
- **Low-weight subtrellis**: subgraph of codewords of weight ≤ w (or around a center). Used for list / iterative refinement (Ch 14).
- **Cartesian product**: trellis of a product/concatenation relates to products of component trellises.

## Frameworks and Methods
- **Build a bit-level trellis from H**:
  1. Process columns of H from left to right.
  2. State at depth i = partial syndrome H_{1:i} v_{1:i}^T (an element of GF(2)^{n−k}).
  3. A bit-0 / bit-1 branch from state s goes to s or s+column_i.
  4. Only states that can reach the all-zero syndrome at time n are kept (backward constraint).
- **Trellis-oriented G**: permute coordinates and row-reduce so each row has minimal span (first-1 and last-1 as tight as possible). Active rows at depth i = state dimension s_i.
- **When trellis decoding beats algebraic**: short-to-medium n (say n ≤ 128) with moderate k, or when soft decisions are available and no algebraic decoder exists (RM of mixed order, extended Hamming, Golay).
- **BCJR on a block trellis**: APP bit posteriors for turbo/LDPC-style concatenation (Ch 14 MAP).
- **Wolf bound**: s_i ≤ n−k, so at most 2^{n−k} states — dual of “at most 2^k paths.” Pick the smaller: encode-enumerate if k small, syndrome-trellis if n−k small.

## Key Results
- Forney–Muder: every linear code has a unique minimal trellis (for a fixed bit order). Coordinate permutation can dramatically change S — *bit order is a design parameter*.
- State-complexity bounds: s_i ≤ min(i, n−i, k, n−k). Hamming codes, RM, Golay have known profiles.
- Squaring construction (Ch 4 RM) ⇔ sectional trellis with a 2-section or 4-section decomposition (Forney).
- Viterbi on the minimal trellis is MLD. Complexity ~ n · 2^{s_max} ACS operations.
- (24,12) Golay: a 2^8-state sectional trellis exists; practical soft MLD.
- Sectionalization theorem: there is an optimal section boundary set minimizing a given complexity measure; it is found by dynamic programming on the bit-level profile.

## Algorithms and Techniques
**Minimal-trellis construction (generator span)**:
1. Compute for each basis vector the start (first 1) and end (last 1) positions.
2. At time i (just after bit i), active generators are those with start ≤ i < end.
3. State bits = the values already chosen for those active generators.
4. A branch is labeled with the code bit produced by the sum of active generators plus any generator that *starts* at i.

**Viterbi on a block trellis** (preview of Ch 14):
Same ACS as convolutional Viterbi, but the trellis is time-varying (state count changes with depth) and terminates at a single state.

**Parallel Golay-style decode**:
Decompose into 8 or 16 parallel subtrellises of 32–64 states; 8 small Viterbis + a final compare is faster than one 256-state Viterbi in hardware.

## Anti-patterns
- **Using a random coordinate order**: s_max can be k or n−k; a min-span order may cut states by orders of magnitude.
- **Bit-level Viterbi when a 4-bit sectionalization is cheaper**: more sections ≠ faster; branch metric computation can dominate.
- **Assuming convolutional-style regular trellis**: block trellises are time-varying; ACS units must handle varying fan-in.
- **Ignoring 2^{n−k} Wolf bound**: for high-rate codes, syndrome trellises are small; for low-rate, use G-enumeration instead.
- **Building the full trellis for an RS(255,k) code**: state spaces are huge; algebraic decoding remains the right tool.

## Key Takeaways
1. Linear block codes have trellises; MLD = Viterbi on the minimal trellis.
2. Complexity = peak states × length; minimize via coordinate permutation and sectionalization.
3. Duality: 2^k vs 2^{n−k} — pick the smaller view.
4. RM/Golay/Hamming are the codes whose trellises actually get used.
5. Low-weight subtrellises and parallel decomposition feed the soft algorithms of Ch 14.

## Connects To
- **Ch 3–4**: G, H, RM squaring, Golay — inputs to trellis construction.
- **Ch 12**: Viterbi/BCJR originally for convolutional trellises; same ACS here.
- **Ch 14**: trellis-based soft block decoding (Viterbi, MAP, max-log-MAP, low-weight iterative).
- **Ch 15**: decomposition and multistage decoding exploit sectional/product trellises.

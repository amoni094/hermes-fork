# Chapter 14: Trellis-Based Soft-Decision Decoding Algorithms for Linear Block Codes

## Core Idea
Apply the convolutional soft toolbox (Viterbi, recursive ML, MAP, max-log-MAP) to the *block-code trellises* of Ch 9. Sectionalization, parallel decomposition, and low-weight subtrellises cut complexity below 2^{min(k,n−k)} while remaining ML or near-ML — the “exact” alternative to Chase/OSD list decoding (Ch 10).

## Key Concepts
- **Block Viterbi**: ACS on the time-varying minimal (or sectional) trellis; unique start and end states. Output is the ML codeword.
- **Recursive MLD**: divide-and-conquer on the trellis (or on the squaring construction): ML on left and right halves, then combine on the shared state. Related to fast Hadamard / RM recursive decoding.
- **Low-weight subtrellis iterative decode**: restrict search to codewords of weight ≤ w around the current center; iterate (suboptimum, good at high SNR).
- **MAP / BCJR on a block trellis**: bit APPs for every code bit. Needed when the block code is a constituent of a concatenated / turbo-product system.
- **Sectionalized MAP**: one BCJR step per section of ℓ bits; branch labels are ℓ-bit vectors. Fewer time steps, 2^ℓ branch alphabet.
- **Max-log-MAP**: replace log-sum-exp by max; equivalent to forward+backward Viterbi; outputs approximate LLRs with a well-known overconfidence that is often scaled by a factor < 1.
- **Soft-output Viterbi on block trellises**: SOVA variant; cheaper APPs than BCJR.

## Frameworks and Methods
- **Choose the graph**:
  - Bit-level minimal trellis if s_max is already small (extended Hamming, Golay, short RM).
  - Sectionalize at Forney’s optimal boundaries (RM of length 32/64).
  - Parallel coset subtrellises for hardware (8×32-state rather than 256-state).
- **ML path (Viterbi) vs bit APP (MAP)**: sequence-metric applications (one-shot decode) use Viterbi; iterative concatenation needs MAP/max-log-MAP.
- **Recursive ML for RM / squaring**:
  RM(r,m) = {(u, u+v)} with u ∈ RM(r,m−1), v ∈ RM(r−1,m−1). Decode v from the difference of the two halves, then u from a combination — the Reed algorithm in trellis language, or Viterbi on a 2-section trellis.
- **Suboptimum low-weight iteration** (Ch 14.3):
  1. Hard-decide or chase a center codeword c0.
  2. Run Viterbi on the subtrellis of low-weight offsets.
  3. If a better codeword is found, recenter and repeat.

## Key Results
- Viterbi on the minimal trellis = true MLD (same proof as Theorem 12.1; trellis may be time-varying).
- MAP on the same trellis = true bit-APP; complexity ~ twice Viterbi (forward+backward) times extra bookkeeping.
- Max-log-MAP is typically 0.2–0.5 dB from MAP on AWGN for these short codes, cheaper and stabler.
- (8,4) RM / extended Hamming: tiny trellis, Viterbi is trivial; used as a running example in the problems.
- Sectional MAP can be faster than bit-level MAP even with larger branches because ACS count drops.
- Low-weight subtrellis methods approach MLD at high SNR with much smaller graphs; they miss ML at low SNR when the error is not low-weight.

## Algorithms and Techniques
**Block Viterbi**:
Identical ACS to Ch 12, with:
- time-varying state sets S_t from Ch 9,
- possibly 2^ℓ-ary branches if sectionalized,
- termination forced to the unique zero state at t=n.

**MAP on a sectional trellis**:
γ on a section is the product (sum of logs) of ℓ bit-channel likelihoods for that section’s label. α, β as in BCJR. Bit APP for a bit inside a section is obtained by marginalizing over the 2^{ℓ−1} labels that have that bit = 0 vs 1.

**Max-log-MAP LLR**:
L(u_i) ≈ max_{paths u_i=1} M(path) − max_{paths u_i=0} M(path).
Each max is a Viterbi (or a traceback-on-α/β). Optional scale 0.7–0.9 before feeding a turbo loop.

**Recursive ML (two-section)**:
For each interface state s:
- ML cost of the left half ending in s,
- ML cost of the right half starting in s,
- add; pick the best s. Recurse inside halves if they themselves square-decompose.

## Anti-patterns
- **BCJR without sectionalization on n=256**: too many time steps and irregular ACS; this is why long BCH still uses Chase/OSD or is abandoned for LDPC.
- **Using MAP when only the codeword is needed**: Viterbi is half the work and is ML for the word.
- **Forgetting time-varying topology in hardware**: a convolutional ACS array does not map 1:1 onto a Golay trellis.
- **Low-weight iteration as a low-SNR decoder**: the true ML word may have high analog weight; list/OSD is safer near the threshold.
- **Unscaled max-log LLRs into an iterative decoder**: overconfident extrinsic values stall iteration.

## Key Takeaways
1. Block-code MLD = Viterbi on Ch 9’s trellis; block-code APP = BCJR on the same graph.
2. Sectionalize and parallelize — state count is not the only cost.
3. RM/Golay/Hamming are in the sweet spot; long primitive BCH are not.
4. Max-log-MAP is the practical SISO; full MAP when 0.2 dB matters.
5. Low-weight subtrellises are a high-SNR complexity cut, not a replacement for Chase at threshold.

## Connects To
- **Ch 9**: trellis construction, sectionalization, low-weight subgraphs.
- **Ch 10**: competing approximate-ML family (lists on algebraic decoders).
- **Ch 12**: Viterbi/BCJR/SOVA/max-log-MAP defined for convolutional trellises.
- **Ch 15**: multistage MLD on decomposed trellises.
- **Ch 16**: SISO block constituents in turbo-like concatenations.

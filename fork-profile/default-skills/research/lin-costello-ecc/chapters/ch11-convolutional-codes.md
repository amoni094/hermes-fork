# Chapter 11: Convolutional Codes

## Core Idea
Convolutional encoders are linear sequential circuits: each n-bit output block is a convolution of the input stream with k finite impulse responses. Memory creates a trellis (and a state diagram) whose free distance d_free, not a per-block d_min, governs error rate. Design knobs are rate R=k/n, memory m (or constraint length ν), and generator polynomials — systematic vs nonsystematic, feedforward vs recursive.

## Key Concepts
- **(n,k,m) encoder**: k input bits per step, n output bits, memory order m (longest input shift register). Constraint length ν = total memory elements (ν = m for k=1). 2^ν states.
- **Generator sequences g^{(j)}**: impulse response from the input to output j. For k=1, G(D) = [g^{(0)}(D) … g^{(n−1)}(D)] with g^{(j)}(D)= Σ g_i^{(j)} D^i.
- **Feedforward (NFF)**: polynomial generators; finite impulse response. Nonsystematic NFF is the classical NASA/GSM style.
- **Recursive systematic convolutional (RSC)**: G(D)=[1, g_num(D)/g_den(D)]. Infinite impulse response; needed for turbo codes (Ch 16). Feedback polynomial is usually primitive.
- **Time-domain generator matrix G**: semi-infinite banded matrix; v = u G.
- **State diagram**: 2^ν nodes; edges labeled u/v. The zero-state loop structure determines catastrophic behavior and d_free.
- **Catastrophic encoder**: a finite-weight nonzero codeword corresponding to infinite-weight input (gcd of generators ≠ 1 for k=1). Never use: a few channel errors can cause infinite decoded bit errors.
- **Free distance d_free**: minimum Hamming weight of any nonzero code sequence that leaves and returns to the zero state. Analog of d_min.
- **Column distance / minimum distance d_min^{(L)}**: min weight over unmerged paths of length L; used to design sequential decoders (Ch 13).
- **Weight enumerating function (WEF / IOWEF)**: generating function from the state diagram (Mason / transfer-function method) counting input weight vs output weight of paths. Feeds union bounds (Ch 12) and turbo analysis (Ch 16).

## Frameworks and Methods
- **Encode (k=1 NFF)**:
  v_t^{(j)} = Σ_{i=0}^m u_{t−i} g_i^{(j)}  (mod 2), then multiplex outputs.
  Example 11.1: R=1/2, m=3, g^{(0)}=(1 0 1 1), g^{(1)}=(1 1 1 1) i.e. (15,17) octal.
- **Terminate**: append ν zero (feedforward) or tail-biting (start=end state) or recursive tail (solve for feedback tail bits). Termination costs ν input bits; rate loss ν/K for block length K.
- **Puncturing**: delete bits from a mother R=1/n code on a periodic pattern to get R=2/3, 3/4, … Same decoder trellis (insert erasures). Standard for adaptive wireless.
- **Good-code search**: maximize d_free, then minimize number of nearest neighbors (A_{d_free}), among non-catastrophic generators of given ν. Tables in Ch 12.
- **Systematic feedforward vs RSC**: systematic FF has worse d_free at given ν; RSC matches nonsystematic d_free but keeps systematic bits for turbo concatenation.

## Key Results
- For k=1, encoder is non-catastrophic iff gcd(g^{(0)}(D),…,g^{(n−1)}(D)) = D^s (usually 1).
- d_free ≤ n(m+1) for NFF k=1 (singleton-like); Heller / Griesmer-type bounds tighten this.
- Transfer-function bound: the generating function T(D,N) of the modified state diagram (zero state split) yields
  T(D,N) = Σ A_{w,d} N^w D^d,
  used in Ch 12 union bounds.
- Example 11.1 path: u=(1 0 1 1 1) with those generators → v=(11,01,00,01,01,01,00,11) after termination handling.
- Rate 2/3 encoder (Example 11.2): k=2 registers, 3 generators per input; G(D) is 2×3 polynomial matrix. Left-invertible for feedforward recovery of u from v in the noiseless case.

## Algorithms and Techniques
**Octal generator notation** (engineering standard):
(1+D+D^2, 1+D^2) = (7,5)_8. NASA standard R=1/2, ν=6: (171,133)_8, d_free=10.

**State labeling**:
State = the ν bits in the shift register(s). For u_t=0 or 1, two branches leave each state; output is the inner product of the extended state with each generator.

**Catastrophic test (k=1)**:
Compute gcd of the n generator polynomials. If the gcd is not a power of D, reject.

**WEF via Mason’s gain formula**:
Split S_0 into S_start and S_end; enumerate simple loops; T(D) = paths from start to end. Computer: solve a 2^ν linear system for generating functions, or DFS with a weight cap.

**Tail-biting**:
Choose the start state so that after K steps the encoder returns there without a tail. No rate loss; decoder uses a circular trellis (Ch 12).

## Anti-patterns
- **Catastrophic generators** such as (1+D, 1+D): gcd=1+D. A single infinite 111… input produces a weight-2 codeword; two channel flips can lock the decoder.
- **Comparing codes by m instead of ν** when k>1: complexity is 2^ν, not 2^m.
- **Using systematic feedforward as a “turbo constituent”**: poor IOWEF; always RSC for parallel concatenation.
- **Forgetting termination** on short packets: unterminated Viterbi has weak ending bits.
- **Puncturing without an erasure-aware metric**: deleted bits must be inserted as erasures (branch metric 0), not as zeros.

## Key Takeaways
1. Convolutional code = linear filter + multiplexer; trellis states = shift-register bits.
2. Design for large d_free and small multiplicity, non-catastrophic, given 2^ν budget.
3. RSC is the turbo building block; NFF (171,133) is the NASA/Viterbi building block.
4. Puncture a mother code rather than designing a new trellis for every rate.
5. Distance analysis uses path weights on the state diagram, not a single-block d_min.

## Connects To
- **Ch 1**: convolutional vs block; example (2,1,2) encoder.
- **Ch 12**: Viterbi, SOVA, BCJR — optimum decoding on this trellis.
- **Ch 13**: sequential and MLG decoding when 2^ν is too large.
- **Ch 16**: two RSC encoders + interleaver = turbo code.
- **Ch 18**: the same trellis labels mapped onto PSK/QAM = TCM.

# Chapter 12: Optimum Decoding of Convolutional Codes

## Core Idea
On a convolutional trellis, maximum-likelihood sequence decoding is the Viterbi algorithm (add-compare-select of survivors). Maximum a posteriori *bit* decoding is the BCJR (forward–backward) algorithm. Together they are the workhorses of wireless, satellite, and turbo inner decoding; puncturing, tail-biting, and SOVA are the practical variants.

## Key Concepts
- **Trellis**: state diagram expanded in time. For (n,k,ν) and information length h (in k-bit blocks): h+m+1 time units if terminated. 2^k branches in/out of each state in the mid-trellis.
- **Path metric M(r|v) = Σ log P(r_i | v_i)** on a DMC. AWGN: equivalent to Euclidean / correlation (Ch 10). Hard BSC: Hamming (minimize disagreements).
- **Viterbi ACS**: at each state, keep only the entering path with the best metric (the survivor). Final survivor at the unique end state is ML (Theorem 12.1).
- **Survivor depth / traceback**: in unterminated streaming, dump a bit after a delay L ≈ 5ν; the survivors have typically merged.
- **Union bound / transfer-function bound**: P_e ≤ Q(√(2 d_free R Eb/N0)) × multiplicity + higher terms from T(D,N).
- **SOVA (Hagenauer)**: Viterbi that also records the metric difference at each ACS; produces a reliability for each bit (approximate APP) for concatenated systems.
- **BCJR / MAP**: compute APP P(u_t | r) via forward α, backward β, and branch γ. Exact bit-MAP on the trellis. Log-MAP / max-log-MAP for numerical stability.
- **Punctured convolutional codes**: delete bits from a mother code; decoder inserts erasures. Same 2^ν trellis.
- **Tail-biting**: circular trellis, no tail bits. Decode by wrapping Viterbi (several methods: two-circle, least-squares start-state search) or circular BCJR.

## Frameworks and Methods
- **Viterbi algorithm** (book steps):
  1. At time t=m, compute partial metrics of the unique paths into each reached state; store survivors.
  2. t ← t+1. For each state: add 2^k branch metrics to previous survivors; compare; select max; discard the rest.
  3. Repeat until t = h+m. The unique survivor is the ML path.
- **Integer metrics**: replace log P(r|v) by c2 (log P + c1) rounded to integers. 3-bit quantized AWGN is near-unquantized.
- **AWGN branch metric**: for BPSK, Σ r_i (2v_i−1) (maximize) or Σ (r_i − c_i)^2 (minimize).
- **Construction of good codes**: computer search maximizing d_free then minimizing A_{d_free} for given R,ν; tables of best (n,1,ν) codes. NASA (171,133)_8, d_free=10, ν=6 is the landmark.
- **Performance**: at high SNR, P_b ~ A_{d_free} Q(√(2 d_free R Eb/N0)). Soft Viterbi ≈ 2–3 dB better than hard Viterbi.

## Key Results
- Theorem 12.1: Viterbi’s final survivor is the ML path (proof: an ML path cannot be eliminated, else grafting the survivor prefix would beat it).
- Complexity: 2^ν states × 2^k ACS per trellis depth × (h+m) depths. Independent of n except in the branch-metric sum of n bits.
- Heller bound / sphere-packing-type bounds on d_free vs ν.
- Soft-output: true MAP = BCJR; SOVA is ~0.1–0.4 dB worse as a SISO in turbo loops but cheaper.
- Max-log-MAP = Viterbi in the forward and backward directions; equivalent to SOVA-with-update in some implementations.
- Punctured R=1/2 mother codes exist that stay non-catastrophic and keep good d_free at R=2/3, 3/4, 5/6 (Yasuda / Cain / Hagenauer tables).

## Algorithms and Techniques
**Viterbi ACS (one state)**:
M_t(s) = max_{s',u} [ M_{t−1}(s') + λ(r_t, v(s',u)) ]
with s = f(s',u). Store argmax as a traceback pointer (1 bit if k=1).

**Traceback**:
From the ending state (0 if terminated, else the state with best metric), follow pointers L steps back and emit that bit. For streaming, do this every few cycles with a sliding window.

**BCJR (log domain sketch)**:
- γ_t(s',s) = P(u_t) · P(r_t | v_t(s',s))
- α_t(s) = max*_s' [α_{t−1}(s') + log γ_t]   (max* = log-sum-exp)
- β_{t−1}(s') = max*_s [β_t(s) + log γ_t]
- L(u_t) = max*_{u=1} (α+γ+β) − max*_{u=0} (α+γ+β)
Initialize α_0(0)=0, α_0(s≠0)=−∞; β_end similarly if terminated.

**SOVA**:
Run Viterbi; at each ACS, Δ = |M_win − M_lose|. For bits that differ along the two paths, update bit reliability to min(current, Δ).

**Punctured decode**:
Insert a dummy branch-metric contribution 0 at punctured coordinates; do not treat them as received 0s.

## Anti-patterns
- **Too-short traceback** (L < 4ν): BER floor on the dumped bits, especially the systematic bits of RSC.
- **Metric saturation / overflow** without renormalization: subtract min-state metric every step.
- **Using Hamming metrics on soft r**: throws away the 2 dB.
- **BCJR in linear probability domain**: underflow; always log-MAP or max-log-MAP.
- **Puncturing a catastrophic mother** or a pattern that collapses d_free to 2.
- **Comparing ν=7 Viterbi to turbo at the same complexity**: Viterbi is ML for *that* code, but the code itself is far from capacity; turbo/LDPC win at large block length.

## Key Takeaways
1. Viterbi = ML sequence decode on the trellis; ACS + traceback.
2. BCJR = bit-MAP; the SISO engine for turbo (Ch 16).
3. Complexity exponential in ν, linear in time — pick ν=5–8 for Viterbi, ν=2–4 for turbo constituents.
4. Quantize to ~3 bits; puncture for rate agility; terminate or tail-bite packets.
5. Union bound from d_free and T(D,N) predicts the high-SNR slope.

## Connects To
- **Ch 9, 14**: same ACS/MAP on *block-code* trellises.
- **Ch 11**: generators, d_free, catastrophic test.
- **Ch 13**: sequential decoding when ν is too large for 2^ν ACS.
- **Ch 16**: iterative BCJR on RSC pairs.
- **Ch 18**: Viterbi with Euclidean metrics on Ungerboeck trellises.

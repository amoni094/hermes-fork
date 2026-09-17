# Chapter 11: Error-Correcting Codes and Real Channels

## Core Idea
The noisy-channel theorem is an existence result; this chapter connects it to codes you can actually implement (Hamming, repetition, convolutional) and to analog channels (AWGN), where the relevant objects are likelihoods, not Hamming balls. Gaussian noise is the default “real channel”; the capacity formula involves SNR, not flip probability.

## Frameworks Introduced
- **From BSC to Gaussian**: a received real y = x + n, n ~ Normal(0,σ²). Soft information P(x|y) beats hard-sliced bits.
- **Linear block codes over GF(2)**: generator matrix G (K×N), parity-check matrix H (M×N), H G^T = 0. Codewords x = u G.
- **Syndrome decoding**: s = H y; syndrome identifies the inferred noise pattern (for simple codes).
- **Convolutional codes**: sliding linear encoder with memory; decoded by Viterbi (Ch 25 trellises).
- **Shannon’s AWGN capacity**: C = (1/2) log2(1 + S/N) nats-per-real-dimension (or bits with log2).

## Key Concepts
- **Gaussian P(y|μ,σ²) = (2πσ²)^{−1/2} exp(−(y−μ)²/(2σ²))** — MacKay’s “About Chapter 11” prerequisite.
- **Hard vs soft decoding**: hard = slice y to 0/1 then Hamming-decode; soft = use full P(y|x). Soft is worth ~2 dB on AWGN.
- **Hamming code** as the canonical linear code: H columns = all nonzero 3-bit vectors; N=7, M=3, K=4, d=3.
- **Rate, SNR, Eb/N0**: coding theory’s real-channel currency is energy per *information* bit over noise PSD.
- **Concatenation / interleaving**: burst channels look i.i.d. after interleaving.

## Key Equations
- y = x + n,  n ~ Normal(0, σ²)
- P(y | x=±1) ∝ exp(−(y∓1)² / 2σ²)
- LLR(x) = log P(y|x=1)/P(y|x=0)  (soft bit)
- C_AWGN = ½ log2(1 + P/σ²)   per real channel use
- For binary input AWGN, C is the BSC-like I(X;Y) with Gaussian kernels, < unconstrained C
- Hamming: d_min=3, corrects t=1 error

## Algorithms and Techniques
**Soft MAP bit for uncoded BPSK**
1. Receive y.
2. Compute LLR = 2y/σ² (for x=±1).
3. Decide sign(LLR); the magnitude is confidence.

**Hamming syndrome decoder (hard)**
1. s = H r  (mod 2).
2. If s=0, accept r; else flip the bit whose H-column equals s.

## Mental Models
- Never throw away analog reliability if you can help it: a 0.1-volt 0 is not the same as a 1.0-volt 0.
- Linear codes turn decoding into inferring a sparse noise vector consistent with the syndrome (foreshadows LDPC).
- AWGN capacity grows only logarithmically with power: doubling power adds ½ bit per real dimension, not 2× rate.

## Worked Example
BPSK ±1 in AWGN, σ=0.5. Received y=0.2.
- P(y|x=+1)/P(y|x=−1) = exp(−(0.2−1)²/2σ² + (0.2+1)²/2σ²) = exp(2y/σ²)=exp(1.6)≈5.
- Posterior if equal priors: P(x=+1|y)≈0.83. Hard slicing to +1 and then pretending it was a clean bit would report certainty 1 — overconfident and harmful to outer codes.

Hamming (7,4) on BSC(f=0.01): P(uncorrectable) ≈ C(7,2) f² ≈ 0.002, vs uncoded 4-bit word error 1−(1−f)^4≈0.04.

## Anti-patterns
- **Hard-slicing before a powerful decoder** (kills turbo/LDPC gains).
- **Optimizing Hamming distance on AWGN as if it were BSC** — the metric is Euclidean.
- **Quoting SNR instead of Eb/N0** when comparing codes of different rates.
- **Using Hamming (7,4) near the BSC Shannon limit of Ch 1’s plots** — it lives at high SNR / low f.

## Key Takeaways
1. Real channels give analog likelihoods; keep them.
2. Linear algebra over GF(2) is the language of almost all practical binary codes.
3. AWGN capacity is ½ log(1+SNR); binary-input capacity is strictly less.
4. Convolutional + Viterbi is the 1960s–90s workhorse; sparse-graph codes overtake it in Part VI.
5. Interleave bursts into an i.i.d. model before applying DMC theory.

## Connects To
- **Ch 1, 9–10**: theory this chapter instantiates.
- **Ch 13**: distance, perfect codes, why Hamming is a dead-end as a family.
- **Ch 25**: trellis / Viterbi / BCJR for convolutional codes.
- **Ch 47–48**: LDPC and turbo on real channels.

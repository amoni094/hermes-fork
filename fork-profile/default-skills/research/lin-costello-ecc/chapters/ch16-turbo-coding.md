# Chapter 16: Turbo Coding

## Core Idea
A turbo encoder is parallel concatenation of two (usually identical) short RSC convolutional encoders separated by a large pseudorandom interleaver. ML decoding of the huge equivalent trellis is impossible; iterative SISO (BCJR) exchange of extrinsic LLRs between the two constituents reaches within a few tenths of a dB of the Shannon limit at moderate BER.

## Key Concepts
- **Parallel concatenation**: systematic bits u transmitted once; parity v^{(1)} from RSC1(u); parity v^{(2)} from RSC2(Π u). Rate ~1/3; puncture to 1/2 by alternating parity bits.
- **RSC constituent**: G(D)=[1, g_n(D)/g_d(D)], typically ν=2–4. Recursive feedback makes weight-1 inputs produce infinite-weight parity — essential so the interleaver can break low-weight codewords.
- **Interleaver Π**: permutation of K bits. Pseudorandom / S-random; *not* a row-column block interleaver (except at tiny K). K is usually thousands.
- **SISO decoder**: BCJR/MAP (best), log-MAP, max-log-MAP, or SOVA. Inputs: channel LLRs + a priori LLRs; output: extrinsic LLR = posterior − a priori − channel, to avoid double-counting.
- **Extrinsic information**: the new information about u from one constituent’s parity; becomes a priori for the other constituent after de/interleaving.
- **Turbo cliff / waterfall**: BER drops steeply over a fraction of a dB near the iterative threshold.
- **Error floor**: high-SNR BER flattening caused by low-weight codewords (often weight-2 input, weight d_free,eff output). Floor ~ K^{-1} A_d Q(√(2 d R Eb/N0)).
- **Multiple turbo codes**: three or more constituents, rate 1/4, …
- **Serial concatenation (SCCs)**: outer + inner convolutional with interleaver; interleaver gain K^{−d_outer/2} even stronger floors, slower convergence.

## Frameworks and Methods
- **Typical operating rules** (from the book’s remarks):
  - Large K (several thousand+) to approach Shannon.
  - Short constituents (ν ≤ 4) for the waterfall; long constituents raise the floor but worsen the cliff.
  - Recursive, usually identical constituents; asymmetric pairs can help the floor.
  - Puncture parities for R=1/2; puncturing systematic bits is possible but delicate.
  - 10–20 iterations, or a stopping rule (CRC, cross-entropy, LLR magnitude).
- **Why not ML?** State complexity of the joint encoder is enormous (interleaver is part of the code). Iterative SISO is not ML, but is typically within 0.1–0.5 dB of ML at waterfall SNRs.
- **Termination**: terminate RSC1 with ν tail bits. RSC2 usually left unterminated for large K; both can be terminated with extra tricks.

## Key Results
- Parallel concatenated RSC + random Π: most weight-2 inputs are mapped so that the two parities cannot both be low weight ⇒ d_free,eff grows (slowly) with K.
- Union bound using the IOWEF of the constituents and the uniform-interleaver average (Benedetto) predicts waterfall (loosely) and floor (well).
- Example constituent in Fig. 16.1(b): (2,1,4) RSC with G=[1, (1+D^4)/(1+D+D^2+D^3+D^4)] — a classic Berrou-style generator.
- Design: primitive (or irreducible) feedback polynomial; feedforward chosen to maximize effective free distance of weight-2 inputs.
- S-random interleaver: |Π(i)−Π(j)| ≥ S for |i−j| < S; raises the floor vs purely random Π.
- Block codes as constituents (turbo product / block turbo) use Ch 10/14 SISOs instead of BCJR.

## Algorithms and Techniques
**Iterative turbo decode (one iteration)**:
1. Decoder 1: BCJR on RSC1 with channel LLRs of (u, v^{(1)}) and a priori L_a^{(1)} (initially 0). Produce extrinsic L_e^{(1)}(u).
2. Interleave L_e^{(1)} → L_a^{(2)}.
3. Decoder 2: BCJR on RSC2 with channel LLRs of v^{(2)} (and of u if systematic is used after Π) and L_a^{(2)}. Produce L_e^{(2)}(u).
4. Deinterleave L_e^{(2)} → L_a^{(1)} for the next iteration.
5. After N_it (or stop): hard-decide L_a^{(1)}+L_ch+L_e^{(1)}.

**Log-MAP vs max-log-MAP**:
Log-MAP uses max*(a,b)=max(a,b)+log(1+e^{−|a−b|}) (lookup). Max-log-MAP drops the correction; lose ~0.3–0.5 dB, save the LUT; often compensated by a 0.7 scaling on extrinsic.

**Puncturing to R=1/2**:
Transmit u, even parities of RSC1, odd parities of RSC2. Decoder treats missing parities as erasures (γ uses only the received bits).

**Stopping**:
Run a CRC on the hard bits each iteration; stop on pass. Saves average iterations at high SNR.

## Anti-patterns
- **Feedforward (nonrecursive) constituents**: weight-1 inputs remain weight-1 after encoding; d_free is tiny regardless of Π.
- **Block interleavers at large K**: regular structure preserves low-weight input pairs; visible error floor.
- **Passing full APP instead of extrinsic**: positive feedback, iteration “sticks.”
- **ν=8 turbo constituents**: waterfall moves *right*; turbo wants simple constituents + big Π.
- **Designing only for d_free**: the floor is about *multiplicity* of low-weight codewords after the interleaver, not the convolutional d_free alone.
- **Too few iterations at the cliff**: BER still 10^{-2} after 2 iters may be 10^{-5} after 8.

## Key Takeaways
1. Turbo = two RSC + big random interleaver + iterative extrinsic BCJR.
2. Recursion + interleaver kill low-weight words; iteration approaches ML of that huge code.
3. Waterfall vs floor is the central design trade (K, S-random, constituent generators, puncture).
4. Rate 1/3 native, 1/2 by puncturing; 3G/4G/CCSDS turbo are this architecture.
5. SISO quality (MAP vs max-log vs SOVA) shows up as a few tenths of a dB — worth it on the cliff.

## Connects To
- **Ch 11**: RSC encoding, IOWEF.
- **Ch 12**: BCJR, SOVA, puncturing, union bounds.
- **Ch 15**: concatenation philosophy turbo upgrades.
- **Ch 17**: LDPC is the competing capacity-approaching iterative code (usually better floors / parallelism).
- **Ch 22**: CRC in the turbo loop as a stopping / HARQ check.

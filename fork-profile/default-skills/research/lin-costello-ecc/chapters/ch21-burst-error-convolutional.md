# Chapter 21: Burst-Error-Correcting Convolutional Codes

## Core Idea
Convolutional codes can be designed to correct *bursts* rather than random errors: Iwadare–Massey-type burst-correcting convolutional codes, interleaved convolutional streams, and diffuse / hybrid burst-and-random convolutional codes. Bounds analogous to Reiger constrain the guard space required between bursts.

Note: this chapter is missing from the OCR merge; content follows ToC 21.1–21.4 and Lin & Costello 2nd ed.

## Key Concepts
- **Guard space**: a run of error-free bits that must separate two bursts so the decoder can reset. Convolutional burst codes need a guard space g ≥ some function of b and the encoder memory.
- **Burst-correcting convolutional code**: corrects any burst of length ≤ b given a sufficient guard space, using a linear sequential decoder (syndrome register + logic), not Viterbi.
- **Wyner–Ash / Iwadare / Massey–Liu constructions**: systematic convolutional codes with simple burst-trapping syndrome circuits.
- **Interleaved convolutional codes**: λ independent (or a multiplexed) convolutional encoders. A burst hits one stream; others provide guard. Equivalent: a convolutional interleaver in front of a random-error Viterbi decoder (the practical approach).
- **Burst-and-random convolutional codes**: Berlekamp–Preparata–Massey “diffuse” codes, Gallager convolutional, or concatenated conv+block. Correct either random t or a burst b with a guard space.
- **Viterbi + interleaving**: not a “burst-correcting convolutional code” in the Massey sense, but the engineering solution of choice on fading channels (GSM, etc.).

## Frameworks and Methods
- **Bound**: a rate-k/n convolutional code that corrects b-bursts with guard space g cannot have too high a rate; analogues of the Reiger and Gallager bounds apply (n−k per unit time vs b).
- **Syndrome burst trap (Iwadare-style)**:
  1. Systematic encoder: v = (u, parity via sparse taps spaced > b).
  2. Syndrome bits fire only when the burst slides over a tap.
  3. Logic waits until the burst has left the information section, then subtracts the estimated burst — needs guard space to avoid overlapping events.
- **Practical fading recipe (preferred unless hardware is 1970s-constrained)**:
  1. Standard (171,133) or turbo/LDPC.
  2. Convolutional or block interleaver spanning several fade durations.
  3. Viterbi/BCJR/BP as if errors were random.
  4. Optional outer RS for residual bursts (Ch 15).

## Key Results
- Guard space g is typically a few times b (often g ≥ n_constraint + 2b). Throughput on a bursty channel is limited by (burst + guard) duty cycle, not just R.
- Interleaving depth λ ≈ T_fade / T_symbol converts a Rayleigh fade into an apparently random error process whose BER Viterbi can handle; latency = interleaver delay.
- Diffuse codes: taps spread over a long constraint so a burst hits only one tap per generator — majority/threshold decoding still works.
- Convolutional interleavers achieve the same separation as block interleavers with about half the delay (Forney).

## Algorithms and Techniques
**Iwadare decoder sketch**:
Keep a syndrome LFSR. When a characteristic syndrome pattern for a burst starting at the current time appears, generate the burst-correction pattern and add it to the delayed information stream. If a second burst arrives inside the guard window, flag erasure.

**Convolutional interleaver (Forney)**:
K rows of delays 0, B, 2B, …, (K−1)B symbols. A burst of length < K is spread by B. Pair with a matching deinterleaver. Total delay K(K−1)B.

**Hybrid**:
Inner interleaved Viterbi (random errors) + outer burst-detecting CRC/RS. Do not mix a Massey burst convolutional decoder with a Viterbi on the same bits.

## Anti-patterns
- **Viterbi without interleaving on a slow fade**: the fade lasts many constraint lengths; the trellis is crushed for that interval (error event of huge length).
- **Guard space < burst spacing on the channel**: theoretically correctable bursts overlap in the decoder memory and both are lost.
- **Deep block interleave for voice**: latency exceeds the jitter budget; use convolutional interleaving or shorter codes + ARQ (Ch 22).
- **Treating Iwadare codes as replacements for turbo on AWGN**: they are weak against random errors.

## Key Takeaways
1. Convolutional burst codes exist and have simple syndrome decoders; they need a guard space.
2. The modern substitute is: ordinary conv/turbo/LDPC + interleaving sized to the fade.
3. Guard space and interleaver delay are the real costs, not extra parity alone.
4. Hybrid burst-and-random convolutional designs exist but concatenation is cleaner.
5. Pair with Ch 20 block burst codes: RS/Fire for storage; interleaved Viterbi for wireless.

## Connects To
- **Ch 11–13**: convolutional structure; MLG convolutional is the random-error cousin of these burst trap decoders.
- **Ch 20**: block burst codes and Reiger bound.
- **Ch 15**: interleaved concatenation as the robust hybrid.
- **Ch 22**: when bursts are too long, detect and ARQ rather than correct.

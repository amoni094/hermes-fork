# Chapter 1: Coding for Reliable Digital Transmission and Storage

## Core Idea
Shannon’s noisy-channel coding theorem says that if the information rate is below channel capacity, properly designed encoding and decoding can drive error probability arbitrarily low. The engineering problem is to build encoder/decoder pairs that approach that limit under power, bandwidth, latency, and complexity constraints.

## Key Concepts
- **Channel encoder / decoder**: maps k-bit messages to n-symbol codewords and recovers an estimate of the information sequence from a noisy received sequence.
- **Block code (n, k)**: each k-bit message is independently mapped to an n-symbol codeword; rate R = k/n; encoder is memoryless combinational logic.
- **Convolutional code**: each n-symbol block depends on the current k-bit block and m previous blocks (memory order m); encoder is sequential logic.
- **Coding channel**: modulator + physical channel/storage + demodulator, with input v and output r.
- **Hard-decision decoding**: demodulator outputs a discrete symbol; decoder uses Hamming distance.
- **Soft-decision decoding**: demodulator outputs a real (or finely quantized) metric; decoder uses likelihood / Euclidean distance. Typical gain over hard decision is ~2–2.5 dB at practical SNR, ~3 dB asymptotically.
- **Maximum-likelihood decoding (MLD)**: choose the codeword maximizing P(r|v); for equally likely codewords this minimizes word-error probability.
- **AWGN / BSC / DMC**: additive white Gaussian noise; binary symmetric channel (hard-decision BPSK); discrete memoryless channel (Q-ary quantized outputs).
- **Coding gain**: reduction in required Eb/N0 versus uncoded modulation at a target BER/WER.
- **Coding threshold**: Eb/N0 below which coding *increases* error rate; operate well above it.
- **Shannon limit**: minimum Eb/N0 for which rate-R error-free communication is theoretically possible.

## Frameworks and Methods
- **System model**: source → source encoder → channel encoder → modulator → noisy channel → demodulator → channel decoder → source decoder. Isolate the coding channel (Figure 1.2) to design the encoder/decoder pair.
- **Block vs convolutional design knobs**:
  - Block: for fixed R, add redundancy by growing n and k together.
  - Convolutional: k and n stay small; add redundancy by growing memory m.
- **BPSK on AWGN**: s1(t) and s0(t) are antipodal carriers of energy Es; received r(t) = s(t) + n(t). Coherent matched-filter samples feed hard or soft decoders.
- **FEC vs ARQ vs hybrid**: forward error correction (one-way, no feedback); automatic-repeat-request (detect + retransmit); hybrid ARQ (FEC + ARQ). Choose FEC for no-feedback / delay-critical links; ARQ when a reverse channel exists and delay is acceptable.
- **Random vs burst errors**: random (independent bit flips, AWGN/BSC) vs burst (fading, magnetic defects). Match code family to the error process, or interleave bursts into random errors.

## Key Results
- Shannon (1948): for R < C, there exist codes with Pe → 0 as n → ∞; random coding is existence, not construction.
- Energy accounting: Eb = Es / R. Plot BER vs Eb/N0, not Es/N0, when comparing rates.
- Asymptotic coding gain, soft-decision MLD of an (n,k) block code with minimum distance d_min:
  - γ_asymp = 10 log10(R d_min) dB versus uncoded BPSK.
- Hard-decision MLD: γ_asymp = 10 log10((R d_min)/2) dB — a 3 dB asymptotic gap versus soft MLD.
- Practical soft-vs-hard gap is typically 2–2.5 dB, not the full 3 dB.
- Example: (23,12) Golay, BPSK, AWGN, BER = 10^{-5}:
  - Hard-decision coding gain ≈ 2.15 dB; soft MLD > 4.0 dB; extra ~1.85 dB from soft decisions.
  - Hard-decision coding threshold ≈ 3.7 dB.
- Uncoded coherent BPSK: Pb ≈ Q(√(2 Eb/N0)); high-SNR approximation (1/2) exp(−Eb/N0).

## Algorithms and Techniques
1. **Hard-decision MLD (block)**: map r to binary vector; decode to the codeword of minimum Hamming distance. Equivalent to nearest-neighbor in Hamming space.
2. **Soft-decision MLD (AWGN)**: map bits {0,1} → {−1,+1}; decode to the codeword minimizing Euclidean distance (equivalently maximizing correlation).
3. **Quantized soft decisions**: Q-level demodulator outputs (DMC). Even 3-bit (8-level) quantization captures most of the unquantized soft-decision gain.
4. **Performance comparison procedure**:
   - Fix modulation and information rate.
   - Plot BER vs Eb/N0 for uncoded, hard-decoded, and soft-decoded systems.
   - Read coding gain at the target BER; check operation is above the coding threshold.

## Anti-patterns
- **Comparing Es/N0 instead of Eb/N0**: rate-R codes use more symbols per information bit; Es/N0 hides the rate penalty.
- **Operating near the coding threshold**: at low SNR, redundancy can *hurt* BER.
- **Assuming 3 dB soft-decision gain at all SNR**: the 3 dB figure is asymptotic; at 10^{-5} it is usually closer to 2 dB.
- **MLD complexity blindness**: optimum decoding of general block codes is exponential in k (or n−k); algebraic and iterative algorithms exist because brute-force MLD does not scale.
- **Ignoring error type**: a random-error code on a bursty channel (or vice versa without interleaving) wastes distance.

## Key Takeaways
1. Capacity is the existence bound; this book is about *constructive* codes and *implementable* decoders.
2. Two code families: block (memoryless per block) and convolutional (shift-register memory).
3. Soft decisions buy ~2–3 dB; spend complexity there before burning power or bandwidth.
4. Coding gain is measured at a BER, versus equal-rate uncoded modulation, in Eb/N0.
5. FEC, ARQ, and coded modulation (Ch 18–19) are complementary tools, not rivals.

## Connects To
- **Ch 2**: finite-field algebra needed for cyclic/BCH/RS constructions.
- **Ch 3–10, 14, 15, 17, 19, 20**: block-code analysis, design, decoding.
- **Ch 11–13, 16, 18, 21**: convolutional codes, turbo, TCM.
- **Ch 22**: ARQ / hybrid ARQ when a reverse channel exists.

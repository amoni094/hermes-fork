# Chapter 1: Coding for Reliable Digital Transmission and Storage

## Core Idea
If the information rate stays below channel capacity, properly chosen encoding and decoding can make the probability of uncorrected error arbitrarily small. Coding is a system-level trade of bandwidth or SNR for reliability, not a patch applied after modulation is frozen.

## Key Concepts
- **Channel coding theorem (Shannon, 1948)**: For rate R < C, there exist codes with Pe → 0 as n → ∞; for R > C, Pe is bounded away from 0.
- **Block code**: Maps k information symbols to n coded symbols; rate R = k/n. Entire block is encoded/decoded as a unit.
- **Convolutional code**: Maps k-bit input blocks continuously into n-bit output blocks with memory of m prior inputs; rate k/n, constraint length related to m.
- **Hamming distance d(u,v)**: Number of positions in which two words differ.
- **Minimum distance d_min**: Smallest distance between distinct codewords. Controls worst-case correction/detection.
- **Error-correction capability**: t = floor((d_min − 1)/2). Corrects any pattern of ≤ t errors.
- **Error-detection capability**: Detects any pattern of ≤ d_min − 1 errors.
- **Hard-decision decoding**: Demodulator outputs binary (or q-ary) symbols; decoder sees a Hamming metric.
- **Soft-decision decoding**: Demodulator outputs reliabilities (LLRs or quantized matched-filter samples); decoder uses Euclidean / correlation metric. Typical gain ~2 dB on AWGN vs hard decisions.
- **Maximum-likelihood (ML) decoding**: Choose the codeword maximizing P(r | c), equivalent (AWGN, equal priors) to nearest neighbor in Euclidean distance.
- **Coding gain**: Reduction in required Eb/N0 versus uncoded modulation at a target Pe.
- **Shannon limit**: Minimum Eb/N0 for reliable communication at a given rate (binary-input AWGN unconstrained Shannon limit ≈ −1.59 dB as R → 0).
- **FEC vs ARQ vs hybrid ARQ**: Forward error correction; automatic repeat request (detect + retransmit); combination.

## Frameworks and Methods
- **Place coding in the system**: Source → encoder → modulator → channel → demodulator → decoder. Do not design the code independently of the constellation, interleaver, and channel memory.
- **Choose code class by error type**: Random independent errors → Hamming / BCH / convolutional / turbo / LDPC. Burst errors → RS, Fire, interleaved codes, burst-correcting convolutional codes. Mixed → concatenated or product constructions.
- **Hard vs soft**: Use hard decisions when the inner demodulator is cheap or the channel is BSC-like; use soft decisions whenever matched-filter samples exist — the extra 2 dB usually dominates extra decoder complexity for convolutional/turbo/LDPC.
- **Performance measures**: Bit error rate (BER), block/word error rate (WER), undetected error probability P_ud, coding gain at a BER operating point, throughput (for ARQ).
- **Coded modulation**: Treat coding and modulation jointly (TCM, BCM, multilevel). Expanding the constellation to “make room” for redundancy avoids bandwidth expansion.

## Key Results
- Shannon: reliable communication is a coding problem once R < C.
- For an (n,k) code with d_min, any error of weight ≤ t is uniquely correctable; any error of weight ≤ d_min−1 is detectable.
- ML decoding of a linear code is NP-hard in general; practical systems use algebraic, trellis, or iterative approximations.
- Uncoded coherent BPSK on AWGN: P_b = Q(√(2 Eb/N0)). Coding gain is measured against this (or against uncoded same-bandwidth modulation).
- Bandwidth expansion of a rate-R binary code with the same modulation is 1/R. Coded modulation can avoid this by using a larger alphabet.

## Algorithms and Techniques
1. **ML decoding (hard, BSC)**: Decode to the codeword at minimum Hamming distance from r.
2. **ML decoding (soft, AWGN)**: Maximize correlation ⟨r, c⟩ or minimize ||r − c||².
3. **Error-control strategy selection**:
   - One-way / deep space / storage: FEC only.
   - Two-way with feedback and delay tolerance: ARQ or hybrid ARQ.
   - Delay-constrained wireless: FEC (turbo/LDPC) plus limited HARQ.
4. **Interleaving**: Convert burst channels into approximately independent-error channels so random-error codes apply.

## Anti-patterns
- **Designing the code after freezing modulation and bandwidth**: Leaves no room for redundancy except by cutting information rate or SNR.
- **Using d_min as the only figure of merit**: Weight spectrum, trapping sets, and the distance to the Shannon limit dominate turbo/LDPC performance.
- **Hard-decision decoding “because it is simpler” on AWGN**: Throws away ~2 dB that iterative soft decoders exist to harvest.
- **Ignoring undetected error rate**: A decoder that always outputs a codeword can be worse for storage/ARQ than one that flags erasures.
- **Comparing coding gain at the wrong Pe**: Gains look huge at Pe=10−2 and modest at 10−9; quote the operating point.

## Worked Example
Uncoded BPSK needs Eb/N0 ≈ 9.6 dB for P_b = 10−5. A rate-1/2 convolutional code with soft Viterbi might operate at ~4.5 dB for the same P_b: coding gain ≈ 5 dB, at the cost of doubled bandwidth (or a shift to coded modulation if bandwidth is fixed).

## Key Takeaways
1. Coding works because of Shannon; the rest of the book is how to approach capacity with implementable encoders/decoders.
2. Match code type to error statistics (random, burst, mixed) and to the presence of feedback.
3. Soft information is worth roughly 2 dB on AWGN — treat it as a first-class interface.
4. Rate, d_min, decoding complexity, and latency are the four-way trade, not rate vs d_min alone.
5. Coded modulation is the tool when bandwidth cannot expand.

## Connects To
- **Ch 2**: Algebra (groups, fields, GF(2^m)) needed for all algebraic constructions.
- **Ch 3–10**: Block-code theory, from linear/cyclic/BCH/RS through trellis and soft decoding.
- **Ch 11–13**: Convolutional codes and Viterbi/sequential/threshold decoding.
- **Ch 16–17**: Capacity-approaching turbo and LDPC.
- **Ch 18–19**: TCM/BCM when constellation and code are joint.
- **Ch 20–22**: Bursts and ARQ.

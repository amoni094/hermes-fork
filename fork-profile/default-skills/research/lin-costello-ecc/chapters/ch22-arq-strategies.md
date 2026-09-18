# Chapter 22: Automatic-Repeat-Request Strategies

## Core Idea
If a reverse channel exists, detect errors (cheap CRC / cyclic code) and request retransmission instead of — or in addition to — correcting them. ARQ throughput depends on the protocol (stop-and-wait, go-back-N, selective-repeat), the delay-bandwidth product, and whether FEC is combined with ARQ (hybrid Type-I/II). Invertible half-rate codes let Type-II systems send parities first, then extra bits that form a second codeword.

Note: this chapter is missing from the OCR merge; content follows ToC 22.1–22.8 and Lin & Costello 2nd ed.

## Key Concepts
- **Pure ARQ**: error *detection* only (typically shortened cyclic / CRC). On detected error, NAK and retransmit.
- **Stop-and-wait (SW)**: send one frame, wait ACK/NAK. Simple; throughput collapses on long RTT.
- **Go-back-N (GBN)**: window of N frames; NAK of frame i resends i and everything after. Needs only sequential delivery buffer at receiver; wasteful on high RTT × rate links.
- **Selective-repeat (SR)**: retransmit only the NAKed frames. Best throughput; receiver needs random-access buffer. Finite buffer ⇒ special handling (this chapter’s §22.2).
- **Hybrid ARQ Type-I**: each transmission is already FEC-coded (e.g. BCH+CRC). Decode; if fail, retransmit the *same* word. Useful on a mix of good/bad SNR.
- **Hybrid ARQ Type-II (incremental redundancy)**: first send a high-rate word (or just information + CRC); on fail, send extra parity that, combined with the first block, forms a lower-rate code. Lin–Yu invertible codes; punctured conv / turbo / LDPC in later standards (3G/4G HARQ).
- **Invertible half-rate code**: from the parity block alone one can recover the information (and vice versa). If either half arrives clean, done; if both are noisy, decode the concatenated (n, k) word.
- **Throughput η**: information bits accepted per channel bit (or per second). For ideal SR with P_d the frame-error/detect probability, η ≈ R (1−P_d) for Type-I rate-R FEC. SW includes idle time 1/(1+D) where D is delay in frames.

## Frameworks and Methods
- **When ARQ vs FEC-only**:
  - ARQ: two-way channel, delay OK (file transfer, TCP-like, satellite with buffering).
  - FEC-only: broadcast, deep space one-way, hard latency (speech).
  - Hybrid: cellular (3G/4G HARQ), WiFi.
- **Detection code**: CRC-16/32 or shortened BCH. P_undetected ~ 2^{−r} for r parity bits (Ch 3–5). Never use a weak checksum as the ARQ detector on a noisy link.
- **Finite-buffer SR**: if the receiver window fills, fall back to GBN-like stalls or NAK a block of frames. Analysis in §22.2 is the book’s distinctive contribution vs textbook infinite-buffer SR.
- **Type-II with invertible (n, n/2) code** (e.g. half-rate invertible block):
  1. Send information half I.
  2. If NAK, send parity half P = I · P_matrix. Receiver recovers I from P if P is clean (invertibility), else decodes (I,P) as a length-n codeword.
  3. Further NAKs repeat I or P (mixed-mode, §22.3).

## Key Results
- SW throughput: η = (k/n) / (1 + D) × (1−P_f) for frame failure P_f, D = RTT/frame duration. Unusable when D ≫ 1.
- Ideal infinite-buffer SR: η = (k/n)(1−P_f) — delay disappears from the formula (but not from latency).
- GBN: η = (k/n) (1−P_f) / (1 + D P_f) approximately — one error costs D extra frames.
- Type-II vs Type-I: on good channels Type-II sends almost no extra parity (high throughput); on bad channels it falls back to a strong code (reliability). Type-I always pays the FEC rate.
- Concatenated coded-modulation HARQ (§22.8): TCM/BCM inner + ARQ outer uses Viterbi/BCM reliability as a quality metric to NAK.

## Algorithms and Techniques
**SR with finite receiver buffer B**:
- Accept out-of-order good frames into B slots.
- If B is full and a hole remains, NAK the oldest missing frame *and* pause the window (or go-back).
- Deliver in order to the user.

**Type-II invertible cycle**:
1. Encode u → (u, p(u)) with an invertible half-rate code (p invertible: u = f(p)).
2. Transmit u. CRC. If OK, done.
3. Transmit p. CRC on p; if OK, invert to u. If not, run the (2k,k) decoder on received (û, p̂).
4. Optional extra rounds: retransmit the noisier half.

**Convolutional hybrid ARQ** (§22.7):
Puncture a mother conv/turbo code for the first transmission; send previously punctured bits on retransmission (incremental redundancy). Decode with erasures at still-missing bits (Ch 12).

**CRC in the loop**:
r parity bits, undetected error ≈ 2^{−r}. Choose r so that 2^{−r} × frames/session ≪ target integrity (often r=16 or 32). FEC reduces P_f; CRC reduces P_undetected.

## Anti-patterns
- **SW on a GEO satellite**: D huge; use SR or GBN with a large window.
- **SR without a delivery-order buffer**: the user sees reordered data; most applications cannot.
- **Type-I heavy FEC on a clean channel**: wasted rate; Type-II or adaptive modulation+code.
- **ARQ without a bound on retries**: livelock on a dead link; cap retries and fail upward.
- **Using error-correcting decode without CRC**: miscorrection looks like a good frame (silent data corruption). Always detect after correct, or use a code with leftover detection capability (d_min ≥ 2t+2).

## Key Takeaways
1. ARQ converts detection capability into reliability at the cost of throughput and delay.
2. Protocol choice is dominated by delay-bandwidth: SW < GBN < SR.
3. Hybrid Type-II (incremental redundancy, invertible codes) is the throughput-optimal mix of FEC and repeats — ancestor of 3G/4G HARQ.
4. Finite receiver buffers change SR analysis; real systems are finite.
5. Always CRC (or equivalent) to bound undetected error; FEC/ARQ only handles detected failures.

## Connects To
- **Ch 3, 5**: undetected-error probability; CRC as shortened cyclic codes.
- **Ch 6–7**: BCH/RS as Type-I FEC or Type-II extra parity.
- **Ch 12, 16, 17**: punctured conv/turbo/LDPC incremental redundancy.
- **Ch 18–19**: coded-modulation HARQ.
- **Ch 1**: FEC vs ARQ vs hybrid as the three error-control strategies.

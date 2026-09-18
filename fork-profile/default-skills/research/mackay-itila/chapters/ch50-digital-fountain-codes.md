# Chapter 50: Digital Fountain Codes

## Core Idea
For erasure channels (internet packets), feedback retransmission is Shannon-wasteful — especially on broadcast. LT / digital fountain codes are *rateless* sparse-graph codes: the encoder emits a limitless stream of random XOR packets; the decoder recovers K source packets from any K′≈K(1+ε) received packets, with encoding/decoding cost ~ K ln(K/δ). No need to know f in advance.

## Key Concepts
- **q-ary erasure channel**: alphabet size q=2^ℓ (packet of ℓ bits); delivered intact with prob 1−f, else “?”. Capacity (1−f)ℓ bits per packet slot. Feedback does not increase capacity.
- **Coupon collector / balls and bins**: N=K random inspections leave ~1/e pages unseen; to hit all K with probability 1−δ need N≃ K ln(K/δ). This is the *repetition* fountain; XOR degree>1 beats it.
- **Reed–Solomon**: any K of N symbols suffice, but polynomial cost, fixed N, small K,N,q, no on-the-fly rate change.
- **LT code (Luby transform)**: each encoded packet has degree d~ρ(d), then XOR of d random source packets. Rateless; universal (one scheme for every f).
- **Overhead**: K′−K ~ √K (ln(K/δ))² in the analysis Luby gives; ~5% in practice as quoted.
- **Ripple / peeling decoder**: degree-1 packets reveal a source symbol; XOR it out of neighbours; repeat (same as iterative erasure decoding of LDPC).

## Frameworks and Methods
- **Why not ACK/NACK**: many receivers, independent erasures; retransmitting “whoever missed it” duplicates work. A fountain lets each receiver stop when *their* bucket is full.
- **Degree distribution is the design**: all degree 1 ⇒ coupon collector. Robust soliton distribution keeps a small “ripple” of degree-1 checks throughout peeling so you neither stall nor flood.
- **Graph**: bipartite source nodes — encoded nodes; received encoded nodes only. Decoding = peeling / message passing on an erasure channel (BP is exact enough here).
- **Universal + cheap**: near-optimal for every erasure rate; cost O(K ln(K/δ)) packet XORs both ways.

## Key Equations
- Capacity of erasure channel: C = (1−f) log₂ q  per use
- Coupon collector: N ≃ K ln(K/δ) to cover all with prob 1−δ
- Encoded packet: t_n = ∑_{i∈S_n} s_i   (mod 2, bitwise),  |S_n|=d_n ~ ρ
- Ideal soliton (sketch): ρ(1)=1/K,  ρ(d)=1/(d(d−1)) for d=2..K
- Robust soliton: extra mass on small degrees so the ripple does not die
- Overhead: K′ = K + O(√K ln²(K/δ))
- Cost: O(K ln(K/δ)) XORs

## Algorithms and Techniques
**Encode (endless)**
1. Draw d from ρ (robust soliton).
2. Draw d distinct source indices uniformly.
3. XOR those packets; emit. Repeat until receivers stop you (or a time budget).

**Peeling decode**
1. While some received packet has degree 1: identify that source symbol.
2. XOR it out of every other received packet that includes it (degrees drop).
3. If stuck with no degree-1 and unrecovered sources, collect more fountain drops and retry.
4. Success when all K sources recovered.

## Anti-patterns
- **Fixing N from a guessed f** when f is unknown or heterogeneous across users — this is what rateless avoids.
- **Degree-1-only fountain** — you pay full coupon-collector log K.
- **RS for huge K** — cubic/quadratic packet operations, no streaming extension.
- **Using feedback capacity-style “we needed it because erasures”** — Shannon says no.

## Key Takeaways
1. Erasure + broadcast: fountain beats ACK protocols.
2. LT: random sparse XORs + peeling; rateless and universal.
3. The degree distribution *is* the code.
4. Overhead a few percent, complexity K log K, not K(N−K).
5. End of the book’s sparse-graph arc: LDPC, turbo, RA, fountain.

## Connects To
- **Ch 9–11**: erasure capacity, why feedback is unnecessary.
- **Ch 47**: peeling is BP on erasures; LDPC also peel on BEC.
- **Ch 1**: from toy repetition to codes that work on packet networks.
- **Ch 12**: hashing / coupons as information-retrieval cousins of collector.

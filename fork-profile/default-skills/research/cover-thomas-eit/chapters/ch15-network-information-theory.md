# Chapter 15: Network Information Theory

## Core Idea
Many senders and receivers introduce interference, cooperation, and side information. The general network problem is unsolved; the solved islands are the multiple-access channel (MAC), Slepian–Wolf distributed lossless compression, the degraded broadcast channel, some relay channels, and rate-distortion with side information (Wyner–Ziv). Proofs extend joint typicality to many variables; converses use Fano plus identification of auxiliaries.

## Key Concepts
- **Capacity region**: closure of achievable rate tuples (R1,R2,...) with Pe→0, not a single C.
- **MAC**: two (or m) encoders, one decoder, p(y|x1,x2). Senders cannot see each other’s messages.
- **Slepian–Wolf**: two correlated sources X,Y encoded separately, decoded jointly. Rates R1≥H(X|Y), R2≥H(Y|X), R1+R2≥H(X,Y).
- **Broadcast channel (BC)**: one encoder, two decoders p(y,z|x). Degraded: p(y,z|x)=p(y|x)p(z|y).
- **Relay**: sender X, relay (X1,Y1), destination Y. Decode-and-forward / compress-and-forward.
- **Interference / two-way / MIMO**: mostly unsolved or Gaussian-specialized.
- **Wyner–Ziv**: rate distortion with side information at the decoder only.
- **Gelfand–Pinsker**: channel with state known to the encoder (dual of Wyner–Ziv).
- **Joint typicality among k variables**: A_ε^{(n)}(S) for every subset S.

## Frameworks and Methods
- **MAC achievability**: independent random codebooks; decode by joint typicality with *both* codewords. Time-sharing convexifies; equivalently a time-sharing Q.
- **MAC converse**: Fano on each message and on the pair; identify X1,X2 as channel inputs; introduce Q as a time index.
- **Slepian–Wolf random binning**: each source sequence independently thrown into 2^{nR} bins; decoder looks for the unique jointly typical pair in the received bins.
- **Superposition coding (broadcast)**: cloud centers for the weak user, satellites for the strong user.
- **Max-flow min-cut**: every cut’s mutual information upper-bounds the sum rate through that cut; rarely tight.

## Key Results and Theorems

**Gaussian single-user reminder.** C=½ log(1+P/N).

**Gaussian MAC (m users, equal noise).**
C_sum = ½ log(1 + (∑ P_i)/N). Individual rates: R_i ≤ ½ log(1+P_i/N) after others are decoded (SIC). The region is a pentagon (two users) / polymatroid (m users).

**Theorem 15.3.1 (MAC capacity).** For independent inputs X1~p1, X2~p2,
R1 < I(X1;Y|X2),  R2 < I(X2;Y|X1),  R1+R2 < I(X1,X2;Y).
Capacity region = closure of convex hull of all such pentagons. Equivalent form (Thm 15.3.4): the same inequalities with a time-sharing Q, X1–Q–X2 Markov, |Q| small (Carathéodory).

**Convexity (Thm 15.3.2).** Time-sharing makes C convex.

**Theorem 15.4.1 (Slepian–Wolf).** Separate encoding of i.i.d. pairs (Xi,Yi) with joint decoding is possible iff
R1 ≥ H(X|Y),  R2 ≥ H(Y|X),  R1+R2 ≥ H(X,Y).
Achievability: random binning + joint typicality. Converse: Fano as if the other source were side information (Ch 5) plus the joint entropy bound.

**Many sources.** For X^{(1)},...,X^{(m)},
∑_{i∈S} R_i ≥ H(X^{(S)} | X^{(S^c)})  for every subset S.

**Duality SW ↔ MAC.** The SW rate region looks like a MAC region with “channel” p(x,y) playing the role of a joint; packing vs covering dual.

**Degraded broadcast capacity.** Auxiliary U:
R2 ≤ I(U;Y2),  R1 ≤ I(X;Y1|U),  U→X→(Y1,Y2),
with Y2 degraded wrt Y1. Superposition coding achieves it.

**Gaussian BC** (same noise, different SNRs): superposition + dirty-paper / superposition ordering; capacity known (degraded).

**Relay (Thm 15.7.1).** Cut-set
C ≤ sup_{p(x,x1)} min{ I(X,X1;Y), I(X; Y,Y1 | X1) }.
Achieved for *degraded* relays by decode-and-forward.

**Source coding with side information.** If Y is at both encoder and decoder, rate H(X|Y). If only at decoder (lossless): still H(X|Y) — Slepian–Wolf with R2=H(Y) “free”.

**Wyner–Ziv (rate distortion with SI at decoder).**
R_{X|Y}(D) = min I(X;U|Y) over U→X→Y and E d(X, X̂(U,Y))≤D.
Generally R_{X|Y}(D) > R_{X|Y}^{full SI at encoder}(D) (no rate loss for Gaussian MSE, rate loss for binary Hamming).

**Gelfand–Pinsker.** Channel p(y|x,s) with i.i.d. state S known noncausally at encoder:
C = max_{p(u,x|s)} [I(U;Y)−I(U;S)].
Dirty-paper coding: Gaussian interference known at encoder costs nothing.

**General networks.** Cut-set bounds; inner bounds via random coding, binning, superposition, decode-forward. Capacity of the general interference channel is open.

## Key Equations
- MAC: R1≤I(X1;Y|X2), R2≤I(X2;Y|X1), R1+R2≤I(X1,X2;Y)
- Gaussian MAC sum: ½ log(1+∑P_i/N)
- SW: R1≥H(X|Y), R2≥H(Y|X), R1+R2≥H(X,Y)
- Degraded BC: R2≤I(U;Y2), R1≤I(X;Y1|U)
- Wyner–Ziv: min I(X;U|Y)
- Gelfand–Pinsker: max[I(U;Y)−I(U;S)]
- Cut-set: R_S ≤ I(X_S; Y_{S^c} | X_{S^c})

## Worked Example
Slepian–Wolf: X,Y i.i.d. Bern(1/2) with P(X≠Y)=0.11. Then H(X,Y)=1+H(0.11)≈1.5, H(X|Y)=H(0.11)≈0.5. Rates (0.5,1), (1,0.5), (0.75,0.75) all work. Naive separate compression would need 1+1=2 bits. Binning saves 0.5 bit — the correlation is used only at the decoder.

Gaussian MAC, two users P1=P2=N: sum capacity ½ log(1+2)=½ log 3 ≈ 0.792, whereas TDMA gives ½ · ½ log(1+2) wait no: TDMA with power P during half time: (1/2)(1/2)log(1+2P/N) if power cannot concentrate; with power concentration ½ · ½ log(1+4) wait — standard: without power reallocation TDMA sum is ½ log(1+P/N)=0.5 < 0.792. Superposition/SIC beats taking turns.

## Anti-patterns
- **Adding single-user capacities**: MAC sum can be less than C1+C2 because of interference; SW sum can be less than H(X)+H(Y) because of correlation.
- **Assuming encoder-side SI and decoder-side SI are equivalent for lossy coding**: they are for lossless, not for lossy (Wyner–Ziv rate loss).
- **Using cut-set as capacity**: it is only an outer bound.
- **Forgetting independence of MAC inputs**: p(x1,x2)=p(x1)p(x2) (or given Q); cooperation would be a different network.
- **Treating the general BC / interference channel as solved**: they are not.

## Key Takeaways
1. Networks have regions, not scalars; extra ingredients are binning, superposition, and auxiliaries.
2. Slepian–Wolf: correlation is useful even if encoders do not communicate.
3. MAC is the best-solved multiuser channel; Gaussian MAC waterfills / SIC.
4. Dualities: SW↔MAC, Wyner–Ziv↔Gelfand–Pinsker, packing↔covering.
5. Most general networks remain open; use cut-set + a matching inner bound.

## Connects To
- **Ch 7**: single-user template.
- **Ch 10**: Wyner–Ziv extends R(D).
- **Ch 9**: Gaussian specializations of every network.
- **Ch 3, 11**: joint typicality / types for multiuser error events.

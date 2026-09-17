# Chapter 7: Channel Capacity

## Core Idea
The capacity of a discrete memoryless channel is C = max_{p(x)} I(X;Y): all rates R < C are achievable with Pe → 0, and no higher rate is. The proof is random coding + jointly typical decoding; the converse is Fano. Feedback does not increase DMC capacity; source–channel separation holds for i.i.d. sources.

## Key Concepts
- **DMC**: p(y^n|x^n) = ∏ p(y_i|x_i). Memoryless, no ISI.
- **(M,n) code**: M messages, n channel uses, encoder {1..M}→X^n, decoder Y^n→{1..M}. Rate R = (1/n) log M. Pe^{(n)} = (1/M) ∑_w Pr(ŵ≠w|w).
- **Achievable rate**: some sequence of (2^{nR}, n) codes with Pe^{(n)}→0. Capacity = supremum of achievable rates.
- **Jointly typical set A_ε^{(n)}**: pairs (x^n,y^n) that are separately typical and jointly typical, i.e. −(1/n)log p(x^n)≈H(X), etc., and −(1/n)log p(x^n,y^n)≈H(X,Y).
- **Symmetric channel**: rows of p(y|x) are permutations of each other, and so are columns (weakly symmetric: columns have the same sum). Capacity at uniform input.
- **Zero-error capacity**: rates with Pe=0 exactly; combinatorial, generally unknown (Lovász).
- **Feedback capacity**: encoder may see past Y^{i−1}. For DMC, C_FB = C.

## Frameworks and Methods
- **Operational vs information**: define C operationally (max achievable R), then prove it equals max I(X;Y).
- **Joint typicality decoding**: generate 2^{nR} i.i.d. codewords ~ p(x); decode the unique codeword jointly typical with Y^n.
- **Error events**: (i) true pair atypical; (ii) some wrong codeword jointly typical with Y. (i)→0 by AEP; (ii) ≤ 2^{nR} 2^{−n(I(X;Y)−3ε)} →0 if R < I−3ε.
- **Converse**: nR = H(W) = I(W;Y^n)+H(W|Y^n) ≤ I(X^n;Y^n)+nε_n ≤ ∑ I(X_i;Y_i)+nε_n ≤ nC+nε_n, with Fano bounding H(W|Y^n).
- **Time-sharing / convexity**: C is already a max of a concave function; no need to convexify for a single DMC.

## Key Results and Theorems

**Examples.**
- Noiseless binary: C=1.
- Noisy typewriter (26 letters, each letter → itself or next, 1/2): C = log 13.
- BSC(p): C = 1 − H(p).
- BEC(α): C = 1−α.

**Symmetric channels.** C = log|Y| − H(row of p(y|x)) = log|Y| − H(Y|X) at uniform X.

**Properties.** 0 ≤ C ≤ min{log|X|, log|Y|}; C=0 iff p(y|x)=p(y).

**Theorem 7.6.1 (Joint AEP).** If (X_i,Y_i) i.i.d. ~ p(x,y):
1. P((X^n,Y^n) ∈ A_ε^{(n)}) → 1.
2. |A_ε^{(n)}| ≤ 2^{n(H(X,Y)+ε)}.
3. If X̃^n ~ p(x^n) independent of Y^n ~ p(y^n), then
P((X̃^n,Y^n)∈A_ε^{(n)}) ≤ 2^{−n(I(X;Y)−3ε)},
and ≥ (1−ε)2^{−n(I(X;Y)+3ε)} for n large.

**Theorem 7.7.1 (Channel coding theorem).** All rates R < C = max_{p(x)} I(X;Y) are achievable. Conversely, any sequence of codes with Pe^{(n)}→0 must have R ≤ C.

**Feedback (Thm 7.12.1).** For a DMC, feedback does not increase capacity: C_FB = C. Proof: I(W;Y^n) still ≤ ∑ I(X_i;Y_i) ≤ nC even if X_i = X_i(W,Y^{i−1}). (Feedback *can* help with second-order / complexity / channels with memory.)

**Source–channel separation (Thm 7.13.1).** An i.i.d. source of entropy H can be sent reliably over a DMC iff H < C. Joint source-channel coding cannot beat separation for this i.i.d. point-to-point setting. (Fails for networks, some lossy settings, non-ergodic channels.)

**Hamming codes.** Concrete BSC codes; minimum distance decoding; show the coding theorem is not vacuous, but do not achieve capacity.

**Zero-error.** C_0 ≤ C; generally C_0 < C. Shannon 1956; still open in general.

## Key Equations
- C = max_{p(x)} I(X;Y)
- BSC: C = 1−H(p)
- BEC: C = 1−α
- Joint typicality: P(unrelated pair typical) ≈ 2^{−n I(X;Y)}
- Converse skeleton: R ≤ (1/n)I(X^n;Y^n) + ε_n ≤ C + ε_n

## Worked Example
BSC(p=0.11): H(0.11)≈0.5, so C≈0.5 bits/use. Random coding at R=0.4: about 2^{0.4 n} codewords in {0,1}^n. The output sphere around a codeword has “effective” size 2^{n H(p)} ≈ 2^{0.5 n}; packing 2^{0.4 n} of them into 2^n leaves room (0.4+0.5<1). At R=0.6 there is no room: 0.6+0.5>1.

BEC(α=0.5): C=0.5. Capacity-achieving input is Bernoulli(1/2); erasures are known, so you get 1 bit on non-erased uses.

## Anti-patterns
- **Maximizing I over p(y|x)**: the channel is given; maximize only over p(x).
- **Expecting feedback to raise DMC capacity**: it does not.
- **Using joint source-channel codes to beat H<C**: not in this theorem’s setting.
- **Confusing Pe→0 with Pe=0**: capacity allows vanishing error, not zero error.
- **Decoding by nearest neighbor without typicality in the proof**: equivalent at the BSC, but joint typicality is the general argument.
- **Assuming C is achieved at uniform input**: only for (weakly) symmetric channels.

## Key Takeaways
1. C = max I(X;Y) is both operational and informational.
2. Random coding + joint typicality is the achievability template for the rest of the book.
3. Fano + chain rule + memoryless is the converse template.
4. Feedback and separation are DMC luxuries; they fail in networks (Ch 15).

## Connects To
- **Ch 2**: I, Fano, DPI, concavity of I in p(x).
- **Ch 3**: AEP upgraded to pairs.
- **Ch 8–9**: continuous analog; AWGN formula.
- **Ch 10**: rate-distortion is the dual covering theorem.
- **Ch 13**: universal codes ↔ channel capacity of the “type channel”.
- **Ch 15**: MAC, broadcast, Slepian–Wolf reuse this proof with extra typicality.

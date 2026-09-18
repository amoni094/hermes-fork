---
name: cover-thomas-eit
description: "Knowledge base from Cover & Thomas 'Elements of Information Theory' (2nd ed, 2006). Use when applying rigorous information theory: entropy measures, AEP, channel capacity proofs, rate-distortion, network IT, portfolio theory connections, or verifying theorem statements."
related_skills:
  - shannon-1948
  - gallager-itrc
  - mackay-itila
---

# Cover & Thomas — Elements of Information Theory (2nd ed, 2006)

Graduate reference. 17 numbered chapters (not 18). Logs base 2 unless noted. Verify theorem numbers against [theorems.md](theorems.md) and [cheatsheet.md](cheatsheet.md).

## Core framework: five quantities

**Entropy H(X) = −∑ p(x) log p(x).** Uncertainty / lossless description length. H≥0, H≤log|X| (eq. iff uniform). Chain rule H(X^n)=∑ H(Xi|X^{i−1}). Conditioning reduces entropy *on average*: H(X|Y)≤H(X). For processes, use the **entropy rate** H = lim (1/n)H(X^n) = lim H(Xn|X^{n−1}) (stationary).

**Relative entropy D(p||q) = ∑ p log(p/q).** Directed discrepancy; D≥0, eq. iff p=q (information inequality — the master inequality). Not a metric. Infinite if supp(p) ⊈ supp(q). Chain rule D(p(x,y)||q(x,y))=D(p(x)||q(x))+D(p(y|x)||q(y|x)). Operationally: extra bits when coding p with a q-code; Sanov rate function; Stein exponent.

**Mutual information I(X;Y) = D(p(x,y)||p(x)p(y)) = H(X)−H(X|Y).** Bits that Y reveals about X. I≥0, eq. iff independent. Concave in p(x) for fixed channel, convex in p(y|x) for fixed input — so C=max_p I is a concave program. **DPI:** X→Y→Z ⇒ I(X;Y)≥I(X;Z). **Fano:** small I (large H(X|Y)) ⇒ large Pe.

**Differential entropy h(X)=−∫ f log f.** Algebra of H carries over; h can be negative and scales as h(aX)=h(X)+log|a|. Not an operational entropy. **I and D are the invariants.** Gaussians maximize h given covariance: h(N(0,K))=(1/2)log((2πe)^n|K|). This single fact yields AWGN capacity and Gaussian R(D).

**Capacity C = max_{p(x)} I(X;Y).** Operationally, the max rate with Pe→0 on a DMC. Packing: ~2^{nC} distinguishable n-sequences. Dual covering problem: **R(D)= min_{Ed≤D} I(X;X̂)** is the min rate to describe X at distortion D.

Relations: I is a D; H is a self-information I(X;X); C and R(D) are optimizations of I; typical-set size 2^{nH} is AEP applied to H; mismatch costs D; side information is worth at most I (exactly I in the horse race). Proof templates: **achievability = random code + (joint) typicality**; **converse = Fano + chain rule + single-letterization**.

## Three fundamental theorems

1. **Noiseless source coding.** i.i.d. X compresses to H(X) bits/symbol: H ≤ L_n^*/n < H+1/n. One-shot: Kraft ∑ D^{−l_i}≤1 and L≥H_D; Huffman optimal. Typical-set coding: enumerate A_ε^{(n)}, |A|≈2^{nH}.

2. **Noisy channel coding.** DMC: all R<C=max_p I(X;Y) are achievable with Pe→0; conversely R≤C. Joint typicality decoding; converse via Fano. BSC: C=1−H(p). BEC: C=1−α. AWGN power P: C=(1/2)log(1+P/N). Feedback does not increase DMC C. Separation: i.i.d. source through DMC iff H<C.

3. **Rate distortion.** R(D)=min_{Ed≤D} I(X;X̂). Bern/Hamming: H(p)−H(D) (D≤p). Gaussian/MSE: (1/2)log(σ^2/D) (D≤σ^2). Strong typicality / covering, not packing.

## Chapter index

| Ch | Title | Key theorems |
|----|--------|----------------|
| 1 | Introduction and Preview | Program: H compresses, C communicates |
| 2 | Entropy, Relative Entropy, Mutual Information | Chain rules; D≥0; DPI; Fano; H≤log\|X\| |
| 3 | Asymptotic Equipartition Property | AEP; \|A_ε^n\|≈2^{nH}; smallest probable set |
| 4 | Entropy Rates of a Stochastic Process | H=H' stationary; Markov H=H(X2\|X1); 2nd law via D |
| 5 | Data Compression | Kraft; L≥H; Huffman; McMillan; wrong-code D |
| 6 | Gambling and Data Compression | Kelly b^*=p; W^*=∑p log o − H; ΔW=I |
| 7 | Channel Capacity | C=max I; coding thm; joint AEP; C_FB=C; separation |
| 8 | Differential Entropy | h; Gaussian maxent; H(X^Δ)+log Δ→h |
| 9 | Gaussian Channel | C=½ log(1+P/N); waterfill; bandlimited W log(1+P/N0W) |
| 10 | Rate Distortion Theory | R(D)=min I; binary/Gaussian formulas; reverse waterfill |
| 11 | Information Theory and Statistics | Types; Sanov; Stein; Chernoff; Fisher/Cramér–Rao |
| 12 | Maximum Entropy | Exponential family; Burg Gauss–Markov |
| 13 | Universal Source Coding | Minimax redundancy=C(θ;X); LZ → H a.s.; arithmetic |
| 14 | Kolmogorov Complexity | Invariance; E K≈nH; P_U≈2^{−K}; uncomputable |
| 15 | Network Information Theory | MAC; Slepian–Wolf; degraded BC; Wyner–Ziv; GP |
| 16 | Information Theory and Portfolio Theory | Log-optimal b^*; ΔW≤I; universal portfolio; SMB AEP |
| 17 | Inequalities in Information Theory | EPI; de Bruijn; Han; Hadamard; Pinsker |

## Topic index

- AEP / typical sets → Ch 3, 7, 16 (SMB)
- Binary entropy, BSC, BEC → Ch 2, 7
- Broadcast / MAC / relay → Ch 15
- Capacity computation (Blahut–Arimoto) → Ch 7, 10
- Chain rules, DPI, Fano → Ch 2, 17
- Differential entropy / Gaussian maxent → Ch 8, 9, 17
- English entropy / gambling → Ch 6
- EPI, Fisher, de Bruijn → Ch 11, 17
- Feedback → Ch 7, 9
- Huffman, Kraft, Shannon codes → Ch 5
- Hypothesis testing, Sanov, types → Ch 11
- Kolmogorov / MDL / universal probability → Ch 14
- Lempel–Ziv, arithmetic, mixtures → Ch 13
- Maxent, Burg, exponential families → Ch 12
- Mutual information / KL → Ch 2
- Networks, Slepian–Wolf, Wyner–Ziv → Ch 15
- Portfolios, Kelly, growth rate → Ch 6, 16
- Rate distortion, quantization → Ch 10
- Separation theorem → Ch 7
- Source coding lossless → Ch 3, 5
- Sufficient statistics → Ch 2
- Universal coding / redundancy=capacity → Ch 11, 13
- Waterfilling / reverse waterfill → Ch 9, 10

## How to use this skill

- **Verify a statement** → [theorems.md](theorems.md) then the chapter file.
- **Grab a formula** → [cheatsheet.md](cheatsheet.md).
- **Look up a term** → [glossary.md](glossary.md).
- **Need proof structure** → chapter “Frameworks and Methods” + “Key Results”.
- **Agent / coding use of IT** (compaction, KL routing, bits-back) → map to H, D, I, AEP; do not invent operational claims that violate DPI or Fano.

## Chapter files

- [ch01-introduction-and-preview.md](chapters/ch01-introduction-and-preview.md)
- [ch02-entropy-relative-entropy-mutual-information.md](chapters/ch02-entropy-relative-entropy-mutual-information.md)
- [ch03-asymptotic-equipartition-property.md](chapters/ch03-asymptotic-equipartition-property.md)
- [ch04-entropy-rates-stochastic-process.md](chapters/ch04-entropy-rates-stochastic-process.md)
- [ch05-data-compression.md](chapters/ch05-data-compression.md)
- [ch06-gambling-and-data-compression.md](chapters/ch06-gambling-and-data-compression.md)
- [ch07-channel-capacity.md](chapters/ch07-channel-capacity.md)
- [ch08-differential-entropy.md](chapters/ch08-differential-entropy.md)
- [ch09-gaussian-channel.md](chapters/ch09-gaussian-channel.md)
- [ch10-rate-distortion.md](chapters/ch10-rate-distortion.md)
- [ch11-information-theory-and-statistics.md](chapters/ch11-information-theory-and-statistics.md)
- [ch12-maximum-entropy.md](chapters/ch12-maximum-entropy.md)
- [ch13-universal-source-coding.md](chapters/ch13-universal-source-coding.md)
- [ch14-kolmogorov-complexity.md](chapters/ch14-kolmogorov-complexity.md)
- [ch15-network-information-theory.md](chapters/ch15-network-information-theory.md)
- [ch16-information-theory-and-portfolio-theory.md](chapters/ch16-information-theory-and-portfolio-theory.md)
- [ch17-inequalities-in-information-theory.md](chapters/ch17-inequalities-in-information-theory.md)

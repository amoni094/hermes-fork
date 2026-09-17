# Chapter 1: Introduction and Preview

## Core Idea
Information theory answers two questions: the ultimate data-compression limit is entropy H, and the ultimate reliable communication rate is channel capacity C. Those two quantities, plus relative entropy, mutual information, and later differential entropy, organize the whole subject — physics, statistics, computer science, and gambling included.

## Key Concepts
- **Entropy H**: the ultimate compressed description length of a random variable (bits if log is base 2).
- **Channel capacity C**: logarithm of the number of distinguishable n-length signals, growing as 2^{nC}; equivalently C = max_{p(x)} I(X;Y).
- **Typical set**: for i.i.d. sequences, about 2^{nH} sequences each of probability about 2^{-nH} carry almost all the probability (AEP).
- **Mutual information I(X;Y)**: reduction in uncertainty of X given Y; the information-theoretic distance between the joint and the product of the marginals.
- **Rate distortion R(D)**: minimum bits per symbol needed to describe a source within average distortion D.
- **Kolmogorov complexity K(x)**: length of the shortest program that prints x; probability-free cousin of entropy.
- **Network information theory**: many senders/receivers; interference, cooperation, feedback; capacity *regions* rather than a single number.

## Frameworks and Methods
- **Two-question framing**: every later chapter is either a compression problem (source coding, AEP, rate-distortion, Kolmogorov, universal codes) or a transmission problem (channels, Gaussian, networks), or a dual (gambling, portfolios).
- **Typical-set method**: prove coding theorems by restricting attention to jointly typical sequences and counting them.
- **Orthogonal-to-technique stance**: fundamentals (H, I, C, R(D)) are independent of the engineering used to approach them; proofs first, codes later.
- **Duality**: data compression vs channel coding; horse-race growth vs entropy; Slepian–Wolf vs multiple-access.

## Key Results and Theorems
This chapter states the program, not the proofs.

- **Source coding (preview)**: n i.i.d. draws of X can be compressed to about nH(X) bits with vanishing error; fewer bits is impossible.
- **Channel coding (preview)**: n uses of a DMC admit about 2^{nC} reliably distinguishable messages, C = max_{p(x)} I(X;Y).
- **Rate-distortion (preview)**: describing X to distortion D requires R(D) = min I(X;X̂) bits subject to E d(X,X̂) ≤ D.
- **AEP (preview)**: −(1/n) log p(X^n) → H(X) in probability.

## Key Equations
- H(X) = −∑ p(x) log p(x)
- I(X;Y) = H(X) − H(X|Y) = D(p(x,y) || p(x)p(y))
- C = max_{p(x)} I(X;Y)
- |A_ε^{(n)}| ≈ 2^{nH}, P(A_ε^{(n)}) → 1

## Worked Example
Fair coin: H(X) = 1 bit, so n flips need ~n bits. Biased coin with P(Heads)=0.11 has H ≈ 0.5 bits, so n flips compress to ~n/2 bits. A BSC with crossover p has C = 1 − H(p); at p=0.11, C ≈ 0.5 bits per use. The numerical coincidence is pedagogical, not a duality identity.

## Anti-patterns
- **Treating IT as only communication theory**: Cover–Thomas insist it also governs thermodynamics, Kolmogorov complexity, hypothesis testing, and investment.
- **Confusing typical with high-probability-and-small**: the smallest high-probability set has size ~2^{nH}, same order as the typical set, but they are not identical for finite n.
- **Seeking zero-error capacity first**: ordinary capacity allows vanishing (not zero) error; zero-error capacity is a harder combinatorial object (Ch 7).

## Key Takeaways
1. H is the compression limit; C is the transmission limit; both are operational.
2. Mutual information is the common currency connecting sources, channels, statistics, and gambling.
3. Joint typicality plus counting is the standard proof engine for the three Shannon theorems.
4. Later chapters add process rates (Ch 4), continuous alphabets (Ch 8–9), distortion (Ch 10), types (Ch 11), networks (Ch 15).

## Connects To
- **Ch 2**: makes H, D, I rigorous.
- **Ch 3–5**: AEP then noiseless coding.
- **Ch 7, 9**: C for DMC and Gaussian.
- **Ch 10**: lossy analogue of Ch 5.
- **Ch 14–16**: complexity, networks, portfolios — the “much more than communication” claim.

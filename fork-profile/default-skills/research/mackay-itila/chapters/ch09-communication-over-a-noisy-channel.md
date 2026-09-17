# Chapter 9: Communication over a Noisy Channel

## Core Idea
The information a channel conveys is the mutual information I(X;Y), not “bits sent minus flips”. Capacity C = max_{P(x)} I(X;Y) is the highest rate at which the noisy channel can be made to behave like a noiseless one. Optimal decoding is Bayesian inference of the input given the output.

## Frameworks Introduced
- **Separation picture**: compress the source to a nearly fair bit stream, then add *designed* redundancy for the channel. Do not keep the source’s native redundancy.
- **Discrete memoryless channel (DMC)**: P(y|x) applied independently each use. Specified by a transition matrix.
- **Information conveyed**: I(X;Y)=H(X)−H(X|Y)=H(Y)−H(Y|X).
- **Optimal decoder**: argmax_x P(x|y) = argmax_x P(y|x)P(x). For equiprobable codewords, ML: argmax P(y|x).
- **Preview of the coding theorem**: random codes of rate R<C succeed with high probability because jointly typical (x,y) pairs isolate the sent codeword.

## Key Concepts
- **Binary symmetric channel**: P(y≠x)=f. C=1−H2(f).
- **Binary erasure channel (BEC)**: y∈{0,1,e}, erasure prob ε. C=1−ε.
- **Z channel**: 0→0 always; 1→0 with probability f. Capacity-achieving P(x) is *not* 1/2.
- **Noisy typewriter**: each letter confusable with neighbours; capacity = log2(of a non-confusable subset).
- **H(X|Y) as noise entropy**: remaining uncertainty about the input after seeing the output.
- **Rate**: not the raw symbol rate; after coding it is K information bits per N channel uses.

## Key Equations
- P(x|y) ∝ P(y|x) P(x)
- I(X;Y) = sum_{x,y} P(x,y) log2 [P(y|x)/P(y)]
- C = max_{P(x)} I(X;Y)
- BSC: C=1−H2(f)
- BEC: C=1−ε
- For a channel used N times, I(X^N;Y^N) ≤ N C

## Algorithms and Techniques
**Compute C for a small DMC**
1. Parameterize P(x) (e.g. p=P(x=1) for binary input).
2. Form P(y)=sum_x P(x)P(y|x), then I(p).
3. Maximize I(p) by calculus or grid search. At the maximum, the “information content of each output” is constant (Blahut–Arimoto / Kuhn–Tucker).

**MAP decoding of a single transmission**
1. For each possible input symbol, compute P(y|x)P(x).
2. Pick the maximizer; report posterior if you need reliability.

## Mental Models
- Do not subtract error counts from bit counts: when f=0.5, 50% of bits are “correct” and information is *zero*.
- Think of encoding as choosing a needle in {0,1}^N so that the channel’s typical noise ball rarely hits another needle.
- Use BEC intuition: erasures are known locations, so C=1−ε is “just send the non-erased bits”; BSC is harder because you do not know which bits flipped.

## Worked Example
1000 bits/s over BSC(f=0.1). Naive guess: 900 information bits/s. Wrong.
- Uncoded I(X;Y)=1−H2(0.1)≈0.531 bits per use if P(x)=1/2.
- So raw transmission conveys ~531 bits/s of mutual information, not 900, and *without coding you cannot recover the original 1000 bits*.
- With coding at R=0.5<0.531, Ch 10 says vanishing error is possible; at R=0.9>C it is not, even though 0.9<0.9 (the naive 900/1000).

Z-channel with f=0.5: optimal input is biased toward the unflippable symbol 0; putting P(x=1)=1/2 leaves capacity on the table.

## Anti-patterns
- **Keeping uncompressed redundancy “for protection”**: source redundancy is the wrong code for the channel.
- **ML decoding when codewords are not equiprobable**.
- **Assuming binary-input capacity-achieving distribution is always fair** (false for Z channel).
- **Confusing mutual information of the uncoded channel with achievable reliable rate without codes**: I is an average information measure; vanishing error needs block coding.

## Key Takeaways
1. Information through a channel is I(X;Y); capacity is its maximum over input distributions.
2. Optimal receivers are Bayesian.
3. Compress first, then channel-code.
4. f=0.5 BSC (or any channel with I=0) transmits nothing, however large the baud rate.
5. Compute C before you design a code.

## Connects To
- **Ch 1**: informal capacity picture.
- **Ch 8**: I(X;Y) definitions.
- **Ch 10**: theorem and jointly typical sets.
- **Ch 11**: real codes vs Gaussian channels.

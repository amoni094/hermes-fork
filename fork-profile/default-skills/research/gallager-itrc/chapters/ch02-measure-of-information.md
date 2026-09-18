# Chapter 2: A Measure of Information

## Core Idea
Mutual information I(X;Y) is the unique natural measure of how much observing Y reduces uncertainty about X in a probabilistic ensemble. Entropy H(X) is self-information of X; channel coding and source coding are both theorems about this quantity.

## Key Concepts
- Ensemble / sample space: a set of alternatives with a probability measure. Discrete ensembles are finite or countable; continuous ensembles are specified by densities.
- Self-information of event a: I(a) = −ln P(a) (natural units, nats). Rare events carry more information.
- Mutual information of a pair (x, y): I(x; y) = ln [P(x,y) / (P(x)P(y))] = ln [P(y|x)/P(y)]. Positive when the pair is more likely jointly than independently.
- Average mutual information: I(X;Y) = E[I(x;y)] = ∑_{x,y} P(x,y) ln [P(x,y)/(P(x)P(y))].
- Entropy: H(X) = −∑ P(x) ln P(x) = I(X;X). Conditional entropy H(X|Y) = H(X) − I(X;Y).
- Chain rules: H(X,Y) = H(X) + H(Y|X); I(X;Y) = H(X) − H(X|Y) = H(Y) − H(Y|X).
- Continuous ensembles: differential entropy h(X) = −∫ p(x) ln p(x) dx is not an absolute information measure (it shifts under coordinate changes); I(X;Y) remains well-defined and invariant.
- Arbitrary ensembles: Gallager extends I(X;Y) via partitions and limits so that mixed discrete/continuous alphabets are covered.

## Frameworks and Methods
- Information as a random variable: I(x;y) fluctuates; theorems about coding use both the mean I(X;Y) and concentration (later Chernoff bounds in Ch 5).
- Units: natural logs → nats; log2 → bits. Capacity and exponents in this book are usually in nats; convert by dividing by ln 2 for bits.
- Convexity preview: I(X;Y) is concave in the input distribution P(x) for fixed P(y|x), convex in the channel for fixed P(x). This is why capacity is a maximum over inputs and why random coding exponents are optimizable (Ch 4–5).
- Continuous-from-discrete: obtain densities as limits of quantized ensembles; never treat h(X) as “the” information in a waveform.

## Key Results and Theorems
- Nonnegativity: I(X;Y) ≥ 0 with equality iff X and Y are independent.
- Data-processing: if X → Y → Z is a Markov chain, I(X;Z) ≤ I(X;Y). Processing cannot create mutual information.
- Entropy bounds: 0 ≤ H(X) ≤ ln |alphabet|, equality on the right iff letters are equiprobable.
- Conditioning reduces entropy: H(X|Y) ≤ H(X).
- Continuous mutual information: I(X;Y) = ∫∫ p(x,y) ln [p(x,y)/(p(x)p(y))] dx dy when the integral exists.
- Interpretation for channels: I(X;Y) is the information transferred per use when X ~ Q and the channel is P(y|x). Capacity will be C = max_Q I(Q; P).
- Interpretation for sources: H(X) is the information produced per letter; it will be the minimum compression rate.

## Algorithms and Techniques
1. Specify the joint P(x,y) or the pair (Q(x), P(y|x)).
2. Compute P(y) = ∑_x Q(x) P(y|x) (or the density analog).
3. Evaluate I(X;Y) = ∑_{x,y} Q(x)P(y|x) ln [P(y|x)/P(y)].
4. For entropy, set Y = X or use −∑ Q ln Q.
5. For continuous alphabets, discretize finely enough that I(X;Y) converges; do not report differential entropy as an operational rate without a distortion or power constraint.

## Anti-patterns
- Calling −log P(x) “information” in a non-probabilistic setting.
- Confusing differential entropy with discrete entropy: h(X) can be negative; H(X) cannot.
- Maximizing I(X;Y) over the channel instead of the input: the designer chooses Q, not P(y|x).
- Using log2 in one place and ln in another without converting R, C, and E_r(R) consistently.
- Assuming I(X;Y) is the error exponent. The mean I is capacity; the large-deviations behavior of I(x;y) produces E_r(R).

## Key Takeaways
1. I(X;Y) is the primitive; H and C are special cases / maxima of it.
2. Mutual information is an expectation of a log-likelihood ratio — the same LR that maximum-likelihood decoding uses.
3. Continuous channels are handled by the same I, not by a new “analog information.”
4. Convexity of I in the channel and concavity in the input are the analytic engine of Ch 4–5.

## Connects To
- Ch 1: supplies the measure promised in the system model.
- Ch 3: H becomes the source-coding rate.
- Ch 4: C = max I(X;Y); converse uses Fano-type reasoning on H(message | output).
- Ch 5: E_0(ρ, Q) deforms I; at ρ → 0, ∂E_0/∂ρ = I(Q;P).
- Ch 7–8: same I for densities and Gaussian processes.
- Ch 9: R(d*) is a minimized I(X;X̂) subject to a distortion constraint.

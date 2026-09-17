# Chapter 1: Communication Systems and Information Theory

## Core Idea
Information theory is a quantitative theory of encoding for probabilistic sources and channels. The central engineering claim is that a source of entropy H can be transmitted over a channel of capacity C with arbitrarily small error if and only if H < C, at the cost of delay and complexity.

## Key Concepts
- Discrete source: a random sequence of letters from a finite alphabet, specified by joint probabilities on blocks.
- Entropy H: the average self-information of a source letter (or letter per unit time). Gallager treats H as the fundamental rate at which the source produces information, later identified with the minimum number of code letters per source letter.
- Channel: a probabilistic mapping from input sequences to output sequences. Memoryless means successive uses are independent given the inputs.
- Capacity C: the supremum of rates at which information can be transmitted with arbitrarily small error probability by coding of sufficiently long block length.
- Source coding vs channel coding: source coding removes redundancy so that representation uses about H nats (or bits) per letter; channel coding adds controlled redundancy so that noise can be corrected at rates below C.
- Block length N and rate R: an (N, R) block code has about e^{NR} code words of length N (natural units). Error probability is a function of N, R, and the channel.
- Fidelity criterion: for analog or continuous sources, “perfect” reconstruction is impossible; the right figure of merit is average distortion (developed in Ch 9).

## Frameworks and Methods
- Probabilistic modeling: replace physical sources/channels by ensembles. The theory is only as good as the model; atypical rare events dominate error rates.
- Encoder–channel–decoder: encoder maps messages (or source blocks) into channel inputs; decoder maps outputs to estimated messages.
- Separation of source and channel coding: first compress to rate just above H, then protect with a channel code of rate just below C. Justified later (Ch 4 converse, Ch 5 coding theorem, Ch 9 rate-distortion).
- Asymptotics in block length: reliability is an exponential function of N, not a property of clever one-shot mappings.

## Key Results and Theorems
- Source coding (preview of Ch 3): if H is the source entropy, the source can be represented by slightly more than H nats per letter with vanishing failure probability (fixed-length) or with unique decodability (variable-length).
- Noisy-channel coding (preview of Ch 5): for any discrete memoryless channel there is a capacity C such that for every R < C there exist codes with P_e ≤ exp(−N E_r(R)) and E_r(R) > 0; for R > C, P_e cannot be made small.
- Joint source–channel: reliable transmission is possible when the source information rate is less than C. If a source requires rate R(d*) to meet distortion d*, then d* is achievable over the channel iff R(d*) < C (Ch 9).
- Practical bottleneck: finding codes is not the hard part (random codes work); implementing encoding and decoding without exponential storage is the hard part (Ch 6).

## Algorithms and Techniques
1. Model the source (alphabet, statistics, stationarity/Markov).
2. Model the channel (input/output alphabets, P(y|x), memory or not).
3. Choose a coding architecture: block vs convolutional; detect-and-retransmit vs forward error correction.
4. Set the operating rate R with H < R < C (or R(d*) < C).
5. Increase block length (or constraint length) until P_e meets the spec; budget delay and decoder complexity.

## Anti-patterns
- Treating “information” as a universal semantic quantity. Gallager’s measures apply only to probabilistic communication models.
- Optimizing modulation in isolation and then hoping coding will “clean up.” Capacity and error exponents are properties of the coded channel, not of uncoded symbol error rate alone.
- Assuming short, unstructured codes can approach C. Unstructured ML decoding costs exponential storage in N.
- Spending a one-semester course on Ch 3 at the expense of Ch 5–6. Gallager warns that the noisy-channel theorem and implementable codes are the engineering core.
- Ignoring delay: vanishing P_e requires N → ∞.

## Key Takeaways
1. H and C are operational: they are the limits of compression and of reliable transmission, not merely formulas.
2. Error probability decays exponentially in N below capacity; the exponent, not C alone, governs finite-length reliability.
3. The theory separates what is possible (random coding) from what is instrumentable (parity-check, convolutional, sequential decoding).
4. Continuous sources need a distortion measure; “lossless” is the special case of a discrete source with zero-distortion.

## Connects To
- Ch 2: defines I(X;Y) and H so that C = max I(X;Y) is meaningful.
- Ch 3: makes H operational via source coding.
- Ch 4–5: make C operational via converse and random-coding bound.
- Ch 6: implementable codes whose P_e still tracks E_r(R).
- Ch 7–8: the same theorems for Gaussian and waveform channels.
- Ch 9: rate-distortion R(d*) as the source-coding analog of capacity.

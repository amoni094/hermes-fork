# Chapter 6: Stream Codes

## Core Idea
Compression *is* probabilistic modelling plus coding. Arithmetic coding turns any sequential model P(x1), P(x2|x1), … into a compressor whose length is −log2 P(x) + O(1) bits — arbitrarily close to the Shannon information content. Lempel–Ziv is the universal alternative that learns repetitions without an explicit model, but only becomes optimal at unfeasible data sizes.

## Frameworks Introduced
- **The guessing game**: a human (or model) guesses the next character until correct; the guess-count sequence is a sufficient statistic and is highly compressible (often a stream of 1s). Demonstrates English redundancy and that a predictor is a compressor.
- **Arithmetic coding**: maps a sequence to a subinterval of [0,1) whose width is P(x); the binary expansion of any point in that interval is the code.
- **Lempel–Ziv (LZ78 / gzip-style)**: parse into unseen phrases, emit (pointer to prefix, new symbol). Universal for ergodic sources in the infinite-N limit.

## Key Concepts
- **Sequential (adaptive) model**: after seeing x_<n, the model produces P(xn | x_<n). Arithmetic coding needs only this.
- **Interval invariant**: start with [0,1); for each symbol, shrink to the subinterval corresponding to that symbol’s cumulative probability.
- **Termination / unique decodability**: emit enough bits to distinguish the final interval from its neighbours (≈ −log2 P(x) + 2 bits).
- **Modelling vs coding**: arithmetic coding is “just” the coder; all the intelligence is in the model (context-mixing, PPM, CTW in later literature).
- **Redundancy of English**: letter frequencies, bigrams, words, semantics — guessing game numbers: many 1s, spikes at syllable onsets.

## Key Equations
- P(x1..xN) = P(x1) P(x2|x1) … P(xN|x_<N)
- Final interval width = P(x)
- Code length l(x) < log2 1/P(x) + 2
- Expected length L < H + 2  (for a perfect model)
- If model is Q: L ≈ H(P) + DKL(P||Q) + O(1)

## Algorithms and Techniques
**Arithmetic encoding**
1. lo←0, hi←1.
2. For each symbol a with range [F(a), F(a)+p(a)) under the current conditional:
   w ← hi−lo; hi ← lo + w·(F(a)+p(a)); lo ← lo + w·F(a).
3. After the last symbol, emit a binary fraction in [lo,hi) long enough to uniquely identify it.
4. Practical implementations renormalize (emit bits, rescale) to avoid underflow; use integer arithmetic.

**Arithmetic decoding**: invert the same interval splits using the received bits as the target point.

**LZ78 sketch**
1. Dictionary starts empty / with alphabet.
2. Find longest prefix of remaining input already in the dictionary; emit its index plus the next novel symbol; insert the new phrase.

## Mental Models
- Use arithmetic coding whenever you have (or can learn) P(next|context).
- Use LZ when you want a general-purpose tool and the source has repeated strings (source code, English), accepting suboptimality on small files.
- Think of the guessing game as: the guess counts are the data; a good language model makes them almost all ones, hence tiny entropy.

## Worked Example
Source symbols {a,b} with P(a)=2/3, P(b)=1/3, encode “aba”.
- Start [0,1). a → [0, 2/3). Next a would be [0, 4/9); we have b: within [0,2/3), b occupies [4/9, 2/3). Then a occupies the first 2/3 of that: [4/9, 4/9+(2/3)(2/9)] = [4/9, 16/27).
- Width = P(aba)=(2/3)(1/3)(2/3)=4/27, −log2(4/27)≈2.75 bits. Emit ~3–4 bits naming a point in [4/9, 16/27) ≈ [0.444, 0.593], e.g. 0.5 = 0.1 binary, plus disambiguation bits.

Guessing game on “THERE IS NO REVERSE ON A MOTORCYCLE”: many letters cost 1 guess; R in REVERSE cost 15, V cost 17 — the high-information onsets.

## Anti-patterns
- **Huffman on characters of English** and calling it done: ignores dependence; arithmetic+context model wins.
- **Claiming gzip is entropy-optimal** for short documents.
- **Floating-point arithmetic coding without renormalization**: precision collapse.
- **Forgetting the model is the compressor**: a wrong model + perfect arithmetic still wastes DKL bits.

## Key Takeaways
1. Any sequential probability model is a compressor via arithmetic coding.
2. Length = −log2 P_model(x) + O(1); extra cost is DKL to the true source.
3. LZ is universal but slow to converge; great as a baseline, not as a bound-achiever.
4. The guessing game is both a demo of English redundancy and a recipe (guess-counts as a transformed source).
5. Source coding theorem is now constructive.

## Connects To
- **Ch 4–5**: H and Huffman as the integer-length special case.
- **Ch 3**: Bayesian adaptive models feed the same coder.
- **Ch 28**: MDL / evidence ≈ compressed length.
- **Ch 16, 26**: message passing can compute the conditionals a model needs.

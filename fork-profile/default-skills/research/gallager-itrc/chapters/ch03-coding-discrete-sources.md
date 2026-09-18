# Chapter 3: Coding for Discrete Sources

## Core Idea
The entropy H of a discrete source is exactly the minimum number of code letters (in logarithmic units of the code alphabet) needed per source letter for essentially lossless representation. Huffman coding meets the bound for independent letters; extensions and Markov structure handle dependence.

## Key Concepts
- Code alphabet of size D: encoded sequence uses D-ary letters; the ideal rate is H / ln D letters per source letter (H in nats).
- Fixed-length codes: map source n-blocks to D-ary blocks of length m. Fail with small probability if some source blocks are unrepresented.
- Variable-length codes: map letters (or blocks) to D-ary strings of unequal length. Need unique decodability (preferably prefix-free).
- Kraft inequality: for a prefix (or uniquely decodable) D-ary code with lengths ℓ_i, ∑ D^{−ℓ_i} ≤ 1. Conversely, any lengths satisfying Kraft are realizable by a prefix code.
- Instantaneous / prefix code: no code word is a prefix of another; can decode as soon as a word ends.
- Huffman procedure: an optimal prefix code (minimizes average length) constructed by iteratively merging the two least probable symbols.
- Discrete stationary source: shift-invariant letter statistics; entropy rate H_∞ = lim H(X_1…X_n)/n exists.
- Markov source: next letter depends only on a finite state; entropy rate is the average of H(letter | state).

## Frameworks and Methods
- Typicality intuition: about e^{nH} source n-blocks carry almost all probability. Fixed-length coding of those blocks uses about nH / ln D letters.
- Length as self-information: choosing ℓ_i ≈ −log_D P_i makes average length ≈ H / ln D. Integer constraints cost at most 1 letter (or 1/n after blocking).
- Blocking: encode n-tuples to drive the overhead 1/n → 0 and to exploit dependence.
- Unique decodability vs prefix: Kraft–McMillan says uniquely decodable codes cannot beat prefix codes in average length.

## Key Results and Theorems
- Source coding theorem (fixed-length): for a discrete memoryless source of entropy H, for any ε > 0, there exist fixed-length codes with rate < (H/ln D) + ε and failure probability → 0 as n → ∞. If the rate is below H/ln D, failure probability ↛ 0.
- Variable-length bound: any uniquely decodable code satisfies L ≥ H / ln D. There exist prefix codes with H / ln D ≤ L < H / ln D + 1.
- Huffman optimality: among D-ary prefix codes for a given distribution, Huffman minimizes L. After encoding n-blocks, L/n → H / ln D.
- Stationary sources: the same theorems hold with H replaced by the entropy rate H_∞.
- Markov sources: H_∞ = ∑_s π(s) H(X | S = s). Encoding can be done state-conditionally or by blocking.

## Algorithms and Techniques
Huffman algorithm (binary, D = 2):
1. List symbol probabilities.
2. Merge the two smallest into a new symbol whose probability is the sum; record the merge as a sibling pair in the tree.
3. Repeat until one symbol remains.
4. Read code words off the tree (edges 0/1). Lengths satisfy Kraft with equality if the tree is complete.

Fixed-length typical-set coding:
1. Form n-blocks. Keep the most probable M blocks, M ≈ exp(n(H+ε)).
2. Number them with binary (or D-ary) indices.
3. Declare failure on the complement. P(failure) → 0.

Markov / stationary:
1. Estimate entropy rate from conditional distributions.
2. Encode n-blocks (or use conditional Huffman given state).

## Anti-patterns
- Using Huffman on single letters of a highly dependent source: L tracks H(X_1), not H_∞. Block first.
- Treating Huffman as “the” source-coding theorem. It is an algorithm achieving a bound; the theorem is about existence/limits.
- Forgetting integer-length overhead: without blocking, up to 1 extra letter per symbol.
- Assuming unique decodability without Kraft. Comma-free hacks can fail on concatenation.
- Applying lossless methods to analog sources. Use Ch 9 distortion; quantization is a distortion code, not Huffman on samples with infinite entropy.

## Key Takeaways
1. Entropy is an operational compression rate.
2. Kraft is the geometry of prefix codes; Huffman is the optimal integer-length solution.
3. Dependence is handled by entropy rate plus blocking, not by a new measure.
4. Source coding is the easy, clean half of the book; the noisy channel is where exponential error bounds and implementation matter.

## Connects To
- Ch 2: H is the quantity being achieved.
- Ch 1: this is the source-coding half of H < C.
- Ch 4: the converse to channel coding uses the same entropy inequalities.
- Ch 9: rate-distortion is source coding with a fidelity criterion; lossless is d = 0 on a discrete alphabet.
- Ch 6: compressed bits become the “information digits” of a parity-check or convolutional encoder.

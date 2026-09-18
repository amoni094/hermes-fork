# Chapter 5: Symbol Codes

## Core Idea
A symbol code assigns a binary string to each alphabet symbol. Instantaneous (prefix) codes exist with expected length L arbitrarily close to H(X), and no uniquely decodeable code can beat H(X). Huffman coding constructs an optimal prefix code for a known discrete distribution; the leftover gap is at most 1 bit per symbol.

## Frameworks Introduced
- **Symbol code**: encoder c: AX → {0,1}^+, length li = |c(ai)|, expected length L = sum pi li.
- **Kraft–McMillan inequality**: a uniquely decodeable code with lengths {li} exists iff sum_i 2^{−li} ≤ 1. Equality ⇔ complete prefix code (dyadic).
- **Shannon–Fano bound**: there exist prefix codes with H(X) ≤ L < H(X)+1, by setting li = ⌈log2 1/pi⌉.
- **Huffman algorithm**: optimal among symbol codes (minimizes L). Not optimal among all compressors — block/stream codes can do better per original symbol.

## Key Concepts
- **Prefix (instantaneous) code**: no codeword is a prefix of another; can decode as soon as a codeword ends, without lookahead.
- **Uniquely decodeable**: the concatenation map is injective; prefix ⇒ unique, but not conversely (e.g. some suffix codes).
- **Self-delimiting**: prefix codes are self-delimiting.
- **Ternary/D-ary Huffman**: same algorithm with D-ary trees; pad alphabet so (I−1) is divisible by (D−1).
- **Redundancy** L − H(X): wasted bits due to integer-length constraint and to model error.

## Key Equations
- L(C,X) = sum_i pi li
- Kraft: sum_i D^{−li} ≤ 1  for D-ary uniquely decodeable codes
- Shannon code: li = ⌈log2 1/pi⌉  ⇒  H ≤ L < H+1
- Huffman optimality: L_Huffman ≤ L_any-symbol-code
- For a dyadic distribution (pi=2^{−li}), Huffman achieves L=H exactly

## Algorithms and Techniques
**Huffman coding**
1. List the symbols with their probabilities as leaves.
2. Repeatedly merge the two smallest probabilities into a parent with weight p+q; assign 0/1 to the two branches.
3. Read codewords off the path from root to leaf.
4. Ties: any choice is optimal for L; different choices change individual li and variance.

**Shannon–Fano (not always optimal)**
1. Set li=⌈log2 1/pi⌉.
2. Assign those lengths any prefix set satisfying Kraft (e.g. via Shannon–Fano–Elias on cumulative probabilities).

**Verify unique decodability**
1. Check prefix property, or
2. Check Kraft sum ≤ 1 (necessary; sufficient for existence of *some* UD code with those lengths).

## Mental Models
- Think of a prefix code as a full binary tree; Kraft says the leaf “areas” 2^{−li} fit in the unit interval.
- Use Huffman when N=1 (one symbol at a time) and the alphabet is modest and static.
- Use block Huffman on pairs/triples when you need to close the +1-bit gap without arithmetic coding.
- Think of the extra <1 bit as “you cannot send a fraction of a bit in a symbol code”.

## Worked Example
Ensemble AX={a,b,c,d} with PX={1/2, 1/4, 1/8, 1/8}. H=1.75 bits.
- Shannon lengths: 1,2,3,3. Huffman tree: a=0, b=10, c=110, d=111. L=1.75=H. Perfect because dyadic.
- If PX={0.4, 0.3, 0.2, 0.1}, H≈1.85. Huffman: e.g. 0, 10, 110, 111 or 00, 01, 10, 11 depending on tie-breaking. L≈1.9, redundancy ~0.05 < 1.

English letters: Huffman on monograms gets L slightly above H(monogram)≈4.1 bits/char, far above the true English entropy (~1–2 bits/char) because it ignores dependence (Ch 2 bigrams, Ch 6).

## Anti-patterns
- **Huffman on a bad model** (wrong pi): you can do worse than a simple fixed-length code; DKL(P||Q) is the extra cost of using Q-code on P-data.
- **Calling Huffman “optimal compression”**: it is optimal among *symbol* codes for a known distribution, not among compressors.
- **Forgetting to pad for D-ary Huffman**.
- **Using Huffman for tiny alphabets with huge blocks** — the tree of |A|^N leaves explodes; switch to arithmetic / ANS (Ch 6).
- **Non-prefix codes without a unique-decodability proof**.

## Key Takeaways
1. Kraft is the existence condition; Huffman is the construction that minimizes L.
2. H ≤ L_Huffman < H+1 for one-shot symbol codes.
3. To beat the +1 gap, code blocks or use stream codes.
4. Match the code to the true distribution; model error costs DKL bits.
5. Prefix ⇒ online decodable; that is what you want for concatenation.

## Connects To
- **Ch 4**: H is the target L cannot beat.
- **Ch 6**: arithmetic coding closes the integer-length gap.
- **Ch 7**: codes for integers (unbounded alphabets).
- **Ch 2**: DKL as extra length when the code assumes the wrong P.

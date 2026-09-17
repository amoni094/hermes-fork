# Chapter 5: Data Compression

## Core Idea
The shortest expected description length of a discrete random variable is essentially its entropy: for instantaneous (and uniquely decodable) D-ary codes, L ≥ H_D(X), and Shannon / Huffman codes come within 1 bit (or 1/n bits per symbol for blocks). Kraft’s inequality is the geometry of prefix codes.

## Key Concepts
- **Source code**: map x ↦ C(x) ∈ D^*, length l(x). Expected length L = ∑ p(x) l(x).
- **Nonsingular**: injective on single symbols.
- **Uniquely decodable**: the extension C(x1)...C(xn) is injective on strings.
- **Prefix / instantaneous code**: no codeword is a prefix of another; self-punctuating.
- **Kraft inequality**: ∑ D^{−l_i} ≤ 1; necessary and sufficient for existence of a prefix code with those lengths (also necessary for uniquely decodable: McMillan).
- **D-adic distribution**: p_i = D^{−n_i}; equality L = H_D iff p is D-adic and l_i = −log_D p_i.
- **Huffman code**: greedy merge of two least probable symbols; optimal among UD codes.
- **Shannon code**: l(x) = ⌈log (1/p(x))⌉.
- **Shannon–Fano–Elias**: code by truncated modified CDF F̄(x); lengths ⌈log(1/p(x))⌉+1; arithmetic-coding ancestor.
- **Wrong-code penalty**: using q instead of p costs D(p||q) extra bits.

## Frameworks and Methods
- **Kraft as tree packing**: each codeword of length l occupies D^{−l} of the unit interval / leaf budget.
- **Lagrange / information inequality for optimality**: minimize ∑ p_i l_i s.t. ∑ D^{−l_i} ≤ 1 yields l_i ≈ log_D (1/p_i).
- **Block to kill the +1**: encode n-tuples so overhead 1/n → 0, thus L_n^*/n → H.
- **Huffman optimality proof**: sibling property + exchange argument; local greedy = global optimal.
- **Competitive optimality**: Shannon lengths beat any other UD lengths more often than they lose (dyadic case).

## Key Results and Theorems

**Theorem 5.2.1 (Kraft).** Instantaneous D-ary codes satisfy ∑_i D^{−l_i} ≤ 1. Conversely, lengths satisfying Kraft are realized by some prefix code. Extended Kraft (Thm 5.2.2) holds for countably infinite prefix codes.

**Theorem 5.3.1.** Any instantaneous D-ary code has L ≥ H_D(X), equality iff p_i = D^{−l_i}.
Proof: L − H_D = D(p || q) + log_D (∑ D^{−l_i}) ≥ 0 with q_i ∝ D^{−l_i}.

**Theorem 5.4.1 (Shannon code bounds).** Optimal lengths satisfy
H_D(X) ≤ L^* < H_D(X) + 1.

**Theorem 5.4.2 (Block coding).** H(X^n)/n ≤ L_n^* < H(X^n)/n + 1/n.
For i.i.d., H ≤ L_n^* < H + 1/n.

**Theorem 5.4.3 (Wrong code).** If l(x) = ⌈log (1/q(x))⌉ then
H(p) + D(p||q) ≤ L < H(p) + D(p||q) + 1.

**Theorem 5.5.1 (McMillan).** Uniquely decodable codes also satisfy Kraft. Hence the UD and prefix length classes coincide; prefix codes lose nothing in expected length.

**Theorem 5.8.1.** Huffman coding is optimal: L(C_Huffman) ≤ L(C) for every UD C.

**Shannon–Fano–Elias.** l(x) = ⌈log(1/p(x))⌉ + 1 yields a prefix code via truncated F̄(x).

**Theorem 5.10.2 (Competitive optimality of Shannon lengths, dyadic p).**
Pr(l(X) < l'(X)) ≥ Pr(l(X) > l'(X)) for any other UD lengths l', equality iff l'=l.

**Generation of distributions (Section 5.11).** Generating a sample of X from fair coin flips requires (essentially) H(X) coin tosses; Knuth–Yao: expected flips < H(X)+2.

## Key Equations
- Kraft: ∑ D^{−l_i} ≤ 1
- L ≥ H_D(X)
- H ≤ L^* < H+1
- Wrong code: L ≈ H(p)+D(p||q)
- Huffman: merge two smallest probabilities, repeat

## Worked Example
X ∈ {a,b,c,d} with p = (1/2, 1/4, 1/8, 1/8). H=1.75 bits. Shannon/Huffman lengths (1,2,3,3), L=1.75 = H (dyadic). Huffman tree: merge c,d → 1/4, merge with b → 1/2, merge with a.

If you encode with q=(1/4,1/4,1/4,1/4), lengths all 2, L=2 = H+D(p||u) = 1.75+0.25.

## Anti-patterns
- **Comma codes without Kraft**: you can always uniquely decode with separators, but you pay more than H.
- **Huffman on a misspecified p**: optimality is with respect to the design distribution; mismatch costs ≈ D(p||q).
- **Claiming Huffman is unique**: only the length vector is optimal; several trees may share it.
- **Using Huffman for unknown or changing sources**: go to arithmetic / Lempel–Ziv (Ch 13).
- **Confusing unique decodability with prefix**: UD is weaker pointwise but equivalent for length exponents.

## Key Takeaways
1. Entropy is the operational expected-length limit.
2. Kraft is the only constraint; McMillan says UD ⇏ shorter than prefix.
3. The +1 bit dies by blocking.
4. Mismatch penalty is exactly relative entropy.
5. Huffman is optimal for known p; Shannon–Fano–Elias opens the door to arithmetic coding.

## Connects To
- **Ch 3**: typical-set coding also achieves H; here the bound is non-asymptotic and for one-shot X.
- **Ch 6**: a gambler with wealth growth W compresses at rate log m − W.
- **Ch 7**: duality — channel coding is packing, source coding is covering of probability.
- **Ch 10**: lossy compression; R(D) ≤ H with D=0 recovering this chapter.
- **Ch 13**: universal codes when p is unknown.

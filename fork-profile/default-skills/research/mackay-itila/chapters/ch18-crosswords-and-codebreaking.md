# Chapter 18: Crosswords and Codebreaking

## Core Idea
Language is a constrained channel plus a source code. Crossword grids and simple ciphers are inference problems: recover a high-probability English string consistent with local constraints. The same typical-set / language-model tools used for compression become attacks on substitution ciphers and a measure of crossword information content.

## Frameworks Introduced
- **Crosswords as constrained generation**: black-square pattern + dictionary + crossing letters. How much extra information do the crossings provide vs a stack of independent words?
- **Codebreaking as Bayesian inference**: ciphertext c, unknown key k, plaintext language model P(m). Posterior P(k|c) ∝ P(c|k) P(k) with P(c|k)=P_lang(k^{−1}(c)).
- **Unicity distance**: roughly n ≈ H(key)/D bits of ciphertext suffice to make the posterior concentrate, where D is the redundancy per character of English (≈ 1 − η bits if alphabet entropy is log|A| and true entropy is η).

## Key Concepts
- **Redundancy of English**: ≈ 1–2 bits/char true entropy vs log2 26≈4.7, or vs 27-ary with space. Guessing game (Ch 6) already measured this.
- **Substitution cipher**: key is a permutation of the alphabet; H(key)=log2(26!)≈88 bits. Unicity ≈ 88 / (4.7−1.5) ≈ 30 characters (order of magnitude).
- **Crossing constraints**: a crossword letter is typically determined by two words; the grid is an error-reducing code for language.
- **Dictionary attacks / frequency analysis**: first-order (ETAOIN) then bigram then word-list.

## Key Equations
- P(m | c) ∝ P_lang(m) 1[Enc_k(m)=c]
- Unicity n ≈ H(K) / D,  D = log|A| − H_lang  (redundancy per symbol)
- log2(26!) ≈ 88.4 bits
- I(grid; words) = H(words) − H(words | grid)  measures how much the pattern helps

## Algorithms and Techniques
**Simple substitution cryptanalysis**
1. Count ciphertext frequencies; align with English monograms (weak).
2. Score candidate keys by language-model log-likelihood of decoded text (bigrams/words).
3. Search: greedy swaps, MCMC on permutations (Ch 29 style), or dictionary pattern matching.
4. Stop when one plaintext has likelihood ≫ all others (unicity reached).

**Crossword fill as inference**
1. Factors: dictionary indicator per slot, equality factors at crossings.
2. Message passing / backtrack search. Information theoretically, crossings supply parity-like constraints.

## Mental Models
- A cipher is a channel with a secret parameter; language redundancy is the ECC that lets you recover the parameter.
- If your language model is weak, unicity distance grows — you need more ciphertext.
- Crosswords work because English is sparse in A^N; two intersecting dictionaries usually pin letters down.

## Worked Example
H(key)=88 bits for substitution. If English has 1.5 bits/char entropy and 4.7 bits/char raw, D≈3.2 bits/char, n≈88/3.2≈28 characters. That is why newspaper cryptograms of ~50 letters are usually unique, and 10-letter ones are not.

Crossword: two 5-letter crossing words, 9 letters of grid, vs 10 letters unconstrained. The shared letter is a 4.7-bit constraint that is usually consistent with few dictionary pairs — analogous to a parity check.

## Anti-patterns
- **Frequency analysis alone on short ciphertext**.
- **Assuming unicity distance is a guarantee of computational breakability** (one-time pad has H(K)≥H(M), D effectively unused).
- **Treating random-looking English (technical text) as having the same D as MacKay’s estimates**.
- **One-time pad with reused key**: becomes a substitution/Vigenère and falls to this chapter.

## Key Takeaways
1. Redundant sources make secret keys identifiable from enough ciphertext.
2. Unicity distance = H(key)/redundancy per symbol.
3. Crosswords are language plus equality constraints — a human LDPC.
4. Better language models (Ch 6) are better cryptanalytic scoring functions.
5. Perfect secrecy requires H(key) ≥ H(message) (Shannon), outside this chapter’s amateur-cipher regime.

## Connects To
- **Ch 6**: guessing game / English entropy.
- **Ch 17**: constraints as reduced capacity.
- **Ch 26, 47**: factor graphs with dictionary and equality factors.
- **Ch 29**: MCMC search over keys.

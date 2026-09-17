# Chapter 3: Asymptotic Equipartition Property

## Core Idea
The AEP is the information-theoretic WLLN: for i.i.d. X_i ~ p, −(1/n) log p(X^n) → H(X) in probability. Almost all probability mass sits on a typical set of size ≈ 2^{nH}, each sequence having probability ≈ 2^{−nH}. That counting fact is the engine of source coding.

## Key Concepts
- **AEP**: −(1/n) log p(X1,...,Xn) → H(X) in probability (not a.s.; a.s. needs SLLN / later Ch 16).
- **Typical set A_ε^{(n)}**: {x^n ∈ X^n : 2^{−n(H+ε)} ≤ p(x^n) ≤ 2^{−n(H−ε)}}.
- **Sample entropy**: −(1/n) log p(x^n), the empirical analog of H.
- **High-probability set B_δ^{(n)}**: smallest (or any) subset of X^n with P ≥ 1−δ.
- **an ≐ bn**: (1/n) log(an/bn) → 0; exponential-rate equality.

## Frameworks and Methods
- **Typical-set coding**: enumerate A_ε^{(n)} with n(H+ε) bits; send a 1-bit flag plus either that index or the raw n log|X| bits for nontypical sequences.
- **Volume vs probability**: typical sequences are *not* always the most probable (a sequence of all heads can be likelier but atypical if p≠1). Probability concentrates on typical, not on mode.
- **Smallest probable set**: any set with probability → 1 must have size at least ≈ 2^{nH}. Typical set is essentially smallest.

## Key Results and Theorems

**Theorem 3.1.1 (AEP).** If X1,X2,... are i.i.d. ~ p(x), then
−(1/n) log p(X1,...,Xn) → H(X) in probability.
Proof: −log p(X_i) are i.i.d. with mean H(X); apply WLLN.

**Theorem 3.1.2 (Properties of A_ε^{(n)}).**
1. If x^n ∈ A_ε^{(n)}, then H−ε ≤ −(1/n) log p(x^n) ≤ H+ε.
2. P(A_ε^{(n)}) → 1 as n→∞.
3. |A_ε^{(n)}| ≤ 2^{n(H+ε)} for all n.
4. |A_ε^{(n)}| ≥ (1−ε) 2^{n(H−ε)} for n large.

Proof of (3): 1 ≥ P(A) ≥ |A| · 2^{−n(H+ε)}. Proof of (4): P(A) ≥ 1−ε and each mass ≤ 2^{−n(H−ε)}.

**Theorem 3.2.1 (AEP coding).** For i.i.d. X^n ~ p and any ε>0 there is a one-to-one binary encoding of x^n with expected length per symbol
E[(1/n) l(X^n)] ≤ H(X) + ε
for n large. (Flag + typical index, or flag + naive encoding of nontypical.)

**Theorem 3.3.1 (Smallest probable set).** Let X_i i.i.d. ~ p. For δ < 1/2 and any δ'>0, if P(B_δ^{(n)}) > 1−δ then
(1/n) log |B_δ^{(n)}| > H − δ' for n large.
So you cannot hide probability 1−δ in a set much smaller than 2^{nH}.

## Key Equations
- p(x^n) ≈ 2^{−nH} on A_ε^{(n)}
- |A_ε^{(n)}| ≐ 2^{nH}
- P(A_ε^{(n)}) → 1
- Compression rate → H bits/symbol

## Worked Example
Bernoulli(p=0.9), H ≈ 0.469 bits. Sequences with about 90% ones are typical; the all-ones sequence is *most probable* but *not typical* (sample entropy 0 ≠ 0.469). The typical set has size ~ 2^{0.469 n} ≪ 2^n. Any encoder that only keeps the most probable 2^{nR} sequences with R < H leaves residual probability bounded away from 0.

## Anti-patterns
- **Equating typical with most probable**: false unless the source is uniform.
- **Using |X|^n as the effective alphabet**: only if H = log|X|.
- **Claiming a.s. AEP from Thm 3.1.1**: that is in probability; the Shannon–McMillan–Breiman theorem (Ch 16) gives a.s. for ergodic processes.
- **Forgetting the ε-slack**: finite-n typical-set bounds always carry ±ε in the exponent.

## Key Takeaways
1. AEP converts entropy from a formula into a counting statement.
2. Source coding at rate H+ε is immediate from enumerating the typical set.
3. No high-probability set is exponentially smaller than 2^{nH}.
4. Joint typicality (Ch 7, 10, 15) is this idea on pairs/triples.

## Connects To
- **Ch 2**: −log p(X) has expectation H.
- **Ch 4**: entropy *rate* replaces H for processes; AEP needs ergodicity.
- **Ch 5**: Kraft/Huffman achieve H without explicit typical sets.
- **Ch 7**: jointly typical (X^n,Y^n) prove channel coding.
- **Ch 11**: method of types is a finite-n refinement (every type class is equally likely).
- **Ch 16**: general AEP (SMB theorem) for ergodic processes and markets.

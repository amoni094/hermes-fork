# Cheatsheet — Li and Vitányi Kolmogorov Complexity

Reference machine U fixed. All O(1) depend on U, not on the strings. log = log2.

## Notation

| Symbol | Meaning |
|---|---|
| ℓ(x) | binary length of x |
| ⟨x,y⟩ | computable pairing |
| C(x), C(x\|y) | plain Kolmogorov complexity |
| K(x), K(x\|y) | prefix (self-delimiting) complexity |
| C(x,y) := C(⟨x,y⟩) | joint plain |
| K(x,y) := K(⟨x,y⟩) | joint prefix |
| x* | a shortest prefix program for x, ℓ(x*)=K(x) |
| m(x) | universal discrete semimeasure |
| M(x) | universal continuous semimeasure |
| Q_U(x) | sum_{U(p)=x} 2^{−ℓ(p)} |
| Ω | sum_{U(p)↓} 2^{−ℓ(p)} |
| Kt(x) | min {ℓ(p)+log t : U(p)=x in t steps} |
| I(x : y) | K(y)−K(y\|x) |
| I(x ; y) | K(x)+K(y)−K(x,y) |
| E1(x,y) | max{K(x\|y), K(y\|x)} |
| NID e(x,y) | E1 / max{K(x),K(y)} |

## Invariance

- C_φ(x\|y) ≥ C(x\|y) − c_φ; |C_U − C_V| ≤ O(1). (Thm 2.1.1)
- Same for K on prefix machines. (Thm 3.1.1)
- No additively optimal element among all (not necessarily computable) partial functions.

## Trivial bounds

- C(x) ≤ ℓ(x) + O(1); C(x\|y) ≤ C(x)+O(1). (Thm 2.1.2)
- K(x) ≤ ℓ(x) + 2 log ℓ(x) + O(1); K(x\|ℓ(x)) ≤ ℓ(x)+O(1).
- K(x) ≤ C(x) + K(C(x)) + O(1); C(x) ≤ K(x)+O(1).
- Typically K(x) = C(x) + Θ(log C(x)).
- Computable injection φ: |C(φ(x))−C(x)|=O(1). Same for K.

## Counting / incompressibility

- #{x : C(x) < n−c} < 2^{n−c+1}. Most n-bit strings: C(x) ≥ n−c. (Thm 2.2.1)
- sum_x 2^{−K(x)} ≤ 1 (Kraft). Most n-bit strings: K(x) ≥ n (actually ≥ n+K(n)−O(1)).
- C and K unbounded, →∞ slower than every unbounded computable function, not computable, upper semicomputable.

## Subadditivity (the C vs K split)

- C(x,y) ≤ C(x)+C(y)+2 log min(C(x),C(y))+O(1). Log term necessary.
- C(x,y | C(x)) ≤ C(x)+C(y)+O(1).
- K(x,y) ≤ K(x)+K(y)+O(1); K(xy) ≤ K(x)+K(y)+O(1).

## Symmetry of information

- K(x,y) = K(x) + K(y | x, K(x)) + O(1). (Thm 3.8.1)
- Equivalently K(x,y) = K(x)+K(y\|x*)+O(1).
- Naive form K(x,y)=K(x)+K(y\|x) fails by Ω(log K(x)).
- I(x ; y) = I(y ; x)+O(1).
- I(x : y) = I(y : x)+O(1) when conditioners are shortest programs.

## Coding theorem / universal prior

- log 1/m(x) = log 1/Q_U(x) = K(x)  (additive O(1)). (Thm 4.3.3)
- m(x) = Θ(2^{−K(x)}) = Θ(Q_U(x)).
- −log m(x\|y) = K(x\|y)+O(1). (Thm 4.3.4)
- m(x) ≥ 2^{−K(P)} P(x) for every lower-semicomputable discrete semimeasure P.
- No universal computable semimeasure.
- Shannon–Fano: semimeasure P ⇒ prefix code ℓ ≤ −log P + 2.

## Entropy vs complexity

- For computable P: H(P) ≤ ∑ P(x)K(x) ≤ H(P)+K(P)+O(1).
- Typical x ~ P: K(x) ≈ −log P(x).

## MDL / Solomonoff decision rules

- Solomonoff predict: P(b|x) = M(xb)/M(x).
- Sum_n (M−μ)^2 prediction error ≤ O(K(μ)) if μ computable.
- Ideal MDL: H* = argmin_H [ K(H) + K(D\|H) ].
- Two-part, not one-part: do not use argmin K(D) (overfit).
- Practical MDL: replace K by a code length L in a fixed language.
- Sufficient statistic: S ∋ x with K(S)+log|S| ≈ K(x) and K(x\|S)≈log|S|.

## Information distance

- E1(x,y) = max{K(x\|y), K(y\|x)}  (universal admissible).
- E4(x,y) = K(x\|y)+K(y\|x)  (between E1 and 2·E1).
- NID: e(x,y) = max{K(x\|y),K(y\|x)} / max{K(x),K(y)}.
- NCD: [C(xy)−min{C(x),C(y)}] / max{C(x),C(y)}.
- E1(x,y) ≤ D(x,y)+O(1) for every admissible D.

## Resource-bounded

- Kt(x) = min {ℓ(p)+log t : U(p)=x in time t}.
- Levin search inverts f in time O(2^{K(A)} t_A).
- Logical depth: time at which most Q_U-mass for x has appeared.
- Random strings are shallow; incompressible ≠ deep.

## Complexity classes (informal dictionary)

| Class of objects | Complexity picture |
|---|---|
| 0^n, n, π_{1:n} | C = O(log n) |
| typical n-bit string | C ≈ n, K ≈ n+K(n) |
| Martin-Löf random ω | K(ω_{1:n}) ≥ n+K(n)−O(1) |
| Ω_{1:n} | K ≥ n−O(1); decides halting ≤ n |
| SAT witness search | Kt ≈ n + log t_{solve} |
| Deep string | small K, huge runtime for all short p |

## Integer encodings (pay this or use prefix K)

- 1^{ℓ(n)} 0 n : 2ℓ(n)+1 bits.
- 1^{ℓ(ℓ(n))} 0 ℓ(n) n : ℓ(n)+2ℓ(ℓ(n))+1.

## What fails

| Claim | Status |
|---|---|
| C(x,y) ≤ C(x)+C(y)+O(1) | False |
| K(x,y) = K(x)+K(y\|x)+O(1) | False (need x*) |
| −log m(x) = C(x)+O(1) | False |
| C, K computable | False (halting) |
| Universal computable prior | False |
| Named string proved incompressible | Only finitely often in a given F |
| NCD = NID | Heuristic only |

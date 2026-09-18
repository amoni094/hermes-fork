# Chapter 10: Algorithms for Factoring and Discrete Logarithms

## Core Idea
The security margins of RSA and DH depend on the best known factoring and discrete-log algorithms. Understanding these algorithms determines minimum key lengths: GNFS for factoring is sub-exponential (L[1/3,c]), making RSA-1024 insecure and RSA-2048 the current minimum.

## Key Concepts
- **Pollard's p-1 algorithm**: fast factoring if p-1 has only small prime factors; defense: ensure p-1 has a large prime factor
- **Pollard's rho algorithm**: O(N^{1/4}) factoring; faster than trial division; breaks small RSA keys quickly
- **Quadratic sieve (QS)**: sub-exponential L[1/2,1] factoring; practical for N up to ~150 digits
- **General Number Field Sieve (GNFS)**: best known factoring algorithm; L[1/3, 1.923]; subexponential; breaks RSA-1024 feasibly
- **Baby-step/Giant-step**: O(√p) DLP algorithm; generic (works in any group); defeats small prime-order groups
- **Pohlig-Hellman**: reduces DLP in group of order N to DLP in groups of prime-order factors of N; defense: prime-order subgroups
- **Index calculus**: sub-exponential DLP in Z*_p; L[1/3] class; does NOT work on elliptic curves
- **Recommended key lengths** (2024): RSA 2048+ bits (3072 for 128-bit security); DH in prime-order group: 2048-bit modulus; ECDH P-256 (256-bit)

## Reference Table: Attack Complexities

| Algorithm | Target | Complexity | Practical for |
|---|---|---|---|
| Pollard's rho | Factoring | O(N^{1/4}) | N < 2^60 |
| QS | Factoring | L[1/2, 1] | N < 2^500 |
| GNFS | Factoring | L[1/3, 1.923] | N < 2^1024 feasible |
| Baby-step/giant-step | DLP (generic) | O(√p) | p < 2^64 |
| Index calculus | DLP in Z*_p | L[1/3] | p < 1024 bits |
| Shor's algorithm | Factoring/DLP | Poly(log N) | Quantum only |

## Key Takeaways
1. GNFS makes RSA-1024 insecure; use RSA-2048 minimum (RSA-3072 for 128-bit security post-2030)
2. Index calculus breaks DLP in Z*_p but NOT on elliptic curves — ECC advantage
3. Baby-step/giant-step always applies: prime-order group of order q costs O(√q) → q ≥ 2^256
4. Pohlig-Hellman: always use prime-order groups; never composite-order for DLP hardness

## Connects To
- **Ch 9**: The assumptions these algorithms try to break
- **Ch 14**: Shor's algorithm (quantum) breaks all of these in polynomial time

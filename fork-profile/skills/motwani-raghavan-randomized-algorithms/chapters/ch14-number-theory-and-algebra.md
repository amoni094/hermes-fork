# Ch 14 — Number Theory and Algebra

Abundance of witnesses: a huge search space contains many certificates; sample one.

## Preliminaries (Ch 14.1–14.2)

Euclid: `gcd(a,b)` and Bézout `ax+by=gcd` in polynomial time (Thm 14.1–14.2). Modular inverse (Thm 14.3). Chinese Remainder Theorem (Thm 14.4). Fast exponentiation (Thm 14.5). Euler `φ` (Thm 14.6). Euler’s theorem `x^{φ(n)} ≡ 1 (mod n)` (Thm 14.10); Fermat (Thm 14.11). `Z_p^×` cyclic for prime `p` (Thm 14.13).

**Theorem 14.16.** Given the factorisation of `p−1`, a generator of `Z_p^×` is found by a Las Vegas / Monte Carlo poly-time algorithm (sample; test order).

## Quadratic residues (Ch 14.3)

Legendre / Jacobi symbols. Euler’s criterion (Thm 14.18). **Theorem 14.21:** a poly-time square-root algorithm modulo *every* `n` yields a randomised factoring algorithm.

## RSA (Ch 14.4)

`n=pq`, encrypt `x ↦ x^e mod n`. Partial inversion on a non-negligible fraction of ciphertexts yields a Las Vegas inverter on all of `Z_n^×` (Thm 14.22).

## Polynomial roots (Ch 14.5)

**Theorem 14.26.** PolyRoot is Las Vegas and factors a degree-2 polynomial over `Z_p` (`p` odd prime) in expected poly time. Random affine shift so that roots split by quadratic residuosity.

## Primality (Ch 14.6)

**Theorem 14.27.** PRIMALITY ∈ NP (Pratt certificate: generator of `Z_n^×` plus recursive certificates for prime factors of `n−1`).

Carmichael numbers break naive Fermat tests.

**Theorem 14.31 (Solovay–Strassen style Primality1).** Always PRIME on primes; COMPOSITE on composites with probability `≥ 1/2`. Hence COMPOSITENESS ∈ RP, PRIMALITY ∈ co-RP.

**Theorem 14.33.** Primality2 (Miller–Rabin style) errs with probability `≤ 2^{-t}` after `t` independent bases.

**Theorem 14.34.** Primality3 is an RP algorithm for COMPOSITENESS; derandomisable under ERH.

(Deterministic poly-time primality — AKS 2002 — is after the book.)

## Hermes

- Witness abundance: if a check has many random witnesses, one sample plus amplification (Ch 1.2) beats exhaustive search.
- Never treat a Fermat test without Carmichael handling as a primality proof; use Miller–Rabin (Thm 14.33) and amplify.

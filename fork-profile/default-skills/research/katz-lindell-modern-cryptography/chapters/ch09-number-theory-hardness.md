# Chapter 9: Number Theory and Cryptographic Hardness Assumptions

## Core Idea
Public-key cryptography relies on computational hardness assumptions about number-theoretic problems: integer factoring (RSA), discrete logarithm (DH/Schnorr), and their elliptic-curve analogues. These problems have no known polynomial-time algorithms on classical computers.

## Key Concepts
- **Group Z*_N**: integers coprime to N under multiplication mod N; |Z*_N| = φ(N) (Euler's totient)
- **Factoring assumption**: given N = pq (product of two large primes), no PPT algorithm computes p, q
- **RSA assumption**: given (N, e, y), hard to compute x with x^e ≡ y (mod N); reduces to factoring
- **CDH (Computational Diffie-Hellman)**: given (g, g^a, g^b) in cyclic group G, compute g^{ab}; no known efficient algorithm
- **DDH (Decisional Diffie-Hellman)**: distinguish (g^a, g^b, g^{ab}) from (g^a, g^b, g^c) for random c; strictly stronger than CDH
- **Discrete logarithm (DL)**: given g^a in cyclic group, find a; believed hard in prime-order groups and elliptic curves
- **Cyclic group**: every element is a power of generator g; prime-order subgroups of Z*_p used in DH
- **Elliptic curves**: group law defined geometrically; ECDH uses the same DH protocol; smaller key sizes for equivalent security
- **Recommended key lengths**: RSA 2048+ bits; ECDSA P-256 (128-bit security); Symmetric AES-128

## Reference Table: Hardness Assumptions and Applications

| Assumption | Hard Problem | Scheme(s) Built On It |
|---|---|---|
| Factoring | Factor N = pq | RSA encryption, Rabin |
| RSA | Compute e-th root mod N | RSA-OAEP, RSA-FDH |
| CDH | Compute g^{ab} from g^a, g^b | ElGamal (with ROM) |
| DDH | Distinguish g^{ab} from g^c | ElGamal CPA-security, plain DH |
| DLP | Compute log_g(g^a) | Schnorr signatures, DSA |
| ECDLP | DLP on elliptic curve | ECDSA, ECDH |

## Key Takeaways
1. All public-key cryptography rests on computational assumptions that may be broken in the future (especially by quantum computers — see Ch 14)
2. RSA key ≥ 2048 bits; elliptic curve key ≥ 256 bits; symmetric key ≥ 128 bits for comparable security
3. DDH is strictly stronger than CDH; schemes assuming DDH are more restrictive but give cleaner proofs
4. Elliptic curves offer same security as Z*_p at 1/3 the key size

## Connects To
- **Ch 10**: Algorithms for factoring and DLP determine concrete key-length recommendations
- **Ch 11**: DH key exchange built on CDH assumption
- **Ch 12**: El Gamal and RSA encryption
- **Ch 13**: RSA-FDH and Schnorr signatures

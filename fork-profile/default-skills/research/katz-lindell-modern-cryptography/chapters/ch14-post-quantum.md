# Chapter 14: Post-Quantum Cryptography

## Core Idea
Shor's quantum algorithm solves factoring and DLP in polynomial time, breaking all public-key cryptography based on these assumptions. Post-quantum alternatives use lattice problems (LWE), hash-based signatures, and error-correcting codes — most already standardized by NIST (2024).

## Key Concepts
- **Shor's algorithm**: quantum factoring and DLP in poly(log N) time; requires large-scale fault-tolerant quantum computer
- **Grover's algorithm**: quantum search in O(2^{n/2}) instead of O(2^n); halves symmetric key security → double key lengths
- **Impact on symmetric crypto**: AES-128 → 64-bit security against quantum; AES-256 → 128-bit; SHA-256 → 128-bit collision security (Grover doesn't help much for hash)
- **Lattice-based cryptography**: security based on Learning With Errors (LWE) or Module-LWE; CRYSTALS-Kyber (NIST ML-KEM) for KEM
- **CRYSTALS-Dilithium (ML-DSA)**: NIST-standardized post-quantum signature scheme based on Module-LWE
- **Hash-based signatures**: Lamport, Winternitz, XMSS, SPHINCS+; security only requires collision-resistant hash functions
  - SPHINCS+: NIST-standardized; stateless; ~50KB signatures; conservative choice if lattice assumptions fail
- **Lamport's scheme**: sign 1 bit by revealing one of two preimages; sign n-bit hash → reveal n preimages; one-time only
- **Chain-based and tree-based signatures**: Winternitz reduces signature size vs Lamport; Merkle tree reuses one-time keys

## Reference Table: Post-Quantum Signature Options

| Scheme | Assumption | Sig Size | Notes |
|---|---|---|---|
| SPHINCS+ | Hash function only | ~8-50 KB | Stateless; conservative choice |
| ML-DSA (Dilithium) | Module-LWE | ~2.5 KB | NIST standard; efficient |
| Falcon | NTRU lattice | ~0.9 KB | Compact; complex implementation |
| XMSS | Hash function | ~2.5 KB | Stateful; standardized RFC 8391 |

## Key Takeaways
1. Shor breaks RSA, DH, ECDSA, El Gamal — all public-key schemes based on factoring/DLP
2. Grover halves symmetric security; double key lengths now (AES-256, SHA-384)
3. NIST standards (2024): ML-KEM (Kyber), ML-DSA (Dilithium), SPHINCS+ — use these for new systems
4. Hash-based signatures (SPHINCS+) are the most conservative; security reduces only to hash functions
5. Migration strategy: hybrid classical+PQC now; full PQC migration before large-scale quantum computers

## Connects To
- **Ch 9**: RSA and DLP are broken by Shor
- **Ch 6**: Hash functions underlie post-quantum signatures; SHA-256 remains secure
- **Ch 13**: Classical signatures are replaced; hash-based signatures use Merkle trees from Ch 6

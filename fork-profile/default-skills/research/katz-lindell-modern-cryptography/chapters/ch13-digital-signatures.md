# Chapter 13: Digital Signature Schemes

## Core Idea
Digital signatures are the public-key analogue of MACs: anyone can verify with the public key, but only the secret key holder can sign. EUF-CMA is the security notion; hash-and-sign + RSA-FDH or Schnorr/ECDSA are the practical schemes. Signatures underpin PKI, TLS, and code signing.

## Frameworks Introduced
- **Digital Signature = (Gen, Sign, Vrfy)**: Gen → (pk, sk); Sign_sk(m) → σ; Vrfy_pk(m, σ) → 0/1
- **EUF-CMA for signatures**: adversary sees pk and gets signing oracle; wins if it produces (m*, σ*) with Vrfy_pk(m*, σ*) = 1 for unseen m*
- **Hash-and-Sign Paradigm**: sign H(m) instead of m; avoids raw-RSA attacks; H must be collision resistant
  - When to use: All practical signature schemes; RSA-FDH, Schnorr, ECDSA all use this
- **Schnorr Identification Protocol**: 3-round sigma protocol proving knowledge of discrete log; basis for signatures
  - Commit: R = g^r; Challenge: c ←{0,1}^κ; Respond: s = r + cx mod q
  - ZK property: verifier learns nothing about x beyond "prover knows x"

## Key Concepts
- **Existential forgery**: produce valid signature for any message (even chosen by forger); must be prevented
- **RSA-FDH (Full-Domain Hash)**: σ = H(m)^d mod N; H maps to Z*_N; IND-CMA in ROM under RSA
- **RSA-PKCS#1 v1.5**: widely deployed; has known weaknesses (Bleichenbacher attack variants); prefer PSS
- **RSA-PSS**: probabilistic RSA signature scheme; IND-CMA in ROM with better security bounds than FDH
- **Schnorr signature**: (R, s) where R = g^r, s = r + H(R||m)·x; efficient, short; Fiat-Shamir from ZK protocol
- **DSA (Digital Signature Algorithm)**: NIST standard based on Schnorr; use ECDSA for modern deployments
- **ECDSA**: DSA on elliptic curves; P-256 curve (128-bit security); widely used (TLS, Bitcoin)
- **Certificates (X.509)**: CA signs (identity, public key) pair; chain of trust up to root CA
- **TLS handshake**: server sends certificate (signed pk); client verifies chain; DH key exchange authenticated by server's signature
- **Signcryption**: simultaneously sign and encrypt in a single operation; more efficient than Sign then Encrypt
- **Zero-knowledge proof**: prover convinces verifier of a statement without revealing witness; Schnorr ID is a ZK proof of knowledge of DLP

## Mental Models
- "Sign the hash, not the message": H(m) compresses to fixed size, prevents existential forgery via RSA math
- Fiat-Shamir heuristic: replace verifier's challenge with H(commitment || message); turns ZK protocol into signature scheme
- Certificate chain: user trusts root CA → root signs intermediate CA cert → intermediate signs server cert → server proves identity

## Anti-patterns
- **Signing without hashing (plain RSA)**: existential forgery: pick σ, compute m = σ^e; σ is a valid signature on m
- **Verifying ECDSA without checking curve point validity**: allows fault attacks on key recovery
- **Reusing nonce r in Schnorr/ECDSA**: catastrophic; reveals private key via linear equations (Sony PS3 hack)

## Worked Example
**Schnorr ZK proof applied to skill provenance**:
- Setup: skill generator has secret key x; public commitment pk = g^x
- Claim: "I generated this skill" without revealing x
- Protocol: r ← Zq random; commit R = g^r; receive challenge c; respond s = r + cx mod q
- Verifier checks: g^s = R · pk^c (i.e., g^s = g^r · g^{cx})
- ZK: verifier learns nothing about x (simulation: choose s, c → R = g^s · pk^{-c})
- Soundness: if s = r + cx holds for two different c values, x can be extracted → prover knows x
- Fiat-Shamir → non-interactive: replace c with H(R || message)

## Key Takeaways
1. Hash-and-Sign is mandatory; never sign raw messages with RSA (existential forgery)
2. ECDSA P-256 is the standard for new deployments; Schnorr (Ed25519) is preferred for systems that can choose
3. Nonce reuse in Schnorr/ECDSA reveals private key; use deterministic nonces (RFC 6979) or hardware RNG
4. X.509 certificates bind public keys to identities; verify full chain to root CA
5. ZK proofs (Schnorr) prove knowledge without revealing the witness; Fiat-Shamir makes them non-interactive

## Connects To
- **Ch 4**: MACs are the private-key analogue; same EUF-CMA notion
- **Ch 6**: Hash-and-sign uses collision-resistant hash
- **Ch 9**: RSA and DLP assumptions underlie all signature schemes
- **Ch 14**: Post-quantum signatures (hash-based, lattice-based) needed when Shor's algorithm arrives

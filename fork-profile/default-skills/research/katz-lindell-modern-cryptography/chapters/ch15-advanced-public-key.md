# Chapter 15: Advanced Topics in Public-Key Encryption

## Core Idea
Advanced public-key primitives enable computation on encrypted data (homomorphic encryption via Paillier), distributed decryption (threshold encryption, secret sharing), and cryptographic schemes with unique mathematical properties (Goldwasser-Micali, Rabin). These extend the toolkit for privacy-preserving multi-party settings.

## Key Concepts
- **Homomorphic encryption**: Enc(m₁) ○ Enc(m₂) = Enc(m₁ + m₂) or Enc(m₁ · m₂) without decrypting
- **Paillier encryption**: additively homomorphic; Enc(m₁) · Enc(m₂) = Enc(m₁ + m₂ mod N); based on composite residuosity assumption
- **Goldwasser-Micali (GM)**: 1-bit encryption based on quadratic residuosity; XOR-homomorphic; historical importance as first provably IND-CPA scheme
- **Rabin encryption**: decryption requires factoring; CCA-secure in ROM (with appropriate padding)
- **Secret sharing (Shamir)**: split secret s into n shares; any k shares reconstruct s; fewer than k reveals nothing; based on polynomial interpolation
- **Verifiable secret sharing (VSS)**: shares include commitment enabling verification without revealing secret
- **Threshold encryption**: decrypt only when k-of-n parties cooperate; uses secret sharing to split decryption key
- **Electronic voting**: ElGamal threshold encryption + ZK proofs of vote validity → privacy-preserving tallying
- **Trapdoor permutation**: one-way permutation with trapdoor enabling inversion; RSA is canonical example

## Mental Models
- Homomorphic encryption: "compute on the ciphertext side, decrypt once"; enables privacy-preserving computation
- Secret sharing: "k-of-n threshold": need k keyholders present to unlock; each share is worthless alone
- Threshold encryption: distribute trust; no single server can decrypt

## Key Takeaways
1. Paillier homomorphic encryption enables adding encrypted values; useful for privacy-preserving aggregation
2. Secret sharing (Shamir) enables (k, n)-threshold schemes; any k shares reconstruct secret; polynomial interpolation
3. Full homomorphic encryption (FHE) exists but is ~10^4x slower than plaintext; avoid for performance-critical use
4. Threshold decryption distributes trust; no single party can decrypt alone; used in HSMs and MPC protocols

## Connects To
- **Ch 9**: RSA trapdoor permutation; composite residuosity assumption for Paillier
- **Ch 12**: Public-key encryption extended with new properties
- **Ch 13**: ZK proofs used in voting protocols and verifiable secret sharing

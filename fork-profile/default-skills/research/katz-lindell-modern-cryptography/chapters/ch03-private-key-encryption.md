# Chapter 3: Private-Key Encryption

## Core Idea
Computational security — restricting adversaries to PPT algorithms and allowing negligible failure probability — enables short keys to encrypt arbitrarily long messages, overcoming the fundamental limits of perfect secrecy through PRGs and PRFs.

## Frameworks Introduced
- **Asymptotic Security Framework**: Security is parameterized by security parameter `n`; honest parties run in poly(n) time; adversary success probability is negligible(n)
  - When to use: When designing or proving schemes abstract of concrete parameters
  - How: Express all bounds as functions of n; show advantage ≤ negl(n) for all PPT adversaries
- **Proof by Reduction**: Assume adversary A breaks Π with non-negligible advantage → build B that uses A to break P with non-negligible advantage → contradiction since P is hard
  - When to use: Every security proof in modern cryptography
  - How: Run A as a subroutine; translate queries and answers between P's game and Π's game; extract P solution from A's output
- **EAV-Security (eavesdropper security / IND-EAV)**: No PPT adversary can distinguish Enc_k(m₀) from Enc_k(m₁) with advantage > negl(n)
  - Security against passive eavesdroppers (single encryption)
- **CPA-Security (IND-CPA)**: EAV + adversary has encryption oracle; multi-message security
  - When to use: The baseline for any real-world encryption scheme
  - How: Encryption must be randomized; same plaintext encrypts to different ciphertexts
- **Pseudorandom Generator (PRG)**: G: {0,1}^n → {0,1}^{l(n)}, l(n) > n; output indistinguishable from uniform
  - Enables short seed to produce arbitrarily long keystream
- **Pseudorandom Function (PRF)**: F_k: {0,1}^n → {0,1}^n; indistinguishable from truly random function
  - Enables CPA-secure encryption: Enc_k(m) = (r, F_k(r) ⊕ m) for random r

## Key Concepts
- **Security parameter (n)**: integer controlling all security guarantees; corresponds to key length
- **Negligible function**: f(n) < 1/p(n) for all polynomials p and all large n; written negl(n); e.g., 2^{-n}
- **PPT (probabilistic polynomial-time)**: model for efficient adversaries and honest parties
- **EAV-security**: indistinguishability under passive eavesdropping; implies semantic security
- **Semantic security**: no partial information about plaintext is learned by PPT adversary
- **CPA-security**: IND-CPA; requires randomized encryption; multiple encryptions remain secure
- **CPA-secure construction**: Enc_k(m) = (r, F_k(r) ⊕ m) where r ← {0,1}^n is random
- **CTR mode**: Enc_k(m) = (ctr, F_k(ctr) ⊕ m₁ || F_k(ctr+1) ⊕ m₂ || ...); IND-CPA if ctr is random
- **CBC mode**: c_i = F_k(m_i ⊕ c_{i-1}); IND-CPA with random IV; not CCA-secure
- **Nonce-based encryption**: Replaces random IV with a nonce; secure only if nonce never repeats

## Mental Models
- Use "PRF = keyed black box"; PRF key gives a specific random-looking function; changing key gives completely different function
- Think of CPA-security as "encryption must be a random-looking permutation on a fresh nonce each time"
- Reduction arrows: adversary A → reduction B → hard problem P; B should run in poly(n) time

## Anti-patterns
- **Deterministic encryption under CPA**: Same plaintext always encrypts to same ciphertext → adversary distinguishes
- **ECB mode**: Each block encrypted independently; patterns in plaintext visible in ciphertext
- **Nonce reuse in CTR/OFB**: Two messages with same nonce → attacker XORs ciphertexts to get m₁ ⊕ m₂

## Code Examples
```python
import os, hmac, hashlib

def cpa_secure_enc(key: bytes, plaintext: bytes) -> bytes:
    """CTR-mode-style encryption using HMAC-SHA256 as PRF."""
    nonce = os.urandom(16)
    # Generate keystream blocks via PRF(key, nonce || counter)
    keystream = b""
    for i in range((len(plaintext) + 31) // 32):
        block_input = nonce + i.to_bytes(4, 'big')
        keystream += hmac.new(key, block_input, hashlib.sha256).digest()
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream))
    return nonce + ciphertext
```
- **What it demonstrates**: CPA-secure encryption using HMAC as a PRF; nonce ensures fresh randomness per encryption

## Worked Example
PRF-based CPA-secure encryption proof sketch:
- Adversary A queries encryption oracle getting (r₁, F_k(r₁) ⊕ m₁), ..., and finally challenge ciphertext (r*, F_k(r*) ⊕ m_b)
- If r* is fresh (not repeated), then F_k(r*) is pseudorandom and independent of all prior outputs
- Build reduction B: replace F_k with truly random function f; now F_k(r*) is uniform → A's advantage = 0
- Since A can't distinguish F_k from f (that's what PRF means), A's advantage against real scheme ≤ negl

## Key Takeaways
1. PRG enables short key + long message encryption; PRF enables CPA-security
2. CPA-security requires randomized encryption; deterministic CPA schemes don't exist
3. Proof by reduction is the universal tool: always reduce security to a known-hard primitive
4. EAV = semantic security; CPA ⊃ EAV; all real schemes should target at minimum CPA
5. CTR mode with random nonce achieves CPA-security from any PRF; nonce reuse breaks it completely

## Connects To
- **Ch 4**: MACs provide integrity that CPA-secure encryption lacks
- **Ch 5**: Combining encryption + MAC gives authenticated encryption (CCA-security)
- **Ch 8**: Theoretical construction of PRF from one-way functions
- **Ch 7**: AES/ChaCha20 as concrete PRPs used in practice

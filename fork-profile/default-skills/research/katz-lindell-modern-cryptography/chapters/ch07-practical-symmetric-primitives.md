# Chapter 7: Practical Constructions of Symmetric-Key Primitives

## Core Idea
Real-world symmetric-key primitives (AES, ChaCha20, SHA-2, SHA-3) are designed using substitution-permutation networks and Feistel structures to achieve diffusion and confusion, providing practical PRPs and hash functions that resist known cryptanalytic attacks.

## Key Concepts
- **Block cipher**: keyed pseudorandom permutation on fixed-size blocks (AES: 128-bit blocks, 128/192/256-bit keys)
- **AES (Advanced Encryption Standard)**: Rijndael cipher; Substitution-Permutation Network; 10/12/14 rounds; hardware acceleration (AES-NI); use for all block cipher needs
- **DES/3DES**: 56-bit effective key (DES broken); 3DES uses 3 keys (112-bit security); legacy only
- **Feistel network**: splits block in halves; L₁ = R₀, R₁ = L₀ ⊕ f(R₀, k₁); invertible for any f; used in DES
- **SPN (Substitution-Permutation Network)**: S-boxes (nonlinear) + P-boxes (diffusion); AES uses this
- **ChaCha20**: stream cipher based on ARX (add-rotate-XOR); no S-boxes; faster without AES-NI; used in TLS 1.3
- **RC4**: historically used stream cipher; multiple weaknesses; never use in new code
- **SHA-256**: Merkle-Damgård + Davies-Meyer compression; 256-bit output; 128-bit collision security
- **SHA-3 (Keccak)**: sponge construction; immune to length-extension; different design from SHA-2; NIST standard
- **Differential cryptanalysis**: finds key bits by analyzing differences in input/output pairs; S-boxes in AES designed to resist
- **Linear cryptanalysis**: exploits linear approximations of S-boxes; also defended by AES design

## Practical Construction Rules

| Need | Primitive | Notes |
|------|-----------|-------|
| Block encryption | AES-128 or AES-256 | Use with CTR or CBC mode + MAC |
| Stream encryption | ChaCha20 | Use with Poly1305 (ChaCha20-Poly1305) |
| Hash | SHA-256 | 128-bit collision security |
| Hash (length-ext safe) | SHA-3-256 | Preferred when Merkle-Damgård is a risk |
| Legacy compat | 3DES | Only if no other option |

## Key Takeaways
1. AES is the default block cipher; hardware acceleration (AES-NI) makes it fast
2. Never use raw AES in ECB mode; always use authenticated modes (GCM) or CTR+MAC
3. ChaCha20-Poly1305 is the stream cipher alternative; preferred when no AES-NI available
4. SHA-3 is immune to length-extension; prefer over SHA-2 when building PRNG or KDF from scratch
5. RC4, DES, and MD5 are broken — never use for security

## Connects To
- **Ch 3**: AES as concrete PRP for CTR/CBC modes
- **Ch 5**: AES-GCM as authenticated encryption standard
- **Ch 6**: SHA-2/SHA-3 as hash functions; Merkle-Damgård structure

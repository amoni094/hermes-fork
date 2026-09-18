# Cheatsheet — Introduction to Modern Cryptography (Katz & Lindell)

## Primitive Selection Decision Tree

```
Need to PROTECT DATA?
├─ Need CONFIDENTIALITY only?
│   └─ Use AES-256-CTR + separate HMAC (or just AES-GCM below)
├─ Need INTEGRITY only?
│   ├─ Shared key available? → HMAC-SHA256
│   └─ No shared key (public verify)? → ECDSA P-256 signature
└─ Need BOTH confidentiality + integrity?
    └─ Use AES-256-GCM or ChaCha20-Poly1305
        (both give authenticated encryption = CCA-security)

Need to AUTHENTICATE IDENTITY?
├─ Shared key? → HMAC-based challenge-response
└─ No shared key? → ECDSA signature over challenge

Need to EXCHANGE KEYS?
├─ Classical? → ECDH (Curve25519) → derive with HKDF
└─ Post-quantum? → ML-KEM (Kyber) → derive with HKDF

Need HASH?
├─ General purpose, collision-resistant → SHA-256
├─ Length-extension safety (e.g., PRNG) → SHA-3-256
└─ Slow hash (passwords) → Argon2id (not SHA-256!)
```

## Security Level Quick Reference

| Security bits | Symmetric | RSA | EC | DH (FFDH) |
|---|---|---|---|---|
| 80 | 3DES | 1024 | P-192 | 1024-bit |
| 112 | 3DES | 2048 | P-224 | 2048-bit |
| 128 | AES-128 | 3072 | P-256 | 3072-bit |
| 192 | AES-192 | 7680 | P-384 | 7680-bit |
| 256 | AES-256 | 15360 | P-521 | 15360-bit |

**Post-quantum**: Double symmetric key lengths (AES-256, SHA-384). Replace all RSA/EC with ML-KEM + ML-DSA.

## MAC / Integrity Quick Rules

| Situation | Rule |
|---|---|
| Verify file integrity | HMAC-SHA256(key, file_contents) |
| Authenticate session data | HMAC-SHA256(key, session_id \|\| data) |
| Check MAC | `hmac.compare_digest()` — NEVER `==` |
| Variable-length CBC-MAC | Prefix with message length |
| HMAC vs H(key\|\|m) | Always HMAC; H(key\|\|m) has length-extension vulnerability |
| HMAC key size | ≥ 256 bits (32 bytes) |

## Encryption Mode Decision

| Mode | Security | Use when |
|---|---|---|
| AES-GCM | AE (CCA) | Default for all symmetric encryption |
| ChaCha20-Poly1305 | AE (CCA) | No AES-NI hardware; mobile/embedded |
| AES-CTR + HMAC | AE (if EtM) | Building block; prefer GCM |
| AES-CBC + HMAC | AE only if EtM | Legacy; careful nonce management |
| AES-ECB | NOT SECURE | Never use (patterns visible) |
| AES-CBC alone | CPA only | NOT CCA; padding-oracle vulnerable |

## Composition Rules

| Composition | Result | Safe? |
|---|---|---|
| Encrypt-then-MAC | AE (provably) | ✅ Yes — use this |
| MAC-then-Encrypt | Fragile | ⚠️ POODLE/BEAST; avoid |
| Encrypt-and-MAC | Insecure | ❌ MAC leaks plaintext info |

## Hash Function Security Properties

| Property | Definition | Broken by | SHA-256 bits |
|---|---|---|---|
| Preimage resistance | Given h, find x with H(x)=h | Brute force | 256 |
| Second-preimage resistance | Given x, find x' with H(x')=H(x) | Targeted brute force | 256 |
| Collision resistance | Find any x≠x' with H(x)=H(x') | Birthday attack (√) | 128 |

## Tells and Smells

| If you see... | Likely problem |
|---|---|
| `H(key \|\| message)` as MAC | Length-extension attack possible; use HMAC |
| `==` to compare MACs/tags | Timing oracle; use `hmac.compare_digest` |
| Same nonce in CTR/GCM twice | Complete break; nonces must be unique per key |
| ECB mode | Patterns visible in ciphertext; never use |
| MD5 or SHA-1 for integrity | Collision attacks exist; use SHA-256 |
| Bare RSA (textbook) | Deterministic; no padding; forgeable |
| MACthen-Encrypt in CBC | Padding-oracle vulnerability |
| Nonce reuse in Schnorr/ECDSA | Private key recovery via linear algebra |
| Signing without hashing | Existential forgery possible |

## Commitment Scheme Quick Cheat

```
Commit:  (com, nonce) = SHA256(random_nonce || message), random_nonce
Reveal:  publish (nonce, message)
Verify:  SHA256(nonce || message) == com
Binding: collision resistance of SHA-256 (infeasible to find m' with same com)
Hiding:  preimage resistance + random nonce (com reveals nothing about m)
```

## Merkle Tree Cheat

```
Build:  leaves = [SHA256(item) for item in items]
        while len(leaves) > 1: leaves = [SHA256(l+r) for l,r in pairs(leaves)]
        root = leaves[0]

Proof size: O(log N) hashes
Verify: recompute path from leaf to root; compare with stored root
Security: collision resistance of SHA-256
Use for: skill file batch integrity; action log checkpointing
```

## Key Hierarchy Pattern

```
master_secret (HSM or env var)
    │
    ├─ HKDF(master, "mac-key")      → MAC key for integrity
    ├─ HKDF(master, "enc-key")      → Encryption key
    ├─ HKDF(master, "token-key")    → Session token PRF key
    └─ HKDF(master, "commit-key")   → Commitment verification key
```

## Security Proof Checklist

Before claiming a scheme is secure:
1. ☐ Stated the security definition (EAV / CPA / CCA / EUF-CMA)?
2. ☐ Identified the hardness assumption (PRF / OWF / DDH / factoring)?
3. ☐ Built a reduction (adversary breaks scheme → breaks assumption)?
4. ☐ Reduction runs in polynomial time?
5. ☐ Adversary's advantage is non-negligible → contradiction?
6. ☐ Hybrid argument closes the gap if multiple reductions needed?

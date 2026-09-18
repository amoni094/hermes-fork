# Chapter 5: CCA-Security and Authenticated Encryption

## Core Idea
Chosen-ciphertext attacks (CCA) — where an adversary can decrypt arbitrary ciphertexts — break all CPA-secure schemes in practice. Authenticated encryption (AE) provides both confidentiality and integrity, achieving CCA-security. The Encrypt-then-MAC composition is the provably secure construction.

## Frameworks Introduced
- **CCA-Security (IND-CCA2)**: Adversary has both encryption and decryption oracles; cannot decrypt challenge ciphertext; cannot distinguish encryptions of m₀ vs m₁
  - When to use: Any scheme where adversary might inject or modify ciphertexts
  - Practical implication: All internet protocols need CCA-security; CPA-alone is insufficient
- **Authenticated Encryption (AE)**: simultaneously CPA-secure (confidentiality) + EUF-CMA (integrity)
  - Equivalently achieves CCA-security
  - Standard: AES-GCM, ChaCha20-Poly1305
- **Encrypt-then-MAC (EtM)**: Enc_k1(m) → c; Mac_k2(c) → t; send (c, t)
  - When to use: Constructing AE from separate encryption and MAC primitives
  - Why: Tag is over ciphertext, not plaintext; decryption can check MAC before decrypting → prevents oracle
- **MAC-then-Encrypt (MtE)**: Mac_k2(m) → t; Enc_k1(m || t) → c; send c
  - Fragile: receiver must decrypt before verifying MAC → decryption oracle leaks padding → padding-oracle attack
  - Used in TLS 1.0/1.1 (and was broken by BEAST, POODLE)

## Key Concepts
- **Chosen-ciphertext attack**: adversary submits arbitrary ciphertexts to decryption oracle; learns partial information from response
- **Padding-oracle attack**: server reveals whether decryption padding is valid; attacker learns plaintext byte-by-byte in O(256n) queries for n-byte message
- **Malleability**: a scheme is malleable if ciphertexts can be meaningfully modified; malleable schemes cannot be CCA-secure
- **Authenticate-then-Encrypt (AtE)**: third composition; also fragile for some schemes
- **AES-GCM**: authenticated encryption standard; AES-CTR for encryption + GHASH (polynomial MAC) for authentication; single key, single pass possible
- **ChaCha20-Poly1305**: stream cipher + Carter-Wegman MAC; used in TLS 1.3 when AES hardware unavailable
- **Secure communication sessions**: use separate keys for each direction and session; include sequence numbers in MAC to prevent replay

## Mental Models
- CCA-security is "security with a decryption oracle except for the challenge" — the real-world model for network protocols
- Encrypt-then-MAC: "MAC what you send"; MAC tag covers the actual wire bytes; prevents oracle attacks
- If you see "MACthen-Encrypt" in legacy code → look for padding-oracle vulnerabilities

## Anti-patterns
- **Encrypt-and-MAC**: compute both Enc and MAC of plaintext independently; MAC leaks plaintext information
- **MAC-then-Encrypt in CBC mode**: POODLE, BEAST attacks; avoid in TLS 1.0/1.1 configuration
- **Nonce reuse in AES-GCM**: catastrophic; reusing a nonce with same key allows forgery (Poly1305 MAC becomes transparent)
- **Decrypting then checking MAC**: creates decryption oracle; must verify MAC first (constant-time) before any decryption

## Code Examples
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def ae_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """AES-GCM authenticated encryption — provides AE = CPA + integrity."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce; never reuse with same key
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ciphertext

def ae_decrypt(key: bytes, data: bytes, aad: bytes = b"") -> bytes:
    """Raises InvalidTag exception if ciphertext is tampered."""
    aesgcm = AESGCM(key)
    nonce, ciphertext = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ciphertext, aad)  # constant-time MAC verify internally
```
- **What it demonstrates**: AES-GCM provides authenticated encryption; AAD binds context metadata; any tampering raises exception before any plaintext is returned

## Worked Example
**Padding-oracle attack on CBC + MAC-then-Encrypt** (POODLE-style):
1. Sender encrypts: MAC(m) → t; Enc_CBC(m || t) → c; transmit c
2. Attacker intercepts c; modifies last byte of last ciphertext block
3. Server decrypts: if padding is invalid, returns error; if valid, proceeds to check MAC
4. Error reveals whether last byte of plaintext had valid padding
5. Repeat for all 256 possible modifications: one reveals the actual byte value
6. Attacker recovers plaintext byte-by-byte without the key
7. Fix: Encrypt-then-MAC — MAC covers ciphertext; check MAC first (constant-time); reject before any CBC decryption

## Key Takeaways
1. CPA-security is not CCA-security; internet protocols need CCA or authenticated encryption
2. Encrypt-then-MAC is the provably secure composition for AE from separate primitives
3. Padding-oracle attacks require only error responses; timing differences also work (timing oracle)
4. AES-GCM / ChaCha20-Poly1305 are the recommended defaults; prefer library implementations
5. Never reuse a GCM nonce with the same key; use random 96-bit nonces or a counter

## Connects To
- **Ch 4**: MAC component of AE
- **Ch 13**: TLS uses authenticated encryption with digital signatures for server authentication
- **Ch 7**: AES and ChaCha20 as underlying stream cipher components

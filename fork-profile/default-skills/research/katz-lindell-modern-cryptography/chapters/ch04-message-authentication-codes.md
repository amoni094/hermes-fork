# Chapter 4: Message Authentication Codes

## Core Idea
Encryption does not provide integrity — stream cipher ciphertexts are malleable (bit flips in ciphertext flip bits in plaintext). MACs, built from PRFs, provide existential unforgeability: an adversary who sees polynomially many (message, tag) pairs cannot forge a valid tag on any new message.

## Frameworks Introduced
- **MAC = (Gen, Mac, Vrfy)**: Gen produces key k; Mac_k(m) → t; Vrfy_k(m, t) → 0/1
  - Correctness: Vrfy_k(m, Mac_k(m)) = 1 always
- **EUF-CMA (Existential Unforgeability under Chosen-Message Attack)**: adversary gets oracle Mac_k(·) for poly-many queries; wins if it outputs (m*, t*) with Vrfy_k(m*, t*) = 1 for m* not previously queried
  - When to use: The required security notion for any MAC
  - How: Prove no PPT adversary can forge with non-negligible probability
- **Fixed-Length MAC from PRF**: Mac_k(m) = F_k(m) for m ∈ {0,1}^n
  - Secure because F_k is indistinguishable from random; any tag on new message is unpredictable
- **CBC-MAC (domain extension)**: chain PRF evaluations; c₁ = F_k(m₁), c₂ = F_k(m₁ ⊕ c₁), ...; output final c_t
  - Secure for fixed-length messages; requires length-prepending for variable-length
- **HMAC**: HMAC_k(m) = H((k ⊕ opad) || H((k ⊕ ipad) || m))
  - Secure in random-oracle model; avoids length-extension attacks on Merkle-Damgård hash functions
  - Industry standard; use for any MAC requirement in Python (hmac module)

## Key Concepts
- **Message integrity**: ensure a received message was not tampered with or forged
- **EUF-CMA**: existential unforgeability under chosen-message attack; the standard MAC security notion
- **Tag (t)**: short authenticator appended to message; typically 128–256 bits (HMAC-SHA256 outputs 32 bytes)
- **Chosen-message attack**: adversary can request MAC tags for arbitrary messages of its choice
- **Existential forgery**: produce any valid (m*, t*) for a new message — even one adversary doesn't care about
- **Length extension attack**: given H(m), can compute H(m || padding || m') without knowing key; Merkle-Damgård vulnerability; HMAC is immune
- **CBC-MAC attack (variable-length)**: if CBC-MAC is used for variable-length without length-prefix, forging is trivial
- **Poly1305**: Carter-Wegman MAC based on polynomial evaluation modulo prime; used with ChaCha20 in TLS
- **GMAC**: polynomial MAC over GF(2^128); used in AES-GCM
- **MAC ≠ encryption**: MAC alone does not hide message content; use authenticated encryption for both

## Mental Models
- Think of a MAC as a "keyed fingerprint": only someone with the key can produce a fingerprint that verifies
- EUF-CMA means "even one forgery is a win for the adversary" — the bar for MAC security is high
- Use HMAC as default; it is battle-tested, provably secure in ROM, and available in every language

## Anti-patterns
- **Using encryption instead of MAC for integrity**: malleable ciphertexts allow forging without detection
- **Truncating HMAC to <80 bits**: reduces forgery security; use full 256-bit output or at minimum 128 bits
- **CBC-MAC for variable-length messages without length-prefix**: trivially forgeable (append attack)
- **Sending MAC without a secure key**: MAC with a known key provides zero security

## Code Examples
```python
import hmac, hashlib, secrets

def compute_mac(key: bytes, message: bytes) -> bytes:
    """HMAC-SHA256 tag — EUF-CMA secure MAC."""
    return hmac.new(key, message, hashlib.sha256).digest()

def verify_mac(key: bytes, message: bytes, tag: bytes) -> bool:
    """Constant-time verification — prevents timing oracle attacks."""
    expected = compute_mac(key, message)
    return hmac.compare_digest(expected, tag)

# For skill integrity: MAC the file contents
def skill_mac(mac_key: bytes, skill_path: str) -> bytes:
    with open(skill_path, 'rb') as f:
        return compute_mac(mac_key, f.read())
```
- **What it demonstrates**: HMAC-SHA256 for EUF-CMA secure MAC; constant-time comparison prevents timing attacks that could reveal key bits

## Worked Example
**Cookie integrity with HMAC** (real-world use case from the book):
- Merchant stores cart data in cookie; must ensure user can't modify prices
- Solution: cookie = (data, HMAC_k(data))
- When cookie is returned: verify HMAC_k(data) == stored tag; reject if mismatch
- Security: even knowing the data and tag, adversary cannot forge a valid tag on modified data without k
- Attack prevented: user changes price from $100 to $10 → tag verification fails → request rejected

## Key Takeaways
1. Encryption is malleable: stream cipher bit-flips in ciphertext directly flip plaintext bits
2. MAC provides existential unforgeability: adversary seeing many (m, Mac_k(m)) pairs can't forge for new m
3. HMAC is the right default: secure in ROM, immune to length-extension, standardized (RFC 2104)
4. Always use constant-time comparison (hmac.compare_digest); timing attacks can leak key bits
5. For variable-length messages, always prefix message with its length before CBC-MAC

## Connects To
- **Ch 5**: Combining MAC with encryption gives authenticated encryption (AE)
- **Ch 6**: HMAC construction uses hash functions; collision resistance of hash is not required for HMAC security (PRF assumption suffices)
- **Ch 13**: Digital signatures give public-key analogue of MACs (public verification, no shared key)

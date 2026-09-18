# Chapter 6: Hash Functions and Applications

## Core Idea
Collision-resistant hash functions compress arbitrary inputs to fixed-length digests; finding two inputs with the same digest is computationally infeasible. This enables fingerprinting, commitment schemes, Merkle trees, password hashing, and HMAC — making hash functions the Swiss Army knife of applied cryptography.

## Frameworks Introduced
- **Collision Resistance**: No PPT adversary can find x ≠ x' with H(x) = H(x') with non-negligible probability
  - When to use: Any application needing a unique identifier for data (fingerprinting, deduplication, Merkle trees)
  - How: Use SHA-256 (256-bit output → 128-bit collision security) or SHA-3
- **Merkle-Damgård Transform**: Extends fixed-length compression function h to arbitrary-length hash H
  - Iterates h(state, block); appends length-encoding padding
  - Used by MD5, SHA-1, SHA-2; vulnerable to length-extension if used naively
- **Merkle Trees**: Binary tree where leaf i = H(xᵢ); internal node = H(left || right); root authenticates all leaves
  - When to use: Authenticated data structures, sparse proofs, blockchain, action logs
  - How: O(log t) proof of inclusion (authentication path); root hash commits to all t values
- **Commitment Scheme**: com = H(r || m) where r ← {0,1}^n is random; reveals (r, m) to open
  - Binding: can't find m' ≠ m with same commitment (collision resistance of H)
  - Hiding: H(r || m) reveals nothing about m if r is uniformly random (preimage resistance)
- **HMAC Construction**: HMAC_k(m) = H((k ⊕ opad) || H((k ⊕ ipad) || m))
  - ipad = 0x36...36, opad = 0x5c...5c; pads to block size
  - Secure PRF even for Merkle-Damgård hash functions; length extension attacks cannot pierce the outer hash

## Key Concepts
- **Collision resistance** ⟹ second-preimage resistance ⟹ preimage resistance (strict hierarchy)
- **Birthday bound**: expected collision after ~2^{n/2} evaluations; use n=256 for 128-bit security
- **Preimage resistance (one-wayness)**: given h, hard to find any x with H(x) = h
- **Second-preimage resistance**: given x, hard to find x' ≠ x with H(x') = H(x)
- **Length-extension attack**: Merkle-Damgård: given H(m), can compute H(m || padding || m') without key
- **Sponge construction (SHA-3/Keccak)**: absorb input into state; squeeze output; immune to length extension
- **Random oracle model**: idealization where H is a truly random function; oracle queries are the only evaluation method
- **Fingerprinting**: hash as unique file identifier; collision resistance ensures uniqueness
- **Password hashing**: store H(salt || password); salt prevents rainbow table attacks; use Argon2/bcrypt for slow hash
- **Key derivation (HKDF)**: HMAC-based key derivation; extract randomness then expand to desired length

## Mental Models
- Merkle tree: "binary tree of trust"; root hash is a single commitment to all leaves; proof reveals path (O(log n) hashes)
- Commitment: "sealed envelope": commit(m) is like sealing m in an envelope; open(com, r, m) breaks the seal
- Use "birthday bound → halve output bits" as rule: 256-bit SHA-256 gives 128-bit collision security

## Anti-patterns
- **Using MD5 or SHA-1**: collision attacks exist; never use for security-critical applications
- **H(key || m) as MAC**: length-extension attack allows forging H(key || m || padding || m') without key; use HMAC instead
- **Storing passwords in plaintext or unsalted hash**: rainbow table attacks recover passwords in seconds; always salt
- **Truncating hash to <128 bits**: reduces collision security below 64-bit; unacceptable for modern systems

## Code Examples
```python
import hashlib, hmac, os, secrets

def hash_file(path: str) -> str:
    """Fingerprint a file with SHA-256 — collision resistant."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def commit(message: bytes) -> tuple[bytes, bytes]:
    """Hash-based commitment scheme: binding + hiding."""
    r = secrets.token_bytes(32)  # 256-bit random nonce (hiding)
    com = hashlib.sha256(r + message).digest()  # binding via collision resistance
    return com, r

def open_commitment(com: bytes, r: bytes, message: bytes) -> bool:
    expected = hashlib.sha256(r + message).digest()
    return hmac.compare_digest(com, expected)

def merkle_root(leaves: list[bytes]) -> bytes:
    """Compute Merkle root; root commits to all leaves."""
    layer = [hashlib.sha256(leaf).digest() for leaf in leaves]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])  # duplicate last for odd counts
        layer = [hashlib.sha256(layer[i] + layer[i+1]).digest()
                 for i in range(0, len(layer), 2)]
    return layer[0]
```
- **What it demonstrates**: file fingerprinting, hiding+binding commitment, and Merkle tree root — all implementable with Python's `hashlib`

## Worked Example
**Merkle tree for action log integrity** (Hermes application):
- Agent takes N actions a₁, ..., aₙ during a session
- Compute Merkle root r = MT(H(a₁), ..., H(aₙ))
- Store r in a trusted location (signed, or on a separate log store)
- To audit action aᵢ: retrieve aᵢ and the O(log N) sibling nodes (authentication path)
- Verifier recomputes path hashes and checks against root r
- Security: if any aᵢ is tampered, the root will not match; binding from collision resistance of H

## Key Takeaways
1. SHA-256 provides 128-bit collision security; SHA-3 is immune to length-extension attacks
2. HMAC_k(m) is the correct way to use hash functions for MAC — never H(key || m)
3. Commitment schemes (H(r || m)) provide binding + hiding with a single hash call
4. Merkle trees authenticate N values with O(log N) proof size; essential for scalable integrity
5. Password hashing must use slow functions (Argon2, bcrypt) with salts — not bare SHA-256
6. Birthday attacks find collisions in 2^{n/2} evaluations; 256-bit output gives 128-bit security

## Connects To
- **Ch 4**: HMAC as MAC built from hash function
- **Ch 7**: SHA-2, SHA-3 concrete constructions; MD5/SHA-1 weaknesses
- **Ch 13**: Hash-and-Sign paradigm for digital signatures
- **Ch 15**: Commitment schemes used in secret sharing and ZK proofs

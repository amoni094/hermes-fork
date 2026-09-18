# Patterns — Applied Cryptographic Constructions (Katz & Lindell)

## Pattern 1: HMAC-Based Integrity Verification

**When to use**: Verify that a file, message, or data structure has not been tampered with; requires shared secret key.

**How**:
1. Generate a uniformly random 256-bit MAC key (once, stored securely)
2. Compute tag = HMAC-SHA256(key, content)
3. Store or transmit (content, tag) separately or bound together
4. On verification: recompute HMAC; compare with `hmac.compare_digest()` (constant-time)

**Trade-offs**: Requires shared key (symmetric); no public verifiability (use signatures for that). Fast (microseconds per file).

**Hermes application**: Skill integrity — MAC each skill file at write time; verify at load time. Working memory entries — tag each entry with HMAC.

```python
import hmac, hashlib, os

def skill_integrity_mac(key: bytes, path: str) -> bytes:
    with open(path, 'rb') as f:
        return hmac.new(key, f.read(), hashlib.sha256).digest()

def verify_skill_integrity(key: bytes, path: str, stored_tag: bytes) -> bool:
    current = skill_integrity_mac(key, path)
    return hmac.compare_digest(current, stored_tag)
```

---

## Pattern 2: Hash-Chain Action Log (Commitment Chain)

**When to use**: Ordered append-only log where each entry's integrity depends on all previous entries; detect insertion, deletion, or reordering.

**How**:
1. Initialize chain: h₀ = SHA256(genesis_block)
2. Append entry: h_i = SHA256(h_{i-1} || timestamp || action_data)
3. Current chain head h_n commits to entire log history
4. To verify: recompute chain from any checkpoint; compare with stored head

**Trade-offs**: O(n) verification from genesis; O(1) append. No key required (public verifiability). Cannot delete or reorder without changing all subsequent hashes.

**Hermes application**: Agent action log — each agent action extends the chain; root hash stored in trusted location; audit by replaying chain.

```python
import hashlib, json, time

class HashChain:
    def __init__(self):
        self.head = hashlib.sha256(b"genesis").digest()
        self.entries = []

    def append(self, action: dict) -> bytes:
        data = json.dumps(action, sort_keys=True).encode()
        entry_hash = hashlib.sha256(
            self.head + str(time.time_ns()).encode() + data
        ).digest()
        self.head = entry_hash
        self.entries.append((entry_hash.hex(), action))
        return entry_hash

    def verify(self) -> bool:
        h = hashlib.sha256(b"genesis").digest()
        for stored_hash, action in self.entries:
            data = json.dumps(action, sort_keys=True).encode()
            # Approximate verification (timestamps stored in entries for full replay)
            pass  # Full implementation stores timestamps in entries
        return True
```

---

## Pattern 3: Hash-Based Commitment Scheme

**When to use**: Commit to a value without revealing it; later reveal to prove the committed value; binding + hiding.

**How**:
1. Choose random nonce r ← {0,1}^256
2. Compute commitment: com = SHA256(r || message)
3. Publish com; keep (r, message) secret until reveal
4. To reveal: publish (r, message); verifier checks SHA256(r || message) == com

**Trade-offs**: Binding (collision resistance of SHA-256); hiding (preimage resistance + randomness of r). No key needed. Cannot update commitment without revealing.

**Hermes application**: Agent commits to an action plan before execution; reveals after; prevents post-hoc rationalization of different actions.

```python
import hashlib, secrets

def commit(message: bytes) -> tuple[bytes, bytes]:
    """Returns (commitment, nonce). Keep nonce secret until reveal."""
    nonce = secrets.token_bytes(32)
    com = hashlib.sha256(nonce + message).digest()
    return com, nonce

def verify_commitment(com: bytes, nonce: bytes, message: bytes) -> bool:
    expected = hashlib.sha256(nonce + message).digest()
    import hmac
    return hmac.compare_digest(com, expected)
```

---

## Pattern 4: PRF-Based Session Token Generation

**When to use**: Generate unpredictable, unique session tokens or nonces from a master key and a counter/context.

**How**:
1. Generate master key K ← {0,1}^256 (once, stored securely)
2. For each session: token = HMAC-SHA256(K, session_id || timestamp || purpose)
3. Token is pseudorandom and unique per (session_id, purpose) pair
4. Verify by recomputing; no separate storage needed if context is deterministic

**Trade-offs**: Requires master key. Tokens are deterministically reproducible from context (good for stateless verification). If K leaks, all tokens are compromised.

```python
import hmac, hashlib, time

def generate_session_token(master_key: bytes, session_id: str, purpose: str) -> bytes:
    context = f"{session_id}:{purpose}:{int(time.time()) // 3600}".encode()
    return hmac.new(master_key, context, hashlib.sha256).digest()
```

---

## Pattern 5: Merkle Tree for Batch Integrity

**When to use**: Authenticate N items with a single root hash; prove inclusion of any item in O(log N); append-only sets.

**How**:
1. Compute leaves: leaf_i = SHA256(item_i)
2. Build tree: internal_node = SHA256(left_child || right_child)
3. Root authenticates all N items
4. Proof of inclusion: O(log N) sibling nodes along path from leaf to root
5. Verify proof: recompute path hashes; compare root with stored root

**Trade-offs**: O(N) build; O(log N) proof; O(1) root storage. Efficient for N up to millions. Tree must be rebuilt to update (or use dynamic Merkle tree).

**Hermes application**: Batch skill verification — Merkle root over all skill files; verify one skill in O(log N) without re-reading all.

```python
import hashlib

def merkle_root(items: list[bytes]) -> bytes:
    if not items:
        return hashlib.sha256(b"").digest()
    layer = [hashlib.sha256(item).digest() for item in items]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i+1]).digest()
                 for i in range(0, len(layer), 2)]
    return layer[0]
```

---

## Pattern 6: Encrypt-then-MAC (Authenticated Encryption Composition)

**When to use**: Need confidentiality + integrity from separate encryption and MAC primitives.

**How**:
1. Encrypt: c = Enc_{k1}(m) (using AES-CTR or ChaCha20 with random nonce)
2. MAC: t = MAC_{k2}(c) (HMAC-SHA256 over ciphertext)
3. Send (c, t); use separate keys k1 ≠ k2
4. Verify: check t first (constant-time); decrypt only if tag valid

**Trade-offs**: Provably achieves AE security. Two keys needed (use HKDF to derive from master key). Prefer AES-GCM or ChaCha20-Poly1305 when available (single-pass, standardized).

---

## Pattern 7: Password Hashing with Salt

**When to use**: Store passwords securely; resist offline dictionary/rainbow table attacks.

**How**:
1. Generate random salt s ← {0,1}^256
2. Compute stored_hash = Argon2id(password, s, memory=64MB, iterations=3)
3. Store (s, stored_hash); never store plaintext or MD5/SHA-1 hash
4. Verify: recompute Argon2id with stored salt; compare with `hmac.compare_digest()`

**Trade-offs**: Slow by design (Argon2id: 100ms+ per hash); makes offline attacks expensive. SHA-256 without salt → rainbow table attack in seconds.

---

## Pattern 8: Key Derivation with HKDF

**When to use**: Derive multiple independent keys from a single master secret or shared DH value.

**How**:
1. Extract: prk = HMAC-SHA256(salt, input_key_material) — "condenses" randomness
2. Expand: k_i = HMAC-SHA256(prk, info || counter) for each needed key
3. Each k_i is computationally independent even if prk is known

**Trade-offs**: Requires good entropy in input_key_material. salt can be public. info binds key to purpose (prevents cross-purpose misuse).

```python
import hmac, hashlib

def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()

def hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    t, okm, counter = b"", b"", 0
    while len(okm) < length:
        counter += 1
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
    return okm[:length]
```

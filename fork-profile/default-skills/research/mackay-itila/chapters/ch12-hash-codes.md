# Chapter 12: Hash Codes: Codes for Efficient Information Retrieval

## Core Idea
Error-correcting codes and hash codes are the same geometry run with different noise models: ECC recovers a nearest codeword after channel noise; hashing maps keys so that random collisions are rare and lookups are O(1). Information theory bounds how short a fingerprint can be while still identifying a record.

## Frameworks Introduced
- **Retrieval as communication**: the “channel” is the query; the “codeword” is the stored key/fingerprint.
- **Hashing**: compute h(key) ∈ {1..M}; store records in buckets. Collision probability is a birthday-paradox / typical-set calculation.
- **Bloom-filter style thinking** (MacKay’s fingerprinting): store a short syndrome/hash of each item; false positives scale as 2^{−b} per b-bit hash.
- **Source coding connection**: a perfect hash for a known set of N keys is a compressor of the key to log2 N bits.

## Key Concepts
- **Collision**: two keys with the same hash. For random h, P(collision in N keys, M bins) ≈ 1 − exp(−N(N−1)/2M).
- **Load factor** N/M: keep below ~0.5–0.7 for chaining/open addressing.
- **Universal hash family**: P(h(x)=h(y)) = 1/M for x≠y; analysis need not assume a magical fully random h.
- **Information bound**: to distinguish N items you need ≥ log2 N bits; to have false-positive ε you need ~ log2(1/ε) extra bits.
- **Coding vs hashing**: ECC deliberately clusters around codewords; hashing wants images *uniform and unclustered*.

## Key Equations
- P(at least one collision) ≈ 1 − exp(−N²/2M)
- Expected collisions ≈ N²/(2M)
- Fingerprint false-positive ≈ 2^{−b} for b-bit random hash
- Storage for N items at FP rate ε: ~ N log2(1/ε) bits (Bloom-like)

## Algorithms and Techniques
**Design a fingerprint store**
1. Choose acceptable false-positive ε and N.
2. Set b = log2(N/ε) or similar depending on whether you need unique IDs vs membership.
3. Use a universal hash (mod prime, multiply-shift).
4. On query, compare fingerprints; on match, verify full key if FP is not tolerable.

**Birthday-paradox sanity check**: M ≈ N² to make collisions unlikely among all pairs; M ≈ N for expected O(1) per item (table hashing).

## Mental Models
- Use hashing when you need *average-case speed* and can tolerate rare collisions; use ECC when you need *worst-case recovery from noise*.
- Think of a b-bit hash as a random linear syndrome (foreshadows Ch 13 duals and Ch 47).
- Retrieval capacity: you cannot beat log2 N bits to name an item in a known list.

## Worked Example
N=10^6 keys. Want P(some collision)<1% in a hash table.
- 1−exp(−N²/2M)=0.01 ⇒ N²/2M ≈ 0.01 ⇒ M ≈ N²/0.02 = 5×10^{10} bins — this is *unique fingerprinting of all pairs*.
- For a normal hash table you instead accept collisions and chain: M=2×10^6, expected ~0.25 collisions per bin, P(empty)≈e^{−0.5}≈0.61. Completely different regime: do not apply the birthday N² law when you *wanted* buckets to hold ~1 item.

b=32-bit fingerprints: FP per comparison 2^{−32}; after 10^6 random queries against one stored fingerprint, FP expected ~10^6/2^{32}≈0.0002.

## Anti-patterns
- **Using cryptographic hashes for in-memory tables**: slow; universal hashes suffice.
- **Birthday-paradox M~N² for ordinary dictionaries**.
- **Storing only hashes when the adversary can collide** (need crypto hashes then).
- **Confusing ECC minimum distance with hash avalanche**: both want random-looking maps, opposite clustering.

## Key Takeaways
1. Hashing is information theory of identification under random collisions.
2. Choose M ~ N for tables; M ~ N²/ε for globally unique short IDs.
3. b-bit fingerprints fail with 2^{−b}; that is the right units.
4. A hash is a compressor of the key if the set is known.
5. Same linear-algebra tools as codes, different success criterion.

## Connects To
- **Ch 4**: typical-set counting / birthday bounds.
- **Ch 13**: linear maps, dual codes, random linear hash = random H.
- **Ch 47**: sparse H as both code and hash.
- **Ch 50**: fountain codes as rateless hashes of packets.

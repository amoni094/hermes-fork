# Ch 8 — Data Structures

Random reordering and random hash functions replace worst-case balanced trees.

## Random treaps (Ch 8.2)

Each key gets a random priority. Heap-order on priorities, BST-order on keys. Equivalent to a random binary search tree (random insertion permutation). Expected depth `O(log n)`; expected rotation cost for insert/delete `O(log n)`.

## Skip lists (Ch 8.3)

Each key is promoted to level `i+1` independently with probability `1/2` (geometric height). Search, insert, delete: expected `O(log n)` time, expected `O(n)` space.

**Theorem 8.11.** In a random skip list of `n` keys, FIND / INSERT / DELETE take expected `O(log n)` time.

Height is `O(log n)` w.h.p. (Chernoff / geometric tails).

## Hash tables (Ch 8.4)

### 2-universal families (Ch 8.4.1–8.4.3)

Family `H ⊆ {h : U → [m]}` is **2-universal** if for all `x ≠ y`,

`P_{h∼H}[h(x) = h(y)] ≤ 1/m`

(or `O(1/m)` in some texts). Then expected collisions involving `x` are `|S|/m`; chaining expected lookup `O(1+α)`, `α=|S|/m`.

**Construction.** Prime `p ≥ |U|`, `h_{a,b}(x) = ((a x + b) mod p) mod m`, `a ∈ F_p^×`, `b ∈ F_p`.

Proof is the same arithmetic as pairwise independence (Ch 3.4).

### Strongly universal (Ch 8.4.4)

`P[h(x)=α ∧ h(y)=β] = 1/m²` for `x≠y`. Equivalent to pairwise-independent hash values. Chebyshev applies directly to bucket loads.

### Perfect hashing (Ch 8.5)

`h` is **perfect** for static `S` if injective on `S`.

FKS two-level: a 2-universal top-level hash into `n` buckets; for bucket `i` of size `b_i`, a second-level table of size `O(b_i²)` that is collision-free with constant probability. Expected total space `O(n)` because `E[∑ b_i²] = O(n)` for 2-universal hashing. Worst-case `O(1)` lookup.

**Exercise 8.11.** A perfect hash exists for any `S` (in fact many); constructing it randomly is Las Vegas: retry until injective.

Perfect hashes do **not** support efficient range queries or nearest-neighbour — only membership.

## Hermes

- Routing weight buckets / load balancing: 2-universal `h_{a,b}`; Chebyshev on max load. Pairwise independence is enough (user application 3).
- Static skill-id map: FKS perfect hash, `O(1)` lookup.
- Ordered skill keys with random priorities: treap / skip list, don't hand-balance.

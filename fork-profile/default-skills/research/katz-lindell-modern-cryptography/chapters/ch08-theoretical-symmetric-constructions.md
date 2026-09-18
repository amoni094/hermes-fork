# Chapter 8: Theoretical Constructions of Symmetric-Key Primitives

## Core Idea
All symmetric-key primitives (PRG, PRF, PRP) can be constructed from one-way functions (OWF), the minimal computational hardness assumption. This theoretical foundation shows that if OWFs exist, secure encryption is possible — and all of modern private-key cryptography follows.

## Key Concepts
- **One-way function (OWF)**: f: {0,1}* → {0,1}*; easy to compute; hard to invert (no PPT adversary finds x' with f(x') = f(x) for random x, except negl. prob.)
- **Candidate OWFs**: multiplication (factoring), discrete exponentiation (DLP), AES (assumed one-way)
- **Hard-core predicate**: B(x) is a hard-core predicate for f if given f(x), no PPT adversary predicts B(x) with probability > 1/2 + negl
- **Goldreich-Levin theorem**: for any OWF f, the inner product ⟨x, r⟩ mod 2 is a hardcore predicate of f'(x, r) = (f(x), r)
- **PRG from OWF**: Blum-Micali, Blum-Blum-Shub; constructed via hard-core predicates; expands by one bit per OWF evaluation
- **PRF from PRG (GGM construction)**: binary tree where node at path b₁b₂...bₙ computes F_k(b₁b₂...bₙ) via applying PRG selectively; O(n) calls for n-bit key
- **PRP from PRF (Feistel)**: 3-round Feistel with PRF gives PRP; 4-round gives strong PRP (indistinguishable from random permutation even with decryption oracle)
- **Computational indistinguishability**: two distribution ensembles {X_n} and {Y_n} are computationally indistinguishable if no PPT distinguisher has non-negligible advantage

## Mental Models
- OWF is the foundation: everything from PRG to MACs to signatures can be built from it
- GGM tree: key k is the root; PRG doubles each node; path to leaf determines PRF output
- Hybrid argument: to prove A ≈_c B, interpolate through hybrids H₀ = A, H₁, ..., Hₙ = B; show adjacent hybrids are computationally indistinguishable

## Key Takeaways
1. OWF is the minimal assumption for private-key cryptography; P ≠ NP is necessary but not sufficient
2. Goldreich-Levin gives hard-core bits from any OWF; hard-core bits → PRG
3. GGM tree constructs PRF from PRG; Feistel constructs PRP from PRF — the full hierarchy
4. Hybrid arguments are the main proof technique for showing computational indistinguishability
5. These constructions are theoretically optimal but impractical; AES/ChaCha20 are used in practice

## Connects To
- **Ch 3**: PRG and PRF defined; now formally constructed
- **Ch 9**: OWFs realized by number-theoretic problems (factoring, DLP)

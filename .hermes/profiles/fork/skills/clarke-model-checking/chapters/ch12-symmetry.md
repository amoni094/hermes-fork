# Chapter 12: Symmetry

## Core Idea
If a group of permutations of S commutes with R and preserves L (or permutes identical processes), the orbit quotient is bisimilar to M. Check φ on representatives.

## Frameworks Introduced
- **Symmetry group G** acting on S: for g∈G, R(s,s') ⇒ R(g(s), g(s')), and L(s)=L(g(s)) when atoms are symmetric (or atoms are permuted consistently).
  - When to use: n identical workers, n identical cache lines, n identical cron clones.
  - How: choose a canonical representative per orbit (e.g. sorted id tuple); build R on representatives.
- **Annotated symmetries**: some atoms name a specific process (pc_i). Then φ must be symmetric or you use scalarset restrictions (Ip/Murφ style, discussed in the literature around this chapter).

## Key Concepts
- **Orbit**: {g(s) | g∈G}. Quotient state = orbit.
- **Soundness**: quotient is bisimilar ⇒ all CTL* preserved.
- **Representative function** ξ(s): computational bottleneck; must be cheap (hash canonicalization).

## Mental Models
- If swapping two process ids cannot change the spec, you should not store both orders.
- Symmetry does not help a fully asymmetric formula (AG writer_3).

## Anti-patterns
- Quotienting while φ mentions a distinguished id.
- Dynamic symmetry (heap allocations) without a canonical heap — 1999 static group action does not apply out of the box.

## Worked Example
N identical skill-router workers. States are assignments of {idle, busy} to workers. G = S_N. Orbit of “exactly k busy” is one abstract state. GF(skill_queried → F skill_returned) is symmetric; check on k=0..N.

## Key Takeaways
1. Group action + label invariance ⇒ bisimilar quotient.
2. Formula must respect the same symmetry.
3. Combine with BDDs carefully (orbit BDDs are nontrivial).

## Connects To
- **Ch 9**: bisimulation.
- **Ch 13**: parameterized n is a different problem (unbounded family).

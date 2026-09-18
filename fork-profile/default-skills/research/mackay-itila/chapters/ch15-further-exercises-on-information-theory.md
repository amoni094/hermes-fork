# Chapter 15: Further Exercises on Information Theory

## Core Idea
This chapter is a problem set, not new theory: it forces you to compute entropies, design codes, and apply typicality until the Ch 1–14 toolkit is automatic. Treat it as a diagnostic: if an exercise feels foreign, reread the cited chapter.

## Frameworks Introduced
- **Exercise-driven consolidation** of: entropy calculus, Huffman/Kraft, typical sets, capacity calculations, linear codes, hash/birthday bounds.
- **MacKay’s difficulty tags**: [1] warm-up, [2] should-do, [3] hard, [4] researchy. Numbers in brackets in the book are part of the pedagogy.

## Key Concepts
- Recycled objects: BSC/BEC/Z-channel capacities, Hamming code, jointly typical pairs, DKL as extra code length, weighing problems, integer codes.
- **Sanity checks** you should now pass without notes:
  - H2(0)=H2(1)=0, H2(0.5)=1, H2(0.1)≈0.47
  - C_BSC(f)=1−H2(f), C_BEC=1−ε
  - Huffman L ∈ [H, H+1)
  - Hamming bound vs GV vs Shannon

## Key Equations
- All of Ch 2, 4, 8, 9, 10 — this chapter does not add new named equations.
- Useful numerics: log2 e ≈ 1.443, ln 2 ≈ 0.693, log2 10 ≈ 3.32

## Algorithms and Techniques
**How to attack a MacKay exercise**
1. Identify whether it is forward probability, inverse probability, a code construction, or a bound.
2. Write the ensemble (alphabet + P) explicitly.
3. Compute H / I / L symbolically before plugging numbers.
4. Check units (bits vs nats) and extremes (p→0, p→1/2).
5. If it asks “is this possible?”, compare to H or C before constructing.

## Mental Models
- If you cannot do the [2]s, do not proceed to Part IV pretending fluency.
- Many later “new” ideas (Occam, variational bounds, LDPC density evolution) are these same counting arguments.

## Worked Example
Typical exercise pattern: “A source emits symbols from {a,b,c} with probabilities 1/2, 1/4, 1/4. A channel is a BEC(ε=1/2). Can you communicate the source reliably at 1 channel use per source symbol?”
- H(source)=1.5 bits. C_BEC=0.5 bits/use. 1.5 > 0.5, so **no**. You need at least 1.5/0.5=3 channel uses per symbol. Compression then channel coding; do not Huffman-then-uncoded-BEC.

## Anti-patterns
- **Skipping exercises** then getting lost in Ch 10 proofs or Ch 47.
- **Inventing a code when a bound already forbids it**.
- **Mixing log2 and ln in numerical I(X;Y)**.

## Key Takeaways
1. This chapter is optional as reading, mandatory as practice.
2. Always compare requested rates to H (sources) or C (channels) first.
3. Keep a one-page sheet of H2(p) and standard capacities.
4. Difficulty tags tell you when to stop.

## Connects To
- **Ch 1–14**: the syllabus being drilled.
- **Ch 16+**: optional IT topics assume this fluency.

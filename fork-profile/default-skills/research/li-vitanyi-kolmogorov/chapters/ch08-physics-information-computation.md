# Chapter 8: Physics, Information, and Computation

## Core Idea

Kolmogorov complexity analyzes individual messages where Shannon entropy analyzes ensembles, and the two agree in expectation for computable distributions. The rest of the chapter develops reversible computation (no forced energy dissipation), the universal information distance E(x, y) = max{K(x|y), K(y|x)} and its normalized form NID (a similarity metric), thermodynamic and algorithmic entropy, quantum Kolmogorov complexity, and compression as a phenomenon in nature.

## Key Concepts

- Shannon vs Kolmogorov: H(P) is uncertainty of a random variable with law P; C(x) and K(x) are information in one x. For computable P, E_P[K(X)] = H(P) + K(P) + O(1) (precise forms in §8.1); similarly E[C(X)] ∼ H(P) under extra conditions (already in §2.8).
- Rate-distortion (algorithmic): lossy description length vs Hamming (or other) distortion for an individual x; denoising as “throw away the incompressible residue.”
- Reversible computation: bijective transition function; Landauer’s principle — erasing one bit costs kT ln 2; reversible computation can in principle dissipate arbitrarily little energy except for final copy/erase of garbage.
- Reversible Turing machine and reversible Kolmogorov complexity Kr: shortest reversible program taking (a blank or given input) to x, possibly with garbage that must itself be cleanable.
- Admissible information distance D(x, y): nonnegative, 0 iff x = y, upper semicomputable, and satisfying the density (Kraft-type) requirement sum_{y ≠ x} 2^{−D(x,y)} ≤ 1.
- Universal information distance E1(x, y) = max{K(x|y), K(y|x)}. Minorizes every admissible distance up to O(1): E1(x, y) ≤ D(x, y) + O(1).
- Sum distance E4 = K(x|y) + K(y|x); E3 is E4 up to a log term. E3 can lie anywhere between E1 and 2 E1.
- Normalized information distance (NID, Def. 8.4.1): e(x, y) = max{K(x|y), K(y|x)} / max{K(x), K(y)} (with 0/0 := 0). A metric up to O(1/max{K(x),K(y)}) and the “similarity metric” used for clustering.
- Normalized compression distance (NCD): practical NID with K replaced by a real compressor C: NCD(x, y) = [C(xy) − min{C(x), C(y)}] / max{C(x), C(y)}.
- Information diameter: radius of a set under E or NID; used for clustering quality and for “the information in a family of objects.”
- Algorithmic entropy: K(microstate) as the physical entropy of an individual configuration; regular microstates have small K, random ones have K ≈ log |Γ|.
- Quantum Kolmogorov complexity: length of a shortest classical (or quantum) program for a universal quantum TM that outputs a state close to |ψ⟩. Several non-equivalent proposals surveyed in §8.8.

## Frameworks and Methods

- Expectation identity: convert Shannon theorems into almost-sure Kolmogorov theorems plus O(K(P)) terms via the coding theorem and typicality.
- Denoising / lossy compression: two-part code (model + residual); residual incompressible ⇒ treat as noise (link to structure function, Ch 5).
- Reversible simulation of irreversible computation: Bennett’s pebble game / history-saving then uncomputing; garbage is reversibly erased after copying the output. Table 8.1: combining x→y and y→x irreversible maps into a reversible x↔y.
- Universal distance: E1 is the greatest lower bound (up to O(1)) on all admissible distances, analogous to m dominating all semimeasures.
- NID clustering: compute NCD with a compressor (gzip, bzip2, PPM, CompLearn); hierarchical clustering of the distance matrix (mammalian mtDNA, file types, MNIST digits, Wikipedia, novels-by-author — Figures 8.7–8.9, Tables 8.3–8.4).
- Thermodynamics: Carnot cycle, adiabatic demagnetization; Maxwell’s demon / Szilard engine resolved by the memory-erasure cost matching kT ln 2 per bit, identified with K of the record.

## Key Results and Theorems

- Entropy–complexity: for computable P, H(P) ≤ sum_x P(x) K(x) ≤ H(P) + K(P) + O(1). Thus K-expectation equals entropy up to the complexity of the model.
- Analogues of mutual information, chain rule, and rate-distortion hold individually with K in place of H, up to the slop of Ch 3.
- Reversible computation: any irreversible TM running in time t, space s can be simulated reversibly in time ≈ t^{1+ε} and space ≈ s log t (Bennett tradeoffs); energy dissipation can be confined to the leftover output copy.
- Universality of E1 (Thm 8.3.1 lineage): E1(x, y) ≤ D(x, y) + O(1) for every admissible D. Hamming distance, edit distance, etc., after Kraft-normalization, sit above E1.
- Metricity: E1 satisfies the triangle inequality up to O(log n) (or O(1) in carefully normalized K-forms). NID satisfies metric inequalities up to vanishing additive terms.
- Muchnik’s theorem / minimal overlap: shortest programs p : y ↦ x and q : x ↦ y can be chosen with maximal mutual information I(p : q) ≈ min{l(p), l(q)}; whether they can be chosen independent depends on the allowed additive term (O(log(K(x|y)+K(y|x))) no; O(log K(x, y)) yes).
- NID is a universal similarity metric: it minorizes every other upper-semicomputable normalized distance satisfying a density inequality.
- NCD theorems: if the compressor is “normal” (C(xx) ≈ C(x), C(xy) ≈ C(yx), etc.), NCD approximates NID. Real compressors only approximately normal.
- Algorithmic thermodynamics: Clausius / Boltzmann entropy of a macrostate Γ is max_{x ∈ Γ} K(x | Γ) ≈ log |Γ| for typical x; a regular (compressible) microstate has algorithmic entropy ≪ thermodynamic entropy and can be exploited (Szilard).
- Quantum K: no single canonical analogue; qubit programs, classical programs outputting circuit descriptions, and Brudno-type theorems for quantum typicality are all treated as partial.

## Algorithms and Techniques

1. Reversible AND from Toffoli / billiard-ball (Fredkin–Toffoli) gates; Figures 8.3–8.6.
2. Bennett uncomputing: compute forward, copy output, reverse the forward computation to clean garbage.
3. E1 computation (noncomputable): approximate K(x|y) from above by compression. Practical substitute: NCD with a real compressor.
4. NCD pipeline: compress x, y, xy (and optionally yx); plug into the NCD formula; cluster with neighbor-joining or hierarchical clustering.
5. Denoising: compress with a model class; treat the incompressible residual as noise; reconstruct from the model part only (Figure 8.2, noisy cross).
6. Information diameter of a set X: max_{x,y ∈ X} e(x, y) or min-radius centers; used as a clustering quality score.

## Anti-patterns

- Equating H(X) with K(x) for a “random-looking” x without stating the ensemble: a compressible x in a high-entropy ensemble is a nonequilibrium microstate.
- Using sum of conditional complexities E4 as “the” distance: it is not universal in the E1 sense and can be twice too large.
- Treating NCD as NID: gzip fails normality (C(xy) vs C(yx), C(xx) ≫ C(x) for large x). Use NCD as a heuristic with compressor caveats.
- Ignoring Landauer while counting thermodynamic cost of computation: logically irreversible steps, not computation per se, cost energy.
- Claiming quantum K is just K of the amplitude list: phases and bases make that representation-dependent; state the model.
- Triangle inequality for raw max{C(x|y), C(y|x)} without prefix and O(log) slop: use K and the book’s E1.

## Key Takeaways

1. Entropy is expected Kolmogorov complexity (plus K of the model); complexity is individual entropy.
2. E1 is the universal admissible distance; NID is the universal similarity metric; NCD is the experimental version.
3. Reversibility is the computational content of the second law: erasure, not computation, dissipates energy.
4. Algorithmic entropy explains Maxwell’s demon: the demon’s memory is a compressible record whose erasure pays the debt.
5. Compression in nature (ant navigation, DNA, file clustering) is an empirical counterpart of K, always via real compressors.

## Connects To

- Ch 2–4: expectation identities and E1 rest on invariance, symmetry of information, and the coding theorem.
- Ch 5: NID clustering is two-part MDL similarity; denoising is the structure function.
- Ch 7: reversible simulation overheads and logical depth as “buried” computation in physical states.

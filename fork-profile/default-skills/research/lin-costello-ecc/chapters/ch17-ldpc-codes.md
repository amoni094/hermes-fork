# Chapter 17: Low-Density Parity-Check Codes

## Core Idea
An LDPC code is the null space of a sparse parity-check matrix H. Sparseness makes iterative message passing (belief propagation on the Tanner graph) practical and, for well-designed ensembles, approaches the Shannon limit with more parallelism and typically lower error floors than turbo codes. This chapter emphasizes *structured* constructions (finite geometry, circulant, RS-based) as well as Gallager random ensembles.

## Key Concepts
- **(γ,ρ)-regular LDPC** (Def. 17.1): H has γ ones per column, ρ ones per row; any two columns overlap in at most λ=1 position; γ,ρ ≪ n. Density r = ρ/n = γ/J.
- **Irregular LDPC**: variable/check degree distributions λ(x), ρ(x); better thresholds than regular (Richardson–Urbanke), at the cost of floor and implementation uniformity.
- **Tanner graph**: bipartite graph, variable nodes (bits) ↔ check nodes (rows of H). Edge = a 1 in H. A cycle of length 4 is two columns overlapping in two places — forbidden by λ≤1 (girth ≥ 6).
- **Belief propagation / sum-product**: iterative exchange of LLRs between variables and checks; exact MAP on trees, approximate on loopy graphs.
- **Bit-flipping (Gallager A/B)**: hard-decision cousin; flip bits that fail many checks. Majority-logic (Ch 8) when checks are orthogonal.
- **EG-LDPC / PG-LDPC**: H = incidence matrix of Euclidean/projective geometry flats (Ch 8). Cyclic or quasi-cyclic, girth ≥6, easy encoding via LFSR, excellent floors.
- **Gallager construction**: stack γ permutation copies of a block-diagonal ρ-ones row; search permutations to avoid 4-cycles.
- **QC-LDPC**: H is an array of circulants; encoder is shift registers; 802.11 / DVB-S2 / 5G-like structure (standards post-date the book but match this chapter’s circulant decomposition).
- **Masking, row/column splitting, cycle breaking, shortening**: tools to derive irregular or larger-girth codes from a geometry/Gallager mother matrix.
- **BIBD and shortened-RS constructions**: combinatorial designs as H; RS 2-information-symbol evaluations give QC-LDPC.

## Frameworks and Methods
- **When LDPC vs turbo vs algebraic**:
  - LDPC: long blocks, high throughput (parallel checks), need low floor (storage, DVB, 5G).
  - Turbo: moderate K, existing RSC/BCJR IP, 3G/CCSDS.
  - Algebraic: short n, guaranteed t, no waterfall delay.
- **d_min bound**: for regular codes with λ≤1, d_min ≥ γ+1 (one-step MLG). True d_min is often much larger for random ensembles but hard to compute; geometry codes have known combinatorial distances.
- **Encoding**:
  - Generic: Gaussian elimination of H → systematic G (dense — bad).
  - Richardson–Urbanke approximate-lower-triangular H: O(n) encode.
  - Cyclic EG/QC: LFSR / polynomial multiply, O(n) and hardware-friendly.

## Key Results
- Example 17.1: a 15×15 4-regular H, density 0.267, null space (15,7) d_min=5, actually cyclic BCH.
- Example 17.2: Gallager k=5, ρ=4, γ=3 → (20,7) d_min=6, density 0.20.
- Finite-geometry LDPC: often cyclic, girth 6 or 8, no error floor down to 10^{-9} in the book’s simulations — their headline advantage vs early random LDPC/turbo.
- Irregular ensembles: optimized degree distributions approach capacity on BI-AWGN (density evolution threshold).
- Concatenating LDPC with turbo/algebraic (17.19) is optional insurance for floors; less necessary for well-designed QC-LDPC.

## Algorithms and Techniques
**Sum-product (LLR) on a Tanner graph** — one iteration:
1. Variable-to-check: L_{v→c} = L_ch(v) + Σ_{c'≠c} L_{c'→v}  (init L_{c→v}=0).
2. Check-to-variable (box-plus):
   L_{c→v} = 2 tanh^{−1}( ∏_{v'≠v} tanh(L_{v'→c}/2) )
   or min-sum: L_{c→v} ≈ (∏ signs) min |L_{v'→c}|  (with optional scale 0.75).
3. After I iterations (or syndrome 0): decide sign of L_ch + Σ_c L_{c→v}.

**Hard bit-flip**:
Compute all syndromes. Flip bits whose number of unsatisfied checks exceeds a threshold. Repeat. Cheap, ~1–2 dB worse than BP.

**Geometry H**:
Points vs lines of EG(m, 2^s). Each column weight = lines through a point. λ≤1 because two points determine at most one line. Cyclic if you puncture the origin and use a Singer cycle.

**Column/row splitting**:
Replace a weight-γ column by two columns that partition its ones → lower variable degree, longer code, often better threshold.

**Circulant decomposition**:
Factor a cyclic H into an array of b×b circulants (QC model). Shift-register encoder; parallel decoder with b-fold lifting.

## Anti-patterns
- **4-cycles (λ≥2)**: BP messages double-count immediately; floors and threshold loss. Enforce girth ≥6 at construction.
- **Dense Gaussian G for encoding**: O(n^2) storage kills the sparse advantage; use QC/triangular H.
- **Too few iterations at the cliff**: like turbo, 5 vs 50 iterations is worth tenths of a dB to a dB.
- **Min-sum without scaling/offset**: consistent SNR loss vs sum-product.
- **Tiny n with irregular ultra-high degrees**: degree-1 variables or overstretched checks wreck the floor; irregularity wants long n.
- **Stopping at γ+1 as if it were the true d_min**: MLG bound is weak; floors come from trapping sets, not that bound.

## Key Takeaways
1. LDPC = sparse H + iterative BP on the Tanner graph.
2. λ≤1 (girth ≥6) is the structural hygiene condition; geometries give it for free.
3. Regular geometry/QC codes: great floors, simple encode; irregular random: best thresholds.
4. Decoder is embarrassingly parallel — the practical reason LDPC won 5G/DVB/WiFi vs turbo.
5. Bit-flip / MLG is the low-power fallback; min-sum is the hardware workhorse.

## Connects To
- **Ch 3**: code = null space of H.
- **Ch 8**: orthogonal checks, EG/PG incidence, MLG as one-shot BP.
- **Ch 16**: competing iterative capacity-approaching scheme.
- **Ch 15**: concatenation with turbo/RS if floors remain.
- **code-selection-guide.md**: DVB-S2 LDPC, 5G NR LDPC, 802.11 LDPC.

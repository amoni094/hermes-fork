# Glossary — Computational Optimal Transport

## Notation

| Symbol | Meaning |
|---|---|
| Σ_n | Probability simplex {a ∈ R+^n : Σa_i=1} |
| U(a,b) | Transportation polytope {P≥0: P1=a, P^T1=b} |
| LC(a,b) | Kantorovich OT cost with cost matrix C |
| L^ε_C(a,b) | Entropic regularized OT cost |
| Wp(α,β) | p-Wasserstein distance |
| K | Gibbs kernel K_{ij} = exp(-C_{ij}/ε) |
| (f,g) | Dual potentials (Kantorovich) |
| (u,v) | Sinkhorn scalings (u=e^{f/ε}, v=e^{g/ε}) |
| T_#α | Push-forward of measure α through map T |
| T^#g | Pull-back of function g through map T |
| H(P) | Discrete entropy -Σ P_{ij}(log P_{ij}-1) |
| KL(α\|β) | Kullback-Leibler divergence |
| SW | Sliced Wasserstein distance |
| GW | Gromov-Wasserstein distance |
| EMD | Earth mover's distance (= W₁) |
| MMD | Maximum mean discrepancy |
| IPM | Integral probability metric |
| (α_t) | Dynamic measures (Benamou-Brenier) |
| J = αv | Momentum field for dynamic OT |

## Key Terms

### A

**Auction algorithm**: Market-inspired algorithm for assignment; buyers bid up prices for goods.

### B

**Barycenter (Wasserstein)**: `argmin_α Σ_s λ_s W₂²(α,α_s)` — Fréchet mean in W₂ geometry.

**Benamou-Brenier formula**: `W₂²(α₀,α₁) = min_{αt,vt} ∫₀¹ ∫||vt||² dαt dt` — dynamic formulation.

**Birkhoff polytope**: Set of doubly stochastic matrices = convex hull of permutation matrices.

**Birkhoff's theorem**: Vertices of U(1/n, 1/n) = permutation matrices.

**Bregman divergence**: `Bψ(a|b) = ψ(a) - ψ(b) - ⟨∇ψ(b), a-b⟩`; KL divergence is a special case.

**Bures metric**: W₂ between Gaussian distributions; `B(Σ₁,Σ₂)² = tr(Σ₁+Σ₂-2(Σ₁^{1/2}Σ₂Σ₁^{1/2})^{1/2})`.

### C

**C-transform**: `(f^C)_j = min_i(C_{ij}-f_i)` — optimal g from fixed f in the dual.

**Complementary slackness**: P_{ij}>0 ⟹ f_i+g_j=C_{ij} (mass flows only along tight dual constraints).

**Copula**: Joint distribution with uniform marginals; encodes dependency structure.

**Coupling**: Joint distribution π over X×Y with marginals α and β.

### D

**Displacement interpolation**: `αt = ((1-t)Id + tT)_#α₀` — Wasserstein geodesic.

**Doubly stochastic matrix**: Matrix with nonneg entries, row sums = 1, col sums = 1.

**Dual ascent**: Maintain feasible dual variables, improve via max-flow subproblem.

**Dual potentials (f,g)**: Solution to OT dual problem; economic interpretation as transport prices.

### E

**Earth mover's distance (EMD)**: Same as W₁; named in computer vision literature.

**Entropy function**: Convex, lower-semicontinuous function on [0,∞) used for φ-divergences.

**Entropic regularization**: Add -εH(P) to OT objective → unique, smooth, differentiable solution.

### F

**φ-divergence**: `Dφ(α|β) = ∫φ(dα/dβ) dβ` — compares densities pointwise.

**Frank-Wolfe**: Linearization-based algorithm; used for GW computation.

### G

**Gibbs kernel**: `K_{ij} = e^{-C_{ij}/ε}` — soft assignment matrix.

**Gradient flow**: Evolution αt following steepest descent of E in Wasserstein metric.

**Gromov-Hausdorff distance**: Compares metric spaces by how close they are to being isometric.

**Gromov-Wasserstein**: `GW² = min_P Σ|D_{ii'}-D'_{jj'}|² P_{ij}P_{i'j'}` — compares distributions on different spaces.

### H

**Hilbertian**: A metric is Hilbertian if it can be embedded isometrically in a Hilbert space. W_p is NOT Hilbertian.

**Hungarian algorithm**: Dual ascent algorithm for square assignment problems; O(n³).

### J

**JKO scheme**: Proximal stepping in W₂: `α_{k+1} = argmin[E(α) + W₂²(α,αk)/(2τ)]`.

### K

**Kantorovich duality**: `LC(a,b) = max_{(f,g)∈R(C)} ⟨f,a⟩+⟨g,b⟩` (strong duality for OT LP).

**Kantorovich potentials**: Dual variables (f,g) in OT; unique (for strictly convex costs).

**Kantorovich problem**: Linear program over transportation polytope; always feasible.

**Kantorovich relaxation**: Replace Monge's deterministic maps with probabilistic couplings.

**KL divergence**: `KL(α|β) = ∫log(dα/dβ) dα`; asymmetric; φ-divergence with φ(s)=s log s - s + 1.

### L

**Laguerre cells**: `Lag_j(g) = {x: c(x,y_j)-g_j ≤ c(x,y_k)-g_k ∀k}` — power diagram.

**Langevin dynamics**: Gradient flow in KL divergence; MCMC sampling algorithm.

### M

**McCann interpolation**: Wasserstein geodesic via pushforward interpolation of Monge map.

**MMD (Maximum Mean Discrepancy)**: `MMD²(α,β) = E_αk + E_βk - 2E_{α,β}k` (RKHS norm).

**Monge map**: Deterministic transport T: X→Y with T_#α=β (may not exist).

**Monge problem**: Find minimum-cost Monge map; nonconvex, may be infeasible.

**Monge-Ampère equation**: PDE `det(∂²φ/∂x²) = ρ_α(x)/ρ_β(∇φ(x))` characterizing W₂ Monge map.

**Multimarginal OT**: Couple S distributions simultaneously; generalizes pairwise OT.

### N

**Network simplex**: Primal simplex algorithm exploiting OT's network LP structure.

**NW corner rule**: Greedy initialization for network simplex; produces BFS in O(n+m) steps.

### P

**Permutation matrix**: 0-1 matrix with exactly one 1 per row and column; vertex of Birkhoff polytope.

**Power diagram**: Laguerre cells for squared Euclidean cost; weighted Voronoi diagram.

**Push-forward**: `T_#α(B) = α(T^{-1}(B))`; moves measure α through map T.

### R

**R(C)**: Set of dual-feasible potentials `{(f,g): f_i+g_j≤C_{ij} ∀i,j}`.

**Ruzicka similarity**: `Σ min(a_i,b_i) / Σ max(a_i,b_i)` — fuzzy Jaccard index.

### S

**Schrödinger bridge**: Min-entropy path measure between α₀ and α₁; entropic OT over paths.

**Semidiscrete OT**: One continuous marginal, one discrete; Laguerre cells partition domain.

**Sinkhorn algorithm**: Alternating row/column normalization of Gibbs kernel K; solves entropic OT.

**Sinkhorn divergence**: Debiased `2W^ε(α,β)-W^ε(α,α)-W^ε(β,β)≥0`; proper metric.

**Sliced Wasserstein**: Average W_p over random 1D projections; O(Kn log n).

**Soft-minimum**: `min_ε z = -ε log Σ_i e^{-z_i/ε}` — smooth approximation of min.

### T

**Transportation polytope**: `U(a,b)` — bounded convex polytope with n+m equality constraints.

**TV (Total Variation)**: `TV(α,β) = sup_{||f||≤1} ∫f d(α-β)`; L1 norm on signed measures.

### U

**Unbalanced OT**: Relax marginal constraints with KL penalty; allows mass creation/destruction.

### W

**Wasserstein distance**: `W_p(α,β) = LC(a,b)^{1/p}` with `C_{ij}=d(x_i,y_j)^p`; metric on distributions.

**Wasserstein geodesic**: Displacement interpolation connecting two distributions optimally.

**Wasserstein gradient flow**: Continuous descent of energy E in W₂ metric; JKO time-discretized.

**WGAN**: Wasserstein GAN — uses W₁ dual as adversarial loss for generative model training.

# Chapter 31: Ising Models

## Core Idea
Ising models are arrays of ±1 spins with neighbour couplings. They are the book’s laboratory for Monte Carlo, exact tree computation, phase transitions, and later Hopfield / Boltzmann machines. Heat capacity is energy fluctuation: you do not need to change T to measure C.

## Key Concepts
- **Spin / state**: x ∈ {−1,+1}^N. Neighbours (m,n) ∈ N.
- **Energy**: E(x; J, H) = −½ ∑_{m,n} J_mn x_m x_n − ∑_n H x_n. J>0 ferromagnetic (align), J<0 antiferromagnetic (anti-align).
- **Boltzmann distribution**: P(x | β,J,H) = exp[−β E]/Z with β = 1/(k_B T).
- **Partition function**: Z(β,J,H) = ∑_x exp[−β E]. Thermodynamics lives in Z.
- **Spin glass / infinite-range**: heterogeneous J_mn, h_n — Hopfield and Boltzmann machines.
- **Phase transition / universality**: 2-D Ising has a critical T; scaling matches other 2-D systems with the same symmetries.
- **Constrained channel link**: 2-D barcode constraints ≈ antiferromagnet at low T; entropy of the model ≈ channel capacity (Ch 17).
- **Binary images**: Ising as a crude spatial prior on black/white pixels.

## Frameworks and Methods
- **Monte Carlo simulation**: Gibbs or Metropolis on spins. Watch magnetization m = (1/N)∑ x_n and energy. Below T_c, magnetization freezes in a sign; mixing fails.
- **Fluctuation–dissipation**: C = dĒ/dT = k_B β² var(E). Measure C from equilibrium energy variance, not from a finite-difference in T.
- **Direct Z on trees / strips**: transfer-matrix / sum–product (Ch 25–26) computes Z exactly for 1-D and for 2-D strips of modest width.
- **Finite-size high-T behaviour**: all states equiprobable ⇒ Ē almost constant, C → 0, but var(E) stays O(1); the 1/T² in C = k_B β² var(E) reconciles the paradox.

## Key Equations
- E(x; J, H) = −½ ∑ J_mn x_m x_n − ∑ H x_n
- P(x) = e^{−βE}/Z,  Z = ∑_x e^{−βE}
- Ē = −∂ ln Z / ∂β
- var(E) = ∂² ln Z / ∂β²
- C ≡ dĒ/dT = k_B β² var(E)
- In β-units: C(β) ≡ dĒ/dβ wait no — MacKay’s preferred: C_{(β)} ≡ dĒ/d(−β)? He writes C_{(β)} ≡ dĒ/dT-analogue = var(E) if temperature is defined as β.
- Magnetization: m̄ = (1/N) ∑ ⟨x_n⟩; susceptibility χ related to var(m)

## Algorithms and Techniques
**Metropolis Ising**
1. Pick a spin n.
2. Compute ΔE for a flip (only neighbours contribute).
3. Accept with min(1, e^{−β ΔE}); else keep.
4. After burn-in, record E, m. Histogram var(E) → C.

**Gibbs Ising**
1. P(x_n = +1 | rest) = σ(2β (∑_{m∈N(n)} J x_m + H)) with σ the logistic.
2. Draw the spin from that Bernoulli.

**Exact Z (1-D / strip)**
1. Build the transfer matrix between successive columns.
2. Z is a product (or largest-eigenvalue power) of transfer matrices.
3. Same as sum–product on a chain/trellis.

## Anti-patterns
- **Changing T to measure C** when you already have equilibrium samples: use var(E).
- **Declaring mixing from a short magnetization trace** below T_c — the chain is stuck in one magnetized well.
- **Using infinite-range / fully connected MC intuition on a 2-D lattice** (and vice versa): topology changes mixing and criticality.
- **Treating Hopfield energy as “just Ising” without noting** that J_mn is data-dependent and typically dense.

## Key Takeaways
1. Ising is the shared language of magnets, images, 2-D constrained channels, and associative nets.
2. Fluctuations *are* response functions: C ∝ β² var(E).
3. Z is the hard object; trees/strips make it easy, 2-D grids do not (without Onsager or sampling).
4. Monte Carlo can look fine and still be unmixed (broken ergodicity below T_c).
5. Spin glasses with arbitrary J, h are the statistical-physics name for Hopfield / Boltzmann.

## Connects To
- **Ch 17**: 2-D constrained channels ↔ antiferromagnet entropy.
- **Ch 25–26**: transfer matrix / sum–product for exact Z.
- **Ch 29–30**: Gibbs, Metropolis, annealing on this model.
- **Ch 32**: coupling from the past on Ising (monotonicity).
- **Ch 33**: mean-field variational approximation of the same P(x).
- **Ch 42–43**: Hopfield and Boltzmann = spin glasses.

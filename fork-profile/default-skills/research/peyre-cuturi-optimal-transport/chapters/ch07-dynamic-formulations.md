# Chapter 7 — Dynamic Formulations

## Core Idea
OT can be reformulated as finding the geodesic in the space of probability measures with the Wasserstein metric. The Benamou–Brenier formula expresses W₂² as a fluid dynamics problem (continuity equation + kinetic energy). This connects OT to PDEs, gradient flows, and Schrödinger bridges.

## Frameworks Introduced

### 7.1 Benamou–Brenier Formula
W₂(α₀, α₁)² = min over (αₜ, vₜ) satisfying continuity equation:
```
∂αₜ/∂t + ∇·(αₜ vₜ) = 0,  α₀ given, α₁ given
∫₀¹ ∫ ||vₜ(x)||² dαₜ(x) dt  → minimized
```
Using momentum Jₜ = αₜ vₜ, this is a convex problem in (αₜ, Jₜ).

### 7.2 Discretization on Staggered Grids
- Space-time discretization on uniform Cartesian grids
- Staggered grid: densities on cells, fluxes on faces
- Enables finite-difference approximation of continuity equation

### 7.3 Proximal Solvers
Solve Benamou–Brenier via splitting methods:
- **ADMM / Douglas-Rachford**: split into convex subproblems
- **Proximal point** on the convex kinetic energy + indicator of continuity equation
- Each step = projection or proximal map, available in closed form

### 7.4 Dynamical Unbalanced OT
Relax mass conservation by adding KL source term:
```
min ∫₀¹ ∫ [||vₜ||² αₜ + ρ KL(source term)] dt
```
Handles creation/destruction of mass along the path.

### 7.5 More General Mobility Functionals
Replace kinetic energy ||v||² with:
```
∫ ψ(αₜ(x), vₜ(x)) dx
```
where ψ is a convex function — gives different interpolation geometries (Hellinger, Fisher-Rao, etc.).

### 7.6 Dynamic Formulation over Path Space
Schrödinger problem = entropy-regularized Benamou–Brenier:
- Reference: Brownian motion between α₀ and α₁
- Minimize KL divergence of path measure from Brownian bridge
- Connects to stochastic optimal control and DDPM diffusion models

## Key Concepts
- **Wasserstein geodesic**: displacement interpolation αₜ = ((1-t)Id + tT)#α₀ (pushforward of linear interpolation of maps)
- **McCann interpolation**: for W₂, optimal αₜ = interpolated pushforward at time t
- **Schrödinger bridge**: minimum-entropy coupling between α₀ and α₁ via Brownian reference
- **Benamou–Brenier**: expresses static OT (coupling) as dynamic OT (path)

## Mental Models
- Dynamic OT = fluid flowing optimally from shape α₀ to shape α₁
- Geodesic in Wasserstein space = interpolated "morph" between two distributions
- Schrödinger bridge = most likely path of particles connecting two distributions

## Anti-patterns
- Computing dynamic OT via full space-time discretization when static Sinkhorn suffices
- Ignoring staggered grid constraints (causes checkerboard artifacts)
- Confusing Wasserstein geodesic with linear interpolation of densities

## Code Examples
```python
# Wasserstein geodesic via displacement interpolation (1D)
def wasserstein_geodesic_1d(x0, x1, t):
    """Interpolate between empirical distributions at time t ∈ [0,1]."""
    # Sort both (optimal coupling for 1D is monotone)
    x0s, x1s = np.sort(x0), np.sort(x1)
    # Linear interpolation of support points
    return (1-t) * x0s + t * x1s

# McCann interpolation (pushforward)
def mccann_interpolation(alpha_samples, T_map, t):
    """T_map: optimal Monge map from α₀ to α₁."""
    return (1-t) * alpha_samples + t * T_map(alpha_samples)
```

## Key Takeaways
1. Benamou–Brenier: W₂² = min kinetic energy along continuity-equation trajectories
2. Dynamic OT is convex in momentum (ρ,J) formulation
3. Wasserstein geodesic = displacement interpolation (not linear mix of densities)
4. Schrödinger problem connects OT to stochastic processes and diffusion models
5. ADMM/proximal methods handle dynamic OT on discrete grids

## Connects To
- Ch 2: W₂ defined statically; Ch 7 gives its dynamic (geodesic) interpretation
- Ch 9: gradient flows in Wasserstein metric = natural continuous-time optimization
- Ch 4: entropic regularization → Schrödinger bridge (static version)

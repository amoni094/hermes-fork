# Patterns: Villani OT Theory → Hermes Applications

## Pattern 1: Routing Cost via Kantorovich Duality

**When:** Need to compare two routing distributions µ,ν efficiently without
constructing the full transport plan.

**Theory (Ch. 5):** Kantorovich duality:
```
C(µ,ν) = sup_{ψ c-convex} { ∫ψᶜ dν − ∫ψ dµ }
```
For W₁: `W₁(µ,ν) = sup_{‖f‖_Lip ≤ 1} ∫f d(µ−ν)`

**Implementation:**
1. For W₁: solve the 1-Lipschitz dual (linear program on discrete distributions)
2. For W₂: use entropic regularization (Sinkhorn) — see Peyré–Cuturi skill
3. Dual value = primal transport cost = routing cost metric

**Feasibility: HIGH**  
**Key reference:** Theorem 5.10 (Kantorovich duality), Particular Case 5.16

---

## Pattern 2: Geodesic Interpolation in Skill Embedding Space

**When:** Routing needs to smoothly transition between two skill distributions
(e.g., warm-start a new router from an existing one).

**Theory (Ch. 7):** For µ₀ ≪ vol with Brenier map T = ∇ψ:
```
µₜ = ((1−t)·Id + t·T)# µ₀
```
This is the unique constant-speed geodesic in (P₂,W₂).

**Implementation:**
1. Solve OT from µ₀ to µ₁ to get transport map T (or Sinkhorn coupling)
2. For Gaussian distributions: T = Σ₀^{−1/2}(Σ₀^{1/2}Σ₁Σ₀^{1/2})^{1/2}Σ₀^{−1/2}
3. Interpolated distribution: push µ₀ through (1−t)Id + t·T

**When Gaussians:** Closed form (see cheatsheet). Otherwise, use Sinkhorn.

**Feasibility: MEDIUM** (exact T requires OT solve; Gaussian case: HIGH)  
**Key reference:** Theorem 7.21, Corollary 7.23

---

## Pattern 3: Displacement Convexity for Convergence Certificate

**When:** Need to prove that a routing optimization converges.

**Theory (Ch. 16–17):** If loss functional F = Uν with U ∈ DC_∞, then F is
displacement convex. If Ric ≥ λ, then F is λ-displacement convex.

**Check procedure:**
```python
def check_dc_class(U, dU, d2U):
    """Check if U ∈ DC_∞: need p₂(ρ) ≥ 0"""
    def p(rho): return rho * dU(rho) - U(rho)
    def p2(rho): return rho * (d2U(rho)*rho) - p(rho)  # ≈ ρp'(ρ)−p(ρ)
    return all(p2(rho) >= 0 for rho in test_points)
```

**Common result:** KL divergence U = ρ log ρ ∈ DC_∞ always.  
**Convergence:** If F is λ-convex, JKO converges as e^{−λt}.

**Feasibility: HIGH** (theoretical check only, no runtime OT needed)  
**Key reference:** Definition 17.1, Theorem 17.15

---

## Pattern 4: Wasserstein-2 Barycenter for Ensemble Aggregation

**When:** Aggregating N skill routing distributions {µ₁,...,µN} with weights.

**Theory (Ch. 7, background):** The Wasserstein-2 barycenter is:
```
µ* = argmin_µ Σᵢ wᵢ W₂(µ, µᵢ)²
```

**Properties:**
- Unique when at least one µᵢ is absolutely continuous
- For Gaussians 𝒩(mᵢ, Σᵢ): barycenter is 𝒩(Σwᵢmᵢ, Σ*) where Σ* satisfies
  fixed-point equation Σ* = ΣᵢwᵢS(Σ*,Σᵢ) with S = geometric mean operator

**Implementation:**
1. Fixed-point iteration: start with µ₀ = mixture, iterate
   `µₖ₊₁ = (1/N) Σᵢ Tᵢ# µₖ` where Tᵢ = OT map from µₖ to µᵢ
2. For Gaussians: direct algebraic solution via Bures metric

**Feasibility: MEDIUM** (exact: requires N OT solves per step; Gaussian: HIGH)  
**Key reference:** Villani Ch. 7; Peyré–Cuturi for algorithms

---

## Pattern 5: Regularity Check for Differentiable Skill Scoring

**When:** Designing a differentiable skill scorer that uses OT maps.

**Theory (Ch. 12):** OT map T = ∇ψ is C^{k+1,α} iff:
1. c(x,y) = |x−y|²/2 (quadratic cost)
2. Source support supp(µ) is convex
3. Target support supp(ν) is convex
4. Densities f,g ∈ C^{k,α}

For other costs (hyperbolic, manifold), MTW condition must be verified.

**Decision procedure:**
```
Is cost quadratic? → YES → Are both supports convex? → YES → Caffarelli applies → T is smooth
                  → NO  → Check MTW condition → Usually fails → T not smooth
Are distributions supported on a manifold? → Usually MTW fails → T not smooth
```

**Recommendation:** Use entropic regularization (Sinkhorn) instead of exact T.
Sinkhorn transport plan is always smooth in the regularization parameter ε.

**Feasibility: LOW** (verifying MTW is intractable at runtime)  
**Key reference:** Theorem 12.7, Definition 12.14

---

## Pattern 6: KL-to-Wasserstein Conversion via Talagrand

**When:** Have a KL divergence bound and need a Wasserstein bound.

**Theory (Ch. 22):** If ν satisfies T₂(λ):
```
W₂(µ,ν)² ≤ (2/λ) · KL(µ‖ν)
```

**When does ν satisfy T₂?**
- Gaussian 𝒩(0, Σ): T₂(1/‖Σ‖)
- Log-concave measure e^{−V}: T₂(1/L) if V is L-smooth and strongly convex
- Measure on manifold with Ric ≥ K: T₂(K)

**Implementation:**
```python
def kl_to_wasserstein_bound(kl_value, talagrand_constant_lambda):
    """Upper bound on W₂ given KL divergence and T₂ constant."""
    return (2 * kl_value / talagrand_constant_lambda) ** 0.5
```

**Feasibility: HIGH** (just a formula, no OT needed)  
**Key reference:** Theorem 22.10, Theorem 22.14

---

## Pattern 7: JKO Step as Principled Distribution Update

**When:** Updating a routing distribution minimizing a loss while controlling
how much the distribution changes (regularization by W₂).

**Theory (Ch. 23):** One JKO step:
```
µₙₑₓₜ = argmin_µ { L(µ) + W₂(µ, µ_current)² / (2τ) }
```

**Interpretation:** Gradient descent in Wasserstein space with step size τ.
Converges to gradient flow as τ→0.

**Implementation (approximate):**
1. Fix τ (step size)
2. Solve: min_µ { L(µ) + ε-regularized W₂(µ, µ_curr)² / (2τ) }
3. Use Sinkhorn iterations for the W₂ term
4. Outer loop: gradient on L, inner loop: OT

**Feasibility: LOW-MEDIUM** (one OT solve per update step; expensive at scale)  
**Key reference:** Definition 23.7, JKO 1998

---

## Anti-Patterns

### Anti-Pattern 1: Assuming OT Maps are Smooth
**Mistake:** Using T = ∇ψ in a neural network gradient computation.  
**Problem:** T is discontinuous when support is non-convex or MTW fails.  
**Fix:** Use Sinkhorn coupling (always smooth) or assume Gaussian structure.

### Anti-Pattern 2: Linear Mixture Instead of Displacement Interpolation
**Mistake:** µₜ = (1−t)µ₀ + tµ₁ for interpolating between routing distributions.  
**Problem:** Creates bimodal/multimodal distributions at intermediate t.  
**Fix:** Use displacement interpolation (geodesic in W₂) via Brenier map.

### Anti-Pattern 3: W₂ at Runtime for Large N
**Mistake:** Computing exact W₂ between N-point empirical distributions at each routing step.  
**Problem:** O(N³) for LP, O(N²/ε²) for Sinkhorn — too slow for inference.  
**Fix:** Use sliced Wasserstein, random features approximation, or pre-compute embeddings.

### Anti-Pattern 4: Ignoring Curse of Dimensionality
**Mistake:** Applying W₁ concentration results in high-dimensional embedding space.  
**Problem:** Empirical Wₚ rates are N^{−1/d} — poor for d > 20.  
**Fix:** Project to lower-dimensional subspace first (sliced OT), or use kernel-based MMD.

# Patterns: Real Analysis (Royden-Fitzpatrick)
Reusable proof patterns and algorithmic frameworks extracted from the text.

---

## Pattern: Two-Stage Measure Construction (Carathéodory)
**When to use**: Building a countably additive measure from a simpler prescription (length, probability on atoms, etc.)
**How**:
1. Define primitive function on simple sets (e.g., ℓ(I) = length of interval I)
2. Extend to outer measure: μ*(A) = inf{Σ p(Aₙ): A ⊆ ∪Aₙ} — monotone, subadditive, defined on all sets
3. Define measurable sets via Carathéodory condition: E measurable iff μ*(A) = μ*(A∩E) + μ*(A∩Eᶜ) ∀A
4. Prove measurable sets form a σ-algebra and μ = μ*|_M is countably additive
**Trade-offs**: Produces a complete measure (null-set supersets measurable). May include non-Borel sets. Requires outer regularity proof separately.

---

## Pattern: Rapidly Cauchy Subsequence → Completeness
**When to use**: Proving a normed space is complete (Riesz-Fischer pattern)
**How**:
1. Take Cauchy sequence {fₙ}
2. Extract subsequence {fₙₖ} with Σ ‖fₙₖ₊₁ - fₙₖ‖ < ∞ (rapidly Cauchy)
3. Define dominator g = |f_{n₁}| + Σ|fₙₖ₊₁ - fₙₖ| and show ‖g‖ < ∞ (via MCT + triangle inequality)
4. Show partial sums of fₙₖ converge a.e. to f and ‖fₙₖ - f‖ → 0 (via DCT with dominator g + g)
5. Since original sequence Cauchy and subsequence converges, whole sequence converges
**Trade-offs**: Requires MCT (for g ∈ Lp) and DCT (for Lp convergence). Works for any Lp, 1 ≤ p ≤ ∞.

---

## Pattern: Bounded Sequence → Weakly Convergent Subsequence (Diagonal Argument)
**When to use**: Extracting convergent subsequences in infinite-dimensional spaces
**How** (for Lp with 1 < p < ∞, separable Lq):
1. Let {gₙ} be countable dense set in Lq
2. For each k, pass to subsequence where ∫fₙg_k converges (bounded real sequence has convergent subsequence)
3. Diagonal argument: {fₙₖₖ} satisfies ∫fₙₖₖg_k → L(g_k) for all k
4. Extend L to all of Lq by density and boundedness
5. By Riesz Representation, L(g) = ∫f·g for some f ∈ Lp
**Trade-offs**: Requires separability of the dual space. Fails for L∞ → L1 (non-separable). Result is only weak convergence, not norm convergence.

---

## Pattern: DCT Application Checklist
**When to use**: Justifying interchange of limit and integral
**Steps**:
1. ✓ Identify: does fₙ → f pointwise (or a.e.)?
2. ✓ Find dominator: ∃g integrable with |fₙ| ≤ g a.e. for all n?
3. ✓ If yes: ∫fₙ → ∫f and ∫|fₙ-f| → 0. Done.
4. ✗ If no dominator: check uniform integrability instead → apply Vitali Convergence Theorem
5. ✗ If only lim inf available: apply Fatou's Lemma (lower bound only)
**Trade-offs**: DCT is the simplest; look for dominator first. Vitali is more general but requires verifying UI.

---

## Pattern: Radon-Nikodym Change-of-Measure Calculation
**When to use**: Changing the reference measure; computing expectations under a new distribution
**How**:
1. Verify ν ≪ μ (check: every μ-null set is also ν-null)
2. By RN theorem, ∃ unique f = dν/dμ ≥ 0 with ν(E) = ∫_E f dμ
3. For any μ-integrable h: ∫_X h dν = ∫_X h·(dν/dμ) dμ (change-of-measure formula)
4. Chain rule: if also μ ≪ λ, then dν/dλ = (dν/dμ)·(dμ/dλ) a.e.[λ]
5. If ν ≪ μ and μ ≪ ν: dν/dμ · dμ/dν = 1 a.e. — densities are reciprocals
**Trade-offs**: Requires σ-finiteness. If ν ⊄ μ (not absolutely continuous), RN density doesn't exist; use Lebesgue decomposition first.

---

## Pattern: Egorov's Theorem — Identifying the Stable Core
**When to use**: Upgrading a.e. convergence to uniform convergence on a large set
**How**:
1. Verify m(E) < ∞ (required)
2. For each k ≥ 1, define E_k^N = ∪_{n≥N} {x: |fₙ(x)-f(x)| ≥ 1/k}; m(E_k^N) → 0 as N→∞
3. For each k, choose N_k s.t. m(E_k^{N_k}) < ε/2^k
4. Set F = E \ ∪_k E_k^{N_k}; then m(E\F) < ε and fₙ→f uniformly on F
**Trade-offs**: Requires finite measure on E — the theorem fails on ℝ (infinite measure). The exceptional set E\F is unavoidable.

---

## Pattern: Uniform Integrability Verification
**When to use**: Before applying Vitali Convergence or Dunford-Pettis
**Sufficient conditions for UI**:
- {fₙ} dominated by g ∈ L1 → {fₙ} UI (via DCT with threshold M)
- ‖fₙ‖_p ≤ C for some p > 1 → {fₙ} UI in L1 (Hölder: ∫_{|fₙ|>M}|fₙ| ≤ ‖fₙ‖_p · m({|fₙ|>M})^{1/q} → 0)
- Finite family of integrable functions is always UI
**Verification algorithm**:
1. Compute sup_n ∫_{|fₙ|>M}|fₙ| dμ for large M
2. Show this → 0 as M → ∞
3. Equivalently: for ε > 0, find M s.t. this sup < ε

---

## Pattern: Banach Contraction Fixed-Point Iteration
**When to use**: Proving existence and uniqueness of a fixed point; convergence of iterative algorithms
**How**:
1. Verify X is complete metric space
2. Verify T: X → X with d(Tx,Ty) ≤ c·d(x,y) for some c < 1 (check Lipschitz constant)
3. Start from any x₀ ∈ X; iterate xₙ₊₁ = T(xₙ)
4. Geometric convergence: d(xₙ, x*) ≤ cⁿ · d(x₁,x₀)/(1-c)
5. Unique fixed point x* = lim xₙ
**Trade-offs**: Contraction constant c must be strictly < 1. If c ≥ 1 (nonexpansive), fixed point may still exist but convergence is not guaranteed.

---

## Pattern: Hahn-Banach Norm Computation
**When to use**: Computing ‖x‖ as a supremum over linear functionals
**Formula**: ‖x‖ = sup{|T(x)| : T ∈ X*, ‖T‖* ≤ 1}
**Use cases**:
- Proving x ≠ 0 by exhibiting T with T(x) ≠ 0
- Separating x from a closed convex set C: if x ∉ C, ∃ T separating them
- Computing dual norms: ‖x‖** (second dual) = ‖x‖ (reflexive case)

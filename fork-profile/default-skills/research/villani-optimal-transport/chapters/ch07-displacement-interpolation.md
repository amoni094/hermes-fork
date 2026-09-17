# Chapter 7: Displacement Interpolation

**Book pages:** 113–162  
**Hermes relevance:** HIGH — Geodesic interpolation between distributions; the foundation for skill-space interpolation.

## Core Concept

Displacement interpolation is the "correct" way to interpolate between probability
measures: instead of linear interpolation µₜ = (1−t)µ₀ + tµ₁ (which is
not geodesic in Wasserstein space), one moves mass along geodesic paths.

## Action Functional Setting

For a Lagrangian L(x,v,t) on a manifold M, the action of a path γ:[0,1]→M is:
```
A(γ) = ∫₀¹ L(γₜ, γ̇ₜ, t) dt
```
The quadratic Lagrangian L(x,v,t) = |v|²/2 gives action A(γ) = ∫|γ̇|²/2 dt,
whose minimizers are geodesics (constant-speed, minimizing).

## Key Theorem: Displacement Interpolation (Theorem 7.21)

**Setup:** Let µ₀, µ₁ ∈ P₂(M). For cost c(x,y) = action of minimizing path from x to y:

**Theorem:** There exists a random path (γₜ)_{t∈[0,1]} such that:
1. law(γₜ) = µₜ is a path of probability measures
2. (γₜ) is a.s. an action-minimizing curve (geodesic for quadratic cost)
3. (µₜ) is a geodesic in (P₂(M), W₂): `W₂(µₛ,µₜ) = |t−s|·W₂(µ₀,µ₁)`

For quadratic cost on ℝⁿ with µ₀ ≪ vol:
```
µₜ = ((1−t)Id + t T)# µ₀,    where T = ∇ψ is the Brenier map
```

## Properties

**Absolute continuity preservation (Property (ii)):**
If either µ₀ or µ₁ is absolutely continuous, then µₜ is absolutely continuous
for all t ∈ (0,1).

**Constant speed:** The path (µₜ) satisfies:
```
W₂(µₛ, µₜ) = |t−s| · W₂(µ₀, µ₁)
```
It is a constant-speed geodesic in Wasserstein space.

**Non-crossing:** Individual particle trajectories t ↦ γₜ do not cross at
intermediate times t ∈ (0,1), even if they start/end at the same point.

**Uniqueness:** When µ₀ ≪ vol, the geodesic is unique.

## Characterization via Measures on Path Space

Equivalently, displacement interpolation is encoded by a measure Π on
C([0,1]; M) (space of paths), such that:
- (e₀, e₁)# Π = π is an optimal coupling of (µ₀, µ₁)
- Π-a.s., γ is a minimizing curve

The marginals are: (eₜ)# Π = µₜ.

## McCann's Condition for Uniqueness

If µ₀ is absolutely continuous and c comes from a Lagrangian satisfying
mild conditions (superlinearity in velocity), then:
1. The optimal coupling π is unique and deterministic: π = (Id, T)# µ₀
2. The displacement interpolation (µₜ) is unique
3. Each minimizing curve γ is µ₀-a.s. uniquely determined by its endpoints

## Hermes Application

**Skill interpolation:** Given two skill embedding distributions µ₀ (current skill
state) and µ₁ (target skill state), the geodesic (µₜ) provides a principled
interpolation path in distribution space.

**Computational note:** For d-dimensional Gaussian distributions, displacement
interpolation has a closed form (see cheatsheet). For general distributions,
requires solving OT problem first.

**Path planning in probability space:** The JKO gradient flow (Ch. 23) can be
viewed as following the gradient of an energy along displacement geodesics.

**Interpolation vs. mixture:** For routing blend, displacement interpolation
µₜ = ((1−t)Id + tT)#µ₀ is geometrically correct (moves mass to right locations)
vs. mixture (1−t)µ₀ + tµ₁ which creates artificial bimodality.

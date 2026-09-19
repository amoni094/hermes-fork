---
name: maclane-working-mathematician
description: "Use when applying adjoint functors, monads, or Kan ext."
tags: [category-theory, mathematics, adjoints, monads, kan-extensions, functors, yoneda]
source: "Mac Lane, S. (1998). Categories for the Working Mathematician (2nd ed.). Springer GTM 5."
---

# Mac Lane — Categories for the Working Mathematician (2nd ed.)

Authoritative reference for category-theoretic reasoning in Hermes: adjunctions, monads, Kan extensions, natural transformations, and the Yoneda lemma. Load this skill when structuring agent pipelines categorically, auditing plugin monadic laws, designing k-tier policy generalizations, or detecting duplicate tool results.


## Model Routing

Dense abstract math reference lookup (no tool calls): deepseek-v4-pro non-think session. Categorical implementation (Haskell, Python type constructs): grok-4.6 workers via delegate_task.


## Core Frameworks

### 1. Categories (Ch I)
A **category** C consists of:
- Objects: `ob(C)`
- Morphisms (arrows): `hom(A,B)` for each pair of objects A, B
- Composition: `g ∘ f` for `f: A→B`, `g: B→C`, yielding `g∘f: A→C`
- Identity: `id_A: A→A` for each object A

Axioms:
- **Associativity**: `h∘(g∘f) = (h∘g)∘f`
- **Unit**: `id_B ∘ f = f = f ∘ id_A`

Key categories: **Set**, **Grp**, **Top**, **Ab**, **Cat**, preorders as categories (at most one arrow between any two objects).

### 2. Functors (Ch I–II)
A **functor** `F: C → D` assigns to each object `A∈C` an object `FA∈D` and to each morphism `f: A→B` a morphism `Ff: FA→FB`, preserving composition and identities:
- `F(g∘f) = Fg∘Ff`
- `F(id_A) = id_{FA}`

Contravariant functors reverse arrow direction. The **opposite category** `C^op` reverses all morphisms.

### 3. Natural Transformations (Ch I, III)
A **natural transformation** `α: F ⇒ G` between functors `F,G: C → D` assigns to each object `A∈C` a morphism `α_A: FA → GA` in D such that for every `f: A→B` in C:
```
α_B ∘ Ff = Gf ∘ α_A    (naturality square commutes)
```
A **natural isomorphism** has each component `α_A` invertible.

**Hermes application**: A scoring function change in jev-compaction is a natural transformation `α: score_old ⇒ score_new` iff it preserves ranking order (the naturality square commutes). A change that reorders messages is **not** natural and creates cross-session inconsistencies — use this test before deploying new scoring policies.

### 4. Yoneda Lemma (Ch III §2)
**Statement**: For any functor `K: D → Set` and object `r∈D` (D with small hom-sets):
```
Nat(D(r,−), K) ≅ K(r)    (naturally in K and r)
```
The bijection sends each natural transformation `α: D(r,−)⇒K` to `α_r(id_r) ∈ K(r)`.

**Corollary (Yoneda embedding)**: The functor `Y: D → Set^{D^op}`, `r ↦ D(r,−)` is full and faithful. Two objects are isomorphic iff their representable functors are naturally isomorphic.

**Hermes application**: Represent each message `m` by its retrieval probe set `D(m,−)` = {queries that return m}. Two messages are isomorphic in the retrieval category iff they respond identically to all probes. Use to detect duplicate tool results for the fast-demote path without full content comparison.

### 5. Adjoint Functors (Ch IV)
**Definition**: An **adjunction** `(F, G, φ): X ⇌ A` consists of functors `F: X→A` (left adjoint) and `G: A→X` (right adjoint) and a natural bijection:
```
φ_{x,a}: A(Fx, a) ≅ X(x, Ga)    natural in x∈X, a∈A
```
Write `F ⊣ G`.

**Unit and counit** (Mac Lane Thm IV.1.1):
- **Unit**: `η: Id_X ⇒ GF`,  with `η_x: x → GFx` universal from x to G
- **Counit**: `ε: FG ⇒ Id_A`, with `ε_a: FGa → a` universal from F to a

**Triangle identities** (the adjunction equations):
```
G --Gη--> GFG --εG--> G   = id_G
F --ηF--> FGF --Fε--> F   = id_F
```

**Hermes application — demotion is informationally irreversible**:
The retain/demote functor `F: Messages → {R,D}` (mapping each message to Retained or Demoted) has **no left adjoint**. A left adjoint would require a functor `L: {R,D} → Messages` and a counit `ε: FL ⇒ Id_{Messages}` — i.e., a canonical way to reconstruct any message from its binary classification. No such reconstruction exists. By Mac Lane Thm IV.1.1, the non-existence of the counit implies F has no left adjoint. **State this explicitly in plugin docstrings**: demotion is informationally irreversible by the categorical non-existence of the adjoint counit.

### 6. Freyd Adjoint Functor Theorem (Ch V §6)
A functor `G: A → X` has a left adjoint iff:
1. G preserves all small limits
2. A satisfies the **solution set condition**: for each `x∈X` there is a set of arrows `{x → Ga_i}` through which every `x → Ga` factors

### 7. Monads (Ch VI)
**Definition**: A **monad** `T = (T, η, μ)` in category X consists of:
- An endofunctor `T: X → X`
- **Unit**: `η: Id_X ⇒ T`
- **Multiplication**: `μ: T² ⇒ T` (where `T² = T∘T`)

Satisfying (Mac Lane §VI.1):
```
Associativity:  μ ∘ Tμ = μ ∘ μT     (as natural transformations T³ ⇒ T)
Left unit:      μ ∘ ηT = id_T
Right unit:     μ ∘ Tη = id_T
```
"A monad in X is just a monoid in the category of endofunctors of X." (Mac Lane p.138)

Every adjunction `(F,G,η,ε): X ⇌ A` generates a monad `(GF, η, GεF)` in X.

**Kleisli category**: Given monad `(T,η,μ)`, the **Kleisli category** `X_T` has the same objects as X and morphisms `X_T(x,y) = X(x,Ty)`. Composition of Kleisli arrows `f: x→Ty` and `g: y→Tz` is `μ_z ∘ Tg ∘ f`. The identity Kleisli arrow at x is `η_x: x→Tx`.

**T-algebras (Eilenberg-Moore)**: A T-algebra is a pair `(x, h: Tx→x)` with `h∘η_x = id_x` (unit law) and `h∘μ_x = h∘Th` (associativity). Beck's theorem characterizes when a functor is monadic.

**Hermes application — jev pipeline monad laws**:
The jev pipeline (score → classify → demote) is a Kleisli arrow chain. The monad unit law requires: the identity Kleisli arrow `η_x = id` must be a no-op. **The EMA (exponential moving average) state update inside `classify` violates the monad unit law**: even the identity Kleisli arrow (no-op classify) mutates EMA state, so `classify ∘ η ≠ η`. Fix: **separate pure scoring from EMA state updates** — make `score` a pure function returning a value, and perform EMA updates in a separate side-effecting step outside the Kleisli chain.

### 8. Kan Extensions (Ch X)
**Definition**: Given functors `K: M→C` and `T: M→A`, a **right Kan extension** of T along K is a pair `(R, ε: RK⇒T)` universal among functors from `A^C` to `A^M`: for every `(S, α: SK⇒T)` there is a unique `σ: S⇒R` with `α = ε∘(σK)`.

`R = Ran_K T`  is determined up to natural isomorphism.

Dually, the **left Kan extension** `(L, η: T⇒LK)` satisfies the dual universality.

**Formula** (pointwise, when A is complete/cocomplete):
```
(Ran_K T)(c) = lim_{K(m)→c} T(m)   (limit over comma category)
(Lan_K T)(c) = colim_{c→K(m)} T(m)     (colimit over comma category)
```

**All concepts are Kan extensions** (Ch X §7):
- Colimits = left Kan extensions along `M → 1`
- Limits = right Kan extensions along `M → 1`
- Left adjoints = right Kan extensions of identity along G (Thm X.7.2)
- Every functor is a left Kan extension of itself along identity

**Hermes application — k-tier policy generalization**:
The current 3-tier retain/review/demote policy `P: {R,V,D}→[0,1]` assigns thresholds to 3 tiers. To generalize to k tiers without ad-hoc redesign:
- Treat the 3-tier set as a discrete category `3 = {R,V,D}` with inclusion `K: 3 → [0,1]` (into the unit interval as a category/preorder)
- The k-tier policy is the **left Kan extension** `Lan_K P: [0,1] → Policy` of the 3-tier policy along K
- This gives the correct universal generalization: every k-tier threshold assignment factors uniquely through the 3-tier policy, with no ad-hoc parameter tuning

## Hermes Applications Table

| Theorem | Location | Hermes Context | Actionable Rule |
|---|---|---|---|
| Adjoint functor theorem | Ch IV §1 | Retain/demote functor F: Messages→{R,D} | No left adjoint exists; demotion is irreversible. State in plugin docstring. |
| Triangle identities | Ch IV §1 | Adjunction unit/counit composition | If counit can't be constructed, the functor is not adjoint — check before assuming invertibility. |
| Yoneda lemma | Ch III §2 | Message deduplication | Two messages are duplicates iff identical retrieval probe responses; use for fast-demote path. |
| Naturality (nat. transformation) | Ch I §4, Ch III | jev scoring function changes | A scoring change is safe (consistent) iff it's a natural transformation — check ranking preservation. |
| Monad unit law | Ch VI §1 | jev pipeline Kleisli chain | EMA side-effect in classify violates unit law; separate pure scoring from EMA state mutation. |
| Monad associativity | Ch VI §1 | jev pipeline composition order | Pipeline stages must associate: `(demote∘classify)∘score = demote∘(classify∘score)`. |
| Beck's theorem | Ch VI §7 | Plugin algebra reconstruction | A functor G is monadic iff it creates coequalizers of G-split pairs; use to verify plugin reversibility. |
| Left Kan extension | Ch X §3,5 | k-tier policy generalization | k-tier policy = Lan_K(3-tier policy) along inclusion K: 3→[0,1]; avoids redesign. |
| All concepts = Kan ext. | Ch X §7 | Adjoint existence | Left adjoint = right Kan extension of identity; verify existence via limit conditions. |
| Freyd AFT | Ch V §6 | Plugin left adjoint existence | G has left adjoint iff G preserves limits AND solution set condition holds. |

## Chapter Index

| Ch | Title | Key Content |
|---|---|---|
| I | Categories, Functors, Natural Transformations | Axioms, metacategories, functors, natural transformations, monics/epis, hom-sets |
| II | Constructions on Categories | Duality, opposite categories, products, functor categories, comma categories |
| III | Universals and Limits | Universal arrows, **Yoneda lemma**, coproducts, products, groups in categories |
| IV | Adjoints | **Adjunctions**, unit/counit/triangle identities, reflective subcategories, equivalence |
| V | Limits | Limit creation, **Freyd adjoint functor theorem**, special adjoint functor theorem |
| VI | Monads and Algebras | **Monads**, T-algebras, Kleisli category, **Beck's theorem**, free algebras |
| VII | Monoids | Monoidal categories, coherence, simplicial category, closed categories |
| VIII | Abelian Categories | Kernels, additive categories, diagram lemmas |
| IX | Special Limits | Filtered limits, ends, coends, iterated ends |
| X | Kan Extensions | **Left/right Kan extensions**, pointwise formula, **all concepts = Kan extensions** |
| XI | Symmetry and Braiding | Symmetric monoidal categories, braid groups |
| XII | Structures in Categories | Internal categories, 2-categories, bicategories |

## Quick Reference

```
Adjunction:     F ⊣ G  ⟺  A(Fx,a) ≅ X(x,Ga) natural in x,a
Unit:           η: Id_X ⇒ GF
Counit:         ε: FG ⇒ Id_A
Triangle ids:   εG∘Gη = id_G,  Fε∘ηF = id_F

Monad:          (T, η: Id⇒T, μ: T²⇒T)
Laws:           μ∘Tμ = μ∘μT,  μ∘ηT = id = μ∘Tη
Kleisli comp:   g ★ f = μ∘Tg∘f  for f:x→Ty, g:y→Tz

Yoneda:         Nat(C(r,−), K) ≅ Kr  naturally in r,K

Left Kan:       Lan_K T:  (Lan_K T)(c) = colim_{c→K(m)} T(m)
Right Kan:      Ran_K T:  (Ran_K T)(c) = lim_{K(m)→c} T(m)
```

## Loaded Reference Files

- `references/ch4-adjoints.md` — Full adjunction theory with triangle identities and examples
- `references/ch7-monads.md` — Monad definition, Kleisli category, Beck's theorem
- `references/ch10-kan-extensions.md` — Kan extension theory, pointwise formula, all-concepts theorem
- `references/cheatsheet.md` — One-page categorical cheatsheet with Hermes decision rules

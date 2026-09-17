---
name: milewski-category-theory
description: "Use when applying Milewski: functors, monads, ADTs."
related_skills:
  - coding-conventions
  - test-driven-development
---

# Category Theory for Programmers
**Author**: Bartosz Milewski | **Edition**: v1.3.0 (Aug 2019, compiled by Igal Tabachnik) | **License**: CC BY-SA 4.0 | **Chapters**: 31 (3 parts)

Knowledge base from Milewski, *Category Theory for Programmers*. Use when reasoning about type safety, composability, functors, monads, algebraic data types, or functional programming patterns.

Toolkit, not a recap. Prefer these formulations over textbook paraphrases. Cite chapter when applying a rule.

## How to Use

- Load this skill when designing types, composing pipelines, reviewing `.map`/`.then`/`flatMap`, or choosing sum vs product types.
- Apply the **decision rules** first; open the chapter index only for a named construction.

---

## Core Frameworks

### Category (Ch 1)

Objects + arrows (morphisms). Two laws, always:

1. **Associativity.** If `f : A → B`, `g : B → C`, `h : C → D` then `h ∘ (g ∘ f) = (h ∘ g) ∘ f`.
2. **Identity.** Every object `A` has `id_A` with `f ∘ id_A = f` and `id_B ∘ f = f`.

Read `g ∘ f` as "g after f." In code: `g(f(a))` / Haskell `g . f`.

**Programming claim (Ch 1.3).** Programming *is* hierarchical decomposition plus recomposition. A chunk's **surface** (type / interface) is what you need to compose it; its **volume** is the implementation you must forget. If you have to look inside an object to compose it, the paradigm has already failed.

### Types as composability (Ch 2)

Arrows compose only when the target of one equals the source of the next. Types are that matching constraint, mechanically checked. Stronger types → better described, better verified composition. Testing is probabilistic; type checking is closer to proof ("Testing is a poor substitute for proof," Ch 2.2). Design types first; annotations become compiler-enforced comments.

Haskell types + bottoms ≈ **Hask**, not **Set**. Partial functions inhabit every type via `⊥`.

### Kleisli category (Ch 4, Ch 20.1)

Same objects (types). A morphism `A → B` is an *embellished* function `A → m B` (endofunctor `m`). Composition and identity are redefined so the embellishment (log, failure, state, …) is combined *outside* the individual functions.

Writer recipe (Ch 4.1): run first, feed `fst` to second, `mappend` the logs. Identity is `return x = (x, mempty)`. Composition is associative because both function composition *and* the log monoid are.

Fish: `(>=>) :: (a → m b) → (b → m c) → (a → m c)`.

**If `m` has associative composition + identities, `m` is a monad and the result is a Kleisli category.** Each Kleisli arrow is independently a function `a → m b`; the fish is the only glue.

### Products and coproducts (Ch 5)

Defined by universal construction (relationships, not internals).

- **Initial object:** unique morphism to every object — `Void` / empty set; `absurd :: Void → a`.
- **Terminal object:** unique morphism from every object — unit `()`.
- **Product:** pair `(a, b)` with projections; both parts must be inhabited.
- **Coproduct:** `Either a b`; a value is *one* of the alternatives.

### Algebraic data types (Ch 6)

Product and sum types form a **semiring** (rig) of types:

| Numbers | Types |
|---|---|
| 0 | `Void` |
| 1 | `()` |
| a + b | `Either a b` |
| a × b | `(a, b)` |
| 1 + a | `Maybe a = Nothing \| Just a` |
| 2 = 1 + 1 | `Bool` |

`data List a = Nil | Cons a (List a)` solves `x = 1 + a*x`.

Sum types in C++/Java are routinely faked with sentinels: empty string, negative number, null pointer (Ch 6.3). Those are not sums — they make illegal inhabitants representable. Prefer tagged unions / enums-with-data / `Optional`/`Maybe`/`Either`. Haskell constructors are reversible via pattern matching because values are immutable; construction remembers which constructor was used.

### Functors (Ch 7)

A functor `F` maps objects *and* morphisms, preserving structure:

```
F id_a = id_{F a}
F (g ∘ f) = F g ∘ F f
```

No tearing: may smash/glue, never break connections. Endofunctors on types: type constructors + `fmap`.

**Functor laws for `Maybe`/`optional` (Ch 7.1.2):**

```
fmap id = id
fmap (g . f) = fmap g . fmap f
```

Equational reasoning (substitute by definition) **fails** for C++-style functions with side effects. Counterexample: `square(counter())` vs `counter() * counter()` — inlining is invalid. Therefore any `fmap`/`map` whose callback has effects is not a functor.

List, Reader, Writer, `optional` are the working examples. `fmap` on `Nothing` stays `Nothing` — structure preserved, no invented values.

### Natural transformations (Ch 10)

Polymorphic `F a → G a` that commutes with `fmap`:

```
fmap f . α = α . fmap f
```

"One moves the eggs, the other boils them." Example: `safeHead :: [a] → Maybe a`. Do not inspect or manufacture elements; only repackage.

### Monads (Ch 20–22)

A monad is **a way of composing embellished functions**, not "a thing for side effects." Three equivalent presentations:

| | Composition | Flatten |
|---|---|---|
| Fish | `(>=>)`, `return` | Kleisli |
| Bind | `(>>=)`, `return` | `ma >>= f` |
| Join | `join :: m (m a) → m a`, `return` | `ma >>= f = join (fmap f ma)` |

**Monad / Kleisli laws (Ch 20.1):**

```
(f >=> g) >=> h = f >=> (g >=> h)   -- associativity
return >=> f = f                    -- left unit
f >=> return = f                    -- right unit
```

They cannot be enforced by Haskell; they *are* the category laws. Writer satisfies them iff the log is a monoid. `do` notation is sugar for nested `>>=` ("overloading the semicolon"). C++ futures / coroutines are the same pattern (Ch 20.3).

Effects (Ch 21) that become Kleisli arrows instead of impurity: partiality, nondeterminism (`[]`), Reader, Writer, State, exceptions (`Either`/`Maybe`), continuations, I/O. Embellishment alone is not a monad — **insisting on associative composition** is what makes it one.

---

## Decision rules

1. **Compose through the surface.** If a function is only correct when the caller follows unstated protocol (hidden field, global, ordering, "don't call this yet"), it is not a morphism you can compose. Flag it. (Ch 1.2–1.3, Ch 2.2)
2. **Types first.** Change a type, fix compile breaks; do not rely on tests to propagate a new contract. (Ch 2.2)
3. **Sum over sentinel.** `Maybe`/`Either`/enum-with-payload instead of null, `-1`, `""`, boolean flags that encode mode. (Ch 6.3–6.4)
4. **`map` is a functor or it is a bug.** Callback pure; `map(id)` is identity; `map(g∘f) = map(g)∘map(f)`; do not drop/add structure inside `map`. (Ch 7, 7.1.2)
5. **Chains must be Kleisli.** `Promise.then`, `flatMap`, `Result`/`Either` pipes need associativity and units. If regrouping `(f then g) then h` vs `f then (g then h)` changes results, the "monad" is broken — ordering bugs. (Ch 20.1, Ch 1.2)
6. **Test arrows, then the fish.** Each `a → m b` is independently specifiable (Ch 4: log aggregation is *not* the function's concern). Prove each arrow; then prove the composed pipeline. (Ch 4, Ch 20.1)
7. **Effects at the composition, not the function.** Prefer embellished return types over globals/mutation so purity of the steps is preserved. (Ch 4, Ch 21)

---

## Anti-patterns

- **Spaghetti / soup of objects (Ch 1.3).** Surface grows as fast as volume; you cannot forget the implementation.
- **Unsafe coercions as habit (Ch 2.2).** `unsafeCoerce` / type-system backdoors exist; Kafka's Gregor is the cautionary tale.
- **"If it compiles it is correct" (Ch 2.2).** Types do not prove the right output; Haskell still needs tests.
- **Unit tests as a type system (Ch 2.2).** Refactors that change an argument type will not light up call sites in a weak language.
- **Sentinel optionality (Ch 6.3).** Null, empty, negative as "no value."
- **C++ `union` as a sum (Ch 6.3).** Cannot hold `std::string`; use a tagged type.
- **Side-effecting `fmap` (Ch 7.1.2).** Breaks identity and composition; equational reasoning dies.
- **Inventing values in `Nothing`/`[]`.** Functor must not tear or fabricate structure (Ch 7).
- **Monad mysticism (Ch 20).** Not burritos; not "for IO." It is duct tape for Kleisli arrows.
- **Inlining glue instead of composing (Ch 20).** Named intermediates + ad-hoc combination hide that you needed a lawful fish.
- **Non-monoidal log/state combiner.** Writer laws fail if `mappend` is not associative / `mempty` is not a unit (Ch 20.1).
- **Continuation spaghetti (Ch 20.3).** Handler-calls-handler without bind/`do`/coroutines.

---

## Chapter index

**Part I** — 1 Composition laws · 2 Types · 3 Categories great/small, monoids · 4 Kleisli / Writer · 5 Products, coproducts · 6 ADTs · 7 Functors · 8 Functoriality, profunctors · 9 Function types, CCC, Curry-Howard · 10 Natural transformations

**Part II** — 11 Declarative · 12 Limits/colimits · 13 Free monoids · 14 Representable functors · 15 Yoneda · 16 Yoneda embedding

**Part III** — 17 Morphisms · 18 Adjunctions · 19 Free/forgetful · 20 Monad (programmer) · 21 Effects · 22 Monads categorically · 23 Comonads · 24 F-algebras · 25 Algebras for monads · 26 Ends/coends · 27 Kan extensions · 28 Enriched categories · 29 Topoi · 30 Lawvere theories · 31 Monads, monoids, categories

## Topic index

- **associativity / identity** → Ch 1.2, Ch 20.1
- **composability / types** → Ch 2.2
- **Kleisli / fish / return** → Ch 4, Ch 20.1
- **sum types / Maybe / Either** → Ch 5, Ch 6.3–6.4
- **functor laws / fmap** → Ch 7, Ch 7.1.2
- **naturality** → Ch 10
- **monad laws / bind / join / do** → Ch 20
- **effects as embellishment** → Ch 21

## Scope

Book content only (blog-post compilation). Not a Haskell tutorial and not a substitute for Mac Lane. For applying these laws in review/tests, combine with `coding-conventions` and `test-driven-development`.

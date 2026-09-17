---
name: pearl-causality
description: "Use when confounding, do-calculus, or causal debugging."
related_skills:
  - systematic-debugging
  - test-driven-development
  - coding-conventions
---

# Causality: Models, Reasoning, and Inference
**Author**: Judea Pearl | **Edition**: 2nd (2009) | **Chapters**: 11 + Epilogue

Knowledge base from Pearl *Causality: Models, Reasoning and Inference*. Use for root-cause analysis, confounding in experiments, causal vs correlational debugging, and valid A/B tests and evaluations. Toolkit of named criteria — not a book report. Load [references/cheatsheet.md](references/cheatsheet.md) for decision rules; [references/glossary.md](references/glossary.md) for terms.

## How to Use

- Root-cause / A/B / eval design → Core Frameworks below, then cheatsheet
- d-separation, back-door, do-calculus details → glossary + cheatsheet
- Not a substitute for `systematic-debugging` process; it supplies the causal tests that process needs

---

## Core Frameworks

### 1. Causal vs statistical (Ch 1.5)

Statistical claims are functions of a joint distribution P. Causal claims are not: they refer to a *mutilated* model after an intervention. P(Y | X=x) ≠ P(Y | do(X=x)) in general. If a claim can be computed from observational P alone, it is not causal.

**Use when:** someone treats a regression coefficient, a log correlation, or "X appears when the bug appears" as a cause.

### 2. Structural causal models (SCM) (Ch 1.4, 7.1)

An SCM is a set of autonomous assignments Xi = fi(PAi, Ui). Each equation is a mechanism: any subset remains a valid model under intervention. Autonomy means intervening on one equation does not rewrite the others.

do(Xi = xi) *deletes* Xi = fi(PAi, Ui) and substitutes Xi = xi in the rest (Strotz–Wold surgery). The resulting submodel induces P(Y | do(x)).

The associated DAG: arrow Pai → Xi for each parent. Latent dependence among U's → bidirected dashed arcs.

**Use when:** you need a semantics for "what would happen if we changed X" that is not conditioning.

### 3. Causal DAGs and d-separation (Ch 1.2.3, Def 1.2.3)

A path is **d-separated** (blocked) by Z iff:
1. it contains a **chain** i → m → j or **fork** i ← m → j with middle node m ∈ Z, **or**
2. it contains a **collider** i → m ← j whose middle node m ∉ Z and no descendant of m is in Z.

Z d-separates X from Y iff Z blocks every path. Theorem 1.2.4: d-separation ⇒ conditional independence in every distribution compatible with G; absence of d-separation ⇒ dependence in almost all such distributions.

Three elementary structures:

| Structure | Graph | Marginal | Condition on middle |
|----------|-------|----------|---------------------|
| Chain | X → Z → Y | dependent | blocked (independent) |
| Fork (confounder) | X ← Z → Y | dependent | blocked |
| Collider (inverted fork) | X → Z ← Y | independent | **opens** (dependent) |

Conditioning on a descendant of a collider also opens the path (Berkson's paradox / selection bias / explaining-away).

**Use when:** deciding what to condition on, what a log filter does to independence, whether two bugs can be related only through a common effect.

### 4. Interventions vs observations (Ch 1.3, 3.2)

Seeing vs doing. Observing Sprinkler=On updates beliefs about Season and Rain. do(Sprinkler=On) severs the Season → Sprinkler arrow; do **not** update Season.

Truncated factorization (causal Bayes net):
P(v | do(x)) = ∏_{Vi ∉ X} P(vi | pai) for v consistent with x.
Graphically: delete all arrows into X (mutilated graph GX).

P(y | do(x)) ≡ P(Yx = y) (potential outcomes) ≡ Lewis counterfactual "Y would be y if X were x".

**Rule:** "X appears when the bug appears" is observation. "Disabling X prevents the bug" is intervention. Only the latter confirms causation.

### 5. Confounders and the back-door (Ch 3.3.1, 6)

A **confounder** is a common cause of treatment and outcome. There is **no statistical test for confounding** (Ch 6): confounding is a causal, not associational, concept. Collapsibility ≠ confounding.

**Back-door criterion (Def 3.3.1).** Z is admissible for the effect of X on Y if:
(i) no node in Z is a descendant of X; and
(ii) Z blocks every path from X to Y that contains an arrow *into* X.

Then P(y | do(x)) = Σz P(y | x, z) P(z) (back-door adjustment).

Do not adjust for descendants of treatment (post-treatment variables) — they are not back-door admissible and can open colliders or block the effect itself.

**Use when:** a fix "works" in test but fails in prod — suspect an unobserved U correlated with both the fix-context and the outcome. Do not declare victory until the causal path is identified, not merely correlated.

### 6. Front-door (Def 3.3.3)

Z satisfies the front-door relative to (X, Y) if:
(i) Z intercepts all directed paths X → … → Y;
(ii) no unblocked back-door from X to Z;
(iii) all back-door paths from Z to Y are blocked by X.

Then the effect is identifiable even with an unobserved confounder of X and Y:
P(y | do(x)) = Σz P(z | x) Σx' P(y | x', z) P(x').

Classic: smoking → tar → cancer with unobserved genotype confounding smoking and cancer.

### 7. do-calculus (Thm 3.4.1) — complete for identification

Let GX = G with arrows **into** X deleted; GX_bar = G with arrows **out of** X deleted.

- **Rule 1** (insert/delete observations): P(y | do(x), z, w) = P(y | do(x), w) if Y ⟂ Z | X,W in GX.
- **Rule 2** (action/observation exchange): P(y | do(x), do(z), w) = P(y | do(x), z, w) if Y ⟂ Z | X,W in GX with arrows out of Z deleted. (Back-doors from Z to Y blocked ⇒ seeing Z = doing Z.)
- **Rule 3** (insert/delete actions): P(y | do(x), do(z), w) = P(y | do(x), w) if Y ⟂ Z | X,W in the corresponding mutilated graph GX,Z(W).

A query P(y | do(x), z) is identifiable iff a finite sequence of these rules reduces it to a do-free expression in observables (Corollary 3.4.2). Completeness: if do-calculus cannot reduce it, the effect is not identifiable from that graph (Ch 11).

**Use when:** deciding whether an A/B (intervention) can be replaced by observational adjustment, or whether a metric is even identifiable from logs.

### 8. Counterfactuals (Ch 1.4.4, 7)

Three-rung ladder: (1) association P(y|x); (2) intervention P(y|do(x)); (3) counterfactuals P(Yx=y | X=x', Y=y') — "would Y have been y had X been x, given that we saw x', y'?"

Evaluation in an SCM: abduct U given evidence; mutilate the equations for the antecedent; predict Y in the submodel. Twin-network method (Ch 7.1.4) shares U between factual and counterfactual worlds.

Axioms of structural counterfactuals: composition, effectiveness, reversibility.

**Use when:** verifying a fix. The counterfactual test is: if the fix were absent, this test fails. A green test that would also be green without the fix is not evidence.

### 9. Simpson, collapsibility, selection (Ch 6)

Simpson's reversal is not a paradox once the causal DAG is drawn: whether to aggregate or stratify is a causal decision (which variables are confounders vs mediators vs colliders), not a statistical one. Chronological order alone is not enough.

---

## Practitioner rules (debugging, evals, A/B)

1. Draw the DAG of causes *before* interpreting a correlation, a dashboard metric, or a "fix worked."
2. Distinguish **see** vs **do**. Correlation in logs ≠ intervening on the suspected cause.
3. Do not condition on colliders or their descendants (error-only log slices, "users who filed a ticket", survivors). That manufactures associations.
4. Adjust for confounders (common causes), not for mediators (on the causal path) when the target is the *total* effect.
5. If test env and prod disagree, name the unobserved common cause; do not treat the test-pass as the causal effect of the patch.
6. A/B tests are do(treatment). Observational "users who chose X" are not, unless back-door/front-door conditions hold.
7. Identifiability is a graph property. If the query is not identifiable, more data of the same kind will not save it — change the experiment or the assumed graph.

## Anti-patterns

- **Equating regression with causation.** Coefficients are associational unless the adjustment set is back-door admissible.
- **Conditioning on the outcome or on error state** to "focus analysis" (collider bias).
- **Adjusting for everything measured** (M-bias: two independent causes of treatment and outcome linked through a collider you conditioned on).
- **Declaring a fix causal because tests went green** without the counterfactual (tests would fail without the fix) and without ruling out confounders (test-only environment).
- **Cycles in the causal DAG of state** in concurrent systems: if A mutates before B and B before A with no ordering edge, that is not a valid causal model of the runtime — it is a race.

## Chapter index

| # | Title | Load for |
|---|-------|----------|
| 1 | Probabilities, graphs, causal models | d-separation, SCM, see vs do |
| 2 | Inferred causation | discovery, stability, Markov |
| 3 | Identification of causal effects | back-door, front-door, do-calculus |
| 4 | Actions, plans, direct effects | sequential back-door, mediation |
| 5 | Structural models in social science | SEM meaning, exogeneity |
| 6 | Simpson, confounding, collapsibility | no statistical test for confounding |
| 7 | Structure-based counterfactuals | twin networks, axioms |
| 8 | Imperfect experiments | IV bounds, noncompliance |
| 9 | Probability of causation | PN, PS, PNS |
| 10 | The actual cause | preemption, beams |
| 11 | Reflections | do-calculus intuition, ignorability |

## Topic index

- **back-door / adjustment / ignorability** → Ch 3, 11.3
- **collider / Berkson / selection bias** → Ch 1.2.3, 6
- **confounding** → Ch 3.3, 6 (not a statistical concept)
- **counterfactuals / twin network** → Ch 1.4.4, 7
- **d-separation** → Ch 1.2.3, 11.1.2
- **do-calculus / do(x)** → Ch 3.4, 11.3.6
- **front-door** → Ch 3.3.2
- **SCM / structural equations / autonomy** → Ch 1.4, 5, 7.1
- **Simpson** → Ch 6

## Scope

Book content only (Pearl 2009). For debugging procedure use `systematic-debugging`; for the failing-before test use `test-driven-development`. Does not cover post-2009 identification software packages.

# Chapter 1: Events and Their Probabilities

## Core Idea
Probability theory is built on a triple (Ω, F, P): a sample space, a σ-field of events, and a probability measure. The σ-field constraint (closed under countable unions and complements) is what makes rigorous probability possible on infinite spaces.

## Frameworks Introduced

- **Probability Space (Ω, F, P)**: The fundamental object of probability theory.
  - When to use: Formalizing any random system.
  - How: (1) Define Ω (all outcomes), (2) Define F (σ-field of events of interest), (3) Assign P satisfying countable additivity.

- **σ-field (σ-algebra)**: Collection F of subsets of Ω closed under: ∅ ∈ F; countable unions; complements.
  - When to use: Whenever you need to assign probabilities to infinite collections of events.
  - Distinction from field: A field is closed only under *finite* unions — insufficient when Ω is infinite.

## Key Concepts

- **Ω** — sample space: set of all possible outcomes
- **Event** — subset of Ω that belongs to F
- **σ-field** — collection of subsets closed under countable unions and complements; also called σ-algebra
- **Probability measure P** — function F → [0,1] with P(∅)=0, P(Ω)=1, countably additive on disjoint events
- **Conditional probability** — P(A|B) = P(A∩B)/P(B) for P(B) > 0
- **Independence** — A, B independent iff P(A∩B) = P(A)P(B)
- **Bayes' theorem** — P(B|A) = P(A|B)P(B)/P(A)
- **Partition theorem** — P(A) = Σ P(A|Bi)P(Bi) for partition {Bi}
- **Borel σ-field** — smallest σ-field containing all open intervals of ℝ; standard for continuous r.v.s

## Mental Models

- Think of F as "the events we can meaningfully ask about." Not every subset of an infinite Ω can be assigned a probability (non-measurable sets exist).
- Use conditional probability as a restriction: P(·|B) is a new probability measure on (Ω, F).
- Independence of events ≠ disjointness. Disjoint events (P(A∩B)=0) are negatively correlated, not independent (unless P(A)=0).

## Anti-patterns

- **Ignoring measure theory**: Treating probabilities on infinite spaces without a σ-field leads to paradoxes (Vitali sets).
- **Confusing independence and disjointness**: Two events can be independent yet intersecting.
- **Bayes inversion without base rates**: P(disease|test+) ≠ P(test+|disease) without the prior P(disease).

## Worked Example

**Gambler's ruin framing** (§1.7): Sample space Ω = all paths of random walk. Event A = "walk hits 0 before N". σ-field = all cylinder sets on paths. P = product measure from coin tosses. This triple lets us compute P(A) rigorously via conditioning on first step.

## Key Takeaways

1. A probability space REQUIRES all three components (Ω, F, P); informal statements skip F at their peril.
2. σ-fields are necessary for continuous and infinite sample spaces to avoid non-measurable events.
3. Conditional probability P(·|B) is itself a valid probability measure — use the tower property freely.
4. Bayes' theorem = conditional probability + law of total probability; requires P(B) > 0.

## Connects To

- **Ch07**: Conditional expectation generalizes conditional probability to random variables.
- **Ch12**: Filtrations are increasing sequences of σ-fields — the information structure of martingales.

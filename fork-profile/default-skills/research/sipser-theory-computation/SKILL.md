---
name: sipser-theory-computation
description: "Knowledge base from Introduction to the Theory of Computation by Sipser. Use when applying finite automata, regular languages, context-free grammars, Turing machines, decidability, complexity theory (P, NP, PSPACE) to agent task planning, halting detection, resource-bounded reasoning, and complexity-gated planning in Hermes."
related_skills:
  - clrs-algorithms
  - wald-sequential-analysis
  - complexity-gated-planning
  - systematic-debugging
  - adaptive-agent-reasoning
book_type: technical
depth: study
---

# Sipser — Introduction to the Theory of Computation (3rd ed., 2013)

Knowledge base from Michael Sipser *Introduction to the Theory of Computation*, 3rd Edition (Cengage, 2013, 482pp). ISBN 978-1-133-18779-0.

Structure: three parts — **Automata and Languages** (Ch 0–2), **Computability Theory** (Ch 3–6), **Complexity Theory** (Ch 7–10).

Load [references/cheatsheet.md](references/cheatsheet.md) for formal definitions and key theorems; [references/glossary.md](references/glossary.md) for terms; [references/hermes-applications.md](references/hermes-applications.md) for agent use patterns.

---

## When to use this skill

- **Halting detection** — recognizing when an agent loop may not terminate (reductions to ATM)
- **Complexity-gated planning** — estimating whether a task is tractable (P-class) or requires approximation / timeout (NP-complete or harder)
- **Pattern matching optimization** — exploiting DFA/regex theory for skill routing (regular expression optimization, pumping lemma anti-patterns)
- **Formal language theory** — CFG/PDA for structured input validation
- **Decidability analysis** — identifying which agent queries are decidable vs. undecidable in principle

---

## Part One: Automata and Languages (Ch 0–2)

### Chapter 0: Introduction

Mathematical foundations: sets, sequences, functions, relations, graphs, strings, languages, Boolean logic, proof techniques (construction, contradiction, induction).

**Key notation:**
- Σ = alphabet, Σ* = all strings over Σ, ε = empty string
- A **language** L ⊆ Σ* — the central object of study
- A **problem** is a decision problem ↔ a language membership test

### Chapter 1: Regular Languages

#### 1.1 Finite Automata (DFA)

**Formal definition:** M = (Q, Σ, δ, q₀, F) where Q = states, δ: Q×Σ→Q = transition function, q₀ ∈ Q = start, F ⊆ Q = accept states.

**Computation:** M accepts w = w₁w₂…wₙ if ∃ sequence r₀,r₁,…,rₙ of states:
- r₀ = q₀
- rᵢ = δ(rᵢ₋₁, wᵢ) for i=1..n
- rₙ ∈ F

**Regular language:** L(M) for some DFA M.

Regular languages are closed under union, concatenation, complement, intersection, Kleene star.

#### 1.2 Nondeterminism (NFA)

NFA: δ: Q×Σε→P(Q). Every NFA has an equivalent DFA (subset construction); exponential blowup in states possible but not in computation.

**Key insight for Hermes:** Nondeterminism is a *mathematical* tool (certificates, guess-and-verify), not a physical one. Agent branching approximates NTM computation.

#### 1.3 Regular Expressions

Closed-form description of regular languages. Equivalence to DFA/NFA (Kleene's theorem). Used in skill routing pattern matching.

**Optimization:** Compile skill-selector regexes to DFAs to eliminate exponential backtracking; avoid nested repetition patterns.

#### 1.4 Nonregular Languages / Pumping Lemma

**Pumping Lemma (regular):** If L is regular with pumping length p, then every s ∈ L with |s| ≥ p can be written s = xyz with:
1. |y| > 0
2. |xy| ≤ p  
3. ∀k ≥ 0: xyᵏz ∈ L

**Use in Hermes:** If a skill-routing pattern *cannot* be pumped — i.e., the set of matching inputs is not closed under repetition — then a DFA/regex cannot express it; use a PDA/grammar or a more complex matcher.

**Anti-pattern detector:** If a proposed regex pattern for skill routing has nested counting constraints (e.g., "match exactly n balanced brackets"), it is *not regular* — the pumping lemma demonstrates impossibility. Escalate to CFG or explicit parser.

### Chapter 2: Context-Free Languages

#### 2.1 Context-Free Grammars (CFG)

G = (V, Σ, R, S): variables V, terminals Σ, rules R (productions), start symbol S.

**Chomsky Normal Form (CNF):** every rule A→BC or A→a. Every CFG convertible to CNF. Key for CYK parsing.

**Ambiguity:** multiple parse trees for same string → ambiguous grammar → parsing problems. Inherent ambiguity exists for some CFLs.

#### 2.2 Pushdown Automata (PDA)

PDA = NFA + stack. Equivalent to CFGs. Nondeterministic PDAs more powerful than deterministic PDAs.

#### 2.3 Non-Context-Free Languages / Pumping Lemma (CFL)

**Pumping Lemma (CFL):** s = uvxyz, |vy| > 0, |vxy| ≤ p, uvⁿxyⁿz ∈ L for all n ≥ 0.

**Hermes application:** Pattern-matching rules that require matching two separate counting constraints simultaneously (e.g., balanced parentheses *and* matched keywords) require CFG or custom parser — neither regex nor simple finite state will work.

#### 2.4 Deterministic CFLs (DCFL)

Deterministic PDAs (DPDA) decide DCFLs. Proper subset of CFLs. LR(k) parsing works for DCFGs — basis for programming language parsing.

---

## Part Two: Computability Theory (Ch 3–6)

### Chapter 3: The Church–Turing Thesis

#### 3.1 Turing Machines

**Formal definition:** M = (Q, Σ, Γ, δ, q₀, q_accept, q_reject)
- Γ = tape alphabet ⊇ Σ ∪ {□} (blank)
- δ: Q×Γ → Q×Γ×{L,R} = transition
- Infinite tape, read/write head

**Configuration:** (q, tape content, head position). Computation = sequence of configurations. Machine *halts* by entering q_accept or q_reject; *loops* if it runs forever.

**Church–Turing Thesis:** Every effectively computable function is Turing-computable. Any "reasonable" model of computation is equivalent to TMs.

#### 3.2 Variants of TMs

Multitape TMs, nondeterministic TMs, enumerators — all equivalent in *language recognition power* to single-tape deterministic TMs (polynomial overhead for multitape; exponential for nondeterministic simulation).

#### 3.3 Algorithm = TM that halts on all inputs

A **decider** halts on every input. A **recognizer** (Turing-recognizable) may loop.

---

### Chapter 4: Decidability

#### 4.1 Decidable Languages

```
A_DFA = {⟨B,w⟩ | B is a DFA accepting w}         — decidable (Thm 4.1)
E_DFA = {⟨A⟩ | L(A) = ∅}                          — decidable (Thm 4.4)
EQ_DFA = {⟨A,B⟩ | L(A) = L(B)}                    — decidable (Thm 4.5)
A_CFG = {⟨G,w⟩ | G is a CFG generating w}         — decidable (Thm 4.7)
E_CFG = {⟨G⟩ | L(G) = ∅}                          — decidable (Thm 4.8)
```

#### 4.2 Undecidability — The Halting Problem

**ATM = {⟨M,w⟩ | M is a TM and M accepts w}**

**THEOREM 4.11:** ATM is **undecidable**.

**Proof sketch (diagonalization):** Assume decider H for ATM exists. Construct D: on input ⟨M⟩, run H on ⟨M,⟨M⟩⟩ and do the opposite. D(⟨D⟩) accepts iff D rejects — contradiction. ∎

**ATM is Turing-recognizable** (by universal TM U) but not decidable: there is no algorithm that correctly answers "does M halt on w?" for all M, w.

**HALT_TM** (the halting problem) is also undecidable — reduction from ATM.

**⚠️ Hermes implication:** No agent loop can *generally* decide whether another agent will terminate. Halting detection for Hermes agents is a *heuristic*, not an algorithm — there are inputs on which any heuristic is wrong.

---

### Chapter 5: Reducibility

**Many-one (mapping) reducibility:** A ≤_m B means a computable f exists s.t. w ∈ A ↔ f(w) ∈ B. If B decidable then A decidable. Contrapositive: A undecidable → B undecidable.

**Key undecidable languages:**
```
HALT_TM = {⟨M,w⟩ | M halts on w}               — undecidable
E_TM = {⟨M⟩ | L(M) = ∅}                         — undecidable  
REGULAR_TM = {⟨M⟩ | L(M) regular}               — undecidable
EQ_TM = {⟨M₁,M₂⟩ | L(M₁) = L(M₂)}             — undecidable
```

**Rice's Theorem:** Every non-trivial semantic property of TMs is undecidable.

**Hermes implication:** Deciding *any non-trivial property* of agent behavior (does it always produce valid JSON? does it ever loop?) is undecidable in general.

---

### Chapter 6: Advanced Computability

**Recursion Theorem:** A TM can obtain its own description and act on it — basis for self-modifying agents, quines, and proof of ATM undecidability.

**Turing reducibility (oracle):** A ≤_T B — A decidable relative to oracle B. Hierarchy of unsolvability.

**Kolmogorov complexity:** C(x) = length of shortest TM description of x. Most strings are incompressible (|C(x) ≥ |x| - c for all but finitely many c). Incompressible strings are "random" — no compact pattern.

---

## Part Three: Complexity Theory (Ch 7–10)

### Chapter 7: Time Complexity

#### Complexity classes (time)

**Definition:** TIME(t(n)) = languages decidable by O(t(n)) time TM.

**P** = ⋃_k TIME(nᵏ) — polynomial time, deterministic.

**NP** = languages with polynomial-time verifiers, equivalently decided by polynomial-time NTMs.

**NP alternative:** L ∈ NP iff ∃ polynomial-time verifier V and polynomial p s.t. for all w: w ∈ L ↔ ∃ certificate c with |c| ≤ p(|w|) and V accepts ⟨w,c⟩.

**P ⊆ NP.** P = NP? — open; assumed P ≠ NP.

#### 7.4 NP-completeness

**Polynomial reducibility:** A ≤_p B — computable in polynomial time.

**NP-hard:** ∀A ∈ NP: A ≤_p B.  
**NP-complete:** NP-hard ∧ B ∈ NP.

**Cook–Levin Theorem:** SAT is NP-complete.

**Classic NP-complete problems:**
- SAT, 3SAT
- CLIQUE, VERTEX-COVER, INDEPENDENT-SET
- HAMPATH, TSP
- SUBSET-SUM, PARTITION

**Hermes complexity-gating rule:**
- If task ∈ P: attempt direct algorithmic solution
- If task ∈ NP-complete: use approximation, randomization, or timeout heuristic; do NOT expect polynomial exact solution
- If task is PSPACE-complete: requires exhaustive search over exponential state space; decompose or approximate

### Chapter 8: Space Complexity

**PSPACE** = ⋃_k SPACE(nᵏ). P ⊆ NP ⊆ PSPACE ⊆ EXPTIME.

**PSPACE-complete:** TQBF (True Quantified Boolean Formulas), Generalized Geography.

**Savitch's Theorem:** NSPACE(f(n)) ⊆ DSPACE(f(n)²) — space more forgiving than time with nondeterminism.

**L** (logarithmic space), **NL** (nondeterministic log space), **NL = coNL** (Immerman–Szelepcsényi).

### Chapter 9: Intractability

**Hierarchy theorems:** More time/space → strictly more languages:
- TIME(n) ⊊ TIME(n log n) ⊊ TIME(n²) ⊊ … (TIME hierarchy)
- Resources are genuinely separable

**Relativization:** Oracle machines can make P ≠ NP and P = NP simultaneously true — diagonalization alone cannot resolve P vs NP.

**Circuit complexity:** Boolean circuits as a model; NC (efficient parallelism); P-completeness.

### Chapter 10: Advanced Complexity

**BPP** — bounded-error probabilistic polynomial time. BPP ⊆ PSPACE. Likely BPP = P.

**Approximation algorithms** — when exact NP-complete solutions are too slow, polynomial approximation ratios are achievable (vertex cover ≤ 2×OPT, TSP with triangle inequality ≤ 1.5×OPT).

**Interactive Proof Systems:** IP = PSPACE. Randomized verifier + prover interaction can verify PSPACE problems.

**Polynomial hierarchy (PH):** Σ₂ = NP^NP, Π₂ = coNP^NP, etc. Likely infinite.

---

## Hermes Agent Applications

### 1. Halting Detection (Heuristic)

ATM is undecidable → no general halting detector. Hermes strategy: deploy **bounded resources** (step counter, wall-clock timeout) rather than a halting oracle. A loop that has run > n_max steps *probably* won't halt — escalate, abort, or report.

**Heuristic:** Track the sequence of (state, last-output) pairs. If a recent window of k steps shows no progress (no change in environment state, no new tool calls succeeding), treat as probable loop and trigger `agent-runtime-loop-patterns` recovery.

### 2. Complexity-Gated Planning

Before selecting a planning strategy, classify the task:
- **P-class indicators:** sorting, graph traversal, pattern matching, linear programming
- **NP-complete indicators:** scheduling with arbitrary constraints, TSP-style routing, combinatorial optimization, SAT-like constraint solving
- **PSPACE indicators:** game tree search (Go, chess), full quantified planning, modal verification

For NP-complete tasks: decompose, find polynomial special cases, or bound search to polynomial approximation.

### 3. Pumping Lemma as Anti-Pattern Detector

If a proposed skill routing pattern requires counting or balanced matching, it is *not regular*. Signal to replace regex routing with:
- CFG-style parsing for context-free patterns
- Explicit state machines for bounded counting
- Semantic matching (embeddings) for open-ended matching

### 4. Regular Expression Optimization for Skill Routing

Compile skill trigger patterns to DFAs at startup to avoid exponential backtracking. Apply subset construction to merge overlapping patterns. Avoid `(a+)+`-style catastrophic backtracking patterns.

---

## Chapter Index

| # | Title | Core concepts |
|---|-------|---------------|
| 0 | Introduction | Math prereqs, proof methods |
| 1 | Regular Languages | DFA, NFA, regex, pumping lemma |
| 2 | Context-Free Languages | CFG, PDA, CNF, CYK, pumping lemma CFL |
| 3 | Church–Turing Thesis | TM definition, variants, Church–Turing |
| 4 | Decidability | ATM undecidable, diagonalization, halting |
| 5 | Reducibility | many-one reducibility, Rice's theorem |
| 6 | Advanced Computability | recursion theorem, Kolmogorov complexity |
| 7 | Time Complexity | P, NP, NP-completeness, Cook–Levin |
| 8 | Space Complexity | PSPACE, L, NL, Savitch |
| 9 | Intractability | hierarchy theorems, circuit complexity |
| 10 | Advanced Complexity | BPP, approximation, IP, PH, cryptography |

## Topic Index

- **ATM / halting problem** → Ch 4.2, Thm 4.11
- **Church–Turing Thesis** → Ch 3.3
- **CFG / PDA** → Ch 2.1–2.3
- **Complexity classes P, NP, PSPACE** → Ch 7–8
- **Cook–Levin Theorem** → Ch 7.4
- **Decidability** → Ch 4.1–4.2
- **DFA / NFA / regex** → Ch 1.1–1.3
- **Diagonalization** → Ch 4.2
- **Kolmogorov complexity** → Ch 6.4
- **NP-completeness** → Ch 7.4–7.5
- **Pumping lemma (regular)** → Ch 1.4
- **Pumping lemma (CFL)** → Ch 2.3
- **Reducibility** → Ch 5
- **Rice's Theorem** → Ch 5.1
- **Turing machines** → Ch 3.1–3.2

## Scope

Full 3rd edition (482pp), Cengage 2013. Source PDF digitally extracted (text layer). Combine with `clrs-algorithms` for algorithm analysis, `wald-sequential-analysis` for stopping decisions, `adaptive-agent-reasoning` for resource-bounded planning.

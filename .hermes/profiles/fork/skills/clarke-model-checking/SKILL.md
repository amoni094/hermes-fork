---
name: clarke-model-checking
description: Use when verifying concurrent properties with CTL/LTL.
version: 1.0.0
author: Hermes Agent
license: MIT
book_type: technical
depth: study
triggers:
  - CTL / LTL model checking of concurrent systems
  - Kripke structure, labelling, initial states
  - safety G ¬bad, liveness F good, fairness GF
  - symbolic BDD / OBDD model checking
  - bounded model checking SAT unrolling
  - partial order reduction ample stubborn sets
  - SPIN SMV counterexample guided simulation
  - cron scheduling invariants, atomic write, gate-audit
related_skills:
  - harrison-practical-logic
  - huth-ryan-logic
  - sipser-theory-computation
  - puterman-mdp
  - astrom-murray-feedback
metadata:
  hermes:
    tags: [model-checking, ctl, ltl, kripke, bdd, fairness, verification]
    related_skills:
      - harrison-practical-logic
      - huth-ryan-logic
      - sipser-theory-computation
---

# Clarke / Grumberg / Peled — Model Checking (MIT Press 1999)

**Authors**: Edmund M. Clarke Jr., Orna Grumberg, Doron A. Peled | **Pages**: xiv+314 | **ISBN**: 0-262-03270-8 | **Chapters**: 16

Source DJVU `~/Downloads/Model checking.djvu` could not be extracted (`djvutxt` not installed). Content is reconstructed from the 1999 edition's known definitions, algorithms, and complexity bounds — not copied text. Bounded model checking is Clarke-lineage (Biere, Cimatti, Clarke, Zhu, TACAS 1999), contemporaneous with the book, not a numbered 1999 chapter.

Not for Hoare-logic proofs or resolution (use `huth-ryan-logic` / `harrison-practical-logic`). Not for MDP policies (use `puterman-mdp`).

Load [cheatsheet.md](cheatsheet.md) for Hermes CTL/LTL recipes; [patterns.md](patterns.md) for algorithms; [glossary.md](glossary.md) for terms. Load a chapter file before answering a topic not in Core Frameworks.

---

## When to Use

- Verify a concurrent Hermes subsystem (cron, WAL writes, gate-audit, skill router, exit-code machine) against a temporal property
- Classify a claim as **safety** (`G ¬bad`), **liveness** (`F good` / `AF p`), or **fairness** (`GF` / justice / compassion) before writing an invariant
- Choose explicit CTL labelling vs BDD symbolic vs SAT unrolling vs partial-order reduction
- Turn a failed check into a counterexample path and a guided simulation

**Don't use for:** theorem proving of sequential functional correctness; probabilistic MDPs; informal "it should eventually happen" without a Kripke model.

---

## Core Frameworks

### 1. Kripke structure (Ch 2)

M = (S, S₀, R, L)

- S — finite set of states
- S₀ ⊆ S — initial states
- R ⊆ S × S — **total** transition relation: ∀s ∃s'. R(s,s')
- L : S → 2^AP — labelling with atomic propositions

A **path** π = s₀ s₁ s₂ … is an infinite sequence with R(s_i, s_{i+1}). M ⊦ φ iff ∀s ∈ S₀. s ⊦ φ.

Use when the system is finite-state concurrent (interleaving product of local machines). If R is not total, add a self-loop on terminals so X/F/G stay well-defined.

### 2. CTL, LTL, CTL* (Ch 3)

**Path quantifiers:** A = all paths, E = exists a path.
**Temporal operators:** X next, F eventually, G globally, U until (R release).

CTL (branching): every temporal operator is immediately preceded by A or E. Minimal set: {EX, EG, EU}; the rest are derived.

```
EX φ     some successor satisfies φ
AX φ     all successors satisfy φ
EF φ     some path eventually φ          = E[true U φ]
AF φ     all paths eventually φ
EG φ     some path always φ
AG φ     all paths always φ              = ¬EF ¬φ
E[φ U ψ] some path: φ until ψ
A[φ U ψ] all paths: φ until ψ
```

LTL (linear): path formulas only; interpreted on all paths from s (implicit A). Typical specs:

- Safety: `G ¬bad`
- Liveness: `F good`
- Response: `G (req → F ack)`

CTL* is the superset (state + path formulas freely mixed). CTL and LTL are incomparable fragments: `AG EF p` is CTL-not-LTL; `FG p` is LTL-not-CTL.

**Rule:** safety + local next-state → CTL `AG`/`AX`. Infinite-trace response under fairness → LTL. Nested path quantifiers (`AG EF recover`) → CTL.

### 3. Explicit CTL labelling (Ch 4) — O(|S| × |φ|)

Label states bottom-up by subformulas of φ:

1. Atoms: s labelled p iff p ∈ L(s).
2. ¬, ∧: Boolean combination of existing labels.
3. EX ψ: label s if some R-successor is labelled ψ.
4. E[φ U ψ] = **least** fixpoint μZ. ψ ∨ (φ ∧ EX Z) — iterate from ∅ adding predecessors of Z that satisfy φ.
5. EG φ = **greatest** fixpoint νZ. φ ∧ EX Z — restrict to the subgraph of φ-states; keep states on a cycle (or infinite path) in that subgraph.

CES 1986: time **O(|S| × |φ|)** with an adjacency-list graph (more precisely O((|S|+|R|) · |φ|)). Fair CTL: restrict E/A to **fair** paths; EG under fairness needs SCC analysis, still linear in |R| per subformula.

Done when every subformula of φ has a label set, and every s ∈ S₀ is labelled φ (or a counterexample is extracted).

### 4. OBDDs and symbolic MC (Ch 5–6)

Encode S as boolean vectors. Represent a set of states and R as **ordered binary decision diagrams** (Bryant). Canonicity ⇒ equality of BDDs is semantic equality.

**Image:** Img(Z)(s') = ∃s. Z(s) ∧ R(s,s')  (relational product; the bottleneck).

**CheckSet** is the same fixpoint as labelling, executed on BDDs:

- EU: Z ← ψ; repeat Z ← ψ ∨ (φ ∧ EX Z) until Z stabilizes
- EG: Z ← φ; repeat Z ← φ ∧ EX Z until Z stabilizes

Variable order dominates runtime (exponential in the worst case). SMV (McMillan) is the reference tool: synchronous modules, CTL specs, fairness constraints.

### 5. LTL, fairness, automata (Ch 7)

LTL MC via tableau / Büchi automaton A_{¬φ}: M ⊦ φ iff L(M) ∩ L(A_{¬φ}) = ∅ iff the product has **no fair cycle** (no reachable accepting SCC).

**Fairness (Manna/Pnueli terms used in the book):**

| Kind | Constraint on a path |
|---|---|
| Weak / justice | FG enabled(t) → GF taken(t), i.e. GF(¬enabled(t) ∨ taken(t)) |
| Strong / compassion | GF enabled(t) → GF taken(t), i.e. FG ¬enabled(t) ∨ GF taken(t) |

Justice: if t is almost-always enabled, it is taken i.o. Compassion: if t is enabled i.o., it is taken i.o. Liveness typically **fails** on unfair schedulers; add fairness constraints before declaring AF/GF false.

Complexity: LTL MC is PSPACE-complete in |φ|; polynomial in |S| for fixed φ.

### 6. Partial-order reduction (Ch 8)

Independence I: α I β iff they commute and neither disables the other. Explore only an **ample** subset of enabled(s):

- **C0** ample(s)=empty iff enabled(s)=empty
- **C1** (persistent): no transition dependent on ample(s) appears before some ample transition is taken
- **C2** (invisibility): if ample(s) ≠ enabled(s), every α ∈ ample(s) is invisible to the formula
- **C3** (cycle): every cycle contains a fully expanded state (or an ample transition taken on the cycle)

Ample sets (Peled), stubborn sets (Valmari), persistent sets (Godefroid). SPIN implements POR + nested DFS on Promela.

### 7. State explosion and mitigation (Ch 9–13)

|S| grows as the product of local states. Mitigate, do not "hope":

- **Abstraction** (Ch 11): existentially abstract; ACTL properties that hold on the abstract model hold on the concrete. Spurious counterexamples → refine.
- **Compositional reasoning** (Ch 10): assume-guarantee. M1 ∥ M2 ⊦ φ from M1 ⊦ φ under assumptions on M2.
- **Symmetry** (Ch 12): quotient by a permutation group that preserves R and L; check on orbit representatives.
- **Equivalence** (Ch 9): bisimulation preserves all CTL*; simulation preserves ACTL.

### 8. Counterexamples and BMC

- AG p fails → finite path from S₀ to ¬p.
- AF p fails → lasso: stem + cycle on which p never holds.
- EG p holds → witness lasso inside p.

Use the path as **guided simulation** (replay on the concrete scheduler / log).

**Bounded MC (SAT):** unroll R to depth k; SAT(∨_{i≤k} ¬p at i) finds a safety bug of length ≤ k. Completeness threshold: k large enough that every loop-free path is covered (e.g. |S|, or recurrence diameter). Unsat at the threshold ⇒ property holds. Prefer BMC for shallow bugs; BDDs/fixpoints for full AG proofs.

### 9. Tools

- **SMV / NuSMV / nuXmv** — synchronous, CTL, BDDs, (later) SAT BMC
- **SPIN** — asynchronous Promela, LTL, nested DFS, POR

---

## Hermes procedure

1. Write the **Kripke model**: enumerative states or a product of local machines (cron jobs, WAL writer, audit gate). Completion: S, S₀, R, L written; R total.
2. Classify the claim: safety / liveness / fairness. Write φ in CTL or LTL (see cheatsheet). Completion: φ is a well-formed CTL or LTL formula over AP ⊆ range(L).
3. Pick engine: |S| small → labelling; boolean next-state → BDD; hunt a short bug → BMC; many independent interleavings → POR.
4. Run the check. If false, extract the counterexample path/lasso and replay it. If liveness failed, **re-check under fairness** before changing the code.
5. If state explosion: abstract, compose, symmetry-reduce, or POR — then re-verify. Completion: every initial state labelled, or a concrete failing trace.

---

## Chapter Index

| # | Title | Key frameworks |
|---|-------|----------------|
| [ch01](chapters/ch01-introduction.md) | Introduction | automatic vs deductive vs testing; counterexamples |
| [ch02](chapters/ch02-modeling-systems.md) | Modeling Systems | Kripke (S,S₀,R,L); interleaving product |
| [ch03](chapters/ch03-temporal-logics.md) | Temporal Logics | CTL, LTL, CTL*; A/E, X/F/G/U |
| [ch04](chapters/ch04-model-checking.md) | Model Checking | labelling; O(∣S∣×∣φ∣); fair CTL |
| [ch05](chapters/ch05-binary-decision-diagrams.md) | Binary Decision Diagrams | OBDD canonicity; apply; variable order |
| [ch06](chapters/ch06-symbolic-model-checking.md) | Symbolic Model Checking | image; fixpoints; SMV |
| [ch07](chapters/ch07-ltl-model-checking.md) | LTL Model Checking | Büchi product; safety/liveness; justice/compassion |
| [ch08](chapters/ch08-partial-order-reduction.md) | Partial Order Reduction | independence; ample/stubborn; SPIN |
| [ch09](chapters/ch09-equivalences-preorders.md) | Equivalences and Preorders | bisimulation; simulation; ACTL |
| [ch10](chapters/ch10-compositional-reasoning.md) | Compositional Reasoning | assume-guarantee |
| [ch11](chapters/ch11-abstraction.md) | Abstraction | existential abstraction; refinement |
| [ch12](chapters/ch12-symmetry.md) | Symmetry | orbit quotient |
| [ch13](chapters/ch13-infinite-families.md) | Infinite Families of Finite-State Systems | parameterized systems |
| [ch14](chapters/ch14-discrete-realtime.md) | Discrete Real-Time | quantitative temporal |
| [ch15](chapters/ch15-continuous-realtime.md) | Continuous Real Time | timed automata / regions |
| [ch16](chapters/ch16-conclusion-bmc-tools.md) | Conclusion, BMC, tools | SAT unrolling; SPIN/SMV; counterexamples |

## Topic Index

- **Ample / stubborn / persistent sets** → ch08
- **Atomic write / I/O automata** → cheatsheet, ch02, ch07
- **BDD / OBDD / image computation** → ch05, ch06
- **Bisimulation / simulation** → ch09
- **Bounded model checking** → ch16, cheatsheet
- **CTL labelling algorithm** → ch04
- **CTL*** → ch03
- **Counterexample / lasso / guided simulation** → ch04, ch16
- **Cron no-contention AG(writer → AX ¬concurrent)** → cheatsheet
- **Fairness, justice, compassion** → ch07, patterns
- **Gate-audit AF(calibration_data_available)** → cheatsheet
- **Kripke structure** → ch02
- **LTL safety/liveness** → ch03, ch07
- **SMV** → ch06, ch16
- **SPIN** → ch08, ch16
- **State explosion** → ch01, ch08, ch10–ch13
- **Symmetry reduction** → ch12

## Supporting Files

- [glossary.md](glossary.md) — terms
- [patterns.md](patterns.md) — algorithms and proof patterns
- [cheatsheet.md](cheatsheet.md) — decision rules + Hermes CTL/LTL recipes

## Common Pitfalls

- Treating LTL `FG p` as CTL `AF AG p` (they differ).
- Declaring liveness false without fairness constraints.
- Non-total R, then using X.
- SAT BMC unsat at small k ≠ proved; need completeness threshold.
- Existential abstraction: concrete may satisfy ACTL that abstract rejects (spurious cex).

## Verification Checklist

- [ ] M = (S,S₀,R,L) written; R total; AP match φ
- [ ] φ is CTL or LTL (not an illegal CTL* mix unless intended)
- [ ] Safety vs liveness vs fairness classified
- [ ] Engine matches |S| and property class
- [ ] Counterexample replayed, or all s ∈ S₀ labelled
- [ ] Liveness re-checked under the intended fairness

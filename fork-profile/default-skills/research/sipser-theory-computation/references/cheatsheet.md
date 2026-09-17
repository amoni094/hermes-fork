# Sipser Theory of Computation — Quick Reference Cheatsheet

## Formal Definitions

### DFA
M = (Q, Σ, δ, q₀, F)
- Q: finite set of states
- Σ: input alphabet
- δ: Q × Σ → Q (transition function)
- q₀ ∈ Q: start state
- F ⊆ Q: accept states
Language: L(M) = {w | M accepts w}

### NFA
M = (Q, Σ, δ, q₀, F)
- δ: Q × Σε → P(Q)  (Σε = Σ ∪ {ε})
Every NFA has equivalent DFA (subset construction, up to 2^Q states).

### Regular Expression
- ∅ (empty language), ε (empty string), a ∈ Σ
- R₁ ∪ R₂, R₁ ∘ R₂, R₁* (Kleene star)
Equivalent to DFA/NFA (Kleene's theorem).

### CFG
G = (V, Σ, R, S)
- V: variables, Σ: terminals, R: production rules (A → w), S: start
Generates: L(G) = {w ∈ Σ* | S ⇒* w}
CNF: A → BC or A → a

### PDA
M = (Q, Σ, Γ, δ, q₀, F)
- Γ: stack alphabet
- δ: Q × Σε × Γε → P(Q × Γε)
Equivalent to CFG (nondeterministic PDA).

### Turing Machine
M = (Q, Σ, Γ, δ, q₀, q_acc, q_rej)
- Γ: tape alphabet (□ ∈ Γ, Σ ⊆ Γ)
- δ: Q × Γ → Q × Γ × {L,R}
Accepts: enters q_acc. Rejects: enters q_rej. Loops: neither.

---

## Key Theorems

| Theorem | Statement |
|---------|-----------|
| Pumping Lemma (DFA) | Regular L, ∃p: s∈L, |s|≥p → s=xyz, |y|>0, |xy|≤p, xykz∈L ∀k≥0 |
| Pumping Lemma (CFL) | CFL L, ∃p: s∈L, |s|≥p → s=uvxyz, |vy|>0, |vxy|≤p, uvⁿxyⁿz∈L ∀n≥0 |
| Kleene | Regular ↔ DFA ↔ NFA ↔ regex |
| CFL = PDA | CFL (via CFG) ↔ nondeterministic PDA |
| Church–Turing | TM = effective computability |
| Thm 4.11 | ATM undecidable (diagonalization) |
| Rice | Every nontrivial semantic TM property undecidable |
| Cook–Levin | SAT is NP-complete |
| Savitch | NSPACE(f(n)) ⊆ DSPACE(f(n)²) |
| Hierarchy | TIME(t) ⊊ TIME(t log t): more time → more languages |
| Immerman–Sz. | NL = coNL |
| IP = PSPACE | Interactive proofs capture polynomial space |

---

## Complexity Class Hierarchy

```
L ⊆ NL ⊆ P ⊆ NP ⊆ PSPACE ⊆ EXPTIME ⊆ EXPSPACE
         ‖
        coNL
```

All inclusions known; most separations open (P ≠ NP assumed).

---

## Decidability Table

| Language | Status | Method |
|----------|--------|--------|
| A_DFA | Decidable | Simulate DFA |
| E_DFA | Decidable | BFS/DFS from start |
| EQ_DFA | Decidable | Symmetric difference |
| A_CFG | Decidable | CYK algorithm |
| E_CFG | Decidable | Mark generating vars |
| A_TM | **Undecidable** (Turing-recognizable) | Diagonalization |
| HALT_TM | Undecidable | Reduce from A_TM |
| E_TM | Undecidable | Reduce from A_TM |
| REGULAR_TM | Undecidable | Rice's theorem |
| EQ_TM | Undecidable | Rice's theorem |
| All semantic TM props | Undecidable | Rice's theorem |

---

## NP-Complete Problems

| Problem | Description |
|---------|-------------|
| SAT | Boolean formula satisfiability |
| 3SAT | 3-CNF satisfiability |
| CLIQUE | Graph has k-clique |
| VERTEX-COVER | Graph has vertex cover of size k |
| INDEPENDENT-SET | Graph has independent set of size k |
| HAMPATH | Directed Hamiltonian path s→t |
| TSP | Traveling salesman ≤ k |
| SUBSET-SUM | Subset summing to t |
| PARTITION | Split multiset into equal-sum parts |

Reduction chain: SAT ≤_p 3SAT ≤_p CLIQUE ≤_p VERTEX-COVER

---

## Hermes Quick Rules

1. **Task has no termination guarantee?** → It may be ATM-equivalent; bound it with timeout, not logic.
2. **Pattern requires counting/balancing?** → Not regular; use CFG or explicit parser.
3. **Optimization over combinatorial space?** → Check NP-completeness; use approximation.
4. **Regex with nested repetition in skill router?** → Compile to DFA first; avoid catastrophic backtracking.
5. **Need to verify any semantic property of agent code?** → Rice's theorem: undecidable in general; use static analysis heuristics.
6. **Game/planning with full state space search?** → Likely PSPACE; bound depth/breadth.

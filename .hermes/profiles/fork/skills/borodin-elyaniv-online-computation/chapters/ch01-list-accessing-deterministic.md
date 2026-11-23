# Chapter 1: Introduction to Competitive Analysis — The List Accessing Problem

## Core Idea
An online algorithm must answer each request before seeing the rest of the sequence. Quality is the **competitive ratio**: ALG’s cost versus an offline OPT that sees all of `σ`. List accessing (list update) is the first worked example: maintain an unsorted linear list; cost of accessing an item is its position.

## Key Concepts
- **Request sequence** `σ = (σ_1,…,σ_n)` over a universe of items. Static model: no inserts/deletes (book also treats dynamic).
- **Cost model (full cost):** accessing the item at position `i` costs `i`. After the access the algorithm may reorganize.
- **Free transposition:** swap the accessed item with any item closer to the front (or adjacent, depending on model). **Paid exchange:** any other swap, charged 1.
- **MTF (Move-to-Front):** after access, move the item to the front (free).
- **TRANS (Transpose):** swap the accessed item with its immediate predecessor.
- **FC (Frequency Count):** keep access counts; keep the list in nonincreasing frequency order. Extra unbounded memory.
- **OPT:** offline optimum (may use paid exchanges). Paid exchanges are necessary: a 3-item sequence exists with OPT_free = 9 vs OPT = 8 (Exercise 1.1).
- **Potential / amortized cost:** `a_i = ℓ_i + Φ_i − Φ_{i−1}`. If `Φ ≥ 0` then `∑ ℓ_i ≤ ∑ a_i + Φ_0`.

## Frameworks and Methods
- **Sleator–Tarjan inversion potential.** `Φ` = number of inversions of MTF’s list vs OPT’s list: pair `(x,y)` with `x` before `y` in MTF but `y` before `x` in OPT. `Φ_0 = 0` if lists start equal; `Φ ≥ 0` always.
- **Amortized bound per request.** If OPT finds the item at position `s` and then does `P` paid and `F` free transpositions, MTF’s amortized cost is at most `2s − 1 + P − F`. Summing and using `∑(−1) = −n` yields Theorem 1.1.
- **Lower bounds via adversary.** Construct `σ` so every deterministic ALG is forced to pay ~2·OPT (cruel: always request the last item, or pairwise crossing arguments).
- **List factoring.** Reduce n-list analysis to pairwise 2-lists (phase partitioning); used for tighter bounds in Ch. 2.

## Key Results and Theorems

**Definition (c-competitive).** ∃ `α` such that ∀ `σ`: `ALG(σ) ≤ c · OPT(σ) + α`.

**Theorem 1.1 (Sleator–Tarjan).** If MTF and OPT start in the same configuration and `σ` has `n` requests,
```
MTF(σ) ≤ 2 · OPT_C(σ) + OPT_P(σ) − OPT_F(σ) − n.
```
Hence MTF is **2-competitive** (paid exchanges of OPT only help the bound). Proof: inversion potential as above.

**TRANS is not competitive.** There are sequences on which TRANS/OPT → ∞. Do not MTF-substitute TRANS in a cache of skills/scripts.

**FC is not (worst-case) competitive.** Frequency can be stuck on a stale prefix while OPT MTF-cycles a small working set.

**Deterministic lower bound.** No deterministic list-update algorithm is better than 2-competitive (up to the usual additive). Matching MTF.

**Exercise 1.2.** Any algorithm can be simulated using only paid transpositions (before the access) at the same cost; holds for general access costs `f(i)` when adjacent-swap cost is `f(i)−f(i+1)`.

## Key Equations
- `ALG(σ) = ALG_C(σ) + ALG_P(σ)` (search + paid); MTF/TRANS/FC pay only search if they use free moves.
- `a_i = ℓ_i + ΔΦ_i`, `∑ ℓ = ∑ a − Φ_n + Φ_0 ≤ ∑ a + Φ_0`.
- Inversions involving the requested item `x_j` at MTF position `k`, OPT position `s`: `k − 1 − v` items precede `x` in both lists.

## Worked Example
List `{x1,x2,x3}`, MTF vs OPT, `σ = x3,x2,x1`. Each MTF miss that OPT also pays, plus inversion accounting, stays within 2·OPT. For Exercise 1.1, `σ = x3,x2,x1,x2` from `(x1,x2,x3)`: OPT = 8 with a paid exchange; free-only OPT = 9.

## Hermes application
Cron / skill-cache / recently-used tool list is **list update**. Default: **MTF** (or a 2-competitive TIMESTAMP). Do not use TRANS or raw FC for worst-case guarantees. See [patterns.md](../patterns.md).

## Anti-patterns
- **Calling TRANS “almost MTF.”** TRANS is not competitive.
- **Dropping the additive `α`.** Needed when initial Φ or finite startup cost appears.
- **Comparing to a suboptimal offline baseline** and calling the number a competitive ratio.
- **Using average-case (i.i.d. requests) as competitive analysis.** That is Appendix B / distributional, not Ch. 1.

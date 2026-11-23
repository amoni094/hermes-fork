# Cheatsheet — CTL/LTL for Hermes

## Decision rules

| Claim kind | Form | Logic | Engine |
|---|---|---|---|
| Invariant | G ¬bad / AG ¬bad | LTL or CTL | reachability / BDD |
| Next-state mutex | AG (p → AX q) | CTL | labelling or SMV |
| Recovery exists | AG EF p | CTL (not LTL) | labelling / BDD |
| Eventually on every run | AF p / F p | CTL / LTL | needs fairness |
| Response | G (req → F ack) | LTL | Büchi + fairness |
| Persistence | FG p | LTL (not CTL) | Büchi |
| Fair response i.o. | GF req → GF ack | LTL + compassion | Streett / fair product |

**CTL vs LTL:** AG EF p ∈ CTL\\LTL; FG p ∈ LTL\\CTL. Do not translate blindly.

**Complexity:** CTL O(|S|×|φ|); LTL PSPACE in |φ|.

**R total:** add self-loops on terminals before X/G/F.

**BMC:** unsat at k is not AG unless k ≥ completeness threshold.

---

## Hermes recipes

### 1. Cron no-contention

**Property (CTL):** `AG (writer_active → AX ¬concurrent_writer)`

**Model:** WAL-mode SQLite as a Kripke product: writer ∈ {idle, active}, lock ∈ {free, held}, readers. `writer_active` iff writer=active; `concurrent_writer` iff two agents hold the write lock (should be impossible).

**Why it holds:** WAL serializes writers; next-state after `writer_active` has the lock still exclusive, so every successor satisfies ¬concurrent_writer. Prove on the SMV/boolean model (BDD AG), not by testing.

**Failure shape:** finite path to a state with two active writers — lock not in R.

### 2. Atomic write invariant

**Property (LTL safety):** `G ¬partial_write_visible`

**Model:** I/O automaton with actions `begin_write`, `commit`, `abort`. Visible reader states see only pre- or post-images. Intermediate buffers are *not* labelled visible, or are labelled `partial_write_visible` and must be unreachable to readers.

**Check:** reachability of a reader state with torn data. No fairness. Cex is a finite prefix — the guided simulation for the WAL/fsync bug.

### 3. Gate-audit cold-start

**Property (CTL liveness):** `AF calibration_data_available`

**Holds iff** every path from cold-start eventually runs the sweep (and the sweep labels `calibration_data_available`).

**Fairness:** a self-loop at idle with `sweep` enabled but never taken falsifies AF. Add **justice** on `sweep` if the scheduler is weakly fair; otherwise the cex lasso is “cron never fires” — a real ops bug.

### 4. Skill router loop

**Property (LTL fairness):** `GF (skill_queried → F skill_returned)`

Equivalently on fair paths: infinitely often, a query is eventually answered.

**Needs strong fairness (compassion):** `skill_returned` may be enabled only i.o. (when a query is outstanding), not almost-always. Weak fairness does not force it. Beta-posterior updates that starve a skill violate compassion — the lasso shows the starved skill id.

### 5. Exit-code state machine

**Property (CTL):** `AG (exit=0 ∨ exit=intentional)`

**Method:** enumerate S (run, ok, fail, intentional, crash, …); label atoms `exit0`, `intentional`; run the Ch 4 labelling algorithm. EF(¬exit0 ∧ ¬intentional) must be empty from S₀.

**Verify by hand** when |S| is tiny: list states, check R, check no path to crash/fail unless labelled intentional.

---

## Operator pocket card

```
EX φ      some successor φ
AX φ      all successors φ
EF φ      exists path to φ
AF φ      all paths eventually φ
EG φ      exists path always φ
AG φ      all paths always φ
E[φ U ψ]  exists path: φ until ψ
A[φ U ψ]  all paths: φ until ψ

X φ       next (LTL)
F φ       eventually (LTL)
G φ       always (LTL)
φ U ψ     until (LTL)

Justice     FG en → GF take   ≡  GF(¬en ∨ take)
Compassion  GF en → GF take   ≡  FG ¬en ∨ GF take
```

## Fixpoints

```
E[φ U ψ]  = μZ. ψ ∨ (φ ∧ EX Z)
EG φ      = νZ. φ ∧ EX Z
AG φ      = νZ. φ ∧ AX Z
AF φ      = μZ. φ ∨ AX Z
```

## Tool pick

| Tool | Use |
|---|---|
| SMV / NuSMV | symbolic CTL, FAIRNESS, WAL boolean models |
| SPIN | Promela async product, LTL, POR |
| SAT BMC | short safety bugs; then prove with BDD or k* |

## Explosion kit (in order)

1. Cone of influence
2. POR if async + LTL_{-X}
3. BDD order / partitioned R
4. Assume-guarantee split
5. Existential abstraction (ACTL only)
6. Symmetry if identical processes
7. Network invariant if ∀n

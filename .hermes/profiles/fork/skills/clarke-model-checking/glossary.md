# Glossary — Clarke / Grumberg / Peled Model Checking

| Term | Definition |
|---|---|
| **ACTL** | Universal fragment of CTL (AX, AG, AF, AU; negation only on atoms). Preserved by simulation and existential abstraction. |
| **Ample set** | Subset of enabled transitions at s satisfying C0–C3 (Peled). Basis of POR in this book. |
| **Atomic proposition (AP)** | Boolean observable; L(s) ⊆ 2^AP. |
| **Bisimulation** | Two-way matching of transitions and labels. Preserves CTL*. |
| **Büchi automaton** | ω-automaton; run accepting iff Inf ∩ F ≠ ∅. Target of LTL translation. |
| **Compassion** | Strong fairness: GF enabled → GF taken. |
| **Completeness threshold** | Depth k* such that BMC unsat up to k* implies the (safety) property on all infinite runs. |
| **Computation tree** | Unrolling of (S,R) from a state; semantics of CTL. |
| **Counterexample** | Finite path (safety) or lasso (liveness) showing M ⊭ φ. |
| **CTL** | Computation Tree Logic. Path quantifier A/E glued to X/F/G/U. |
| **CTL*** | Superset of CTL and LTL; free mix of state and path formulas. |
| **Enabled** | Transition/action firable in s. |
| **Existential abstraction** | Merge concrete states; extra abstract transitions. Simulation from concrete to abstract. |
| **Fair path** | Path meeting justice/compassion constraints. Fair CTL/LTL quantify over these only. |
| **Fairness constraint** | Set of states/actions that must be visited/taken i.o. on allowed paths. |
| **Greatest fixpoint νZ. τ(Z)** | Used for EG, AG. Iterate from true (or from φ) downward. |
| **Guided simulation** | Replay of a counterexample on the concrete system or log. |
| **Image / pre-image** | Relational product through R forward/backward. BDD bottleneck. |
| **Independence I** | Commuting, non-disabling pair of actions. POR fuel. |
| **Initial states S₀** | Start set of the Kripke structure. |
| **Invisibility** | Action does not change labels of atoms in φ. POR C2. |
| **Justice** | Weak fairness: FG enabled → GF taken, i.e. GF(¬enabled ∨ taken). |
| **Kripke structure** | M=(S,S₀,R,L) with R total. |
| **Labelling algorithm** | Explicit CTL MC; O(|S|×|φ|). |
| **Lasso** | Stem + cycle. Shape of infinite-path witnesses/cex. |
| **Least fixpoint μZ. τ(Z)** | Used for EU, EF. Iterate from empty upward. |
| **Liveness** | “Something good happens”; no finite bad prefix. Typical F / AF / GF. |
| **LTL** | Linear Temporal Logic. Properties of infinite paths; implicit A. |
| **Network invariant** | Abstract process I such that adding a process preserves simulation of I. Parameterized proofs. |
| **OBDD** | Reduced ordered binary decision diagram (Bryant). Canonical boolean representation. |
| **Partial-order reduction** | Explore ample/stubborn/persistent subsets; preserve Mazurkiewicz traces. |
| **Path** | Infinite sequence of R-related states. |
| **Persistent set** | Godefroid POR set: outside actions cannot disable inside actions. |
| **Reachable set** | States from S₀ via R*. Check safety here, not on all S. |
| **Region graph** | Finite quotient of a timed automaton’s dense state space. |
| **Safety** | “Something bad never happens”; finite violating prefix. Typical G ¬bad / AG ¬bad. |
| **Simulation** | One-way matching. Preserves ACTL from simulated to simulator (implementation ≼ spec). |
| **SMV** | Symbolic Model Verifier (McMillan). BDD CTL checker. |
| **SPIN** | Explicit LTL model checker (Holzmann). Promela, nested DFS, POR. |
| **State explosion** | |S| exponential in components/variables. |
| **Streett / generalized Büchi** | Acceptance for strong fairness / multiple fairness sets. |
| **Stubborn set** | Valmari POR construction. |
| **Stutter-invariant** | Property insensitive to finite repetition of states. LTL without X. |
| **Symbolic MC** | Sets as BDDs (or SAT); fixpoints without enumerating states. |
| **Totality of R** | ∀s ∃s'. R(s,s'). Required for X/F/G. |
| **Until U** | φ U ψ: φ holds until (and ψ occurs). Strong until. |
| **Weak fairness** | Synonym of justice. |
| **Witness** | Path showing a formula *holds* (e.g. EG p lasso). |

# Chapter 6: Symbolic Model Checking

## Core Idea
Replace explicit label sets by BDDs. The CTL fixpoints of Ch 4 run as boolean iterations: image/pre-image until the set BDD stabilizes. SMV is the reference implementation.

## Frameworks Introduced
- **Pre-image / image**:
  Pre(Z)(s) = ∃s'. R(s,s') ∧ Z(s')
  Img(Z)(s') = ∃s. Z(s) ∧ R(s,s')
  - When to use: CTL CheckSet and reachable-set computation.
- **CheckSet (symbolic)**:
  - EX ψ = Pre(ψ)
  - EU: Z₀ = ψ; Z_{i+1} = ψ ∨ (φ ∧ Pre(Z_i)) until Z_{i+1}=Z_i  (least fp)
  - EG: Z₀ = φ; Z_{i+1} = φ ∧ Pre(Z_i) until stable  (greatest fp)
  - When to use: hardware, synchronous software, SMV modules.
- **Reachability**: Rch₀ = S₀; Rch_{i+1} = Rch_i ∨ Img(Rch_i). AG p on reachable states: Rch → p (BDD implication).
- **Fair symbolic EG**: iterate over fairness constraints; see Emerson-Lei / McMillan: Z stays in φ and can reach each fairness set infinitely often (nested fixpoints).

## Key Concepts
- **Fixpoint iteration**: monotonic operators on a finite lattice 2^S ⇒ termination.
- **Early quantification**: in ∃s. ∧ R_i, quantify variables as soon as they disappear.
- **SMV language**: VAR / ASSIGN next() / SPEC AG … / FAIRNESS.
- **Counterexamples symbolically**: pick a concrete assignment from the BDD of bad states; walk Pre to S₀.

## Mental Models
- Same mathematics as Ch 4; different data structure.
- If the reachable BDD stays small, you have verified 10^20 states; if it explodes, switch to BMC/POR/abstraction — do not add RAM.

## Anti-patterns
- Iterating image without a visited-set (non-fixpoint “unbounded unwind”).
- Mixing asynchronous interleaving into one SMV module without an explicit scheduler variable (you accidentally made it synchronous).
- Checking AG on *all* S rather than reachable S — spurious failures in unreachable junk.

## Worked Example
SQLite WAL-mode lock as SMV-style next-state: `next(writer_active) := case !writer_active & req: TRUE; writer_active & done: FALSE; TRUE: writer_active; esac`. SPEC `AG (writer_active -> AX !concurrent_writer)`. Symbolic AG is ¬EF(writer_active ∧ EX concurrent_writer) on the reachable BDD.

## Key Takeaways
1. Image + fixpoint = symbolic CTL.
2. Restrict to reachable states.
3. SMV is the tool for this chapter.
4. Fairness = extra nested fixpoints, not a different logic.

## Connects To
- **Ch 5**: OBDD operations.
- **Ch 16**: SAT BMC when BDDs fail.
- **Cheatsheet**: cron AG on WAL-mode model.

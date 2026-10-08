# Chapter 2: Modeling Systems

## Core Idea
Concurrent systems are Kripke structures M = (S, S₀, R, L). Composition is interleaving (asynchronous) or lock-step (synchronous); atomic propositions are the only interface to temporal logic.

## Frameworks Introduced
- **Kripke structure**: S finite; S₀ ⊆ S; R ⊆ S×S **total** (∀s ∃s'. R(s,s')); L : S → 2^AP.
  - When to use: any CTL/LTL check.
  - How: enumerate or generate S from variable valuations; define R by next-state predicates; label with booleans you will mention in φ.
- **Interleaving product**: for local machines M_i, a global step is one M_i stepping while others stutter (asynchronous) or all step (synchronous hardware).
  - When to use: cron jobs, protocols, WAL writer vs readers.
  - How: S = ∏ S_i; R lifts local R_i. Shared variables are part of the global state.
- **I/O automata style atomicity**: an action is atomic iff no intermediate valuation is a state in S.
  - When to use: file writes, SQLite transactions.
  - How: put only committed/visible valuations in S so partial writes are not states — or add an explicit `partial` proposition if you need to forbid them.

## Key Concepts
- **State**: a valuation of the system's variables (program counters + data).
- **Initial states S₀**: legal start configurations (cold start, empty WAL, no writer).
- **Path**: infinite sequence s₀ s₁ … with R(s_i, s_{i+1}). Totality of R guarantees infinitude.
- **Deadlock vs terminal**: if a state has no real successor, add a self-loop; otherwise X is undefined.
- **Atomic proposition**: boolean observable; keep AP small — extra labels explode CTL formulas needlessly.

## Mental Models
- Use **shared-variable product** when processes communicate by memory (SQLite WAL).
- Use **message-passing / handshake** when they communicate by events (cron mailbox).
- If two actions commute and you do not care about order, they are candidates for later POR independence (Ch 8).

## Anti-patterns
- **Non-total R**: model checkers assume infinite paths; terminals without self-loops break G/F.
- **Leaking internals into AP**: labelling every register makes symmetry and POR fail C2 (invisibility).
- **Non-atomic writes as several R-steps without a `partial` label**: you cannot even *state* G ¬partial_write_visible.

## Worked Example
WAL writer (Hermes): local states {idle, writing, committed}. Readers {reading, idle}. Global AP: `writer_active`, `concurrent_writer`, `partial_write_visible`. R forbids two writers entering `writing` if the mutex/WAL lock is modelled. Totality: idle self-loops when no job is due.

## Key Takeaways
1. Write (S, S₀, R, L) explicitly before φ.
2. Force R total.
3. Atomicity is a modelling choice that *defines* what safety can say.
4. Product construction is where explosion starts.

## Connects To
- **Ch 3**: AP become atoms of CTL/LTL.
- **Ch 8**: independence lives on the same R.
- **Cheatsheet**: atomic-write I/O automaton.

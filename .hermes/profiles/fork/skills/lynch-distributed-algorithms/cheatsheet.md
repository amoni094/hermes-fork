# Cheatsheet — Lynch Distributed Algorithms

## I/O automaton

```
A = (sig, states, start, trans, part)
sig = (in, out, int)          disjoint
input-enabled: every input enabled in every state
part: countable classes of local (out∪int) actions  = fairness units
```

```
execution:  s0 π1 s1 π2 …     (s0 start, each triple a step)
schedule:   π1 π2 …           all actions
trace:      external π only
fair:       ∀ class C: infinitely often (step in C ∨ C disabled)
```

Composition: match out to in; internals private; unique output owner.

**Safety** = prefix-closed (invariants, simulations).
**Liveness** = eventuality under fairness or boundmap.

Forward simulation *f*: starts related; each impl step matched by spec fragment with same external projection ⇒ traces(impl) ⊆ traces(spec).

## Timing

| Sync | Async | Partial / MMT |
|---|---|---|
| rounds | arbitrary interleaving | boundmap `[ℓ,u]` per class |
| *f*+1 crash consensus | FLP impossible | timeouts sound if *u*<∞ |

Lamport clocks: `clock = max(local,stamp)+1`; send < receive; reordering theorem.

## Failures

| | Crash-stop | Omission | Byzantine |
|---|---|---|---|
| Sync consensus | *n*>*f*, *f*+1 rounds | **impossible** (two generals) | *n*>3*f*, *f*+1 rounds |
| Async consensus | FLP: no det. 1-resilient | — | even harder |

## Consensus spec

```
Agreement:  at most one decided value
Validity:   all inputs v ⇒ decide v     (commit: any 0 ⇒ 0)
Termination: fair / 1-fair / timed
```

**FLP:** bivalent start; bivalence preservable; no 1-RCP.

**Escapes:** sync, timeouts, coins (Ben-Or, *n*≥7*f*+1 in notes), RMW/CAS, weak termination (2PC, Paxos).

**Paxos:** ballot `(t,i)` → promise (no smaller YES) → pick value of highest prior YES from a majority → majority YES → decide. Agreement by majority intersection. Livelock if duelling originators.

**Ben-Or round 2:** `m≥n−2f` decide; `m≥n−4f` adopt; else coin.

## Mutex

```
R → T → C → E → R
ME: |C|≤1                         safety
deadlock-free: someone enters     liveness
lockout-free: each trying enters  stronger
```

Peterson 2-process: `level[i]=1; turn=i; wait level[j]=0 ∨ turn≠i`.
Bakery: tickets; lockout-free; unbounded unless CTS.
R/W mutex needs ≥*n* bits. RMW (TAS) trivial. Network: Ricart–Agrawala + logical time.

## Registers (single-writer)

```
safe    overlapping read → garbage
regular overlapping read → old or new   (new-then-old OK)
atomic  linearizable                    (new-then-old forbidden)
```

Safe binary SR/SW → (wait-free ladder) → MWMR *k*-ary atomic.

**Atomicity:** serialization points inside intervals; incomplete ops included or dropped consistently.

**Wait-free:** fairness to *i* ⇒ *i* completes. Composes.

R/W cannot implement consensus (1 crash). RMW can.

## Commit

2PC: weak termination; coordinator crash **blocks**.
3PC: extra precommit; strong termination in crash-no-partition model.
Paxos: majority; survives coordinator crash.

## MST / election / sync

- LCR: forward larger UID; Θ(*n*²) worst, Θ(*n* log *n*) average, *n* rounds.
- HS: *O(n log n)* messages.
- GHS: async MST, *O(|E|+n log n)* messages.
- Synchronizers α (acks, *O(|E|)/round), β (tree, *O(n)/round).

## Self-stabilization

From **any** state, eventually legal and stays legal. Local checking ∧_e P_e + local correction transformer. Crash-recovery without durable state ≠ start-state reasoning.

## Timed automata

Timed exec = untimed exec + timestamps obeying *bℓ(C)*, *bu(C)*. ABP: 1-bit seq if FIFO. After node crash: durable seq or incarnation handshake.

## Hermes four mappings

1. Atomic write = serial ADT + safety *I* “no torn visible”; rename = serialization point.
2. Cron WAL = MW register; mutex or CAS; not regular.
3. Gate-audit returns = liveness under fairness/boundmap, not an invariant.
4. Skill router = leader election; Paxos/CAS if crash, LCR if not.
---

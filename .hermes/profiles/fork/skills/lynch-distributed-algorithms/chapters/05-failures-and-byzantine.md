# Failures: omission, crash-stop, Byzantine (Lectures 4–6)

## Coordinated attack (link / omission failures)

Gray’s generals / two-generals problem. Synchronous processes, binary inputs, **any messages may be lost**. After a fixed *r* rounds, decide.

- **Agreement:** all decide the same value.
- **Validity:** all-0 inputs ⇒ decide 0; all-1 **and all messages delivered** ⇒ decide 1.

Validity is weak: a single loss allows any decision. Still **impossible** on any graph with ≥2 nodes.

**Theorem.** No algorithm solves coordinated attack on two nodes joined by an edge.

**Proof idea.** Let α₁ be the all-1, all-delivered execution (must decide 1). Drop the last message: the recipient cannot distinguish this from α₁, so still decides 1; the sender of that message *can* distinguish, but agreement forces the other to match. Iterate, dropping one message at a time, until the no-messages execution, which is indistinguishable (for a process that heard nothing) from an all-0 run that must decide 0. Contradiction.

**Indistinguishability:** α ~_i β iff *i* has the same initial state and the same per-round receipts. Then *i*’s local behavior is identical.

Randomized coordinated attack can succeed with probability arbitrarily close to 1, but not certainty (Lecture 4.1.2).

## Crash-stop (stopping) failures

A process halts. In the round it stops it may send only a subset of its messages. Links are reliable; graph complete. At most *f* stops.

Consensus:

- **Agreement:** all decided values equal (faulty processes that decide must agree too, in the strong form).
- **Validity:** all inputs *v* ⇒ decide *v*.
- **Termination:** every nonfaulty process decides.

**Flooding / EIG tree algorithm.** Each process maintains a tree of depth *f*+1. Node labeled *i₁…i_k* holds “i_k told me that i_{k−1} told … that i₁’s input is *v*.” Fill level *k* in round *k*. After *f*+1 rounds, let *W* be the set of values appearing in the tree; if |W|=1 decide that value, else a default.

*f*+1 rounds are necessary (a chain of *f* crashes can hide a value until the last round). *n > f* is enough (unlike Byzantine).

## Byzantine failures

Faulty processes send arbitrary messages, including different lies to different neighbors, and may have arbitrary state.

**Oral-message Byzantine agreement (Lamport–Shostak–Pease).**

- **Agreement:** all **nonfaulty** processes decide the same.
- **Validity:** if all nonfaulty inputs are *v*, they decide *v*.
- **Termination:** nonfaulty processes decide.

**Upper bound:** solvable for *n ≥ 3f+1* in *f*+1 rounds (exponential-size OM/*EIG* recursive protocol). Turpin–Coan and later work reduce communication; still *f*+1 rounds in deterministic sync.

**Lower bound (notes Lemma 1 + reduction).**

- Three processes cannot tolerate one Byzantine fault.
- Proof: two copies of each of *p,q,r* arranged in a hexagon. Each process’s local view is identical to a 3-process run with one traitor. Validity/agreement on overlapping triples force contradictory decisions at the wrap-around.

**Reduction:** if *n ≤ 3f*, partition into three groups of size ≤*f* and simulate the 3-process impossibility.

**General graphs:** need vertex-connectivity > 2*f* (Byzantine nodes can cut the network).

**Weak Byzantine agreement:** validity only required when *all n* inputs (including faulty) equal *v*. Still requires *n > 3f* in the standard oral model.

Do not confuse with crash-stop: *n > f* and *f*+1 rounds suffice for crash; Byzantine needs *n > 3f*.

## Hermes

- A crashed subagent is crash-stop: ignore it; remaining majority may still decide.
- A prompt-injected or lying tool is closer to Byzantine: do not believe a single source; require *n > 3f* independent witnesses or move the trust boundary (signed / authenticated channels — the “signed-message” model weakens the *n>3f* bound).
- Coordinated-attack impossibility: do not design a two-node commit that must succeed despite arbitrary packet loss.
---

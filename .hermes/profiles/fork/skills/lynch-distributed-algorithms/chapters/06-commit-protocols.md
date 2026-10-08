# Commit protocols (Lecture 7)

Commit (Dwork–Skeen) is consensus with a biased validity condition, matching distributed databases: abort is contagious.

Complete graph, reliable messages, stopping faults (any number, depending on the variant).

- **Agreement:** at most one decision value (0 = abort, 1 = commit).
- **Validity:**
  1. If any process starts with 0, then 0 is the only possible decision.
  2. If all start with 1 and there are no failures, decide 1.
- **Termination:**
  - **Weak:** required only in failure-free runs.
  - **Strong:** all nonfaulty processes decide.

Vs ordinary crash consensus: validity is asymmetric (a single 0 forces abort); weak termination is allowed.

## Two-phase commit (2PC)

Distinguished coordinator *p₁*.

1. All processes send their vote to *p₁*.
2. *p₁* decides 0 if any vote is 0 or a vote is missing (in some presentations); broadcasts the decision.

Notes presentation: *p₁* decides whether anyone had initial 0, broadcasts.

**Satisfies** agreement, validity, **weak** termination. **Fails strong termination:** if *p₁* crashes, others may be blocked. They cannot safely abort (maybe *p₁* already decided commit and told a cohort that then also crashed) and cannot safely commit (maybe *p₁* never voted 1).

Two rounds. Does not contradict the *f*+1 round lower bound for **strong** termination.

## Three-phase commit (3PC)

Key idea: the coordinator must **not** decide commit until the others know it *intends* to. Extra phase so that after a coordinator crash, survivors can elect a new coordinator and decide from a state that is not ambiguous between “already committed” and “still abortable.”

Notes sketch (four rounds in their counting):

1. All send values to *p₁*. If *p₁* sees a 0 or misses a message, it can abort (and abort is safe to broadcast).
2. If all 1s, *p₁* sends “prepare-commit” / precommit.
3. Cohorts ack.
4. *p₁* decides commit and broadcasts.

After precommit is majority-known, a recovery coordinator can complete commit; before that, abort is still legal. **Strong termination** in the crash model of the notes (not in the presence of partitions — 3PC is not partition-tolerant; Paxos/Raft are the modern “commit under majority” answer).

## Message lower bounds

Even weak commit has a nontrivial message lower bound (notes §7.2.3): information about every 0 vote must reach the decision, and a commit decision must collect all votes.

## Hermes

- Cron job that “commits” a WAL + side effect: 2PC-shaped. If the coordinator (the cron process) dies between side effect and log fsync, recovery is the 2PC blocking case. Prefer a single atomic rename/fsync (one object) or a Paxos-like majority if multiple writers.
- Gate-audit that waits for a single coordinator is weakly terminating. Strong termination needs a timeout + abort path (timed model) or a backup coordinator.
---

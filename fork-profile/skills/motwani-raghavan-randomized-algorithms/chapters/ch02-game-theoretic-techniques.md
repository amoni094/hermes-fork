# Ch 2 — Game-Theoretic Techniques

Randomisation as a mixed strategy against an adversary. Yao's minimax principle converts distributional lower bounds into randomised lower bounds.

## Game-tree evaluation (Ch 2.1)

Boolean tree: internal nodes are alternating AND/OR; leaves are 0/1. Evaluate the root.

Deterministic algorithms can be forced to read all leaves on some inputs. A randomised algorithm that inspects children in random order has expected leaf-reads `n^{α}` with `α = log₂((1+√33)/4) ≈ 0.793` on balanced NAND trees `T_{2,k}` (depth `2k`, `n = 2^{2k}` leaves) — **Theorem 2.1**.

This is the canonical **foiling an adversary**: the adversary cannot arrange the worst child-order against a random permutation.

## Yao's minimax principle (Ch 2.2)

View a randomised algorithm as a distribution `p` over deterministic algorithms `A`, and an input distribution `q` over instances `x`.

**Minimax.** For a cost `C(A,x)` (runtime, error, …),

`max_q min_A E_{x∼q}[C(A,x)] = min_p max_x E_{A∼p}[C(A,x)]`

(finite zero-sum game; von Neumann).

**Use.** To lower-bound every randomised algorithm's expected cost on worst-case inputs, exhibit **one** input distribution on which **every** deterministic algorithm is expensive. The randomised lower bound equals that distributional lower bound.

Do not confuse: a lower bound against a *specific* input distribution is not automatically a worst-case randomised lower bound unless you invoke minimax (or argue for every distribution).

## Randomness and non-uniformity (Ch 2.3)

A probabilistic existence argument can prove that for every `n` there *exists* a deterministic algorithm (a string of advice / a circuit) with the desired bound — **non-uniform**. Uniform randomised algorithms need an efficient sampler of that advice. This distinction reappears in expander constructions (Ch 5) and routing with few random bits (Thm 5.10).

## Hermes

When arguing a randomised routing / retry policy is necessary, use minimax: pick a hard input *distribution*, show every deterministic policy fails in expectation, conclude no randomised policy with that resource bound exists.

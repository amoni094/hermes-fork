# Chapter 6: Game-Theoretic Foundations

## Core Idea
Competitive analysis is a **two-person zero-sum game** (online player vs adversary). Randomization in games is not a single notion: mixed, behavioral, and general strategies differ once memory / information sets are bounded.

## Key Concepts
- **Extensive form:** game tree; nodes are information sets. Online ALG = strategy that, at each request, picks an answer given its history.
- **Strategic (normal) form:** a complete plan for every information set; payoff matrix (ALG cost, adversary cost).
- **Mixed strategy:** probability distribution over deterministic (pure) strategies. Chosen once, then play.
- **Behavioral strategy:** independent randomization at each information set (coins tossed along the path).
- **General strategy:** arbitrary correlation of randomizations across information sets.
- **Perfect recall:** a player never forgets what they knew or did. Kuhn: mixed ≡ behavioral under perfect recall.
- **Linear games:** payoffs / structure where mixed and behavioral coincide even more strongly (book §6.3).
- **Memory-bounded online algorithms.** Forgetting past requests breaks perfect recall; mixed vs behavioral vs general can separate (open questions 6.1–6.3 for paging and list accessing).

## Frameworks and Methods
- **ALG as a strategy, adversary as the opponent.** The value of the game is the competitive ratio (Ch. 8 makes the infinite-game caveat precise).
- **PERM₂ / MIXPERM.** Memory-limited paging: PERM₂ is k-competitive; mixed memoryless paging (Raghavan–Snir) needs the extensive-form language.
- **Do not collapse “randomized online algorithm” to “behavioral.”** Ch. 7 defines randomized ALG as a **mixture over deterministic online algorithms** (mixed strategy). That is the default in later chapters.

## Key Results and Theorems

**Kuhn’s theorem.** In games of perfect recall, mixed and behavioral strategies are equivalent (same induced distribution on plays).

**Equivalence for linear games / perfect recall (§6.3).** For the request–answer games of later chapters with unbounded memory, mixed ≡ behavioral.

**Application to paging (§6.4).** Memoryless randomized paging (eviction probabilities depend only on the current cache) is a behavioral strategy with tiny information sets; its power relative to general randomized paging is *not* settled by Kuhn because recall is bounded.

**Theorem 6.5 (countable extension).** Finite-game equivalence extends when game length and information-set branching are at most countable.

## Key Equations
- Mixed: `p ∈ Δ(Pure)`, play `D ~ p`, cost `E_D[D(σ)]`.
- Behavioral: at information set `I`, `π(· | I) ∈ Δ(Actions)`.
- Value (preview Ch. 8): `max_q min_p E[cost] = min_p max_q E[cost]` when minimax applies.

## Worked Example
Paging with memory 0: eviction distribution as a function of the current k-set only. A mixed strategy could pick a permutation of pages once (PERM) and run deterministic; a behavioral strategy re-randomizes every miss. These are not obviously equivalent.

## Hermes application
Hermes routing that (a) samples a skill once per session (mixed) vs (b) re-samples every turn (behavioral) are different once the router is **memory-bounded**. If the router keeps the full transcript, Kuhn applies and the distinction is bookkeeping. If it keeps only last-k skills, do not quote mixed-strategy ratios for a per-turn softmax.

## Anti-patterns
- **Invoking Kuhn for a bounded-memory router.** Perfect recall fails.
- **Calling any coin-flip algorithm a mixed strategy.** If coins are tossed each turn from a state-dependent distribution, it is behavioral.
- **Assuming a unique game value** before checking that the game is finite or otherwise minimax-legal (Ch. 8.2).

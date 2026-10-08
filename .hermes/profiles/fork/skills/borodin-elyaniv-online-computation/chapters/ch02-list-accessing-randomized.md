# Chapter 2: Randomized Algorithms — The List Accessing Problem

## Core Idea
Randomization against an **oblivious** adversary can beat the deterministic ratio 2. Coins are private; OBL must fix `σ` before seeing them. Expectation is over ALG only.

## Key Concepts
- **Randomized competitive ratio vs OBL:** `E[ALG(σ)] ≤ c · OPT(σ) + α` for all `σ`.
- **Barely random:** a constant number of random bits (or a random seed chosen once), then deterministic. RMTF is barely random; fully random algorithms may toss coins every step.
- **BIT:** each item has a random bit, flipped on access; move-to-front only when the bit becomes 0 (or 1 — symmetric). 1.75-competitive.
- **RMTF:** with probability `p` move to front, else stay. Not better than MTF in the worst case for naive `p`; used to separate barely-random from fully random.
- **TIMESTAMP / COMB:** COMB mixes BIT with a timestamp rule; **8/5-competitive** (Albers), the landmark randomized list-update ratio in this book’s lineage.
- **List factoring + phase partitioning** (revisited): pairwise 2-item sequences determine the n-item ratio for a class of algorithms (including MTF, BIT, COMB).

## Frameworks and Methods
- **Distribution over deterministic algorithms.** A mixed strategy is a probability over DET algorithms (Ch. 6–7). BIT is equivalent to a simple mixed strategy over two MTF-like rules.
- **Pairwise analysis.** For two items `{x,y}`, compute E[cost] vs OPT on every sequence; lift via factoring.
- **Do not claim the ratio against ADON/ADOFF** without a separate proof. BIT/COMB guarantees in this chapter are vs **OBL**.

## Key Results and Theorems

**Theorem (BIT).** BIT is **7/4-competitive** vs OBL.

**Theorem (COMB).** COMB is **8/5-competitive** vs OBL.

**Barely vs fully random.** A barely-random algorithm cannot match the best fully-random list-update ratios; extra coins per request help.

**Randomized lower bound.** No randomized ALG is better than **1.5-competitive** vs OBL (Yao: a hard distribution on sequences; Ch. 8). Deterministic 2 is therefore not an artifact of derandomization failure — the models differ.

## Key Equations
- `E[ALG(σ)] = ∑_D Pr[D] D(σ)` when ALG is a mixture over deterministic `D`.
- Two-item OPT cost on a run of accesses is linear in run length; BIT’s expected move-to-front rate is 1/2.

## Worked Example
Two items `x,y`, start `(x,y)`. Oblivious sequence `y,y,x,x`. MTF pays 2+1+2+1 = 6; OPT can transpose once and pay less. BIT’s random bits make the first `y` MTF only with probability 1/2, cutting expected inversions relative to always-MTF.

## Hermes application
If a skill/tool LRU list is randomized (coin-flip MTF), treat it as **BIT-style vs OBL**: good when the request sequence (user tasks) does not adapt to the coins. If the user/adversary reacts to what you just cached, the guarantee is ADON, not 7/4. Cron job MTF-cache: deterministic MTF (Ch. 1) is the right default.

## Anti-patterns
- **Reporting 8/5 against an adaptive user.** COMB needs oblivious `σ`.
- **Confusing barely-random with “essentially deterministic.”** Barely-random still needs OBL; against ADOFF it collapses toward DET (Ch. 7).
- **Using FC with random tie-break** and claiming BIT’s ratio.

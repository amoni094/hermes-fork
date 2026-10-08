# Patterns — Online Computation applied to Hermes fork

## P1. FTRL routing as expert learning (Ch 14, 13)

PROBLEM: routing-weight-updater.py uses EMA weights without a provable regret bound.

THEORY: Exponential weights on K providers with per-round success/fail loss achieves
  R_T ≤ √(T · ln K / 2)
Using EMA with decay γ achieves "discounted regret" (sliding window of ~1/(1−γ) steps):
  R_{eff} ≤ √(W · ln K / 2)  where W = effective window = 1/(1−EMA_DECAY) = 10 at 0.9

HERMES WIRING:
- Current: EMA_DECAY=0.9, MIN_SAMPLES=5, WEIGHT bounds [0.1,2.0].
- regret tracking added in O1 (routing-weight-updater.py L177-228).
- Alarm at >5% relative regret (regret_this_run > 0.05 * total_n).
- Calibration: if total_n < 50, regret is noise; suppress alarms until N ≥ 50.

ACTION: Check routing-regret-log.jsonl weekly. Persistent positive regret → provider weights miscalibrated; reset weights or investigate data quality of success signals.


## P2. Skill router as k-server (Ch 10, 11)

PROBLEM: Skill routing loads k skills into context (context window = cache of size k). Which k to load for a given query?

THEORY: k-server on metric (skills as servers, query as request point, dist = cosine distance).
- LRU policy = conservative k-server → ratio k (worst case).
- WFA on semantic metric → ratio 2k−1 but computationally expensive.
- HARMONIC randomized → ratio H_k ≈ ln k; much better for large k.

HERMES WIRING:
- Current: top-k TF-IDF cosine retrieval (closest to LRU/greedy).
- Improvement: randomized loading with probability ∝ softmax(−dist/T) where T is temperature.
  At T→0: greedy (deterministic nearest neighbor = LRU-like, ratio k).
  At T=1/H_k: approaches HARMONIC distribution; expected ratio H_k.
- Practical: set T so that top-1 has probability 0.6, remainder distributed over next 4.

IMPLEMENTATION SKETCH:
  scores = cosine(query, each_skill)  # TF-IDF from index
  probs = softmax(scores / T)
  selected = sample_without_replacement(skills, k, probs)


## P3. Context / tool cache as paging (Ch 3, 4, 5)

PROBLEM: LLM context has a page limit. Which tools/skills to evict when context fills?

THEORY: k = context page slots. LRU, FIFO, CLOCK all achieve ratio k deterministically.
MARK achieves 2H_k randomized vs OBL (optimal).

HERMES WIRING:
- Lambda-tuner / context compression handles eviction; applies summarization rather than drop.
- For tool-set selection: implement MARK over tool descriptions.
  Mark each tool on access; on fault (new tool needed), evict a random unmarked tool.
  Reset all marks when all context-resident tools are marked.
- Ratio guarantee: 2H_k ≈ 2 ln k. For k=20 tools: ratio ≈ 6 vs offline optimal.


## P4. Cron list update as MTF cache (Ch 1, 2)

PROBLEM: Which cron scripts to keep "hot" (short queue, high priority)?

THEORY: List update with MTF. If script i is accessed with frequency f_i (stationary), expected cost of MTF = 2 · (optimal static ordering) − n. For non-stationary access: COMB achieves 8/5 vs OBL.

HERMES WIRING:
- skill-beta-feedback.py records skill invocations → use as "access list" for MTF ordering.
- Sort cron jobs by recent invocation frequency (from executions.db); assign higher priority to frequent ones.
- Implement as priority field update in jobs.json: every 24h, re-rank jobs by 7-day invocation count.


## P5. Memory TTL as ski rental (Ch 15)

PROBLEM: recall-miss-ttl-adjuster decides how long to keep memory facts (TTL).

THEORY: Ski rental: pay 1/day to store OR pay B to store permanently.
- Optimal det.: store until cost = B−1, then make permanent.
- With stochastic access: threshold at E[lifetime] · storage_cost.

HERMES WIRING:
- MRAS gain_cap = 0.10: conservative, analogous to paying rent for ≤10% rate per step.
- To implement full ski-rental policy: track cost_so_far for each fact; when cost_so_far ≥ B−1, mark as permanent (never decay).
- B = ratio of permanent storage cost to per-period storage cost (estimate from lifecycle.db eviction history).


## P6. Primal-dual certificates for new scripts (Ch 15)

PRINCIPLE: Any new online Hermes script that makes irreversible decisions (evict, reject, assign, promote) should have a primal-dual certificate establishing its competitive ratio before merge.

PROCEDURE:
1. Write LP relaxation of the offline optimum.
2. Pair each ALG decision with a dual variable increment Δd.
3. Verify dual feasibility (constraints satisfied after each Δd).
4. If ALG cost Δp ≤ c · Δd at each step → ALG is c-competitive (primal-dual theorem).
5. Document ratio c and the hard-instance lower bound in the script's docstring.

EXAMPLES ALREADY DONE:
- LRU paging: c=k (conservative algorithms theorem, Ch. 3).
- MTF list update: c=2 (Sleator-Tarjan potential argument, Ch. 1).
- FTRL: regret O(√T log K) → competitive ratio 1 + O(√T log K / OPT).

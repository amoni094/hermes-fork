# Glossary — Borodin & El-Yaniv

**Adaptive-offline adversary (ADOFF).** Adversary observes ALG's past answers when choosing future requests, then is served by an optimal offline algorithm on the realized sequence. Strongest adversary; randomization gives no benefit vs ADOFF.

**Adaptive-online adversary (ADON).** Observes ALG's past answers; must serve itself online (not offline). Middle power. Randomization helps against ADON but less than vs OBL.

**Competitive ratio R(ALG).** inf{c : ∃α. ∀σ. ALG(σ) ≤ c·OPT(σ)+α}. Multiplicative analogue of approximation ratio for offline.

**Conservative algorithm.** Paging: only evicts on a fault; never evicts a page before faulting. LRU, FIFO, CLOCK are all conservative. All k-competitive (Ch. 3).

**Double Coverage (DC).** k-server algorithm on a line: serve request by moving the nearest server; if request is between two servers, move both toward it simultaneously. Achieves ratio k.

**Experts problem.** N experts give binary advice each round; learner suffers loss based on chosen expert. Exponential Weights: regret O(√T log N). Continuous analogue = universal portfolio.

**FWF (Flush When Full).** Paging: on fault, evict all cached pages. Ratio k; simple but wasteful.

**H_k.** k-th harmonic number = 1 + 1/2 + … + 1/k ≈ ln k + 0.577. Lower bound on randomized paging vs OBL; also randomized k-server on uniform metric.

**HARMONIC algorithm.** Randomized k-server: move server i with probability ∝ 1/d(s_i, request). Optimal on uniform metric (ratio H_k); ratio O(k^2) in general.

**Lazy algorithm.** Only makes "necessary" moves; never moves a server unless it must. Lazy versions achieve same competitive ratio as non-lazy variants.

**LFD (Longest Forward Distance).** Optimal offline paging: always evict the page whose next request is farthest in the future (Belady's algorithm). Ratio 1 (offline OPT).

**Loose vs strict.** Loose: ALG ≤ c·OPT + α. Strict (strongly c-competitive): α = 0 for all σ.

**MARK algorithm.** Randomized paging: mark pages on access; on fault, evict a uniformly random unmarked page; reset marks when all cached pages marked. Ratio 2H_k vs OBL (optimal up to constant).

**Metrical task system (MTS).** General framework: N states, distance function d, task = cost vector over states. ALG must transition states. Traversal achieves 8(N−1); WFA achieves 2N−1 (optimal).

**MTF (Move To Front).** List update: on access of element x, move x to front. Ratio 2 vs any DET offline (Sleator–Tarjan). Optimal deterministic.

**Oblivious adversary (OBL).** Fixes entire request sequence before seeing any ALG coins. Weakest adversary; randomization most beneficial.

**Primal-dual online.** Maintain primal solution (ALG cost) and dual (OPT lower bound) simultaneously; prove dual stays feasible to establish competitive ratio.

**Regret.** Additive excess over best expert/strategy in hindsight: R_T = Σ_t loss_t(ALG) − min_i Σ_t loss_t(i). FTRL achieves R_T = O(√T).

**Ski rental.** Pay 1/day to rent OR pay B once to buy. Optimal det.: rent B−1 days then buy (ratio 2−1/B). Optimal rand.: ratio e/(e−1) vs OBL.

**TRANS.** List update: paid transpositions (swap adjacent elements for cost 1). Not competitive in standard cost model; 0 is best possible ratio.

**WFA (Work Function Algorithm).** Defines work function w_t(x) = min cost to serve σ_1..σ_t ending with server at x. Serve request r by minimizing w_{t-1}(x) + d(x,r) − w_{t-1}(x). Optimal known ratio for MTS (2N−1) and k-server (2k−1).

**Yao's minimax principle.** For randomized ALG vs OBL: R_OBL(ALG) = max_{dist. over σ} min_{DET ALG} E[ALG]/OPT. Lower bound: exhibit a hard distribution; any DET ALG performs poorly on it.

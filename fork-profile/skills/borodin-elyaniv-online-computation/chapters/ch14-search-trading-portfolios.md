# Ch 14 — Search, Trading, and Universal Portfolio

## One-way trading (search problem)

**Problem.** Exchange 1 unit of currency at some exchange rate r_t arriving online. Must trade exactly once (or a fraction). Rates in [m, M]. Goal: maximize received amount.

**Threat-based algorithm (El-Yaniv et al. 1992).**
- Parameter φ = √(M/m) (geometric mean of range).
- Trade when rate ≥ φ (first crossing of threshold).
- Ratio: √(M/m). Optimal among deterministic one-way traders.

**Randomized one-way trading.**
- Sample threshold T uniformly from [log m, log M]; trade when rate ≥ e^T.
- Ratio: (ln(M/m) + 1) / ln(M/m) → 1 + 1/ln(M/m) as M/m → ∞.
- Beats deterministic √(M/m) when M/m is large.

## Two-way trading (buy and sell)

- Buy low, sell high, unknown future prices.
- Optimal deterministic ratio: related to "reservation price" algorithms.
- Connection to ski rental: buying the asset = buying skis; price fluctuation = rental cost.

## Universal portfolio (Cover 1991)

**Problem.** Allocate wealth across k assets at each period t; observe returns, rebalance. Maximize log-wealth vs best constant rebalancing (CRP) in hindsight.

**Cover's algorithm.**
- Maintain a distribution over all portfolio weight vectors b ∈ Δ_k.
- Update: weight each b proportionally to its accumulated wealth.
- Ratio: polynomial in T (not competitive in the multiplicative sense).
- **Regret formulation**: log(W_T^COVER) ≥ log(W_T^CRP) − O(k log T / 2).

**Connection to FTRL.**
- Universal portfolio = FTRL with log-loss on the simplex.
- Gradient descent on −log(wealth) = follow the regularized leader with entropy regularization.
- EXP3 is the discrete analogue (finite experts, not continuous simplex).

## Hermes application
Routing-weight-updater as universal portfolio:
- k assets = k LLM providers (Anthropic/OpenAI/Mistral/Grok).
- Returns = success indicator per call.
- FTRL weight update = Cover's multiplicative update on success probabilities.
- Regret guarantee: cumulative success loss ≤ best-single-provider + O(√T log k).
- Alarm threshold: if running regret > 5% · T, FTRL is underperforming uniform — investigate provider outage or weight decay miscalibration.
- EMA_DECAY=0.9 implements discounted portfolio (non-stationary returns): trade-off between forgetting speed and regret bound; 0.9 is consistent with Raj & Kalyani (2017) discounted Thompson sampling.

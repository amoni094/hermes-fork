# Sector Correlations, PEAD Status, Kelly Sizing, and Momentum Crash Risk (August 2026)

Compiled from research session August 2026. All live data verified (PortfoliosLab Aug 6, 2026).
Academic sources verified via web_extract or DOI. [UNVERIFIED] flags mark unconfirmed claims.

---

## Sector ETF Correlation Data (Live, August 6 2026)

Source: PortfoliosLab.com

### XLK (Tech) vs XHB (Homebuilders)
| Period     | Correlation |
|------------|-------------|
| 1Y         | 0.29 (LOW — diverging recently) |
| 3Y         | 0.40 |
| 5Y         | 0.54 |
| 10Y        | 0.54 |
| All-time (since Feb 2006) | 0.59 |

**Annual returns comparison (2022 rate-hike year):**
- XLK: -27.73%
- XHB: -28.93%
Both fell ~28% simultaneously in the 2022 rate-shock year despite different rate mechanisms.

### ITA (Defense) vs XAR (Defense)
| Period     | Correlation |
|------------|-------------|
| 1Y         | 0.91 |
| 3Y         | 0.90 |
| 5Y         | 0.91 |
| 10Y        | 0.93 |

Near-perfect substitutes. Holding both adds essentially zero diversification.

### Defense vs Tech/Homebuilders (2022 divergence)
- ITA 2022: **+9.96%** (POSITIVE during rate-hike year)
- XAR 2022: -5.02%
- XLK 2022: -27.73%
- XHB 2022: -28.93%

Defense is the genuine uncorrelated leg of a tech/homebuilder portfolio. Government-budget-driven revenue is structurally rate-independent.

---

## Rate Sensitivity Ranking (Most → Least Sensitive)

1. **Homebuilders (XHB/ITB)** — Most sensitive. Direct transmission through mortgage affordability.
   Every +1% in mortgage rates reduces buyer qualification by ~10% (standard affordability math).
   Mechanism: Consumer-credit channel. Symmetric: rate rises hurt, rate cuts help.

2. **Technology (XLK)** — Highly sensitive. Indirect via discount-rate / growth-stock valuation duration.
   Mechanism: Growth PE compression. 40x P/E + 1% real rate rise → ~7% theoretical multiple compression.
   AAPL/NVDA/MSFT (dominant in XLK) trade 25-35x P/E — significant embedded duration.

3. **Defense (ITA/XAR)** — Least sensitive. Revenue from obligated government contracts.
   Mechanism: Budget-driven. Often INVERSE: geopolitical stress that drives rate hikes also
   drives defense spending increases (e.g. Ukraine 2022).
   Source: QuantStrategy.io backtesting article, April 2026

---

## Mortgage Lock-In Effect: Key Academic Evidence

### FHFA Working Paper 24-03 (Batzer, Coste, Doerner, Seiler — August 2024)
URL: https://www.fhfa.gov/research/papers/wp2403
- **For every 1% point market rates exceed origination rate, probability of sale decreases by 18.1%**
- Lock-in caused **57% reduction in home sales** (fixed-rate mortgages) in 2023Q4
- Prevented **1.33 million sales** between 2022Q2 and 2023Q4
- Supply reduction raised home prices by **+5.7%** (outweighed direct rate impact of -3.3%)

### Federal Reserve FEDS Working Paper (2025), "Locked In: Mobility, Market Tightness, and House Prices"
- Lock-in explains **44% of the drop in mortgage borrower mobility** from 2021 to 2022

### Philadelphia Fed WP 26-33 (Graybill, Mangum — July 10 2026)
- Lock-in causes sellers to withdraw
- **BUT**: buyers are MORE sensitive to rates than sellers are to lock-in
- A rate drop → increases sales volumes but does NOT reduce market tightness
- Implication: Lock-in thesis BREAKS when rates normalize; benefits demand more than it suppresses supply

**Thesis-breaking conditions:**
1. Rate normalization (Fed cuts to <4% on 30Y) — releases locked sellers and swamps new-build demand
2. Life-event forced sales (divorce, death, relocation) — baseline inventory exists regardless
3. Builder affordability compression — at elevated rates, rate buydowns required → margin squeeze
4. Overbuilding / absorption risk — cyclical risk independent of structural lock-in

---

## PEAD Status (2025-2026)

### Current academic consensus
**Large-cap PEAD is largely dead** (for non-microcap stocks, since ~2006):
- Martineau, C. (2022, Univ. of Toronto), SSRN 3111607: "Rest in Peace Post-Earnings Announcement Drift"
  PEAD in non-microcap stocks disappeared by 2006. Decimal trading + HFT = faster price discovery.
- Subrahmanyam, A. (2025, UCLA Anderson), SSRN 5930255: "Keeping it Simple..."
  When microcap stocks excluded: PEAD t-stat drops from 2.18 to 1.43 (below significance).
  Microcaps are only 3% of market cap but drive all statistical PEAD tests.

**PEAD survives in microcap / small-cap stocks:**
- Quantpedia (citing Brandt, Kishore, Santa-Clara, Venkatachalam): "main performance contributors are
  small-capitalization stocks" — long-short PEAD strategy 15%/yr (1987-2004), max drawdown -11.2%
- Hirshleifer, Peng, Wang (2025, RFS 38(3)): t-stat ~14 in full sample — but Subrahmanyam argues
  this is a market-cap effect, not robust to proper controls

### Combined earnings + price momentum signal (still works):
Chan, Jagadeesh, Lakonishok (NBER WP 5375, 1996):
- Past return + past earnings surprise each predict large drifts independently
- **Combined strategy (EAR + SUE)**: ~12.5% abnormal annual returns
- EAR (earnings announcement return) strategy alone: ~7.55%/year

### Sector PEAD heterogeneity
No peer-reviewed paper found directly comparing PEAD across defense/tech/homebuilders. Synthesis:
- **Large-cap tech (XLK)**: Minimal PEAD. Dense analyst coverage, maximum HFT, options price in
  expected moves precisely. Earnings repriced day-of for mega-caps (AAPL, NVDA, MSFT).
- **Defense contractors (ITA/XAR)**: Moderate PEAD potential for mid-caps (LDOS, HII, KTOS).
  Lower analyst breadth, less retail attention, multi-year contract surprises less predictable.
- **Homebuilders (XHB/ITB)**: Potentially strongest PEAD. Moderate analyst coverage, earnings
  driven by order rate/backlog/cancellation — partially predictable but still surprises.
  [ALL PER-SECTOR RANKINGS: UNVERIFIED — no direct comparative study found]

Supporting: Duggaraju & Bharadwaj (SSRN 6174938, 2025): "sectoral and firm-size heterogeneity
shape the magnitude and persistence of post-earnings momentum" — confirms differences exist.

---

## Kelly Criterion — Key Quantitative Reference

### Core formulas (verified)
- Binary bet: f* = (pb - q) / b = edge / odds  [Kelly 1956, Bell Labs]
- Continuous equity: f* = (μ - r) / σ² = SR / σ  [Thorp formulation]
- Multi-asset: f* = Σ⁻¹(μ - r·1)  [covariance-adjusted]

### S&P 500 calibration (Atlas Peak Research 2026, using Damodaran 1928-2025)
- S&P 500 excess return ~8.4%, volatility ~19.4%
- Raw Kelly ≈ 8.4% / (19.4%)² ≈ **2.2x leveraged equity** — institutionally impossible
- Historical max drawdown without leverage: **-64.8%** — Kelly path would be lethal

### Fractional Kelly table (Atlas Peak Research, April 2026)
| Fraction | Expected Excess Growth (vs Full Kelly) | Volatility vs Full Kelly |
|----------|----------------------------------------|--------------------------|
| 0.25x    | ~44%                                   | 25%                      |
| 0.50x    | **~75%**                               | **50%**                  |
| 1.00x    | 100% (maximum)                         | 100%                     |
| 1.50x    | ~75% (same as 0.5x!)                   | 150%                     |
| 2.00x    | ~0% (edge consumed)                    | 200%                     |
| >2.00x   | **Negative**                           | >200%                    |

Key insight: "Half Kelly retains ~75% of full-Kelly growth with 50% the volatility, and reduces
the probability of ever losing half starting capital from 1/2 (full Kelly) to **1/8** (half Kelly)"
— Thorp, cited in Atlas Peak Research 2026

### Recommended Kelly fractions by strategy type (Atlas Peak Research 2026)
| Strategy Type | Fraction |
|---------------|----------|
| Repeatable, liquid, diversified factors (stat arb) | 0.30-0.50x |
| High-conviction active equity (fundamental + catalyst) | 0.20-0.35x |
| Moderate conviction / factor-sensitive equity | 0.10-0.20x |
| Speculative, event-driven, crowded, option-like | 0.05-0.10x |

### Input sensitivity (Chopra-Ziemba ratio — MacLean/Thorp/Ziemba)
Errors in means : variances : covariances affect portfolio outcomes in ratio **20 : 2 : 1**
Implication: A sophisticated covariance model cannot rescue a Kelly process that overstates alpha.
Shrink expected return FIRST before computing Kelly fraction.

### Barroso & Santa-Clara (2015), "Momentum Has Its Moments"
- Adjusting momentum exposure inversely to its own recent volatility significantly improves Sharpe
- **Momentum volatility rises sharply BEFORE crashes** — provides early warning signal
- Practical rule: if 21-day vol of strategy rises >40% above 63-day average → cut exposure 50%

---

## Factor Crowding and Portfolio-Level Correlation

### The core problem for PEAD + momentum portfolios
20 positions all selected via PEAD + price momentum load the SAME factor. They are NOT 20 independent bets.
All share: PEAD factor + price momentum factor + possibly small-cap + earnings-revision factor.

"A 5% semiconductor long, 4% cloud long, 4% AI software long, 3% digital advertising long, and 3% index
overlay may be ONE COMMON TRADE if they share real-rate, mega-cap momentum, AI capex sentiment, and
earnings-revision exposure." — Atlas Peak Research 2026

**Individual Kelly fractions cannot simply be summed.** Portfolio Kelly requires: f* = Σ⁻¹(μ - r·1)

### Effective position count math
For n=20 positions, r=1% per-position dollar risk, normal correlation ρ=0.2:
  Portfolio vol ≈ 1% × √(20 × (1 + 19×0.2)) = 1% × √(20×4.8) ≈ **9.8%**

During factor crash (ρ spikes to 0.7):
  Portfolio vol ≈ 1% × √(20 × (1 + 19×0.7)) = 1% × √(20×14.3) ≈ **16.9%**

Effective independent bets in a 20-stock same-factor portfolio ≈ 8-12 (not 20).

### Practical sizing adjustment
If portfolio can tolerate 15% drawdown from simultaneous factor unwind of -20% across 20 positions:
  Max per-position dollar risk ≈ 15% / 20 / 1.0 = **0.75% ceiling**
Use 0.5% per position (not 1%) until factor crowding is monitored and confirmed low.

### MSCI Integrated Factor Crowding Model (2007-2017 sample)
When momentum/value/size factors are crowded: frequency of 5%+ drawdown in factor return
over next 12 months increases significantly.
Source: info.msci.com/MSCI-Integrated-Factor-Crowding-Model

---

## Momentum Crash History (Long-Only Perspective)

### 2009 — The Classic Momentum Crash
- Long-short Fama-French momentum factor: **-80%** over Q1-Q2 2009 (bank/real-estate shorts reversed)
  Source: Freenance.io, citing French Data Library, 2026
- Long-only momentum (MSCI WM): **-35% in a single quarter**, Q1 2009
  Source: Freenance.io, 2026
- Daniel & Moskowitz (2016): worst crashes occur when market was down over prior 1-2 years
  AND then has a strong positive month (bear market rally lifts former worst stocks)
- **Long-only avoids the worst**: no short side blowing up. "Simply underperforms, doesn't blow up."
  Source: CrackingMarkets.com, citing Stockopedia, 2025

### 2000-2002 (Dot-Com Bust)
- Momentum portfolios heavily weighted to tech (1999-2000 winners = mostly tech)
- Severe losses as tech reversed; no verified exact long-only drawdown figure found
  [UNVERIFIED — specific magnitude]

### March 2020 (COVID Crash)
- MSCI World Momentum max drawdown: **-28%** (similar to broad market)
  Source: Freenance.io, 2026
- Rapid V-shape recovery. "A similar but less severe crash in late 2020 as rotation
  from COVID losers to COVID winners accelerated." — BananaFarmer.app, 2025
- Long-only momentum recovered fully by 2021; MSCI WM +92% cumulative 5Y through 2025

### 2022 Rate Rotation
- Rising rates triggered derating of long-duration growth stocks (overlapping with momentum)
- MSCI World Momentum lagged briefly before reasserting in late 2023
- Sector-dependent: tech/homebuilders -28%; defense +10%

### Portfolio-level circuit breaker evidence
Adding a **10% individual trailing stop** to momentum:
- Reduced worst monthly loss from ~-50% to ~**-11%**
- **Doubled Sharpe ratio** vs unmanaged momentum
Source: CICF conference paper cited in CrackingMarkets.com, 2025

Tiered circuit breaker recommended by practitioners:
- Portfolio drawdown -8%: review all positions, pause new entries, tighten stops to 5%
- Portfolio drawdown -15%: halve all position sizes, halt new entries
- Portfolio drawdown -20%: exit all equity positions, move to cash, wait for 200MA re-cross
Source: CrackingMarkets.com "US Stock Momentum Trading System" deep research, Feb 2025

---

## Key Sources (All Verified)

1. PortfoliosLab.com — live ETF correlation data (XLK/XHB, ITA/XAR), August 6, 2026
2. FHFA WP 24-03 (Batzer, Coste, Doerner, Seiler, 2024) — fhfa.gov/research/papers/wp2403
3. Philadelphia Fed WP 26-33 (Graybill, Mangum, July 2026) — mortgage lock-in housing tightness
4. Federal Reserve FEDS (2025) — "Locked In: Mobility, Market Tightness, and House Prices"
5. Subrahmanyam, A. (2025), SSRN 5930255 — PEAD revival critique, UCLA Anderson
6. Martineau, C. (2022), SSRN 3111607 — "Rest in Peace PEAD"
7. Brandt, Kishore, Santa-Clara, Venkatachalam — "Earnings Announcements are Full of Surprises" (Quantpedia)
8. Chan, Jagadeesh, Lakonishok (1996, NBER 5375) — "Momentum Strategies"
9. Duggaraju & Bharadwaj (2025), SSRN 6174938 — earnings surprise sector heterogeneity
10. Atlas Peak Research (April 25, 2026) — "Kelly Criterion in Financial Markets" — atlaspeakresearch.com/report/07bf72
11. Kelly, J.L. (1956) — "A New Interpretation of Information Rate," Bell System Technical Journal
12. MacLean, Thorp, Ziemba — "Good and Bad Properties of the Kelly Criterion"
13. Busseti, Ryu, Boyd (2016) — "Risk-Constrained Kelly Gambling"
14. Barroso & Santa-Clara (2015) — "Momentum Has Its Moments"
15. Daniel & Moskowitz (2016) — "Momentum Crashes"
16. Freenance.io (2026) — MSCI World Momentum history, crash statistics (citing French Data Library)
17. CrackingMarkets.com (Feb 2025) — momentum system deep research (stop-loss, circuit breakers)
18. QuantStrategy.io (April 2026) — defense stocks backtesting, rate sensitivity
19. MSCI Integrated Factor Crowding Model (2007-2017 sample) — info.msci.com
20. Asness, Moskowitz, Pedersen (2013, JF) — "Value and Momentum Everywhere"

# PEAD and Price Momentum — Verified Academic Evidence (August 2026)

Compiled from deep research session August 2026.
Full report: /tmp/research-cluster1-pead-momentum.txt (822 lines)
Context: trading strategy review — long equities with positive earnings surprises + price momentum.
All citations verified against DOI, NBER, JSTOR, or full-text PDF unless marked [UNVERIFIED].

---

## PEAD: Core Quantified Evidence

**Ball & Brown (1968)** — Journal of Accounting Research 6(2): 159-178. DOI: 10.2307/2490232.
Founding paper. NYSE 1957-1965. Established price drift continues months after earnings announcement.

**Bernard & Thomas (1989)** — Journal of Accounting and Economics 11(1): 1-36. DOI: 10.1016/0165-4101(89)90003-2.
The definitive rigorous paper. Quarterly data 1974-1986. SUE-decile sort.
- Top vs bottom SUE decile: **~4.2% CAR spread over 60 trading days**
- Long side (top decile): +2.0% to +3.0% on size-adjusted benchmark
- Short side (bottom decile): -1.5% to -2.5%
- ~Half the excess return materialized AFTER first 10 days (rules out microstructure)
- Days to 50% absorption: 25-35 days (positive), 20-30 days (negative)
- Explicitly ruled out CAPM risk premium: drift signs differ between long/short, inconsistent with systematic risk

**Bernard & Thomas (1990)** — Journal of Accounting and Economics 13(4): 305-340. DOI: 10.1016/0165-4101(90)90008-R.
- Documented seasonal structure: disproportionate drift concentrated around the NEXT quarter's announcement
- Interpretation: investors anchor to prior quarter's results, re-discover information when next quarter confirms

**Livnat & Mendenhall (2006)** — Journal of Accounting Research 44(1): 177-205. DOI: 10.1111/j.1475-679X.2006.00196.x.
- Analyst forecast errors (vs time-series seasonal model) produce stronger drift signal
- Mechanistically distinguishes PEAD from generic momentum: identifiable information gap, not diffuse price continuation

**Hirshleifer, Lim & Teoh (2009)** — Journal of Finance 64(5): 2289-2325. DOI: 10.1111/j.1540-6261.2009.01501.x.
- Limited attention amplifies PEAD: stocks reporting on high-volume announcement days drift larger
- Friday earnings announcements (lower attention): larger drift. Behavioral mechanism confirmed.

---

## PEAD: Size-Cap Gradient (QuantDecoded backtest, 2000-2025, CRSP/Compustat)

SUE quintile spread (Q5 minus Q1), cumulative abnormal return at day 60:

| Market Cap | Gross Drift (Day 60) | Net After Costs | Half-Life | Drift Complete |
|---|---|---|---|---|
| Micro (<$500M) | 5.8% | ~2.8% | ~28 days | Day 90+ |
| Small ($500M-$2B) | 4.9% | ~3.8% | ~22 days | Day 75 |
| Mid ($2B-$10B) | 3.2% | ~2.8% | ~15 days | Day 50 |
| Large ($10B-$50B) | 1.7% | ~1.6% | ~8 days | Day 20 |
| Mega (>$50B) | 1.5% | ~1.5% | ~6 days | Day 20 |

**Practical implication:** Small-cap sweet spot for net exploitable drift (~3.8% after costs).
Mega-cap PEAD offers only ~1.5% gross — marginal for active strategies with overhead.

Analyst coverage gradient: mega-cap avg 22.4 analysts, micro-cap avg 1.9 analysts.
This coverage differential is the primary mechanism for the size effect.

**Ng, Rusticus & Verdi (2008)** — Journal of Accounting Research 46(3): 661-696. DOI: 10.1111/j.1475-679X.2008.00290.x.
Transaction costs constrain informed trades; PEAD profits significantly reduced by trading costs, especially small firms.

**Chordia, Subrahmanyam & Tong (2014)** [UNVERIFIED — full text not accessed]
Reportedly documented PEAD magnitude declined in 2000s for large/mid caps as efficiency improved.

---

## Price Momentum: Core Quantified Evidence

**Jegadeesh & Titman (1993)** — Journal of Finance 48(1): 65-91. DOI: 10.1111/j.1540-6261.1993.tb04702.x.
NYSE+AMEX 1965-1989.
- 6/6 strategy (6-month formation, 6-month holding): ~9.5-12% excess return annually
- ~1%/month is the standard citation across J/K combinations from 3-12 months
- Partial reversals years 2-3 but initial 12-month signal robustly positive
- One-month skip between formation and holding avoids short-term reversal contamination

**Jegadeesh & Titman (2001)** — Journal of Finance 56(2): 699-720. DOI: 10.1111/0022-1082.00342.
Out-of-sample confirmation: extended to 1990-1998, profits continued at similar magnitudes. Not data snooping.

**Rouwenhorst (1998)** — Journal of Finance 53(1): 267-284. DOI: 10.1111/0022-1082.95722.
12 European markets, 1980-1995.
- International diversified momentum portfolio outperforms past losers by **>1%/month after risk adjustment**
- Positive in ALL 12 countries; stronger in small caps within each country
- Japan showed weaker momentum than other developed markets

**Asness, Moskowitz & Pedersen (2013)** — Journal of Finance 68(3): 929-985. DOI: 10.1111/jofi.12021.
8 diverse markets and asset classes (US equities, UK, Europe, Japan, equity futures, bonds, currencies, commodities). ~1981-2011.
- Consistent positive momentum premia in ALL eight markets/asset classes
- Global momentum strategies positively correlated with each other across asset classes
- Value and momentum negatively correlated: within-asset ~-0.5 to -0.6
- 50/50 value + momentum: approximately **DOUBLES Sharpe ratio** of either alone
- US large-cap equity momentum Sharpe: ~0.38-0.40
- Funding liquidity risk is partial (not complete) source of value-momentum correlation structure

**Japan Failure — Asness (2011)** — Journal of Portfolio Management 37(4): 67-75. DOI: 10.3905/jpm.2011.37.4.067.
July 1981 - December 2010, large-cap value-weighted, top 90% market cap.
- Japan standalone momentum Sharpe: **effectively 0 (≈0.03)** for 29.5 years
- Japan standalone value Sharpe: strongest of all four regions (US, UK, Europe, Japan)
- Japan 50/50 value + momentum: strongly positive Sharpe — "exception proves the rule"
- Three-factor model (controlling value, size, market): Japan momentum significantly positive
- Univariate failure is artifact of extremely strong value premium offsetting momentum
- Chui, Wei & Titman (2010) attributed Japan failure partly to cultural factors (lower individualism) [UNVERIFIED]

---

## Critical Question: Are PEAD and Price Momentum the Same Factor?

### Paper 1: Chan, Jegadeesh & Lakonishok (1996) — INDEPENDENT FACTORS
Journal of Finance 51(5): 1681-1713. DOI: 10.1111/j.1540-6261.1996.tb05222.x.
NYSE/AMEX/NASDAQ 1977-1993.
**Finding:** Past return and past earnings surprise each predict large drifts AFTER controlling for the other.
Neither subsumes the other in bivariate sorts or Fama-MacBeth regressions.
Dual high price + high earnings momentum portfolio: highest drift (~2-3% quarterly excess return).
Conclusion: Both reflect underreaction to different information; market responds gradually to all new information.

### Paper 2: Chordia & Shivakumar (2006) — EARNINGS SUBSUMES PRICE
Journal of Financial Economics 80(3): 627-656. DOI: 10.1016/j.jfineco.2005.05.005.
**Finding:** Systematic component of earnings momentum fully captures price momentum in time-series tests.
Price momentum strategies have no significant alpha once earnings momentum is controlled.
Directional conclusion: "the price momentum anomaly is a manifestation of the earnings momentum anomaly."
Caveat: tests identified primarily off small-cap stocks (pointed out by Novy-Marx 2015).

### Paper 3: Novy-Marx (2015) — EARNINGS MOMENTUM DRIVES PRICE MOMENTUM (working paper)
"Fundamentally, Momentum Is Fundamental Momentum" — U. of Rochester working paper.
Available: mysimon.rochester.edu/novy-marx/research/FMFM.pdf [UNVERIFIED as published]
**Finding:**
- Fama-MacBeth regressions: earnings surprises subsume coefficient on past returns (loses significance)
- Adding past returns does NOT change coefficient on earnings surprise
- Time-series: price momentum has zero alpha vs earnings momentum; earnings momentum has large significant alpha vs price momentum
- Holds across BOTH large cap and small cap (extends Chordia-Shivakumar beyond small caps)
- Price momentum ADDS CRASH RISK without adding return: earnings momentum strategies controlling for price momentum have lower volatility and no negative skew, at same or higher average returns
- Conclusion: investors trading earnings momentum lose nothing by ignoring price momentum

### Paper 4: Sadka (2006) — COMMON LIQUIDITY RISK CHANNEL
Journal of Financial Economics 80(2): 309-349. DOI: 10.1016/j.jfineco.2005.06.001.
Substantial part of BOTH momentum and PEAD returns can be viewed as compensation for the SAME liquidity risk factor
(unexpected variations in aggregate informed-to-noise-trader ratio). Shared risk channel.

### Synthesis on Stacking PEAD + Momentum

Weight of evidence leans toward: **NOT two independent underreaction edges.**

1. Both reflect market underreaction — they share the same behavioral foundation.
2. Earnings momentum (PEAD) is the more fundamental of the two.
3. Price momentum captures earnings momentum + noise (other information, sentiment, liquidity dynamics).
4. Dual filter (positive SUE + strong price momentum) concentrates earnings-momentum signal, adds price momentum's crash risk.
5. From Novy-Marx: clean earnings momentum > combined strategy for risk-adjusted returns.
6. CJL (1996) independent alpha in bivariate sorts is likely due to coarse 3×3 grid not adequately controlling for correlation.

**For long-only implementation:** Requiring BOTH filters simultaneously may screen out genuine PEAD opportunities where momentum hasn't yet caught up (most valuable early drift window). Consider using PEAD as primary signal and momentum as a CONFIRMING screen, not a dual-required filter.

---

## Momentum Decay: Has Alpha Been Arbitraged Away?

**McLean & Pontiff (2016)** — Journal of Finance 71(1): 5-32. DOI: 10.1111/jofi.12365.
97 anomaly variables:
- **26% lower returns** out-of-sample (pre-publication; upper bound on data mining)
- **58% lower returns** post-publication
- Additional ~32% post-publication decline attributed to investor learning and arbitrage

**Lee / KAIST (2025)** — arXiv: 2512.11913.
Using 8 Fama-French factors 1963-2024:
- Momentum returned ~**10% annually in the 1990s** → ~**2% annually in 2015-2024**
- Hyperbolic decay model fits: R²=0.65 (vs linear 0.51, exponential 0.61)
- Crowding accelerated post-2015, correlated with factor ETF growth (ρ = -0.63)
- Crowded momentum shows **LOWER** crash probability (0.38x, p=0.006) — benign crowding

**Nullberg Out-of-Sample Test (2017-2026)**
Value-weighted, NYSE breakpoints, J=11 skip-1:
- D10-D1 = **-0.134%/month, t = -0.16** → FAILED (null result, not inverted)
- Equal-weighted J=11: +0.048%/month, t=0.10 → FAILED
- Equal-weighted **J=6 skip-1: +0.615%/month, t=1.45** → Best surviving spec, right direction, sub-threshold
- Both 2017-2021 and 2021-2026 sub-halves independently null
- Verdict: **decayed to null**, not reversed. 6-month lookback is more robust than 12-month.

**Practical implication:** The canonical 1%/month (~10%/year) momentum premium is NOT replicable in standard long-short form today. Momentum as a directional FILTER within a long-only strategy retains more value than as a standalone long-short factor.

---

## Momentum Failure Modes

### Momentum Crashes (Daniel & Moskowitz 2016)
Journal of Financial Economics 122(2): 221-247. DOI: 10.1016/j.jfineco.2016.01.009.

**Historical crashes (1927-2013 sample, top/bottom decile long-short):**
- July-August 1932: Past losers +232%, winners +32% → net approximately **-73% to -91.6%** (2 months)
- March-May 2009: Past losers +163%, winners +8%, market +26% → net approximately **-40% to -73%** (3 months)

**Mechanism:**
- Following sustained market decline, past-losers become HIGH-BETA stocks, past-winners become LOW-BETA
- At market rebound, momentum portfolio is effectively SHORT high-beta → catastrophic losses
- In bear markets: loser portfolio beta can exceed 3.0, winner beta below 0.5
- Up-beta vs down-beta asymmetry in bear markets: -1.51 vs -0.70 (t-stat for difference = 4.5)
- Behavior in bear markets: written call option on market (small gain if market falls, large loss if rebounds)

**Forecastability (CRITICAL for risk management):**
Crashes are PARTLY forecastable. They cluster in "panic states":
1. Prior 12-month market return significantly negative (bear market state) — OBSERVABLE IN ADVANCE
2. Ex ante volatility elevated (high VIX) — OBSERVABLE IN ADVANCE
3. Contemporaneous sharp market rebound — NOT forecastable, triggers the loss

When conditions (1) and (2) present: conditional expected momentum return is LOW.
**Dynamic strategy:** scale WML exposure by forecast conditional Sharpe ratio → approximately DOUBLES alpha and Sharpe vs static (from ~0.45 to ~0.85).

**Cooper, Gutierrez & Hameed (2004)** — Journal of Finance 59(3). DOI: 10.1111/j.1540-6261.2004.00665.x.
1929-1995 US data:
- Monthly momentum profit in UP market state (positive prior 3yr return): **+0.93%/month**
- Monthly momentum profit in DOWN market state (negative prior 3yr return): **-0.37%/month**

### PEAD Sector-Specific Decay
- **Mega-cap tech (AAPL, MSFT, NVDA):** 20+ analysts, 70-80% institutional ownership → PEAD absorbed within 5-10 days. Using 60-day window offers only ~1.5% gross spread, likely below overhead costs.
- **Defense large caps (LMT, RTX, NOC):** Earnings additionally diluted by non-earnings catalysts (contracts, budget news). PEAD signal weaker relative to sector noise.
- **Mid-cap homebuilders ($2-10B):** More viable — 8-12 analysts, meaningful drift. Large homebuilder (DHI, LEN) PEAD similar to large-cap dynamics.

### Factor Crowding at Portfolio Level
- Both PEAD and momentum are actively targeted by quant and event-driven hedge funds
- Combined filter defines a universe that is heavily crowded
- Exit risk: multiple funds attempting simultaneous reduction creates correlated drawdowns
- Crowding-based timing fails: crowding knowledge is already priced (Lee 2025)

### Transaction Cost Drag (Rule of Thumb)
- Large-cap ($10B+): ~0.2-0.4% round-trip. Against 1.7% drift: marginal.
- Mid-cap ($2-10B): ~0.7-1.0% round-trip. Against 3.2% drift: ~2.2-2.5% net.
- Small-cap: ~1.1% round-trip. Against 4.9% drift: ~3.8% net (best risk-adjusted).

---

## Key Tensions / Unresolved Questions in the Literature

1. **CJL (1996) vs Chordia-Shivakumar (2006) vs Novy-Marx (2015):** The independence of price and earnings momentum is genuinely contested. No consensus. Most recent (Novy-Marx) argues earnings drives price with the stronger methodology.

2. **Japan:** Standalone failure but conditional success (with value, or in three-factor model). Suggests momentum needs to be evaluated as a SYSTEM with value, not in isolation.

3. **Decay or gone?** 2017-2026 standard 12-month momentum is statistically null (Nullberg). But 6-month and quality-filtered variants survive. Not arbitraged away so much as the easy form is gone; structured variants retain edge.

4. **Long-only vs long-short:** Most academic evidence is for long-short factor portfolios. For long-only, momentum as a filter retains more value (you benefit from concentrating winners; you avoid the catastrophic short-leg crash risk).

---

## Citation Verification Status

**VERIFIED (DOI/full text/NBER confirmed):**
Ball & Brown 1968, Bernard & Thomas 1989, Bernard & Thomas 1990, Jegadeesh & Titman 1993,
Jegadeesh & Titman 2001, Rouwenhorst 1998, Chan Jegadeesh Lakonishok 1996 (full text accessed),
Asness Moskowitz Pedersen 2013 (full text accessed), Asness 2011 Japan (full text accessed),
Daniel & Moskowitz 2016 (full text accessed), Cooper Gutierrez Hameed 2004 (Wiley abstract),
Chordia & Shivakumar 2006 (EconPapers confirmed; full text inaccessible),
Novy-Marx 2015 (working paper, full text accessed), Hirshleifer Lim Teoh 2009,
Livnat & Mendenhall 2006, Ng Rusticus Verdi 2008, Sadka 2006, McLean & Pontiff 2016,
Lee / KAIST 2025 (arXiv full text accessed).

**[UNVERIFIED]:** Chordia Subrahmanyam Tong 2014 · Geczy & Samonov 2013 (cited in D&M 2016) ·
Israel & Moskowitz 2013 (cited in D&M 2016) · DellaVigna & Pollet 2009 ·
van Vliet et al 2024 (cited in Nullberg) · Chui Wei Titman 2010 (cited in Asness 2011)

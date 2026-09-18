# Trading Strategies — Verified Academic Evidence (July 2026)

Compiled from research session July 2026. All sources directly verified (full text or DOI).
This is a condensed knowledge bank for use in future investing/trading research tasks.
Full source file: /tmp/trading-academic-research.txt (889 lines, 60KB)

---

## Momentum Trading

| Finding | Source | Quantified Result | Practical Note |
|---|---|---|---|
| US momentum works | Jegadeesh & Titman, JF 1993 | 6M/6M strategy: ~9.5% excess return over 12 months (NYSE/AMEX 1965-89); gains partially reverse in years 2-3 | Verified full text |
| European momentum works | Rouwenhorst, JF 1998 | >1%/month excess return, 12 European markets, 1980-95; stronger in small-caps | DOI verified |
| Japan: momentum FAILS | Asness, JPM 2011 | Standalone momentum Sharpe ≈ 0 in Japan 1981-2010; value+momentum combined works | Full text via AQR PDF |
| China: contrarian better | Wu, HKIMR WP 2003 | Pure momentum fails; mean reversion half-life ~232 days; combined strategy 22.2% annualised excess (SHSE) | Full text verified |
| Korea: mixed | Lee et al. 2015; Tandfonline 2022/2025 | Traditional 3-12M momentum unprofitable; 1-week short-term momentum works | Abstracts verified |
| Value+momentum combined | Asness, Moskowitz & Pedersen, JF 2013 | Combined portfolio Sharpe roughly DOUBLE either alone; ~-0.5 to -0.6 pairwise factor correlation | Verified |

**Key rule:** Never use momentum as a standalone in East Asian markets. Combine with value.

---

## Mean Reversion / Contrarian

| Finding | Source | Quantified Result |
|---|---|---|
| Long-term US contrarian | DeBondt & Thaler, JF 1985 | Loser portfolios outperform winner portfolios by ~24.6% CAR over 36 months | Verified via citations |

---

## Portfolio Construction

| Method | Source | Key Finding |
|---|---|---|
| Mean-variance (Markowitz) | Markowitz, JF 1952 | Diversification reduces variance; only free lunch in finance. But: input-sensitivity makes raw MVO unstable in practice | DOI verified |
| Black-Litterman | Black & Litterman, FAJ 1992 | Global diversified portfolio: +85bp/year at same 10.7% risk vs domestic-only. Start from market-cap baseline, tilt modestly. Only 2/14 assets positive weight with raw MVO | Key stats verified |
| Risk Parity | Qian, PanAgora 2005/2009 | 60/40 Sharpe 0.36; Risk Parity at same 10% risk: Sharpe 0.45 (+90bp/year). Stocks contribute 95% of risk but 60% of capital. FAILS when bonds+stocks correlate positively (2022) | Full text verified |

---

## Market Timing

| Finding | Source | Quantified Result |
|---|---|---|
| Mutual funds can't time market | Treynor & Mazuy, HBR 1966 | Only 1/57 funds showed statistically significant timing ability | Widely verified |
| Mutual funds can't time market | Henriksson, JB 1984 | 116 funds, 1968-80: no evidence of significant positive timing ability | Abstract confirmed |

**Implication:** Rules-based rebalancing (e.g. monthly, or drift >5% threshold) dominates discretionary timing.

---

## Day Trading Profitability

| Finding | Source | Quantified Result |
|---|---|---|
| >80% lose money | Barber, Lee, Liu & Odean, 2004 | Taiwan TSE, 130k+ traders: >8/10 lose money after costs; transaction costs flip gross profit to net loss | Full text verified |
| 97% lose money (persistent traders) | Chagué, De-Losso & Giovannetti, SSRN 3423101 (2020) | Brazil, 19,646 traders; of 1,551 who persisted >300 days: 97% net negative; only 17 earned above min wage; **no learning effect** | Statistics verified |
| High turnover ~6%/year drag | Barber & Odean, JF 2000 | 78k US households: high-turnover quintile earned ~11.4% net vs 17.5% market | Abstract verified (Wiley DOI) |

**Critical: no learning effect** — day trading performance does NOT improve with experience (Brazil study).

---

## Factor Investing

| Factor | Source | Quantified Result | Retail Access |
|---|---|---|---|
| Low volatility (BAB) | Frazzini & Pedersen, JFE 2014 | Sharpe ratio ≈ 0.75 since 1926; anomaly exists across equities, bonds, futures | iShares MSCI Min Vol ETF |
| Quality / gross profitability | Novy-Marx, JFE 2013 | ~0.26%/month excess; hedges value perfectly (negatively correlated) | VanEck or multi-factor ETF |
| Value (HML) | Fama & French, JFE 1993 | ~4.5-5.1%/year premium 1927-91; weakened post-2000 in US large-caps; still present internationally | Value ETFs |
| Momentum | Jegadeesh & Titman 1993 | ~9.5%/year (US); Betashares MTUM (ASX:MTUM) for ASX | MTUM, IWMO |

**Priority order for retail (by evidence strength):** Low-vol > Quality > Momentum > Value > Size

**Best combination:** Multi-factor ETF (value + momentum + quality) — factor correlations reduce portfolio risk below any single factor.

---

## ASX-Specific Notes (non-academic but community-validated)

- Mean reversion on liquid ASX large-caps (daily timeframe): community-validated in r/algotrading
- Pairs trading: CBA/WBC, BHP/RIO — lower vol than single stock, statistical arbitrage logic
- ASX factor ETFs: Betashares MTUM (momentum), VanEck MSCI Multifactor (VLUE + MTUM + QUAL)
- Community consensus: sector rotation (materials → financials → consumer) on 3-6M cycles has backing
- What consistently doesn't work: day trading ASX with <$500k (costs kill edge), RL/ML black-box on short series, chasing screener signals

---

## Tax Overlay for Australian Investors (47% marginal rate)

- Short-term gains (<12 months): 47% — destroys most active strategy edge
- Long-term gains (>12 months, pre-2027): 23.5% effective after 50% CGT discount
- Post-1 July 2027: CPI indexation + 30% minimum — worse for high-growth assets
- PPOR (principal residence): **completely CGT exempt** — no partial discount, full exemption
- SMSF accumulation: 10% effective on long-term gains; fully-franked dividends → often 0% tax
- Day trading income: 47% as ordinary income, no CGT discount regardless of hold period

**Ranking: factor ETF held >12 months >> individual stock picking >> mean reversion swing trades >> day trading**

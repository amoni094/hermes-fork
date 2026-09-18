# Technical Trading Strategies — Cross-Market Evidence & Multilingual Sweep
# August 2026 | Research for Slava's PEAD+momentum strategy context

## Source
Multilingual academic sweep (English + CJK + EU + LatAm) + cross-validation against
paperswithbacktest/awesome-systematic-trading GitHub repo.
Full report: /tmp/slava-technical-strategies-multilang-comparison.md (850 lines, 38 refs)

## Slava baseline (reference for all comparisons)
- Strategy: PEAD + price momentum (tech/defense/homebuilder sectors, AU context)
- Gross backtest: 8-12% pa. Net realistic (AU 47% tax + execution + OOS): 0-3% pa
- Gross Sharpe ~0.3-0.5; net ~0.2-0.4
- Core papers: J&T 1993 DOI:10.2307/2328882; B&T 1989 DOI:10.1016/0165-4101(89)90003-2

## FINDINGS FROM PAPERSWITHBACKTEST/AWESOME-SYSTEMATIC-TRADING CROSS-VALIDATION

### Asset Growth Effect — most important new finding
- Paper: Cooper, Gulen & Schill (2008), JF 63(4):1609-1651. SSRN:1335524
- QuantConnect Sharpe: 0.835 (yearly rebalance, vol 10.2%)
- Mechanism: companies with high YoY asset growth underperform; low growth outperform
- AU-tax relevance: YEARLY rebalance = positions held >12M = 50% CGT discount eligible
  — one of the most AU-tax-efficient equity factors available
- Post-pub decay: ~50% per McLean & Pontiff (2016)
- Slava application: within existing sector universe (tech/defense/homebuilders),
  screen OUT names with recent high asset growth (dilutive M&A, overexpansion)

### Low Volatility Factor & BAB
- Low Vol: Baker, Bradley & Wurgler (2011). FAJ 67(1):40-54. QuantConnect Sharpe 0.717
- BAB: Frazzini & Pedersen (2014). JFE 111(1):1-45. QuantConnect Sharpe 0.594
- Both monthly rebalance — tax drag in AU context but not fatal
- Slava application: within sectors, tilt toward lower-beta names
  Defense/infrastructure = lower beta; tech = higher beta; homebuilders = moderate+rate-sensitive

### Time-Series Momentum — calibrated Sharpe
- Paper: Moskowitz, Ooi & Pedersen (2012). JFE 104(2):228-250. DOI:10.1016/j.jfineco.2011.11.003
- INSTITUTIONAL Sharpe: ~1.28 (vol-targeted at 10% with leverage across 58 futures contracts)
- INDIVIDUAL unleveraged Sharpe (QuantConnect): ~0.58
- Both figures are real; ~1.28 is the institutional implementation, ~0.58 is individual reference
- Do NOT cite 1.28 as "the implementable Sharpe" for a personal account — this overstates the edge
- Net (institutional, 2/20 fees): ~8-14% pa. Net individual: lower, not clearly > Slava's 0-3% net
- Hurst et al. (2017): ~1.00 Sharpe net of fees across 100+ years (vol-targeted, also institutional)
- Conclusion: multi-asset futures TF is genuinely better than Slava at institutional scale;
  advantage narrows considerably at individual/unleveraged scale

### Reversal During Earnings vs PEAD — timing risk
- Reversal During Earnings Announcements: QuantConnect Sharpe 0.785 (SSRN:2275982)
- PEAD is the 2-60 day drift AFTER announcement; reversal effect is ON announcement day
- They are sequential, not opposed — but entering PEAD on announcement day risks buying
  into the reversal. Best practice: wait 1-2 days post-announcement before entering PEAD

### Complete factor Sharpe league table (QuantConnect unleveraged backtests)
From paperswithbacktest/awesome-systematic-trading, strategies relevant to Slava:
  Asset Growth Effect           Sh 0.835  yearly   AU-tax-OK   JF 2008
  Low Volatility Factor         Sh 0.717  monthly  some drag   FAJ 2011
  Reversal at Earnings          Sh 0.785  daily    short-term  SSRN:2275982
  BAB (Betting Against Beta)    Sh 0.594  monthly  some drag   JFE 2014
  Time-Series Momentum (unlevd) Sh 0.576  monthly  futures req JFE 2012
  Sector Momentum Rotation      Sh 0.401  monthly  OK          various
  Momentum Factor (XS)          Sh -0.008 monthly  --          (nearly dead)
  
Naive cross-section 6/12M momentum: Sharpe nearly ZERO in unleveraged form — this is
what McLean & Pontiff and Nullberg's out-of-sample evidence shows. Slava's edge comes from
the PEAD+sector overlay, not from naive momentum screening.

## MULTILINGUAL SWEEP KEY FINDINGS

### Asia: momentum FAILS, mean reversion dominates
- China (A-share): pure 6-12M momentum NEGATIVE post-2005 (Split-Share Reform → institutions
  arbitrage it). Noise-filtered momentum: ~8.2% gross (SAIF/SJTU working paper, Zhang & Zi 2025)
- Japan: standard MACD (12,26,9) on Nikkei futures: NEGATIVE returns (Kang 2021, JRFM).
  RSI/BB mean reversion works (commercial backtest Sharpe 0.91-1.21) — GPIF + BOJ ETF floor
  creates systematic demand at oversold levels
- Korea: 40 years (1983-2023) of data shows REVERSAL dominates individual stocks (Kang & Ryu 2025)
- Mechanism across all three: retail overreaction → institutional correction → reversal
- Slava implication: ASX stocks with >60% retail ownership may behave like KOSPI (reversal-dominant)
  rather than US S&P 500 (momentum-dominant). Check broker ownership before applying US parameters.

### European/LatAm: thin corpus, access barriers
- France/Germany: researchers publish in English international venues; no separate French/German
  TA academic corpus exists
- Russia (CyberLeninka): RSI/MA work in crisis/high-vol regimes, near-zero in low-vol conditions
- Brazil/LatAm: genuine literature gap — no peer-reviewed quantified TA profitability research found

### Confirmed weak/dead strategies
- Bollinger Bands (post-2001): returns NEGATIVE in developed markets (Fang, Jacobsen & Qin 2017, JPM)
- MA crossover (modern): ~2-5% net after costs — below Slava's 0-3% net (yes, below)
- RSI short-term reversal: gross ~24%/pa but EXTREMELY high turnover → 47% ordinary income AU → net ~4-8%
- Intraday MIM: works in US/Korea but 47% ordinary income in AU destroys edge

### What improves Slava without replacing it
1. Vol-managed overlay (Moreira & Muir 2017, JF): +25% Sharpe. When 21-day strategy vol
   rises >40% above 63-day avg, cut all sizes 50% [UNVERIFIED thresholds — Barroso & Santa-Clara 2015]
2. Overnight execution (Lou, Polk & Skouras 2019, JFE): PEAD+momentum alpha is entirely overnight.
   Execute entries at close, exits at open.
3. Pre-FOMC overlay (Lucca & Moench 2015, JF): Sharpe >=1.1 on 8 events/year. Low turnover.
4. Asset Growth screen: yearly low-turnover quality filter on existing sector universe
5. Low-beta tilt: within sectors, prefer lower-beta names (consistent with Low-Vol/BAB factors)

## ADVERSARIAL REVIEW LESSONS (from this session)
See adversarial-review skill references/financial-research-report-adversarial-checks.md for:
- Body vs table Sharpe consistency checks
- Leveraged vs unleveraged Sharpe detection
- Citations-in-body vs reference-list sweep
- Broken URL detection
- Reference numbering drift after edits

This session's report went through 3 adversarial passes, resolving 3 HIGH and 12 MEDIUM issues
before reaching clean status. Expected convergence for a ~700-line multi-section research report.

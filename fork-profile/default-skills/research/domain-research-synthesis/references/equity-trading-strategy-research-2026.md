# Equity Trading Strategy Deep Research — Knowledge Bank (August 2026)

Compiled August 2026 from a three-subagent parallel research session.
Primary report (full 50KB): /tmp/slava-trading-strategy-report.md
Raw cluster files: /tmp/research-cluster1-pead-momentum.txt, cluster2-sectors-sizing.txt, cluster3-alternatives-execution-tax.txt

---

## Strategy Context

Strategy reviewed: long equities with positive earnings surprises (PEAD) + price momentum
across three sectors (tech, defense, homebuilders). 25% cash reserve. 0.5-1% dollar risk
per position. Trailing stops on winners via broker platform.

---

## PEAD (Post-Earnings Announcement Drift) — Key Findings

**Foundational papers:**
- Ball & Brown (1968), JAR 6(2):159-178. DOI:10.2307/2490232. Original discovery.
- Bernard & Thomas (1989), JAE 11(1):1-36. DOI:10.1016/0165-4101(89)90003-2.
  Definitive quantification: 4.2% CAR spread (top vs bottom SUE decile) over 60 days.
- Bernard & Thomas (1990), JAE 13(4):305-340. DOI:10.1016/0165-4101(90)90008-R.
  Seasonal pattern: drift concentrated around NEXT quarterly announcement.
- Hirshleifer, Lim & Teoh (2009), JF 64(5):2289-2325. DOI:10.1111/j.1540-6261.2009.01501.x.
  Limited attention mechanism: PEAD amplified when investor attention is divided.
- Livnat & Mendenhall (2006), JAR 44(1):177-205. DOI:10.1111/j.1475-679X.2006.00196.x.
  Analyst forecast errors produce stronger drift than time-series seasonal models.
- Ng, Rusticus & Verdi (2008), JAR 46(3):661-696. DOI:10.1111/j.1475-679X.2008.00290.x.
  Transaction costs significantly reduce PEAD profits; limits-to-arbitrage explanation.
- Sadka (2006), JFE 80(2):309-349. DOI:10.1016/j.jfineco.2005.06.001.
  Both PEAD and momentum share a common liquidity risk channel.

**Size-cap gradient (QuantDecoded backtest, 2000-2025):**

  Cap tier          | Gross 60-day CAR | Net after costs
  ------------------|------------------|----------------
  Micro (<$500M)    | 5.8%             | ~2.8%
  Small ($500M-$2B) | 4.9%             | ~3.8% (sweet spot)
  Mid ($2B-$10B)    | 3.2%             | ~2.8%
  Large ($10B-$50B) | 1.7%             | ~1.6%
  Mega (>$50B)      | 1.5%             | ~1.5%

**Large-cap arbitrage:** Martineau (2022, U. Toronto) and Subrahmanyam (2025, UCLA,
SSRN 5930255) both argue PEAD in non-microcap stocks is largely gone since ~2006
(decimal trading + HFT). When microcaps excluded, PEAD t-stat drops from 2.18 to 1.43.

**Practical implication:** PEAD only meaningfully exploitable in small-to-mid cap.
Mega-cap tech (AAPL/NVDA/MSFT): drift absorbed within 5-10 days. Avoid as PEAD play.

---

## Momentum — Key Findings

**Foundational:**
- Jegadeesh & Titman (1993), JF 48(1):65-91. DOI:10.1111/j.1540-6261.1993.tb04702.x.
  6/6 strategy: ~9.5-12% excess annual return, NYSE/AMEX 1965-1989.
- Jegadeesh & Titman (2001), JF 56(2):699-720. DOI:10.1111/0022-1082.00342.
  Out-of-sample (1990-1998) confirmed. Not data snooping.
- Rouwenhorst (1998), JF 53(1):267-284. DOI:10.1111/0022-1082.95722.
  12 European markets, >1%/month, positive in all 12. Japan weaker.
- Asness, Moskowitz & Pedersen (2013), JF 68(3):929-985. DOI:10.1111/jofi.12021.
  Value+momentum combined: Sharpe ~double either alone. Correlation -0.5 to -0.6.
- Asness (2011), JPM 37(4):67-75. DOI:10.3905/jpm.2011.37.4.067.
  Japan standalone momentum Sharpe ~0.03 (effectively zero). Combined with value: works.

**Decay:**
- McLean & Pontiff (2016), JF 71(1):5-32. DOI:10.1111/jofi.12365.
  Returns 58% lower post-publication across 97 predictors. Momentum included.
- Lee (2025), arXiv:2512.11913 (KAIST). Hyperbolic decay model: 10%/yr (1990s) →
  ~2%/yr (2015-2024). Crowding from factor ETF growth (rho = -0.63). Crowding LOWERS
  crash probability for momentum (unlike reversal factors). Factor timing based on
  crowding signals fails.
- Nullberg (2026), nullberg.com. 5,568 US stocks, 2017-2026: Value-weighted 12M
  momentum FAILED (D10-D1 = -0.134%/month, t=-0.16). 6M equal-weighted: +0.615%/month
  (positive direction, below significance). 12M momentum is effectively dead in US
  large-cap post-2017.

**Verdict:** 6-month lookback retains more value than canonical 12-month. Long-only
momentum as a quality filter (avoiding bottom quartile) more robust than long-short alpha.

---

## PEAD vs Momentum: The Same Factor?

**The critical question for combined strategies.** Literature is genuinely contested.

**Independence evidence (CJL 1996):**
Chan, Jegadeesh & Lakonishok (1996), JF 51(5):1681-1713. DOI:10.1111/j.1540-6261.1996.tb05222.x.
Both signals independently predict returns after controlling for the other. Combined
top-quintile portfolio: ~2-3% quarterly excess return, higher than either alone.

**Redundancy evidence (stronger weight of evidence):**
- Chordia & Shivakumar (2006), JFE 80(3):627-656. DOI:10.1016/j.jfineco.2005.05.005.
  Earnings momentum fully captures price momentum. Price momentum = noisy proxy for
  earnings momentum. Subsumption is directional.
- Novy-Marx (2015), U. Rochester WP (mysimon.rochester.edu, full text verified).
  Price momentum loses statistical significance once earnings surprise included.
  Earnings momentum unaffected by adding price momentum. Combined filter adds crash
  risk without proportional alpha. Optimal use of price momentum: as EXCLUSION
  criterion to reduce noise, not additive confirmation screen.
- Sadka (2006): Common liquidity risk channel links both anomalies.

**Bottom line:** PEAD and momentum share a common underreaction foundation. Stacking
concentrates the earnings signal + adds crash risk of price momentum. The dual filter
outperforms either alone (CJL) but NOT because they're independent — primarily because
both filters point at the same underlying phenomenon. Position sizing should treat them
as one factor, not two.

---

## Momentum Crashes

Daniel & Moskowitz (2016), JFE 122(2):221-247. DOI:10.1016/j.jfineco.2016.01.009.

**Historical record (long-short momentum):**
- July-August 1932: ~-91.6% drawdown.
- March-May 2009: ~-40% to -73% (long-short). Long-only (MSCI World Momentum): ~-35%.
- March 2020: -28% (similar to broad market). V-shape recovery; less severe.

**Mechanism:** In bear markets, momentum acquires large negative beta. Past-losers are
high-beta; past-winners are low-beta defensives. On sharp market rebound, high-beta
losers surge. Long-only avoids the worst (no short side to blow up) but still badly
underperforms as defensives lag the recovery.

**Forecastability:** Crashes cluster when: (1) prior significant market decline
(negative 12M return) AND (2) elevated VIX. Both observable before crash. Condition
(3) = contemporaneous sharp rebound, which triggers the loss, is NOT forecastable.

**Regime signal (Cooper, Gutierrez & Hameed 2004, JF 59(3):1387-1412):**
- Monthly momentum profit in UP state (positive 3Y market): +0.93%/month.
- Monthly momentum profit in DOWN state (negative 3Y market): -0.37%/month.
The 3-year market return is the most actionable regime-detection signal available.

**Dynamic scaling (Daniel-Moskowitz 2016):** Scaling WML exposure based on predicted
conditional Sharpe (using prior market decline + current vol) approximately DOUBLES
alpha and Sharpe vs static momentum (from ~0.45 to ~0.85).

**Volatility targeting (Barroso & Santa-Clara 2015, "Momentum Has Its Moments"):**
Scaling exposure inversely to strategy's own recent vol significantly improves Sharpe.
Momentum vol RISES before crashes — early warning signal. Implementation: when 21-day
portfolio vol rises >40% above 63-day average, cut all position sizes 50%.

---

## Sector Analysis: Tech / Defense / Homebuilders

**Correlation (PortfoliosLab.com, verified August 6, 2026):**
- XLK vs XHB: 1Y = 0.29, 3Y = 0.40, 5Y = 0.54, 10Y = 0.54. Long-run ~0.54 (material).
- ITA vs XAR: 0.91-0.93 across all periods. Near-perfect substitutes — pick one.

**2022 rate shock performance (key diversification event):**
- XLK: -27.73%
- XHB: -28.93%
- ITA: +9.96%

**Rate sensitivity ranking:**
1. Homebuilders (most): Direct mortgage affordability mechanism. Every +1% in mortgage
   rates reduces buyer qualification ~10%. Rate sensitivity symmetric and fast.
2. Technology (high): Indirect via discount rate / growth-PE duration compression.
   1% real rate rise with 40x PE → ~7% theoretical multiple compression.
3. Defense (lowest): Government-budget-driven revenue. Multi-year obligated contracts.
   Decoupled from consumer credit cycles. ITA +9.96% in 2022 (rate hike year).

**Homebuilder lock-in thesis:** Well-supported.
- FHFA WP24-03 (Batzer et al., 2024): Every +1% rate gap above origination rate reduces
  sale probability 18.1%. Lock-in prevented 1.33M home sales 2022Q2-2023Q4. Supply
  reduction raised home prices +5.7%.
- Fed WP (2025): Lock-in explains 44% of drop in mortgage borrower mobility 2021-2022.
- Philadelphia Fed WP26-33 (July 2026): Buyers more sensitive to rate drops than sellers
  are to lock-in. Rate cuts increase demand more than they release locked-in supply.
Break conditions: (1) rate normalization to ~4% 30Y mortgage narrows the gap; (2)
affordability destruction forces margin-compressing buydowns; (3) overbuilding into
softening demand; (4) demographic slowdown reduces household formation.

**Per-sector PEAD strength (synthesised, no direct cross-sector study found):**
- Mega-cap tech: Effectively zero after 10-20 days. Arbitraged.
- Defense mid-cap: Moderate (lower analyst coverage, genuine contract-award surprise).
- Homebuilders mid-cap: Likely strongest (moderate analyst coverage, order rate/backlog
  data partially predictable but still genuinely surprising quarterly).

---

## Position Sizing Under Correlated Factor Exposures

**The factor correlation problem:**
A 20-stock PEAD+momentum portfolio is NOT 20 independent bets. All positions share:
(1) PEAD factor, (2) price momentum, (3) possibly small-cap, (4) earnings-revision factor.

Portfolio vol formula:
  portfolio_vol = r * sqrt(n * (1 + (n-1)*rho))

For 20 positions, r = 1% per position:
  Normal conditions (rho = 0.2): ~9.8% portfolio vol.
  Factor crash (rho = 0.7):      ~16.9% portfolio vol.

"1% per position" rule effectively becomes 0.8-1.7% portfolio risk per position in a
crash. Treat effective independent bet count as 8-12, not 20.

**Kelly Criterion calibration:**
S&P 500 naive Kelly = 2.2x leveraged (220% of portfolio). Full Kelly always too
aggressive for any realistic investor. Half-Kelly retains ~75% of growth with 50% vol.
For crowded, factor-sensitive momentum: recommended Kelly fraction 0.05-0.20x.
The 0.5-1% dollar risk per position is consistent with extremely conservative Kelly
(well below 0.25x) — this is appropriate given uncertain alpha estimates and shared
factor loading. Do not increase from here.

**Volatility targeting (Barroso-Santa-Clara 2015):** Adjusting momentum exposure based
on the strategy's own realized vol: when 21-day vol rises >40% above 63-day baseline,
cut all sizes 50%. This is the most actionable mechanical crash-protection available.

**Portfolio circuit breaker design:**
Level 1 (>8% drawdown): Pause new entries; tighten all individual stops to 5%.
Level 2 (>15%): Reduce all position sizes 50%; halt new entries.
Level 3 (>20%): Exit all equity; 100% cash. Re-entry: S&P above 200-day MA AND
momentum vol normalized.

Source: CrackingMarkets.com (2025) citing cicfconf.org paper: 10% per-position stop
reduced worst monthly loss from ~50% to ~11% and doubled Sharpe.

---

## Australian Tax Overlay for Active Equity Strategies

**Current rules (pre-July 2027):**
- Short-term (<12M): Taxed at full marginal rate. At $250k income: 47%.
- Long-term (≥12M): 50% CGT discount. Effective rate: 23.5%.
- SMSF short-term: 15%. SMSF long-term: 10% effective (1/3 discount × 15%).
Sources: ATO.gov.au (June 2026), ectd.com.au, smsfaustralia.com.au, trackmyshares.com.

**CGT Reform (Act No. 49 of 2026, Royal Assent 26 June 2026, effective 1 July 2027):**
- 50% discount REPLACED by CPI indexation + 30% minimum tax for personal accounts.
- Grandfathering: pre-1 July 2027 purchases keep 50% discount permanently.
- SMSF/super: EXEMPT from reform. Retains 10% effective long-term CGT rate.
Numerical: $100k nominal gain, 2yr hold, 3% CPI → old $23,500 tax vs new $44,138.
The reform REDUCES the incentive to hold >12M (gap narrows from 23.5pp to ~3pp for
new purchases after 2027), paradoxically making high-turnover active strategies
relatively less disadvantaged vs buy-and-hold post-2027.
Sources: 1july2027.com.au, budget.gov.au, taxtallee.com.au.

**12-month hold tradeoff:**
Tax saving from waiting = gain × 23.5%. Breakeven: position can fall by up to 23.5%
of the GAIN (not total position) before the saving is wiped out.
Rule of thumb:
- Gain >20% of position: Wait for 12M unless signal clearly reversed.
- Gain <10% of position: Redeploy into fresh signal; CGT saving too small.
- Position DOWN: Crystallise loss immediately; no benefit from waiting.

**Trader vs investor classification — HIGH RISK for active momentum strategies:**
ATO uses holistic "badges of trade" test. Typical active PEAD/momentum profile:
- Hold period 30-90 days → TRADER indicator.
- Systematic rules-based approach → TRADER indicator.
- Explicit short-term alpha intent → TRADER indicator.
- ~3-4 trades/month → grey zone (not clearly >20/month).
Risk: ATO likely classifies as trader if audited.
Consequences: Short-term gains unchanged (47% anyway). Long-term gains LOSE the 23.5%
rate. Losses deductible against salary (advantage in loss years).
Mitigation: Maintain separate documented investment + trading accounts. Private binding
ruling from ATO for certainty. Run active portion in SMSF (classification irrelevant —
s295-85 ITAA97: SMSF trading is ALWAYS capital account regardless of frequency).

**SMSF vs personal account per $100k gain:**

  Scenario               | Personal | SMSF  | Saving
  -----------------------|----------|-------|-------
  Short-term (<12M)      | $47,000  | $15,000 | $32,000
  Long-term (≥12M), pre-2027 | $23,500 | $10,000 | $13,500
  Long-term (≥12M), post-2027 new | $44,000 | $10,000 | $34,000

SMSF practical constraints: preservation to age 60, ~$2-5k annual compliance, ~$200k+
minimum effective portfolio for cost-efficiency.

---

## Strategy Rankings (for an Australian investor at 47% marginal rate)

Best to worst on risk-adjusted, after-tax expected value:
1. SMSF + multi-factor ETF (long-term, 10% CGT, zero execution skill, Sharpe ~0.5-0.8)
2. SMSF + disciplined active momentum (10-15% CGT, adds execution risk and alpha)
3. Personal account + factor ETF held >12M (23.5% effective, minimal effort)
4. Personal account + active momentum managed to >12M (23.5% rate, high skill, ATO risk)
5. Personal account + active momentum short-term (47% rate, needs 25%+ gross alpha to beat #3)

---

## Verified Citations Reference List

  Ball & Brown (1968), DOI:10.2307/2490232
  Bernard & Thomas (1989), DOI:10.1016/0165-4101(89)90003-2
  Bernard & Thomas (1990), DOI:10.1016/0165-4101(90)90008-R
  Jegadeesh & Titman (1993), DOI:10.1111/j.1540-6261.1993.tb04702.x
  Jegadeesh & Titman (2001), DOI:10.1111/0022-1082.00342
  Rouwenhorst (1998), DOI:10.1111/0022-1082.95722
  Chan, Jegadeesh & Lakonishok (1996), DOI:10.1111/j.1540-6261.1996.tb05222.x
  Asness, Moskowitz & Pedersen (2013), DOI:10.1111/jofi.12021
  Asness (2011), DOI:10.3905/jpm.2011.37.4.067
  Daniel & Moskowitz (2016), DOI:10.1016/j.jfineco.2016.01.009
  Cooper, Gutierrez & Hameed (2004), DOI:10.1111/j.1540-6261.2004.00665.x
  Chordia & Shivakumar (2006), DOI:10.1016/j.jfineco.2005.05.005
  Hirshleifer, Lim & Teoh (2009), DOI:10.1111/j.1540-6261.2009.01501.x
  Livnat & Mendenhall (2006), DOI:10.1111/j.1475-679X.2006.00196.x
  Ng, Rusticus & Verdi (2008), DOI:10.1111/j.1475-679X.2008.00290.x
  Sadka (2006), DOI:10.1016/j.jfineco.2005.06.001
  McLean & Pontiff (2016), DOI:10.1111/jofi.12365
  Novy-Marx (2015), U. Rochester WP (mysimon.rochester.edu/novy-marx/research/FMFM.pdf)
  Lee (2025), arXiv:2512.11913
  Lesmond, Schill & Zhou (2004), JFE 71(2):349-380
  Han, Zhou & Zhu (2014), SSRN 2407199
  FHFA WP24-03 (Batzer et al.), fhfa.gov/research/papers/wp2403
  Philadelphia Fed WP26-33 (Graybill, Mangum, July 2026)

UNVERIFIED (secondary citations only — do not rely without independent check):
  Chordia, Subrahmanyam & Tong (2014) — large-cap PEAD attenuation
  Geczy & Samonov (2013), SSRN 2292544 — 212yr momentum backtest
  Israel & Moskowitz (2013), JFE 108(2):275-301
  Barroso & Santa-Clara (2015), "Momentum Has Its Moments"
  DellaVigna & Pollet (2009) — Friday earnings PEAD
  Martineau (2022) — "Rest in Peace PEAD"
  Subrahmanyam (2025), SSRN 5930255

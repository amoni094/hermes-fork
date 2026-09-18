# AU Active Momentum Strategy: Alternatives, Execution Drift & Tax Overlay (August 2026)

Research for: Australian investor, ~$250k income, 47% marginal rate.
Strategy: active momentum/PEAD, moderate-to-high turnover, ASX mid-cap focus.
Full output: /tmp/research-cluster3-alternatives-execution-tax.txt

---

## SECTION A — OPPORTUNITY COST / ALTERNATIVES

### S&P 500 Long-Run Sharpe

- Long-run Sharpe (1926–present): ~0.35–0.50 (academic consensus; various secondary sources)
- Nominal gross return: ~10–11% pa; real: ~7.0–7.5% pa
- After-tax (47% marginal, pre-2027 purchase held >12m): ~7.5–8.5% pa net (50% discount + tax deferral)
- Key advantage vs. active: ~5–10% annual turnover defers CGT indefinitely
  → Active momentum at 200%+ turnover forfeits the deferral advantage entirely

### Multi-Factor ETFs — Combined Sharpe

Source: Asness, Moskowitz & Pedersen (2013), JF 68(3), DOI: 10.1111/jofi.12021 (verified):
- Value + momentum combined Sharpe: roughly **DOUBLE** either factor alone across 8 markets/asset classes
- Pairwise V+M correlation: ~−0.50 to −0.60 → near-zero combined risk at equivalent return
- Quality factor (Novy-Marx 2013, JFE): ~0.26%/month excess; negatively correlated with value
- Low-vol/BAB (Frazzini & Pedersen 2014, JFE): Sharpe ~0.75 since 1926 — highest evidence-strength single factor

Multi-factor ETF (e.g., VanEck MSCI Multifactor, VBLD, QUAL+VLUE+MTUM):
- Higher Sharpe than single factor; lower turnover → better tax efficiency than active momentum
- No execution skill required; no earnings-season slippage; no whipsaw stops

### SPIVA Data (S&P Global, Year-End 2024)

- **15-year horizon: ZERO out of 22 U.S. equity categories had majority of active managers outperform**
- 1-year 2024: 65% of large-cap active funds underperformed S&P 500
- Small-cap exception: 70% outperformed in 2024 (best year since SPIVA began)
  → SPIVA authors attribute this to large-cap tilt by small-cap managers, not stock-picking
- Source: ETFTrends.com (March 2025) citing S&P Global SPIVA US Year-End 2024

### Conditions for Active Momentum to Beat Factor ETF

Active momentum wins only when ALL of:
1. Gross alpha >15% (after-cost) to overcome 47% tax at short-term holds
2. Average hold managed to 12m+ (reduces effective rate to 23.5%, same as factor ETF)
3. Capital >$500k–$1M for reasonable execution quality on ASX mid-cap
4. OR: SMSF structure (15%/10% rate makes the threshold far easier to clear)
5. Documented, rules-based discipline sustained through momentum crashes

Cost evidence (Keim & Madhavan 1997; updated AQR 2017):
- Pre-decimalization: small-cap ~7–9%/trade; large-cap ~1–2%/trade
- AQR institutional (2017): large-cap ~0.15–0.35%/trade; small-cap ~0.5–1.0%/trade
  (algorithmic execution; retail adds 5–10x)
- At 200% turnover: annual drag ~2–4% large-cap; ~10–18% small-cap

---

## SECTION B — EXECUTION DRIFT

### PEAD / Earnings Announcement Slippage

Source: Ng, Rusticus & Verdi (2008), JAR 46(3): 661–696, DOI: 10.1111/j.1475-679X.2008.00290.x:
- Transaction costs **significantly reduce PEAD profits** in portfolio analyses
- PEAD profits highest for HIGH transaction-cost firms — but too costly to exploit those firms
- Bid-ask spreads widen 2–3× around earnings announcement times (Lee, Mucklow & Ready 1993)

Practical for ASX mid-cap at earnings:
- Expect +0.5–1.5% additional slippage vs. backtest per trade near announcement dates
- At 30–50 trades/year with ~50% near earnings: ~0.75–1.5% pa additional drag vs. assumptions
- Lesmond, Schill & Zhou (2004): momentum profits for small/illiquid stocks largely disappear
  after realistic costs; large-cap momentum survives

### Trailing Stop Whipsaw

Source: Han, Zhou & Zhu (2014), "Taming Momentum Crashes," SSRN 2407199:
- At **10% stop-loss from month-start price**: average returns INCREASED; Sharpe ratio MORE THAN DOUBLED
- Key: the stop removes crash-period losses without hurting normal momentum signal
- Mechanism: momentum in bear markets behaves like a written call option → stops exit before worst losses

Whipsaw threshold for ASX mid-cap:
- Typical volatility ~30–40% pa = ~2–2.5%/day
- An 8% trailing stop is triggered by ~4 days of adverse moves → WITHIN normal noise
- Recommended: 12–15% trailing stop avoids normal momentum noise while limiting crash exposure
- Tighter than 8% → excess whipsaw; produces more taxable events with no net benefit

Whipsaw tax asymmetry at 47% (investor classification):
- Gain on whipsaw round-trip: taxed at 47% (short-term)
- Loss on whipsaw: only offsets other capital gains, not salary
  → Whipsaw is MORE costly in Australian personal-account context than in zero-tax/lower-tax regimes

### Momentum Crash + Stop Interaction

Source: Daniel & Moskowitz (2016), JFE 122(1): 221–247, DOI: 10.1016/j.jfineco.2015.12.002 (open access):

Crash magnitude:
- July–August 1932: winner decile +32%; loser decile +232% → L/S strategy lost ~200% on spread
- March–May 2009: losers +163%; winners +8% → ~155% spread loss in 3 months (long-only: major drawdown)
- Long-only momentum: ~−30% to −40% drawdown in 2008–2009 typical [UNVERIFIED for ASX]

Mechanism:
- Crashes occur in "panic states": market declined + VIX elevated + sharp market rebound
- Past-loser portfolio beta can rise ABOVE 3.0 following major market declines
- Past-winner portfolio beta can fall BELOW 0.5
- Momentum strategy in bear markets = written call on market (small gain if market falls more;
  large loss when market rebounds sharply)

Stop-crash interaction problem:
- During crash: momentum winner positions are FIRST to trigger trailing stops
  (they've run the most; a 10–15% drop still fires before positions reverse)
- Mass simultaneous exit: all momentum positions exit within days, correlations → 1.0
- In mid-cap names: selling into deteriorating bids while other momentum traders do the same
- Stops "help" by avoiding the worst losses but also:
  (a) Ensure you miss the recovery
  (b) Create concentrated short-term CGT events all at once at 47%
  (c) Re-entry costs when trend resumes

Better alternative (from Daniel & Moskowitz): **dynamic momentum** — scale WML weight down when
prior 3-year market return negative AND VIX elevated; this approximately doubles alpha and Sharpe
vs. static momentum OR blunt trailing stops.

### Backtest vs. Live Performance Decay

Academic consensus:
- Expect 50–66% of gross backtest alpha to survive institutional live trading
  (combining costs, market impact, overfitting, regime change)
- Israel & Moskowitz (2013), JFE 108(2): 275–301: long-side momentum survives costs for large-cap

Practitioner evidence (Glasshouse Research, June 2026, 21 strategies, ~5,000 simulated trades):
- Smart-money-concepts: backtest profit factor 1.22 → live **0.46** (−62%)
- Money-flow long: backtest 1.19 → live **0.11** (over first 10 trades)
- HT momentum: backtest 1.31 → live 1.67 (early small sample, N=7)
- Source: glasshousedesk.com/lab/notes/backtest-vs-live (June 2026)

SGH/EAM "Momentum and Trading Costs" (January 2025 PDF):
- AQR (2017): real-world costs 5–10× LOWER than old academic estimates for large-cap
- But AQR uses algorithmic execution; retail pays 5–10× AQR costs
- Realistic retail momentum Sharpe (long-only, after costs, before tax): ~0.3–0.5

Realistic performance gap for retail momentum at 47% tax:
- Gross backtest alpha: +8–12% pa (J&T 1993 basis)
- After execution costs (mid-cap retail): −2–4% pa
- After overfitting/OOS decay: −2–3% pa
- After Australian 47% tax (short-term holds): −4–6% pa on gains
- **NET REALISTIC LIVE ALPHA vs. INDEX: +0–3% pa** — marginal without structure

---

## SECTION C — AUSTRALIAN TAX OVERLAY

### Current CGT Rules (confirmed via secondary sources, August 2026)

| Hold period     | Marginal rate | Effective rate | Tax on $100k gain |
|-----------------|---------------|----------------|-------------------|
| <12 months      | 47%           | 47.0%          | $47,000           |
| ≥12 months      | 47%           | 23.5%          | $23,500           |
| SMSF <12 months | 15%           | 15.0%          | $15,000           |
| SMSF ≥12 months | 15%           | 10.0%          | $10,000           |

Sources: ATO.gov.au CGT Discount (June 2026 update), ectd.com.au, trackmyshares.com (June 2026).
Capital losses: can ONLY offset capital gains (not salary) for investors; carry forward indefinitely.
$250k annual cap on CGT discount (from 2024): gains above $250k/year get reduced discount. [UNVERIFIED mechanics above cap]
12-month rule: exactly 12 calendar months + 1 day (e.g., buy 1 March 2025 → sell on or after 2 March 2026).

### 12-Month Hold Tradeoff: When to Wait vs. Exit

Tax saving from extending hold to 12 months per $100k gain = **$23,500** (47% − 23.5%).

The position can fall by UP TO 23.5% of the gain before the tax saving is wiped out.
- Example: $100k cost → $130k value (gain = $30k)
  - Tax saving from waiting: $30k × 23.5% = $7,050
  - Position can fall to $123k (−5.4% from $130k) before saving is lost
  
Momentum signal decay complication:
- Jegadeesh & Titman (1993): momentum alpha concentrates in months 3–12; REVERSAL begins 12–36m
- PEAD drift: typically complete within 60–90 days of announcement
  → Holding 9–12 months to capture CGT discount likely means holding through signal fade

**Practical rule**:
- Gain >20% of cost base AND within 3 months of 12m mark → hold unless signal fully reversed
- Gain <10% of cost base → tax saving modest; redeploy to fresh signal
- Position in loss → no CGT saving; crystallise loss immediately (offset other gains)

### Post-July 2027 Reform (Act No. 49 of 2026, Royal Assent 26 June 2026)

Key facts confirmed from multiple sources (1july2027.com.au, simplesalarycalculator.com.au, taxtallee.com.au, navexa.com):

- **50% CGT discount REPLACED** for new acquisitions after 1 July 2027 with:
  1. CPI indexation of cost base (only REAL gain is taxable)
  2. **30% minimum tax floor** on the indexed gain
- Applies to: individuals, trusts, partnerships
- **GRANDFATHERED (SHARES)**: shares purchased before 1 July 2027 keep 50% discount forever regardless of when sold
- **SMSF EXEMPT**: super funds retain existing CGT settings under Act No. 49 of 2026

Impact on new purchases after 1 July 2027 at 47% marginal rate:
- Short-term (<12m): UNCHANGED at 47%
- Long-term (≥12m): OLD effective rate 23.5% → NEW effective rate ~44–47% (CPI indexation
  reduces taxable gain by inflation only; no 50% discount; at 47% MTR, the 30% floor doesn't bind)
  
Example ($100k gain held 2 years, 3% annual CPI, post-2027 rules):
- Indexed cost: $100k × 1.0609 = $106,090 → real gain = $93,910
- Tax: $93,910 × 47% = $44,138 (vs. OLD $23,500) → extra $20,638 per $100k gain

**Strategic implications for active momentum post-2027**:
- 12-month hold incentive SHRINKS dramatically for new purchases:
  Short-term 47% vs. long-term ~44% → minimal incentive to hold to 12m (unlike old 47% vs 23.5%)
- Perversely, the reform makes high-turnover active strategies LESS disadvantaged vs. buy-and-hold
  for NEW positions purchased after July 2027
- But grandfathered positions (bought before July 2027) still have 23.5% long-term rate → manage these carefully
- SMSF advantage INCREASES substantially post-reform: SMSF retains 10% vs. personal ~44% for new long-term gains

### ATO Trader vs. Investor Classification — Applied to PEAD/Momentum Strategy

**Risk assessment for this strategy: HIGH RISK of trader classification**

ATO "badges of trade" test (holistic; no single factor decisive):
Source: ATO.gov.au (share-investing-versus-share-trading, June 2026), ectd.com.au, trackmyshares.com

Key factors applied to active PEAD/momentum strategy:

| Factor | This Strategy | Signal |
|--------|---------------|--------|
| Frequency | 30–50 trades/year (~3–4/month) | Grey zone (not clearly >20/month) |
| Hold period | 30–90 days average | TRADER indicator |
| Profit motive | Systematic exploitation of short-term price reaction | TRADER indicator |
| Organisation | Written rules, screening, analysis time, documented | TRADER indicator |
| Capital/scale | $250k with 200%+ turnover = ~$500k gross trades | Borderline |

**Consequences of trader classification**:
- All profits taxed as ordinary income at 47% — same as short-term CGT anyway → neutral for short holds
- **CRITICAL LOSS**: 50% CGT discount destroyed on any 12m+ positions you worked to hold
  → This eliminates the 12m hold strategy entirely if classified as trader
- Capital losses CAN offset salary (advantage in loss years)
- Trading expenses deductible (platform fees, data, home office)

**Net impact**: If strategy is mostly short-term, trader classification is roughly neutral.
If deliberately managing some positions to 12m+ for CGT discount, trader classification DESTROYS that strategy.

**Mitigation**:
- Private binding ruling from ATO (free) — gives legal certainty before classification dispute
- Keep long-term investment portfolio (ETFs, large-cap holds) as a DOCUMENTED SEPARATE account
  from the active trading portfolio — allows mixed classification
- Per ectd.com.au: "For most casual traders (fewer than 10 trades per month, holding period over 6 months), ATO treats as investor"
- Note: ATO does NOT use a rigid "4-factor test" codification; test is holistic/common law badges of trade

**SMSF resolution**: by statute (s295-85 ITAA97), SMSF share trading is ALWAYS capital account
regardless of frequency — no trader/investor ambiguity applies inside SMSF.

### SMSF as a Vehicle: Quantified Comparison

SMSF accumulation phase rules (confirmed: smsfaustralia.com.au, ato.gov.au, presm.com):
- Income tax: 15% flat
- CGT short-term (<12m): 15%
- CGT long-term (≥12m): 1/3 discount → 10% effective rate (2/3 × 15%)
- CGT pension phase: 0% (entirely tax-free)
- Post-2027: SMSF EXEMPT from reform (retains 10% long-term rate)

**Scenario comparisons ($100k gain)**:

Short-term trade:
- Personal: $47,000 tax → $53,000 net
- SMSF: $15,000 tax → $85,000 net
- **Saving: $32,000**

Long-term (≥12m) pre-2027 rules:
- Personal: $23,500 tax → $76,500 net
- SMSF: $10,000 tax → $90,000 net
- **Saving: $13,500**

Long-term (≥12m) post-2027 new purchases:
- Personal: ~$44,000 tax → ~$56,000 net
- SMSF: $10,000 tax → $90,000 net
- **Saving: ~$34,000** (SMSF advantage grows post-reform)

**Compounding estimate on $250k active portfolio** (rough, [UNVERIFIED]):
- Assume 200% turnover, 10% avg gain → $50k annual short-term gains
- Personal: $50k × 47% = $23,500 tax/year
- SMSF: $50k × 15% = $7,500 tax/year
- Annual saving: ~$16,000 → over 10 years compounded ~$230k+

SMSF practical constraints:
- Cannot access until preservation age (60 for most born post-1964)
- Annual compliance: ~$2,000–$5,000 admin/audit
- Minimum effective portfolio: ~$200k+
- Division 296 tax (from 1 July 2026): applies to TSB >$3M → not relevant at $250k scale

Additional dividend advantage: fully franked dividends in SMSF → 15% credit refund vs.
17% additional tax in personal account at 47%.

---

## STRATEGY RANKING (after-tax, after-costs, for this investor)

1. **SMSF + factor ETF** (long-term, 10% CGT, no execution risk) — BEST
2. **SMSF + disciplined momentum** (10–15% rate, adds alpha opportunity + execution risk)
3. **Personal + factor ETF held >12m** (23.5% rate, minimal effort)
4. **Personal + active momentum managed to >12m** (23.5% rate, high skill + ATO classification risk)
5. **Personal + active momentum short-term** (47% rate, very high gross alpha required to justify)

---

## KEY SOURCES

Academic (verified):
- Jegadeesh & Titman (1993), JF 48(1): 65–91
- Asness, Moskowitz & Pedersen (2013), JF 68(3), DOI: 10.1111/jofi.12021
- Novy-Marx (2013), JFE — quality factor
- Frazzini & Pedersen (2014), JFE — BAB Sharpe ~0.75
- Daniel & Moskowitz (2016), JFE 122(1): 221–247, DOI: 10.1016/j.jfineco.2015.12.002
- Han, Zhou & Zhu (2014), SSRN 2407199 — stop-loss doubles momentum Sharpe
- Ng, Rusticus & Verdi (2008), JAR 46(3): 661–696 — PEAD + transaction costs
- Lesmond, Schill & Zhou (2004), JFE 71(2): 349–380
- Keim & Madhavan (1997) — trading cost estimates by cap tier

SPIVA:
- S&P Global SPIVA US Year-End 2024 (via ETFTrends.com March 2025)

Practitioner:
- AQR (2017) "Implementing Momentum: What Have We Learned?" (cited in SGH/EAM Jan 2025 PDF)
- SGH Hiscock/EAM "Momentum and Trading Costs" (Jan 2025)
- Glasshouse Research backtest-vs-live data (June 2026)

Australian Tax (secondary sources — ATO.gov.au frequently anti-bot blocked):
- Act No. 49 of 2026, Treasury Laws Amendment (Tax Reform No. 1) Act 2026 (Royal Assent 26 June 2026)
- 1july2027.com.au, simplesalarycalculator.com.au, taxtallee.com.au, navexa.com (May–August 2026)
- smsfaustralia.com.au, ectd.com.au, trackmyshares.com (June 2026)
- ATO.gov.au CGT Discount + Share investing vs. trading pages (June 2026)

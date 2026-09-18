# ASX / Australian Investing — Domain Knowledge Bank

*Verified July 2026. Not financial advice.*

---

## ASX Data Access

### yfinance ticker format
- Append `.AX` to ASX ticker symbol: `CBA.AX`, `BHP.AX`, `WBC.AX`, `WES.AX`
- Full ASX200 components accessible
- Intraday data available (1m to 1h) but subject to Yahoo rate limits
- **Caveat**: Yahoo Finance data has gaps, survivorship bias issues, and rate limits.
  Not suitable as sole source for production live trading.

### ASX market hours
- 10:00–16:00 AEST (UTC+10 standard, UTC+11 during DST Oct–Apr)
- Pre-open auction: 07:00–10:00 AEST
- No overnight session

### Broker APIs with ASX access
| Broker | API | Notes |
|--------|-----|-------|
| Interactive Brokers (IBKR) | Python (ib_insync), Java | Best programmatic access; supports ASX |
| CMC Markets | Proprietary algo order types | 2500+ ASX instruments; institutional tools |
| SelfWealth | Limited API | Retail; no algo capabilities |
| CommSec | No public API | Consumer only |

### Data sources
- **Free**: yfinance (.AX suffix), OpenBB Terminal (Yahoo Finance integration)
- **Paid**: ASX Online Data (asxonlinedata.com.au), Refinitiv/LSEG Eikon, Bloomberg
- **Tick data**: Not freely available; must be purchased or obtained from broker

---

## Australian Tax Context for Investors (2024–25)

### Personal income tax brackets (post Stage 3 cuts)
| Taxable Income | Rate (excl. Medicare) |
|----------------|----------------------|
| $0–$18,200 | 0% |
| $18,201–$45,000 | 19% |
| $45,001–$120,000 | 30% |
| $120,001–$190,000 | 37% |
| $190,001+ | 45% |

**Medicare Levy**: +2% on all income
**Medicare Levy Surcharge**: +1.0–1.5% for singles earning >$97k without private hospital cover

**At $250k gross income**: marginal rate = 47% (45% + 2% Medicare)

### Capital Gains Tax (CGT) discount
- **Assets held ≥12 months**: 50% CGT discount → effective rate 22.5% at 47% marginal
- **Assets held <12 months**: full marginal rate (47%) applies
- **In super**: 10% effective CGT (15% flat less one-third discount for assets >12 months)
- **Key implication**: Short-term trading (<12 months) at $250k income faces 47% tax on every dollar of gain — enormously high hurdle vs. buy-and-hold index investing

### Franking credits
- ASX companies paying fully-franked dividends have already paid 30% company tax
- Franking credit offsets personal tax on that dividend income
- **High-income earner (47% marginal)**: receives partial offset — net dividend tax ~17%
- **Inside SMSF/super (15% tax)**: franking credits often fully offset the 15%, near-zero tax on dividends
- **Key ASX stocks with full franking**: CBA, WBC, ANZ, NAB (banks), WES (Wesfarmers), WOW (Woolworths), BHP
- **45-day holding rule**: Must hold shares for 45+ days (90 for preference shares) to claim franking credits

### Superannuation
- **Concessional (pre-tax) cap**: $30,000/year (FY2024–25), includes employer SG contributions
- **Tax rate inside super**: 15% (vs up to 47% personal)
- **Division 293 tax**: If income + concessional super > $250,000, extra 15% tax on contributions (total 30% — still better than 47%)
- **Carry-forward rule**: Unused concessional cap from past 5 years (if super balance < $500k) can be used in current year — enables "catch-up" contributions
- **Non-concessional cap**: $120,000/year (after-tax); grows at 15% tax rate

### SMSF (Self-Managed Super Fund)
- Same 15% tax rate as retail super during accumulation phase
- Greater control: can hold individual ASX shares, ETFs, property, international
- **Pension phase** (after preservation age): 0% tax on income and capital gains
- **Setup/running costs**: ~$1,500–$3,000/year (SMSF auditor, accounting, ASIC)
- **Recommended minimum balance**: $200–500k for SMSF costs to be worthwhile
- **Best use**: Hold high-franking ASX dividend stocks — franking credits nearly eliminate the 15% tax; also very effective for assets expected to grow significantly (CGT in pension phase is zero)

### Negative gearing
- Investment property losses deductible against total income at marginal rate
- Example: $7k rental loss × 37% marginal rate = $2,590 tax saving
- Combined with building depreciation can be substantial for new properties

### CGT management techniques
- Hold assets >12 months for 50% CGT discount
- Realise losses in same year to offset gains (loss harvesting)
- Time sales in lower-income years (career break, sabbatical)
- Use super for high-growth assets to shelter CGT

### Family trust / investment company
- Can split investment income to lower-bracket beneficiaries (e.g. non-working spouse)
- Setup: ~$1,500–$3,000/year ongoing
- Corporate tax rate: 30% (or 25% for base-rate entities) — lower than top marginal rate

---

## Australian Reddit Communities

| Community | Focus | Character |
|-----------|-------|-----------|
| r/AusFinance | Personal finance, budgeting, investing, super | Conservative; index-fund dominant; anti-active-trading bias |
| r/ausstocks | ASX-specific stock picks and discussion | More speculative than r/AusFinance |
| r/ASX | Broader ASX community, sector discussion | Mix of fundamentals and speculation |
| r/ASX_Bets | Australian WallStreetBets equivalent | High-risk, meme stocks, "yolo" energy |
| r/fiaustralia | Financial independence / FIRE community | DCA/index/super focused; long-term only |

### r/AusFinance community consensus (as of 2024–2026)
- Short-term investing (<3 years): HISA, term deposits, no ETFs/shares
- Medium-term: ETF DCA (VAS + VGS) via Vanguard/Betashares/Pearler
- Short-term stock trading: consistently discouraged
- "Just buy VAS and VGS" is the dominant advice
- SMSF discussion growing but still specialist territory

---

## Australian Algo Trading Landscape

- **No Australian-specific open-source algo trading community exists** at significant scale
- International tools dominate; the Australian edge is:
  - ASX data via yfinance (.AX suffix)
  - IBKR or CMC Markets for execution
  - Australian tax optimization as a strategic lever
- **CMC Markets** provides algorithmic order types for 2500+ ASX instruments at 0.033% per trade

### ASX-specific strategy considerations
- ASX is smaller/less liquid than US markets; wider spreads on small-caps
- Bank pairs (CBA/WBC, ANZ/NAB) popular for statistical arbitrage
- Mining/resources sector offers momentum plays on commodity cycles
- Blue-chip dividend capture (CBA, WES, BHP) effective in SMSF structures
- Sector rotation (materials → financials → consumer) on 3–6 month cycles has community backing
- Day trading with <$500k capital: transaction costs, spreads typically kill returns

---

## Practical Summary for High-Income Earner ($250k+, $100–200k to invest)

1. **Superannuation first**: Max concessional contributions to $30k cap (salary sacrifice). Reduces taxable income; grows at 15%.
2. **Division 293 warning**: Already triggered at $250k if maxing contributions — plan for 30% effective rate on super contributions (still 17pp better than marginal rate).
3. **Short-term trading tax drag**: 47% effective rate on gains. Every $10k gain costs $4,700. Need >5% alpha just to match after-tax index fund returns.
4. **SMSF when balance warrants it**: At $200k+ in super, SMSF gives direct ASX control + franking credit harvesting.
5. **Hold period matters enormously**: If trading, try to structure positions to exceed 12-month threshold for 50% CGT discount.
6. **Active trading: small speculative allocation**: Keep active/short-term trading to ~10–15% of total capital; treat as a learning/entertainment cost, not core wealth strategy.
7. **Engage a tax accountant** who specialises in investors — the interplay of Division 293, catch-up contributions, SMSF, and CGT is complex.

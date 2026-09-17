# Technical Trading Strategies — English-Language Academic Reference Bank
*Session: August 2026 — English-language sweep of technical/chart-based trading strategies*
*Purpose: Comparison vs. PEAD+momentum baseline (Slava's strategy)*
*Baseline: Jegadeesh-Titman (1993) 6/6 momentum ~12% gross pa; Bernard-Thomas (1989) PEAD 4.2% CAR 60-day; AU net 0–3% pa at 47% marginal tax*

---

## Access notes specific to this sweep

| Source | Status | Notes |
|---|---|---|
| **SSRN (papers.ssrn.com)** | ❌ Anti-bot on most pages | Use web_search to confirm DOI + abstract; only some SSRN pages load via web_extract |
| **ScienceDirect / Elsevier** | ❌ Anti-bot | Use author-hosted PDFs (lhpedersen.com, lse.ac.uk/polk, amoreira2.github.io) |
| **Journal of Portfolio Management (pm-research.com)** | ❌ Paywall | DOI confirmed but full text locked; key stats verified via open working-paper PDFs |
| **Wiley Online Library** | ❌ Anti-bot | Access via author-hosted PDFs (e.g. amoreira2.github.io for Moreira-Muir 2017) |
| **Author-hosted PDFs** | ✅ Usually accessible | AQR staff (fairmodel.econ.yale.edu/ec439/hurst.pdf), LSE (personal.lse.ac.uk/polk), FRBNY (newyorkfed.org), emanuelmoench.com |
| **AQR working papers (stoictrading.wordpress.com mirror, fairmodel.econ.yale.edu)** | ✅ Full text | AQR papers reliably mirrored on academic hosting sites |
| **arXiv (arxiv.org)** | ✅ Full access | HTML abs page + PDF both work via web_extract |
| **arXiv search for indicator names (RSI, MACD, Bollinger)** | ❌ Returns 0 results | arXiv full-text search does NOT index these as keywords — see pitfall below |
| **tradicted.com summaries** | ✅ Reliable secondary | High-quality stats-accurate summaries of primary papers; use for verification cross-check |
| **econpapers.repec.org** | ✅ Abstract + DOI confirmed | Reliable for JFE/JF paper metadata |

---

## Verified primary papers quick-reference

| Strategy | Paper | DOI / arXiv | Key quantified result | Verification status |
|---|---|---|---|---|
| **Short-term reversal (RSI analog)** | Jegadeesh, N. (1990). "Evidence of Predictable Behavior of Security Returns." JF 45(3):881–898. | DOI: 10.1111/j.1540-6261.1990.tb05110.x | Prior-month loser–winner reversal: ~2%/month, 1934–1987; Sharpe not reported in original | ✅ DOI confirmed via multiple sources; stats from secondary summaries |
| **Bollinger Bands** | Fang, J., Jacobsen, B., & Qin, Y. (2017). "Popularity vs. Profitability: Evidence from Bollinger Bands." JPM 43(4):152–159. | DOI: 10.3905/jpm.2017.43.4.152 | Pre-1983: positive buy–sell spread across 14 international markets. Post-2001: **returns mostly negative** on S&P 500; alpha largely destroyed. | ✅ DOI confirmed via pm-research.com page; paper content confirmed via open working paper (acfr.aut.ac.nz PDF) |
| **Bollinger Bands (working paper)** | Fang, J., Jacobsen, B., & Qin, Y. (2014 working paper, same authors, longer version). Massey University / Edinburgh. | No published DOI — working paper only | 14-market international sample; full buy–sell spread statistics across full sample + 3 sub-samples (pre-1983, 1983–2001, post-2002) | ✅ Full text directly accessed (acfr.aut.ac.nz PDF); quantified buy–sell spreads vary by market and period |
| **Breakout / time-series momentum** | Moskowitz, T.J., Ooi, Y.H., & Pedersen, L.H. (2012). "Time Series Momentum." JFE 104(2):228–250. | DOI: 10.1016/j.jfineco.2011.11.003 | Diversified 58-contract futures portfolio: annualised excess return ~14.9%, Sharpe ~1.28 (vol-targeted 10% vol), 1985–2009 | ✅ Full text accessed (docs.lhpedersen.com); confirmed JFE 2012 |
| **Trend-following (century evidence)** | Hurst, B., Ooi, Y.H., & Pedersen, L.H. (2017). "A Century of Evidence on Trend-Following Investing." JPM 44(1):15–29. | DOI: 10.3905/jpm.2017.44.1.015 [UNVERIFIED open-access — inferred from journal page; paper confirmed JPM Fall 2017 Vol 44 No 1] | Full sample (1903–2016): Gross ~20% pa at 10% vol target; Net of 2/20 fees ~14.3% pa; **Sharpe net of fees ~1.00**. Decade-by-decade positive in every decade. | ✅ Full text accessed (fairmodel.econ.yale.edu/ec439/hurst.pdf + stoictrading.wordpress.com/wp-content mirror). Exhibit 1 performance table extracted. |
| **Moving average crossover** | Brock, W., Lakonishok, J., & LeBaron, B. (1992). "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns." JF 47(5):1731–1764. | DOI: 10.1111/j.1540-6261.1992.tb04681.x | VMA buy-signal days: avg daily return 0.042% (~12% pa); sell-signal days: avg daily return –0.025% (~–7% pa); buy–sell spread ~19% pa in-sample. DJIA 1897–1986. | ✅ DOI confirmed (Wiley + EconPapers); stats confirmed via tradicted.com and multiple academic citations |
| **Volatility-managed portfolios** | Moreira, A., & Muir, T. (2017). "Volatility-Managed Portfolios." JF 72(4):1611–1644. | DOI: 10.1111/jofi.12513 | Market vol-managed: alpha **4.9% pa**; appraisal ratio 0.33; **25% increase in Sharpe vs buy-and-hold**. Works for market, value, momentum, profitability, ROE, investment, BAB, and currency carry factors. | ✅ Full text directly accessed (amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf). Exact numbers confirmed from abstract. |
| **Volatility-managed portfolios (update)** | DeMiguel, V. et al. (2024). "A Multifactor Perspective on Volatility-Managed Portfolios." JF (Oct 2024). | DOI: 10.1111/jofi.13395 | Multifactor MVE: Sharpe rises from 1.441 to 1.735 with vol timing. Extends Moreira-Muir. | ✅ DOI confirmed (Wiley); stats from abstract confirmed via lbsresearch PDF |
| **Pre-FOMC overnight drift** | Lucca, D.O., & Moench, E. (2015). "The Pre-FOMC Announcement Drift." JF 70(1):329–371. | DOI: 10.1111/jofi.12196 | S&P 500: avg +49 bp in 24h pre-FOMC; ~80% of annual equity excess returns since 1994; **annualised Sharpe ≥1.1** for pre-FOMC-only strategy. 8 events/year. | ✅ Full text directly accessed (emanuelmoench.com PDF). Exact figures confirmed from paper body. |
| **Overnight/gap — tug of war** | Lou, D., Polk, C., & Skouras, S. (2019). "A Tug of War: Overnight versus Intraday Expected Returns." JFE 134(1):192–213. | DOI: 10.1016/j.jfineco.2019.03.011 | Overnight winner–loser decile spread: 3-factor overnight alpha **3.47%/month** (t=16.83); intraday: –3.02%/month (t=–9.74). Momentum profits earned **entirely overnight**. | ✅ Full text accessed (personal.lse.ac.uk/polk/research/TugOfWar.pdf). Confirmed JFE 134(1). |
| **Overnight drift (microstructure)** | Boyarchenko, N., Larsen, L.C., & Whelan, P. (2020, rev. 2022). "The Overnight Drift." FRBNY Staff Report No. 917. | SSRN: 10.2139/ssrn.3546173 [Working paper — no journal DOI confirmed as of 2022 version] | S&P 500 e-mini: 2:00–3:00 AM ET window avg **3.7% pa** (1.48 bp/day); statistically significant in 20/23 years 1998–2020. | ✅ Full text accessed (newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf). |
| **Post-publication decay (cross-strategy)** | McLean, R.D., & Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" JF 71(1):5–32. | DOI: 10.1111/jofi.12365 | 97 predictors: portfolio returns **26% lower OOS** and **58% lower post-publication** vs in-sample. | ✅ DOI confirmed (JF Vol 71 Issue 1 Feb 2016 at afajof.org; JSTOR 43869094). |
| **Trend-following (analytical framework)** | Sepp, A., & Lucic, V. (2026). "The Science and Practice of Trend-Following Systems." arXiv:2607.19497 [q-fin.ST]. | arXiv: 2607.19497; DOI: 10.48550/arXiv.2607.19497 | Closed-form Sharpe ratio for TF systems; empirical evaluation on 84 liquid contracts 1959–2026. Submitted July 2026 — empirical numbers in full paper body, not abstract. | ✅ arXiv abs page confirmed. Full empirical results not extracted from abstract alone. |
| **Baseline: price momentum** | Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers." JF 48(1):65–91. | DOI: 10.2307/2328882 | 6M/6M strategy: **~12.01% annualised excess return** (1965–1989). Reversal starts ~month 12. | ✅ Full text (bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf) — see existing trading-strategy reference file |

---

## arXiv search failure: technical indicator names

**Critical pitfall for this domain**: arXiv full-text search (`https://arxiv.org/search/?searchtype=all&query=TERMS`) returns **0 results** for queries using technical indicator names as keywords:

- `RSI mean reversion equity strategy` → 0 results
- `RSI relative strength index equity trading` → 0 results
- `Bollinger Band trading strategy equity` → likely same failure

**Why**: arXiv's search indexes title, abstract, and a few metadata fields. Technical indicators like "RSI", "MACD", "Bollinger" are not standard academic terminology in q-fin papers, which use terms like "mean reversion", "contrarian strategy", "short-horizon reversal", "technical analysis". The indicator names appear in the body text, not indexed fields.

**Working alternatives for this domain**:
1. Use web_search with `site:arxiv.org q-fin [academic terms]` (e.g. "mean reversion contrarian equity signal q-fin")
2. Search SSRN directly: `site:ssrn.com [strategy name] returns Sharpe`
3. Use Google Scholar via Semantic Scholar API (no anti-bot) for cross-validation
4. Look for the strategy under its academic label: RSI → "short-term reversal" / "contrarian strategy"; Bollinger → "price channel breakout" / "technical trading rules"; MA crossover → "moving average technical trading rules"

---

## Strategy-specific fabrication risk areas (technical trading)

**High-risk for hallucination in this domain:**

1. **Paywalled Sharpe/alpha figures**: Most technical trading papers (JF, JFE, RFS) are paywalled. A specific Sharpe number (e.g. "Bollinger Bands Sharpe 0.87") that can't be confirmed from an author-hosted PDF should be flagged [UNVERIFIED]. The abstract alone rarely contains the Sharpe; it's in a results table.

2. **Post-publication decay quantification**: Papers often state "alpha has decayed" or "strategy no longer profitable" — always trace this to a specific secondary paper (e.g. McLean-Pontiff 2016) rather than asserting it as general knowledge. The specific % decay by strategy is rarely stated in abstracts.

3. **DOIs for JPM papers**: Journal of Portfolio Management (pm-research.com) DOIs are format `10.3905/jpm.YYYY.VV.N.PP`. These can be confirmed via the journal's own page even when the full text is paywalled. Don't assert a JPM DOI from memory — it's a fabrication risk.

4. **RSI-specific primary papers**: No top-tier (JF/JFE/RFS/JPM) paper with a rigorous quantified Sharpe for standalone RSI(14) overbought/oversold equity strategy was found in this sweep. Claims about "RSI Sharpe = X" from SSRN working papers should be clearly distinguished from peer-reviewed results.

5. **Hurst et al. (2017) performance numbers**: The full performance table (Exhibit 1) is in the paper body, not the abstract. The key extractable numbers are: Gross ~20% pa, Net of 2/20 ~14.3% pa, Sharpe net ~1.00 for full 1903–2016 sample. Don't cite decade-by-decade Sharpe from memory — each decade differs substantially (range 0.66–1.45+).

---

## Strategy comparison vs. PEAD+momentum baseline (for AU investor at 47% marginal tax)

Summary of net alpha relative to Slava baseline (AU net 0–3% pa):

| Strategy | Best academic source | Gross Sharpe | AU-comparable net | Position vs. baseline |
|---|---|---|---|---|
| Time-series momentum / trend-following | Moskowitz et al. 2012; Hurst et al. 2017 | ~1.0–1.28 | ~8–14% pa (net 2/20 fees) but requires multi-asset futures | Above baseline in multi-asset; equity-only harder to implement |
| Volatility-managed portfolios | Moreira & Muir 2017 | +25% Sharpe improvement | +3–4% pa alpha net | Complementary overlay — combine with Slava |
| Pre-FOMC drift | Lucca & Moench 2015 | ≥1.1 | Low-turnover, AU-friendly | Complementary — 8 events/year; reduces AU tax drag |
| MA crossover | Brock et al. 1992 | High in-sample | ~2–5% pa modern | Below baseline post-cost in modern regime |
| Overnight drift | Boyarchenko et al. 2020 | N/A as standalone | ~3.7% pa | Below baseline as standalone |
| Short-term reversal (RSI analog) | Jegadeesh 1990 | High gross | Very low net (high turnover) | Below baseline after costs |
| Bollinger Bands | Fang et al. 2017 | Negative post-2001 | Negative in developed markets | Well below baseline; alpha destroyed |

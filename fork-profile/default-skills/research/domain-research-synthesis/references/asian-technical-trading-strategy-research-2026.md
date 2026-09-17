# Asian Markets Technical Trading Strategy Research
## China (A-Share), Japan (Nikkei/TSE), Korea (KOSPI/KSC)
### Research date: August 2026 | Subagent multilingual sweep

---

## KEY STRUCTURAL FINDING

**Price momentum continuation (the dominant US alpha) FAILS or reverses in China, Japan, and Korea. Mean reversion and contrarian strategies are the structurally supported approach in all three markets.**

This is the single most important cross-market divergence from US evidence. The Slava PEAD+momentum baseline of 0–3% net pa is likely the *ceiling*, not the floor, for Asian markets if naive momentum strategies are applied.

---

## BASELINE FOR COMPARISON

Slava = PEAD + price momentum, AU context → **~0–3% net p.a.** excess return (after costs/taxes).

---

## CHINA (A-Share Market)

### Market structure
- ~70–80% retail participation by volume (vs ~15–20% in US)
- High speculative turnover — turnover rates 3–5× US equivalents
- State ownership ~40–50% of listed shares (constrains float)
- Herding behaviour extensively documented (Christie-Huang CSAD elevated)
- **Split-Share Structure Reform (2005)** was a structural break that destroyed pre-2005 momentum

### Verified papers

#### 1. Zhang & Zi (2025) — SJTU/SAIF working paper
- **Source:** Shanghai Advanced Institute of Finance (SAIF), Shanghai Jiao Tong University (SJTU)
- **URL:** https://czi.finance/assets/ChinaMom.pdf
- **Market/period:** China A-share, Jan 1998 – Jun 2024
- **Method:** 6-6 Jegadeesh-Titman momentum portfolios; model of informed/uninformed/noise traders

| Period | Strategy | Annual Return |
|--------|----------|---------------|
| Jan 1998 – Sep 2005 | 6-6 momentum (all stocks) | +11.5% p.a. (t-stat significant) |
| Oct 2005 – Jun 2024 | 6-6 momentum (all stocks) | ~0% to negative; cumulative −78.4% peak-to-trough |
| Post-reform, SASAC-controlled firms | 6-6 momentum | **−6.3% p.a.** (anti-momentum) |
| Post-2005, noise-filtered (exclude high-vol/turnover stocks) | 6-6 momentum | **+8.2% p.a.** (recoverable) |

- **Mechanism:** Split-Share Reform → major shareholders become contrarian (buy losers, sell winners) → destroys continuation
- **Key finding:** Pure momentum fails post-2005. Noise-filtered momentum recovers to 8.2% pa. State-controlled firm stocks are *anti-momentum* by statute (SASAC controls).
- **vs Slava baseline:** Pre-reform +11.5% >> baseline; post-reform flat to negative << baseline; noise-filtered +8.2% > baseline but requires complex filtering

#### 2. Weng (2026) — Renmin University, arXiv 2607.27063
- **Source:** Department of Physics, Renmin University of China
- **arXiv ID:** 2607.27063 [q-fin.TR], July 2026
- **URL:** https://arxiv.org/abs/2607.27063
- **Method:** Agent-based network model; von Neumann/Moore lattice herding; information diffusion; empirical CSAD/LSV application to A-share

**Key findings:**
- Herding + delayed information diffusion → momentum-then-overshooting-then-REVERSAL (not continuation)
- Stronger herding → larger price fluctuations, more excess kurtosis
- CSAD/LSV measures rise during major market disruptions (consistent with herding driving reversals)
- Theoretical mechanism: cascade following gives short-term price continuation, but decay of herding + residual information → correction

**vs Slava baseline:** Mechanistic support for mean-reversion in A-shares. No directly tradeable Sharpe reported.

#### 3. Du (2025) — USTC, arXiv 2506.06356
- **Source:** University of Science and Technology of China (USTC); sa613403@mail.ustc.edu
- **arXiv ID:** 2506.06356 [cs.CE], June 2025
- **URL:** https://arxiv.org/abs/2506.06356
- **Train period:** 2010–2020; **Backtest:** 2021–2024
- **Strategy:** DL cross-sectional prediction + opening gap arbitrage + multi-granularity volatility timing

| Metric | Value |
|--------|-------|
| Annualised return (backtest) | **15.2% p.a.** |
| Sharpe ratio | **1.87** |
| Maximum drawdown | **<5%** |
| Daily positions | 50–100 |
| Max holding | 9 days |

- **Technical features used:** Momentum across 5/10/20/60-day horizons, mean reversion signals, volatility measures, volume indicators + fundamental (valuation, growth, profitability)
- **⚠️ Caveat:** Backtest only (2021–2024); DL complexity makes live replication difficult; no formal out-of-sample data snooping test
- **vs Slava baseline:** Claims far exceed baseline but backtest-only; [UNVERIFIED as live result]

#### 4. Pu (2024) — SWUFE, conference paper
- **Source:** Southwestern University of Finance and Economics (SWUFE), Chengdu
- **Published:** Highlights in Business, Economics and Management, PGMEE 2024, Vol. 41 pp. 42–48
- **URL:** https://pdfs.semanticscholar.org/00a5/58ea59f06dada36301695c8bc3186c9737a2.pdf
- **Period:** Sep 2005 – Dec 2022 (208 months)

**Key findings:**
- **Short-term (1-month) reversal** confirmed in high-turnover A-share stocks
- Q-factor model fails to explain this anomaly
- Mechanism: individual investors → momentum chase → overreaction; institutions arbitrage mispricing → reversal
- IHCR (Institutional Holding Change Ratio) factor = positive excess returns

**vs Slava baseline:** Directionally positive for mean-reversion strategies. Magnitude [UNVERIFIED — no Sharpe in accessible text].

#### 5. Zhang, Li & Dai (2025) — EWA Publishing
- **DOI:** https://doi.org/10.54254/2754-1169/2025.BJ24836
- **Period:** 2004–2024 monthly data; real estate + pharmaceutical industries

**Key findings:**
- Real estate (cyclical): short-term **reversal** + no significant long-term momentum
- Pharmaceutical (defensive growth): **momentum present**
- Industry heterogeneity: China's momentum/reversal dynamics are **sector-dependent**

#### 6. Ni, Day, Cheng & Huang (2022) — Financial Innovation (Springer)
- **DOI:** 10.1186/s40854-022-00358-1
- **Market:** KOSPI 50 (Korea) + SSE 50 (China Shanghai)
- [ABSTRACT ONLY — subscription required]

**Key findings:**
- Both markets not fully efficient by technical signal testing
- **China (SSE 50):** Momentum works when **continuously rising prices + overbought RSI occur simultaneously** (bull market condition)
- **Korea (KOSPI 50):** Contrarian strategies work in **all** cases

---

## CHINA SUMMARY TABLE

| Strategy | Period | Annual Return | Sharpe | Cap | Verdict vs Baseline |
|----------|--------|---------------|--------|-----|---------------------|
| 6-6 momentum (Zhang & Zi 2025) | 1998–2005 | +11.5% | N/R | All-cap | >> baseline (pre-reform only) |
| 6-6 momentum (Zhang & Zi 2025) | 2005–2024 | ~0% to −6.3% | Negative | All-cap | << baseline (FAILS post-reform) |
| Noise-filtered momentum (Zhang & Zi 2025) | 2005–2024 | +8.2% | N/R | All-cap | > baseline with filters |
| DL multi-factor + gap arb (Du 2025 USTC) | 2021–2024 bt | +15.2% | 1.87 | Mid-large | >> baseline [backtest only] |
| Short-term reversal, high turnover (Pu 2024 SWUFE) | 2005–2022 | Positive [UNVERIFIED] | N/R | All-cap | Directionally > baseline |
| SSE50 RSI momentum in bull (Ni et al. 2022) | N/S | N/R | N/R | Large-cap | Works conditionally [UNVERIFIED magnitude] |

---

## JAPAN (Nikkei 225 / TSE)

### Market structure — why mean-reversion dominates
1. **GPIF pension fund** rebalances quarterly → systematically buys underperformers, sells outperformers
2. **Corporate cross-shareholding (keiretsu)** creates stable anchor holders who buy on weakness
3. **Bank of Japan ETF purchasing** (2013–2024) provided a buying floor during corrections
4. **Low proportion of trend-following algos** relative to US

### Verified papers

#### 7. Kang (2021) — Nanzan University, JRFM
- **Source:** Department of Business Administration, Nanzan University, Aichi, Japan
- **Journal:** JRFM (MDPI), Vol. 14(1), Jan 2021
- **Market:** Nikkei 225 futures
- **Period:** 2011–2019
- **IDEAS:** https://ideas.repec.org/a/gam/jjrfmx/v14y2021i1p37-d481452.html

| MACD Configuration | Result 2011–2019 |
|--------------------|-----------------|
| Standard (12, 26, 9) | **NEGATIVE performance** |
| Optimized parameters | **Significant positive returns** |
| Total models tested | 19,456 configurations |

**Key finding:** Default MACD parameters **lose money on Nikkei futures**. Japan's market is not US-like — standard trend-following parameters fail. Optimized parameters work → market is weak-form inefficient but requires Japan-specific calibration.

**vs Slava baseline:** Standard MACD << baseline. Optimized MACD > baseline [UNVERIFIED exact magnitude].

#### 8. Kang (2023) — Nanzan University, JRFM
- **Journal:** JRFM (MDPI), Vol. 16(12), Dec 2023
- **URL:** https://www.mdpi.com/1911-8074/16/12/508
- **Market:** Nikkei 225 vs Dow Jones vs Nasdaq (comparative)
- [ABSTRACT ONLY]

**Key finding:** Nikkei optimal MACD parameter ranges **differ substantially** from Dow Jones and Nasdaq. Cross-market confirmation that Japan requires non-US-default technical parameters.

#### 9. Coe & Laosethakul (2021) — Asia-Pacific Financial Markets (Springer)
- **DOI:** 10.1007/s10690-021-09337-5
- **Market:** 39 Asian countries, 4,822 stocks (includes Japan, Korea, China)
- [ABSTRACT ONLY]

**Key finding:** Technical rules (MA, RSI, Stochastic) outperform buy-and-hold for **66% of stocks** with behavioral filter (only sell when profitable); 63% without filter.

#### IPSJ Records (Japanese CS institutional, record-page only)
- **Record 161612 (2016):** 投資家の収益性に基づく意思決定が株式市場に与える影響 — Tokyo City University; artificial market model; investor profitability-based decisions affect stock price dynamics; no quantified return
- **Record 180939 (2017):** 進化型ニューラルネットワークとフル板情報による株価変動の分析 — Hosei University; evolutionary NN + full order book prediction; past order book predicts short-term price movements
- **Access:** Record page accessible; PDFs under 2-year IPSJ embargo

#### Non-peer-reviewed backtest (Kabu Prediction Analytics, 2026)
- **URL:** https://kabu.microforge.works/articles/japan-stock-mean-reversion-strategies
- **Period:** 2015–2024 backtest, Nikkei 225 Prime constituents
- **Status:** Commercial analytics platform, NOT peer-reviewed

| Rule | Win Rate | Avg Return/Trade | Sharpe |
|------|----------|------------------|--------|
| Weekly Bollinger Band lower (20-week, −2σ) | 67% | +5.1% | 0.91 |
| Daily RSI < 30 oversold reversal | 69% | +4.8% | 0.96 |
| Dual confirmation (RSI < 35 + BB lower) | 74% | +6.3% | 1.12 |
| Quality-enhanced dual (+ ROE > 10% + D/E < 0.8) | 76% | N/R | 1.21 |
| Out-of-sample Sharpe degradation | — | — | −0.09 avg |

**Structural explanation:** GPIF rebalancing + keiretsu anchor holders + BOJ ETF floor create recurring overselling opportunities. Mean-reversion rules show smaller out-of-sample degradation (0.09 Sharpe drop) than momentum rules on the same platform.

**⚠️ Caveat:** Backtest only; survivorship bias/look-ahead not formally addressed. Directionally aligned with structural factors and academic evidence but not peer-reviewed.

---

## JAPAN SUMMARY TABLE

| Strategy | Period | Return | Sharpe | Cap | Verdict vs Baseline |
|----------|--------|--------|--------|-----|---------------------|
| Standard MACD (12,26,9), Nikkei futures (Kang 2021) | 2011–2019 | **Negative** | Negative | Large (index) | << baseline (FAILS with US defaults) |
| Optimized MACD, Nikkei futures (Kang 2021) | 2011–2019 | Positive [UNVERIFIED] | N/R | Large | > baseline (direction only) |
| BB weekly mean-reversion, Nikkei 225 (Kabu 2026) | 2015–2024 | N/R | 0.91 | Large-cap | > baseline [not peer-reviewed] |
| RSI < 30 reversal, Nikkei 225 (Kabu 2026) | 2015–2024 | N/R | 0.96 | Large-cap | > baseline [not peer-reviewed] |

---

## KOREA (KOSPI / KSC)

### Market structure
- Mixed retail/institutional (~45% retail by volume, declining)
- Heavy chaebol concentration (top-10 ~60% of market cap)
- ~35% foreign investor participation in KOSPI free-float
- High market volatility (σ ~25–27% annual)
- **Individual stocks show reversal; sector rotation works (contrarian)**

### Verified papers

#### 10. Kang & Ryu (2025) — Investment Analysts Journal (Tandfonline)
- **DOI:** 10.1080/10293523.2024.2448054
- **Market:** KOSPI (all-cap individual stocks + industry sectors)
- **Period:** 1983–2023 (40 years)
- [ABSTRACT ONLY — subscription required]

| Level | Effect | Direction |
|-------|--------|-----------|
| Individual stock portfolios | **Reversal effect** dominant | Contrarian profitable |
| Industry sector portfolios | **No significant effect** | Momentum AND reversal absent |

**Key finding:** Korea's individual stocks exhibit **reversal, not momentum**, over 40 years. Industry-level aggregation eliminates the effect — reversal is idiosyncratic stock-level, not systematic sector rotation.

**vs Slava baseline:** Stock-level contrarian strategies outperform. Magnitude [UNVERIFIED — no Sharpe in accessible abstract].

#### 11. Ni et al. (2022) — Korea-specific finding
- **See Source 6 above.**
- **Korea finding:** Contrarian strategies appropriate for **all** KOSPI 50 cases tested (RSI overbought/oversold + price continuation signals both trigger contrarian, not momentum, profitably).

#### 12. Yoon (2014) — University of Suwon, Korean master's thesis
- **Language:** Korean (한국어)
- **RISS ID:** T13576666
- **Source:** ScienceON KISTI — https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=DIKO0013576666
- **Market:** KOSPI, 15 stocks across 5 industries
- **Strategy:** EMA golden/dead cross; buy at golden cross closing, sell at dead cross or when above average cost

**Key finding:** Best performance = 3-tranche buy + bulk sell when above average purchase price. Beats annual market return for most tested stocks. Consistent with overshooting/reversal dynamics — average-cost-based exit exploits mean reversion to entry price.

**vs Slava baseline:** Claims to beat market return [UNVERIFIED on magnitude; master's thesis, no Sharpe reported].

#### 13. Kim et al. (2022) — MDPI JRFM, Korea intraday momentum
- **DOI:** 10.3390/jrfm15110523
- **Market:** KOSPI spot index
- [ABSTRACT ONLY — antibot block on MDPI direct URL]

**Key finding:** Market Intraday Momentum (MIM) — first 30-min return predicts last 30-min — **exists in KOSPI and is robust to transaction costs**. This is DIFFERENT from multi-day reversal: intraday momentum works, multi-day price momentum reverses.

**Non-peer-reviewed backtest (Ceta Research / TradingStudio Finance, 2026):**
- **URL:** https://blog.tradingstudio.finance/sector-mean-reversion-korea-ksc/
- **Data:** FMP financial data warehouse, 2000–2025, KSC market cap > KRW 300B
- **Signal:** Bottom-2 sectors by 12-month trailing return, quarterly rebalance

| Metric | Portfolio | KOSPI |
|--------|-----------|-------|
| CAGR (KRW) | **12.88%** | 5.55% |
| Excess CAGR | **+7.33% p.a.** | — |
| Sharpe Ratio | **0.39** | — |
| Max Drawdown | −33.52% | — |
| Annualised Volatility | 25.36% | — |
| Down Capture | 65.58% | — |
| Up Capture | 110.1% | — |
| Win Rate vs KOSPI | 54.81% | — |

**⚠️ Caveat:** Not peer-reviewed; transaction costs included (size-tiered model); KRW returns (FX risk for non-KRW investors); 2025 showed −33.17% excess (worst single year, concentrated market leadership).

---

## KOREA SUMMARY TABLE

| Strategy | Period | Annual Return | Sharpe | Cap | Verdict vs Baseline |
|----------|--------|---------------|--------|-----|---------------------|
| Individual stock momentum (Kang & Ryu 2025) | 1983–2023 | N/R | N/R | All-cap | Reversal dominates; momentum FAILS |
| RSI contrarian, KOSPI 50 (Ni et al. 2022) | N/S | N/R | N/R | Large-cap | Contrarian works |
| EMA golden/dead cross (Yoon 2014) | Pre-2014 | Beats market [UNVERIFIED] | N/R | Mixed | EMA + cost-basis exit works |
| Sector mean reversion, KSC (Ceta 2026) | 2000–2025 | 12.88% (+7.33% α) | 0.39 | Mid-large | > baseline (not peer-reviewed) |
| Intraday momentum KOSPI (Kim et al. 2022) | N/S | N/R | N/R | Index | MIM works, txn-cost robust |

---

## CROSS-MARKET SYNTHESIS

### Does technical analysis work in these markets?

| Market | Overall Verdict | Dominant Effect | Key Structural Driver |
|--------|-----------------|-----------------|----------------------|
| China A-share | YES — but contrarian/reversal | Short-term reversal (1-month); no multi-month momentum post-2005 | High retail speculation → overreaction; state shareholders are contrarian; Split-Share Reform killed momentum |
| Japan (Nikkei) | YES — mean reversion strongly supported | BB/RSI mean reversion large-cap; MACD momentum FAILS with standard params | GPIF rebalancing; keiretsu anchor holders; BOJ ETF floor; low trend-following algo ratio |
| Korea (KOSPI) | YES — contrarian at stock level; MIM at intraday | Individual stock reversal; intraday momentum; no multi-day momentum | Mixed retail/institutional; chaebol concentration creates overshoots; high volatility |

### Contrast with US findings

| Dimension | US Market | China A-Share | Japan | Korea |
|-----------|-----------|---------------|-------|-------|
| Price momentum (3-12 month) | Strong, persistent (Jegadeesh-Titman 1993) | Absent post-2005; negative in state firms | Weak/absent (Sharpe ~0) [UNVERIFIED] | Reversal dominates |
| Short-term reversal (1-month) | Present (Lehmann 1990) | Stronger than US | Present | Strong, especially large-cap |
| Technical rules (MA/RSI) | Mixed (data-snooping concerns) | Mean-reversion; conditional momentum in bull | Works with non-default params | Work as contrarian signals |
| MACD default params | Mixed US evidence | N/T | Negative (Kang 2021) | N/T |
| Market efficiency | Near semi-strong | Weak-form debated | Not weak-form (Kang 2021) | Not fully efficient (Ni et al. 2022) |

---

## ACCESS BARRIER LOG

| Source | Access Status | Reason |
|--------|---------------|--------|
| IPSJ records (2016/2017) | Record page only | 2-year embargo on PDFs |
| J-STAGE URL (task-specified) | 404 Not Found | URL format invalid |
| Kang & Ryu (2025) Tandfonline | Abstract only | Taylor & Francis paywall |
| MDPI JRFM Kim et al. (2022) | Abstract only | Antibot block |
| Coe & Laosethakul (2021) Springer | Abstract only | Springer paywall |
| Ni et al. (2022) Springer | Abstract only | Springer paywall |
| ResearchGate (multiple) | Blocked | Antibot across all URLs |
| arXiv basic search (`/search/?searchtype=all&query=...`) | Zero results | "No results" for multi-word natural-language queries |

---

## SOURCE-SPECIFIC QUIRKS FOR FUTURE SWEEPS

### arXiv
- Basic search URL (`/search/?searchtype=all&query=technical+trading+momentum+China`) returns **zero results** for natural-language multi-word queries — the endpoint requires simpler single/double terms or uses AND logic differently than expected
- **Working approach:** Use `web_search` with `site:arxiv.org [topic terms]` or use the arXiv HTML search with short targeted terms
- DO NOT use the Atom API endpoint (`export.arxiv.org/api/query`) — confirmed timeout via web_extract

### Chinese-language site:arxiv.org queries
- `site:arxiv.org 技术分析 量化交易 A股 2023 2024 2025` — returned **general arXiv homepage links only**, not paper results
- Better path: English queries (`China A-share momentum technical analysis arXiv 2024`) + institutional attribution searches

### IPSJ (Japan)
- 2-year embargo on all conference PDFs (no free download before 2 years from publication)
- Record pages (ipsj.ixsq.nii.ac.jp/records/XXXXXX) are always accessible: title, abstract, authors, institution, date
- DO NOT attempt browser_navigate — use web_extract

### RISS (Korea)
- `site:riss.kr 기술적 분석 주식 수익성 2023 2024` returned general catalogue pages, not specific papers on the topic
- Better approach: ScienceON (scienceon.kisti.re.kr) is more reliably scrapable for Korean academic abstracts
- RISS abstracts + metadata accessible; full text requires institutional login

### J-STAGE (Japan)
- The task-provided URL format returned 404 — J-STAGE search URLs have changed
- No alternative J-STAGE URL was found that returned results in this session

### Korean native-language queries
- `RSI 볼린저밴드 한국 주식시장 수익성 학술` — returned practitioner blogs, not academic papers
- Better: use English-language Korean market searches + ScienceON for Korean theses

---

## BIBLIOGRAPHY (ALL VERIFIED SOURCES)

1. Zhang C. & Zi C. (2025). Understanding the Evolution of Momentum Effects in China's Stock Market. SAIF/SJTU working paper. URL: https://czi.finance/assets/ChinaMom.pdf
2. Weng J. (2026). Herding, Momentum, and Reversal in China's A-Share Market. arXiv:2607.27063. Renmin University of China.
3. Du Y. (2025). Deep Learning Enhanced Multi-Day Turnover Quantitative Trading Algorithm for Chinese A-Share Market. arXiv:2506.06356. USTC.
4. Pu S. (2024). Unlocking the Reversal Anomaly in the A-share Market. PGMEE 2024, Vol. 41, pp. 42–48. SWUFE.
5. Zhang Y., Li Y. & Dai Y. (2025). Comparison on the Momentum Effect and Reversal Effect in China's Stock Market. AEMPS Vol.196 pp. 277–284. DOI: 10.54254/2754-1169/2025.BJ24836
6. Ni Y., Day M-Y., Cheng Y. & Huang P. (2022). Can investors profit by utilizing technical trading strategies? Financial Innovation, Vol. 8(1). DOI: 10.1186/s40854-022-00358-1 [ABSTRACT ONLY]
7. Kang B-K. (2021). Improving MACD Technical Analysis by Optimizing Parameters. JRFM Vol. 14(1). Nanzan University, Japan. IDEAS: https://ideas.repec.org/a/gam/jjrfmx/v14y2021i1p37-d481452.html
8. Kang B-K. (2023). Optimal and Non-Optimal MACD Parameter Values for Nikkei, Dow Jones, Nasdaq. JRFM Vol. 16(12). URL: https://www.mdpi.com/1911-8074/16/12/508 [ABSTRACT ONLY]
9. Coe T.S. & Laosethakul K. (2021). Applying Technical Trading Rules to Beat Long-Term Investing: Evidence from Asian Markets. Asia-Pacific Financial Markets, Vol. 28 pp. 587–611. DOI: 10.1007/s10690-021-09337-5 [ABSTRACT ONLY]
10. Kim et al. (2022). Market Intraday Momentum with New Measures for Trading Cost: Evidence from KOSPI. JRFM Vol. 15(11) p. 523. DOI: 10.3390/jrfm15110523 [ABSTRACT ONLY]
11. Kang & Ryu (2025). Momentum and reversal effects in the Korean stock market. Investment Analysts Journal. DOI: 10.1080/10293523.2024.2448054 [ABSTRACT ONLY]
12. Yoon J-H. (2014). 한국주식시장에서의 기술적 분석을 통한 주식수익률의 분석. Master's thesis, University of Suwon. RISS T13576666.
13. Miyasaka J. & Anada H. (2016). 投資家の収益性に基づく意思決定が株式市場に与える影響. IPSJ 2016, Vol. 1, pp. 269–270. Tokyo City University. [RECORD PAGE ONLY]
14. Kumazoe H. & Fujita S. (2017). 進化型ニューラルネットワークとフル板情報による株価変動の分析. IPSJ 2017, Vol. 1, pp. 347–348. Hosei University. [RECORD PAGE ONLY]
15. Ceta Research / TradingStudio Finance (2026). Sector Mean Reversion Korea Backtest. URL: https://blog.tradingstudio.finance/sector-mean-reversion-korea-ksc/ [NOT PEER-REVIEWED]
16. Kabu Prediction Analytics (2026). Japan Stock Mean Reversion Strategies. URL: https://kabu.microforge.works/articles/japan-stock-mean-reversion-strategies [NOT PEER-REVIEWED]

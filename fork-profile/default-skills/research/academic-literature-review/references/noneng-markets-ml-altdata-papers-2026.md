# Non-English Markets + ML/Alternative Data Finance Papers — August 2026 Sweep

## Context
Delta sweep for Slava's multilingual trading-strategy report. Baseline covered: Chinese momentum (Zhang/Zi 2025), Japanese MACD/RSI (Kang 2021), Korean reversal (Kang-Ryu 2025), Russian CyberLeninka, Moroccan HAL, Taiwan (Barber 2004), Brazil (Chagué 2020). This file records NEW findings from the Cluster C sweep (August 2026).

---

## PART 1: Non-English / New Markets

### INDIA (NSE/BSE) — EVIDENCE FOUND

**Paper 1: Four Factor Model in Indian Equities Market**
- Authors: Agarwalla, S.K., Jacob, J., Varma, J.R.
- Year: 2013 (first version); updated regularly via IIMA data library
- Venue: SSRN WP 2334482 [SSRN working paper, not peer-reviewed in a journal as of sweep]
- URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2334482
- Data: NSE, October 1993–December 2013 (and updated; live data library at faculty.iima.ac.in/iffm/)
- Key result: Momentum factor (WML) significant in Indian equities. Factor data library actively maintained at Indian Institute of Management Ahmedabad (IIMA). IIMA is the Indian equivalent of Kenneth French's data library.
- Sharpe: NOT reported in SSRN abstract; factor premium magnitude not confirmed from abstract alone
- Access: SSRN abstract confirmed via web_search; full paper anti-bot blocked on direct extract

**Paper 2: Size, Value, and Momentum in Indian Equities**
- Authors: Agarwalla, S.K., Jacob, J., Varma, J.R.
- Year: 2017
- Venue: VIKALPA (The Journal of Decision Makers), SAGE Journals, DOI: 10.1177/0256090917733848
- URL: https://journals.sagepub.com/doi/10.1177/0256090917733848
- Key result (from abstract): "factor investing using value and momentum is a viable investment strategy in India, but size does not perform well. This remains true, even if short positions are excluded, and only value and momentum tilts to the market portfolio are considered."
- Sharpe: NOT confirmed from abstract (anti-bot blocked on full extraction)
- Access: Abstract confirmed; full text SAGE anti-bot blocked
- Peer-reviewed: YES (VIKALPA is a peer-reviewed journal)

**Paper 3: Four and Five-Factor Models in the Indian Equities Market**
- Authors: Not confirmed from snippet
- Year: 2022 (revised)
- Venue: SSRN WP 4054146 [SSRN working paper]
- URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4054146
- Data: October 2006–February 2022, Refinitiv Datastream
- Key result: Computes Fama-French three/five-factor and momentum factor returns for Indian equities using two breakpoint schemes. More recent data than the 2013 paper above.
- Sharpe: NOT confirmed (SSRN anti-bot)
- Access: Snippet only; anti-bot blocked on extract

**Paper 4: 52-Week High Effect and Momentum in India**
- Authors: Raju, R. [Rajan Raju]
- Year: 2023
- Venue: SSRN WP 4587697 [SSRN working paper]
- URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4587697
- Key result (from snippet): "stocks near their past 52 weeks tend to offer higher returns and Sharpe ratio, even after controlling for firm size." Studies predictive power of 52-week high and contrasts it with academic momentum.
- Sharpe: MENTIONED but not quantified in snippet; full text not accessible
- Access: SSRN anti-bot blocked

**Paper 5: PEAD in India**
- Authors: Various (multiple papers found)
- Venue: Journal of the Knowledge Economy and others
- Key finding: PEAD exists in Indian NSE. One practitioner source (blog.tradingstudio.finance, Jan 2026) claims "India has the strongest PEAD across 14 global markets — T+63 beat drift of +2.93% vs Sensex (t=11.24)." This is a PRACTITIONER CLAIM [NOT PEER-REVIEWED]. The academic paper published in Journal of Knowledge Economy and related venues confirms PEAD exists in NSE (2018 paper found on ResearchGate: "Post-Earnings-Announcement Drift Anomaly in India: A Test of Market Efficiency", various authors).
- ResearchGate URL: https://www.researchgate.net/publication/328500162_Post-Earnings-Announcement_Drift_Anomaly_in_India_A_Test_of_Market_Efficiency
- Access: Abstract-only; full text not confirmed

**Practitioner source (NOT peer-reviewed):**
- QED Capital (2021): "Momentum Factor in Indian Markets: Evidence from the Long Side" — confirms momentum works on the long side in India's large-cap universe (NSE Nifty 200 Momentum 30 index). URL: https://qedcap.com/ast/uploads/2022/03/Momentum-In-India-Sep2021.pdf — ACCESSIBLE full PDF. Key finding: Winner Big portfolio closely mirrors the Nifty 200 Momentum 30. Does NOT report Sharpe ratios explicitly but reports OOS returns vs. Nifty 50.
- Classify as: practitioner working paper / industry analysis, not peer-reviewed

**IIMA Data Library:** https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/ — actively maintained, free access. This is the Indian equivalent of Ken French's data library. Contains downloadable factor return series.

---

### GCC / GULF MARKETS (Saudi Tadawul, UAE, Qatar) — EVIDENCE FOUND

**Paper 1: Post-Earnings Announcement Drift, Momentum, and Contrarian Strategies in the Saudi Stock Market**
- Authors: Boussaidi, R.
- Year: 2023 (published 2024 in journal)
- Venue: Journal of the Knowledge Economy, Vol. 15, pp. 13622–13653 (2024), Springer. DOI: 10.1007/s13132-023-01648-4
- URL: https://link.springer.com/article/10.1007/s13132-023-01648-4
- Data: All listed firms on Tadawul, 2010–2019
- Key result: "These strategies [PEAD, momentum, long-term reversal] are significantly profitable regardless of the formation and holding period length, and their profitability generally persists for the subperiods." Profitability persists after controlling for CAPM, FF3, and FF5. Momentum is explained by market underreaction to earnings announcements (behavioral explanation confirmed). Risk explanation rejected.
- Sharpe: NOT reported (uses alpha methodology, not Sharpe)
- Access: Abstract accessible; full text behind Springer paywall (€39.95)
- Peer-reviewed: YES (Springer, Journal of the Knowledge Economy)

**Paper 2: Momentum Strategies and Stock Returns: A Case of Saudi Stock Market**
- Authors: Not confirmed from snippet
- Year: 2021
- Venue: Journal of Asian Finance, Economics and Business (JAFEB), Vol. 8, No. 7, pp. 365–?
- URL: https://koreascience.or.kr/journal/view.jsp?kj=OTGHEU&py=2021&vnc=v8n7&sp=365
- Data: 194 listed firms on Tadawul, monthly closing prices
- Key result: "Presence of time-series and cross-sectional momentum profits in the Saudi stock market"
- Sharpe: NOT confirmed
- Access: KoreaScience — partial open access; confirmation from snippet
- Peer-reviewed: YES (JAFEB is Scopus-indexed)

**SUMMARY FOR GCC:** Two peer-reviewed papers confirm momentum (and PEAD) is statistically significant in the Saudi Tadawul (2010–2019 data). No Sharpe ratios reported. Behavioral (underreaction) explanation supported over risk-based explanation. No UAE/Qatar-specific studies found.

---

### GERMANY / DACH MARKETS — EVIDENCE FOUND

**Paper 1 (CFR Cologne WP): Determinants of Expected Stock Returns: Large Sample Evidence from the German Market**
- Authors: Artmann, S., Finter, P., Kempf, A.
- Year: 2011 (working paper); published in CFR Working Paper No. 10-01
- Institution: University of Cologne / Centre for Financial Research (CFR)
- URL: https://www.cfr-cologne.de/download/workingpaper/cfr-10-01.pdf — FULLY ACCESSIBLE
- Data: 955 German stocks, 1963–2006 (German market, long-horizon dataset)
- Key result: "value characteristics and momentum explain the cross-section of stock returns." Carhart 4-factor model outperforms FF3 for Germany. Size factor NOT significant (size effect has vanished in Germany). Earnings-to-price + momentum combination best explains returns.
- Sharpe: NOT reported (uses factor alpha/t-stat methodology)
- Access: Full PDF confirmed accessible

**Paper 2 (CFR Cologne WP): Momentum? What Momentum?**
- Authors: Theissen, E., Yilanci, C.
- Year: 2020 (WP 20-09); also on SSRN 3710496
- Institution: University of Mannheim / CFR Cologne
- URL: https://www.cfr-cologne.de/download/workingpaper/cfr-20-09.pdf — FULLY ACCESSIBLE
- Data: CRSP stocks 1963–2018 + international sample of 20 developed countries
- Key result: **Momentum effect is much weaker than previously thought when stock-level (vs. portfolio-level) risk adjustment is used.** Under FF5 stock-level adjustment, NONE of 16 momentum strategies deliver significant returns. Without risk adjustment: 15/16 strategies positive and significant. International: significant momentum in 19/20 countries without adjustment drops to 3/20 with stock-level adjustment.
- Implication: This is a CRITICAL CHALLENGE to the momentum premium — suggests prior studies overstate momentum by using constant-factor-exposure assumption in portfolio-level regression.
- Sharpe: NOT reported; uses t-statistic methodology
- Access: Full PDF confirmed accessible
- Note: This is specifically relevant for AU investors — suggests momentum alpha may be partially risk-compensated

**Paper 3 (Springer peer-reviewed): The Fama-French Five-Factor Model Plus Momentum: Evidence for the German Market**
- Authors: Not confirmed from abstract (anti-bot on full extract)
- Year: 2020
- Venue: Schmalenbach Business Review, Vol. 72, pp. 661–684, Springer. DOI: 10.1007/s41464-020-00105-y
- URL: https://link.springer.com/article/10.1007/s41464-020-00105-y — OPEN ACCESS
- Data: CDAX constituents, 2002–2019
- Key result: FF5 + momentum (6-factor) does NOT add significant explanatory power over FF3 for Germany. No significant profitability or investment premium found. Key finding: additional factors from US context do NOT transfer to German market.
- Sharpe: NOT reported
- Access: Open access — full content accessible in principle but anti-bot blocked on this session's web_extract

**Paper 4 (Springer peer-reviewed): Beating the DAX, MDAX, and SDAX**
- Authors: Not confirmed
- Year: 2016
- Venue: Financial Markets and Portfolio Management, Springer. DOI: 10.1007/s11408-016-0268-6
- URL: https://link.springer.com/article/10.1007/s11408-016-0268-6
- Data: 1988–2015, three German equity indices
- Key result: Momentum and value strategies outperformed buy-and-hold in DAX, MDAX, SDAX 1988–2015
- Sharpe: NOT confirmed from snippet
- Access: Springer paywall

**SUMMARY FOR GERMANY:** Strong evidence that value and momentum explain German cross-sectional returns (1963–2006, Artmann et al.). But Theissen-Yilanci (2020) raises methodological concerns that momentum alpha largely disappears with proper risk adjustment. The 2020 Schmalenbach paper found 6-factor model adds nothing over 3-factor for Germany 2002–2019.

---

### FRANCE (CAC40) — NOT FOUND / ACCESS BARRIERS

- **HAL (hal.science):** Bot-protected — web_extract returns 403 on all direct pages. web_search with `site:hal.science momentum strategie marche boursier France` returned only general HAL homepage and unrelated theses. No specific French-language momentum/factor papers surfaced.
- **ESSEC/HEC Paris working papers:** Not found via available searches. No specific CAC40 momentum studies surfaced.
- **English-language searches:** `France CAC40 momentum premium academic paper 2015 2024` returned no relevant hits — general academia.edu, Google, and unrelated results only.
- **STATUS: [NOT FOUND]** — French equity factor research exists (confirmed by Springer results showing France in international multi-market studies) but no France-specific peer-reviewed momentum paper was located in this sweep. HAL is the primary access barrier.

---

### BRAZIL / LATIN AMERICA — LIMITED EVIDENCE

**Paper found (S&P practitioner):**
- S&P Dow Jones Indices: "Factor Strategies in Brazil: A Practitioner's Guide" (PDF) — discusses S&P/B3 Momentum Index. PRACTITIONER source, not peer-reviewed.

**Latin America multi-market review:**
- Review of Finance (2025): "Empirical Determinants of Momentum: A Perspective Using International Data" — Oxford Academic, DOI confirmed. This is an international study that INCLUDES Brazil as one of many markets. Published January 2025. Confirmed existence via Oxford Academic snippet.
- URL: https://academic.oup.com/rof/article/29/1/241/7772889
- Status: Abstract-only (anti-bot); full text not extracted. This may contain Brazil-specific results.

**SciELO access:** site:scielo.br search returned SciELO homepage and journal index pages, NOT specific finance papers on momentum. Direct momentum/retorno queries on SciELO not productive in this session. **SciELO appears to require direct article URL navigation** — general search doesn't surface finance papers without a known article ID.

**SUMMARY FOR BRAZIL:** Beyond Chagué 2020 (already in baseline), one 2025 multi-market study in Review of Finance (Oxford) likely contains Brazil data but full text not confirmed. S&P practitioner guide confirms Brazil momentum index exists. No new peer-reviewed Brazil-specific study found. [NOT FOUND for Brazil-specific academic paper 2020–2024]

---

### POLAND / EASTERN EUROPE — EVIDENCE FOUND

**Paper 1: Are Value, Size and Momentum Premiums in CEE Emerging Markets Only Illusionary?**
- Authors: Zaremba, A., Konieczka, P.
- Year: 2015
- Venue: Finance Quarterly (Finanse, Rynki Finansowe, Ubezpieczenia), Vol. 11, No. 3. [Journal-level venue confirmed via IDEAS/RePEC: ideas.repec.org/a/wsz/fiq000/v11y2015i3id732.html]
- SSRN: 2375454
- Data: 11 CEE stock markets (Bulgaria, Croatia, Czech Republic, Estonia, Hungary, Latvia, Lithuania, Poland, Romania, Slovakia, Slovenia), 2000–2013
- Key result: **"The answer is mostly YES."** High value and size premiums before costs, but "impact of illiquidity and transaction costs is almost lethal" for momentum and size. After bid-ask spreads and liquidity adjustment: **only the value premium survives; momentum effect is obliterated.**
- Backtest (paperswithbacktest.com replication): Annual return -3.70%, Sharpe 0.03, max drawdown -95.47% — confirming the post-cost finding. NOTE: this is a third-party backtest replication, not the paper's own numbers.
- Access: SSRN abstract accessible; paperswithbacktest.com provided backtest replication summary

**Paper 2: Value, Size, Momentum, and Unique Role of Microcaps in CEE Market**
- Authors: Zaremba, A.
- Year: 2015
- Venue: Finance a úvěr – Czech Journal of Economics and Finance (confirmed via Tandfonline). DOI: 10.1080/00128775.2015.1034059
- Key result: Cross-sectional analysis of value, size, momentum in CEE; highlights unique role of microcap equities
- Access: Tandfonline paywall

**Paper 3: Mean Reversion and Momentum in Central and Eastern European Countries**
- Found on ResearchGate. Covers Poland and Romania. Examines momentum/mean reversion in Czech, Hungary, Poland, Romania.
- URL: https://www.researchgate.net/publication/330013407
- Full text not confirmed

**Paper 4: Time Series Momentum: Evidence from the European Equity Market (2023)**
- Found on ScienceDirect (Heliyon). Studies TSM 2000–2020 across European market broadly.
- DOI: 10.1016/j.heliyon... (exact confirmed via ScienceDirect snippet)
- Key result: "Significant and persistent" TSM in European equity market 2000–2020

**SUMMARY FOR CEE/POLAND:** The Zaremba (2015) result is the key finding: pre-cost momentum premium exists in 11 CEE markets, but transaction costs and illiquidity eliminate it entirely. Value premium survives costs; momentum does not. This is a NET-RETURN negative finding — relevant for AU investors comparing strategies.

---

### AUSTRALIA (ASX) — EVIDENCE FOUND (MIXED)

**Paper 1: Momentum Investing and the GFC: The Case of the S&P/ASX100**
- Authors: Hahn, T. (Tobias Hahn, Bond University / University of Bangor)
- Year: 2013
- Venue: SSRN WP 2312114 [SSRN working paper; also Bond University research output]
- URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2312114
- Data: S&P/ASX100 constituents
- Key result: "Prior momentum studies in Australian equity markets have produced mixed results, describing performance ranging from startling out-performance to no effect." Documents returns to momentum strategies with varying formation/holding periods, examines GFC impact.
- Sharpe: NOT confirmed (SSRN anti-bot blocked)
- Access: SSRN abstract confirmed; full text anti-bot blocked

**Paper 2: Momentum in Australian Style Portfolios: Risk or Inefficiency?**
- Authors: Not confirmed
- Year: 2016
- Venue: Accounting & Finance (Wiley), Vol. 56, Issue 2, pp. 333–361. DOI: 10.1111/acfi.12106
- URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/acfi.12106
- Key result: "Robust evidence of style momentum in the Australian market." Uses Jegadeesh-Titman return decomposition. Momentum strategy predominantly explained by positive autocorrelation.
- Sharpe: NOT confirmed
- Access: Wiley paywall; abstract confirmed
- Peer-reviewed: YES (Accounting & Finance is a peer-reviewed journal)

**Paper 3: Disentangling Size from Momentum in Australian Stock Returns**
- Authors: O'Brien, M.A. et al.
- Year: 2008
- Venue: Australian Journal of Management (SAGE), Vol. 32 No. 3. DOI: 10.1177/031289620803200305
- Key result: "Prior evidence concerning momentum in Australian equity returns has produced inconsistent results. This study examines the interaction between momentum and firm size."
- Status: Long-standing finding — mixed evidence in AU literature

**Practitioner/industry sources:**
- SGH Asset Management (2024): "Momentum and Quality" white paper — data through April 2024. "Over entire sample, both momentum and quality have outperformed market return. Momentum outperformed quality by nearly 300bp annualized." URL: https://sghiscock.com.au/wp-content/uploads/2024/09/Momentum-and-Quality_SGH2024_web.pdf — accessible PDF. PRACTITIONER source.
- MSCI Australia Momentum Index: Factor sheet available. Launched Oct 20, 2014. Back-tested data prior to launch date.

**SUMMARY FOR ASX:** Peer-reviewed evidence of style/stock momentum exists in ASX (Accounting & Finance 2016, confirmed). BUT: (1) pre-GFC studies showed mixed results; (2) no ASX-specific Sharpe ratios found in accessible papers; (3) the Australian literature has notably inconsistent results across studies. SGH practitioner report suggests ~300bp momentum premium over quality in recent data (through April 2024). AT 47% marginal tax rate with >12M holdings, the CGT discount applies if held >12 months — momentum's characteristically high turnover creates tax friction that makes the AU academic result less directly applicable.

---

## PART 2: ML / ALTERNATIVE DATA

### Gu, Kelly & Xiu (2020) — FULLY VERIFIED

**Paper:** Empirical Asset Pricing via Machine Learning
- Authors: Gu, S., Kelly, B., Xiu, D.
- Year: 2020
- Venue: Review of Financial Studies, Vol. 33, No. 5, pp. 2223–2273. DOI: 10.1093/rfs/hhaa009
- SSRN: 3159577; NBER WP 25398
- Full PDF: https://dachxiu.chicagobooth.edu/download/ML.pdf — FULLY ACCESSIBLE (confirmed this session)

**Key quantified results (from full text extraction):**
- S&P 500 timing via neural network: annualized OOS Sharpe = **0.77** vs. 0.51 for buy-and-hold
- Long-short decile spread strategy (stock-level neural network forecasts): annualized OOS Sharpe = **1.35** — "more than doubling the performance of a leading regression-based strategy from the literature"
- Best methods: trees and neural networks (especially gradient-boosted trees and deep NNs)
- Predictive gains traced to: allowing **nonlinear predictor interactions** missed by linear methods
- All methods agree on same dominant predictive signals: **variations on momentum, liquidity, and volatility** (these three are the most important feature clusters)
- Performance on R²: positive OOS R², robust across ML specifications
- Sample: US stocks (CRSP), 1957–2016 (194 predictors covering 94 characteristics)

**Post-publication critique:**
- Theissen-Yilanci (CFR 2020, see Germany section above) uses similar methodology to challenge standard momentum results; relevant to GKX's claimed gains
- Replication confirmed (multiple GitHub repos); core result holds but magnitudes sensitive to sample period

---

### Ke, Kelly & Xiu (2019) — NBER WP, NOT YET PEER-REVIEWED IN A JOURNAL AS OF SWEEP

**Paper:** Predicting Returns with Text Data
- Authors: Ke, Z.T., Kelly, B.T., Xiu, D.
- Year: 2019 (NBER WP 26186, revised Nov 2019); updated version posted to SSRN Sept 2020
- Venue: NBER Working Paper [NOT PEER-REVIEWED]. Note: as of this sweep, paper appears to remain a working paper — NOT confirmed published in a peer-reviewed journal.
- Full PDF: https://www.nber.org/system/files/working_papers/w26186/w26186.pdf — accessible
- Also: https://www.tracyke.net/papers/Sentiment-SSRN.pdf — accessible

**Key result:**
- Methodology: Supervised sentiment extraction from Dow Jones Newswires (text mining via penalized likelihood + topic modeling)
- Constructs article-level sentiment score specifically adapted to return prediction (not dictionary-based)
- Data: Dow Jones Newswires
- Sharpe: NOT quantified in the abstract/introduction sections extracted. The paper reports return predictability (positive OOS R², portfolio returns) but specific Sharpe numbers not in the visible sections. A ResearchGate description of a related paper (using GPT-3) cites Sharpe 3.05 — this is NOT from the Ke-Kelly-Xiu paper, it is from a different paper citing it.
- Key finding: supervised NLP significantly outperforms standard dictionary-based sentiment for return prediction
- Classification: NBER working paper [NOT peer-reviewed as of this sweep]

---

### Alternative Data: Satellite Imagery — PARTIAL PEER-REVIEWED EVIDENCE

**Paper 1: The Firm Next Door: Using Satellite Images to Study Local Information Advantage**
- Authors: Not confirmed (Harvard Business School, Journal of Accounting Research)
- Year: 2021
- Venue: Journal of Accounting Research, Vol. 59, Issue 2, pp. 713–750. DOI: 10.1111/1475-679X.12360
- URL: https://onlinelibrary.wiley.com/doi/10.1111/1475-679X.12360
- Data: Satellite data tracking car counts in parking lots of 92,668 stores for 71 publicly listed US retailers
- Key result: Studies LOCAL INFORMATION ADVANTAGE of institutional investors — nearby institutions trade more profitably using satellite parking lot data. Does not directly report a standalone Sharpe ratio for a satellite-based trading strategy.
- Access: Abstract confirmed; Wiley paywall on full text
- Peer-reviewed: YES (Journal of Accounting Research is top-tier)
- Caveat: This is NOT a paper proposing a retail satellite-based trading strategy — it studies how institutional investors with proximity advantage use satellite data. The alpha is captured by INFORMED institutions, not available to retail.

**Paper 2: Forward-Looking Retailer Performance Using Parking Lot Traffic Data**
- Year: 2022
- Venue: Journal of Retailing (ScienceDirect). DOI: 10.1016/j.jretai.2022.03.002
- Key result: Satellite parking lot data predicts Tobin's q (performance metric), not just returns
- Access: Paywall

**Practitioner context:** RS Metrics pioneered satellite parking lot analysis in 2011 for hedge funds. Orbital Insight followed. This is now a well-established (and heavily arbitraged) alternative data source. No peer-reviewed paper demonstrates a currently tradeable Sharpe-positive retail strategy using raw satellite data — the alpha is captured by institutional players with the data license.

**STATUS:** Peer-reviewed evidence EXISTS that satellite imagery data predicts retailer performance (academic) and that informed institutions use it profitably (academic). But no academic paper reports a standalone Sharpe ratio for a satellite-based strategy available to public investors. The alpha is almost certainly already arbitraged away by institutional alternative-data providers.

---

### Alternative Data: Credit Card / Consumer Spending — PEER-REVIEWED EVIDENCE

**Paper: Consumer Spending and the Cross-Section of Stock Returns**
- Authors: Gupta, T., Leung, E., Roscovan, V.
- Year: 2022
- Venue: Journal of Portfolio Management, Vol. 48, Issue 7, pp. 117–137. DOI: confirmed via pm-research.com and econbiz.de
- URL: https://www.pm-research.com/content/iijpormgmt/48/7/117.full.pdf
- Key result: "Within-quarter measure is powerful in explaining quarterly sales growth, revenue surprises, and earnings surprises, generating average excess announcement returns of 3.4%." Transaction-level credit/debit card data predicts forward stock returns for consumer-facing US stocks.
- Sharpe: NOT reported in abstract (paper uses announcement return and regression metrics, not portfolio Sharpe)
- Data: Individual transaction-level credit/debit card data, universe of US consumer-facing stocks
- Access: pm-research.com paywall; abstract and metadata confirmed open
- Peer-reviewed: YES (Journal of Portfolio Management, peer-reviewed)

**Note:** This data source is institutional/proprietary — requires a commercial data license (similar to RS Metrics satellite). The 3.4% excess announcement return is before costs of data access, transaction costs, and capacity constraints.

---

### ML Post-Publication Decay / Crowding — EVIDENCE FOUND

**Paper 1 (KEY): Not All Factors Crowd Equally: Modeling, Measuring, and Trading on Alpha Decay**
- Author: Lee, C. (Chorok Lee, KAIST)
- Year: 2025 (arXiv preprint)
- Venue: arXiv:2512.11913 [q-fin.PM], December 11, 2025 — PREPRINT, NOT peer-reviewed
- URL: https://arxiv.org/html/2512.11913v1 — FULLY ACCESSIBLE
- License: CC BY 4.0

**Key quantified results (from full text extraction):**
- Derives hyperbolic alpha decay: α(t) = K/(1+λt) from a game-theoretic equilibrium model (Nash equilibrium with N agents competing for fixed alpha capacity K)
- Tests on 8 Fama-French factors, 1963–2024
- **Momentum**: clear hyperbolic decay, R² = 0.65 (vs 0.51 linear, 0.61 exponential) — validates the model
- "Momentum returned approximately 10% annually in the 1990s. Today, that figure is closer to 2%."
- **Crowding accelerated post-2015** (consistent with factor ETF growth): model over-predicts remaining alpha (0.30 vs actual 0.15), correlated with factor ETF growth (ρ = -0.63)
- NOT all factors crowd equally: mechanical factors (momentum, reversal) fit the model; judgment-based factors (value, quality) do NOT
- Crowding-based factor selection: Sharpe 0.22 vs 0.39 factor momentum benchmark — crowding cannot be profitably traded
- Key implication: **crowding predicts TAIL RISK, not means** — crowded momentum shows LOWER crash probability (0.38×, p=0.006); crowded reversal shows HIGHER crash probability (1.7–1.8×)
- Practical use: risk management, not alpha generation

**Paper 2: McLean & Pontiff (2016) — Does Academic Research Destroy Stock Return Predictability?**
- Authors: McLean, R.D., Pontiff, J.
- Year: 2016
- Venue: Journal of Finance, Vol. 71, Issue 1, pp. 5–32. DOI: 10.1111/jofi.12365. Cited 1321 times.
- URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Key result: "Portfolio returns are 26% lower out-of-sample and **58% lower post-publication**" for 97 cross-sectional return predictors
- Interpretation: Academic publishing accelerates factor arbitrage. The more-cited a factor, the faster the decay.
- Access: Wiley paywall; abstract confirmed. Full text on Gwern: https://gwern.net/doc/economics/2016-mclean.pdf (confirmed accessible)
- Peer-reviewed: YES (Journal of Finance, top-tier)

**Paper 3 (Supplementary): From Factor Models to Deep Learning: ML in Reshaping Asset Pricing**
- Year: 2024 (arXiv:2403.06779)
- Venue: arXiv preprint, March 11, 2024 [NOT peer-reviewed]
- Key result: Comprehensive review of ML applications in asset pricing. Notes ML applications extend beyond return prediction to factor explanation and economic mechanism testing.

---

## ACCESS BARRIER LOG BY MARKET/SOURCE

| Source | Status | Notes |
|--------|--------|-------|
| SSRN | Bot-blocked for direct extract | Abstract visible via web_search snippets; use Google snippet only |
| CFR Cologne (cfr-cologne.de) PDFs | ✅ Fully accessible | Direct PDF download works via web_extract |
| Springer (link.springer.com) | ❌ Paywall | Abstract accessible; full text requires subscription |
| Wiley (onlinelibrary.wiley.com) | ❌ Paywall | Abstract accessible |
| SAGE Journals (journals.sagepub.com) | ❌ Bot-blocked | Neither abstract nor full text accessible via web_extract |
| SciELO (scielo.br) | Partial | Homepage accessible; requires direct article URL not general search |
| HAL (hal.science) | ❌ Bot-blocked | 403 on all direct pages; use web_search site:hal.science only |
| Oxford Academic (academic.oup.com) | ❌ Bot-blocked | Cannot extract even abstract |
| IIMA Data Library (faculty.iima.ac.in) | ✅ Fully accessible | Free factor data downloads |
| Chicago Booth PDF (dachxiu.chicagobooth.edu) | ✅ Fully accessible | Direct PDF confirmed |
| NBER WP PDF (nber.org/system/files) | ✅ Fully accessible | Direct PDF confirmed |
| arXiv HTML (arxiv.org/html/) | ✅ Fully accessible | Full text extraction works |
| KoreaScience | ✅ Partial | Abstract accessible for some journals |

---

## MASTER COMPARISON TABLE — NEW FINDINGS

| Market | Evidence Status | Key Paper | Return Metric | Net Return (estimate) | Peer-reviewed |
|--------|----------------|-----------|--------------|----------------------|---------------|
| India NSE | STRONG positive | Agarwalla-Jacob-Varma 2017 (VIKALPA) | Factor premium significant; Sharpe NR | Positive (unquantified) | YES |
| India PEAD | POSITIVE | Multiple papers 2015–2024 | Drift significant | +2.93% vs index (practitioner claim) | Partial |
| Saudi Tadawul | POSITIVE | Boussaidi 2024 (J Knowledge Economy) | Alpha significant | Positive (unquantified) | YES |
| Saudi Tadawul | POSITIVE | JAFEB 2021 | Momentum profits | Positive (unquantified) | YES |
| Germany (1963–2006) | POSITIVE | Artmann-Finter-Kempf 2011 (CFR) | Cross-sectional alpha | Positive | WP (CFR) |
| Germany (2002–2019) | MIXED | Theissen-Yilanci 2020 (CFR); Schmalenbach 2020 | Alpha disappears with stock-level risk adj | Near zero post-adjustment | WP/Peer |
| France CAC40 | NOT FOUND | — | — | — | — |
| Brazil B3 (post-2020) | NOT FOUND | — | — | — | — |
| CEE/Poland | NEGATIVE (net) | Zaremba-Konieczka 2015 | Factor premium obliterated by costs | ~0% or negative net | YES |
| Australia ASX | MIXED/POSITIVE | Accounting & Finance 2016 | Style momentum robust | Positive (unquantified, 300bp est.) | YES |
| ML (US stocks) | STRONG | Gu-Kelly-Xiu 2020 (RFS) | Sharpe 1.35 (L/S decile, OOS) | 1.35 Sharpe | YES |
| NLP/text | PROMISING | Ke-Kelly-Xiu 2019 (NBER WP) | Return predictability; Sharpe NR | Positive (unquantified) | NO (WP) |
| Satellite data | INSTITUTIONAL | JAR 2021 (Firm Next Door) | Info advantage for local institutions | Positive for institutions only | YES |
| Credit card data | INSTITUTIONAL | Gupta-Leung-Roscovan 2022 (JPM) | +3.4% excess announcement return | Positive (pre-data-cost) | YES |
| ML alpha decay | NEGATIVE trend | Lee 2025 (arXiv:2512.11913) | Momentum ~2% pa now vs 10% in 1990s | Declining | NO (preprint) |
| Post-publication decay | CONFIRMED | McLean-Pontiff 2016 (JoF) | 58% lower post-publication | Systematic decay | YES |

NR = Not Reported. WP = Working Paper.

---

## CROSS-LANGUAGE CONVERGENCE SIGNALS

1. **PEAD works globally including non-English markets**: India, Saudi Arabia both show significant PEAD that survives risk adjustment. Combined with Taiwan (Barber 2004, baseline) and Brazil (Chagué 2020, baseline), this is a VERY STRONG signal across 4+ markets.

2. **Momentum pre-cost positive, net-of-cost varies**: India (positive), Saudi (positive), Germany (ambiguous after Theissen 2020), Poland/CEE (obliterated by costs), Australia (positive but unstable). The cross-language lesson: momentum is robust pre-cost but highly sensitive to liquidity/transaction-cost environment. The AU case (liquid market, franking credit tax incentive for dividend stocks) differs materially.

3. **ML alpha concentrated in US market**: All ML/alt-data papers (GKX 2020, Ke-Kelly-Xiu 2019) use US data. No non-US academic replication found in this sweep.

4. **Factor decay is confirmed and accelerating post-2015**: Lee 2025 (arXiv) + McLean-Pontiff 2016 both confirm systematic post-publication decay. Momentum specifically has decayed from ~10% pa to ~2% pa (Lee 2025).

---

## NOT FOUND / NOT VERIFIED SECTION

- [NOT FOUND] France/CAC40 momentum factor academic paper — HAL access blocked; no English-language French-specific paper surfaced
- [NOT FOUND] Brazil-specific momentum paper post-2020 (beyond Chagué 2020) — SciELO access requires direct article URLs; general search not productive
- [NOT FOUND] UAE/Qatar-specific equity factor studies — only Saudi Tadawul covered in academic literature found
- [NOT FOUND] Switzerland (SMI) or Austria (ATX) specific factor studies — no results surfaced
- [NOT VERIFIED] Ke-Kelly-Xiu (2019) specific Sharpe ratio — paper accessible but Sharpe not in intro/abstract section; would require full paper reading
- [NOT VERIFIED] Australia ASX momentum Sharpe ratio — paywall on all Australian academic papers; practitioner SGH report suggests ~300bp but no Sharpe stated

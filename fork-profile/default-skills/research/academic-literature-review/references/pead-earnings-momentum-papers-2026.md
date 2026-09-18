# PEAD + Earnings Momentum Academic Literature — Verified Reference Bank
## Cluster B: PEAD Extensions + Earnings Momentum
## Sweep date: August 2026
## Context: Slava's PEAD+momentum strategy; Australian investor (47% tax on sub-12M gains)

---

## Quick-Reference Table

| # | Paper | Year | Journal | DOI / ID | Key Finding | Gross Return | Verified? |
|---|---|---|---|---|---|---|---|
| B-1 | Ball & Brown | 1968 | JAR | 10.2307/2490232 | Founding PEAD: post-announcement continuation documented | Qualitative | ✅ Full text |
| B-2 | Chan, Jegadeesh & Lakonishok | 1996 | JF | 10.1111/j.1540-6261.1996.tb05222.x | SUE+REV6 additive to price momentum | SUE: +4.3% (6M marginal); REV6: +3.8% (6M marginal) | ✅ DOI+NBER |
| B-3 | Sloan | 1996 | TAR | JSTOR 248290 / SSRN 2598 | Accruals anomaly; investor fixation on earnings | ~10.4%/yr (1962–1991) | ✅ Full text |
| B-4 | Livnat & Mendenhall | 2006 | JAR | 10.1111/j.1475-679X.2006.00196.x | Analyst SUE (I/B/E/S) produces ~2× larger drift than time-series SUE | ~6.9% (70d, analyst) vs ~3.2% (time-series) | ✅ DOI confirmed |
| B-5 | Chordia & Shivakumar | 2006 | JFE | 10.1016/j.jfineco.2005.12.004 | Earnings momentum (PMN) not just risk; partially explains price momentum | PMN: ~1.08%/month | ✅ DOI confirmed |
| B-6 | Cohen & Lou | 2012 | JFE | 10.1016/j.jfineco.2011.08.006 | Conglomerate complexity-delay: pseudo-conglomerate signal predicts returns | EW L/S: 118 bps/month; VW: 95 bps/month | ✅ Full working paper |
| B-7 | Green, Hand & Soliman | 2011 | Mgmt Sci | 10.1287/mnsc.1110.1320 | Accruals anomaly attenuated post-2003/04 | Decay evidence — prior ~10.4% not forward-applicable | ✅ DOI confirmed (INFORMS) |
| B-8 | Hong, Lim & Stein | 2000 | JF | 10.1111/0022-1082.00206 | Bad news travels slowly; low-coverage losers have most momentum | Loser-analyst spread: ~0.7%/month | ✅ DOI+NBER |
| B-9 | So & Wang | 2014 | JFE | 10.1016/j.jfineco.2014.06.009 | 6× reversal intensity pre-announcement (liquidity provider premium) | Entry timing tool, not directional | ✅ DOI (scope mismatch: liquidity, not guidance) |
| B-10a | McLean & Pontiff | 2016 | JF | 10.1111/jofi.12365 | 58% post-publication decay for published anomalies | Haircut: PEAD ~4.2% → ~1.8% (60d) | ✅ DOI+SSRN |
| B-10b | Chordia et al. | 2009 | FAJ | 10.2469/faj.v65.n4.3 | PEAD 1.5–3% post-2000 for large/liquid stocks; small-cap retains more | 1.5–3%/60d (post-2000) | ✅ DOI confirmed |
| B-10c | Chordia & Shivakumar | 2005 | JAR | JAR 43(4) 521–556 | Inflation illusion partially explains PEAD | Partial explanation only | ✅ Existence confirmed |
| B-10d | Kettell, McInnis & Zhao | ~2022 | WP | Semantic Scholar: 8fe079008578e10a004787f27a2cfca3d8e5b5f7 | Declining earnings persistence = new structural explanation for PEAD decline | Structural decline (no quant extracted) | ⚠️ Working paper, confirmed via Semantic Scholar |

---

## Detailed Paper Notes

### B-1: Ball & Brown (1968) — Founding PEAD Paper
- **Full citation:** Ball, R. & Brown, P. (1968). "An Empirical Evaluation of Accounting Income Numbers." *Journal of Accounting Research*, 6(2), 159–178.
- **DOI:** 10.2307/2490232
- **Open-access PDF:** http://ww.e-m-h.org/BallBrown1968.pdf (confirmed accessible)
- **Sample:** 261 NYSE firms, 1946–1966. Annual earnings only.
- **Key finding:** Stock prices begin moving before announcement; continue drifting afterward for ≥2 months. Third-order result of the paper (main finding: earnings-returns correlation). No quantified hedge return.
- **Named "PEAD"?** No — the term was coined later. They noted the drift and flagged concerns about peek-ahead and transaction costs.
- **Award:** Inaugural Seminal Contribution to the Accounting Literature Award (AAA). Cited 8,000+ times.
- **Use for Slava:** Context only. Bernard-Thomas (1989) is the quantified baseline (4.2% 60d CAR). Ball-Brown establishes the anomaly exists from 1946 onward.

---

### B-2: Chan, Jegadeesh & Lakonishok (1996) — Momentum Strategies
- **Full citation:** Chan, L.K.C., Jegadeesh, N. & Lakonishok, J. (1996). "Momentum Strategies." *Journal of Finance*, 51(5), 1681–1713.
- **DOI:** 10.1111/j.1540-6261.1996.tb05222.x
- **NBER WP:** 5375 (DOI: 10.3386/w5375) — abstract accessible at nber.org/papers/w5375
- **SSRN:** abstract_id=7836
- **Access:** Full text paywalled at Wiley. NBER abstract free. Key quantitative detail from CJL 1999 *Financial Analysts Journal* 55(6):80–89 (companion/follow-up by same authors, uses same dataset).
- **Key findings (from CJL 1999 FAJ — flagged as companion paper):**
  - SUE marginal contribution (6M, controlling for price momentum): ~4.3%
  - REV6 marginal contribution (6M, controlling for price momentum): ~3.8%
  - Price momentum marginal contribution (6M, controlling for SUE): ~3.1%
  - Signal correlations: R6-SUE = 0.29; R6-REV6 = 0.29; SUE-REV6 = 0.44
  - ~41% of 6-month price momentum returns cluster around subsequent earnings announcement dates
  - Analyst forecasts are sluggishly revised, especially for past losers ("bad news travels slowly" precursor)
  - No subsequent reversals in high-price-momentum OR high-earnings-momentum stocks
- **Mechanism:** Market underreaction to earnings news. Both price and earnings momentum reflect gradual information diffusion.
- **AU-tax note:** 6-month hold → sub-12M → 47% tax. SUE marginal contribution ~4.3% → ~2.3% net.
- **Standalone Sharpe for earnings momentum:** NOT REPORTED in this paper.

---

### B-3: Sloan (1996) — Accruals Anomaly
- **Full citation:** Sloan, R.G. (1996). "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings?" *The Accounting Review*, 71(3), 289–315.
- **JSTOR stable URL:** http://links.jstor.org/sici?sici=0001-4826%28199607%2971%3A3%3C289%3ADSPFRI%3E2.0.CO%3B2-H
- **SSRN:** abstract_id=2598 (bot-blocked in Aug 2026 session)
- **Full text PDF (open):** https://cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR).pdf ✅ confirmed accessible
- **Sample:** NYSE/AMEX, 1962–1991 (30 years)
- **Key finding:** Hedge portfolio (long low-accrual / short high-accrual) → **~10.4% annualised abnormal return**. Positive in 28 of 30 years. Investor "fixation" on reported earnings, failing to distinguish accrual component (low persistence) from cash flow component (high persistence).
- **Mechanism:** High-accrual firms have lower future earnings → market overvalues → subsequent underperformance.
- **Replication:** 1962 sample start is important — post-2003 results are substantially weaker.
- **AU-tax note:** Annual rebalancing (fiscal-year accruals). Holds ≥12 months qualify for **50% CGT discount** under Australian individual tax. Effective tax rate on gains: ~23.5% (47% × 50%). Net of ~10.4% gross: ~7.9%. Post-decay estimate: gross ~4–7% → net ~3–5%.
- **Post-pub decay:** Green, Hand & Soliman (2011) confirm substantial decay post-2003. Richardson, Tuna & Wysocki (2010) independently confirm. Still positive pre-1996; near-zero or very small post-2004 for large-cap.

---

### B-4: Livnat & Mendenhall (2006) — SUE Magnitude & Analyst vs Time-Series
- **Full citation:** Livnat, J. & Mendenhall, R.R. (2006). "Comparing the Post-Earnings Announcement Drift for Surprises Calculated from Analyst and Time Series Forecasts." *Journal of Accounting Research*, 44(1), 177–205.
- **DOI:** 10.1111/j.1475-679X.2006.00196.x ✅
- **JSTOR:** https://www.jstor.org/stable/3542321
- **Access:** Paywalled at Wiley. Abstract from search snippets. Key figures from secondary source (home.business.utah.edu Trading+the+SUE manuscript, 2006 — cites Livnat-Mendenhall 6.9% figure).
- **Sample:** NYSE/AMEX/NASDAQ, 1987–2003
- **Key finding:** Analyst-consensus SUE (I/B/E/S) produces **~6.9% drift (70 days)** vs time-series SUE **~3.2% drift** — roughly 2× difference. Drift monotonic with SUE magnitude (larger |SUE| → larger drift, no documented hard threshold).
- **The "bug-of-the-market" question:** Both analyst-error explanation and time-series-error explanation have incremental explanatory power. Analyst-based measure is empirically superior.
- **Implication for Slava:** Use Bloomberg/Refinitiv I/B/E/S consensus as the earnings benchmark, NOT seasonal random walk. This is an implementation upgrade that improves the signal 2× without changing strategy structure.
- **AU-tax note:** ~70 day hold → 47% tax. Net of 6.9% gross: ~3.7%.

---

### B-5: Chordia & Shivakumar (2006) — Earnings and Price Momentum
- **Full citation:** Chordia, T. & Shivakumar, L. (2006). "Earnings and Price Momentum." *Journal of Financial Economics*, 80(3), 627–656.
- **DOI:** 10.1016/j.jfineco.2005.12.004 ✅
- **SSRN:** abstract_id=342581 (bot-blocked in Aug 2026 session)
- **Related paper:** Chordia & Shivakumar (2005). "Inflation Illusion and Post-Earnings-Announcement Drift." *Journal of Accounting Research*, 43(4), 521–556. — proposes partial risk-based (inflation) explanation for PEAD.
- **Access:** ScienceDirect paywall for full text. Key figures from secondary sources.
- **Key finding (from secondary sources):**
  - PMN (earnings momentum factor): ~1.08%/month (~13%/yr gross) — confirmed via ResearchGate "Hedge Funds and Earnings Momentum" citing same value
  - Price momentum (WML) is partially explained by earnings momentum in U.S. — earnings momentum is the "more fundamental" driver
  - Both PMN and WML survive risk adjustment (Carhart 4-factor) — behavioral explanation preferred
  - PMN is not subsumed by Carhart model
- **Is earnings momentum just risk?** No. PMN alpha not explained by size, value, market, or Carhart momentum. Behavioral underreaction dominant explanation.
- **AU-tax note:** Monthly rebalancing → 47% tax. PMN ~1.08%/month → ~13% gross → ~7% net (abstract/secondary only, not directly confirmed).
- **Post-pub decay:** 2006 publication; decay has occurred since. Apply McLean-Pontiff ~58% haircut for current expectations.

---

### B-6: Cohen & Lou (2012) — Complicated Firms
- **Full citation:** Cohen, L. & Lou, D. (2012). "Complicated Firms." *Journal of Financial Economics*, 104(2), 383–400.
- **DOI:** 10.1016/j.jfineco.2011.08.006 ✅
- **Full working paper PDF (retrieved):** https://static1.squarespace.com/static/5f6349cae367a31c2bc8d676/t/5f75d6450dd0c87c41a478b7/1601558088468/coh_lou.pdf ✅
- **Award:** First Prize, Crowell Memorial Award for Best Paper in Quantitative Investments (2011)
- **Sample:** NYSE/AMEX/NASDAQ conglomerates, 1977–2009 (387 months)
- **Strategy:** For each conglomerate, build a "pseudo-conglomerate" from single-segment industry firms with matching revenue weights. Sort conglomerates on lagged pseudo-conglomerate returns. L/S portfolio.
- **Key findings (direct from working paper):**
  - EW L/S portfolio alpha: **118 bps/month (t=5.51)**; VW: **95 bps/month (t=3.18)**
  - Smaller conglomerates (EW): **122 bps/month** (t=5.13); Larger: **75 bps/month** (t=2.80)
  - Higher idiosyncratic vol: **120 bps/month** (t=4.27)
  - No reversal — effect is persistent, not transient
  - Not driven by industry momentum (Moskowitz-Grinblatt), not by investor inattention
  - Analyst revisions for single-segment firms predict future analyst revisions for conglomerate peers (same delay mechanism)
  - Cumulative 6-month returns to EW hedge portfolio: ~1.5–2% (from Figure 2)
- **Mechanism:** Multi-segment firms require "complicated processing" — more research to incorporate industry shocks into conglomerate prices. Easy-to-analyze firms update first, predicting complex peers.
- **Confirmed by follow-up:** Barinov, Park & Yıldızhan (2022/2024). "Firm Complexity and Post-Earnings Announcement Drift." *Review of Accounting Studies*, 29:527–579. DOI: 10.1007/s11142-022-09727-8. Finds PEAD directly stronger for conglomerates (confirming the earnings-specific application of Cohen-Lou mechanism).
- **AU-tax note:** Monthly rebalancing → 47% tax. 118 bps/month EW → ~14.2% gross → ~7.5% net annually.
- **For Slava:** When a conglomerate has a large earnings surprise, the drift will be larger AND more persistent than for a comparable single-segment firm. This is an overweighting signal, not a separate strategy.

---

### B-7: Green, Hand & Soliman (2011) — Accruals Anomaly Decay
- **Full citation:** Green, J., Hand, J.R.M. & Soliman, M.T. (2011). "Going, Going, Gone? The Apparent Demise of the Accruals Anomaly." *Management Science*, 57(5), 797–816.
- **DOI:** 10.1287/mnsc.1110.1320 ✅ (confirmed Aug 2026 — INFORMS DOI; PSU Pure repository confirmed at pure.psu.edu; IDEAS/RePEC entry confirmed)
- **SSRN:** abstract_id=1501020 (confirmed via search snippet; page bot-blocked for extraction in Aug 2026)
- **CORRECTION NOTE:** Prior entry in this file incorrectly listed this paper as *The Accounting Review* 86(1). That is wrong. "Going, Going, Gone?" is in *Management Science* (INFORMS), DOI confirmed. A separate paper "The Importance of Accounting Information in Portfolio Optimization" may exist in TAR by the same authors — these are distinct papers. The accruals-decay paper is Management Science.
- **Access:** INFORMS paywall. SSRN working paper (abstract_id=1501020) is the accessible version.
- **Key findings (from secondary citations only — flagged [SECONDARY]):**
  - Annual accruals anomaly attenuates after **2003 or 2004** (cited: Tandfonline 2021 "Testing the accruals anomaly based on the speed of price adjustment")
  - Green et al. choose **1996** as the start of their second sub-period (the year Sloan was published/submitted)
  - Pre-1996: accruals hedge returns positive in virtually all years
  - Post-2003/2004: "likely arbitraged away" as sophisticated investors exploited Sloan's results (cited: assets.super.so "The Accrual Anomaly")
  - Richardson, Tuna & Wysocki (2010) independently confirm similar decay timeline
- **Verification status:** Existence confirmed via multiple citing papers; return magnitude in each sub-period NOT confirmed (need full text).
- **For Slava:** The 10.4% gross return in Sloan (1996) is a historical figure from 1962–1991, NOT a forward estimate. Post-2003, realistic gross accruals return for small-cap: ~4–7%. Annual rebalancing still the most tax-efficient structure for AU investors.

---

### B-8: Hong, Lim & Stein (2000) — Bad News Travels Slowly
- **Full citation:** Hong, H., Lim, T. & Stein, J.C. (2000). "Bad News Travels Slowly: Size, Analyst Coverage, and the Profitability of Momentum Strategies." *Journal of Finance*, LV(1), 265–295.
- **DOI:** 10.1111/0022-1082.00206 ✅
- **NBER WP:** 6553 (accessible at nber.org/papers/w6553)
- **SSRN:** abstract_id=226286 (bot-blocked in Aug 2026 session; NBER WP is the better access route)
- **Sample:** NYSE, AMEX, NASDAQ; approximately 1976–1996
- **Key findings (from NBER abstract + secondary sources):**
  - Momentum profitability declines sharply with firm size (past very small-cap)
  - Holding size fixed, momentum stronger for **low analyst coverage** stocks
  - Effect asymmetric: **stronger for past losers than past winners** — low-coverage losers show most momentum
  - "Loser-analyst spread trade" (long P1/SUB3 vs short P1/SUB1): ~**0.7%/month** return differential (t=5.16), size-neutral and momentum-neutral
  - As of 1996: ~60% of NYSE/AMEX/NASDAQ had analyst coverage; bottom-size-quartile had only 18% coverage
  - Mechanism: Managers push out good news voluntarily; bad news sits until analysts drag it out. Analysts are most valuable for bad-news diffusion.
- **Testing model:** Validates Hong & Stein (1999) "gradual information diffusion" model
- **For Slava:** Filter both PEAD long AND short positions for low analyst coverage (≤5 analysts). The short side (negative-surprise, low-coverage stocks) offers the largest additional edge (~0.7%/month spread). Consistent with Livnat-Mendenhall: analyst-based signals outperform time-series signals.
- **AU-tax note:** 0.7%/month analyst spread → ~8.4% gross/year → ~4.5% net at 47%.

---

### B-9: So & Wang (2014) — News-Driven Return Reversals
- **Full citation:** So, E.C. & Wang, S. (2014). "News-Driven Return Reversals: Liquidity Provision Ahead of Earnings Announcements." *Journal of Financial Economics*, 114(1), 20–35.
- **DOI:** 10.1016/j.jfineco.2014.06.009 ✅ (confirmed via ScienceDirect abstract)
- **Access:** ScienceDirect paywall. Abstract only.
- **Key finding:** **6× increase in short-term return reversals during earnings announcements** vs non-announcement periods. Market makers demand higher expected returns prior to earnings due to elevated inventory risk.
- **Scope note:** This paper is about PRE-ANNOUNCEMENT reversal intensity and liquidity provision. It is NOT about management guidance-driven PEAD drift. The task brief described a "guidance-PEAD" paper — this does not match. The guidance-driven PEAD signal was NOT confirmed from this or any other identified paper in this sweep.
- **Implication for Slava:** Do NOT enter PEAD positions in the days before the earnings announcement — that is the reversal window, not the drift window. Enter post-announcement (close of announcement day or next morning after the open confirms direction).

---

### B-10a: McLean & Pontiff (2016) — Post-Publication Decay
- **Full citation:** McLean, R.D. & Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance*, 71(1), 5–32.
- **DOI:** 10.1111/jofi.12365 ✅
- **SSRN:** abstract_id=2156623
- **Key finding:** 97 cross-sectional predictors studied.
  - Out-of-sample decay: ~**26% lower** returns vs in-sample
  - Post-publication decay: ~**58% lower** returns vs in-sample
  - PEAD: included in predictor set (strongly implied by secondary sources citing the paper in PEAD-decay context); PEAD is among the more persistent anomalies vs. accruals or investment-to-assets
- **Forward estimate for PEAD:** Bernard-Thomas 4.2% (60d) × (1 - 0.58) ≈ **~1.8% (60d)** gross after publication haircut
- **Calibration for Slava:** Use 1.8–2.5% (60d) as the realistic gross PEAD return for diversified mid-large cap portfolio today. Small/illiquid stocks may retain 3%+. At 47% tax: ~1.0–1.3% net per 60-day cycle.

### B-10b: Chordia, Goyal, Sadka, Sadka & Shivakumar (2009) — PEAD Decay Evidence
- **Full citation:** Chordia, T., Goyal, A., Sadka, G., Sadka, R. & Shivakumar, L. (2009). "Liquidity and the Post-Earnings-Announcement Drift." *Financial Analysts Journal*, 65(4), 18–32.
- **DOI:** 10.2469/faj.v65.n4.3 ✅ (confirmed Aug 2026 via FAJ/CFA Institute; also confirmed via Deakin University open-access mirror: dro.deakin.edu.au)
- **Access:** CFA Institute paywall. Secondary citation from Alpha Suite (2026).
- **Key finding:** 1972–2005 sample. PEAD 60-day returns:
  - Pre-2000 large-cap: close to Bernard-Thomas levels
  - Post-2000 large/liquid stocks: ~**1.5–3% (60d)** — substantial decline
  - Small/illiquid stocks: larger drift persists
  - Decay concentrated in easy-to-arbitrage names

### B-10c: Chordia & Shivakumar (2005) — Inflation Illusion
- **Full citation:** Chordia, T. & Shivakumar, L. (2005). "Inflation Illusion and Post-Earnings-Announcement Drift." *Journal of Accounting Research*, 43(4), 521–556.
- **Access:** JAR paywall. Multiple citing papers confirm this citation; existence fully verified.
- **Key finding:** Part of PEAD is explained by inflation illusion — investors fail to adjust nominal cash flows for inflation. When inflation is controlled, part of the drift disappears. Partial risk-based explanation (complementary to behavioral).

### B-10d: Kettell, McInnis & Zhao (~2022) — Why Has PEAD Declined Over Time?
- **Full citation:** Kettell (Griffin), L., McInnis, J. & Zhao, W. (~2022). "Why Has PEAD Declined Over Time? The Role of Earnings News Persistence." Working paper, Columbia Business School / University of Colorado Leeds School of Business.
- **Semantic Scholar ID:** 8fe079008578e10a004787f27a2cfca3d8e5b5f7 ✅
- **Author note:** Laura Kettell is now Laura Griffin, Assistant Professor at University of Colorado Leeds School of Business.
- **Access:** Columbia Business School events page PDF returned 404 in Aug 2026. Existence confirmed via Wikipedia PEAD article citations and Semantic Scholar.
- **Key finding:** Post-earnings announcement drift has declined significantly in recent decades. The paper proposes a **new structural explanation**: declining persistence of earnings news (standardized unexpected earnings / SUE have become less autocorrelated over time). If today's positive SUE predicts next-quarter's SUE less reliably, the long-horizon drift from the PEAD signal shrinks even without additional arbitrage. Two competing mechanisms both confirmed: (1) increased arbitrage by hedge funds; (2) declining earnings persistence.
- **Implication:** PEAD decline is partially structural (earnings quality), not just exploitable-by-small-cap. This modifies the naive "just go smaller" advice.
- **Validation from a parallel paper:** Martineau (2021) "Now You See It, Now You Don't: Post-Earnings Announcement Drift Disappears When You Control for Earnings Expectations" — argues PEAD has essentially disappeared when controlling for predictable components. Cross-reference when full text available.

---



| Strategy | Typical Hold | AU Tax | Gross (Current) | Net Estimate |
|---|---|---|---|---|
| Standard PEAD | 60–90 days | 47% | ~1.8–2.5%/cycle | ~1.0–1.3%/cycle |
| Analyst-SUE PEAD (Livnat-Mendenhall) | 70 days | 47% | ~3–4%/cycle | ~1.6–2.1%/cycle |
| PMN earnings momentum (Chordia-Shivakumar) | Monthly | 47% | ~1%/month | ~0.53%/month |
| REV6 analyst revision (Chan-Jegadeesh-Lakonishok) | 6 months | 47% | ~3.8% (6M marginal) | ~2.0% (6M) |
| **Accruals (Sloan)** | **Annual ≥12M** | **23.5% (CGT discount)** | ~4–7%/yr current | **~3–5%/yr** |
| Complicated firms (Cohen-Lou) | Monthly | 47% | ~95–118 bps/month | ~50–63 bps/month |
| Low-coverage loser spread (Hong-Lim-Stein) | Monthly | 47% | ~0.7%/month incr. | ~0.37%/month incr. |

**Key insight:** Accruals (annual rebalance, ≥12M hold) is the ONLY PEAD-family strategy eligible for the 50% Australian CGT discount. This halves the effective tax rate (47% → ~23.5% on gains), making it structurally more tax-efficient than short-horizon PEAD despite lower gross return.

---

## NOT FOUND / NOT VERIFIED

| Item | Status | Note |
|---|---|---|
| ~~Green, Hand & Soliman (2011) specific DOI~~ | ✅ RESOLVED Aug 2026 | Management Science DOI: 10.1287/mnsc.1110.1320 confirmed via INFORMS and PSU Pure. (Prior entry incorrectly cited TAR 86(1).) |
| So & Wang guidance-PEAD paper | ❌ Scope mismatch | So & Wang (2014) is about liquidity reversals, not management guidance. No guidance-driven PEAD paper identified in this sweep. |
| Earnings momentum standalone Sharpe ratio | ❌ Not reported | No paper in cluster directly reports a Sharpe for earnings-only strategy |
| PEAD in McLean-Pontiff 97 predictor list | ⚠️ Inferred | Strongly implied by secondary citations; not confirmed from paper text |
| Chordia et al. (2009) FAJ DOI | ✅ RESOLVED Aug 2026 | DOI confirmed as 10.2469/faj.v65.n4.3 (not .n4.4 as previously listed) via FAJ/CFA Institute and Deakin open-access mirror |

---

## Access Barrier Log (Finance/Accounting Journals)

| Source | Barrier | Workaround |
|---|---|---|
| SSRN (papers.ssrn.com) | Bot-blocked — ALL pages return anti-bot error in Aug 2026 | Use `web_search site:ssrn.com [topic]` for Google-cached snippet; treat as abstract-only |
| Wiley (JF, JAR, JFE) | Full text paywalled | DOI confirmation from IDEAS/RePEC, EconPapers; quantitative results from secondary sources |
| AAA journals (TAR) | Paywall | Some author-hosted PDFs (CUHK workshop site for Sloan 1996) — search `[author] [title] PDF` |
| ScienceDirect (JFE) | Paywall | SSRN working paper versions often exist; confirm via web_search |
| JSTOR | Mostly paywalled; some open | JSTOR stable URLs useful for DOI-equivalent citation; limited content retrieval |
| Full working papers | Usually accessible | Squarespace/author websites host pre-publication drafts (Cohen & Lou confirmed) |
| NBER working papers | Free | nber.org/papers/wXXXX — abstract + full text for many papers |

### TAR-specific access note
*The Accounting Review* (American Accounting Association) is one of the hardest finance/accounting journals to access open-access. No arXiv preprints, no NBER equivalents. Workflow:
1. Search `[author] [year] [title] site:ssrn.com` — often an SSRN preprint exists
2. Search `[author] [title] PDF` — author homepage or workshop posting (e.g., CUHK, Yale SOM)
3. Search Google Scholar style via web_search `[title] filetype:pdf`
4. If inaccessible, confirm existence via DOI at doi.org or JSTOR stable URL, flag [ABSTRACT ONLY]

---

## Implementation Recommendations (PEAD-specific, not in baseline)

1. **Signal construction:** Use analyst-consensus (I/B/E/S) as earnings benchmark, not seasonal random walk — produces ~2× larger drift (Livnat-Mendenhall 2006)
2. **Triple-signal filter:** Price momentum (6M) + SUE (analyst consensus) + REV6 (6M analyst revision trend) — each contributes independently (CJL 1996/1999)
3. **Low-coverage screen:** Filter for ≤5 analyst coverage, especially on SHORT side — bad news travels slowest in low-coverage stocks (Hong-Lim-Stein 2000)
4. **Conglomerate overweighting:** Multi-segment firms show larger and more persistent PEAD — overweight conglomerates in the PEAD book (Cohen-Lou 2012; confirmed by Barinov et al. 2022)
5. **Entry timing:** Enter AFTER earnings announcement; avoid pre-announcement window (So-Wang 2014: 6× reversal intensity pre-announcement)
6. **Return calibration:** Use ~1.8–2.5%/60d as realistic gross (not 4.2%) for diversified portfolios (McLean-Pontiff 2016; Chordia et al. 2009)
7. **Tax-layer design:** Keep accruals (annual hold ≥12M) as a separate "slow layer" for CGT-discount eligibility; PEAD is "fast layer" taxed at 47%
8. **Revenue-quality filter:** Prefer earnings surprises driven by revenue upside over cost-cutting (Cao-Narayanamoorthy 2012 — more persistent drift for revenue-driven surprises)

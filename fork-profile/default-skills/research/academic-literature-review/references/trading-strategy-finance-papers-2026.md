# Trading Strategy & Finance Academic Papers — Verified Reference Bank
*Session: July 2026 — short-to-medium horizon trading strategies for retail investors*
*Domain: finance/quantitative investing (non-ML; confirms skill applies outside NLP/ML)*

## Access matrix for finance-specific non-English repositories

| Repository | Status | Notes |
|---|---|---|
| **CiNii (cir.nii.ac.jp)** | ❌ Scraping blocked / login-wall | Finance papers confirmed to exist; use English-language studies on same markets as fallback |
| **CNKI (cnki.net)** | ❌ Always paywalled | Same as ML research — go to arXiv for Chinese institutional authors; use English-language papers on Chinese markets (Wu 2003 HKIMR) |
| **RISS (riss.kr / intl.riss.kr)** | ❌ Login required for full text | Confirmed live; metadata/abstract accessible; Korean equity research well-covered in English journals (Tandfonline, Emerging Markets Review) |
| **KIISE/DBpia** | ❌ Subscription required | Korean CS conference papers; use RISS abstract pages or English-language Korean finance journals |
| **CyberLeninka (cyberleninka.ru)** | ✅ Confirmed live | Open-access Russian academic library; direct scraping BLOCKED in July 2026 session (previous ML sessions showed it working — may be intermittent / load-dependent) |
| **ResearchGate** | ❌ Anti-bot | Use for existence-confirmation via web_search; do NOT attempt web_extract — returns 403/anti-bot on every call |
| **JSTOR** | ❌ Anti-bot | Same — confirm DOI via web_search, access via direct institutional PDF mirror |
| **faculty.haas.berkeley.edu (Odean)** | ⚠️ Unstable | Some PDFs have moved; try direct DOI or econ.yale.edu mirror |
| **econ.yale.edu (Shiller BehFin)** | ✅ Direct PDF access | Working mirror for Barber et al. (2004) Taiwan day-trading paper |
| **panagora.com (asset manager PDFs)** | ✅ Full text accessible | Qian (2009) Risk Parity paper retrieved successfully |
| **images.aqr.com (AQR research PDFs)** | ✅ Full text accessible | Asness (2011) Japan momentum paper retrieved successfully |
| **bauer.uh.edu/rsusmel (academic mirrors)** | ✅ Full text accessible | Jegadeesh-Titman (1993) full text retrieved successfully |
| **mysimon.rochester.edu/novy-marx** | ✅ Full text accessible | Novy-Marx (2013) gross profitability paper retrieved successfully |
| **tradicted.com** | ✅ Reliable secondary source | High-quality summaries of primary papers with key statistics; good for verification when primary blocked. Cross-reference with SSRN/DOI to confirm existence |

## Verified primary paper quick-reference

| Paper | Key quantified result | Verification status |
|---|---|---|
| Jegadeesh & Titman (1993), JF 48(1):65-91 | 6M/6M US momentum: ~9.5% cumulative return over next 12 months (1965-1989); reversal in years 2-3 | ✅ Full text accessed |
| Rouwenhorst (1998), JF 53(1):267-284 | >1%/month excess return, 12 European markets, 1980-1995 | ✅ DOI + abstract confirmed |
| Asness (2011), JPM 37(4) | Momentum Sharpe ≈ 0 in Japan alone; All-region (incl. Japan) Sharpe = 0.38 (t=2.06); value+momentum 50/50 works in Japan | ✅ Full text (AQR PDF) |
| Wu (2003), HKIMR WP | China A-shares: pure momentum FAILS; contrarian +22.2% annualised (SHSE baseline, 12M/12M); mean reversion half-life ~232 days | ✅ Full text (aof.org.hk) |
| Black & Litterman (1992), FAJ 48(5):28-43 | Global diversification: +85bp at same 10.7% risk; only 2/14 assets get positive weight under standard MVO | ✅ Key stats verified (tradicted + semanticscholar) |
| Markowitz (1952), JF 7(1):77-91 | Foundational efficient frontier; diversification reduces portfolio variance | ✅ DOI confirmed |
| Qian (2009), PanAgora Risk Parity | Risk Parity Sharpe 0.45 vs 60/40 Sharpe 0.36; +90bp/year excess return 1976-2009; stocks = 97% of losses in 60/40 drawdown months | ✅ Full text (panagora.com) |
| Barber, Lee, Liu & Odean (2004), Working Paper | Taiwan TSE 1995-1999: >80% of day traders lose money per 6-month period; gross profits flipped to net losses by transaction costs | ✅ Full text (econ.yale.edu) |
| Chagué, De-Losso & Giovannetti (2020), SSRN 3423101 | Brazil: 97% of >300-day persistent traders lose money net of fees; only 0.5% earn bank-teller salary; no learning effect | ✅ Key stats (tradicted + SSRN abstract) |
| Barber & Odean (2000), JF 55(2):773-806 | 78k US households: 75% annual turnover; high-turnover quintile underperforms market by ~6%/year | ✅ DOI + abstract (Wiley) |
| Henriksson (1984), JBus 57(1,Pt.1):73-96 | 116 mutual funds 1968-1980: no statistically significant market timing ability | ✅ Abstract via multiple secondary sources; direct PDF blocked |
| Treynor & Mazuy (1966), HBR 44(4):131-136 | 57 mutual funds: only 1/57 shows statistically significant timing ability | ✅ Widely cited; confirmed in multiple primary papers reviewed |
| Novy-Marx (2013), JFE 108(1):1-28 | Gross profitability ≈ same predictive power as B/M; profitability monthly excess ~0.26% (t=5.43); momentum ~0.62%/mo in 4-factor model | ✅ Full text (rochester.edu) |
| Frazzini & Pedersen (2014), JFE 111(1):1-45 | BAB factor Sharpe ≈ 0.75 in US equities since 1926; low-beta anomaly in bonds and futures too | ✅ DOI + confirmed via multiple sources |
| DeBondt & Thaler (1985), JF 40:793-805 | 36-month: losers outperform winners by ~24.6% (CAR); concentrated in January | ✅ Cited across primary papers; abstract confirmed |

## Finance-domain fallback strategy for non-English repositories

When CiNii/CNKI/RISS/CyberLeninka are blocked:

1. **For Japanese equity research**: Search English-language journals directly: Asia-Pacific Financial Markets (Springer), Pacific-Basin Finance Journal, Japanese Journal of Finance. Key search: `site:link.springer.com Japan momentum` or `site:sciencedirect.com Japan stock market momentum`
2. **For Korean equity research**: Tandfonline (Emerging Markets Review), International Review of Finance. RISS abstracts often mention the core findings in English.
3. **For Chinese equity research**: Wu (2003) HKIMR working paper (fully open); czi.finance for recent work; arXiv Chinese institutional authors publish finance preprints less commonly than ML but some exist.
4. **For Russian equity research**: ResearchGate abstract pages (verify existence via web_search); HSE Moscow repository (hse.ru/en/edu/vkr) for theses — English abstract often available.
5. **For French/German equity research**: ResearchGate for existence confirmation; Tandfonline / ScienceDirect for full access. German working papers from CFR Cologne (cfr-cologne.de) — some open.

## Key domain knowledge: finance-specific source reliability tiers

**Tier 1 — Primary verified source**: Full text directly accessed (PDF) or DOI/abstract confirmed at publisher. Cite freely.

**Tier 2 — Existence verified, quantified results confirmed**: Abstract confirmed + key statistics available via reliable secondary sources (tradicted.com summaries, SSRN abstracts, multiple consistent secondary citations). Flag as "abstract/secondary confirmed" but report specific numbers.

**Tier 3 — Existence verified, quantified results NOT accessible**: ResearchGate listing or web_search snippet confirms paper exists; full text blocked. Report finding as "EXISTS, quantified results not accessible."

**Tier 4 — Unverified / should not cite**: Papers mentioned in citations of other papers but not independently confirmed. Do not report quantified figures.

## Finance-specific fabrication risk areas

These categories are highest-risk for citation fabrication in finance literature surveys:

1. **Japanese/Korean-language CiNii/RISS papers**: Very easy to hallucinate plausible-sounding author names + titles. Verify via direct web_search before citing.
2. **Specific alpha/Sharpe figures for less-cited strategies**: If a number isn't in the paper's abstract and the full text is blocked, do not report it.
3. **Practitioner whitepapers**: AQR, PanAgora, Bridgewater publish research papers; these ARE citable but are not peer-reviewed. Distinguish from journal publications.
4. **"Australian ASX factor premium" figures**: Industry sources (Betashares, Vanguard AU) cite these but primary academic sources for ASX-specific factor alphas are harder to verify. Treat as partially verified unless you can access the actual S&P/ASX Index research paper.

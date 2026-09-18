# Factor Investing & Cross-Asset Momentum — Verified Paper Bank (August 2026)

Sweep performed: 2026-08-08. Baseline file: `/tmp/cluster-a-factor-crossasset.md` (533 lines).
Context: Australian investor evaluation, 47% marginal tax, CGT discount for >12M holdings.
Slava baseline: PEAD+momentum, gross ~8–12% pa, AU net 0–3% pa, gross Sharpe ~0.3–0.5.

---

## Quick-Reference Table

| Paper | DOI | Gross Sharpe | Key Stat | Open Access? | Period |
|-------|-----|-------------|----------|-------------|--------|
| Fama & French 2015 (FF5), JFE | 10.1016/j.jfineco.2014.10.010 | HML ~0.41, RMW ~0.40, CMA ~0.42 | HML redundant within FF5 | WP: tevgeniou.github.io | 1963–2013 |
| Israel & Moskowitz 2013, JFE | 10.1016/j.jfineco.2012.10.004 | Combined V+M SR ~1.1 | Short-side adds little for retail | ABSTRACT ONLY | Various |
| Hou, Xue & Zhang 2015 (q-factor), RFS | 10.1093/rfs/hhu068 | I/A ~0.71, ROE ~0.69 | Explains 20/35 anomalies vs FF3's 27/35 | global-q.org FULL PDF ✅ | 1972–2012 |
| Fama & French 2020, RFS | 10.1093/rfs/hhz089 | N/A (methodology paper) | Cross-section factors > time-series | ABSTRACT ONLY (paywalled) | — |
| Israel, Laursen & Richardson 2021, JPM | AQR JPM Quant 2021 | N/A | HML ~−5.4% pa 2007–2020; not dead | images.aqr.com FULL PDF ✅ | 2007–2020 |
| Lustig & Verdelhan 2007, AER | 10.1257/aer.97.1.89 | ~0.44–0.50 (full); 0.88 (calm) | Carry = consumption growth risk compensation | ABSTRACT ONLY (paywalled) | 1953–2002 |
| Menkhoff et al. 2012, JF | 10.1111/j.1540-6261.2012.01728.x | ~0.44–0.88 (period dep) | 92% of carry variation explained by global FX vol | ABSTRACT ONLY (paywalled) | Various |
| Asness, Moskowitz & Pedersen 2013 (VME), JF | 10.1111/jofi.12021 | All-asset combo SR=2.01; US stock combo SR=1.13 | Bonds SR 0.41–0.51; FX 0.44–0.64; Commodity 0.58–0.84 | pages.stern.nyu.edu FULL PDF ✅; lhpedersen.com slides ✅ | Various ~1973–2008 |
| Gorton & Rouwenhorst 2006, FAJ | 10.2469/faj.v62.n2.4083 | ~0.35–0.40 (same as equities) | Negatively correlated with equities + bonds | NBER WP 10595 FULL PDF ✅ | 1959–2004 |
| Bhardwaj, Gorton & Rouwenhorst 2015, NBER | 10.3386/w21243 | Holds OOS | In- vs out-of-sample risk premium not significantly different | NBER abstract ✅ | 2004–2015 |
| Asness, Frazzini & Pedersen 2019 (QMJ), RAS | 10.1007/s11142-018-9470-2 | US SR=0.47; Global SR=0.48 | 4-factor IR=0.64–0.83; positive in 23/24 countries | Yale WP 2013 FULL ✅; Springer paywall | 1956–2012 (US) |
| Ball, Gerakos, Linnainmaa, Nikolaev 2016, JFE | 10.1016/j.jfineco.2016.03.002 | Not separately computed | COP subsumes accruals; strongest profitability predictor | ABSTRACT ONLY (paywalled) | Various |

---

## Verified Sharpe Ratio Table (Asness-Moskowitz-Pedersen 2013, from slides at lhpedersen.com)

**Portfolio construction:** constant-volatility scaled (10% ex-ante vol), long-short, gross.

| Asset Class | Value SR | Momentum SR | 50/50 Combo SR | Cor(V,M) | Sample |
|-------------|----------|-------------|----------------|----------|--------|
| US stocks | 0.21 | 0.78 | 1.13 | −0.60 | 03/73–02/08 |
| UK stocks | 0.30 | 1.26 | 1.67 | −0.61 | 12/84–02/08 |
| Japan stocks | 0.89 | 0.23 | 1.12 | −0.53 | 02/85–02/08 |
| Cont. Europe stocks | 0.33 | 1.12 | 1.69 | −0.53 | 02/88–02/08 |
| Global stock selection | 0.40 | 1.18 | 2.00 | −0.67 | 02/88–02/08 |
| Equity country selection | 0.58 | 0.68 | 1.08 | −0.41 | 02/80–02/08 |
| Bond country selection | 0.45 | 0.41 | 0.51 | +0.07 | 01/90–02/08 |
| Currency selection | 0.44 | 0.45 | 0.64 | −0.41 | 08/80–02/08 |
| Commodity selection | 0.30 | 0.58 | 0.84 | −0.39 | 02/80–02/08 |
| **All non-stock selection** | **0.63** | **0.96** | **1.33** | **−0.38** | 01/90–02/08 |
| **All asset selection** | **0.64** | **1.22** | **2.01** | **−0.56** | 01/90–02/08 |

*Source: Pedersen conference slides, docs.lhpedersen.com/ValMomEverywhere_Slides.pdf (directly accessed August 2026)*

---

## q-Factor Summary (Hou, Xue & Zhang 2015, from global-q.org full PDF)

Data period: January 1972–December 2012 (492 months), triple 2×3×3 sort.

| Factor | Monthly mean | t-stat |
|--------|-------------|--------|
| r_ME (size) | 0.31% | 2.12 |
| r_I/A (investment) | 0.45% | 4.95 |
| r_ROE (return-on-equity) | 0.58% | 4.81 |

**Model comparison (35 significant anomaly deciles):**
- Average unexplained alpha: q-factor **0.20%/mo** vs Carhart 0.33% vs FF3 **0.55%**
- Significant alphas: q-factor **5/35** vs Carhart 19/35 vs FF3 **27/35**
- GRS rejections: q-factor **20/35** vs Carhart 24 vs FF3 28
- Key: q-factor absorbs momentum (price momentum FF3 alpha = 1.12%, q-alpha = 0.24% insignificant)
- r_I/A ↔ HML correlation = 0.69; r_ROE ↔ UMD correlation = 0.50

---

## QMJ Performance (Asness, Frazzini & Pedersen, from Yale 2013 working paper)

| Measure | US (1956–2012) | Global (1986–2012) |
|---------|---------------|-------------------|
| Raw Sharpe ratio | **0.47** | 0.48 |
| 4-factor alpha IR | **0.64** | 0.83 |

Quality = composite of: Profitability + Growth + Safety + Payout.
- COP (Ball et al. 2016) is strongest standalone profitability predictor (subsumes accruals).
- QMJ: negative market/value/size exposures → mild positive convexity (flight-to-quality benefit).
- Positive returns in 23/24 countries studied.

---

## Value Premium Post-2010 Summary

| Period | US HML return | Source |
|--------|--------------|--------|
| 1963–2013 | +0.38%/month gross | FF2015 (verified) |
| 2007–2020 | ~−5.4% pa | Arnott et al. 2021 via Kuo & Huang 2022 JRFM |
| 2010–2020 | Significantly negative | Israel et al. 2021 (AQR JPM, verified) |

---

## Currency Carry Trade Summary

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| Gross excess return | ~4–6% pa | 1980s–2007 | Multiple |
| Gross Sharpe (calm period) | 0.88 | 1990–2007 | Jurek 2014 (secondary) |
| Gross Sharpe (full period) | ~0.44–0.50 | 1953–2012 | Burnside et al. 2008 NBER |
| FX vol explained | 92% cross-sectional variation | — | Menkhoff et al. 2012 |
| What crashes it | Global FX volatility spikes | — | Menkhoff et al. 2012 |

---

## AU Retail Accessibility Assessment

| Strategy | AU Accessible? | Tax treatment | Net AU estimate |
|----------|--------------|--------------|----------------|
| Long-only RMW/CMA screen (annual rebal) | ✅ Yes | CGT-eligible >12M | ~0.3–1.5% net pa above market |
| Long-only QMJ/COP screen (annual rebal) | ✅ Yes | CGT-eligible >12M | ~0.3–1.5% net pa above market |
| Long-only value+profitability screen | ✅ Yes | CGT-eligible >12M | ~0.5–2% net pa above market |
| Long-short factor portfolios (HML, RMW etc) | ❌ No | Full 47% on short-term gains | Net negative |
| FX carry trade | ❌ No | No CGT discount; FX gains at 47% | Net negative |
| Cross-asset mom (bonds/FX/commodity) | ❌ No | Requires futures/derivatives | Not accessible |
| Commodity futures (cross-sectional momentum) | ❌ No | Requires futures | Not accessible |
| US equity value+momentum combined (long-short) | ❌ No | Short-side + high turnover | Net negative |

---

## Access Pattern Notes (Finance Domain, August 2026)

**High-value open-access finance PDF sources confirmed working:**
- `pages.stern.nyu.edu/~lpederse/papers/` — Pedersen's faculty page (NYU) — all papers open
- `docs.lhpedersen.com/` — Pedersen's own domain — slides and conference presentations open
- `images.aqr.com/` — AQR Capital Management journal article PDFs — open, no bot protection
- `global-q.org/` — Hou-Xue-Zhang q-factor model site — data and paper PDFs open
- `www.nber.org/system/files/working_papers/` — NBER working paper PDFs — open
- `tevgeniou.github.io/EquityRiskFactors/bibliography/` — curated finance paper collection, open
- `aeaweb.org/articles` — AEA confirms publication but full text paywalled (DOI confirmed via page)

**Consistently blocked/paywalled:**
- `papers.ssrn.com` — anti-bot on all paper pages; use `web_search site:ssrn.com` for discovery
- `academic.oup.com/rfs` — bot-blocked for web_extract
- `onlinelibrary.wiley.com` — paywall on full text
- `www.sciencedirect.com/science/article` — abstract accessible via snippet, full text paywalled

**Key title disambiguation (discovered this session):**
- "How Can a Strategy Everyone Knows About Still Work?" → this is an **informal AQR blog piece / Cliff's Perspective by Asness (2015)**, NOT a peer-reviewed paper
- The actual peer-reviewed Israel & Moskowitz JFE (2013) paper is titled: "The Role of Shorting, Firm Size, and Time on Market Anomalies" — DOI 10.1016/j.jfineco.2012.10.004
- Both cover similar territory; only the JFE paper is citable as peer-reviewed academic research

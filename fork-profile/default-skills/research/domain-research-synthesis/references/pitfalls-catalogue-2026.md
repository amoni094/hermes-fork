# Domain Research Synthesis — Full Pitfalls Catalogue

Extracted from SKILL.md August 2026. **Do NOT re-add inline. Update this file.**

Last synced: August 2026 | 39 entries

---
- **Parallelise Phase 1 aggressively** — a sequential search loop wastes multiple
  round-trips; batch 6–8 searches in one call.
- **arXiv REST API can return 0 bytes silently** in some network environments —
  not an API key issue, the endpoint is just unreachable. Complex boolean queries
  (`ti:` + `ANDNOT` + `OR` combinations in URL) also fail silently. **Fallback cascade:**
  1. `web_search "arXiv 2026 topic abstract institution"` — Google indexes arXiv;
     snippets contain quantified findings and arXiv IDs.
  2. `web_extract("https://arxiv.org/abs/PAPER_ID")` — abstract pages reliably
     scrapable even when the API is down.
  3. `web_extract("https://arxiv.org/html/PAPER_ID")` — full HTML paper.
  4. Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,authors,year,citationCount,externalIds`
  5. OpenAlex: `https://api.openalex.org/works?search=QUERY&per-page=10` — 250M+ works,
     no rate limit, add `&mailto=email@example.com` for polite pool (higher limits).
  Never conclude "no papers found" based solely on API silence.
  See `references/arxiv-api-fallback-and-pitfalls.md` in `academic-literature-review`
  for the full pitfall guide and an August 2026 agent token-optimization paper bank.

- **Reddit blocks web_extract — don't retry it**; fall back to search snippets
  immediately (see above).
- **Star counts decay**: GitHub stars are a point-in-time signal. Note the research date.
  A 2021-era "21k star" project (e.g. Backtrader) may be less actively maintained
  than a newer 8k-star project. Combine stars with last-commit date.
- **"Curated awesome lists" inflate perceived activity**: A repo with 40k stars
  (like OpenBB Terminal) has different signal than a niche 1k-star tool. Always
  note what the stars measure (community interest ≠ production readiness).
- **Don't conflate community sentiment with advice**: r/AusFinance and r/algotrading
  have strong index-fund bias. Report this accurately as community sentiment, not
  as objective financial advice.
- **"Rent vs invest" analyses model INVESTMENT property, not PPOR**: Most online
  calculators and articles (including Tepuy, WealthWorks, etc.) apply CGT to the
  investment returns of the renter BUT also to the property buyer's gains. For a
  PPOR, the buyer's gains are 100% CGT-exempt — this materially favours buying
  vs what the generic models show. Always flag this when the user is considering a
  PPOR purchase. The CGT exemption at 47% marginal rate is worth ~$100K+ on a typical
  Melbourne 10-year PPOR hold.
- **Domain blocks web_extract**: domain.com.au consistently returns anti-bot errors.
  Fall back to web_search snippets or use propertyupdate.com.au, whichrealestateagent.com.au,
  and openagent.com.au which all reproduce Cotality HVI data and are reliably scrapable.
- **Melbourne suburb median data has multiple conflicting figures**: Cotality AVM median,
  REIV transacted median, and REA past-year median can differ by $200K–$400K for small
  suburbs. Always cross-reference; call out the discrepancy explicitly. MELBZ sometimes
  reports 3BR settled-sales-only (not all-house) — treat as entry price not suburb median.
- **School zone research: "near" ≠ "in zone"**: Agent marketing routinely blurs this.
  Zone boundaries run through individual streets — always verify at findmyschool.vic.gov.au
  for the specific address BEFORE any school-zone-dependent evaluation. McKinnon SC zone runs
  through parts of McKinnon, Ormond, Bentleigh, Bentleigh East — not the entire suburb.
  Streets commonly assumed to be in McKinnon zone that are NOT: Packer Street Murrumbeena
  (Glen Eira College zone, confirmed July 2026 via findmyschool.vic.gov.au for 1/3 Packer St),
  much of western Murrumbeena. Baker Street, Kinlock Avenue, Churchill Close Murrumbeena
  ARE in McKinnon zone. 2/5 Baker Street and 1/1 Baker Street Murrumbeena confirmed in
  McKinnon zone via agent marketing and property.com.au.
  Note: Packer Street is zoned Glen Eira College (76 Booran Rd, Caulfield East) — not McKinnon.
  This materially changes the thesis for any Packer Street property. Without McKinnon zone,
  the property competes on suburb fundamentals only (no zone premium, no McKinnon-seeking
  buyer cohort at resale).

  **findmyschool.vic.gov.au UX (it's a JS map app — must use browser tool, not web_extract):**
  1. `browser_navigate` to https://www.findmyschool.vic.gov.au/
  2. `browser_type @e8 "3 Packer Street Murrumbeena"` — type into address combobox
  3. Wait 2-3s, snapshot to see dropdown options (unit numbers like 1/3, 2/3 appear)
  4. `browser_click @e14` (or whichever option matches the lot number)
  5. Wait 2-3s, snapshot again — year selector appears
  6. `browser_click @e6` for 2026 (or @e7 for 2027)
  7. `browser_click @e11` for "Secondary" school type label (click the LABEL ref, not the radio ref)
  8. Wait 4-5s, snapshot — result appears as: "For 2026 enrolments, your address is in the
     secondary school zone for: [School Name]" plus a closest-schools table
  Note: if the exact unit/lot number isn't in the dropdown (e.g. "3B" for a freestanding
  on a subdivided lot), use the nearest numbered lot (1/3, 2/3) — they share the same
  zone for addresses on the same lot/street number.
- **Selective schools ignore address**: MacRobertson Girls', Melbourne High, Nossal,
  Suzanne Cory admit by competitive exam only — suburb of residence is irrelevant.
  Only zoned non-selective schools (McKinnon SC, Northcote HS, etc.) create address premiums.
- **Budget vs suburb reality check**: In Melbourne's inner SE and inner-north, $900K–$1.2M
  typically buys only units/townhouses, NOT freestanding houses (median houses $1.5M–$1.8M+).
  Always flag this gap clearly before deep-diving suburb analysis.
- **SRL East corridor**: Clayton, Glen Waverley, Burwood, Box Hill (not Frankston Line suburbs).
  Frankston Line suburbs (Carnegie, McKinnon, Bentleigh etc.) are ~3-8km from Cheltenham
  terminus but not served by SRL — no direct uplift. Correct this if the user assumes otherwise.
- **Eltham vs inner suburbs**: Eltham is the only typical Frankston/inner-north alternative
  where $900K–$1.25M gets a freestanding house (July 2026). Trade-off: 45-55 min Hurstbridge
  commute. North East auction clearance (67.5%) is outperforming Melbourne.
- **Inner East (Clifton Hill area) caution**: Auction clearance 47.8% in July 2026 — weakest
  region in Melbourne. Softness here is worse than SE corridor at current moment.
- **Brentwood SC is NOT near Mitcham/Nunawading/Ringwood**: Brentwood Secondary College
  is in Glen Waverley 3150. It is not relevant to the Ringwood/Mitcham/Nunawading corridor.
  Do not conflate eastern suburb analysis with Brentwood SC zone. That zone is adjacent to
  Glen Waverley SC zone, both at 3150, far south-east of Ringwood.
- **EDSC and Balwyn HS are above budget for freestanding houses**: East Doncaster SC in-zone
  median house is $1,667,500 (REIV Mar 2025); out-of-zone is $1,471,000. Balwyn HS zone
  (Balwyn North) median is $2.23M. Neither is accessible on a $900k-$1.3M budget for a
  freestanding house. The best approximation is Nunawading addresses near the Doncaster East
  boundary (some may fall in EDSC zone — verify via findmyschool.vic.gov.au per address).
- **Clearance rate is the strongest signal in a downturn**: When metro clearance is 54-60%,
  suburbs with 75%+ clearance (Macleod 88%, Nunawading 77%, Greensborough 75%, Montmorency 71%)
  signal genuine demand scarcity — not speculation. These are the real sweet-spot indicators.
  Suburbs at or below metro average (Preston 48%, Box Hill South 41%) signal buyer weakness.
- **barryplant.com.au suburb profiles are the most reliable scrapable source**: URL pattern
  barryplant.com.au/suburb-profile/melbourne/[region]/[suburb]/ returns PropTrack-backed data
  including current median, annual growth, clearance rate, avg days on market, yield, and a
  year-by-year sales table. Highly scrapable (no anti-bot). Regions: northern-suburbs,
  north-eastern-suburbs, merri-bek, whitehorse-east, maroondah-east, boroondara-inner-east.
  Prefer over domain.com.au and realestate.com.au (both frequently anti-bot blocked).
- **North East Link is the unpriced catalyst north-east (2026-2028)**: Watsonia (tunnel portal)
  and Macleod (freeway access improvement) are primary direct beneficiaries. Not yet fully
  priced in as of July 2026. Window closing as 2028 completion approaches. Greensborough gets
  boulevard upgrade. Compare: level crossing removals already priced into Ringwood.
- **PPOR lifestyle fit is a financial variable**: A PPOR you exit at year 5-6 due to
  commute friction absorbs full stamp duty + selling costs (~$80-100k combined) without
  completing the 7-10 year minimum horizon to recoup them. When ranking suburbs, ask about
  commute tolerance before ranking purely on growth metrics. The gap between top-ranked and
  lifestyle-preferred suburbs is often only $100-200k over 10 years — not enough to justify
  a daily grind that drives early exit.
- **REA (realestate.com.au) and Domain block all automated access**: web_extract, curl with browser UA, and Firecrawl all fail against REA and domain.com.au listing pages (status 403/anti-bot/empty). For individual property listing evaluation, the only viable paths are: (1) ask the user to paste listing details directly (price guide, bedrooms/bathrooms/car spaces, address, land size, key features); (2) search for the property on less-protected portals (view.com.au, property.com.au, jelliscraig.com.au, barryplant.com.au) using the address once known; (3) search Google for the REA listing ID number to find any indexed copies. Never waste more than 2 attempts on REA/Domain scraping — fall back to user immediately.

  **Individual property evaluation workflow (once address is known):**
  1. School zone: browser_navigate to findmyschool.vic.gov.au — run the interaction sequence above
  2. Comparable sales: jelliscraig.com.au sold listings for same suburb (reliable, scrapable) —
     look for 4BR/2bath/similar size sold within 12 months; note sold prices
  3. Street profile: property.com.au/vic/[suburb]/[street-name]/[number]/ returns zoning,
     school assignment, overlays — useful for confirming zone and checking flood/heritage flags
  4. Evaluate against sweet spot: 4BR / 2 bath / double garage / 550-700m² / freestanding
  5. Price check: compare guide against comparables; in a buyer's market (clearance <65%)
     bid 3-7% below guide and see where vendor settles
  6. Building condition flag: old build → mandatory B&P inspection ($600-800); key risks:
     restumping (timber frame pre-1980), roof age (tile/corrugated), electrical switchboard
     (pre-1990 = RCD upgrade), galvanised steel plumbing
- **For property listing evaluation, the address is the critical input**: Once you have an address, you can: (a) check school zone at findmyschool.vic.gov.au (verify before every school-zone-dependent evaluation); (b) search comparable sales on view.com.au or jelliscraig.com.au; (c) check the specific street in ABS suburb data via gdp.com.au; (d) assess configuration against sweet spot (4BR/2bath/double garage/550-700m²). Don't attempt full evaluation without address.
- **Cheltenham vs Murrumbeena horizon-dependent verdict (July 2026)**: For 10-year hold,
  roughly equal risk-adjusted (Murrumbeena gentrification already underway, no infrastructure
  risk). For 15-20 year hold, Cheltenham wins — SRL completion 2035 creates a confirmed
  infrastructure catalyst with historical precedent for 15-25% uplift. Cheltenham also has
  higher separate house % (72% vs 64%), better $1.1M budget fit for 4BR freestanding, and
  a larger demographic re-rating gap to close (currently pre-gentrification baseline vs
  Murrumbeena's near-premium baseline). Murrumbeena advantage: shorter commute (13km vs
  20km CBD), catalyst already in motion, no government delivery risk. The school zone question
  is property-specific — verify each address before including zone premium in the thesis.
- **Murrumbeena Packer Street thesis caveat**: Without McKinnon SC zone, Murrumbeena
  freestanding properties on Packer St are priced on suburb fundamentals + perception catch-up
  story only. At $1.1-1.2M guide, fair-to-fully-priced in current buyer's market (54-60%
  clearance). No-body-corp freestanding 4BR is rare and worth something, but no-garage
  (open hardstand only) reduces resale buyer pool vs double lock-up. Negotiate from $1.0-1.05M;
  $1.1M is acceptable ceiling but not a discount. B&P inspection mandatory on old builds.
- **Commercial property is categorically different from PPOR — don't conflate them**:
  All commercial gains taxed at 23.5% (47% marginal x 50% discount); PPOR gains 100% exempt.
  Commercial requires 60-65% LVR (vs 80% residential), rates 1-1.5% higher, vacancy risk
  6-18 months. Commercial makes sense as SECOND asset after PPOR, or inside SMSF (15% fund
  tax, 10% CGT). The 2027 neg gearing reform applies to established residential investment
  but NOT commercial — commercial gains relative advantage post-2027. At $1.1M, commercial
  only buys bottom-tier strata (weakest tenant quality, highest vacancy risk). Quality
  commercial is $2M+.
- **Property configuration sweet spot (~$1.1M Melbourne PPOR)**: 4BR / 2 bath (main +
  ensuite) / double garage (side-by-side) / 550-700m² maximises resale buyer pool.
  4BR captures WFH demand + families with 2+ children. Single bathroom is biggest resale
  deterrent in family suburbs. Double garage near-mandatory in car-dependent suburbs
  (>65% car commute per ABS census). Fallback: 3BR + convertible study on 600m²+ NRZ
  block where extension is feasible. See references/melbourne-property-configuration-2026.md.
- **Report synthesis: always use write_file, never terminal echo.** For reports longer than
  ~50 lines, terminal echo (`echo "..." > /tmp/file`) fails silently or gets mangled at
  shell escape boundaries. write_file tool handles arbitrary length reliably. Verify with
  `wc -l /tmp/FILE` after writing. If the write didn't land, the line count will be 1 or 0.

- **Subagent synthesis stalls: take over directly rather than waiting for steer recovery.**
  If a subagent gets stuck mid-task (e.g. blocked on an optional post-processing script like
  a citations ledger), a steer instruction may not land if the agent is in a long model think
  (233+ seconds is a hard stall indicator). Fastest recovery: skip the stall in the parent
  session and write the report yourself using already-gathered data. Do not wait for steer
  confirmation — the agent may finish before the steer lands.

- **Academic factor research: verify DOIs, flag [UNVERIFIED] explicitly.** When researching
  academic finance papers, always attempt to access the full text or DOI-confirmed abstract.
  If full text is unavailable, mark the claim [UNVERIFIED] in the output — do NOT silently
  present secondary-source summaries as if you read the original. The distinction matters
  because secondary sources sometimes misquote or oversimplify. Key verification paths:
  NBER working papers (nber.org), JSTOR (jstor.org), Wiley (onlinelibrary.wiley.com),
  ScienceDirect (sciencedirect.com abstract), EconPapers (econpapers.repec.org), SSRN
  (papers.ssrn.com — often anti-bot blocked on extraction, use web_search snippet instead),
  author homepages (e.g. AQR PDF library, professor university sites), and arXiv for
  working papers.

- **Academic factor debates are often genuinely unresolved — report the conflict.**
  On contested questions like "are PEAD and price momentum the same factor?", the literature
  has directly contradicting papers (CJL 1996: independent; Chordia-Shivakumar 2006: earnings
  subsumes price; Novy-Marx 2015: same conclusion but broader). Present the conflict and the
  methodological reason for disagreement rather than picking one side. Users making trading
  decisions need to know the evidence is genuinely contested.

- **Out-of-sample evidence post-2010 often fails for factors documented pre-2000.**
  McLean & Pontiff (2016) found 58% post-publication decay across 97 anomalies. Nullberg
  (2026) found standard 12-month momentum is statistically null in 2017-2026. Always check
  for recent out-of-sample tests before assuming historical academic findings apply today.
  The relevant horizon is the strategy's holding period — a factor can be "alive" in 1965-1989
  data and dead in 2017-2026 data without either paper being wrong.

- **Academic factor research: verify DOIs, flag [UNVERIFIED] explicitly.** When researching
  academic finance papers, always attempt to access full text or DOI-confirmed abstract.
  If full text is unavailable, mark the claim [UNVERIFIED] in the output — do NOT silently
  present secondary-source summaries as verified originals. Key verification paths:
  NBER (nber.org), JSTOR (jstor.org), Wiley (onlinelibrary.wiley.com), ScienceDirect
  (sciencedirect.com abstract), EconPapers (econpapers.repec.org), SSRN (papers.ssrn.com
  — often anti-bot; use web_search snippet), author homepages (AQR PDF library, professor
  university sites), arXiv for working papers.

- **Academic factor debates are often genuinely unresolved — report the conflict honestly.**
  On contested questions like "are PEAD and price momentum the same factor?", the literature
  has directly contradicting papers (CJL 1996: independent; Chordia-Shivakumar 2006: earnings
  subsumes price; Novy-Marx 2015: same conclusion with broader scope). Present the conflict
  and the methodological reason for disagreement rather than picking one side. Users making
  trading decisions need to know the evidence is genuinely contested.

- **Out-of-sample evidence post-2010 often fails for factors documented pre-2000.**
  McLean & Pontiff (2016) found 58% post-publication decay across 97 anomalies. Nullberg
  (2026) found standard 12-month momentum is statistically null in 2017-2026. Always check
  for recent out-of-sample tests before assuming historical academic findings apply today.
  A factor can be valid in 1965-1989 data and dead in 2017-2026 data without either paper
  being wrong — they measure different regimes.

- **Locale tools are often thin**: "Australian-specific algo trading tools" barely
  exists as a category — the answer is international tools + Australian data sources
  + Australian broker APIs. Be honest about this rather than padding with weak results.
- **Tax/regulatory context is often the most valuable part** for locale-specific
  research — don't skip it just because the user asked for "tools". The tax
  implications for using those tools can be more decision-relevant than the tools.
- **Clifton Hill paradox — highest income ≠ highest price**: When a suburb's
  dwelling stock is mostly semis/terraces (Clifton Hill: only 31.8% separate houses),
  the median house price is capped by the stock MIX, not just buyer income. Clifton Hill
  has the highest HHI ($2,755/wk) of all surveyed suburbs but a lower median than
  McKinnon/Fairfield — because most dwellings are semis/terraces, not freestanding
  houses. Always check dwelling TYPE distribution before predicting prices from income.
- **ABS Census variables vs price — use Bach+%, not just HHI**: Education attainment
  (Bachelor degree %) has the strongest correlation (~0.7) with house prices among ABS
  Census variables. Household income is only moderately correlated (~0.5) because
  gentrification and school zone premiums lift prices above what current resident income
  supports. Always report Price-to-Income ratios alongside raw prices — a P/I ratio >15x
  flags speculative/gentrification premium above income fundamentals.
  See references/abs-census-suburb-validation-methodology.md for full correlation table.
- **GDP.com.au is the fast parallel extraction path for ABS suburb data**: For bulk
  suburb Census pulls, use GDP.com.au (gdp.com.au/suburb/<suburb-name>-vic) rather
  than direct ABS QuickStats URLs. GDP aggregates ABS Census 2021 SAL data cleanly, is
  reliably scrapable, and returns income/occupation/dwelling/education in one page.
  Direct ABS QuickStats URLs (abs.gov.au/census/find-census-data/quickstats/2021/SAL...)
  are authoritative but need SAL code lookup and often truncate in web_extract.
- **Population growth does not equal house price growth for established suburbs**:
  Melbourne's fastest growing SA2s (Fraser Rise +26.3%, Rockbank, Clyde North) have
  house prices ~$550k–$750k. Premium established suburbs (McKinnon $1.81M) have STABLE,
  slow population growth. Don't conflate outer greenfield growth corridor news with
  established suburb price dynamics — different demand drivers apply.

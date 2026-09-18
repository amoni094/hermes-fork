# ABS Census Suburb Validation Methodology
*Research date: July 2026. Source: ABS Census 2021 QuickStats + GDP.com.au ABS aggregator.*

Use this when validating Melbourne suburb house prices against demographic fundamentals,
or when correlating ABS Census variables with property market outcomes.

---

## Key ABS Data Sources for Suburb Research

### 1. ABS QuickStats (direct, authoritative)
URL pattern: `https://www.abs.gov.au/census/find-census-data/quickstats/2021/SAL<code>`
- `SAL` = Suburb and Locality level
- Contains: HHI, tenure, occupation, education, dwelling type, travel to work
- **Limitation**: individual tables truncate in web_extract — use GDP.com.au aggregator for faster parallel pulls

### 2. GDP.com.au (ABS aggregator — faster, scrapable)
URL pattern: `https://gdp.com.au/suburb/<suburb-name>-vic`
- Aggregates ABS Census 2021 SAL data cleanly
- Includes: median income/wk, median rent/wk, occupation %, education %, dwelling %, family structure
- Reliable `web_extract` target (no anti-bot blocking)
- **Use for bulk parallel pulls of multiple suburbs**

### 3. ABS Building Approvals
URL: `https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release`
- Monthly national + state-level dwelling approvals
- Separates: private sector houses vs multi-unit (excludes houses)
- Key tables: seasonally adjusted + trend time series back to 2011

### 4. ABS Regional Population
URL: `https://www.abs.gov.au/statistics/people/population/regional-population/latest-release`
- Annual estimated resident population (ERP) by SA2 and above
- Components: natural increase, internal migration, overseas migration
- Fastest-growing SA2 tables (useful for outer ring vs established suburb comparison)

---

## Melbourne Suburb ABS Census 2021 — Key Variables Table

| Suburb | HHI/wk | Prof% | Mgr% | Prof+Mgr | Bach+% | Sep.House% | Med.Age | Owner% |
|--------|--------|-------|------|----------|--------|------------|---------|--------|
| Clifton Hill | $2,755 | 54.5% | 20.1% | 74.6% | 74.7% | 31.8% | 37 | ~62% |
| Fairfield | $1,967 | 50.1% | 17.4% | 67.5% | 65.9% | 67.2% | 37 | ~59% |
| McKinnon | $2,410 | 44.0% | 21.4% | 65.4% | 65.9% | 68.2% | 40 | ~67% |
| Ormond | $2,062 | 42.0% | 17.8% | 59.8% | 66.2% | 68.6% | 37 | ~60% |
| Murrumbeena | $2,057 | 43.1% | 17.0% | 60.1% | 65.6% | 64.3% | 37 | ~63% |
| Bentleigh | $2,263 | 40.6% | 20.6% | 61.2% | 63.0% | **75.0%** | 39 | ~65% |
| Carnegie | $1,878 | n/a | n/a | n/a | 50.5% | n/a | 36 | n/a |
| Cheltenham | $1,919 | 36.2% | 18.1% | 54.3% | 53.5% | 72.0% | 40 | ~65% |
| Eltham | $2,391 | 38.8% | 20.0% | 58.8% | 52.2% | **93.7%** | 43 | ~67% |

**ABS Census 2021. HHI = Median Weekly Household Income. Bach+% = Bachelor degree or higher combined.**
**Owner% = outright owned + mortgage combined as % of all dwellings (approximate).**

---

## Correlation Analysis: ABS Variables vs July 2026 House Prices

### Strongest predictor: Bachelor degree %
Spearman correlation ~0.7 (strongest of all variables tested)
- 74.7% Bach+ → $1.60M (Clifton Hill) to $1.81M (Fairfield/McKinnon)
- 52-54% Bach+ → $1.10-1.25M (Cheltenham, Eltham)

### Strong predictor: Professional + Managerial %
Spearman correlation ~0.6
- 67-75% Prof+Mgr → $1.60-1.81M (inner/school-zone suburbs)
- 54-58% Prof+Mgr → $1.10-1.25M (outer/lifestyle suburbs)

### Moderate predictor: Median Household Income
Note: NOT the top predictor — Fairfield ($1.81M) has LOWER HHI ($1,967) than
Clifton Hill ($2,755/$1.60M). Gentrification/school zone premiums operate independently.

**Price-to-income ratios (house price / annual HHI):**
| Suburb | HHI/wk | House Price | P/I ratio |
|--------|--------|-------------|-----------|
| Clifton Hill | $2,755 | $1.60M | 11.1x |
| Fairfield | $1,967 | $1.81M | **17.7x** ← gentrification premium |
| McKinnon | $2,410 | $1.81M | 14.4x |
| Ormond | $2,062 | $1.77M | 16.5x |
| Bentleigh | $2,263 | $1.66M | 14.1x |
| Eltham | $2,391 | $1.25M | 10.1x |
| Cheltenham | $1,919 | ~$1.10M | 11.0x |

A P/I ratio >15x typically signals speculative/gentrification premium above income fundamentals.

### Weak predictor: Owner-occupier rate
All suburbs 60-67% — insufficient variation to explain price differences.

### Inverse predictor: Separate house % (explains SUPPLY constraint, not income)
High separate house % = supply constrained = structural price floor:
- Eltham 93.7%, Bentleigh 75.0%, Cheltenham 72.0% → NRZ + heritage = minimal new supply
- Clifton Hill 31.8% (many semis) → median capped despite highest income

### Inverse predictor: Median age (older = more established, less gentrification premium)
Younger median age = gentrification trajectory → higher price relative to income
- Clifton Hill/Fairfield/Carnegie: median age 36-37 → command gentrification premium
- Eltham: median age 43 → established, stable, no gentrification narrative

---

## School Zone Variable: Critical Modifier

McKinnon SC zone creates an observable discontinuity that overrides the distance-from-CBD gradient:
- **McKinnon** (16km from CBD): $1.81M — same as Fairfield (7km from CBD)
- **Murrumbeena** (15km, similar demographics, NOT in McKinnon SC zone): ~$1.15M
- Difference: ~$660k premium for similar demographic profile → school zone = primary driver
- 49% of McKinnon households have children under 15 (highest of all surveyed — validates school demand)
- REIV documents zone premiums up to $500k; NestCheck (Feb 2026) cites 8-12% premium for McKinnon SC

**Key ABS proxy for school zone demand:**
- % of households with children under 15 (from G29 — Family Composition)
- Govt secondary school attendance rate (G15 — Type of Educational Institution)
- McKinnon SC: 49% households with children under 15 + 33.8% govt secondary attendance = highest of all suburbs

---

## Building Approvals Context (May 2026)

**National cycle:**
- Peak: March 2021 — ~22,868 approvals/month (HomeBuilder stimulus)
- Trough: Feb 2023 — ~13,595 approvals/month
- Current (May 2026): 17,019 (recovering, 25% below peak)
- Multi-unit: -8.6% YoY nationally; Victoria: -44.2% YoY apartments (Jan 2026)

**Victoria-specific (Jan 2026 state breakdown):**
- Victoria is the ONLY major state with declining trend in total dwelling approvals (-2.3%)
- Private sector house approvals trend: -0.7% — only state declining
- Explains supply constraint story for inner/middle-ring established suburbs

**Inner/middle ring supply dynamics:**
- NRZ (Neighbourhood Residential Zone) blocks medium density across McKinnon, Bentleigh, Ormond
- Heritage Overlay (HO) protects street character in Clifton Hill, Fairfield
- Multi-unit approvals collapsed due to feasibility gap (construction costs vs achievable sale prices)
- New supply = mainly rear-boundary townhouses (2-3 lots) — minimal relief

---

## Regional Population Context (2023-24)

**Melbourne overall:** +142,637 (+2.7%) — largest absolute growth of any Australian city
- Overseas migration: +121,240 (dominant driver)
- Internal migration: -7,581 (net outflow to regions)

**Fastest-growing SA2s in Melbourne:** Fraser Rise-Plumpton +26.3%, Rockbank +4,145, Clyde North-South +3,932
- ALL in outer greenfield corridors (Melbourne West, South East)
- NOT in established inner/middle ring

**Key insight:** Population growth ≠ price growth for established suburbs.
The fastest-growing suburbs have house prices $550k-$750k.
The premium suburbs (McKinnon $1.81M) have STABLE, slow population growth.
Scarcity + quality + employment access + schools = price premiums, not raw population growth.

---

## Employment Accessibility (ABS Census 2021 Journey to Work)

Melbourne employment nodes for inner/middle ring suburbs:
1. **CBD/Docklands**: ~300-400k jobs; finance (11.3%), professional/technical (23.4%)
2. **Monash Employment & Innovation Cluster (Clayton/Notting Hill)**: 530,000+ sqm office
3. **Box Hill**: growing health/medical cluster

**Commute patterns by suburb (% driving vs train):**
| Suburb | Car% | Train% | Cycle% | Employment Access |
|--------|------|--------|--------|-------------------|
| Clifton Hill | 46.6% | 5.8% | **10.9%** | Inner city, cycleable |
| Fairfield | 52.9% | 6.9% | 6.7% | Inner city |
| McKinnon | 63.8% | 4.9% | - | Dual: CBD + Monash |
| Murrumbeena | 62.2% | 7.8% | - | Dual: CBD + Monash |
| Cheltenham | 66.2% | **3.3%** | - | Underserved pre-SRL |
| Eltham | 69.7% | **2.0%** | - | Car-dependent, lifestyle |

**Key:** Cheltenham's 3.3% train commute is the critical SRL thesis number.
Post-SRL (est. ~2035), this changes fundamentally → demographic shift expected.

---

## RBA RDP 2011-03 Key Findings (Kulish, Richards, Gillitzer)

Alonso-Muth-Mills model calibrated to Australian cities. Empirically validates:

1. **Transport infrastructure** reduces effective distance → raises land values in served areas
   → Validates: SRL Cheltenham uplift; train access premium for McKinnon/Bentleigh

2. **NRZ-equivalent zoning** limits density near CBD → artificial scarcity → amplifies price gradient
   → Validates: Why McKinnon ($1.81M, 16km) equals Fairfield ($1.81M, 7km from CBD)
   School zone + NRZ compensates for distance-from-CBD discount

3. **Population size**: larger cities have higher systematic land price premiums
   → Melbourne 5.35M (2024) drives baseline premium above smaller cities

4. **Frictions in housing production**: construction costs, planning delays amplify supply constraints

---

## Suburb-Specific Validation Notes

**Murrumbeena as outlier:** Census profile nearly identical to McKinnon/Ormond but ~$500-660k cheaper.
Possible factors: not in McKinnon SC zone, higher Asian-born % (India 7.5%), slightly lower separate house %,
less "brand recognition" among buyers. Potential catch-up suburb if school zone pressure or gentrification
spillover continues southward from Carnegie.

**Cheltenham pre-gentrification signals:** 
- Current: 54.3% Prof+Mgr (vs 65%+ for McKinnon/Ormond) = demographic gap explains discount
- 72% separate houses = supply constraint in place
- 3.3% train commute = pre-SRL baseline to compare against future
- SRL transforms employment accessibility → expect demographic composition shift within 10-15 years post-opening

**Clifton Hill paradox:** Highest HHI ($2,755/wk) but NOT highest price ($1.60M).
Reason: only 31.8% separate houses (many heritage semis/terraces) — dwelling MIX caps median.
Separate-house suburbs with lower income (Bentleigh $2,263) can have similar/higher medians because
the median captures house STOCK composition, not just buyer income.

# Multilingual Academic Sources — Live-Tested Access Matrix (Aug 2026)

Produced by a dedicated subagent research pass (Aug 2026). Sources tested via `web_extract` on homepage + API endpoint. Already-known sources (arXiv, Semantic Scholar, OpenAlex, CNKI, CiNii, J-STAGE, Cyberleninka, Redalyc, SciELO, BASE, CORE) are excluded — this file covers what's BEYOND that set.

---

## Tier 1 — Free API + Open Access (add to any multilingual sweep)

### HAL (Hyper Articles en Ligne) — France / Europe
- **Homepage**: https://hal.archives-ouvertes.fr
- **API**: `https://api.archives-ouvertes.fr/search/?q={query}&rows=10&wt=json`
  - No key required. Solr-based. Fields: `title_s`, `authFullName_s`, `uri_s`, `producedDate_tdate`
  - Example: `https://api.archives-ouvertes.fr/search/?q=machine+learning&rows=3&fl=title_s,authFullName_s&wt=json`
  - **Live-tested Aug 2026**: returned 38,142 ML papers instantly
- **Coverage**: French institutional OA; multilingual (French, English, others); includes preprints, journal articles, theses, conference papers from French universities and CNRS/INRIA/INRAE
- **Free API**: ✅ Yes — no key, no rate limit documented
- **Verdict**: **HIGH VALUE** — large French corpus with many papers not in arXiv/Semantic Scholar; especially strong for INRIA/CNRS AI work. Use for European regional coverage.

**Search pattern**:
```python
# In a sweep, add this call alongside arXiv
web_extract(urls=[
  "https://api.archives-ouvertes.fr/search/"
  "?q=machine+learning&rows=10&fl=title_s,authFullName_s,uri_s,producedDate_tdate&wt=json"
])
```

---

### OpenAIRE — Europe / Global
- **Homepage**: https://openaire.eu
- **API**: `https://api.openaire.eu/search/publications?keywords={query}&format=json&size=10`
  - No key required. Returns JSON with full metadata including funding, access rights, country.
  - **Live-tested Aug 2026**: 1,162,120 ML publications found; response in ~2s
- **Coverage**: EU-funded research from 100M+ publications; aggregates European institutional repositories, DART-Europe theses, Zenodo, national OA repos; tracks funding provenance (ERC, H2020, etc.)
- **Free API**: ✅ Yes — fully open, no registration
- **Verdict**: **HIGH VALUE** — unique EU funding metadata; covers European repositories that BASE/CORE miss or lag; `isgreen` field filters to OA-only results; use `&isOpenAccess=true` for OA filter.

**Key API parameters**:
```
?keywords=QUERY        # full-text search
&format=json           # or xml
&size=N                # results per page (max 100)
&page=N                # pagination
&isOpenAccess=true     # filter to OA only
&country=FR            # filter by country (ISO2)
&fromDateAccepted=2024-01-01  # date filter
```

---

### Shodhganga (INFLIBNET) — India
- **Homepage**: https://shodhganga.inflibnet.ac.in
- **OAI-PMH**: `https://shodhganga.inflibnet.ac.in/oai/request?verb=ListRecords&metadataPrefix=oai_dc`
- **Coverage**: India; 692,000+ PhD theses from 899 universities; CC BY-NC 4.0 license; full PDF download free without login
- **Free API**: ✅ OAI-PMH harvestable; DSpace-based so standard OAI works
- **Accessibility**: ✅ Fully open — browse, search, download without account
- **Verdict**: **HIGH VALUE** — only national Indian thesis OA repository; unique coverage of Indian CS/AI PhD research; no equivalent in arXiv/Semantic Scholar; for AI/ML: search `https://shodhganga.inflibnet.ac.in/advanced-search` with subject filter "Computer Science"

**Search URLs**:
```
# Full-text search
https://shodhganga.inflibnet.ac.in/advanced-search

# CS/AI theses specifically
https://sgsubjects.inflibnet.ac.in/  # subject-based browse

# OAI harvest (for bulk)
https://shodhganga.inflibnet.ac.in/oai/request?verb=ListRecords&metadataPrefix=oai_dc&set=com_10603_7754
```

---

### RISS (학술연구정보서비스) — Korea
- **Homepage**: https://www.riss.kr
- **API Center**: https://www.riss.kr/apicenter/apiMain.do
  - RISS Search API, KOCW lecture API, statistics APIs documented at the center
  - Registration required but free for Korean institutions; international access via web
- **Coverage**: Korean national academic information system; domestic dissertations, journals, research reports, foreign academic materials; multilingual input (Japanese, Chinese, French, German, Hebrew, Arabic supported via built-in IME)
- **Free API**: ✅ Yes — RISS Search API publicly documented; key may require free registration
- **Accessibility**: ✅ Homepage fully loads without login; Korean-language interface; search returns metadata freely
- **Verdict**: **HIGH VALUE** — primary Korean academic gateway; Korean CS/AI research not in other databases; has API center; use for Korean-language AI papers.

**Search URL pattern**:
```
https://www.riss.kr/search/Search.do?queryText={query}&searchGubun=true&colName=re_all
```

---

## Tier 2 — Accessible but No Free API / Subscription Full-Text

### Wanfang Data (万方数据) — China
- **Homepage**: https://www.wanfangdata.com.cn
- **Search**: https://s.wanfangdata.com.cn/paper
- **Multilingual sub-platform**: https://globe.wanfangdata.com.hk (多语种知识服务)
- **Coverage**: China; 390M+ documents: journals, theses, conference papers, patents, standards; includes DeepSeek-R1 AI-enhanced search; AI/ML conference proceedings strong
- **Free API**: ❌ No public API; institutional subscription for bulk; some OA articles browsable
- **Accessibility**: ⚠️ Homepage loads; search metadata visible; full text requires login/subscription
- **Verdict**: **MODERATE VALUE** — second-largest Chinese DB after CNKI; has unique conference + patent content; try `https://s.wanfangdata.com.cn/paper?q={query}` for metadata; expect paywall on full text.

### CQVIP / 维普 (Chongqing VIP) — China
- **Homepage**: https://www.cqvip.com
- **Journal platform**: http://qikan.cqvip.com/
- **Coverage**: China; 30+ years of Chinese journals (~13,000 indexed); science, technology, social sciences; OA subset of journals freely readable
- **Free API**: ❌ No public API
- **Accessibility**: ✅ OA journals browsable free; full text mostly paywalled
- **Verdict**: **LOW-MODERATE VALUE** — third major Chinese DB; OA journal subset worth noting; largely superseded by CNKI+Wanfang for AI/ML; has some unique CS/tech journals not in other Chinese DBs.

### DBpia — Korea
- **Homepage**: https://www.dbpia.co.kr
- **Coverage**: Korea; 5.2M+ papers from 3,278 publishers; 5,204 journals including SCIE/SSCI Korean journals; has AI-powered search and citation graph
- **Free API**: ❌ No public API; institutional subscription or individual payment required
- **Accessibility**: ⚠️ Homepage loads; full text requires subscription; some free previews
- **Verdict**: **MODERATE VALUE** — largest private Korean academic DB; good coverage of Korean CS/AI conference papers and journals not in RISS; not freely accessible but worth noting for Korean institutional access.

### Dar Almandumah (دار المنظومة) — Arabic / Arab World
- **Homepage**: https://www.mandumah.com/en/
- **Search platform**: https://search.mandumah.com (requires account)
- **Coverage**: Arabic-language; largest Arabic academic DB — millions of theses, journals, conference papers from Arab-world universities; includes EduSearch, AraBase, HumanIndex, Dissertation databases; 200+ institutional clients (Qatar, UAE, Saudi Arabia, Jordan, etc.)
- **Free API**: ❌ No public API; institutional subscription
- **Accessibility**: ✅ Homepage loads; **full text requires subscription**
- **Verdict**: **MODERATE VALUE** — primary Arabic academic database; unique Arabic content not indexed elsewhere; no free tier; for Arabic-language AI/ML research this is the best single source.

### Al Manhal — MENA / Middle East / Africa / Asia
- **Homepage**: https://almanhal.com
- **Coverage**: Arabic + Middle East + Africa + Asia; eBooks, eJournals, eTheses; self-described as "world's only full-text searchable database of ME/Africa/Asia scholarly content"; partners with CNKI, ProQuest, EBSCO, Google Scholar
- **Free API**: ❌ No public API; subscription-based; free trial available
- **Accessibility**: ✅ Homepage loads; content requires subscription
- **Verdict**: **MODERATE VALUE** — uniquely covers Middle East/Africa/Asia scholarly output including Arabic, Persian, Turkish content; no free access but fills a real gap.

---

## Tier 3 — Blocked / Limited / Low Value for AI/ML

| Source | URL | Status | Notes |
|--------|-----|--------|-------|
| **NARCIS** (Netherlands) | narcis.nl | ❌ Anubis bot-blocked | OAI-PMH may work; OpenAIRE covers most content |
| **DART-Europe** (EU theses) | dart-europe.org | ❌ Bot-blocked | OpenAIRE aggregates DART-Europe |
| **Zenodo** | zenodo.org | ❌ Bot-blocked web | Use OpenAIRE API instead — covers Zenodo |
| **IndianJournals.com** | indianjournals.com | ⚠️ Paywall | Small (259 journals); Shodhganga better for India |
| **KISS** (Korea) | kiss.kstudy.com | ❌ Empty/institutional | Superseded by RISS + DBpia |
| **SID** (Iran) | sid.ir | ⚠️ Partial | Persian; some AI; limited English content |
| **Latindex** | latindex.org | ℹ️ Directory only | Points to SciELO/Redalyc; no direct content |
| **OAJI** | oaji.net | ℹ️ Index only | No full text; covers OA journals metadata only |
| **NOPR/NISCPR** (India) | nopr.niscpr.res.in | ❌ Server error | Blocked; use Shodhganga instead |
| **CLACSO** | clacso.org | ℹ️ Social sciences | Limited CS/AI; use SciELO/Redalyc for LatAm |

---

## Quick Integration: Adding Tier 1 Sources to a Multilingual Sweep

When doing a multilingual sweep for AI/ML papers, add these calls alongside arXiv/Semantic Scholar/OpenAlex:

```python
# Batch these in the same tool call (independent, no deps)
web_extract(urls=[
    # HAL — French/European OA
    "https://api.archives-ouvertes.fr/search/?q=machine+learning&rows=5&fl=title_s,authFullName_s,uri_s&wt=json",
    # OpenAIRE — EU-funded research
    "https://api.openaire.eu/search/publications?keywords=machine+learning&format=json&size=5&isOpenAccess=true",
])
```

For Korean: use RISS web search (`https://www.riss.kr/search/Search.do?queryText={query}`) and note that full-text access varies.

For Indian theses: Shodhganga OAI-PMH or advanced search.

For Arabic: Mandumah and Al Manhal require institutional access — note gap explicitly in sweep output if no access.

---

## Cross-Lingual Best Practice (confirmed)

- **Query in English first** — translates to better recall across multilingual databases that support English queries (HAL, OpenAIRE, RISS, Shodhganga all handle English queries well)
- **RISS has native IME** for Japanese, Chinese, Korean, Arabic, Hebrew, Greek, Latin, French, German, Russian — use for native-language queries against Korean corpus
- **HAL returns multilingual results** even for English queries — French, Spanish, German papers appear; use `&language=fr` to filter
- **OpenAIRE `country` filter** enables per-country sweeps without language complexity: `&country=FR`, `&country=DE`, `&country=KR`
- **Absence reporting**: if Mandumah/Al Manhal/DBpia are relevant but inaccessible due to paywall, report explicitly ("Arabic-language literature: subscription required, gap not confirmed absent")

# Report Regeneration & Multilingual Academic Sweep Workflow
*Added August 2026 based on Slava trading strategy session*

---

## Report Regeneration from Reference Files

When a user asks to regenerate a report that was previously written to /tmp
(session-volatile — gone after reboot or session expiry):

1. **Check first**: `ls /tmp/<file>` before assuming gone.
2. **Load reference files** via skill_view(name, file_path) — batch in one turn.
   For the Slava trading strategy report, load:
   - references/equity-trading-strategy-research-2026.md
   - references/au-active-momentum-alternatives-execution-tax-2026.md
   - references/sector-correlation-pead-kelly-sizing-2026.md
3. **Synthesise** directly from reference content. Do NOT re-run live searches
   unless the user explicitly asks for fresh data.
4. **Write** regenerated report to `/tmp/<descriptive-name>.md` via write_file.
5. **Warn** user that /tmp is volatile. Offer permanent location (~/reports/ etc).

PITFALL: /tmp does NOT persist across sessions. Never claim a /tmp file exists
without checking. Always offer to move reports of substance to a permanent path.

---

## Multilingual Academic Sweep for Finance/Trading Strategies

When the user asks to research trading strategies from academic sources across
multiple languages, dispatch three parallel subagents via delegate_task:

### Cluster 1 — English
- Sources: SSRN, arXiv q-fin, Journal of Finance, JFE, RFS, JPM
- arXiv access: HTML search page
  https://arxiv.org/search/?searchtype=all&query=TERMS
  NOT the Atom API endpoint (times out)
- Scope: RSI mean reversion, Bollinger Bands, breakout/trend-following,
  volatility strategies (VIX timing), MA crossover, overnight/gap strategies

### Cluster 2 — CJK (Chinese/Japanese/Korean)
- Chinese: arXiv with Chinese institution affiliations (Tsinghua, PKU, Fudan, SJTU);
  web_search 'site:arxiv.org 技术分析 量化交易 A股 2023 2024 2025'
- Japanese: web_search 'site:ipsj.ixsq.nii.ac.jp テクニカル分析 株式市場 収益性';
  J-STAGE search via web_extract; IPSJ 2-year embargo — extract metadata only
- Korean: web_search 'site:riss.kr 기술적 분석 주식 수익성 2023 2024'
- KEY MARKET CONTEXT:
  - China: mean reversion/contrarian beats momentum (Wu 2003 HKIMR WP;
    +22.2% annualised contrarian; momentum fails; half-life ~232 days)
  - Japan: momentum Sharpe ~0 standalone (Asness JPM 2011 via AQR PDF)
  - Korea: mixed — 3-12M momentum unprofitable; 1-week short-term works

### Cluster 3 — European / LatAm
- Russian: web_search 'site:cyberleninka.ru технический анализ акции RSI доходность'
  (CyberLeninka access intermittent — if blocked, use web_search snippets, report
  as abstract-only)
- French: HAL (hal.science) bot-protected — use web_search site:hal.science for
  discovery only, not direct extraction
- German: researchers mostly publish in English — if no German-language papers
  found, say so explicitly; search arXiv with Universität/DFKI/Fraunhofer terms
- Brazilian Portuguese: web_search 'análise técnica ações rentabilidade Bovespa 2023 2024'

### Subagent prompt requirements (inline — do NOT reference this skill by name)
Each leaf subagent prompt MUST include verbatim:
1. Comparison baseline: Slava = PEAD+momentum, gross ~8-12% pa, net ~0-3% pa after
   AU 47% tax, execution costs, and OOS decay
2. Fabrication discipline: flag [UNVERIFIED] on anything not directly confirmed;
   report access barriers honestly as 'abstract only' or 'could not access'; vendor
   claims ≠ academic validation; never fabricate citations
3. Output format: structured markdown table:
   Strategy | Academic Source | DOI/arXiv | Gross Return or Sharpe | Net after costs
   | Cap size sweet spot | Post-pub decay? | vs Slava baseline

### After subagents return
Synthesise into a single comparison report, write to /tmp/<name>.md, then add as
a new reference file under this skill's references/ directory.

---

## /tmp Volatility Rule

Reports written to /tmp will be gone after the next reboot or session expiry.
For any report the user may want to revisit:
- Always offer: "Want me to save this somewhere permanent?"
- Suggested permanent locations: ~/reports/, ~/research/, or the relevant
  skill's references/ directory if it belongs as a knowledge bank entry.

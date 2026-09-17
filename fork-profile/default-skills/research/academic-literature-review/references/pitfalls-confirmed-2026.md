# Confirmed Pitfalls — Academic Literature Review (2026)

Full pitfall catalogue extracted from SKILL.md to keep the main file under the 80KB limit.
Last synced: August 2026. Update this file; do NOT re-add inline to SKILL.md.

---

## Loop-cap vs. context-exhaustion (two distinct subagent failure modes)

Two failure modes look similar (subagent exits without writing the file) but have different fixes.
- **Loop-cap** (api_calls < 15, todos not complete): subagent got stuck cycling the same query.
  Fix: retry with the explicit SEARCH STRATEGY block (in SKILL.md Phase 1); cap at 2 attempts/topic.
- **Context-exhaustion** (api_calls > 15 AND todos show completed): subagent ran out of
  context budget between completing research and calling write_file.
  Fix: retry with CRITICAL write-file instruction prominently at the top of the prompt;
  the subagent needs to prioritize writing before context runs out, not after.
Do not retry a context-exhaustion failure with the loop-cap fix — they are different problems.

---

## Inherited/baseline citation fabrication — re-verify before building on them

Confirmed July 2026 on a legal AI-agent-evaluation critique continued from a *compacted context summary* (not a fresh user request). The summary asserted several highly specific citations as already-established findings — "Sugimoto et al. (2025), Inter-Rater Reliability in AI-Driven Case Assignment: A Japanese Legal Corpus Study, CiNii", "Wang & Li (2026), Transparency Risks of LLM-as-Judge in Legal Allocation, CNKI", a "Case Assignment Fairness Corpus" (Japan, 12,000 labeled records), and a "Legal Allocation Bias Dataset" (EU/HAL, attributed to "European Commission 2026", 8,500 records). Running the *exact* native-language search workflow this skill prescribes (CiNii, CNKI-adjacent, HAL, direct + translated queries) found **no trace of any of the four** — not a paywall, not an access barrier, just absent. These read as plausible-sounding fabrications that had entered the reference material upstream (likely a prior session's hallucination, laundered into "established fact" by a context-compaction summary that gets treated as ground truth). Rule: when resuming or extending a sweep via a compacted summary or an existing reference file you didn't personally verify, **re-check every named-author/named-dataset citation independently before repeating it** — a specific-sounding citation (author names, year, venue, exact N-count for a dataset) is not evidence it exists. Flag unconfirmable citations explicitly as "unverified — could not locate, recommend striking" rather than quietly re-citing them forward into yet another document; each pass that repeats an unverified citation without re-checking makes it look more established than the last.

**Second confirmed instance (same critique, later round, July 2026)**: a compacted-context summary asserted "a 2025 draft of ISO/IEC 27043:2026 (Annex C on AI-generated logs)" and "NIST IR 8497 (2025) extending SP 800-86 to AI systems" as already-verified findings, complete with a plausible-looking DOI. Direct verification against iso.org's own OBP listing and multiple standards-catalog mirrors confirmed **ISO/IEC 27043 has no 2026 revision and no Annex C — the sole published version remains 2015, with zero AI-specific content**; no primary NIST source (csrc.nist.gov) confirms an "NIST IR 8497" of that description either. Standards-body citations (ISO/IEC, NIST SP/IR numbers) are exactly as fabricable as author/dataset citations and need the identical treatment: check the standards body's own current listing directly (iso.org OBP, csrc.nist.gov/pubs) rather than trusting a specific-sounding number+title+date combination. This is now a repeating failure mode specifically tied to context-compaction summaries carrying forward prior-session citations as settled fact — treat every citation in a compacted summary as unverified until independently re-confirmed, not just the ones that feel surprising.

---

## Regulatory commentary can directly contradict the primary standard

Confirmed July 2026 (zen/elt-memo research sweep). A LinkedIn practitioner post stated "APRA CPS 230 requires notification within 24 hours" — the primary standard text at apra.gov.au/standards/cps-230 says 72 hours for a material operational risk incident. The 24-hour figure does not exist in CPS 230. When a generated output (e.g. an AI-written memo) states a regulatory notification clock, verify it against the primary standard, not commentary, practitioner summaries, or third-party explainers. Use the official regulator's own publication page as the canonical source. This applies to all regulatory timeframes, thresholds, and applicability tests — not just APRA standards.

---

## Verify regulatory/legal scope claims against the primary text, not an inherited paraphrase

Same session — a prior draft asserted an internal, in-house-only AI matter-allocation tool "qualifies as high-risk under EU AI Act Annex III (legal services) if linked to access to justice (e.g. pro bono case distribution)." Reading Annex III point 8 directly (`aiactinfo.eu/annex/3`) shows it covers systems used *by or on behalf of a judicial authority*, or in alternative dispute resolution — not internal corporate case-routing. This is the regulatory-domain version of the citation-verification pitfall above: a plausible-sounding *applicability* claim needs the same treatment as a plausible-sounding *citation* — pull the primary clause/article text and check the actual trigger conditions (who must use it, what output, what extraterritorial nexus) before asserting a law applies. Don't accept an inherited conflation (e.g. "access to justice" broadly vs. "used by a judicial authority" specifically) just because it appeared in earlier framing.

---

## Institutional attribution drift

arXiv abs pages show author names but not affiliations. Web-search the author name + institution for verification. Especially important for flagship results (e.g., ICML Oral papers).

---

## Venue from arXiv "Comments" field

The arXiv abs page often shows "Comments: ICML 2025 Oral" or "NeurIPS 2025" in the metadata. `web_extract` on the abs page catches this; pure API XML requires parsing the `<arxiv:comment>` element.

---

## Publication year vs. arXiv submission year

A paper submitted Dec 2024 and accepted NeurIPS 2025 should be listed as NeurIPS 2025. Check the venue, not just submission date.

---

## Named techniques ≠ unique papers

EAGLE-1 (ICML 2024), EAGLE-2, EAGLE-3 (NeurIPS 2025) are separate papers from the same group. Verify version numbers.

---

## "Significant improvement" with no numbers

Flag these explicitly rather than echoing the claim. Reviewers and future sessions need actual numbers.

---

## Geographic coverage gaps

Major regions (Japan, Korea, Germany) often publish at systems venues (OSDI, USENIX ATC, EuroSys) not just ML venues (NeurIPS, ICML, ICLR). Include systems conferences for infrastructure/efficiency work.

---

## Japanese institutional research — IPSJ/CiNii access model

IPSJ Digital Library (ipsj.ixsq.nii.ac.jp) enforces a **two-year embargo** on SIG Technical Reports and symposium papers. The PDF download link is visible but returns a login wall or payment prompt (¥660 non-member) until the embargo expires. The record page itself is always accessible and contains title, authors, institution affiliations, abstract, ISSN, and publication date — extract all metadata from the record page. CiNii (cir.nii.ac.jp) is an aggregator that redirects to IPSJ for most CS papers — treat it as a discovery index, not a separate extraction target. Open-access IPSJ papers (Transactions on Digital Practices, some symposia) publish PDFs directly; attempt web_extract on the PDF URL to test. Do NOT attempt browser_navigate on IPSJ — Chromium dependencies may not be present; use web_extract and web_search throughout.

---

## Korean institutional research — RISS/DBpia/KIISE access model

RISS (riss.kr) is the Korean government aggregator; abstract and metadata are freely accessible but full text requires institutional login. DBpia (dbpia.co.kr) hosts KIISE conference papers; abstract visible, full text requires subscription. KoreaScience (koreascience.or.kr) offers partial open access for some KISS/KIPS journals — try direct extraction. Practical workflow: extract what you can from the record page (Korean abstract, authors, publication date, venue, UCI/DOI), then translate the abstract in-context rather than chasing the full PDF. KIISE conference index at `sub.kiise.or.kr/conference/{year}/KSC/paper_index.asp` is fully public and lists all papers with presenter names — useful for topic scanning without login.

---

## Lawwave.kr — HIGH-SIGNAL Korean in-house legal practitioner channel ✅

Fully open. Publishes named qualitative fieldwork series with in-house counsel at named major Korean corporates (당근마켓, 현대제철, 엘박스, large chaebol legal teams). Extracts real adoption patterns, governance approaches, and barriers with lawyer quotes. Not peer-reviewed but citable as primary qualitative fieldwork evidence (named sources, identifiable organisations). Confirmed July 2026: lawwave.kr/feel/1071 yielded detailed evidence on zero-friction AI governance design, Korean LegalTech ecosystem (ElBox AI, 슈퍼로이어), and in-house AI adoption curve. Use `web_extract` directly; full text accessible without auth. Search pattern: `site:lawwave.kr AI 사내변호사 [year]`. Treat as Tier 1 qualitative practitioner evidence for Korean corporate legal technology.

---

## PyTorchKR weekly AI/ML digest ✅ — HIGH-SIGNAL Korean research curation channel

Fully open, no auth required. Posts weekly digests of 8–10 selected AI/ML papers with detailed Korean-language explanations. URLs follow the pattern `discuss.pytorch.kr/t/YYYY-MM-DD-MM-DD-ai-ml/{post-id}`. Also cross-posts to sigco.tistory.com. Use `web_search 'site:discuss.pytorch.kr AI ML 논문 YYYY-MM'` for discovery, then `web_extract` on the thread URL for full content. Confirmed July 2026: the Jun 29–Jul 5 2026 digest surfaced AutoMem, Memora, PreAct, AdaCoM, Latent Agents, SkillComposer, and MOSS — several appeared in this digest *before* English-language Twitter/HuggingFace daily-papers coverage completed. Treat PyTorchKR as a primary discovery channel for Korean-community-curated English arXiv papers.

---

## French/Russian/Ukrainian/German non-English repositories — access matrix

- **TALN / talnarchives.atala.org** ✅ Fully open — direct PDF download, complete index. Primary French NLP conference (ATALA). Full proceedings accessible. **TALN 2026 confirmed open July 2026**: main proceedings at `talnarchives.atala.org/TALN/TALN-2026/index.html`; EvalLLM workshop at `talnarchives.atala.org/ateliers/2026/evalLLM/index.html`. Conference held June 29–July 3 2026, Nantes. Use `web_extract` on index page for full paper list, then `web_extract` on individual `.html` résumé pages for abstracts — these are always accessible even when the PDF is large. Key 2026 findings in agent efficiency domain: xLadder (#15, memory-efficient PEFT), AutoBenchmark for conversational agents (#733466 EvalLLM), Sem-G-RAG (#30), parametric vs. contextual memory conflict quantification (EvalLLM Qwen3.5 paper). Also check `coria-taln-2026.ls2n.fr/programme/` for the full session schedule.
- **HAL (hal.science)** ❌ Bot protected — returns 403 on direct scrape. Use `web_search site:hal.science` for discovery then browser navigation for specific papers.
- **CyberLeninka (cyberleninka.ru)** ✅ Fully open — Russian open-access repository. Use `web_extract` directly on article URLs. Full paper text visible. `site:cyberleninka.ru` search works well. **IMPORTANT CAVEAT:** CyberLeninka coverage is domain-dependent. For fast-moving or newly-coined terminology (e.g. `нейро-символический ИИ`), CyberLeninka may return general NN articles instead of the actual field. In that case, route to **mathnet.ru** (RAS journals, including *Trudy SPIIRAS*) and **rscf.ru** (Russian Science Foundation grant database) — these are the real channels for Russian Academy of Sciences neuro-symbolic AI research. Confirmed July 2026 NeSy sweep: key Russian NeSy papers (Smirnov/Shilov/Ponomarev, SPC RAS, ontology-oriented NeSy for collaborative decision support) found via mathnet.ru and rscf.ru, NOT CyberLeninka.
- **eLibrary.ru** ❌ Login required — no unauthenticated access. Skip; use CyberLeninka as Russian alternative.
- **ACL Anthology UNLP workshop (aclanthology.org/2024.unlp-*)** ✅ Open — Ukrainian NLP research published here since 2022. Direct PDF extraction works.
- **UA-LLM project (uallm.org)** ✅ Open — indexes Ukrainian LLM research; papers link to arXiv.
- **ela.kpi.ua** ❌ No public search index. Not useful for discovery.
- **nbuv.gov.ua (Ukrainian national library)** ❌ Public interface does not return LLM/AI queries usefully. Skip.
- **GI Digital Library (gi.de)** ❌ Institutional access only. Not publicly indexable.
- **German NLP research generally**: German AI/NLP researchers publish in English at international venues (ACL, EMNLP, NeurIPS, ICML) — no German-language academic AI corpus exists separately. Search arXiv with `"Universität" OR "DFKI" OR "Fraunhofer" OR "Technische Universität"` affiliation terms. Semantic Scholar German institution filtering does not work via web search.

---

## CyberLeninka scraping reliability is session-dependent

The access matrix lists CyberLeninka as open (confirmed in ML-domain sessions), but a July 2026 finance-domain session found direct web_extract blocked. Treat it as "usually open, sometimes blocked" — if web_extract fails on cyberleninka.ru, fall back to web_search with `site:cyberleninka.ru [topic in Russian]` to get Google-cached snippets and confirm paper existence, then treat as abstract-only. Do not declare CyberLeninka permanently unavailable from a single blocked session.

---

## AU-tax structuring for trading strategy research

Always distinguish sub-12M (ordinary income, 47%) from annual-hold (CGT discount, ~23.5% effective) strategies. Confirmed August 2026 (Slava PEAD sweep). When researching trading strategies for an Australian individual investor, the tax treatment depends entirely on holding period. Strategies with sub-12M holds (nearly all short-horizon quantitative strategies: PEAD 30–90 days, earnings momentum monthly, analyst revision momentum 6M) are taxed at marginal income rate (~47% for high earners). Strategies with ≥12M holds (accruals, annual value/quality factors, some carry strategies) qualify for the **50% CGT discount** — effectively halving the tax rate to ~23.5% on gains. This is a **first-order consideration** for net return estimation. When writing up a finance literature sweep for AU context: (a) always compute net return separately for sub-12M and ≥12M strategies; (b) flag whether each strategy is structurally CGT-discount-eligible by its typical holding period; (c) note that sub-12M PEAD gains are ALL taxed as ordinary income — no CGT discount, no averaging — making high gross returns necessary just to justify the strategy after tax.

---

## Accounting journals (TAR, JAR, JAE) are the hardest finance journals to access open-access

*The Accounting Review* (TAR, American Accounting Association), *Journal of Accounting Research* (JAR), and *Journal of Accounting and Economics* (JAE) have no arXiv equivalents, no NBER working paper analogues, and limited SSRN preprint coverage. In August 2026 sweeps, SSRN was bot-blocked for all page extraction, Wiley was paywalled, and AAA's own site had no free access. Working access hierarchy: (1) search `[author] [year] [title] PDF` — some papers are author-hosted at workshop sites or university repositories; (2) search `[title] filetype:pdf` via web_search; (3) confirm existence via JSTOR stable URL or DOI at doi.org; (4) use IDEAS/RePEC or EconPapers for DOI lookup + abstract; (5) flag [ABSTRACT ONLY] and rely on secondary sources for specific return figures. Specific confirmed open copies: Sloan (1996) TAR at CUHK workshop page (cuhk.edu.hk/acy2/workshop). This is a systematic access barrier, not a one-session transient issue.

---

## Practitioner asset-manager PDFs (AQR, PanAgora, Bridgewater) are directly accessible

Unlike journal paywalls, many asset-manager research PDFs are hosted on their own domains and serve without anti-bot protection. Confirmed July 2026: AQR (images.aqr.com), PanAgora (panagora.com) PDFs returned full text via web_extract. These are high-quality, methodologically rigorous sources for finance surveys — citable as working papers / practitioner research (clearly distinguish from peer-reviewed journals in citations).

---

## Faculty finance PDF domains are high-yield open-access sources

Confirmed August 2026. The following domains consistently serve full PDFs with no bot protection: `pages.stern.nyu.edu/~lpederse/papers/` (Lasse Pedersen, NYU), `docs.lhpedersen.com/` (Pedersen's own domain), `global-q.org/` (Hou-Xue-Zhang q-factor model site), `tevgeniou.github.io/EquityRiskFactors/` (curated finance paper collection). Pattern for finance literature sweeps: **web_search to get the DOI and confirm existence → web_extract on the author-hosted PDF or NBER WP → only fall back to journal abstract if both fail**.

---

## Blog piece / "Cliff's Perspective" vs. peer-reviewed paper — verify the actual venue

Confirmed August 2026. "How Can a Strategy Everyone Knows About Still Work?" is an informal **AQR blog post / Cliff's Perspective piece by Cliff Asness (2015)** — it has no DOI, no SSRN ID, and is not peer-reviewed. The underlying peer-reviewed research is Israel & Moskowitz (2013), "The Role of Shorting, Firm Size, and Time on Market Anomalies," *Journal of Financial Economics* 108(2): 275–301, DOI 10.1016/j.jfineco.2012.10.004. **Rule: when a task assigns a paper title and venue, verify the actual peer-reviewed citation independently — if search finds a blog/perspective piece rather than a journal article, flag the discrepancy and report the real JFE/JF/RFS paper.** This pattern recurs with AQR's "Cliff's Perspective" series, Research Affiliates' "Rethinking the Equity Risk Premium" essays, and similar practitioner-blog series.

---

## Subagent context-budget truncation before write_file in multi-paper research sweeps

A research subagent performing 10+ web_search/web_extract calls can exhaust its context budget AFTER completing all searches but BEFORE executing the final write_file step. The live log ends with "Now I have enough data to write..." followed by a todo update — then terminates with no output file on disk. Detection: `ls -la /tmp/cluster-*.md` after delegation returns. Confirmed August 2026 (Cluster B PEAD extensions sweep). Fix on retry: (1) Add a CRITICAL block to the goal stating file write is mandatory and must be confirmed with `terminal('ls -la <path>')` before declaring done; (2) offer a heredoc fallback if write_file fails; (3) state in context that prior research was complete so the retry can skip rediscovery and go straight to synthesis+write. Prevention: instruct research subagents to write partial findings files after every 3-4 papers. **Confirmed working instruction pattern (August 2026, Cluster C sweep):**
```
CRITICAL OUTPUT STEP: After all research, write /tmp/cluster-c-noneng-ml.md. Use write_file tool. Then confirm with terminal('ls -la /tmp/cluster-c-noneng-ml.md'). This is the most important step — do not skip it.
```
The `terminal ls` confirmation step is load-bearing: it gives the subagent an external verification action that prevents "declared done without writing" because the subagent must observe the file actually exists before declaring completion.

---

## Search results returning off-topic popular-culture content signal a FAILED query

Confirmed August 2026 (Cluster C sweep). A search for `machine learning factor alpha decay crowding academic 2022 2024` returned results including an IMDB movie page, a Grammy awards YouTube video, and an unrelated Turkish university site. This is a DISTINCT failure mode from: (a) weather/medical results (a known pitfall for country-name queries), and (b) SerpApi 429 rate-limiting. When popular-culture/entertainment content appears in results for an academic query, the search provider's intent-detection has completely misclassified the query — retrying the same terms will not help. Correct response: **immediately change to different search terms**. Never interpret popular-culture garbage results as evidence the research doesn't exist — it's a query failure, not a coverage gap. Log as [SEARCH FAILED — query varied] and note the alternate query used.

---

## 50-search-per-turn cap requires batching discipline for multi-market sweeps

Hermes enforces a hard cap of 50 `web_search` calls per turn (loop_web_search_cap guardrail). A multi-market literature sweep (7 markets + 4 ML topics = 11 parallel tracks) will easily exceed this if searches are issued sequentially. **Required discipline for multi-market sweeps:** (1) Open with ONE large batch of independent parallel searches (12+ calls in a single tool block); (2) follow with ONE batch of targeted follow-ups on the most promising hits; (3) extract key papers and STOP — 3 rounds maximum before writing up findings. Do NOT issue individual searches one-at-a-time or iterate "one search → evaluate → next search" — this burns the cap before all markets are covered. When the guardrail fires mid-sweep, write up findings from what you have and flag the incomplete coverage explicitly. Confirmed August 2026 (Cluster C non-English + ML sweep): cap fired after 50 calls. See `references/noneng-markets-ml-altdata-papers-2026.md` for verified findings up to the cap.

---

## Finance-specific non-English repository access matrix (August 2026)

Beyond the general access matrix above, finance/quantitative research has its own venue landscape:
- **SSRN (papers.ssrn.com)** ❌ Bot-blocked for web_extract — ALL paper pages return anti-bot error. Use `web_search` with `site:ssrn.com [topic]` for DISCOVERY via Google snippets; snippet text often contains the key claim. Cannot extract full abstracts programmatically.
- **CFR Cologne (cfr-cologne.de) working papers** ✅ FULLY ACCESSIBLE — PDF download URLs work reliably via web_extract. URL pattern: `cfr-cologne.de/download/workingpaper/cfr-XX-XX.pdf`.
- **Chicago Booth faculty PDFs (dachxiu.chicagobooth.edu, etc.)** ✅ FULLY ACCESSIBLE — faculty-hosted PDFs return full text.
- **NBER working papers (nber.org/system/files/working_papers/)** ✅ FULLY ACCESSIBLE — PDF accessible. Note: NBER WPs are NOT peer-reviewed; classify as working papers.
- **SciELO Brazil (scielo.br)** ⚠️ Requires direct article URL — homepage and index pages accessible but `site:scielo.br` searches do NOT surface finance papers via general web search. Must know a specific article URL to extract. General search with `site:scielo.br momentum acao bolsa` returns SciELO index pages only.
- **HAL France (hal.science)** ❌ Bot-protected — 403 on all pages. Use `web_search site:hal.science [topic in French]` for discovery. Even then, mostly returns thesis pages, not working papers. Very limited for French finance research.
- **IIMA Data Library (faculty.iima.ac.in/iffm/)** ✅ FULLY ACCESSIBLE — Indian Fama-French and Momentum factor data library, free download. The Indian equivalent of Ken French's data library. Confirmed August 2026.
- **Springer/SBR (link.springer.com)** — Open access papers accessible in principle but anti-bot protection frequently blocks web_extract; use abstract from web_search snippet. Non-open-access: paywall.
- **Wiley (onlinelibrary.wiley.com)** ❌ Paywall on full text; abstract accessible via snippet.
- **Oxford Academic (academic.oup.com/rfs etc.)** ❌ Bot-blocked; cannot extract even abstract via web_extract.

---

## Native-language search queries that work

**Russian**: `большие языковые модели` (LLMs), `управление памятью` (memory management), `агент` (agent), `мультиагентная` (multi-agent), `расширенная поисковая генерация` / `RAG`, `оптимизация` (optimization), `контекст` (context). Append `site:cyberleninka.ru` for Russian open-access results.

**Ukrainian**: `мовна модель` (language model), `штучний інтелект агент` (AI agent), `управління памяттю` (memory management), `оптимізація` (optimization). Ukrainian AI research mostly in English at UNLP workshop (ACL Anthology) or arXiv.

**Chinese institutional research**: CNKI/Wanfang always paywalled — don't attempt extraction from cnki.net or wanfang.com. Nearly all significant Chinese AI/NLP work from Tsinghua THUNLP, PKU, Fudan, Shanghai AI Lab, USTC, Zhejiang, Beihang, BUPT, CAS appears in English on arXiv. Exception: major survey/review papers sometimes appear only in Chinese journals — try `cjc.ict.ac.cn/EN` (Chinese Journal of Computers, open PDFs). CCKS/NLPCC behind Springer paywall; search arXiv for preprint version first. Dual-language useful terms: `大语言模型`(LLM), `多智能体`(multi-agent), `检索增强生成`(RAG), `智能体记忆`(agent memory), `自进化`(self-evolving), `上下文压缩`(context compression), `知识图谱`(knowledge graph), `综述`(survey). Append `arxiv 2025` or a venue name.

**Japanese**: `エージェントメモリ管理`(agent memory mgmt), `RAG検索拡張生成`(RAG), `マルチエージェント協調`(multi-agent coord), `LLMトークン最適化`(LLM token opt), `コンテキスト圧縮`(context compression), `自律エージェント`(autonomous agent), `自己改善`(self-improvement), `長期記憶`(long-term memory).

**Korean**: `AI 에이전트 메모리 관리`(agent memory mgmt), `RAG 검색 증강 생성`(RAG), `LLM 토큰 최적화`(token opt), `컨텍스트 압축`(context compression), `자율 에이전트`(autonomous agent), `자기 개선`(self-improvement), `계층적 다중 에이전트`(hierarchical multi-agent), `지식 그래프`(knowledge graph). Japanese practitioner community (Zenn, Qiita, Mamezou developer blog) often synthesises cutting-edge research before English tooling catches up — search these alongside peer-reviewed venues.

---

## "Second brain" / "personal knowledge base" is not a standard academic search term

Confirmed July 2026. arXiv search for "second brain AI evaluation" returns 15 results, none relevant — the query matches medical/neuro papers on literal second brains. The academic terms for this architecture are "agent memory evaluation", "personal knowledge base RAG evaluation", "long-term conversational memory", and "conversational agent memory". The "second brain" framing (Tiago Forte/PKM community) has not been adopted in academic ML literature. Use LongMemEval, AMA-Bench, LoCoMo as the benchmarks; LRAGE for the legal domain; and OrgForge for synthetic corpus generation. See `references/personal-brain-agent-memory-eval-2026.md` for the full landscape.

---

## Legal AI evaluation benchmarks are mostly jurisdiction-specific and not cross-referencing each other

Confirmed July 2026. The landscape is fragmented by jurisdiction (CN, US, TW, IN, DE, AU) with each benchmark treating its own jurisdiction as the implicit default. When searching for legal benchmarks applicable to a specific jurisdiction (e.g. Australian common law), the most productive search is the jurisdiction term + "contract" or "common law" + "benchmark" or "dataset" — not "legal AI evaluation benchmark" generically. The only AU-specific contract dataset found (LAUKIN) was surfaced by adding "Australia" to a targeted query, not by a generic legal AI benchmark sweep. For practitioners in any non-US jurisdiction: assume most benchmarks are US-centric and verify explicitly.

---

## arXiv search fails for technical indicator names (RSI, MACD, Bollinger, etc.) — use academic synonyms

Confirmed August 2026. arXiv HTML search returns **0 results** for queries using practitioner indicator names as keywords. The academic literature uses different terminology: RSI → "contrarian strategy" / "short-term reversal" / "short-horizon mean reversion"; Bollinger Bands → "price channel" / "technical trading rules"; MA crossover → "moving average technical trading rules" / "trend-following signal"; MACD → "momentum indicator" / "technical analysis signal". **Fix**: search via `web_search` with academic terminology, then verify paper existence via `arxiv.org/abs/{id}`. Never assume a zero-result arXiv search means "no papers exist" for a practitioner strategy — it means your search terms don't match academic vocabulary.

---

## arXiv basic HTML search fails on practitioner/strategy terminology — the tool is domain-blind

Confirmed August 2026. arXiv's basic HTML search page (`arxiv.org/search/?searchtype=all&query=...`) returned **zero results** for `technical+trading+momentum+China` — also failed for native-language queries. Root cause: arXiv's tokenized full-text index does not match against practitioner indicator names or multi-word phrase compounds; it requires academic vocabulary or short 2-term combinations. Fix: use `web_search` with `site:arxiv.org [terms]` — this hits Google's web index of arXiv pages, not arXiv's own search backend, and succeeds on the same terms.

- **J-STAGE task-specified URL returned 404**: The task-provided URL format (`jstage.jst.go.jp/search/-char/en?...`) returned 404 Not Found. J-STAGE search URLs have changed; this format is no longer valid. Alternative: use `web_search site:jstage.jst.go.jp [topic] [year]` for discovery, then `web_extract` on individual article pages.
- **arXiv Chinese-language site queries return homepage links only**: `site:arxiv.org 技术分析 量化交易 A股` returned arXiv homepage links, not paper results. Fix: use English queries with Chinese institutional affiliation terms (`China A-share momentum arXiv 2024 Tsinghua OR Renmin OR SJTU`) or search for the institutions directly (`site:arxiv.org Renmin University China finance`).

---

## arXiv search query design for legal AI: avoid multi-term phrase compounds

Confirmed July 2026. Queries like `legal AI evaluation benchmark contract negotiation` and `contract AI accuracy evaluation CUAD` return zero results — arXiv treats these as exact-phrase matches across all fields. Break into two-to-three term queries: `LLM evaluation legal reasoning benchmark` (116 results), `multi-agent evaluation legal tasks` (28 results), `contract AI benchmark` (separating the domain terms). The legal AI evaluation space has grown rapidly since 2024 — generic term combinations still outperform specific compound queries.

---

## Fixed-rate vs. adaptive compression in surveys

A common error in surveys is treating all compression methods as comparable. Fixed-ratio methods (H2O, StreamingLLM) and adaptive methods (ACC-RAG, SnapKV) solve different problems. Keep them in separate subsections.

---

## web_search backend intermittently failing (connection-refused / TLS-handshake-eof)

This is DIFFERENT from SerpApi 429 — space retries, don't switch tools, and disclose the gap it causes. Confirmed July 2026. `web_search` returned `DuckDuckGo search failed: ConnectError` and `Brave ... tls handshake eof` on a *fluctuating* subset of calls in the same session — roughly half failed while the other half succeeded, and failing queries succeeded on a later retry. This is transient upstream-provider infrastructure flakiness, NOT rate-limiting and NOT a broken integration. Distinguishing signature: 429 is persistent-for-the-session and affects *every* call (→ switch to arXiv-API-via-web_extract path); connection-refused/handshake-eof is *intermittent and per-call* (→ retry the failed query once or twice, ideally spaced out by doing an unrelated `web_extract` in between). When a specific *non-English academic track* couldn't complete because its queries kept hitting the flaky backend, report it as an explicit OPEN GAP, never as a null finding.

---

## Draft/industry-lab framework ≠ ratified standard — check authority status

Confirmed July 2026. A detailed, well-structured, very current CSA whitepaper (27 March 2026) extended NIST AI RMF with a formal 4-tier agentic-autonomy classification and named reference architecture (AAGATE) — genuinely useful and citable. But NIST's own agentic standard (via its new CAISI initiative, announced Feb 2026) isn't due until Q4 2026 — so as of the sweep date, no NIST-ratified agentic-autonomy standard exists at all. A framework being the *newest* thing found is not the same as it being *authoritative*; when a user's document leans on "NIST AI RMF" or similarly institutionally-branded language, explicitly check whether the cited material is (a) the base standard itself, (b) an industry body's draft extension filling an acknowledged gap, or (c) a vendor's interpretation — and say so in the writeup rather than letting recency read as settledness.

---

## "No non-English academic coverage" has two distinct causes — tell them apart

(1) *Access barrier* — real research exists but sits behind CNKI/RISS/IPSJ paywalls. (2) *Topic is too new/applied for academia yet* — the subject is a fast-moving industry-engineering topic where non-English search surfaces only practitioner blogs that translate/summarize the same English-language arXiv or vendor-blog sources, not independent research. Verified case (July 2026, MCP tool-schema/token-optimization survey): native-language queries in Chinese, Japanese, Korean, German, and Russian against general web search returned commentary citing the *identical* quantified figures already sourced from Anthropic's English blog — no novel non-English data or methodology anywhere. To tell the two apart: check whether the non-English source cites/reports numbers already seen in the English sources (derivative) vs. presents its own dataset, benchmark, or measurement (independent). Report this distinction explicitly in the final writeup.

---

## Cross-language convergence is a first-class analytic output of multilingual sweeps

When the same technique appears independently in 2+ language tracks (different institutions, different venues, no cross-citation), that's a *strong signal* the technique is addressing a real bottleneck — stronger evidence than a single well-cited English paper. Verified July 2026: four independent language communities (ZH, RU, JP, KR) converged on tiered/multi-level memory architecture as the solution to long-term agent memory. Reporting pattern: after per-language findings, add a **Cross-Language Convergence** section with a table: `Technique | Tracks | Strength (VERY STRONG / STRONG / MODERATE) | Notes`. Strength criteria: VERY STRONG = same conclusion in 3+ tracks; STRONG = same conclusion in 2+ tracks with different mechanisms; MODERATE = parallel emergence with possible indirect influence. The convergence table is often more actionable than the per-paper findings.

---

## Prompt engineering advice needs calibration context

Budget-hint techniques (TALE) should specify that the budget should be set at the P80 of task-typical length, NOT the median. Median budget causes wrong answers on harder instances.

---

## Multilingual RAG representation is the primary lever, not retrieval algorithm

Confirmed ICLR 2026 (arXiv:2603.04238, Asenov et al.). Systematically varying transcription/preprocessing while holding retrieval fixed shows BM25 can recover large benchmark gaps. Practical implication: when multilingual corpus retrieval underperforms, improve text normalization, script normalization, and chunk metadata BEFORE switching to a more sophisticated embedding model or retrieval system.

---

## Multilingual RAG distractor language matters — query-language distractors are slightly worse

Confirmed EMNLP 2025 Best Paper (arXiv:2504.00597, Qi et al., 48 languages). When multiple retrieved passages are provided and some are distractors, passages written in the SAME language as the query exert a slightly stronger negative influence on answer quality than distractors in other languages. Practical implication: apply stricter relevance filtering to query-language passages than cross-lingual ones. LLMs are surprisingly good at extracting info from cross-lingual passages but weak at producing the answer in the correct language — separate the extraction step from the language-control step.

---

## RAG robustness is most critical on multi-hop queries

RetRobust (2310.01558) and RARE (2506.00789) both confirm multi-hop queries are the worst case — irrelevant context at early hops causes cascading errors. When designing RAG pipelines for Graphiti (which handles multi-hop relational queries), apply NLI filtering at each retrieval step, not just the final generation step.

---

## Google Scholar is not a viable automated retrieval target

Confirmed July 2026 — both `web_extract` and local Firecrawl hit Scholar's bot-detection page ("unusual traffic from your computer network" / CAPTCHA wall) on every request. There is no official Scholar API and no scraper workaround that survives retrying. Treat it as permanently unavailable for programmatic retrieval and go straight to the fallback chain below.

**Metadata/citation-count fallback chain** (in priority order): **arXiv API** (preprints, no auth, no rate limit — use first) → **CrossRef API** (`api.crossref.org/works`, published metadata + DOIs, no key needed, reliably available) → **Semantic Scholar API** (`api.semanticscholar.org/graph/v1`, adds citation counts/abstracts/influential-citation flags, but unauthenticated calls hit 429 Too Many Requests under load — a free API key gives you a dedicated allocation instead of the shared unauthenticated pool) → **OpenAlex API** (`api.openalex.org/works`, broadest coverage + alt-metrics, but anonymous search occasionally returns "search cluster recovering from heavy load" — same fix, get a free key). Confirmed live-tested status as of July 2026: CrossRef worked immediately with no key; Semantic Scholar and OpenAlex both degraded/rate-limited on unauthenticated requests during that test window — expect this and don't treat a single 429/503 as a broken integration, just move down the chain or retry later.

If the task specifically requires Scholar's citation graph/ranking (not just "a citation count for this paper"), say so explicitly rather than silently substituting a different source's citation count — Scholar, Semantic Scholar, and OpenAlex citation counts diverge and aren't interchangeable.

---

## Semantic Scholar API key — real numbers and signup mechanic (verified July 2026)

Unauthenticated calls share a pool rate-limited to 1000 req/sec across *all* unauthenticated users combined (not per-caller), which is why bursty automated use gets sporadic 429s. Requesting a key does NOT raise your personal ceiling to something huge — the introductory rate limit for a new API key is only **1 request/sec on all endpoints**. Signup is a simple web form at `https://www.semanticscholar.org/product/api` → "Request an API Key" (name, email, intended use) — no account or password required; the key is emailed to the address given. Never submit this (or any similar third-party signup form) with an invented name/email on the user's behalf — ask for the real address first.

---

## Check this skill's own reference files BEFORE running fresh live searches

Confirmed July 2026, same NAB "Legal Intelligence Platform" critique, a *later* continuation session. The task asked to update CD-5/EG-6/UA-1 findings with the "latest" academic/regulatory sources — but `references/legal-ai-evidentiary-and-risk-papers-2025-2026.md` already contained a fully-resolved answer for exactly these three topics. Instead of reading that file first, the session ran ~20+ fresh `web_search`/`web_extract` calls re-deriving the same ground, then hit persistent SerpApi 429 rate-limiting and ran out of budget before reaching a conclusion. **Rule: on any repeat/incremental pass over a document this skill has previously swept, `skill_view(name='academic-literature-review', file_path='references/<matching-file>.md')` is the first move, not the last resort** — treat the reference file as the working baseline and only spend live-search budget on what it doesn't already cover.

---

## arXiv API endpoint (`export.arxiv.org/api/query`) times out via `web_extract`

Confirmed July 2026 (legal KM survey). Attempting `web_extract` on the Atom API endpoint timed out after 60s on both queries in the same session. The working alternative: use the arXiv HTML search page `https://arxiv.org/search/?searchtype=all&query=TERMS&start=0` — returns up to 50 results with full abstracts, arXiv IDs, venues (from Comments field), and submission dates. `web_extract` handles it reliably. Separate root cause from the curl-to-python3 pipe approach: that pattern fails because the W3C namespace URL is flagged as a plain-HTTP security risk AND the pipe-to-interpreter is flagged as code injection — both cause auto-rejection.

**Verified working arXiv access hierarchy (July 2026):** (1) `web_extract` on `https://arxiv.org/search/?searchtype=all&query=TERMS` → HTML listing; (2) `web_extract` on `https://arxiv.org/abs/{id}` → individual abstract; (3) `web_search` with `site:arxiv.org TERMS` to surface IDs then verify via (2). Never use the Atom XML API endpoint via `web_extract` — it times out. Never pipe `curl | python3` for XML — security scanner blocks it.

**Second confirmation July 2026:** All four `curl | python3` arXiv API calls failed immediately with XML ParseError on line 1, column 0 — security scanner rewrote/truncated the curl output before the parser saw it. All four `web_extract` calls on Atom API URLs timed out after 60s. The entire survey was completed successfully using only `web_search` + `web_extract` on individual article/abstract URLs. Reinforce: **the arXiv Atom API endpoint has zero practical utility via these tools; don't attempt it.**

---

## web_search rate-limiting (SerpApi 429) fallback: go straight to the arXiv API via `web_extract`

Confirmed July 2026, same session — `web_search` returned `SerpApi returned HTTP 429` on essentially every call for the whole session. The fix that actually produced results: call `web_extract` directly on a URL-encoded arXiv API query string, e.g. `web_extract(urls=["http://export.arxiv.org/api/query?search_query=abs:%22conformal+risk+control%22&start=0&max_results=15"])` — this bypasses web_search entirely, needs no key, and returns full Atom XML with abstracts. **Diagnostic rule: after 2 consecutive web_search 429s in one session, stop retrying web_search and switch to the arXiv-API-via-web_extract path for the rest of that session** — don't burn 10 retries on a backend that is clearly down for the whole session.

---

## Vendor marketing claims and PR-dispute figures are not academic validation

Confirmed July 2026, researching accuracy benchmarks for commercial contract-analytics tools (Kira, Luminance). Multiple search hits quoted specific-sounding accuracy percentages (e.g. "Kira achieves 94-95% on standard M&A clauses, Luminance 85-92%") with no disclosed methodology, dataset, or sample size — and a trade-press piece independently confirmed the two vendors are in an active public PR dispute over exactly these kinds of claims. Rule: when a search turns up an accuracy/performance number for a named commercial product, trace it to its origin before citing — if the origin is the vendor itself, a vendor-affiliated blog, or contested trade-press commentary, state explicitly in the writeup that no independent validation exists and the figure is a marketing claim, rather than presenting it in the same register as an academic finding.

---

## Biomedical clinical briefs — PMC block, abstract≠protocol, citation hygiene (Aug 2026)

Confirmed Aug 2026 migraine-stretch clinical literature email. Full access recipe:
`references/pubmed-openalex-biomedical-bypass-2026.md` (Europe PMC + Springer OA PDF
ladder; sci-research pack).

Load-bearing rules for **clinical literature → patient-facing brief**:
1. **Abstract ≠ full-text protocol.** Session counts, hold times, and frequencies
   from abstracts/secondary listings are HIGH risk. Rezaeian 2021: full text =
   6 sessions/2 weeks (~20 min), not the compressed abstract framing.
2. **Home routine is synthesis.** Label “clinical synthesis for home use, not a
   copy of one trial protocol.” Do not invent RCT-looking hold times.
3. **NMA rank ≠ CPG grade.** Keep ranking evidence and guideline grades in tension
   when they disagree (e.g. strength NMA #1 vs C-grade resistance; neck CMSE null).
4. **Mechanism caution.** Soft-tissue benefit when TrPs reproduce headache ≠
   “migraine is only muscular.” Frame as selected-patient relief, not etiology.
5. **Grounded-citations interaction** (`grounded-citations` is bundled — apply
   these caller-side):
   - Register DOI/OA-PDF URLs at retrieval; attach `quote` from **full text** for
     protocol claims, not abstract snippets.
   - Max 3 ids/sentence; multi-cite design-goal lines → one claim per sentence.
   - Adversarial self-review prose that says “fixed [11]” still counts as a
     citation token — strip phantom ids before `verify`, or verify will fail.
   - Never `sources.py add` with a bare title string as the URL; bad ledger rows
     must be deleted from `$HERMES_HOME/cache/citations/ledger.json` before
     `render --replace-in`.
   - Medical safety absolute rules without a sourced guideline get `[unverified]`,
     not a fake citation.
6. **Email form:** Subject, body, Alexey sign-off, red flags, Sources, recursive
   adversarial appendix. File path under Documents is fine; send only on request.

# Legal-AI Critique — Japanese + Korean Sweep (Round 3, July 2026)

Round 3 of the NAB "Legal Intelligence Platform" (LIP) critique. Seven **new** topics (not in the prior CJK/FR sweep), each swept in Japanese AND Korean against native venues, translated to English. Output mode: "standalone tag-applicability findings file with inherited fabrication blacklist" (see SKILL.md). Output file: `research_round3_fresh_ja_ko.md` in the critique's `research/` dir.

## Verified native venues used this round (all topic-assessable without login)
- **JA**: J-STAGE (jstage.jst.go.jp — abstracts + DOI resolve), JSAI/TJSAI proceedings & 人工知能学会誌, 情報法制研究 (ALIS, legal-informatics venue), METI/総務省 AI事業者ガイドライン PDFs, 内閣府 (Cabinet Office) regulatory-reform WG PDFs, 矢野経済研究所 (Yano Research Institute) press releases.
- **KO**: KCI (kci.go.kr landing pages), DBpia (abstracts), RISS, KLRI (klri.re.kr), KISO Journal (journal.kiso.or.kr), law.go.kr (primary statute text), KLAC (klac.or.kr — live institutional deployment).

## Per-topic verdicts (JA / KO)
| # | Topic | JA | KO |
|---|---|---|---|
| 1 | Conflicts / ethical-wall (情報遮断/정보차단벽) automation | **GAP** — J-STAGE 利益相反 is medical research-ethics COI, not law-firm conflict-checking; 情報法制研究 has a tangential lawyer-discipline article only | **GAP** — KCI *법률사무에 있어 AI 활용과 변호사 윤리* (ethics framing) + DBpia *이익충돌과 쌍방대리금지* (변호사법§31 doctrinal, SC 2024다225580) exist, but no *automated-checking* research |
| 2 | Prompt-injection defense (agentic LLMs) | **HIT (primary)** — JSAI2025_4I2GS1103, UEC authors, multi-agent injection defense | **HIT** — DBpia agentic attack/defense + *Trust Paradox in LLM Multi-Agent Systems* (over-privilege) |
| 3 | Legal knowledge graphs / ontology | **HIT** — 法律オントロジー (人工知能学会誌 v19), JSAI SIG-SWO legal KG challenge | **HIT** — KCI *법률 온톨로지의 이해와 적용* (Ewha 2018) |
| 4 | Multi-agent orchestration failure modes | **HIT** — JSAI2025_3A1GS1003 (agent-eval in LLM multi-agent), TJSAI 40(1), JSAI2024_4G3GS205 | **STRONGEST** — DBpia *Chunk 분할·신뢰점수 오류단계 탐지* (NODE12545212) + *윈도우 증강 오류 귀인 식별* (NODE12855096) — failure detection & attribution, exactly LIP's 15-agent concern |
| 5 | Legal chatbot / access-to-justice | **Institutional** — 法テラス houterasu + 内閣府 AI-legal-tech-access PDF (govt primary); no peer-reviewed bot eval | **Institutional** — KLAC **법률똑똑이** live 24/7 AI chatbot+callbot (primary); no peer-reviewed eval |
| 6 | E-billing standards + legal-spend market data | **Market data (secondary)** — Yano: legal-tech ¥22.8bn (2018, +15.2%), CAGR 9.8% (2016–23), ¥35.3bn by 2023; e-contract ¥3.9bn(2018)→projected ¥39.5bn by 2025. **Standard = GAP** (no LEDES-equiv) | **Vendor/global only** — TR Legal Tracker marketed in KO; GII US$11.06bn by 2030 CAGR 31.5% (global). **Native standard = GAP** |
| 7 | XAI / explainability for legal decisioning | **Strong** — METI/総務省 AI事業者ガイドライン v1.1 (2025-03-28) & v1.2 (2026-03-31), transparency/accountability (primary); JSAI/J-STAGE XAI surveys (ESSFR 16(2), JSSM 34(1), MII 42(2), JSAI2025_4M1OS14a04) but **medical-domain-dominant, not legal-specific** | **Strong (primary statute)** — **AI 기본법** (Law 20676, eff. **2026-01-22**, law.go.kr). **Art. 34** high-impact-AI operator duty explicitly requires 설명: "main criteria for deriving AI final result" + "training-data overview". Art.31 transparency, Art.32 safety, Art.40 investigation (≤₩30M). Analysis: KISO Journal (Prof. Kim Hyun-kyung, SeoulTech) + KLRI report |

## Key durable facts worth reusing across future KO/JA legal-AI work
- **KO AI 기본법 Art. 34 is a *binding statutory explanation duty*** for high-impact AI (eff. 2026-01-22), not aspirational — the strongest KO explainability hook. Verify article text at law.go.kr; secondary analysis at journal.kiso.or.kr/?p=13119 and klri.re.kr.
- **JA has no equivalent binding statute** — METI AI事業者ガイドライン is guidance (透明性/アカウンタビリティ), primary but non-binding.
- **Yano Research Institute** (yano.co.jp/press-release) is the go-to for quantified JA legal-tech/e-contract market data (industry/secondary).
- **KLAC 법률똑똑이** and **法テラス houterasu** are the citable institutional A2J deployments (KO/JA respectively).
- Genuine **GAPs confirmed both languages**: (1) AI conflict/ethical-wall *automation* research, (2) native corporate-legal e-billing *standard*, (3) *legal-domain-specific* applied XAI (JA XAI corpus is medical-dominant).

## Fabrication blacklist — round-3 recheck result
Round-3 searches did **not** resurface any of the four previously-flagged fabrications ("Sugimoto et al. 2025", "Wang & Li 2026", "Case Assignment Fairness Corpus", "Legal Allocation Bias Dataset"), nor the later fake standards ("ISO/IEC 27043:2026 Annex C", "NIST IR 8497"). None cited. Any suspicious-looking hit was verified to resolve to a real J-STAGE/DOI/KCI/law.go.kr page before inclusion. Audit trail recorded in the output file's corrections section.

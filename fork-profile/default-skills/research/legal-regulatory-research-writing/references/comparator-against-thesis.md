# Comparator-against-a-thesis worked example: NAB LIP Cluster A (July 2026)

Task: source memo (`LIP-AI-eval-governance-framework-v1.0`) made two theses about AI plugin/skill governance. Gather **external comparator frameworks** in EN/ZH/JA/KO/FR and position each against the theses. NOT a re-audit of the memo — comparators only.

## The two theses being compared against
1. **Capability-derived tiering** — a plugin's risk tier is a *function of what it can access/do* (file system, network, enterprise tools, sensitive data, ability to take external/irreversible actions), NOT what the author self-declares.
2. **Registry-as-control-plane** — the registry is the *enforcement point*: unregistered/unreviewed plugins are denied tool/data access by construction.

## Document skeleton that worked
1. **Reference frame + non-goals** — restate both theses; state explicitly the doc does not re-validate the memo.
2. **Per-language sections**, each source getting: what it says → primary/secondary flag + URL → **Compare/Contrast** to the two theses.
3. **Cross-cutting synthesis matrix** — `Framework | Tiering basis | Registry precedent | Hard access gate? | Granularity`.
4. **Numbered "real gaps & contradictions found"** list.

## Verified source set (all real, all reachable this pass)

### EN — standards / law / industry
- **NIST AI RMF 1.0** — GOVERN/MAP/MEASURE/MANAGE; risk-based not fixed tiers; GenAI Profile NIST AI 600-1. `airc.nist.gov/airmf-resources/airmf/5-sec-core/`. Verdict: MAP aligns w/ capability tiering, but no registry gate.
- **ISO/IEC 42001** (AIMS) — Annex A requires AI system inventory + impact assessment. Verdict: inventory = passive audit artefact, not runtime gate.
- **EU AI Act** — 4 tiers (unacceptable/high/limited/minimal); **Arts. 49 & 71 + Annex VIII** = public EU database, registration required *before* market placement. Verdict: **strongest statutory registry-as-control-plane precedent**, but tiers by use-case not capability.
- **Model Cards** (Mitchell 2019) / **Datasheets for Datasets** (Gebru 2018) — voluntary, self-authored metadata schema. Verdict: the self-attestation paradigm the memo explicitly rejects.
- **JPMorgan "Securing Agentic AI"** — **"lethal trifecta"** (private data + untrusted content + external comms) = near-exact capability-derived restatement. `jpmorganchase.com/about/technology/blog/securing-agentic-ai`
- **DBS** "AI protocol (registry)" + PURE framework. **CommBank** published responsible-AI reporting.

### ZH — 分级分类 + 备案/登记 (STRONGEST comparator)
- Academic: 《我国人工智能风险分级分类监管制度研究》, 《科技进步与对策》 2026 Vol.43(1) art.011. `kjjb.org/article/2026/1001-7348/2026-43-1-011.htm` — 分级分类 is mainstream, but use-case-based.
- Official: **CAC 生成式人工智能服务管理暂行办法** (2023-07-13, eff. 2023-08-15, 7-ministry). `cac.gov.cn/2023-07/13/c_1690898326795531.htm` — "分类分级监管" + 安全评估/算法备案 as precondition to serve.
- **备案 (filing) vs 登记 (registration) two-tier registry**: 备案 = original model builder/operator (heavy review); 登记 = party calling an already-filed model via API (light review). "双备案" regime. 505 approvals as of Mar 2025 (345 备案 / 159 登记). Tencent Cloud explainer `cloud.tencent.com/developer/article/2520652`. Verdict: real operating capability/dependency-derived registry control plane — tier depends on build-vs-call; same architecture, different unit (model/service) + different motive (content control).

### JA — AI事業者ガイドライン v1.2 (soft law)
- METI+MIC, v1.2 (2026-03-31), no penalties but de-facto standard. `meti.go.jp/shingikai/mono_info_service/ai_shakai_jisso/20260331_report.html`; MIC annex `soumu.go.jp/main_content/001064286.pdf`.
- 3区分: AI開発者/提供者/利用者. Recommended 8-column 台帳 (ledger) = registry precedent.
- v1.2: first AI-agent definition; **HITL mandatory when an "external action" is involved** — enumerated: email send, external API writes, prod deploy, payments, physical-device control, irreversible publication. Training-data traceability recommended→obligatory. Verdict: external-action enumeration is capability-derived; but soft law, ledger not enforcing.

### KO — AI Basic Act + practice layer
- 인공지능 발전과 신뢰 기반 조성 등에 관한 기본법, eff. **2026-01-22**, world's 2nd comprehensive AI law; fines from ~Jan 2027. `law.go.kr/법령/인공지능발전과신뢰기반조성등에관한기본법` + 시행령.
- **2 tiers only**: 고영향 (High-Impact) vs 일반. High-Impact = life/body/fundamental-rights (hiring, credit, medical, education, public services) → risk-mgmt + docs + user-notice + website disclosure of training data & designated manager. Generative-AI labeling mandatory; foreign-operator domestic representative.
- Self-assessment test: irreversible effect? / affects life-body-rights? / contestable? — any yes = High-Impact.
- **Practice layer (KISDI):** Agent Trace Log + **Tool Permission Matrix** + HITL Gate — near-verbatim match for the memo's capability/tool-access model. `kisdi.org/ai-governance-korea-basic-act-eu-ai-act-enterprise-roadmap-2026`. Verdict: statute is impact/use-case-based; *practice* layer is capability-derived. Split validation.
- Empirical anecdote worth quoting: fintech case study — 38 AI systems in use, only 2 with any risk documentation (evidence for abandoning self-attestation).

### FR — registre des systèmes d'IA
- CNIL self-assessment grid `cnil.fr/fr/intelligence-artificielle/guide`.
- **Registre des systèmes IA**: (1) mandatory EU DB (AI Act Arts. 49/71, Annex VIII) — high-risk registered before market; (2) recommended internal register for all systems, cross-referenced to GDPR Art. 30 record. `donneespersonnelles.fr/registre-systemes-ia`.
- Internal-register field model captures capability-relevant fields: AI type, inputs/outputs, human-oversight measures, third-party access, data location, AI-Act risk classification. Verdict: most detailed public registry-entry template, but tier field = AI-Act use-case classification, register = compliance-documentation not runtime gate.

## Synthesis headline findings (the contradictions worth surfacing)
1. No external framework tiers at **plugin/skill** granularity — all comparators are model/system/service/agent level. Memo's unit is genuinely finer; no off-the-shelf standard maps 1:1.
2. **Capability-derived tiering is validated by industry, not by law** — private (JPMorgan, KO-practice) vs. every statutory regime tiering by use-case/impact. Memo runs against the grain of binding law while aligning with leading engineering practice.
3. Registry-as-control-plane has strong statutory precedent (EU Art.49/71, China 备案/登记) — but for public-transparency/content-control, not enterprise tool/data access. Memo *repurposes* a proven regulatory architecture.
4. Self-attestation is the fragile norm the memo rejects (Model Cards, ISO 42001 inventory, JP 台帳) — KISDI fintech case is empirical support.
5. Disclose search limits: one FR HAL/Cairn query failed on backend connect error; CiNii/J-STAGE (JP), RISS/KCI (KO) not queried directly — coverage via primary gov/statute sources instead.

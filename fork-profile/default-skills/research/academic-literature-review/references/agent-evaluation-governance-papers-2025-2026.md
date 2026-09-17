# Agent Evaluation & Governance Literature — July 2026 Sweep

Condensed knowledge bank from a sweep on AI-agent evaluation methodology, LLM-as-judge
calibration, and autonomy governance, run across English/Japanese/Russian/Chinese/French
sources while updating a legal (Trust Deed) AI-agent evaluation critique.

## English (arXiv)

- **Mohammadi et al., "Evaluation and Benchmarking of LLM Agents: A Survey"**, arXiv:2507.21504 (2025).
  Two-dimensional taxonomy (evaluation objectives × evaluation process). Flags enterprise gaps
  current benchmarks miss: role-based data access, reliability guarantees, dynamic/long-horizon
  interactions, compliance. Long-horizon consistency (does the agent's judgment on the same
  underlying issue stay stable across repeated/extended interactions) is named an open problem.

- **Yehudai et al., "Survey on Evaluation of LLM-based Agents"**, arXiv:2503.16416 (ACL Findings;
  revised Apr 2026). Five-perspective review. Names cost-efficiency, safety, and robustness as the
  critical under-measured gaps — most current practice concentrates on task-accuracy metrics alone
  and doesn't gate on whether an agent is operationally affordable/fast enough at scale.

## Japanese (CiNii / JSAI)

- **伊藤駿汰・栗田宗平・大竹桃子 (Ito, Kurita, Otake, Microsoft Japan), "LLM-as-a-Judgeと継続的学習に
  よる評価フレームワークの提案"** (A Proposal for an Evaluation Framework Using LLM-as-a-Judge and
  Continuous Learning), 人工知能学会全国大会論文集 JSAI2025, DOI 10.11517/pjsai.jsai2025.0_2win5102.
  Controlled study of LLM-as-judge evaluators: larger judge models track human ratings more
  closely; **few-shot prompting failed to reliably calibrate a judge model** to house standards;
  fine-tuning on human-adjudicated examples worked, with accuracy scaling with fine-tune data
  volume. Practical implication: any LLM used as a pre-screening judge against a firm's own
  standards needs fine-tuning on that firm's adjudicated examples, not few-shot prompting alone.

## Russian (Cyberleninka)

- **Khozhainov & Nesterenko, "Тестирование ИИ агентов"** (Testing AI Agents), Vestnik Natsionalnogo
  Instituta Biznesa (2025). Independent confirmation that conventional software-QA methods
  transfer only partially to non-deterministic LLM output, and that evaluating "correctness"
  without a single right answer needs a bespoke methodology. Also treats OWASP LLM Top 10
  prompt-injection risk as first-order production QA concern, corroborating from a separate
  research community (not an Anglophone-only framing).

- **Namiot & Ilyushin (Moscow State University), "Об оценке доверия к системам Искусственного
  интеллекта"** (On Assessing Trust in AI Systems), International Journal of Open Information
  Technologies (2025). Argues exhaustive formal guarantees on non-deterministic ML/LLM output
  correctness are not currently achievable; the practical EU-questionnaire-style fallback is a
  **controls-presence audit** — score whether recognised risk-mitigation practices are documented/
  in place, not whether outcomes are verified. Gives developers a concrete checklist and lets
  different implementations be compared even where outcome guarantees are impossible. Useful
  pattern whenever a review has metrics flagged "TBC/stakeholder decision" — a controls-presence
  checklist is the honest interim proxy, not a gap left open indefinitely.

## Industry/standards (not academic but load-bearing)

- **Cloud Security Alliance AI Safety Initiative, "Agentic AI Autonomy Levels and Control
  Framework" v2.0** (March 2026). Post-incident analysis of 10 real agentic-AI security incidents
  (Jan–Mar 2026). Cross-cutting patterns directly reusable for agent-governance reviews:
  (1) **autonomy without proportional controls** — orgs run agents at Autonomy Level 3-4 while
  only implementing Level 0-1 controls; (2) **capability exceeding need** — in 7/10 incidents the
  agent held far more system/tool access than its task required; (3) **architectural separation
  failure** — oversight/kill-switch logic implemented *inside* the agent's own execution context
  can be disabled by the agent itself or by adversarial input (incl. prompt injection) — the fix
  must be an architecturally external policy/gateway component with its own audit trail.

## Non-additive but checked (report honestly, don't omit or pad)

- **Chinese** (Zhihu, CSDN, Tencent Cloud developer blog): corroborates the general industry
  shift toward per-task-type evaluation metrics (dialogue vs. RAG vs. agent) and LLM-as-judge
  adoption, but surfaced no material beyond what's already in the English/Japanese/Russian
  findings above — restatement, not independent research.
- **French** (HAL open-archive): index/landing pages only; no specific paper matched the
  agent-evaluation-governance topic closely enough to extract new findings.

---

## Follow-on sweep (July 2026) — Australian financial-services / NAB legal-ops compliance context

Same reference file, different downstream task: extending a "fairness audit toolkit" +
regulatory matrix for an in-house bank legal-operations AI platform. This pass surfaced genuine
new primary sources, but its more important output was **flagging fabricated citations inherited
from a prior session via a compacted context summary** — see the top-level skill's pitfalls
section ("Verify inherited/baseline citations…") for the general rule this established.

### Newly verified sources (safe to cite)

- **APRA, "Letter to industry on artificial intelligence"** (30 April 2026, apra.gov.au), analysed
  in Clayton Utz commentary (5 May 2026). APRA's first AI-specific, board/executive-facing
  supervisory expectations — four observation areas: cyber/info-security, governance, supplier
  risk, change-management/assurance. Names prompt injection, non-human-actor IAM, and "point-in-
  time assurance is no longer fit for purpose for probabilistic/agentic systems" as explicit
  supervisory concerns. This is the strongest, most current APRA AI-governance primary source
  found to date — anchor any APRA section on this letter ahead of older/generic AI risk papers.
- **Law Society of NSW, "A Solicitor's Guide to Responsible Use of Artificial Intelligence"**
  (9 January 2026 edition — supersedes the Oct 2024 version). Explicitly extends its supervisory/
  verification obligations to "a commercial proprietary system commissioned for in-house use," not
  just public consumer AI tools — the best current in-house-specific hook in Australian legal-
  profession AI guidance.
- **ASIC REP 798, "Beware the gap: Governance arrangements in the face of AI innovation"**
  (29 Oct 2024) remains the operative ASIC AI-governance document; no ASIC "RG 271 AI extension
  (2025)" or "INFO 274 (2026)" could be verified against asic.gov.au in this sweep — treat both as
  unconfirmed pending a direct ASIC citation.
- **French (HAL)**: Nicolas Remond, "La gestion des connaissances à l'ère de l'intelligence
  artificielle: une revue de la littérature," AGeCSO 2024 (hal-04597646); Sid Ali Mahmoudi thesis
  on automatic annotation of judicial decisions via NLP/TALN (hal tel-05220589, 2025); "IA et
  justice: la voie française" meta-analysis of four French official AI/justice reports 2024–2025
  (hal-05192500), including a Sept 2025 joint magistrates/avocats deontology council opinion on
  GenAI use — the strongest non-English source found for the "in-house supervision of legal AI"
  angle in this sweep.

### Citations that could NOT be verified — strike from any deliverable that still cites them

- "Sugimoto et al. (2025), Inter-Rater Reliability in AI-Driven Case Assignment: A Japanese Legal
  Corpus Study" (CiNii) — no matching CiNii record found under direct or translated search.
- "Wang & Li (2026), Transparency Risks of LLM-as-Judge in Legal Allocation: A Chinese
  Perspective" (CNKI) — no matching record found; general Chinese legal-LLM research is real and
  active (e.g. LawGPT arXiv:2406.04614, Supreme People's Court "法信法律基座大模型"), but nothing
  on case-allocation fairness specifically exists in the accessible literature.
- **"Case Assignment Fairness Corpus"** (Japan, claimed ~12,000 labeled records) — not found.
- **"Legal Allocation Bias Dataset"** (EU/HAL, claimed ~8,500 records, attributed to "European
  Commission 2026") — not found; no HAL-indexed or EU-institutional dataset by this name exists.
- Regulatory-scope correction (not a citation, but same "verify before propagating" discipline):
  EU AI Act Annex III point 8 covers systems used *by or on behalf of a judicial authority* or in
  ADR — an internal, in-house-only bank matter-allocation tool does not plainly qualify on the
  primary text, contrary to an inherited "access to justice" framing from a prior draft. Treat the
  EU AI Act as an instructive best-practice benchmark for such a tool, not directly applicable law,
  absent an actual EU deployment footprint.

### Cross-language check performed but non-additive (report honestly)

Direct native-language queries for "case/matter allocation fairness" specifically (not legal-LLM
research generally) returned **nothing** in Chinese (CNKI/arXiv-adjacent), Japanese (CiNii/
practitioner blogs — found only privilege/GenAI-confidentiality commentary, not allocation
fairness), Korean (RISS — general legal-LLM benchmarking exists, allocation-fairness does not),
and French (HAL — general legal-AI/knowledge-management and privilege/liability thesis work
exists, allocation-fairness specifically does not). This is a genuine topical gap across all four
languages, not a paywall artifact — abstracts/indexes were reachable in every case. State this
plainly in any deliverable rather than filling the gap with unverifiable invented sources.

---

## Follow-on sweep (July 2026) — Technical implementation deep-dive for the same LIP/NAB critique

Fourth pass on this same underlying critique document, this time targeting the *system-design*
mechanics rather than legal/regulatory framing: OPE for allocation systems, fairness-metric
alternatives to Gini, privilege-preserving RAG architecture, LLM-judge calibration math, canary/
rollback methodology, counterfactual cost-avoidance measurement, and a currency check on NIST/CSA
autonomy-tier standards. Full per-topic detail (quantified formulas, DOIs, applicability
paragraphs) written to `/var/home/rainbow/lip_research_sweep_new_topics.md` for this task; only
the durable, reusable findings are condensed here.

- **Off-policy evaluation (OPE) for allocation systems**: mature ML methodology
  (Shimizu, "Doubly Robust Estimator for OPE with Large Action Spaces," arXiv:2308.03443 — the
  Marginalized Doubly Robust/MDR estimator; CANDOR counterfactual-annotated DR; ICLR 2024
  SharpeRatio@k for risk-aware OPE-candidate ranking) but **no paper applies OPE to legal
  matter/case allocation specifically** — matter allocation is structurally a large-discrete-
  action-space contextual bandit (action = "assign to lawyer L" across dozens/hundreds of
  practitioners), so the methodology transfers by analogy, not by validated precedent. Two
  transferable cautions: (a) OPE estimator accuracy degrades as the candidate policy diverges from
  the logged/current policy — a first major allocation-policy change is exactly the case where
  this bites hardest; (b) risk-aware OPE evaluation (catching a policy that's accurate on average
  but catastrophically wrong on rare high-severity cases) is itself an open research problem, not
  a solved one — don't let a spec cite "off-policy evaluation" as if the choice of estimator,
  overlap/support assumptions, and divergence-bias bounds were settled questions.

- **Fairness-metric alternatives to Gini for workload allocation**: found a specific, quantified,
  2025 critique of Gini itself — Aymeric & Magdalou, "Does the Gini index represent people's views
  on inequality?", *J. Economic Inequality* 23:637-665 (2025), DOI 10.1007/s10888-025-09695-4:
  in a representative population experiment, **up to 50% of respondents rejected the Pigou-Dalton
  transfer principle** Gini's construction assumes, i.e. Gini encodes a contestable value judgment
  about fairness that roughly half of people would not endorse if surfaced explicitly. Two better-
  fitting alternatives exist in directly analogous domains: **Jain's fairness index**, shown
  usable as an actual optimization objective (not just a retrospective dashboard stat) for
  personnel-to-project assignment — Rezaeinia, Góez & Guajardo, *Computational Management
  Science* 20:42 (2023), DOI 10.1007/s10287-023-00477-9, near-identical problem structure to
  lawyer-to-matter assignment; and **envy-freeness** (arXiv:2504.20704 chore-division, arXiv:
  2505.05353 weighted envy-freeness, AAMAS 2025 bounded-subsidies paper) — conceptually superior
  for legal matters because most matters are *burden* not benefit (chore allocation, not resource
  allocation), and it asks whether each individual lawyer would prefer someone else's allocation,
  not just whether the aggregate dispersion looks even. Caveat: weighted envy-freeness (accounting
  for seniority/capacity) is provably harder to achieve than unweighted and may require subsidy-
  style mechanisms. Recommend any fairness KPI section be checked against these two alternatives,
  not Gini alone.

- **Privilege-preserving RAG / "ethical wall" architecture**: access-control-aware RAG is a real,
  growing 2025-era literature (ACM DOI 10.1145/3672608.3707848 — access control enforced at
  retrieval time, not output-filter time, is the correct architectural principle; SafeRAG security
  benchmark) but it is generic multi-tenant-document framing, not legal-privilege-specific, and
  **no paper addresses "mosaic disclosure"** — the risk that individually-non-privileged fragments
  retrieved across matters let a persistent-memory agent (or a user querying it) reconstruct
  privileged information through aggregation over time. Flag this explicitly as an open gap the
  literature hasn't solved, not something a spec can lean on "RAG security best practice" to cover
  — a bank needs its own mosaic-disclosure controls (session/context isolation per matter, no
  persistent cross-matter memory of privileged content, query-budget limits). "Ethical wall" /
  "information barrier" is the correct legal-industry term to use in place of generic "privilege
  screen" language (per Intapp/Harvey AI industry usage), but those vendor sources are marketing-
  adjacent, not technical validation.

- **LLM-as-judge calibration — genuinely new beyond the JSAI2025 baseline already in this file**:
  Lee, Zeng, Jeong, Sohn & Lee, "How to Correctly Report LLM-as-a-Judge Evaluations,"
  arXiv:2511.21140 (26 Nov 2025, Yonsei/UW-Madison/KRAFTON). Derives the closed-form bias of the
  naive judged-accuracy estimator in terms of judge sensitivity/specificity (q1, q0): naive
  accuracy is **positively biased when true accuracy is low, negatively biased when true accuracy
  is high**, and in the degenerate case of a judge that always says "correct" the naive estimator
  is identically 1 regardless of ground truth. Ships a bias-corrected plug-in estimator with valid
  confidence intervals (accounting for both test-set and calibration-set sampling uncertainty) and
  code (github.com/UW-Madison-Lee-Lab/LLM-judge-reporting). Actionable rule: any LLM-as-judge
  quality gate needs a ground-truth-labeled calibration set, a bias-correction step, and disclosed
  CIs — a raw judge pass-rate is not a trustworthy point estimate on its own.

- **Canary deployment / automatic rollback**: mature, authoritative, non-novel — Google SRE
  Workbook Ch. 16 "Canarying Releases" (sre.google) gives the quantified justification (most
  production incidents are triggered by the deployment/config push itself, not steady-state
  operation) and a testable design principle (canary size proportional to error-budget headroom);
  Netflix Kayenta (open-sourced, Spinnaker-integrated) is the closest real-world precedent for an
  automated *statistical* canary-judgment feeding a rollback decision, rather than ad hoc
  thresholds. No new drift-detection-specific paper found beyond well-known MLOps baseline
  (ADWIN/DDM/page-hinkley) — treat canary/rollback as "confirm and apply known best practice,"
  and check that a spec's "staged rollout with auto-rollback" actually specifies canary sizing and
  a statistical judgment mechanism, not just gesture at the concept.

- **Counterfactual cost-avoidance measurement**: **explicit negative result** — no 2024-2026
  academic or rigorous industry-standard source specifically on "cost avoided"/counterfactual
  savings measurement with uncertainty-band methodology was found. Don't fabricate a citation for
  this narrow a topic; fall back to general, well-established causal-inference principles
  (difference-in-differences, synthetic control, standard CI reporting) as the basis for critiquing
  any point-estimate savings claim that lacks a specified counterfactual/control group and a
  disclosed uncertainty band.

- **NIST AI RMF "earned autonomy" / CSA Autonomy Levels — currency check finding a genuine gap
  between "draft industry framework" and "ratified standard"**: CSA published a detailed draft
  whitepaper (27 March 2026, labs.cloudsecurityalliance.org) extending NIST AI RMF with a formal
  4-tier autonomy classification (Tier 1 fully supervised → Tier 4 full autonomy w/ sub-agent
  spawning) plus tier-specific governance obligations and calibration-review cadences (annually/
  quarterly/monthly for Tiers 2/3/4, with mandatory demotion on elevated error rates), and a named
  reference architecture (AAGATE — Kubernetes-native runtime governance, pre-execution behavioral
  evaluation, single tool-gateway chokepoint, verifiable agent identity via DIDs/SPIFFE). BUT: NIST
  itself only announced a dedicated "AI Agent Standards Initiative" (via CAISI) in Feb 2026, with
  its own AI Agent Interoperability Profile **not due until Q4 2026** — meaning as of this sweep
  there is no NIST-ratified agentic-autonomy standard yet. The CSA material is useful, granular,
  and citable, but a spec that frames "NIST AI RMF earned autonomy" as settled, audited best
  practice is overstating the current state of play — it should be represented as following an
  emerging, industry-lab-proposed (CSA) extension to a gap NIST has only just begun to formally
  address, not compliance with an existing ratified standard.

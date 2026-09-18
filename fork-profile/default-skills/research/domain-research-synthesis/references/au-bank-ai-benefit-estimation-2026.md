# AU Bank AI Benefit Estimation — Research Notes (August 2026)

Reference file for benefit estimation research on AI initiatives in Australian banking.
Covers: trust deed review, marketing communications review, and the Alternative Benefit
Estimation Framework (ABEF) for use when stakeholder engagement is low.

---

## Key Verified Benchmarks

### Trust Deed Review

- **NAB (OpenAI)**: 45 min → 1 min per deed; ~15,000 deeds/year; 97.8% time reduction.
  Calculated: ~11,000 hrs/yr saved; ~AUD 1.1M/yr at AUD 100/hr loaded paralegal rate.
  Source: Australian FinTech, Nov 2024.
  URL: https://australianfintech.com.au/the-growing-adoption-of-ai-in-banking-in-australia-and-new-zealand/

- **APAC bank (HCLTech/Pega)**: USD 1M annual savings; 40% faster resolution; 25% staff
  efficiency improvement via AI-powered compliance/AML/CTF operations.
  Source: HCLTech case study, 2024.
  URL: https://www.hcltech.com/case-study/ai-powered-compliance-transforms-banking-operations-ensuring-safer-transactions

- **Wolters Kluwer 2026 Legal AI Survey (810 professionals, global)**: 62% report 6-20%
  weekly time savings from AI in document-related work; 52% report 11-20% revenue uplift.
  This is a conservative FLOOR for trust deed AI automation (NAB's figure is far higher
  because it replaces near-full manual effort).
  URL: https://www.wolterskluwer.com/en/expert-insights/legal-ai-adoption-time-savings-revenue-growth

### Marketing Communications Review

- **UK digital bank (Onix/Vertex AI, 7M customers)**: Full GenAI marketing compliance
  review against FCA handbook + ASA guidelines; Chain-of-Thought and Tree-of-Thought
  modules; eliminated manual re-evaluation cycles; integrated into existing approval
  workflow. Specific time/cost figures not published.
  URL: https://www.onixnet.com/case-study/digital-bank-automates-marketing-compliance-with-generative-ai/
  AU regulatory analogue: ASIC RG 234 + ACMA advertising standards map directly to FCA/ASA.

- **CBA Compass AI**: Business bank knowledge base queries delivered 3x faster than
  traditional methods; 500,000+ questions answered since July 2024.
  Source: CBA Newsroom, Feb 2026.
  URL: https://www.commbank.com.au/articles/newsroom/2026/02/cba-approach-to-adopting-ai-report-announcement.html

- **Beyond Bank**: AI chatbots handle 50% more chat queries with same team, 24/7.
  Source: Australian FinTech, Nov 2024 (same URL as NAB above).

### Industry-Wide FS AI ROI Benchmarks (EU/Global)

From The Thinking Company 2026 Guide (citing McKinsey, Bain, Moody's):
URL: https://thinking.inc/en/industry-service/financial-services-ai-roi/

| Use Case                     | Investment    | Annual Return | Payback  | 3-Yr ROI |
|------------------------------|---------------|---------------|----------|----------|
| Regulatory reporting/compl.  | EUR 200-600K  | EUR 3-8M      | 3-5 mo   | 400-500% |
| KYC/AML automation           | EUR 300-800K  | EUR 2-5M      | 4-8 mo   | 250-350% |
| Customer service AI          | EUR 200-500K  | EUR 1-3M      | 6-10 mo  | 200-300% |

Additional: 62% of FS execs report difficulty quantifying AI returns (confirms
stakeholder engagement challenge is industry-wide). 45% of FS AI initiatives don't
reach production; portfolio ROI adjusts to 100-140% after failure rate. Bain: 34%
of cancelled bank AI programs would have achieved positive ROI within 6 months of
cancellation.

### German/Swiss (DACH) Banking AI Context

- Deloitte Deutschland (Nov 2025): 95% of German banks deploying or planning AI.
  Document analysis is the #1 production AI use case.
  URL: https://www.deloitte.com/de/de/Industries/banking-capital-markets/research/kuenstliche-intelligenz-im-bankensektor.html

- 3L3C DACH (Dec 2025): Swiss/German banks achieve fastest AI ROI where compliance
  complexity + high personnel costs intersect. Governance (not tech) is the binding
  constraint. "Eine GenAI-Lösung, die in 60% der Fälle funktioniert, ist gefährlich
  für eine Bank." (A GenAI solution that works in 60% of cases is dangerous for a bank.)
  URL: https://www.3l3c.ai/de/blog/ki-in-der-schweizer-finanzbranche-banking-verm-gensverwaltung-2/roi-ki-banken-versicherer

### French Banking Context

- Banque de France Governor (Dec 2025): "AI could first lead to significant productivity
  gains through increased automation of administrative tasks (computer document reading,
  automated photograph analysis, etc.)." EU AI Act compliance overhead nets against gross
  gains — direct analogue to APRA obligations.
  URL: https://www.banque-france.fr/fr/interventions-gouverneur/mettre-en-oeuvre-une-surveillance-efficace-de-lia-dans-le-secteur-financier

---

## Big 4 Australian Banks — AI in Mortgage Processing (Aug 2026)

All four major banks now have AI in production on mortgage document processing.
NAB is the only one with a specific trust deed metric; others have analogous deployments.

### Westpac (most recent — Aug 2026)
- 5 AI agents on Amazon Bedrock AgentCore in production (not prototypes — confirmed by CDAO).
- Mortgage: account scrutiny agent (manual bank statements → transaction classification);
  2 payslip agents (extraction + policy verification against calculation rules).
- Scale: 32,000 payslips + 1.5M transactions processed per week in lending/credit.
- Outcome: 150,000 banker hours saved/year (confirmed Aug 2026, AWS FS Symposium, Sydney).
- Deployment cycle compressed: 6 months → 4-6 weeks per agent.
- Strategic framing (AFR, Aug 2026): "Westpac scrambles to demonstrate ROI and close
  the gap with AI leader CBA." ROI pressure is now board/analyst-level at all Big 4.
- Source: iTnews Aug 2026 https://www.itnews.com.au/news/westpac-plugs-five-aws-ai-agents-into-core-lending-processes-627914
- Source: AFR Aug 2026 https://www.afr.com/companies/financial-services/westpac-deploys-swarm-of-ai-agents-to-assess-loan-applications-20260805-p60lj0

Analogy to trust deed AI: Westpac's payslip agents are architecturally identical to
trust deed AI — document extraction + classification + policy verification. The 150,000
hrs/year figure at Westpac's scale is a ceiling reference for trust deed AI at that bank.

### ANZ (Oct 2024)
- HLQ platform: document ingestion, image processing, categorisation, indexing, redaction,
  data extraction. Direct analogue to trust deed processing.
- CTO Tim Hogarth: "AI can allow us to take information from documents... cutting the
  time from hours and hours down to sometimes mere seconds."
- Strategic framing: "Faster turnaround is particularly important in a competitive market
  where speed can be a differentiating factor."
- AI Immersion Centre: training 3,000 workers at Docklands, Melbourne.
- Source: ANZ BlueNotes Oct 2024 https://www.anz.com.au/bluenotes/2024/october/home-loans-automation-technology-mcmahon/
- Source: ABC News Oct 2024 https://www.abc.net.au/news/2024-10-24/home-loans-artificial-intelligence-big-four-banks-automation/104504224

### CBA (2026)
- Unloan (fully digital home loan): 15-min application, AI-driven origination, near-instant
  conditional approval. "Lower cost to originate" than standard CBA product.
- Loyalty rate discount compounds annually — only viable because AI-driven servicing cost
  is low enough to fund it.
- Home loan book grew AUD 9.3B in Q1 FY26 (1.1x system growth) — AI-enabled speed cited
  as a key driver.
- CBA is the explicit AI benchmark; other three Big 4 are actively trying to close the gap.
- Source: SmallBizAI Mar 2026 https://smallbizai.au/unloan-cba-ai-powered-home-loan-australia/

### Big 4 AI Maturity Comparison (Aug 2026)
```
Bank    | Trust Deed AI       | Mortgage Processing AI      | Maturity
--------|---------------------|-----------------------------|----------
NAB     | Confirmed: 45m→1m   | Deed/doc AI + sentiment      | Production
ANZ     | Inferred: hrs→secs  | HLQ: doc ingest/classify     | Production
Westpac | Inferred: payslip   | 5 agents, 150K hrs/yr saved  | Production
        | agents analogous    |                              |
CBA     | Inferred: Unloan    | Fully digital Unloan;        | Production
        | process speed       | 1.1x system mortgage growth  |
```

---

## NII Revenue Acceleration Model (Trust Deed → Faster Settlement)

The STRONGEST benefit claim for trust deed AI is not headcount savings — it is
NII pull-forward: faster deed review → conditional-to-unconditional approval cycle
accelerates → mortgage settles sooner → interest income accrues earlier.

### Why this framing is preferred
- Avoids headcount politics entirely (no FTE reduction claim)
- Scales with loan book size (much larger base than review volume)
- Directly tied to NII — the bank's primary P&L metric
- Supported by published industry evidence on process speed → satisfaction → retention

### The Calculation

  Annual NII Acceleration (AUD) =
    Annual_New_Loan_Originations (AUD)
    × Proportion_Requiring_Deed_Review
    × Days_Saved_Per_Application
    × Daily_NIM_Rate (= Annual_NIM / 365)

Key inputs:
- Big 4 average NIM: 178 bps (KPMG H1 2026) | NAB FY2025 NIM: 174 bps
  Use 175 bps conservative central. Daily = 0.004795% per day.
- Big 4 combined net interest income: AUD 40.5B in H1 2026 (4.9% growth YoY).
  Source: KPMG Big 4 Half-Year Results 2026 https://kpmg.com/au/en/insights/industry/big-four-major-banks-australia-half-year-results-2026.html
- Proportion of applications requiring deed review:
  High-net-worth/investor: 20-35% | Standard owner-occupier: 5-15% | Portfolio: 10-20%
- Days saved: Current manual lead time 1-4 days. AI: same-day. Net savings: 1-4 days.

### Illustrative Results

Mid-tier major (AUD 20B/yr new originations, 15% deed-affected, 175 bps NIM):
  Conservative (1 day):  AUD 1.44M/yr
  Central    (2 days):   AUD 2.88M/yr
  Upper      (4 days):   AUD 5.75M/yr

Large major (AUD 50B/yr new originations, 15% deed-affected, 175 bps NIM):
  Central (2 days):      AUD 7.19M/yr

Per-loan concrete framing (for CFO presentations):
  "A AUD 600K mortgage at 175 bps NIM earns AUD 29/day.
  Settling 2 days earlier = AUD 58. Across 4,500 deed-affected loans = AUD 261K
  on that cohort alone. Scale to portfolio for the full figure."

### Critical caveat
This model ONLY applies if deed review is on the critical path in the approval chain.
If deed review runs in parallel with credit decisioning or valuation, the acceleration
is partial (only the delta where deed review would have been the last step to complete).
Validate bottleneck position before using this framing with Finance.

### Application capture (secondary, harder to quantify)
ANZ explicitly stated speed is a competitive differentiator. Mortgage brokers (placing ~70%
of AU home loans) use turnaround time as a primary lender selection criterion. Even 0.1%
reduction in application lapse rate = AUD 20M on a AUD 20B origination book.
Do NOT use as a primary claim — present as a qualitative multiplier.

---

## NPS and Customer Satisfaction Evidence

### What the evidence shows (graded by strength)

STRONG (directly cited, credible sources):

1. Application speed is the #1 mortgage satisfaction driver.
   - 63% of mortgage applicants cite "length of the application process" as top frustration
     (WorldMetrics, 100 verified stats, 53 primary sources, verified June 2026)
   - 85% of borrowers value "quick resolution" over personalisation
     (Zendesk 2023 Mortgage Support Report, cited in WorldMetrics)
   - 33% of applicants drop out specifically during the income verification phase —
     structurally the same phase as trust deed review
   - Lenders with streamlined processes see 35% higher conversion rates
   - Lenders with NPS > 50 experience 20% higher retention rates
   - Source: https://worldmetrics.org/customer-experience-in-the-mortgage-industry-statistics/

2. Australian home loan satisfaction is linked to application ease.
   - Roy Morgan Single Source (n=28,398 AU home loan customers, Dec 2025-May 2026):
     ING #1 at 92.1% (easy process + competitive rates cited); Macquarie customers
     explicitly cite "easy application"; NAB saw biggest Big 4 improvement (+6.5pp to 78.8%)
     in the 12 months coinciding with trust deed AI rollout (correlation, not proven causation).
   - Overall AU home loan satisfaction: 78.3% in 6m to May 2026, up 4.2pp from prior year.
   - Source: Roy Morgan July 2026 https://www.roymorgan.com/findings/10278-home-loan-satisfaction-may-2026

3. Operational delays directly cause abandonment (NPS precursor).
   - Regional bank cut approval time 12 days → 48 hours via API integration:
     recovered ~USD 500K/month in borrower attrition.
   - "Borrowers rarely abandon after one major failure. They leave after repeated moments
     of uncertainty." Trust deed review delay = exactly this kind of repeated uncertainty.
   - Document review and underwriting = #1 abandonment-risk stage — exactly where deed
     review sits.
   - Source: V2 Solutions June 2026 https://www.v2solutions.com/blogs/mortgage-operational-efficiency-hidden-delays

WEAK / UNVERIFIED (do NOT use in stakeholder documents):
- Vendor claim: "NPS improvements of 25-30 points for AI-driven loan processing" (Artificio.ai).
  No methodology, no named institution, no primary source. Discard.

### The gap in evidence
No published study isolates trust deed review speed specifically as a driver of NPS.
What the evidence proves is: processing speed → mortgage satisfaction → NPS/retention.
Trust deed review is a documented friction point within that causal chain.

### How to use this in materials
"63% of mortgage applicants cite processing length as their top frustration [WorldMetrics].
33% abandon specifically at income/document verification [WorldMetrics].
Trust deed review is a documented 1-4 day bottleneck at that exact stage.
Eliminating it is therefore directly targeted at the primary dissatisfaction driver.
Roy Morgan data shows NAB's home loan satisfaction improved +6.5pp in the 12 months
coinciding with their trust deed AI deployment." 
→ Directional and structural claim. Do NOT claim a specific NPS point improvement.

### NPS monetisation logic (if your bank has internal NPS data)
- Lenders with NPS > 50: 20% higher retention rate [WorldMetrics]
- On a AUD 150B home loan book: 1% retention improvement = AUD 1.5B loans not refinanced away
- At 175 bps NIM: AUD 26M annual NII from that retention
- This chain requires your own NPS baseline data to close — not derivable from externals alone.

---

## Competitive Urgency and ROI Pressure (Aug 2026)

### The board-level context
- Only 7% of global organisations have "established ROI" from AI (KPMG Global AI Pulse
  Q2 2026, n=2,000+ senior leaders, 20 countries).
- 24% of leaders are under investor/board pressure to demonstrate AI value.
- 42% of enterprises have only partial visibility into AI spending.
- Source: UCToday/KPMG July 2026 https://www.uctoday.com/productivity-automation/kpmg-ai-cost-visibility-roi-survey-2026/

### Big 4 financials confirm the pressure (KPMG H1 2026 analysis)
- Combined Big 4 profit after tax: AUD 15.2B (down 2.1% vs H1 2025).
- Technology-related expenses: up 32.6% vs H1 2025 — primary driver of cost increase.
- Average cost-to-income ratio: 52.1% (up 4.6pp). ROE down 54 bps to 10.7%.
- "Digital transformation is no longer optional or incremental — it is a balance sheet issue."
- Source: KPMG https://kpmg.com/au/en/insights/industry/big-four-major-banks-australia-half-year-results-2026.html

### Governance = ROI (KPMG Q2 2026 finding)
Organisations with CEO accountability for AI AND cost visibility dashboards:
- 3.5x more likely to have established ROI (14% vs 4%)
- 5x more likely to report established ROI vs those without cost visibility (15% vs 3%)

### Competitive urgency timeline
- NOW (2026): All 4 Big 4 banks have AI in production for mortgage document processing.
  A bank without equivalent capability is behind all peers today. Gap is customer-visible
  (broker channel uses turnaround time as lender selection criterion).
- 2027: RBA rate cuts expected → refinancing wave. Banks with faster AI-enabled approvals
  will capture disproportionate volume. 56% of AU/NZ lenders already approve standard
  consumer loans in 1 day (vs 39% global average) — early movers defined.
- 2028+: Data moat compounds. 2-year training data lag = structural disadvantage that is
  very costly to close. WEF: each additional AI use case costs 40-60% less once MLOps
  infrastructure is established (platform optionality effect).

### Risk-adjusted case for trust deed review specifically
- Lower risk than other AI use cases (document extraction, not credit decision)
- APRA has implicitly accepted this use case (NAB in production, no objection)
- Mortgage brokers directly penalise slow lenders — trust deed delay is broker-visible
- Fix is well-scoped: not a full-stack AI transformation, just a document processing task

---

## Benefit Hierarchy for Trust Deed Review (Recommended Priority)

| Priority | Benefit Type              | Quantum (mid-tier major)   | Notes                          |
|----------|---------------------------|----------------------------|--------------------------------|
| 1        | Revenue acceleration (NII)| AUD 1.4-5.8M/yr            | NIM × volume × days saved.     |
|          |                           |                            | Strongest, politically clean.  |
| 2        | Application retention     | AUD 5-20M/yr (est.)        | Broker channel speed effect.   |
|          |                           |                            | Hard to prove; wide range.     |
| 3        | Capacity redeployment     | AUD 0.8-1.5M/yr            | NAB benchmark applied          |
|          | (NOT headcount cut)       |                            | conservatively. Frame as       |
|          |                           |                            | capacity, not FTE reduction.   |
| 4        | Quality/accuracy          | AUD 0.2-0.5M/yr            | Error reduction, re-work cost. |
| 5        | Competitive positioning   | Not directly quantified    | Use peer evidence for urgency. |
| TOTAL    | Core (P1+P3+P4)           | AUD 2.4-7.8M/yr            | Fully supportable from         |
|          |                           |                            | external evidence; no          |
|          |                           |                            | internal engagement required.  |

Headcount savings are real but modest (~5.5 FTE equivalent at NAB scale) and politically
fraught. Lead with NII acceleration. Headcount capacity is a supporting point, not the lead.

---

## APRA/ASIC Regulatory Context (Aug 2026)

**APRA Letter to Industry on AI (April 2026):**
URL: https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai

Key obligations for regulated entities:
- Maintain an inventory of AI use cases with benefits, risks, and lifecycle accountability.
- "Governance has not matured at the same pace" as AI adoption — APRA calling for step-change.
- Board must maintain AI literacy; can't rely on vendor summaries.
- APRA will take supervisory action where AI risks are not managed proportionately.
- Expect: continuous monitoring (not point-in-time); integrated assurance across cyber,
  data governance, model performance, operational resilience, privacy, conduct risk.

**ASIC Report 798 (October 2024):**
- Reviewed 624 AI use cases across 23 Australian licensees.
- Warning: firms adopting AI faster than updating risk and compliance frameworks.
- Existing licensee obligations already apply to AI.

**AU Regulatory Penalty Exposure (indicative only, not legal advice):**
- ASIC: civil penalties up to AUD 1.565M per contravention for certain consumer
  protection breaches (ASIC Act + Corporations Act).
- AUSTRAC: civil penalty up to AUD 18M per contravention for AML/CTF Act breaches.
- APRA: conditions, directions, or higher capital requirements for operational risk failures.

---

## Alternative Benefit Estimation Framework (ABEF)
### For use when stakeholder engagement is low or unavailable

The ABEF triangulates across five methods to build a defensible business case
without relying on self-reported stakeholder effort estimates.

### Method 1: Process Observation (Time Study)
Observe 10-20 representative task executions passively. Record start/end times,
document count, complexity class. Time AI-assisted execution on same sample.
Most practitioners consent to observation framed as "process improvement research"
rather than "AI ROI measurement." Requires minimal stakeholder effort.

### Method 2: Industry Benchmark Mapping
Apply peer benchmarks with a 25-35% conservatism discount for implementation
maturity/tool differences. Always document: which benchmark, source, discount applied.
Present as "Based on [institution], adjusted by 30% conservatism factor..."

### Method 3: Analogous Project Transfer
Map from a known completed internal AI project using a similarity coefficient:
- 1.0 = identical task
- 0.6-0.8 = structurally similar (different document type, same workflow pattern)
- 0.4-0.6 = partial analog (different domain but same labour substitution pattern)

### Method 4: Bottom-Up Productivity Model
Build from observable inputs only (no stakeholder self-reporting):
- Volume: from systems of record (deed management system, marketing approval workflow)
- Baseline time: Method 1 or benchmark
- Reduction factor: vendor-validated performance × 0.7 (production variance discount)
- Hourly loaded rate: from HR (available without individual stakeholder)
- Error rate: from published benchmarks or quality audit data

Formula:
  Annual Benefit =
    (Volume × Baseline_Time × Reduction_Factor × Hourly_Rate)
    + (Volume × Error_Rate_Reduction × Cost_per_Error)
    + (Compliance_Incidents_Avoided × Avg_Remediation_Cost)

### Method 5: Regulatory Cost Avoidance Valuation
Quantify as risk-weighted penalty avoidance. Engages Risk/Legal rather than
business-line (routes around disengaged stakeholders).
Steps:
1. Identify regulatory obligations discharged (ASIC RG 234, AML/CTF Act, etc.)
2. Find max penalty + historical breach frequency for comparable AU FS firms.
3. Probability-weight: (Prob. of breach per year) × (Expected penalty + remediation)
4. Estimate AI contribution to reducing breach probability (conservative: 10-20% Y1)

### Method 6: NII Revenue Acceleration (for approval-chain AI)
NEW — applicable when AI reduces the time from conditional to unconditional approval.
See "NII Revenue Acceleration Model" section above for the full formula and worked examples.
This method is typically the largest single benefit for mortgage processing AI and should
be presented first when the use case is in the lending/approval chain.

### Triangulation Output Format
Present as a range, not a point estimate (Gartner recommendation for low-engagement contexts):

  Method 1 (observation):        AUD [X] - [Y]
  Method 2 (benchmark):          AUD [X] - [Y]
  Method 3 (analogous):          AUD [X] - [Y]
  Method 4 (bottom-up):          AUD [X] - [Y]
  Method 5 (regulatory):         AUD [X] - [Y]
  Method 6 (NII acceleration):   AUD [X] - [Y]  ← lead with this for lending AI
  ----------------------------------------
  Central estimate:               AUD [mid]
  Lower bound (for Finance):      AUD [low]
  Upper bound (strategic):        AUD [high]

Present central to sponsors. Lower bound to Finance/Risk. Upper bound for strategic
framing only — never as the primary claim.

### Converting ABEF into a Stakeholder Engagement Catalyst
Don't ask stakeholders to generate estimates (creates perceived headcount risk).
Present the ABEF estimate as a draft and ask them to correct specific assumptions.
"We estimated X. We believe the primary uncertainty is assumption A. Can you confirm?"
This transforms the dynamic from open-ended to targeted correction — much lower friction.
Source: North Highland, Mastering Benefits Realization, Aug 2025.
URL: https://northhighland.com/insights/guides/mastering-benefits-realization-outcome-management

---

## Scale Adjustment for Different AU Bank Sizes

NAB benchmark (15,000 trust deeds/year) is major-bank scale. Adjust:
- Regional bank (AUD 30-100B balance sheet): 0.2-0.4x volume
- Mid-tier bank (AUD 5-30B): 0.05-0.15x volume
- Customer-owned/mutual: 0.02-0.05x volume

Marketing communications volume scales by product range breadth + campaign frequency,
not balance sheet size. Active mid-tier: ~200-500 materials/yr; major bank: 2,000-5,000+.

For NII acceleration model, scale by new origination volume, not balance sheet size directly.
- Large major (NAB/CBA): AUD 40-80B new originations/yr
- Mid-tier major (WBC/ANZ retail only): AUD 20-40B
- Regional bank: AUD 3-10B

---

## Layered Benefits Beyond Time Savings (for building fuller business cases)

1. Throughput: "can review 10x the deeds without additional headcount" (stronger
   framing than "saves 44 minutes each" — less threatening to stakeholders)
2. Quality/accuracy: error rate reduction, audit trail improvement, reproducibility
3. Scalability: linear headcount growth replaced by marginal model serving cost
4. Regulatory posture: documented review creates APRA/ASIC audit evidence that
   manual processes cannot provide
5. Staff experience: reduced attrition on repetitive tasks; higher-value work retention
6. NII acceleration: earlier settlement = interest income earlier (see model above)
7. NPS / customer retention: speed reduces #1 mortgage friction point (see NPS section)

WEF/Accenture (2026): "biggest benefits come from redesigning holistically" — layers
2-7 often exceed the productivity (layer 1) benefit over a 3-year horizon.

---

## Key Framework References

- McKinsey five-layer AI measurement framework (benefit estimation stalls because
  process owners refuse to estimate own time, fearing headcount implications):
  URL: https://www.mckinsey.com/capabilities/quantumblack/our-insights/from-promise-to-impact-how-companies-can-realize-the-full-value-of-ai

- WEF/Accenture AI Playbook for Financial Services, Jun 2026 (150+ senior leaders,
  100+ orgs; two-speed model; holistic redesign):
  URL: https://reports.weforum.org/docs/WEF_The_AI_Playbook_for_Financial_Services_2026.pdf

- EAJournals: Integrated AI Impact Measurement Framework for FinTech, Jul 2025:
  URL: https://eajournals.org/ejcsit/wp-content/uploads/sites/21/2025/07/Integrated-AI.pdf

- Gartner Peer Community: AI ROI — two-pronged framework (quantitative KPIs +
  qualitative factors; range not point estimate; benchmarked over time), Aug 2025:
  URL: https://www.gartner.com/peer-community/post/how-have-calculated-roi-ai-solutions-including-agents-ve-rolled-at-firm-specific-kpi-s-ve-focused-how-have-measured-validated

- KPMG Big 4 Half-Year Results 2026 (NIM, NII, cost-to-income, tech spend +32.6%):
  URL: https://kpmg.com/au/en/insights/industry/big-four-major-banks-australia-half-year-results-2026.html

- KPMG Global AI Pulse Q2 2026 (ROI accountability, cost visibility, 7% established ROI):
  URL: https://www.uctoday.com/productivity-automation/kpmg-ai-cost-visibility-roi-survey-2026/

- WorldMetrics Mortgage CX Statistics (100 verified stats, 53 primary sources, Jun 2026):
  URL: https://worldmetrics.org/customer-experience-in-the-mortgage-industry-statistics/

- Roy Morgan Home Loan Satisfaction May 2026 (AU-specific, n=28,398):
  URL: https://www.roymorgan.com/findings/10278-home-loan-satisfaction-may-2026

- NAB FY2025 Results MDA (NIM 174 bps):
  URL: https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2025-full-year-results-management-discussion-and-analysis.pdf

---

## Pitfalls

- **Lead with NII acceleration, not headcount, for lending AI**. Headcount savings are
  real but modest and politically toxic. NII pull-forward scales better and avoids FTE debates.

- **Verify deed review is on the critical path before using NII model**. If deed review
  runs in parallel with credit decisioning or valuation, acceleration is partial only.
  Waste of effort to model it fully if it's not the bottleneck.

- **NPS claim must be directional, not quantified**. No study isolates trust deed review
  speed as a specific NPS driver. The claim is "targeted at the #1 satisfaction friction
  point." Do not use the Artificio.ai "25-30 NPS point" figure — it has no primary source.

- **Roy Morgan satisfaction data is correlational only for NAB**. NAB's +6.5pp improvement
  aligns with AI rollout timing but has many confounds (rate environment, service changes).
  Don't claim causation; use as supportive framing only.

- Vendor case studies (HCLTech, Onix) may reflect best-case outcomes. Apply 25-35%
  conservatism discount when transferring to an internal business case.
- NAB's 45-min figure is from a trade publication (Nov 2024), not a formal annual
  report. Use as primary benchmark but cross-check with your own observation (Method 1).
- 45% of FS AI projects don't reach production. Plan for 30-40% failure rate at
  portfolio level — don't present individual initiative ROI as portfolio ROI.
- Regulatory penalty figures are indicative maximums. Actual enforcement varies
  significantly — frame as probability-weighted, not certain.
- Do NOT present benefit ranges from this framework as financial, legal, or regulatory
  advice. Engage qualified AU counsel for APRA/ASIC compliance decisions.

# Comparative / external-landscape sweep — worked recipe

Task shape: "Research OTHER pertinent initiatives … Do NOT re-validate the source document's own content — research what's OUTSIDE it for comparison." The deliverable is a landscape map of external analogues + a per-section tie-back to the document's architecture. Do NOT quote or fact-check the source memo itself.

Worked instance: AI-governance memo, "Cluster F — Other pertinent initiatives", July 2026. Memo architecture under comparison: Champion-network + phased rollout + gated AI-literacy + kill-switch incident response. Output written to `.../research/cluster_F_other_initiatives.md` (~14KB, 7 sections, all source URLs inline).

## Topic families that recur for an AI-governance memo comparison

1. **Frontier-lab responsible-scaling frameworks** (tiering analogues at the model layer):
   - Anthropic RSP v3 (Feb 2026): AI Safety Levels ASL-2/3/4; crossing a Capability Threshold forces ASL-3 Security and/or Deployment Standard. anthropic.com/responsible-scaling-policy ; /news/responsible-scaling-policy-v3
   - OpenAI Preparedness Framework v2 (Apr 2025): Tracked Categories (Bio/Chem, Cyber, AI Self-Improvement) × High/Critical. cdn.openai.com PDF.
   - DeepMind Frontier Safety Framework v3 (Sep 2025): Critical Capability Levels (CCLs) across autonomy/biosecurity/cyber/ML-R&D. deepmind.google/blog/strengthening-our-frontier-safety-framework
   - Shared skeleton: capability-threshold → escalating-safeguard. Layer note: these govern the *model* layer; a deployment memo governs the *deployment* layer — complementary.

2. **AI Safety / Standards Institutes** (evaluation & red-teaming methodology — watch the renames):
   - UK **AI Security Institute** (renamed from "AI Safety Institute", 2025): Inspect eval framework — inspect.aisi.org.uk ; github.com/UKGovernmentBEIS/inspect_ai
   - US **CAISI** (Center for AI Standards & Innovation; renamed from US AISI, June 2025; in NIST): nist.gov/caisi
   - Japan **AISI** (aisi.go.jp): English "Guide to Red Teaming Methodology on AI Safety" v1.00 + v1.10 annex; github.com/Japan-AISI/aisev
   - France **INESIA** (est. 2025): economie.gouv.fr; SGDSN 2026–2027 roadmap PDF.
   - Cite the *current* name + specific artifact; don't cite the superseded "US AISI".

3. **AI incident reporting / databases** (reconcile internal process against these):
   - OECD AI Incidents & Hazards Monitor (AIM): 14 thematic clusters. oecd.ai/en/incidents
   - EU AI Act **Article 73** serious-incident reporting: statutory duty for high-risk-system providers to report to market-surveillance authorities without undue delay; Commission draft guidance + template Sept 2025. artificialintelligenceact.eu/article/73
   - AI Incident Database (AIID), Responsible AI Collaborative: 1,000+ crowdsourced reports; mirrored by MIT AI Incident Tracker. incidentdatabase.ai
   - Tie-back: internal kill-switch/triage is necessary but NOT sufficient for EU-market Art. 73 statutory reporting; recommend reconciling internal taxonomy with AIM clusters + Art. 73 severity tiers.

4. **Comparable enterprise product governance** — apply provenance-tier labeling (see below).

5. **Enterprise AI-literacy case studies** (10k+ employees, measurable outcomes): most public case data is vendor-authored (Simplilearn 10k+ upskilling) — treat outcome figures as claims. The strongest *independent* anchor was academic: "AI literacy development canvas" (Business Horizons / ScienceDirect, Oct 2025) framing literacy as a multidimensional org capability with a validated assessment instrument. Recommend the memo cite a validated capability-assessment instrument, not completion-rate metrics alone.

## Provenance-tier labeling for the product comparator (Claude Cowork worked example)

- **Verified (vendor's own docs/blog):** admin private plugin marketplaces, per-user provisioning, auto-install, unified "Customize" admin menu, connector controls, OpenTelemetry monitoring (claude.com/docs/cowork/monitoring), plugins as portable file systems (open-source templates: github.com/anthropics/knowledge-work-plugins). Cite URLs.
- **Marketing / promotional:** PwC/customer testimonials; the "Silvern Capital" demo — whose own blog footnote states it is a *fictional company*. Capability-signalling, not governance evidence.
- **Speculative / UNCONFIRMED (flagged):** no public Anthropic doc of a formal "kill switch"; no platform-level "gated AI-literacy" requirement tied to access; no granular per-skill permission model at the depth the memo implies. Admin controls (revoke provisioning, disable plugins) *approximate* containment without *being* a documented kill-switch primitive. Flag each as an assumption to verify with the vendor.

## Non-English venue honesty (comparator research)

Same discipline as the companion-sweep reference, applied to comparators. The search backend intermittently failed on CJK query strings (`Connection refused`, `tls handshake eof`) — disclose every failure; never fabricate to compensate.
- **ZH** (`人工智能安全研究院 / 人工智能事故 数据库`) — succeeded: CAICT (中国信通院) AI-security report (aihub.caict.ac.cn), Beijing Institute for AI Safety & Governance (beijing.ai-safety-and-governance.institute), ZH-language AIID coverage.
- **JA** (native `AIセーフティ研究所 レッドチーミング …`) — backend FAILED twice; English-backup query surfaced the authoritative primary source aisi.go.jp. No fabrication; primary confirmed via backup.
- **FR** (`INESIA évaluation`) — succeeded: French govt primary sources + SGDSN roadmap PDF.

Pattern: when a native CJK query fails on the backend, an English-backup query naming the institution usually surfaces the authoritative primary source (the institute's own .go.jp / .gouv.fr site). Report the failure AND the successful backup route in the methodology/disclosure section.

## Section shape that worked

Each topic family = one section ending in an explicit "**Comparison to the document**" paragraph. Close the report with a "Bottom-line comparison to the document's architecture" section that, per memo construct (tiering / kill-switch / literacy-gating / incident-response), states: does the external world confirm the skeleton, what's the layer difference, what's unverified, and what the document must reconcile against externally.

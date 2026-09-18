# Human Oversight / HITL Decay / Vigilance / Autonomy-Gating — External Precedent Sweep (2026)

**Context:** "Cluster D" of a multi-cluster external-literature sweep for a legal/AI-governance critique (same critique family as the NAB LIP rounds). Source memo argued "a human checks it" is not a durable control at scale (HITL decay / automation bias) and prescribed forced-friction confirmation, vigilance probes, and a per-skill autonomy gate. Task: research what's OUTSIDE the memo, do NOT re-validate its own content, and assess novelty of each mechanism against precedent.

## Output mode used: PRECEDENT / NOVELTY AUDIT (distinct from the other modes in SKILL.md)

This is neither a fresh survey, a delta sweep, a tag-applicability findings file, nor a document-patch. It's a **precedent-and-novelty audit** of a source document's proposed mechanisms:
1. For each mechanism the source proposes, find the strongest external precedent (foundational science → operational instantiation → regulatory codification).
2. Produce a **comparison table** with columns: `mechanism | precedent status (well-precedented / partially novel / novel) | key external anchor`.
3. Close with an explicit **novelty verdict** separating (a) the diagnosis, (b) the individual mechanisms, and (c) any genuinely-novel composite — so the critique author knows what to cite as established vs. what is the source's own contribution.
4. The value is telling the author "your diagnosis is textbook, cite X; your probes have a mature operational precedent, cite Y; only your composite gate Z appears novel" — NOT re-proving the memo right.

## Verified findings (durable, reusable anchors for automation-bias / oversight critiques)

- **Automation bias / complacency foundation:** Parasuraman & Manzey (2010), "Complacency and Bias in Human Use of Automation: An Attentional Integration," *Human Factors* 52(3):381–410. Open copy: depositonce.tu-berlin.de (search title). Key: complacency + bias share one attentional mechanism; **strongest precisely when automation is highly reliable** — the direct theoretical basis for "reviewers stop reading after many correct runs." SAGE doi:10.1177/0018720810376055.
- **Vigilance decrement foundation:** Klein & Feltmate (2025), "The vigilance decrement: its first 75 years," *Frontiers in Cognition* 4:1632885, doi:10.3389/fcogn.2025.1632885. Mackworth (1948) established rare-target detection declines with time-on-task. **Load-bearing for design critique:** Mackworth found interruptions/breaks/performance-feedback reduce the decrement while *merely urging attention does nothing* → structural interventions > exhortation. Analyzed via Signal Detection Theory (sensitivity d′ vs. criterion β).
- **Vigilance-probe precedent (STRONGEST):** **Threat Image Projection (TIP)** — airport X-ray screening injects Fictional Threat Items (FTI) into a fraction of live bag images to measure/sustain screener vigilance. This is the exact "inject known items into the live human review queue" mechanism, operational at national-security scale for ~2 decades, with peer-reviewed validity studies: *Applied Ergonomics* (2025, sciencedirect S096585642500268X), *Int. J. Human–Computer Interaction* (2025, tandfonline 10.1080/10447318.2025.2598113), *Sensors* 22(6):2220 (2022, mdpi). In SDT terms these are **catch trials**. Caveat from the lit: probe *realism* matters — if reviewers learn to spot "test" items the measure collapses.
- **Meaningful Human Control:** Santoni de Sio & van den Hoven (2018), "Meaningful Human Control over Autonomous Systems: A Philosophical Account," *Frontiers in Robotics and AI* 5:15, doi:10.3389/frobt.2018.00015. Two conditions — **tracking** (system responds to relevant human reasons) + **tracing** (behavior traceable to a human with technical+moral understanding). "Named risk owner + rollback" ≈ the tracing condition operationalized.
- **Regulatory codification:** **EU AI Act (Reg (EU) 2024/1689) Article 14** — 14(4)(b) *names "automation bias" verbatim*; 14(4)(d)-(e) override right + stop button; 14(5) **two-person ("four-eyes") verification** for biometric ID (regulatory analogue of forced-friction confirmation); 14(3) oversight "commensurate with risk, autonomy, context." Authoritative text: artificialintelligenceact.eu/article/14/.

## Non-English tracks (venue disclosure + honest gaps)

- **Chinese — real academic hit:** 杨惠丽 等 (2024), "人工智能使用过程中自动化偏差文献述评与研究展望" (Literature Review and Research Prospects on Automation Bias in the Use of AI), *科技管理研究* 44(21). Independently lists automation bias as "excessive reliance, reduced vigilance, neglect of verification, individual differences"; flags **immediate error feedback** as a system-level mitigator (converges with Mackworth). URL: kjglyj.ijournals.cn/kjglyj/article/abstract/20240724033.
- **Japanese — results found but NON-peer-reviewed** (Databricks JP blog, Forbes JAPAN, note.com). No J-STAGE primary source confirmed this pass. Reported as an **open gap, not a null** — a targeted J-STAGE query failed on the search backend, not on substance.
- **French — definitional + legal only** (biais-psychologiques.com; LinkedIn analysis of AI Act Art. 14 "supervision humaine efficace"). No HAL/Cairn peer-reviewed psychology confirmed. **Open gap** due to intermittent backend failures — flag for a follow-up pass directly against hal.science / cairn.info.

## Novelty verdict template (reuse this three-part split)

- **Diagnosis** (HITL decay / automation bias / vigilance decrement): NOT novel — textbook human-factors (75+ yrs), now in EU law.
- **Individual mechanisms** (forced friction, vigilance probes): NOT novel as concepts — four-eyes verification + TIP/catch-trials are strong operational precedent; source's contribution is *porting* them into per-skill AI-workflow governance.
- **Composite** (`pass^k` repeated-run stability + the single releaseable per-skill autonomy gate = numeric override ceilings + zero-safety-miss + canary + named owner): the **most plausibly novel** element — no external source presents this exact composite. Frame as an *operationalization* of MHC's tracing condition + SDT stability, not a restatement.

Final report written to: `Documents/Legal Architecture/research/cluster_D_human_oversight_hitl.md`.

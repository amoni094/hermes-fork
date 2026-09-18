# Adversarial Synthesis for Scientific Papers — Recursive Pass Methodology

Drawn from: Sirina et al. 2026 (FcRn inhibitor cellular pharmacology, UCB/Excellerate).
Use as a template when synthesising findings from a primary research paper for
presentation or clinical translation work.

## Pass structure

Same loop as code review:
- Each pass produces severity-tagged findings (HIGH / MEDIUM / LOW)
- Fix ALL severities in the same pass
- Stop when a full pass finds no HIGH or MEDIUM

Typical convergence: 3 passes for a well-written primary research paper.

---

## Attack vectors for scientific papers (not code)

### 1. FALSE EQUIVALENCE in endpoint reporting
Papers often claim two treatments "broadly achieve similar X%" to emphasise convergence.
Check: is the timepoint and dose the same? Is the comparator the actual clinical product
or an analog/surrogate? Flatten/compress of onset or depth differences is a HIGH issue.

Example: "both achieve 60-80% IgG reduction" — but RLZ achieves ~70% by Day 8,
efgartigimod achieves ~60% after the 4th cycle (~Day 29). The onset gap is the
clinically important signal; collapsing it to a range misrepresents PD.

### 2. PROXY / ANALOG LIMITATION
Check whether the in vitro compound is the actual clinical product.
If not, every clinical inference is one proxy step removed — this is a MEDIUM issue
that must be explicitly stated in any translation to clinical claims.

Example: MST-HN IgG Fc (ABDEG mutant) is an efgartigimod analog, not efgartigimod
alpha (Vyvgart). The SC PH20 formulation adds further distance. Always flag: "findings
apply to [analog], not the approved clinical product."

### 3. IN VITRO TO CLINICAL TRANSLATION GAPS
Check the experimental conditions vs. physiological reality:
- Serum IgG concentration in vitro vs. in vivo (~12 mg/mL endogenous IgG)
- Cell line / transfected overexpression systems vs. primary cells at physiological expression
- Single-agent incubation vs. competitive multi-ligand environment

If the paper itself flags the gap, note it. If it doesn't, flag it as a MEDIUM issue.

### 4. ARTIFICIAL EXPRESSION SYSTEM BIAS
Convergent findings measured in overexpressing systems may mask differences that
exist at physiological expression levels. Specifically: recycling kinetics measured
in FcRn-transfected MDCK cells (high FcRn) may not reflect normal endothelial cells
(low FcRn). Flag as MEDIUM when a "convergent" conclusion rests entirely on
overexpression data.

### 5. UNTESTED HYPOTHESES PRESENTED AS FINDINGS
Papers frequently raise mechanistic hypotheses (e.g. higher-order complex formation)
and then say "this was not observed in our system." Check: was it directly tested, or
ruled out by absence of signal in a low-sensitivity assay? Distinguish between
"not detected" and "shown not to occur." Flag as LOW-MEDIUM if presented as resolved.

### 6. FUNDING AND COMPETING INTEREST BIAS
Industry-funded studies comparing a sponsor's drug favorably warrant explicit note.
Not a flaw in the data — a framing lens. Always note in the presentation's conclusion
slide. Flag as LOW.

### 7. MECHANISM-TO-OUTCOME CAUSALITY
Faster in vitro uptake does NOT prove faster clinical onset. Multiple alternative
explanations (dosing schedule, molar occupancy, TMDD kinetics) may equally explain
the clinical observation. Presenting a plausible link as confirmed causality is a
MEDIUM issue. Frame as "plausibly explains" or "consistent with", not "demonstrates."

---

## Convergent findings: handle carefully

When two compounds converge on a finding (e.g. similar recycling kinetics), check:
- Was the convergence measured in the same system as the divergent finding?
- Could a nuanced difference (e.g. prolonged Rab11 dwell for one compound) be
  understated as "similar" when it may have downstream PD implications?

Prolonged Rab11 sequestration = longer recycling endosome residence = potentially
more sustained receptor occupancy. Present as a positive hypothesis, not just a caveat.

---

## Severity assignment guide (science-specific)

| Issue type | Severity |
|---|---|
| False equivalence in primary endpoint | HIGH |
| Proxy analog mistaken for clinical product | HIGH |
| Mechanism-to-outcome presented as causal | MEDIUM |
| In vitro conditions diverge from in vivo | MEDIUM |
| Overexpression system bias in convergent finding | MEDIUM |
| Hypothesis not directly tested | MEDIUM |
| Prolonged Rab dwell understated | LOW |
| Funding bias not disclosed | LOW |

---

## Example: Sirina et al. 2026 resolved issues

Pass 1:
- HIGH: "both achieve 60-80% IgG reduction" conflates Day 8 vs Day 29 onset
- HIGH: MST-HN IgG Fc used as efgartigimod; proxy not flagged
- MEDIUM: low-IgG in vitro conditions mask competitive context
- MEDIUM: recycling convergence measured in FcRn-overexpressing MDCK, not HUVECs
- MEDIUM: higher-order complex hypothesis not directly tested
- LOW: UCB-funded, UCB-majority authors
- LOW: Rab proteins not exclusive markers; GFP-Rab overexpressed

Pass 2 (after fixes):
- MEDIUM: "faster uptake = faster onset" presented without ruling out dosing schedule,
  TMDD kinetics, or molar occupancy as confounders
- LOW: prolonged Rab11 sequestration in RLZ framed as caveat; should be positive hypothesis

Pass 3: CLEAN (no HIGH/MEDIUM).

Final narrative: RLZ pH-independent receptor-mediated uptake vs efgartigimod fluid-phase
pinocytosis is the sharpest mechanistic divide. Trafficking converges post-endosome.
Prolonged Rab11 dwell for RLZ may explain sustained PD to Day 43. Albumin divergence
(Yasuda 2026 RWE) is the cleanest mechanism-to-biomarker clinical link.

---

## Reference validation: detecting fabricated PMC IDs

LLMs generating bibliographies for literature with sparse DOI coverage (e.g. FAERS
pharmacovigilance analyses, grey-literature reports) sometimes fabricate plausible-looking
PMC article IDs. The fabricated ID is syntactically valid but resolves to a 301 redirect
with no article content.

**Detection:**
```python
import subprocess

def check_pmcid_real(pmcid: str) -> bool:
    """Returns True if the PMCID resolves to a real article."""
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
           f"?db=pmc&id={pmcid}&rettype=xml&retmode=xml")
    r = subprocess.run(["curl", "-s", "--max-time", "8", url],
                       capture_output=True, text=True)
    return "<article-id" in r.stdout or "<article-title" in r.stdout
```

**Recovery:** if the PMCID fails, web-search for the actual paper:
```
web_search("FAERS pharmacovigilance [drug A] [drug B] adverse events disproportionality doi")
```
Then verify the candidate DOI via Crossref:
```
https://api.crossref.org/works/<doi>
```
A real article returns full metadata (authors, title, journal, year). A fabricated DOI
returns a 404 or empty `items` array.

**This session:** `PMC12622354` was fabricated. Replaced with Liu et al. 2025,
"Pharmacovigilance analysis of FcRn antagonists in the treatment of myasthenia gravis:
a disproportionality analysis of the FAERS database,"
DOI `10.1080/21645515.2025.2586335` (Hum Vaccin Immunother; Crossref-verified).

**Rule of thumb:** always run Crossref validation on every DOI in an LLM-generated
reference list before using the list in a client-facing document. Budget one
`curl api.crossref.org/works/<doi>` call per reference — the full 14-reference pass
in this session took under 30 seconds and caught 4 wrong DOIs plus 1 fabricated PMCID.

---

## Clinical literature brief / patient-facing synthesis (Aug 2026)

Use when the deliverable is a **cited clinical briefing** (email or memo) that ranks
interventions and proposes a home routine from RCTs/NMAs/CPGs — not when reviewing
a single primary wet-lab paper.

### Extra attack vectors
| Vector | Severity | What to check |
|---|---|---|
| Abstract≠full-text protocol | HIGH | Session count, duration, frequency, hold times — must match full text or be flagged abstract-only |
| Routine mislabeled as trial protocol | HIGH | Home program must say “clinical synthesis,” not imply one RCT’s exact sequence |
| NMA rank collapsed into “best practice” | HIGH | If CPG grade or critique conflicts, keep both; don’t pick the flattering tier only |
| Mechanism overclaim | MEDIUM | Soft-tissue/TrP benefit ≠ disease etiology rewrite |
| Safety absolute without source | MEDIUM | Vascular/pregnancy/red-flag rules → `[unverified]` or cited guideline |
| Multi-cite laundry list | LOW–MEDIUM | >3 ids/sentence or design-goal one-liners with 4+ citations hide load-bearing source |
| Citation bleed into self-review | MEDIUM | Adversarial appendix mentioning `[n]` still trips `sources.py verify` — scrub or use words |
| **Triple restatement / mid-doc clone** | **HIGH** | Same ranking or full routine appears as design goals + body + takeaways, or the file contains two full email bodies — user treat as broken deliverable |
| **Protocol restated twice** | **MEDIUM** | e.g. Varkey 15+20+5 RPE in both efficacy and routine sections — keep effect size in efficacy, prescription once in routine |
| **Citation mode violation** | **HIGH** when user asked end-only | Mid-body `[n]` or a Sources block mid-file after user required “references only at the end” — body must be author–year; one Sources at end |
| Praising A while downgrading B | META | Different interventions/evidence tiers is OK if labeled; false if same endpoint treated as both strong and weak |

### Recursive loop note (email/report form)
1. Pass 1: protocol fidelity + ranking honesty + routine labeling + **single-version structure** (no triple restatement, no mid-file duplicate body).
2. Pass 2: safety language, mechanism caution, citation hygiene (ledger verify **or** end-only author-year ↔ Sources name match).
3. Pass 3: meta-check (apparent contradictions that are actually tier differences) + citation-mode compliance.
4. Pass 4 (if user already complained about duplication): re-read whole file for residual double protocols; trim; stop only when one efficacy block and one routine block each remain.
Stop when no HIGH/MEDIUM correctness issues remain; leave LOW style nits.

Worked session: migraine stretch brief — fixed Rezaeian session-count conflation,
labeled yoga/aerobic/neck package as synthesis, kept strength NMA vs C-grade + Benatto
null in productive tension, stripped phantom citation tokens from adversarial prose,
then **consolidated** after user flags (drop design-goals + takeaways recap; end-only
Sources; Varkey dose only in §routine; single print). Access path:
`academic-literature-review/references/pubmed-openalex-biomedical-bypass-2026.md`.
Protocol bank:
`academic-literature-review/references/migraine-yoga-aerobic-protocols-2026.md`.

### Expansion re-pass (when user adds “best yoga + best aerobic” mid-brief)
After inserting full prevention prescriptions into the body:
1. Re-run Pass 1 vectors on **new** dose/RPE/asana/frequency claims only (full-text
   fidelity; synthesis labeling; effect-size honesty — e.g. Varkey absolute Δ).
2. Re-run `sources.py verify --evidence` (inline mode) **or** body author-year ↔
   end Sources alignment (end-only mode); fix multi-cite laundry lists and appendix bleed.
3. Meta-check: ranking section still matches the expanded routine (no “stretch-only
   best” headline conflicting with yoga+aerobic package in the body).
4. If expansion re-introduced a second full recap or duplicated protocol lines,
   rewrite the whole email once — do not stack another partial patch on a bloated draft.
Do not declare clean from the pre-expansion adversarial pass alone.

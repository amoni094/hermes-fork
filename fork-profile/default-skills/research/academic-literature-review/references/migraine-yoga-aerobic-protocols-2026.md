# Migraine prevention: yoga + aerobic protocol bank (Aug 2026)

Condensed from the migraine stretch/clinical-email brief. Use when a clinical
brief needs **named prevention packages** (not just “do yoga/exercise”).

## Ranking honesty (do not collapse)

| Layer | Best-supported stretch-containing vehicle | Best aerobic template | Caveat |
|-------|-------------------------------------------|------------------------|--------|
| CPG-style | Yoga / mobility package (often B-grade with aerobics) | Moderate continuous aerobic (B-grade) | Isolated stretch alone is weak as standalone prevention |
| NMA | Strength sometimes ranks high on days | — | Keep separate from CPG grades; inclusion bias exists |
| Home routine | **Clinical synthesis**, not one-trial copy | Same | Label every routine block as synthesis |

## Best yoga-style mobility (prevention stretch vehicle)

**Style:** integrated **Hatha** (looseners → asana → breath → Shavasana). Prefer
this over power/hot yoga for migraine prevention packages unless a trial used
those styles.

**Asana core (Mehta et al. 2021 additive yoga+PT RCT — DOI 10.1055/s-0041-1735241):**
Bhadrasana/butterfly, Supta Matsyendrasana, Bhujangasana/cobra, Padahastasana,
Trikonasana, Savasana. Add **cat–cow** as home-synthesis cervical/thoracic
mobility (not Mehta-named — label optional/synthesis).

**Session structure anchor (Kisan et al. 2014, Ann Indian Acad Neurol, PMC4097897):**
looseners + breathing + asanas + Shavasana; ~**1 h × 5 days/week × 6 weeks** with
conventional care. Do **not** attribute the Mehta asana list to Kisan.

**Dose patterns (trial-anchored, not identical copy):**
- Kisan 2014: structure + heavy weekly dose (~1 h × 5 d/wk × 6 wk).
- CONTAIN / **Kumar et al. 2020**, *Neurology* DOI 10.1212/WNL.0000000000009473:
  yoga **add-on**, ~5 days/week, multi-month (~3 months); frequency delta ~3.5
  headache days — use for practice frequency/duration, not mandatory 60-min classes.
- Home synthesis default: **~5×/week, 25–40 min, 8–12+ weeks** before judging prevention.

**Session order (synthesis):** looseners → asanas → breathing → Shavasana.
**Minimal day (~10–12 min):** cat–cow → butterfly → twist → breath → rest.

**Full-text access notes:** Kisan OA often via Europe PMC PMC4097897 /
fullTextXML. CONTAIN may be paywalled on Neurology HTML — prefer DOI metadata +
secondary OA summaries; flag abstract-only if protocol table not retrieved.
Mehta: pull full text before listing holds as trial-exact.

## Best aerobic prevention template

**Primary template — Varkey et al. 2011 (*Cephalalgia*):** indoor cycling RCT.
- Warm-up **15 min RPE 11–13**
- Main set **20 min RPE 14–16**
- Cool-down **~5 min**
- Total **~40 min × 3/week** for **~3 months** in the trial

**Modes:** bike preferred in the trial; walk / swim / elliptical OK in synthesis
if neck-jarring modes trigger attacks.

**Weekly volume build:** toward **~90–150 min moderate/week** (~**300–600 MET-min**),
aligned with dose-response analyses — cite the dose-response paper separately
from Varkey; do not invent MET numbers as Varkey endpoints.

**Effect-size honesty:** Varkey absolute reduction was **modest** (~0.9 attacks/month
in that trial) while matching topiramate/relaxation arms on some comparisons.
Do not sell aerobic exercise as “large effect” without the absolute figure.

## Relief block (when neck TrPs reproduce headache)

Heat → self-MFR → **upper trapezius + SCM + suboccipital** stretches → breathing
(~8–12 min). Prefer short physio course if this is the dominant pattern.
Soft-tissue RCT protocol parameters require **full text** (e.g. Rezaeian session
count: 6 over 2 weeks, 3×/week, ~20 min — not abstract-compressed versions).

## Weekly skeleton (synthesis example)

Mon yoga · Tue aerobic · Wed yoga · Thu aerobic · Fri yoga ± relief · Sat aerobic · Sun rest/minimal ± strength

## Europe PMC fullTextXML for protocol tables

When NCBI PMC HTML is blocked, pull JATS XML:

```
https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML
```

Parse `<table-wrap>` / methods paragraphs for asana lists, RPE, session counts.
Save XML to `/tmp/…` and extract with Python `re` — do not guess hold times.

## Citation hygiene for expanded packages

When the user asks to **add** best yoga + aerobic **into the email body**:
1. Expand body with dose + style + effect-size caveats (not name-only bullets).
2. Register protocol sources in the ledger and `quote` from full text.
3. Re-run `sources.py verify draft.md --evidence` **or** (end-only mode) align
   author–year labels in body with a single end Sources list.
4. Split multi-cite sentences (>3 ids) so verify stays clean; in end-only mode
   drop mid-body `[n]` entirely.
5. Re-run adversarial pass on **new** protocol-fidelity claims **and** structure
   (no triple restatement; Varkey/yoga dose once under routines).
6. After user “consolidate / print once”: rewrite whole email, one print only.

## Primary anchors (verify live before citing)

| Role | Typical cite |
|------|----------------|
| Yoga session structure / heavy dose | Kisan et al. 2014, Ann Indian Acad Neurol (PMC4097897) |
| Named asana set | Mehta et al. 2021, DOI 10.1055/s-0041-1735241 |
| Yoga add-on frequency / delta days | CONTAIN / Kumar et al. 2020, Neurology DOI 10.1212/WNL.0000000000009473 |
| Aerobic RPE template | Varkey et al. 2011, Cephalalgia DOI 10.1177/0333102411419681 |
| Aerobic/yoga CPG grades | La Touche exercise CPG (year per live lookup) |
| Soft-tissue / TrP | Rezaeian full text (not abstract alone) |
| Strength NMA vs grade | Woldeamanuel NMA + Han/Cho comment + CPG C-grade tension |

Update this bank when a newer head-to-head changes the B-grade yoga/aerobic picture.

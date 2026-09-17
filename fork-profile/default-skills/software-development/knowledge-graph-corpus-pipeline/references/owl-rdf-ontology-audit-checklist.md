# OWL/RDF Ontology Audit Checklist

Systematic audit methodology derived from the July 2026 comparative mythology
ontology consolidation pass. Apply this before re-running graph_enrich.py after
any schema change, and whenever adding new properties or classes.

---

## HIGH-Severity Issues (break OWL-DL consistency or cause runtime errors)

### 1. Module-level constants referencing undefined names

**Pattern:** A module-level constant defined before its dependency.

```python
# BAD — ANALYSIS_DIR references BASE_DIR before it is defined
ANALYSIS_DIR = BASE_DIR / "analysis" if False else Path("~/Religion/analysis").expanduser()
BASE_DIR = Path("~/Religion").expanduser()   # defined AFTER use above
```

The `if False` branch hides the error at import time in this specific case,
but it is a fragile hack. Any refactor will break it.

**Fix:** Always define path constants in dependency order:
```python
BASE_DIR      = Path("~/Religion").expanduser()
SCRIPTS_DIR   = BASE_DIR / "scripts"
ONTO_DIR      = BASE_DIR / "ontology"
CHROMA_DIR    = BASE_DIR / "chroma_db"
LOG_FILE      = SCRIPTS_DIR / "graph_enrich.log"
ANALYSIS_DIR  = BASE_DIR / "analysis"
MOTIF_ANALYSIS_FILE = ANALYSIS_DIR / "motif_analysis.json"
CROSS_LINKS_FILE    = ANALYSIS_DIR / "cross_links.json"
```

---

### 2. Typos in class/property names that break range declarations

**Pattern:** A class is declared with a typo, and a property's `range_` points
to the typo'd URI — creating a dangling reference.

**Example:** `MYTH.ThomsonMotifCategory` (Thomson) vs the correct
`MYTH.ThompsonMotifCategory` (Thompson). The property:
```python
declare_prop(MYTH.thompsonMotif, ..., range_=MYTH.ThomsonMotifCategory)
```
…pointed to an undefined class URI.

**Fix:** After declaring any class and any property that references it,
grep for both spellings and confirm they match:
```bash
grep -n 'Thomson\|Thompson' ontology.py
```

---

### 3. Property domain/range violations between scripts

**Pattern:** A property is declared with a specific `domain=X` in ontology.py,
but another script adds it to instances of class Y (Y ≠ X).

**Example:** `myth:influencedBy` declared `domain=ReligiousText`, but
`add_influence_links()` in graph_enrich.py applied it between `Tradition` nodes.

**Fix:** When the use-case genuinely needs two different subject classes:
- Keep the original property for the original domain (text→text)
- Add a new property for the new domain (tradition→tradition):
  ```python
  declare_prop(MYTH.traditionInfluencedBy, "tradition influenced by", ...,
               domain=MYTH.Tradition, range_=MYTH.Tradition)
  ```
- Update the enrichment script to use the correct property name.

---

### 4. Declared properties never populated

**Pattern:** An object property is declared in the ontology but no enrichment
script ever adds triples using it — dead schema weight.

**Example:** `myth:traditionsShare` (Tradition→NarrativeMotif, symmetric) was
declared but never populated. SPARQL queries on it returned empty.

**Fix:** For every declared object property, verify at least one enrichment
function populates it. If none does, either:
- Add a `populate_X()` function, or
- Remove the property declaration.

---

### 5. Wrong Thompson Motif-Index codes

**Pattern:** Multiple motifs share `"A0"` as their Thompson code. `A0` is the
catch-all/undefined placeholder — it means "not yet classified". Using it for
10+ motifs makes the `thompsonCode` property useless for cross-referencing.

**Known bad codes found in motif_taxonomy.py (July 2026):**

| Motif ID | Was | Should be |
|---|---|---|
| `divine_twins` | A0 | A515 |
| `sacrifice_creation` | A0 | A614 |
| `initiation` | A0 | H1558 |
| `dualism` | A0 | A106 |
| `afterlife_judgment` | E0 | E755 |
| `soul_immortality` | E0 | E10 |
| `logos` | A0 | A625.1 |
| `karma` | A0 | Q0 |
| `dharma` | A0 | A180 |
| `moksha_liberation` | A0 | V220 |
| `monotheism` | A0 | A102 |
| `eschatology` | A0 | A1006 |
| `ahimsa` | A0 | W26 |
| `tao` | A0 | A165.1 |
| `wu_wei` | A0 | W10 |

**Fix:** Look up the correct code in the Thompson Motif-Index (Stith Thompson,
*Motif-Index of Folk-Literature*, Indiana University Press). The letter prefix
indicates category (A=Mythological, B=Animals, C=Tabu, D=Magic, E=The Dead,
F=Marvels, G=Ogres, H=Tests, J=The Wise, K=Deception, L=Reversal, M=Ordaining,
N=Chance, P=Society, Q=Rewards, R=Captives, S=Unnatural Cruelty, T=Sex,
U=The Nature of Life, V=Religion, W=Traits of Character, Z=Miscellaneous).

---

### 12. Helper function closure ordering in build_ontology()

**Pattern:** `declare_dprop()` is defined after `declare_prop()` inside
`build_ontology()`, but a property that should be a DatatypeProperty (e.g.
`hasTextType`, `originalLanguage`) is called with `declare_dprop()` in the
object-property section — before Python has executed the `def declare_dprop`.

This causes: `NameError: name 'declare_dprop' is not defined` at runtime.

**Fix:** Move `def declare_dprop(...)` to BEFORE `def declare_prop(...)` (or at
minimum before its first call site). The helper defs can coexist in any order as
long as each def precedes its first call. The final working order in ontology.py:
```python
def declare_dprop(...):   # defined first — used by hasTextType, originalLanguage
    ...
def declare_prop(...):    # defined second
    ...
# ObjectProperty declarations (declare_prop calls)
# Datatype property section (declare_dprop calls — now safe everywhere)
```

---

### 13. ObjectProperty → DatatypeProperty migration

**Pattern:** `hasTextType` and `originalLanguage` were declared as
`OWL.ObjectProperty` with `range_=MYTH.TextType` / `range_=MYTH.Language`, but
graph_enrich.py stored plain `Literal("scripture")` / `Literal("Sanskrit")` values.
This is a range violation: an ObjectProperty must link to a URI individual, not a
Literal.

**Fix options:**
- **A (chosen):** Change to DatatypeProperty (simpler, works with existing data):
  ```python
  declare_dprop(MYTH.hasTextType, "has text type", ..., domain=MYTH.ReligiousText)
  # default range is xsd:string — drop the class range entirely
  ```
  Keep the OWL class (`myth:TextType`) for future enumerated individuals.
  Add a `rdfs:comment` noting it is reserved for future enumeration.

- **B (more correct OWL):** Keep as ObjectProperty, create URI individuals:
  ```python
  TTYPE = Namespace("http://comparativemythology.local/ontology/myth#TextType_")
  g.add((TTYPE.scripture, RDF.type, MYTH.TextType))
  g.add((text_uri, MYTH.hasTextType, TTYPE.scripture))
  ```
  Requires updating graph_enrich.py to write URIs not Literals.

Option A is the pragmatic choice when the enrichment script is already deployed
and stores strings. Option B is correct if the TextType class is meant to be
queryable via SPARQL class hierarchy.

The seed instances added in July 2026 (mythology, scripture, epic, anthology,
commentary, folklore, ritual, philosophy, lawcode) follow Option B's pattern —
they exist as `myth:TextType_*` individuals even though the property is currently
a DatatypeProperty. This leaves the door open for future migration.

---

## MEDIUM-Severity Issues (OWL-DL anomalies, semantic inconsistency)

### 6. Class inheriting from SKOS.Concept

**Pattern:**
```python
declare_class(MYTH.Concept, ..., parent=SKOS.Concept)
```

In OWL-DL, making a custom class a `rdfs:subClassOf skos:Concept` means every
instance of `myth:Concept` is automatically a `skos:Concept`. This is
semantically odd — SKOS concepts live inside ConceptSchemes; making an OWL class
a subclass of a SKOS metaclass mixes layers and causes warnings in some reasoners.

**Fix:** Remove the parent. Declare a ConceptScheme node and link instances via
`skos:inScheme`:
```python
scheme_uri = URIRef("http://yourns.local/data/concept/MyConceptScheme")
g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
# ... then for each concept:
g.add((uri, SKOS.inScheme, scheme_uri))
```

---

### 7. Object properties storing plain Literals (range violation)

**Pattern:** A property is declared `range_=SomeClass` (OWL class), but the
enrichment script adds a plain `Literal` value — a range violation.

**Examples found:**
- `myth:hasTextType` (range=`myth:TextType`) stored `Literal("scripture")`
- `myth:originalLanguage` (range=`myth:Language`) stored `Literal("Sanskrit")`

**Fix:** See issue #13 above — either migrate to DatatypeProperty (Option A) or
create URI individuals (Option B).

---

### 8. Properties used but never declared

**Pattern:** An enrichment or analysis script writes triples using a property URI
that was never declared in the ontology. The triple is stored fine by rdflib
(it doesn't enforce schema), but the property has no label, domain, range, or
comment — it's invisible to SPARQL introspection queries.

**Properties found undeclared (cumulative list through July 2026):**

First wave (graph_enrich.py):
- `myth:motifEvidence` — evidence text for LLM motif assignment
- `myth:narrativeEpisode` — key story episode in a text
- `myth:hasTheme` — free-text theme annotation
- `myth:textCharacter` — brief characterization of a text's content
- `myth:cognateNote` — scholarly note on a deity cognate pair

Second wave (enrich_graph_analytical.py — July 2026):
- `myth:hasTheme` (685 uses), `myth:motifEvidence` (848), `myth:narrativeEpisode` (416),
  `myth:textCharacter` (112) — already in first wave but confirmed here
- `myth:author` (3), `myth:layer` (3), `myth:year` (3) — secondary source metadata
- `myth:definesCategory` (53), `myth:interpretedAs` (31), `myth:interpretedBy` (31)
- `myth:analysedByFramework` (72), `myth:analyticalConcept` (6)
- `myth:derivedFrom` (9), `myth:frazerAnalysisNote` (6), `myth:ottoAnalysisNote` (6)
- `myth:turnerAnalysisNote` (7), `myth:vanGennepPhaseMapping` (6)
- `myth:hasDumezilFunction` (22), `myth:hasFrazerianStructure` (6)
- `myth:hasLiminalStructure` (7), `myth:hasNuminousCharacter` (10)
- `myth:instantiatesSchema` (6), `myth:mediatesBinaryOpposition` (20)
- `myth:poleA` (5), `myth:poleB` (5), `myth:schemaPhase` (7)
- `myth:relatedDumezilFunction` (3)

**Missing classes (enrich_graph_analytical.py):**
- `myth:AnalyticalFramework`, `myth:StructuralSchema`, `myth:DumezilFunction`,
  `myth:BinaryOpposition`, `myth:SecondarySource`

**Fix:** For every property used in any script that writes to the graph, search
ontology.py for `declare_prop`/`declare_dprop` of that property. If absent, add it.
Run the undeclared-property check script (see Audit Procedure below) before every
schema release.

---

### 9. Duplicate properties with identical domain/range

**Pattern:** Two properties with different names but identical `domain` and
`range_` declarations, where one is never used.

**Example:** `myth:hasFigure` and `myth:featuresFigure` both had
`domain=ReligiousText, range=MythologicalFigure`. Only `hasFigure` was used.

**Fix:** Remove the unused duplicate. Leave a comment:
```python
# NOTE: myth:featuresFigure removed — duplicate of myth:hasFigure (same domain/range).
# Use myth:hasFigure for ReligiousText → MythologicalFigure links.
```

---

### 10. Concept-typed entries in the NarrativeMotif taxonomy

**Pattern:** Theological concepts (karma, dharma, logos, moksha, etc.) placed in
the motif taxonomy and typed as `myth:NarrativeMotif` — wrong class.

These are NOT narrative motifs in Thompson's framework (which is about story
patterns, not theological doctrines). Adding them as `NarrativeMotif` pollutes
the motif namespace with conceptual entities.

**Fix:**
1. Add a `CONCEPT_MOTIF_IDS = frozenset({...})` sentinel in `motif_taxonomy.py`
2. In `add_expanded_motifs()`, check this set:
   ```python
   if motif_id in CONCEPT_MOTIF_IDS:
       g.add((uri, RDF.type, MYTH.Concept))
   else:
       g.add((uri, RDF.type, MYTH.NarrativeMotif))
   ```
3. Keep the entries in MOTIFS for keyword-matching by the LLM analyzer — just
   type them correctly in the graph.

**IDs that are concepts, not motifs:**
`dualism, logos, karma, dharma, moksha_liberation, monotheism, eschatology,
ahimsa, tao, wu_wei`

---

### 11. Referenced concept not seeded

**Pattern:** `seed_cross_tradition_links()` references a concept ID in an
equivalence pair, but the concept is not in `seed_core_concepts()`. The guard:
```python
if (ua, RDF.type, MYTH.Concept) in g and (ub, RDF.type, MYTH.Concept) in g:
```
…silently drops the link.

**Example:** `("karma", "nemesis")` — `nemesis` was not seeded.

**Fix:** Search `seed_cross_tradition_links()` for all concept IDs referenced in
equivalences. Cross-check each against `seed_core_concepts()`. Add any missing
ones.

---

### 14. Symmetric properties — verify both OWL.SymmetricProperty type AND manual double-assertion

**Pattern:** A property is declared `symmetric=True` in a helper that adds
`OWL.SymmetricProperty`, but SPARQL engines without OWL reasoning won't infer
the reverse direction.

**Canonical pattern:**
```python
declare_prop(MYTH.sameConceptAs, ..., symmetric=True)
# The helper adds: g.add((MYTH.sameConceptAs, RDF.type, OWL.SymmetricProperty))
# BUT for SPARQL without a reasoner, also add both directions explicitly:
g.add((ua, MYTH.sameConceptAs, ub))
g.add((ub, MYTH.sameConceptAs, ua))   # explicit reverse for SPARQL engines
```

**Affected properties in this ontology:** `sameConceptAs`, `parallelTo`,
`cognateOf`, `cognatePlace`, `traditionsShare`.

---

## Audit Procedure

Run this before any schema release or `graph_enrich.py` full rebuild:

```bash
# 1. Syntax check all three core scripts
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['ontology.py', 'graph_enrich.py', 'motif_taxonomy.py']]"

# 2. Check for A0/E0 Thompson code overuse (expect 0 or very few)
grep -c '"thompson": "A0"' motif_taxonomy.py   # should be 0 after audit

# 3. Check for undeclared properties (run ontology, check against grep of enrichment scripts)
python3 -c "
import re
onto = open('ontology.py').read()
enrich = open('graph_enrich.py').read()
# Find all MYTH.xxx used in enrich but not declared in onto
props = set(re.findall(r'MYTH\.(\w+)', enrich))
decl  = set(re.findall(r'MYTH\.(\w+)', onto))
undeclared = props - decl
print('Potentially undeclared:', sorted(undeclared))
"

# 4. Verify hasTextType and originalLanguage are DatatypeProperty (not ObjectProperty)
python3 -c "
from rdflib import Graph, Namespace, RDF, OWL
g = Graph(); g.parse('../ontology/myth_ontology.ttl')
MYTH = Namespace('http://comparativemythology.local/ontology/myth#')
for p in ['hasTextType', 'originalLanguage']:
    is_dp = (MYTH[p], RDF.type, OWL.DatatypeProperty) in g
    is_op = (MYTH[p], RDF.type, OWL.ObjectProperty) in g
    print(f'{p}: DatatypeProperty={is_dp}, ObjectProperty={is_op}')
"

# 5. Verify CONCEPT_MOTIF_IDS entries exist in concepts (not motifs) after build
# (run after graph_enrich.py)
python3 -c "
from rdflib import Graph, Namespace, RDF
g = Graph(); g.parse('../ontology/myth_knowledge_graph.ttl')
MYTH = Namespace('http://comparativemythology.local/ontology/myth#')
MOTIF = Namespace('http://comparativemythology.local/data/motif/')
for cid in ['karma','dharma','logos','tao','ahimsa','moksha_liberation']:
    is_concept = (MOTIF[cid], RDF.type, MYTH.Concept) in g
    is_motif   = (MOTIF[cid], RDF.type, MYTH.NarrativeMotif) in g
    print(f'{cid}: concept={is_concept} motif={is_motif}')
"

# 6. Verify all 5 analytical classes are declared
python3 -c "
from rdflib import Graph, Namespace, RDF, OWL
g = Graph(); g.parse('../ontology/myth_ontology.ttl')
MYTH = Namespace('http://comparativemythology.local/ontology/myth#')
for cls in ['AnalyticalFramework','StructuralSchema','DumezilFunction','BinaryOpposition','SecondarySource']:
    print(f'{cls}: {(MYTH[cls], RDF.type, OWL.Class) in g}')
"
```

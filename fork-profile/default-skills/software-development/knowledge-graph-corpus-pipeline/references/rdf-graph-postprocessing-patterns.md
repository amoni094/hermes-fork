# RDF Knowledge Graph Post-Processing Patterns

Patterns for correcting and enriching a Turtle RDF graph after the main build
pipeline. All examples assume rdflib 7.x and Python 3.11+.

---

## 1. Symmetrizing OWL symmetric properties

OWL reasoners infer symmetric property reverses, but rdflib SPARQL does not run a
reasoner. Add both directions explicitly.

**Critical**: collect the full set FIRST, then add. Do NOT add while iterating the
live graph — newly added triples become visible in the same iterator on some rdflib
versions and cause double-counting. With 7 asymmetric pairs you end up adding 14
triples (both halves of each missing pair), which is correct:

```python
sameAs = MYTH.sameConceptAs
pairs = {(s, o) for s, p, o in g.triples((None, sameAs, None))}
added = 0
for (a, b) in list(pairs):
    if (b, sameAs, a) not in pairs:
        g.add((b, sameAs, a))
        added += 1
print(f"Added {added} reverse sameConceptAs triples")
```

---

## 2. Adding derived numeric properties from date label strings

The `myth:approximateDateLabel` property stores human-readable strings.
`myth:approximateDateCE` (`xsd:integer`) stores the parsed year (negative = BCE).

### Pattern

```python
from rdflib import Literal, XSD
import re

approxLabel = MYTH.approximateDateLabel
approxCE    = MYTH.approximateDateCE

for text_node in g.subjects(RDF.type, MYTH.ReligiousText):
    for label_val in g.objects(text_node, approxLabel):
        year = parse_date_label(str(label_val))
        if year is not None:
            g.remove((text_node, approxCE, None))   # idempotent: clear old value
            g.add((text_node, approxCE, Literal(year, datatype=XSD.integer)))
```

### Date label regex parser

Handles all formats found in the mythology corpus (verified July 2026):

```python
def parse_date_label(label: str):
    """
    Parse archaeological/historical date label to approximate year CE (int).
    Negative = BCE. Returns None on failure (skips 'varies', 'ancient oral tradition').

    Formats handled:
      "3000-500 BCE"          -> -1750  (midpoint, both BCE)
      "300 BCE - 400 CE"      -> 50     (midpoint, mixed era)
      "1258-1273 CE"          -> 1265   (midpoint, both CE)
      "29-19 BCE"             -> -24    (midpoint, both BCE)
      "c. 500 BCE"            -> -500
      "8 CE"                  -> 8
      "700-900 CE"            -> 800
      "600s-800s CE"          -> 700    (decade ranges)
      "1st century CE"        -> 50
      "13th-10th century BCE" -> -1100  (century range)
      "700-1000 CE (oral older)" -> 850 (parenthetical stripped)
    """
    s = label.strip()
    s = re.sub(r'\(.*?\)', '', s).strip()   # remove parenthetical notes

    def century_to_year(n):
        return (n - 1) * 100 + 50

    # Century range with era: "13th-10th century BCE"
    m = re.match(
        r'(\d+)(?:st|nd|rd|th)[–\-](\d+)(?:st|nd|rd|th)\s+century\s+(BCE|CE|BC|AD)',
        s, re.IGNORECASE)
    if m:
        c1, c2, era = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        mid = (century_to_year(c1) + century_to_year(c2)) // 2
        return -mid if era in ('BCE', 'BC') else mid

    # Single century with era: "1st century CE"
    m = re.match(r'(\d+)(?:st|nd|rd|th)\s+century\s+(BCE|CE|BC|AD)', s, re.IGNORECASE)
    if m:
        c, era = int(m.group(1)), m.group(2).upper()
        y = century_to_year(c)
        return -y if era in ('BCE', 'BC') else y

    # Decade ranges: "600s-800s CE"
    m = re.match(r'(\d+)s[–\-](\d+)s\s+(BCE|CE|BC|AD)', s, re.IGNORECASE)
    if m:
        y1, y2, era = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        mid = (y1 + y2) // 2
        return -mid if era in ('BCE', 'BC') else mid

    # Year range same era: "3000-500 BCE"
    m = re.match(r'(\d+)[–\-](\d+)\s+(BCE|CE|BC|AD)', s, re.IGNORECASE)
    if m:
        y1, y2, era = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        mid = (y1 + y2) // 2
        return -mid if era in ('BCE', 'BC') else mid

    # Mixed era range: "300 BCE - 400 CE"
    m = re.match(
        r'(\d+)\s*(BCE|CE|BC|AD)[–\-\s]+(\d+)\s*(BCE|CE|BC|AD)',
        s, re.IGNORECASE)
    if m:
        y1, e1 = int(m.group(1)), m.group(2).upper()
        y2, e2 = int(m.group(3)), m.group(4).upper()
        v1 = -y1 if e1 in ('BCE', 'BC') else y1
        v2 = -y2 if e2 in ('BCE', 'BC') else y2
        return (v1 + v2) // 2

    # Single year (optionally preceded by "c."): "c. 500 BCE", "8 CE", "1220 CE"
    m = re.match(r'c\.?\s*(\d+)\s*(BCE|CE|BC|AD)', s, re.IGNORECASE)
    if not m:
        m = re.match(r'(\d+)\s*(BCE|CE|BC|AD)', s, re.IGNORECASE)
    if m:
        y, era = int(m.group(1)), m.group(2).upper()
        return -y if era in ('BCE', 'BC') else y

    # Bare range without explicit era (assume CE if plausible): "1258-1273"
    m = re.match(r'(\d+)[–\-](\d+)', s)
    if m:
        y1, y2 = int(m.group(1)), int(m.group(2))
        rest = s[m.end():].strip()
        era_m = re.match(r'(BCE|CE|BC|AD)', rest, re.IGNORECASE)
        if era_m:
            era = era_m.group(1).upper()
            mid = (y1 + y2) // 2
            return -mid if era in ('BCE', 'BC') else mid
        if y1 > 0:
            return (y1 + y2) // 2

    return None   # unparseable: 'varies', 'ancient oral tradition', etc.
```

### Known-skipped labels (July 2026 corpus, 116 texts)

These 20 entries return `None` and are intentionally skipped:
`"varies"` (×14), `"ancient oral tradition"` (×3), `"various ancient"` (×1),
`"varies (pre-Columbian)"` (×1), `"various"` (×1)

---

## 3. Removing CIDOC-CRM / SKOS / OWL orphan import stubs

When myth: classes subclass external standards (CIDOC-CRM, SKOS, OWL), rdflib loads
the external URIs as dangling objects in the graph but does not dereference them.
The OWL sub-class triples remain as the only reference.

To remove them cleanly:

```python
from rdflib.namespace import SKOS, OWL, XSD

# Exact URI set — never use suffix matching (see pitfall below)
CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")

orphan_uris = [
    CIDOC.E53_Place,
    CIDOC.E5_Event,
    CIDOC.E73_Information_Object,
    CIDOC.E74_Group,
    SKOS.ConceptScheme,
    XSD.boolean,
    SKOS.Concept,         # only if it's truly external — check not myth:Concept first
    # OWL.Ontology is the graph-level declaration; removing it removes the ontology header
]

removed = 0
for uri in orphan_uris:
    triples = list(g.triples((uri, None, None))) + list(g.triples((None, None, uri)))
    for t in triples:
        g.remove(t)
    removed += len(triples)
print(f"Removed {removed} orphan triples")
```

**CAUTION — the Concept namespace check:**
Before removing any node whose local name is "Concept", verify its full URI:
```python
myth_concept = MYTH.Concept   # the one to KEEP
skos_concept = SKOS.Concept   # a candidate to remove

# Only remove if they are different URIs
if str(skos_concept) != str(myth_concept):
    for t in list(g.triples((skos_concept, None, None))) + list(g.triples((None, None, skos_concept))):
        g.remove(t)
```

### ⚠️ Pitfall: string-suffix URI matching silently deletes predicates

NEVER use `str(node).endswith('Concept')` to find "Concept" nodes. In the mythology
corpus `myth:sharesConcept` is an ObjectProperty whose URI ends in "Concept". Using
a suffix check found it as a "node" and deleted its 5 ontology definition triples,
silently breaking the property schema.

```python
# DANGEROUS — catches predicates, not just nodes
for s, p, o in g:
    for node in (s, o):
        if str(node).endswith('Concept'):    # <-- DO NOT DO THIS
            ...

# SAFE — exact URI equality
for s, p, o in g:
    for node in (s, o):
        if node == SKOS.Concept:             # exact match only
            ...
```

For namespace-level filtering use prefix: `str(node).startswith("http://www.cidoc-crm.org/")`.

---

## 4. Verifying DataProperty vs ObjectProperty consistency

After any schema change where a property type is migrated:

```python
# Check that hasTextType and originalLanguage store only Literals (not URIRefs)
from rdflib import URIRef

for pred in (MYTH.hasTextType, MYTH.originalLanguage):
    violations = [(s, p, o) for s, p, o in g.triples((None, pred, None))
                  if isinstance(o, URIRef)]
    if violations:
        print(f"⚠ {pred}: {len(violations)} URIRef values — ontology.py needs DatatypeProperty fix")
    else:
        print(f"✓ {pred}: all values are Literals")
```

---

## 5. Idempotency pattern for post-processing scripts

Always make correction scripts safe to re-run:

```python
# Backup first
import shutil
shutil.copy2(TTL_PATH, TTL_PATH + ".bak")

# Load
g = Graph()
g.parse(TTL_PATH, format="turtle")

# --- apply corrections (each idempotent) ---

# For additive: check existence before adding
if (b, sameAs, a) not in g:
    g.add((b, sameAs, a))

# For replace: remove-then-add
g.remove((text_node, approxCE, None))           # clears any prior value
g.add((text_node, approxCE, Literal(year, datatype=XSD.integer)))

# Save
g.serialize(destination=TTL_PATH, format="turtle")
```

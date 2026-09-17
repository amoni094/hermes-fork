# Secondary Literature Embedding Quality Audit — July 2026

ChromaDB collection: `secondary_literature` — 24,298 chunks total.
Conducted: July 2026. Trigger: semantic queries returning JS/HTML boilerplate.

---

## Source Status Table

| Source | Size | Status | Words (recoverable) | Notes |
|--------|------|--------|---------------------|-------|
| **LAYER 2 — Traditional Commentary** | | | | |
| genesis_rabbah_en.txt | 0.39MB | ✅ OK | 67,699 | Clean plain text |
| exodus_rabbah_en.txt | 0.54MB | ✅ OK | 96,635 | Clean plain text |
| leviticus_rabbah_en.txt | 0.48MB | ✅ OK | 83,707 | Clean plain text |
| numbers_rabbah_en.txt | 1.62MB | ✅ OK | 285,787 | Clean plain text |
| ibn_kathir_en.txt | 2.05MB | ✅ OK | 284,199 | quran.com API output — clean |
| shankara_brahmasutra_en.txt | 0.24MB | ❌ STUB | ~1,200 | Internet Archive landing page, not text |
| augustine_city_of_god.txt | 244B | ❌ STUB | ~30 | Page header only |
| clement_stromata.txt | 231B | ❌ STUB | ~30 | Page header only |
| origen_against_celsus.txt | 237B | ❌ STUB | ~30 | Page header only |
| **LAYER 3 — Analytical Frameworks** | | | | |
| jung_psychology_unconscious_1916.txt | 1.11MB | ✅ OK | 182,754 | Clean text |
| jung_collected_papers_1916.txt | 1.09MB | ✅ OK | 176,640 | Clean text |
| jung_man_and_his_symbols.txt | 0.80MB | ✅ OK | 126,297 | User-provided PDF, extracted |
| jung_archetypes_cw9i.txt | 1.17MB | ❌ HTML | 166,104 | Internet Archive page — JS/HTML junk |
| jung_aion_cw9ii.txt | 1.07MB | ❌ HTML | 132,841 | Internet Archive page — JS/HTML junk |
| jung_portable_anthology.txt | 1.58MB | ❌ HTML | 239,375 | Internet Archive page — JS/HTML junk |
| eliade_forge_and_crucible.txt | 0.47MB | ✅ OK | 72,919 | Clean text |
| eliade_sacred_and_profane.txt | 0.46MB | ❌ HTML | 51,356 | Internet Archive page — JS/HTML junk |
| eliade_images_and_symbols.txt | 0.53MB | ❌ HTML | 63,771 | Internet Archive page — JS/HTML junk |
| eliade_myth_and_reality.txt | 0.53MB | ❌ HTML | 62,575 | Internet Archive page — JS/HTML junk |
| campbell_masks_primitive.txt | 1.27MB | ❌ HTML | 193,638 | Internet Archive page — JS/HTML junk |
| neumann_great_mother.txt | 0.88MB | ✅ OK | 134,523 | User-provided PDF, extracted |
| aras_book_of_symbols.txt | 1.64MB | ✅ OK | 237,444 | User-provided PDF, extracted |

**Summary:**
- Clean/OK: 11 sources
- HTML junk (Internet Archive): 7 sources — ~909K words of content embedded as boilerplate
- Stub: 5 sources (3 Church Fathers + Shankara)

---

## Impact: What's Currently Missing from Semantic Search

The 7 HTML-junk sources are the most important analytical framework texts:
- **Jung CW9i** (Archetypes and the Collective Unconscious) — core archetype typology
- **Jung CW9ii** (Aion) — Self, Shadow, Christ as Self-archetype, Gnostic symbols
- **Jung Portable Anthology** — broad survey of individuation stages
- **Eliade Sacred and Profane** — hierophany, axis mundi, sacred time definitions
- **Eliade Images and Symbols** — symbolism across traditions
- **Eliade Myth and Reality** — cosmogony, eternal return, illo tempore
- **Campbell Masks of God Vol.1** — monomyth, hero journey, primitive mythology

Shankara's Brahmasutra Bhashya is entirely absent — the Advaita Vedanta tradition has
no commentary-layer representation. The three Church Fathers (Augustine, Clement,
Origen) are also absent — no patristic commentary layer.

---

## HTML Strip Recipe

For Internet Archive `.txt` files that are actually HTML:

```python
import re

def strip_ia_html(html: str) -> str:
    """Strip Internet Archive HTML wrapper to recover embedded text content."""
    # Remove script and style blocks entirely
    t = re.sub(r'<script[^<]*</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    t = re.sub(r'<style[^<]*</style>', '', t, flags=re.DOTALL|re.IGNORECASE)
    # Remove all remaining HTML tags
    t = re.sub(r'<[^>]+>', ' ', t)
    # Decode common HTML entities
    t = t.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    t = re.sub(r'&[a-z]+;', ' ', t)
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t
```

After stripping, check word count: `len(text.split())`.
- < 5,000 words → still a stub, text not in the page, source elsewhere
- > 10,000 words → likely real content, verify with a snippet check

The `jung_archetypes_cw9i.txt` recovers ~166K words — substantial real content.
The `shankara_brahmasutra_en.txt` only recovers ~1,200 words — still a stub.

---

## Re-Embed Procedure (Per Source)

1. Strip HTML or source real text → write to clean `.txt`
2. Delete existing chunks from collection:
   ```python
   import chromadb
   client = chromadb.PersistentClient(path='/var/home/rainbow/Religion/chroma_db')
   coll = client.get_collection('secondary_literature')
   # Get IDs for this source
   result = coll.get(limit=10000, include=['metadatas'])
   ids_to_delete = [
       result['ids'][i]
       for i, m in enumerate(result['metadatas'])
       if m.get('source_id', '').endswith('jung_archetypes_cw9i.txt')
   ]
   if ids_to_delete:
       coll.delete(ids=ids_to_delete)
       print(f"Deleted {len(ids_to_delete)} chunks")
   ```
3. Re-run the secondary literature vectorizer for that source only

---

## Missing Metadata: analytical_categories

Every `.meta.json` file lists `analytical_categories` (the key concepts the book
introduces), but these are NOT stored in chunk metadata. Current fields per chunk:
- `source_id`, `author`, `label`, `layer`, `type`, `tradition`, `is_secondary_literature`, `chunk_index`

Missing:
- `analytical_categories: list[str]` — e.g. `["Hierophany", "AxisMundi", "SacredTime"]`
- `analytical_framework: str` — e.g. `"eliade"`, `"jung"`, `"dumezil"`

Without these, you cannot filter the collection by framework concept — only by author.
This requires re-embedding to add to existing chunks (ChromaDB metadata is immutable
per chunk; you'd need to delete and re-add with the new field).

---

## Disconnected Layer 4 Schema Files

Located at: `~/Religion/secondary_lit/layer4_modern_scholarship/analytical_schemas/`

| File | Type | Contents | Status |
|------|------|----------|--------|
| `eliade_schema.ttl` | OWL/Turtle | Hierophany, AxisMundi, IlloTempore, EternalReturn, etc. as OWL classes | Not loaded into RDF graph |
| `jung_schema.json` | JSON | Archetype typology, individuation stages, cross-tradition links | Not embedded or loaded |
| `dumezil_trifunctional_schema.json` | JSON | F1/F2/F3 functions, IE tradition mappings, analytical edges | Not embedded or loaded |

To make these queryable, add to `graph_enrich.py`:
```python
def load_eliade_schema(g: Graph):
    """Parse and merge eliade_schema.ttl into the main graph."""
    schema_path = SECONDARY_LIT_DIR / "layer4_modern_scholarship/analytical_schemas/eliade_schema.ttl"
    g.parse(str(schema_path), format="turtle")

def load_dumezil_schema(g: Graph):
    """Add Dumézil trifunctional nodes from JSON schema."""
    import json
    schema = json.loads((SECONDARY_LIT_DIR / "layer4_modern_scholarship/analytical_schemas/dumezil_trifunctional_schema.json").read_text())
    DUMEZIL = Namespace("http://comparativemythology.local/dumezil/")
    for fn_id, fn_data in schema["functions"].items():
        uri = DUMEZIL[fn_id]
        g.add((uri, RDF.type, DUMEZIL.TriFunction))
        g.add((uri, RDFS.label, Literal(fn_data["label"], lang="en")))
```

Also note: **`CoincidenriaOppositorum` typo** in `eliade_schema.ttl` — should be
`CoincidentiaOppositorum` (missing `ti`). Fix before loading into the graph or
SPARQL queries against that class will silently return nothing.

---

## Replacement Sources for Stubs

### Shankara Brahmasutra Bhashya (English)
- WisdomLib: `wisdomlib.org/hinduism/book/brahma-sutras` — full HTML, scrapeable
- Archive.org: search "Brahma Sutra Bhasya Gambhirananda" for a clean PDF version
- The Apte 1960 edition (what was attempted) is scanned only — no OCR text on archive.org

### Augustine City of God (English)
- CCEL: `ccel.org/ccel/augustine/city_of_god.html` — Marcus Dods translation, full text
- Gutenberg: `gutenberg.org/ebooks/45304` (HTML with chapter navigation)

### Clement Stromata (English)
- CCEL: `ccel.org/ccel/clement/stromata.html` — ANF vol.2 translation
- Archive.org ANF02 has the full text — but the HTML page we captured is a login wall

### Origen Against Celsus (English)
- CCEL: `ccel.org/ccel/origen/celsus.html` — ANF vol.4 translation
- Same issue as Clement — IA page was a landing page, not the text

For all Church Fathers: prefer CCEL (Christian Classics Ethereal Library) over
Internet Archive — CCEL provides clean, scrapeable HTML with stable URLs.

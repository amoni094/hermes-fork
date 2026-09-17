# Secondary Literature Re-ingest Procedure

Complete workflow for auditing, repairing, and rebuilding the `secondary_literature`
ChromaDB collection when sources are HTML junk, stubs, or missing metadata.
Developed and verified July 2026.

---

## 1. Audit existing collection

```python
import chromadb, re
from pathlib import Path

client = chromadb.PersistentClient(path="/var/home/rainbow/Religion/chroma_db")
coll = client.get_collection("secondary_literature")
print(f"Total chunks: {coll.count()}")

# Spot-check documents for HTML junk
result = coll.get(limit=3, include=["metadatas", "documents"], where={"author": "C.G. Jung"})
for doc in result["documents"]:
    print(doc[:120])   # "<!DOCTYPE html" = junk; real text = OK

# Check .txt files on disk
SECLIT = Path("~/Religion/secondary_lit").expanduser()
for p in sorted(SECLIT.rglob("*.txt")):
    size = p.stat().st_size
    is_html = b"DOCTYPE html" in p.read_bytes()[:200] or b"<html" in p.read_bytes()[:200]
    wc = len(p.read_text(errors="replace").split())
    print(f"{'HTML' if is_html else 'STUB' if size < 500 else 'OK  '} {size/1e6:.2f}MB {wc:,}w  {p.name}")
```

---

## 2. Strip HTML from Internet Archive junk files

Internet Archive "Full text of ..." pages save as `.txt` but contain full HTML.
Strip scripts/styles/nav, decode entities, then verify word count.

```python
import re

def extract_ia_text(html: str) -> str:
    # Try <pre> block first (djvu.txt view pattern)
    pre = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL | re.IGNORECASE)
    if pre:
        text = re.sub(r'<[^>]+>', '', pre.group(1))
        return clean(text)
    # Full-page strip fallback
    for tag in ['script', 'style', 'nav', 'header', 'footer']:
        html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?p[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', ' ', html)
    return clean(decode_entities(html))

def decode_entities(t):
    for esc, ch in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' '),
                    ('&mdash;','—'),('&ndash;','–'),('&ldquo;','"'),('&rdquo;','"')]:
        t = t.replace(esc, ch)
    t = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), t)
    return re.sub(r'&[a-zA-Z]+;', '', t)

def clean(t):
    t = re.sub(r'[ \t]+', ' ', t)
    return re.sub(r'\n{4,}', '\n\n\n', t).strip()
```

After stripping, write the cleaned text back to the `.txt` file.
Verify: `len(text.split()) > 10_000` for a full scholarly monograph.

---

## 3. Source real text for stubs

### Church Fathers (Gutenberg plain text)
- Augustine City of God: `gutenberg.org/cache/epub/45304/pg45304.txt` (Vol I) + `45305` (Vol II)
- Origen Writings: `gutenberg.org/cache/epub/70561/pg70561.txt` (Vol 1) + `70693` (Vol 2)
- Clement Stromata: New Advent HTML, 7 books — `newadvent.org/fathers/0210{1-7}.htm`
  Strip with `strip_html_newadvent()` (remove nav/sidebar, convert p/h tags to newlines)

### Shankara Brahmasutra
- archive.org djvu.txt stream (not the IA HTML page):
  `archive.org/stream/BrahmaSutraSankaraBhashyaEnglishTranslationVasudeoMahadeoApte1960/...djvu.txt`
  The djvu.txt URL returns raw OCR text with backslash line-continuation artifacts.
  Fix: `re.sub(r'\\\s*\n', ' ', text)` to join broken lines.
  Yields ~370K words — verify before using.

### Strip Project Gutenberg boilerplate
```python
def strip_pg(text):
    m = re.search(r'\*{3}\s*START OF.*?\n', text, re.IGNORECASE)
    if m: text = text[m.end():]
    m = re.search(r'\*{3}\s*END OF.*?\n', text, re.IGNORECASE)
    if m: text = text[:m.start()]
    return text.strip()
```

---

## 4. Fix chunk_text for dense-paragraph sources

Midrash, Tafsir, and commentary texts often have only 21 paragraphs over 285K words.
A naive `\n\n`-splitter produces ~21 oversized chunks that exceed the OpenAI 8192-token
embed limit and are semantically too coarse.

Add sentence-boundary splitting within any paragraph > 2× CHUNK_SIZE (1000 words):

```python
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    fine_paras = []
    for para in paragraphs:
        if len(para.split()) <= CHUNK_SIZE * 2:
            fine_paras.append(para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\u201C\u2018])', para)
            cur = []
            for sent in sentences:
                sw = sent.split()
                if len(cur) + len(sw) > CHUNK_SIZE and cur:
                    fine_paras.append(" ".join(cur))
                    cur = cur[-CHUNK_OVERLAP:]
                cur.extend(sw)
            if cur:
                fine_paras.append(" ".join(cur))
    # Assemble fine paras into overlapping chunks
    chunks, cur, cur_len = [], [], 0
    for para in fine_paras:
        pw = para.split()
        if cur_len + len(pw) > CHUNK_SIZE and cur:
            chunks.append(" ".join(cur))
            cur = cur[-CHUNK_OVERLAP:]; cur_len = len(cur)
        cur.extend(pw); cur_len += len(pw)
    if cur: chunks.append(" ".join(cur))
    return chunks
```

Expected ratios: genesis_rabbah 67K words → 163 chunks (not 21).

---

## 5. Add analytical_categories + motif/archetype bridge to metadata

Each `.meta.json` companion file should list `analytical_categories`. Add these to
chunk metadata at ingest time so the collection is filterable by analytical concept.

```python
# CATEGORY_TO_MOTIF_IDS maps analytical category labels to ontology MOTIF namespace IDs
CATEGORY_TO_MOTIF_IDS = {
    "AxisMundi":         ["world_tree", "cosmic_mountain"],
    "IlloTempore":       ["creation_myth"],
    "EternalReturn":     ["creation_myth"],
    "Hero":              ["hero_journey"],
    "Trickster":         ["trickster"],
    "GreatMother":       ["great_mother"],
    "Mandala":           ["mandala_cosmogram"],
    "Coniunctio":        ["sacred_marriage"],
    "Uroboros":          ["world_serpent"],
    "HeroJourney":       ["hero_journey"],
    "Initiation":        ["initiation"],
    # ... see reingest_secondary.py for full table
}
# ChromaDB only accepts str/int/float/bool — join lists as comma-str
cats_str   = ",".join(meta.get("analytical_categories", []))
motif_ids  = list(dict.fromkeys(m for c in cats for m in CATEGORY_TO_MOTIF_IDS.get(c, [])))
```

---

## 6. Resolve ChromaDB embedding function conflict

If the collection was originally created with `DefaultEmbeddingFunction` and you
now want to use `OpenAIEmbeddingFunction`, ChromaDB raises:
`ValueError: embedding function conflict: new: openai vs persisted: default`

**Introspect the stored EF** without triggering the error (use no EF arg on get):
```python
coll = client.get_collection("secondary_literature")
stored_ef  = coll._model.configuration_json["embedding_function"]["name"]
stored_dim = coll._model.dimension   # 1536 = OpenAI, 384 = sentence-transformers default
print(f"EF: {stored_ef}, dim: {stored_dim}")
```
If `name='default'` but `dimension=1536`, the collection was created with
DefaultEmbeddingFunction but OpenAI vectors were written manually — EF config
is stale. Safe to delete-and-recreate.

**Full rebuild (all sources):** delete the old collection first:
```python
try: client.delete_collection("secondary_literature")
except Exception: pass
collection = client.get_or_create_collection(
    name="secondary_literature",
    embedding_function=embed_fn,
    metadata={"hnsw:space": "cosine"},
)
```

**Partial rebuild (--source flag):** catch ValueError and use stored EF:
```python
try:
    collection = client.get_or_create_collection(name="secondary_literature", embedding_function=embed_fn, ...)
except ValueError:
    collection = client.get_collection("secondary_literature")
```

---

## 7. Run reingest_secondary.py

The script at `~/Religion/scripts/reingest_secondary.py` implements all of the above:
- Detects HTML junk and strips it
- Loads `.meta.json` for `analytical_categories`, `motif_ids`, `archetype_ids`
- Applies the sentence-splitting chunker
- Deletes stale chunks by `source_id` before re-adding (safe upsert)
- Handles the EF conflict with delete-and-recreate on full rebuild

```bash
cd ~/Religion

# Full rebuild (deletes old collection, re-embeds everything):
python3 scripts/reingest_secondary.py

# Dry run (count chunks, no writes):
python3 scripts/reingest_secondary.py --dry-run

# Partial rebuild (one source only):
python3 scripts/reingest_secondary.py --source jung_aion
```

Expected result after full rebuild: ~10,348 chunks across 22 sources, all real content.

---

## 8. Load analytical schemas into graph_enrich.py

Add `add_analytical_schemas(g)` to `graph_enrich.py` and call it in `main()`
after `add_traditions_share_motifs(g)` and before `add_llm_motif_analysis(g)`:

```python
SECLIT_SCHEMA_DIR = BASE_DIR / "secondary_lit" / "layer4_modern_scholarship" / "analytical_schemas"
ELIADE  = Namespace("http://comparativemythology.org/eliade/")
JUNG    = Namespace("http://comparativemythology.org/jung/")
DUMEZIL = Namespace("http://comparativemythology.org/dumezil/")
REL     = Namespace("http://comparativemythology.org/relation/")

def add_analytical_schemas(g: Graph):
    g.bind("eliade", ELIADE); g.bind("jung", JUNG)
    g.bind("dumezil", DUMEZIL); g.bind("rel", REL)

    # 1. Eliade OWL TTL — parse directly (9 OWL classes)
    g.parse(str(SECLIT_SCHEMA_DIR / "eliade_schema.ttl"), format="turtle")

    # 2. Jung JSON — add OWL class individuals (14 archetypes, 6 processes, 7 symbols)
    schema = json.loads((SECLIT_SCHEMA_DIR / "jung_schema.json").read_text())
    JUNG_ARCH = JUNG["Archetype"]
    g.add((JUNG_ARCH, RDF.type, OWL.Class))
    for name, defn in schema.get("psychic_structures", {}).items():
        g.add((JUNG[name], RDF.type, JUNG_ARCH))
        g.add((JUNG[name], RDFS.label, Literal(name, lang="en")))
        g.add((JUNG[name], RDFS.comment, Literal(defn, lang="en")))
    # ... processes (jung:IndividuationProcess), symbols (jung:JungianSymbol) similarly

    # 3. Dumézil JSON — add F1/F2/F3 individuals + deity links (3 trifunctions)
    schema = json.loads((SECLIT_SCHEMA_DIR / "dumezil_trifunctional_schema.json").read_text())
    DUMP_FUNC = DUMEZIL["TriFunction"]
    g.add((DUMP_FUNC, RDF.type, OWL.Class))
    for fn_key, fn_data in schema.get("functions", {}).items():
        g.add((DUMEZIL[fn_key], RDF.type, DUMP_FUNC))
        g.add((DUMEZIL[fn_key], RDFS.label, Literal(fn_data["label"], lang="en")))
    # Seed known deity→function links (guard: only if deity node exists in graph)
    FILLS = REL["fillsFunction"]
    for deity_id, fn_key in [("zeus","F1_sovereignty"), ("odin","F1_sovereignty"),
                               ("thor","F2_military"), ("indra","F2_military"),
                               ("hermes","F3_fertility"), ("freyr","F3_fertility")]:
        if (DEITY[deity_id], RDF.type, MYTH.Deity) in g:
            g.add((DEITY[deity_id], FILLS, DUMEZIL[fn_key]))
```

The Eliade TTL typo `CoincidenriaOppositorum` must be corrected to
`CoincidentiaOppositorum` before parsing (already fixed in the schema file).

Verified output: 213 triples from schemas alone, 9 Eliade OWL classes,
14 Jung archetypes, 3 Dumézil trifunctions, 10 REL object properties.

---

## 9. Verify

```python
import chromadb
client = chromadb.PersistentClient(path="/var/home/rainbow/Religion/chroma_db")
coll = client.get_collection("secondary_literature")
print(f"Total: {coll.count()}")  # expect ~10,348

# Check one Jung document is real text
r = coll.get(limit=1, include=["documents"], where={"author": "C.G. Jung"})
assert "<!DOCTYPE" not in r["documents"][0], "Still HTML junk!"
print("Jung content:", r["documents"][0][:100])

# Check analytical_categories populated
r = coll.get(limit=100, include=["metadatas"])
has_cats = sum(1 for m in r["metadatas"] if m.get("analytical_categories"))
print(f"{has_cats}/100 chunks have analytical_categories")

# Check all 22 labels present
by_label = {}
for offset in range(0, coll.count(), 2000):
    for m in coll.get(limit=2000, offset=offset, include=["metadatas"])["metadatas"]:
        by_label[m.get("label","?")] = True
print(f"Distinct labels: {len(by_label)}")  # expect 22
```

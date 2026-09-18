---
description: 'Use when: asked to build a knowledge graph over a text corpus. Locally queryable graph: web scraping, OWL/RDF
  ontology (CIDOC-CRM + SKOS), ChromaDB, SPARQL, NetworkX.'
name: knowledge-graph-corpus-pipeline
triggers:
- download corpus and make it queryable
- knowledge graph from texts
- RDF ontology for corpus
- vectorize and graph
- SPARQL query corpus
- comparative mythology knowledge graph construction
- semantic search over downloaded texts
- scraper watchdog
- long-running scraper stalled
- restart background downloader
- ontology audit
- OWL schema consolidation
- fix ontology issues
- domain range violation
- Thompson code
- knowledge graph visualization
- D3.js graph
- Cytoscape.js knowledge graph
- force-directed graph browser
- graph community detection browser
- Louvain clustering JavaScript
- graph color encoding
- progressive disclosure graph
- digital humanities network visualization
- humanities graph schema
- simplify knowledge graph
- graph too dense
- graph has connections everywhere
- two-tier graph
- summary graph
- graph navigation layer
- ontology consolidation
- graph hairball
- hub nodes dominating graph
related_skills:
  - graphiti-mcp-setup
  - domain-research-synthesis
  - grounded-citations
  - knowledge-corpus-architecture
  - computational-text-corpus-analysis
---


# Knowledge Graph Corpus Pipeline

## Topology alert

This skill is a **graph bridge**: it is the only connection between the main skill
graph and `comparative-religion-corpus`. If this skill is pruned or significantly
restructured, the religion KG work becomes a disconnected island with no skill-graph
path back to the shared toolchain (ChromaDB, RDF, vectorization patterns). Both
skills must be maintained in tandem. Before pruning, check:
`grep -r 'knowledge-graph-corpus-pipeline\|comparative-religion-corpus' ~/.hermes/skills -l`

## Related tools assessed (not installed)

**code-graph-rag** (vitali87/code-graph-rag, MIT, 3.3k stars) — Tree-sitter → Memgraph knowledge graph
for *code* corpora (functions, classes, imports, call edges). Assessed 2026-08-10, declined:
- cmake not available on Fedora Silverblue without rpm-ostree layer + reboot
- Requires Memgraph + Qdrant (two new always-on containers) separate from FalkorDB
- No current large-monorepo querying need; Graphiti MCP (FalkorDB) already covers this pattern
- Pre-built tree-sitter Python bindings work without cmake → can reuse the FalkorDB stack directly
Decision record: `~/.hermes/decisions/code-graph-rag-assessment-2026-08-10.md`

**Reusable pattern (no cmake, uses existing FalkorDB):**
1. `uv add tree-sitter tree-sitter-python tree-sitter-javascript` (pre-built wheels, no compile)
2. Parse files → extract functions/classes/imports as typed dicts from the AST
3. Store in FalkorDB (already running) using `group_id=hermes-projects-<repo>`
4. Query via `mcp__graphiti__search_memory_facts` or direct Cypher
Use this for any future project that needs code-structure querying without a new graph DB instance.

## When to load this skill
- Building a locally queryable knowledge base from scraped/downloaded texts
- Designing an OWL ontology backed by a vector store
- Combining RDF (SPARQL) + ChromaDB (semantic search) + NetworkX (graph traversal)
- Comparative analysis tasks (mythology, legal, scientific literature, etc.)

---

## Architecture

Four layers working together:

```
scraper.py          Download corpus (rate-limited, resumable, state-tracked)
ontology.py         OWL/RDF schema (classes, properties, motifs, concepts)
vectorize.py        Chunk texts -> embed -> ChromaDB (OpenAI text-embedding-3-small)
graph_enrich.py     Populate RDF graph from manifest + semantic discovery
query.py            CLI: motif/text/deity/influence/similar/sparql/shell
```

Supporting files: `text_manifest.py` (curated entry list), `build.sh` (pipeline runner).

---

## Ontology Design

Use **CIDOC-CRM** (ISO 21127) as the cultural heritage backbone — it models
events, actors, objects, and time cleanly, and is SPARQL-friendly at OWL-DL level.
Layer **SKOS** for concept hierarchies on top.

| Class | Inherits from | Purpose |
|-------|---------------|---------|
| `myth:ReligiousText` | CIDOC E73 Information Object | A text/document in the corpus |
| Domain entity (e.g. Tradition) | CIDOC E74 Group | Top-level grouping |
| Agent entity (e.g. Deity) | CIDOC E21 Person | Actors in the domain |
| Propositional (e.g. Motif) | CIDOC E89 Propositional Object | Cross-corpus patterns |
| Concept | (OWL class; instances via `skos:inScheme`) | Abstract domain concepts — NOT a subclass of SKOS.Concept |

Namespace pattern:
```python
MYTH  = Namespace("http://comparativemythology.local/ontology/myth#")
TEXT  = Namespace("http://comparativemythology.local/data/text/")
TRAD  = Namespace("http://comparativemythology.local/data/tradition/")
```

Always declare `from pathlib import Path` at the **top of the file**, never
only inside `if __name__ == "__main__"` — rdflib scripts commonly need Path for
`out.parent.mkdir()` and the bare module import block won't see it at runtime.

---

### Scraper Pattern

- Rate-limit: 1.5-3.0s random delay between requests (polite bot headers)
- Persist state to JSON (`download_state.json`) after every entry — safe to interrupt
- `html_to_text()`: strip `<script>/<style>/<img>`, decompose first `<table>` (navigation sidebar on sacred-texts.com), `get_text(separator="\n")`, collapse blank lines
- Save both `.htm` (raw) and `.txt` (cleaned) per page — vectorizer uses `.txt`
- Skip files with < 50 words (navigation pages, stubs)
- **archive.org djvu.txt**: for public-domain books (secondary lit, commentary), the
archive.org djvu.txt endpoint is a reliable plain-text source. CRITICAL: use `/download/`
not `/stream/`. `/stream/` returns an HTML login wall even for fully public domain items.
```bash
# CORRECT — use /download/:
curl -sL "https://archive.org/download/<ITEM_ID>/<FILENAME>_djvu.txt" -o /tmp/raw.txt
wc -c /tmp/raw.txt   # should be hundreds of KB; if < 10KB, URL is wrong or item is borrow-only
# WRONG — /stream/ returns HTML login wall even for public domain:
curl -sL "https://archive.org/stream/<ITEM_ID>/<FILENAME>_djvu.txt"
```
Access-restricted items (borrow-only) return HTTP 401 even on /download/. Check
`Access-restricted-item: true` in the item's details page. Confirmed public-domain
analytical framework texts (all use /download/): Otto `in.ernet.dli.2015.22259` ✅,
van Gennep `theritesofpassage` ✅, Dumézil `bub_gb_DZIeNMgZhRwC` ✅,
Frazer `the-golden-bough-abrdiged` (note typo in item ID is correct) ✅,
Tabari `TheCommentaryOnTheQuranVol.1ByAlTabari` ✅, Visuddhimagga `Visuddhimagga-ThePathOfPurification` ✅.
Borrow-only (HTTP 401): Turner `ritualprocessstr00turn`, Lévi-Strauss `structuralanthro0000levi`.
Fallback for borrow-only: Tristes Tropiques (Lévi-Strauss, `tristestropiques000177mbp`) is public ✅.

---

### Force Layout Tuning - Degree-Scaled Charge
Flat charge gives hub and leaf nodes equal repulsion, crowding hub neighbors. Scale by degree:
```javascript
d3.forceManyBody().strength(n => {
  const base = isSummary ? -180 : -60;
  return base * (1 + Math.log((n._deg || 1) + 1) * 0.4);
}).distanceMax(500)
```
Hub with degree 20 repels ~3x more than leaf with degree 1. Also set alphaDecay = 0.015 (vs D3 default 0.028) for better cluster settling.

## Vectorization Pattern

- Chunk size: ~500 words, ~50-word overlap, prefer paragraph boundaries
- Embedding: OpenAI `text-embedding-3-small` (also used by Hindsight — key already in env)
- ChromaDB collection metadata per chunk: `text_id`, `tradition`, `title`,
  `original_language`, `approx_date`, `text_type`, `source_url`, `chunk_index`, `file`
- Batch upsert in groups of 100; on duplicate ID catch, fall back to `collection.upsert()`
- Persist state in `vectorize_state.json` for resumable runs

Getting the OpenAI key — Hermes does NOT export `OPENAI_API_KEY` to subprocess
environments. Read it directly from `~/.hermes/.env`:
```python
def get_openai_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        env_path = Path("~/.hermes/.env").expanduser()
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip()
                    break
    return key
```
Apply this same pattern to `graph_enrich.py` wherever it reads `OPENAI_API_KEY`.

---

## Graph Enrichment Pattern

Populate the RDF graph in this order:

1. **Text nodes** from the manifest (link to tradition, motifs, concepts)
2. **Domain entity nodes** (deities, figures, places) with explicit cognate/parallel edges
3. **Influence/provenance links** between traditions (directional)
4. **Semantic discovery** via ChromaDB — query with motif descriptions, add
   `containsMotif` edges where cosine similarity > 0.35 threshold

### Entity-Text Label Normalization
Naive key matching between deity names and text file keys achieves only 46/116 matches. Apply normalization:
```python
def normalize(s): return re.sub(r'[^a-z0-9]', '', s.lower())
```
This achieves 116/116 match. When ChromaDB is unavailable, fall back to disk-scan: walk ~/Religion/TRADITION/TITLE/*.txt using word-boundary regex for deity names at 2+ mention threshold. Disk-scan achieves 2-3x higher recall than JSON-only extraction.

Then serialize:
- `myth_knowledge_graph.ttl` (Turtle RDF, SPARQL-queryable)
- `graph.json` (NetworkX node-link JSON for fast in-memory traversal)

---

## Query CLI Pattern

Provide both one-shot and interactive shell modes:

```
query.py motif <keyword>
query.py text <keyword>
query.py parallel <motif>
query.py deity <name>
query.py influence <group>
query.py similar <free text>        # ChromaDB semantic search
query.py sparql <file or inline>
query.py stats
query.py shell                       # interactive REPL
```

SPARQL prefix block (inject before every query):
```sparql
PREFIX myth: <http://comparativemythology.local/ontology/myth#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
-- plus text:, trad:, deity:, motif:, concept:, place:
```

---

## Pitfalls

Full catalogue (33 entries): **references/pitfalls-catalogue-2026.md**

Load: `skill_view(name='knowledge-graph-corpus-pipeline', file_path='references/pitfalls-catalogue-2026.md')`

Top 5 recurring pitfalls (+ 2 additional HIGH-priority pitfalls appended below):

1. **rdflib symmetric properties need manual double-assertion** — collect ALL pairs as frozen set first, then add reverses. Do NOT add while iterating live graph (double-count risk).
2. **Background scraper dies when CLI session closes** — pair long-running scrapers with a watchdog cron (every 10m `pgrep -af scraper.py` → restart). The skip-if-done logic makes restarts safe.
3. **ChromaDB EF conflict** — never pass `embedding_function=` to `get_collection()`, never use `query_texts=` on manually-embedded collections. Use `query_embeddings=` always.
4. **HNSW index corruption from mid-write crash** — `link_lists.bin` can grow to TB scale. Use isolated DB per collection (chromadb 1.5.x cross-collection Rust compaction bug).
5. **sacred-texts.com ~24% dead URLs** — always check `references/sacred-texts-url-repairs-2026.md` before adding new scrapers. Use URL-repair manifest, not raw manifests.
6. **LLM motif analysis JSON failures on ancient text quotes**: Icelandic/Norse/Sanskrit source texts contain apostrophes, em-dashes, and unicode that the LLM embeds verbatim inside JSON string values. Fix: strip markdown fences before parsing AND wrap json.loads() in try/except falling back to regex-extracting the JSON block. Prompt must include "respond with ONLY valid JSON". Set confidence threshold to reject motif assignments with truncated evidence quotes.
7. **Entity label normalization for text-key matching**: Naive key matching between deity names and text file keys achieves only 46/116 matches. Apply normalization before any lookup — see ### Entity-Text Label Normalization section in Graph Enrichment Pattern.


## OntoKG — Intrinsic vs Relational Property Routing (arXiv:2604.02618, Aug 2026) <!-- rationale: prevents flattening all entity properties into episode text; ensures KG edges encode relationships rather than attributes -->

OntoKG (Wikidata, 34M nodes, 61.2M edges, 93.3% category coverage) introduces a declarative schema principle: every entity property is classified before storage as either **intrinsic** or **relational**:

| Type | Meaning | KG representation |
|---|---|---|
| **Intrinsic** | Property belongs to the entity itself — describes it regardless of context | Node property/attribute |
| **Relational** | Property connects this entity to another entity — the value IS another node | Graph edge |

**Why this matters for Graphiti/Hermes:** Graphiti MCP often stores all episode content as text in episode nodes, flattening relational structure into attribute blobs. This prevents graph traversal for cross-entity queries.

**Applied to the religion KG:**
- `myth:Deity` → `rdfs:label "Odin"` → intrinsic (node attribute)
- `myth:Deity` → `myth:hasMotif myth:sacrifice_wisdom` → relational (edge to Motif node)
- `myth:ReligiousText` → `myth:approximateDateCE "-700"` → intrinsic (node attribute)
- `myth:ReligiousText` → `myth:expressesMotif myth:creation_from_void` → relational (edge)

**Applied to Graphiti sessions:**
- Session fact about a file path → intrinsic property of the entity (session/task node attribute)
- Session fact about a relationship between two entities → relational edge
- Violation example: `hindsight_retain("Project X uses library Y")` stores as text when it should be stored as a Graphiti edge `Project_X → [uses] → Library_Y`

**Ontology audit gate:** When adding new RDF properties to the ontology, classify each before writing:
1. Does the value refer to another named entity? → ObjectProperty (edge), relational
2. Is the value a literal (string, number, date)? → DatatypeProperty (attribute), intrinsic

Mixing these produces a graph where traversal cannot find relational connections — the query must do text parsing to recover structure the schema should have encoded.

Reference: arXiv:2604.02618 "OntoKG: Ontology-Oriented Knowledge Graph Construction with Intrinsic-Relational Routing", validated on Jan 2026 Wikidata snapshot, Aug 2026.

## Research Provenance

### ENTLORE — Latent Relation Extraction for KG > RAG (arXiv:2608.10679)
ENTLORE extracts latent (implicit, inferable but not stated) relations from text co-occurrence patterns.
Multi-hop QA benchmark: KG with latent relations +23% over flat RAG baseline; gap largest for
cross-document relation queries where the relation spans multiple source texts.
**Pipeline implication:** When building KG over the religion corpus or any multi-document corpus,
run a latent-relation extraction pass after the standard entity/explicit-relation extraction.
Use Graphiti MCP `add_triplet` for latent relations, tagging them with `source: inferred`
to distinguish from explicitly stated relations. This enables multi-hop queries flat RAG cannot answer.

## Reference Files

- `references/node-annotation-enrichment.md` — TTL annotation extraction (block-splitter
  approach), graph-derived enrichment fields, cognate deduplication pitfall, and browser
  info-pane pattern (home/selected states, clickable connection chips).
- `references/jaccard-similarity-force.md` — Jaccard similarity JSON build script,
  custom D3 force application, 3D graph CDN setup (3d-force-graph + Three.js), and
  key API differences from D3 2D.
- `references/deep-analysis-layer.md` — four-script deep analysis pipeline
  (motif_taxonomy → motif_analyzer → cross_linker → graph_enrich), motif taxonomy
  design (65 motifs, Thompson codes), LLM prompt design, new RDF properties, and
  tradition-vs-text fallback logic.
- `references/two-tier-graph-architecture.md` — detailed design notes for the
  summary/full graph split: edge selection rationale, degree analysis before/after,
  `build_tiered_graph.py` implementation notes, Theme node design, OWL changes,
  D3.js 2D visualizer wiring, 3D visualizer (3d-force-graph + Three.js CDN),
  and **PITFALL 40: summary graph disconnected components** — must-read before
  deploying a simplified graph. Use when revisiting the tier split, debugging
  connectivity, or adding a 3D visualization.
- `references/semantic-proximity-force-layout.md` — **semantic proximity force tuning**:
  exact link-distance/strength values per relation type, degree-scaled charge formula,
  Jaccard similarity force (node_similarity.json) for attracting nodes with shared
  neighbours, 3D graph CDN + API patterns (3d-force-graph + Three.js), and GitHub
  publish checklist for a local KG project. Load when building or tuning a force-directed
  graph visualizer for a knowledge graph.
- `scripts/build_tiered_graph.py` — canonical script to build graph_summary.json and
  graph_full.json from graph.json + myth_knowledge_graph.ttl. Run after any graph rebuild.
  Source: `~/Religion/scripts/build_tiered_graph.py` (lives in the project, not the skill dir).
  Rebuild command: `cd ~/Religion && python3 scripts/build_tiered_graph.py`

- `references/comparative-mythology-pipeline-notes.md` — session notes from
  the initial build (sacred-texts.com corpus, CIDOC-CRM design decisions,
  Thompson Motif Index mapping, deity cognate list, runtime issues log)
- `references/sacred-texts-url-repairs-2026.md` — full table of 28 broken URLs
  found after first scraper run, with working replacements and repair procedure.
  Use as a starting point for any future sacred-texts.com corpus build.
- `references/deep-analysis-design-notes.md` — design notes for the LLM motif
  extraction layer (motif_analyzer.py + cross_linker.py): taxonomy design,
  cost estimates, prompt patterns, and graph_enrich integration order.
- `references/kabbalistic-analysis-cross-traditional.md` — primary-source analysis
  of Kabbalistic Torah exegesis (Sefer Yetzirah + Zohar) and assessment of where
  its methods transfer across traditions (Hinduism/Chandas, Taoism, Gnosticism,
  Buddhism, Norse). Includes corpus query commands and tradition-pairing table.
- `references/native-language-sources.md` — confirmed-working APIs and sources for
  native-script primary texts: Sefaria (Hebrew), quran.com (Arabic), GRETIL mirror
  (Sanskrit/Pali), ctext.org (Classical Chinese), Heimskringla.no (Old Norse).
  Includes `fetch_native_languages.py` usage, output structure, and a table of
  which structural features require native language vs. survive translation.
- `references/owl-rdf-ontology-audit-checklist.md` — systematic checklist of HIGH
  and MEDIUM OWL/RDF schema issues found during the July 2026 schema consolidation
  pass. 11 issue patterns with fixes and verification scripts. Load before any
  schema refactor or full graph rebuild.
- `references/secondary-lit-embedding-audit-2026.md` — per-source embedding quality
  audit of the `secondary_literature` ChromaDB collection (July 2026). Identifies
  which sources are HTML junk (7: Jung Aion/CW9i/anthology, Eliade S&P/I&S/M&R,
  Campbell Masks Vol.1), which are stubs (Shankara, Church Fathers), and which are
  clean. Includes HTML strip recipe, re-embed procedure, and missing metadata gaps.
- `references/chromadb-collection-diagnostic.md` — chromadb 1.5.x cross-collection Rust
  compaction bug: isolated DB workaround, what doesn't work (sqlite surgery, WAL clearing,
  threading tricks), and HNSW file structure reference for corruption diagnosis.
- `references/secondary-lit-reingest-procedure.md` — complete remediation workflow
  for a corrupted secondary_literature collection: HTML stripping, public-domain text
  sourcing (Gutenberg, New Advent, archive.org djvu.txt), chunk_text paragraph-splitting
  fix, analytical_categories + motif_ids/archetype_ids metadata, EF-conflict resolution,
  and analytical schema loading into graph_enrich.py (Eliade/Jung/Dumézil).
- `references/rdf-graph-postprocessing-patterns.md` — post-processing correction patterns
  for RDF knowledge graphs: symmetrizing property pairs, adding derived numeric properties
  (e.g. approximateDateCE from date label strings), removing CIDOC-CRM/SKOS orphan import
  stubs, verifying DataProperty vs ObjectProperty consistency, and the string-suffix URI
  matching pitfall. Includes the historical date-label regex parser covering all BCE/CE
  formats found in the mythology corpus.
- `references/entity-enrichment-mining.md` — mining `motif_analysis.json` AND disk text
  files to produce entity↔text and entity↔motif edges that `graph_enrich.py` leaves missing.
  Covers three passes in order: (1) `key_figures→featuresDiety` from motif_analysis JSON
  (fast, high precision), (2) full-text disk scan for deity name occurrences in
  `~/Religion/<tradition>/<title>/*.txt` using word-boundary regex at threshold ≥2 mentions
  (slower, 2-3× higher recall), (3) curated scholarly mapping of deity→motif from comparative
  mythology literature. Label normalization `re.sub(r'[^a-z0-9]','',s.lower())` achieves
  116/116 text-key match vs naive 46/116. Generalizes to any sparse entity type in any corpus
  where text files are organized in per-tradition directories. The disk-scan approach works
  even when ChromaDB collections are corrupted or unavailable.
- `references/kg-visualization-best-practices.md` — browser-side visualization of knowledge
  graphs: library selection by node count, adjacency index schema, graphology Louvain
  benchmarks and tuning, DH tool comparison (Palladio/nodegoat/Kumu), 4-level LOD zoom
  pattern, D3-force tuning for 700-node graphs, Okabe-Ito palette, shape/edge encoding,
  and implementation checklist. Full research output also at ~/knowledge-graph-best-practices.md.
- `references/theme-normalisation-and-metadata-backfill.md` — RDF controlled-vocab
  normalisation pattern (`myth:hasTheme` → `myth:hasThemeVocab` URI nodes), 25 master
  theme definitions with keyword lists, multi-word scoring algorithm, ChromaDB metadata
  backfill with nested source_id path matching (stem + parent-dir two-level strategy),
  ARCHETYPE_MAP → corpus source_id directory table, and paragraph-aware chunker sync notes.

32. **String-suffix URI matching is dangerous for RDF node identification** — NEVER
   use `str(node).endswith('Concept')` or similar suffix checks to identify nodes.
   It matches predicates as well as subjects/objects: in this corpus `myth:sharesConcept`
   (a property) ends with "Concept" and was accidentally caught during an orphan-node
   cleanup pass, causing its 5 ontology definition triples (rdf:type, rdfs:label,
   rdfs:comment, rdfs:domain, rdfs:range) to be deleted — breaking the property schema.

   Always use **exact URI comparison** for known node targets:
   ```python
   # WRONG — matches myth:sharesConcept, myth:subConcept, skos:Concept, and anything ending 'Concept'
   if isinstance(node, URIRef) and str(node).endswith('Concept'):
       candidate_nodes.append(node)

   # RIGHT — exact match for the specific external node you want to remove
   SKOS_CONCEPT = SKOS.Concept   # the exact URI you intend
   if node == SKOS_CONCEPT:
       candidate_nodes.append(node)
   ```
   For dynamically discovering orphan nodes from an unknown namespace, filter by
   **namespace prefix** (never suffix): `str(node).startswith("http://www.cidoc-crm.org/")`.

34. **hasTheme free-text proliferation — normalise to a controlled vocabulary via `hasThemeVocab`.**
   LLM-generated `myth:hasTheme` triples accumulate near-duplicate free-text strings.
   685 triples → 672 near-unique strings makes theme GROUP BY impossible.
   Fix: additive normalisation that keeps originals and adds typed URI nodes:
   - `myth:hasThemeVocab <myth:Theme_heroism_quest>` — new typed pointer
   - `myth:hasTheme "Heroic deeds and heroes"@en` — kept for full-text search
   - `rdfs:label "Heroism & Quest"@en` on the Theme node
   - `myth:themeLabel "..."@en` for each original string that mapped here
   - Use **multi-word keyword scoring** (longer phrases score higher, preventing
     single-char false positives). Route unmapped strings to `myth:Theme_other`.
   Expected: ~77% mapping rate on first pass with 25 themes. Triple count grows
   because `hasThemeVocab` triples are added on top of existing `hasTheme` triples.
   See `references/theme-normalisation-and-metadata-backfill.md` for the full
   25-theme vocabulary, scoring algorithm, and script location.

36. **`re.sub()` fails on JSON data blobs embedded in HTML — use sentinel `replace()` instead.**
   When injecting a large JSON blob into an HTML template as a JS variable, Python's
   `re.sub()` treats `\u` unicode escapes and backslashes inside the JSON as regex
   backreference syntax and raises `re.PatternError: bad escape \u at position N`.

   ```python
   # WRONG — fails on any JSON containing unicode escapes or backslashes
   html = re.sub(r'const DATA = {.*?};', f'const DATA = {data_json};', html, flags=re.DOTALL)

   # RIGHT — use a sentinel that re.sub never needs to see
   # In the HTML template: const GRAPH_DATA = __GRAPH_DATA_PLACEHOLDER__;
   html = html.replace('__GRAPH_DATA_PLACEHOLDER__', data_json)

   # RIGHT — or walk brace depth manually if no sentinel
   idx = html.find('const GRAPH_DATA = {')
   depth, i = 0, idx + len('const GRAPH_DATA = ')
   while i < len(html):
       if html[i] == '{': depth += 1
       elif html[i] == '}':
           depth -= 1
           if depth == 0: break
       i += 1
   html = html[:idx] + 'const GRAPH_DATA = ' + data_json + html[i+1:]
   ```
   `str.replace()` is literal matching with no escape interpretation — safe for
   arbitrary JSON content. The sentinel approach also makes templates readable.

35. **ChromaDB metadata backfill — nested source_id paths require two-level matching.**
   `secondary_literature` source_ids follow nested paths like:
   `secondary/layer3_analytical_frameworks/campbell/campbell_masks_primitive.txt`
   A naive prefix-strip (`source_id.replace('secondary/', '')`) fails to match
   ARCHETYPE_MAP keys (`'campbell'`, `'jung'`, `'eliade'`).
   Correct approach: match on both the **filename stem** AND the **parent directory name**,
   with keys sorted longest-first to prevent `'van'` matching before `'van_gennep'`:
   ```python
   p = PurePosixPath(source_id)
   stem, parent = p.stem, p.parent.name
   for key in sorted(ARCHETYPE_MAP, key=len, reverse=True):
       if stem.startswith(key): return ARCHETYPE_MAP[key]
   for key in sorted(ARCHETYPE_MAP, key=len, reverse=True):
       if parent.startswith(key): return ARCHETYPE_MAP[key]
   ```
   Update with `col.update(ids=batch_ids, metadatas=batch_metas)` in batches of 500.
   Do NOT re-embed — `col.update()` preserves all other metadata fields.
   See `references/theme-normalisation-and-metadata-backfill.md` for the full
   source_id → parent-directory mapping table for this corpus.
## Additional Reference files

- `references/cross-links-passage-quality.md` — cross_links.json Passage Quality Issue

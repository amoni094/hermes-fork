# Knowledge Graph Corpus Pipeline — Full Pitfalls Catalogue

Extracted from SKILL.md August 2026 to keep SKILL.md under 50KB.
**Do NOT re-add inline to SKILL.md. Update this file directly.**

Last synced: August 2026 | 33 entries

---

1. **Missing `from pathlib import Path` in ontology.py** — if `Path` is only used
   in the `__main__` block, it will crash at runtime with `NameError: name 'Path'
   is not defined`. Always import it at file top with the other imports.

2. **ChromaDB `OpenAIEmbeddingFunction` type stub mismatch** — Pyright reports
   `reportArgumentType` when passing `OpenAIEmbeddingFunction` to
   `get_collection(embedding_function=...)`. This is a chromadb stub issue, not a
   runtime error. Ignore or suppress with `# type: ignore`.

3. **Scraper picks up navigation links** — sacred-texts.com uses the first `<table>`
   as a sidebar nav. Always `tables[0].decompose()` before `get_text()`. Also
   filter links containing `cdshop`, `facebook`, `addthis`, `paypal` substrings.

4. **ChromaDB `.count()` returns 0 after upsert if collection was freshly created
   with a different embedding function** — delete and recreate the collection if
   you switch embedding backends mid-pipeline.

5. **Large corpora need batching** — ChromaDB add/upsert has a ~5000 doc limit
   per call on some versions. Batch in groups of 100.

6. **rdflib symmetric properties need manual double-assertion** — OWL symmetric
   properties (`myth:parallelTo`, `myth:cognateOf`, `myth:sameConceptAs`) are inferred
   by a reasoner, but basic SPARQL without a reasoner won't see the reverse direction.
   Add both directions explicitly in the graph.

   When symmetrizing in a post-processing pass: collect ALL existing pairs FIRST as a
   frozen set, then iterate and add missing reverses. Do NOT add while iterating the live
   graph — you may see newly-added triples in the same pass and double-count:
   ```python
   pairs = {(s, o) for s, p, o in g.triples((None, sameAs, None))}
   for (a, b) in list(pairs):
       if (b, sameAs, a) not in pairs:
           g.add((b, sameAs, a))
   ```
   Counter-intuitive: even if the original graph had 7 asymmetric pairs, you may
   end up adding 14 triples (7 + their now-visible reverses), because the freshly
   collected `pairs` set didn't include the new reverses yet.

7. **Resumable scraper needs a stable state key** — use `tradition/safe_title` as
   the key (not URL), since the same text might be referenced from multiple URLs.

8. **Background scraper dies when the CLI session closes** — `terminal(background=True)`
   processes are tied to the session that spawned them. When the user closes or starts
   a new session, the scraper process is gone. Never rely on a background process
   surviving across sessions for a multi-hour job. Always pair a long-running scraper
   with a watchdog cron (every 10m) that checks `pgrep -af "scraper.py"` and restarts
   it if dead. The scraper's own skip-if-done logic makes restarts safe and resumable.

9. **Check for orphaned scraper instances before restarting** — if the scraper
   died mid-run and was restarted (manually or by a watchdog), previous session's
   processes may still be alive, causing multiple concurrent instances writing
   duplicate log lines and racing to write the same files. Always run
   `pgrep -af "python3 scraper.py"` before launching and kill extras:
   `pgrep -f "python3 scraper.py" | sort -n | tail -n +2 | xargs kill`.
   Then start one clean instance. Multiple instances won't corrupt state (skip logic
   is idempotent) but they waste bandwidth and thrash the log.

10. **Newly created watchdog crons may not auto-fire** — after `cronjob(action='create')`,
   the scheduler sometimes does not advance `next_run_at` until it receives a manual
   trigger. After creating any watchdog cron, immediately follow with
   `cronjob(action='run', job_id=...)` to force the first execution and verify
   `next_run_at` advances. Without this, the watchdog can sit idle indefinitely while
   the scraper stalls overnight. This was observed in practice — the watchdog showed
   `next_run_at` from creation time and never advanced until manually triggered.

11. **sacred-texts.com has ~24% dead URLs in any curated manifest** — when scraping
   sacred-texts.com with a pre-curated URL list, expect roughly 1 in 4 to return 404.
   The site restructured its paths at some point; many section-specific sub-paths
   (`/ane/cag/`, `/neu/ice/pro/`, `/gno/pist/`, `/shi/nihon/`) no longer exist.
   Strategy: after a first scraper run, diff the `state["failed"]` list against the
   manifest, then hunt correct URLs by walking the category index page
   (`/afr/index.htm`, `/pac/index.htm`, etc.) and trying sibling paths.
   Key confirmed working paths (as of Jul 2026):
   - Laws of Manu: `/hin/manu.htm` (single-page index, not `/hin/sbe25/`)
   - Pirke Avot: `/jud/sjf/index.htm` (Sayings of the Jewish Fathers)
   - Hadith: `/isl/bukhari/index.htm` (not `/isl/sot/`)
   - Book of the Dead: `/egy/ebod/index.htm` (Budge, not `/egy/ani/`)
   - Sumerian texts: `/ane/sum/index.htm` replaces Descent of Inanna + Chaldean + Hittite
   - Prose Edda: `/neu/pre/index.htm` (not `/neu/ice/pro/` or `/neu/ice/prose/`)
   - Homeric Hymns: `/cla/hh/index.htm` (not `/cla/hmn/`)
   - Kojiki: `/shi/kj/index.htm` replaces Nihongi (`/shi/nihon/` — 404)
   - Tao Te Ching: `/tao/taote.htm` (single page, not `/tao/tao/index.htm`)
   - I Ching: `/ich/index.htm` (not `/ich/icintrv.htm`)
   - Popol Vuh: `/nam/maya/index.htm` (section index, not sub-path `/pvga/`)
   - African: `/afr/yor/index.htm` (Yoruba-Speaking Peoples, not `/afr/afm/`)
   - Hawaiian: `/pac/hm/index.htm` (Hawaiian Mythology)
   - Celtic Mabinogion: `/neu/celt/mab/index.htm` (replaces Celtic Twilight + Tain)
   - Babylonian: `/ane/mba/index.htm` (Myths of Babylonia and Assyria)
   See `references/sacred-texts-url-repairs-2026.md` for the full 28-entry fix table.

   After fixing URLs, clear just the failed entries from `download_state.json` —
   keep the `downloaded` list intact so completed texts aren't re-fetched:
   ```python
   state["failed"] = []
   state["downloaded"] = [d for d in state["downloaded"] if d not in failed_set]
   ```
   Then restart the scraper — it skips already-done entries and only processes the
   repaired ones.

13. **Parallelizing scrapers against a polite-rate site is not worth it** — running
   multiple scraper instances against different tradition subsets would require
   splitting the manifest, separating state files, and coordinating log output.
   For a polite site (1.5-3s/req), the engineering cost outweighs the benefit
   for a one-time corpus download. The per-tradition speedup is marginal because
   most of the time is I/O wait, not CPU. Stick to a single instance with a watchdog.
   Exception: if the site has per-subdomain rate limiting or you're scraping
   truly independent hosts, parallelism is worth it.\n\n14. **OpenAI embeddings API rejects chunks > 8192 tokens with HTTP 400** — the
   error message is `"Invalid 'input[1]': maximum input length is 8192 tokens."`.
   The vectorizer logs it as a ChromaDB error and skips the chunk — no crash,
   no retry. Fix: add a pre-embedding truncation step. Before calling the embedding
   function, split any chunk whose estimated token count (chars / 4) exceeds 7500
   into sub-chunks and embed each separately. The 8192 limit applies per element
   in the batch, not to the total batch size.

15. **Two concurrent vectorize runs are harmless but wasteful** — if a
   post-scrape pipeline starts a second `vectorize.py` while the first is still
   running, both will process overlapping files (the state file update is not
   atomic). The ChromaDB `upsert` is idempotent so no data corruption occurs,
   but you're paying for duplicate OpenAI API calls. Prevent this by checking
   `pgrep -f "vectorize.py"` before launching a second instance, or by making
   the post-scrape pipeline explicitly wait for the first to exit.

13. **Do NOT use `&` inside `terminal(background=True)`**
   `terminal(command="python3 scraper.py &", background=True)` forks a subshell that
   exits immediately, orphaning the real process with no Hermes handle. Hermes sees the
   outer shell exit and marks the job done in ~3s (`status: exited`). Use
   `terminal(command="python3 scraper.py", background=True, notify_on_complete=True)`
   with no trailing `&`. Verify it's actually running with
   `process(action='poll', session_id=...)` a few seconds after launch and confirm
   `status == 'running'`.

16. **ChromaDB `collection.get()` rejects `$eq` filter — use `query()` instead.**
   `collection.get(where={"text_id": {"$eq": id}})` raises `ValueError: Expected where
   operator to be one of $gt, $gte, $lt, $lte, $ne, $eq, $in, $nin, $contains, ... got
   $eq in get.` on ChromaDB ≥0.6. The `$eq` filter is only valid inside `query()`, not
   `get()`. To fetch chunks for a specific text, use:
   ```python
   results = collection.query(
       query_texts=[f"{title} {tradition}"],
       n_results=n_chunks,
       where={"tradition": {"$eq": tradition}},
   )
   ```
   Or use `get()` without a `where` clause and filter the returned metadatas in Python.

18. **`--force` + `--tradition` filter wipes the entire output file.** If `motif_analyzer.py`
   loads results only when `not args.force`, a `--force --tradition X` re-run on a
   filtered subset resets `results = {}` and then saves only the 6 filtered entries,
   destroying the 110 other texts' results. Fix: **always load the existing file first**,
   regardless of `--force`. The `--force` flag should only control whether matched entries
   are re-analyzed, never whether unmatched entries are preserved:
   ```python
   # CORRECT: always load first
   if OUTPUT_FILE.exists():
       with open(OUTPUT_FILE) as f:
           results = json.load(f)
   else:
       results = {}
   # --force only re-analyzes matched entries, never wipes unmatched ones
   ```
   This was observed in practice and caused full data loss of 110 texts' analysis output.
   The graph rebuild that followed produced only 51 motif links instead of 828.
   Note: the 9119-triple graph from the first full run was already overwritten before
   the bug was caught — no TTL backup existed. **Always keep a dated backup of
   `myth_knowledge_graph.ttl` before re-running graph_enrich.py:**
   ```bash
   cp ~/Religion/ontology/myth_knowledge_graph.ttl \
      ~/Religion/ontology/myth_knowledge_graph_$(date +%Y%m%d_%H%M).ttl
   ```

19. **sacred-texts.com "native language" pages contain zero actual script content.**
   The scraper downloads HTML shells; the native Unicode text was never present.
   After scraping, verify with a Unicode range scan (Hebrew `\u05d0`-`\u05ea`, Arabic `\u0600`-`\u06ff`, Devanagari `\u0900`-`\u097f`).
   For genuine native-language text, use dedicated APIs/sources instead.
   See `references/native-language-sources.md` for confirmed-working endpoints
   (Sefaria/Hebrew, quran.com/Arabic, GRETIL/Sanskrit+Pali, Kanripo/Classical Chinese,
   Perseus/Greek+Latin, CELT/Old Irish+Welsh, Wikisource/Old Japanese, Shabados/Gurmukhi,
   Hadith API/Arabic) and the `fetch_native_languages.py` script.

20b. **Comprehensive native-language sourcing for all 116 texts — full language map.**
   Full table of confirmed-working sources (Jul 2026) incl. Ancient Greek/Latin (Perseus),
   Old Irish/Welsh (CELT), Old Japanese (Wikisource), Pali (GRETIL), Sanskrit (GRETIL),
   Classical Chinese (Kanripo), Arabic Hadith (hadith.gading.dev), Punjabi (Shabados).
   NOT SOURCEABLE: oral-only traditions (Aboriginal, Polynesian, Lakota, etc.).
   NOT YET FOUND: Ge'ez (Kebra Nagast), Ardhamagadhi Prakrit (requires auth), cuneiform.
   See `references/native-language-sources.md` for the full table and `fetch_all_native_languages.py`.

20. **Structural schema analysis is impossible on English-only translations.**
   Features like Hebrew gematria (letter=number value), Arabic triliteral root morphology,
   Sanskrit Chandas syllable-meter classification, and the semantic layering of Classical
   Chinese characters are completely invisible in translation. The motif analysis and
   cross-linking in this pipeline operates on English translations only — a significant
   limitation for any claim about *structural* (not just narrative) cross-traditional
   parallels. Always fetch native-language texts before performing structural schema analysis.

17. **LLM motif extraction JSON failures — ancient text quotes break JSON string escaping.**
   When Haiku includes literal passage text in "evidence" values, apostrophes, em-dashes,
   and raw quotes from ancient texts (especially Norse/Icelandic dialogue) corrupt the JSON.
   Two fixes needed together:
   - **Prompt**: add "no raw quotes in string values — paraphrase evidence rather than
     quoting directly". Also avoid apostrophes inside the prompt's JSON example block.
   - **Parser**: extract by brace-finding, don't just strip ``` fences:
     ```python
     start = raw.find("{"); end = raw.rfind("}") + 1
     if start >= 0 and end > start: raw = raw[start:end]
     return json.loads(raw)
     ```
   If all 3 retries fail, re-run affected traditions with
   `--force --tradition norse-icelandic --delay 1.0`. See
   `references/deep-analysis-design-notes.md` lesson 4 for full detail.

21. **GRETIL Rigveda files are IAST (Latin transliteration), not Devanagari.**
   The `rv_{N:02d}_u.htm` files (where `_u` = "unicode") contain IAST romanization
   (ā, ī, ū, ṛ, ṭ, ḍ, ṇ, ś, ṣ, ḥ, ṃ), NOT Devanagari Unicode. Despite the `_u` suffix,
   there are zero chars in the U+0900–U+097F range. To get Devanagari from GRETIL:
   1. Download the IAST file and extract text (strip HTML, filter header lines)
   2. Convert via `indic-transliteration` library:
      ```bash
      pip install indic-transliteration
      ```
      ```python
      from indic_transliteration import sanscript
      from indic_transliteration.sanscript import transliterate
      deva = transliterate(iast_text, sanscript.IAST, sanscript.DEVANAGARI)
      ```
   The conversion is high-quality for standard IAST. Minor edge case: ḷ (vocalic L)
   maps to ऌ, which is correct but rare in Vedic texts.
   Cache the IAST intermediate file to avoid re-downloading on re-runs.
   See `fetch_native_lang_patch.py` for the full implementation.

22. **OWL schema audit — run before every graph_enrich rebuild.**
   A full schema consolidation pass (July 2026) found 6 HIGH and 9 MEDIUM issues.
   Key patterns to catch: module-level constants in wrong order; class/property name typos;
   property domain/range violations (add a second property rather than widening);
   declared properties never populated; Thompson code collisions (never use "A0");
   Concepts typed as NarrativeMotif; ObjectProperty storing Literals; undeclared properties
   (every property used anywhere must have `declare_prop`/`declare_dprop` in ontology.py);
   helper function closure ordering; SKOS.Concept as parent class (use `skos:inScheme` instead);
   missing concept seeds; missing `g.bind()` for all namespaces; 5 new analytical classes
   (`AnalyticalFramework`, `StructuralSchema`, `DumezilFunction`, `BinaryOpposition`,
   `SecondarySource`) must be declared before enrich_graph_analytical.py runs.
   New properties added Jul 2026: `approximateDateCE` (xsd:integer), `myth:Theme` as OWL.Class.
   Full checklist with verification scripts: `references/owl-rdf-ontology-audit-checklist.md`

23. **Secondary literature ChromaDB embedding quality — audit before trusting results.**
   Chunk count alone does not mean content is usable. Internet Archive HTML pages
   saved as `.txt` embed as pure JS/HTML boilerplate, not scholarly content.

   **Quick spot-check:**
   ```python
   sample = coll.get(limit=3, include=["documents"], where={"author": "C.G. Jung"})
   for doc in sample["documents"]:
       print(doc[:120])   # if this starts with <!DOCTYPE or <html, source is junk
   ```

   **Detection at ingest time**: read first 200 bytes of each .txt file and check
   for `b'DOCTYPE html'` or `b'<html'`. Those files need HTML stripping first.

   **HTML strip recipe** (Internet Archive pages):
   ```python
   import re
   t = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
   t = re.sub(r'<style.*?</style>', '', t, flags=re.DOTALL|re.IGNORECASE)
   t = re.sub(r'<[^>]+>', ' ', t)
   t = re.sub(r'&(?:amp|nbsp|[a-z]+);', ' ', t)
   t = re.sub(r'\s+', ' ', t).strip()
   ```
   After stripping, verify word count is substantial (>10K words for a full book).
   A 1MB HTML file that yields only ~1,200 words is still a stub — the actual
   text was not in the archive page (Shankara Brahmasutra case). Source it elsewhere.

   **Re-embed procedure**: delete old chunks by source_id, write clean .txt,
   re-run vectorizer for that source only. Do NOT re-embed the whole collection.

   **Stub files** (<500 bytes): landing pages / ToC stubs with no real text.
   Chunks from stubs are noise even though the count looks plausible. Flag and replace.

   **Missing analytical_categories in metadata**: each `secondary_literature` chunk
   should carry `analytical_categories` from its `.meta.json` file (e.g.
   `["Hierophany", "AxisMundi"]` for Eliade). Without it, you can only filter by
   author/tradition, not by analytical concept. Add at ingest time; re-embed to backfill.

   **Disconnected layer4 schema files**: `layer4_modern_scholarship/` JSON and TTL
   schemas (Eliade OWL, Jung JSON, Dumézil JSON) are not loaded into the RDF graph
   and not embedded in ChromaDB. Add graph_enrich.py loader functions to make
   analytical framework classes (e.g. `eliade:Hierophany`, `dumezil:F1_sovereignty`)
   queryable via SPARQL alongside primary text triples.

   See `references/secondary-lit-embedding-audit-2026.md` for the full source-by-source
   status table (which are HTML junk, which are stubs, which are OK) and remediation plan.

27. **hnswlib stack overflow segfault on large collections (chromadb 1.5.x).**
   On collections with ~13K+ nodes, `client.get_collection()` crashes with exit 139
   (no traceback) because hnswlib's recursive DFS overflows the default 8MB stack.
   **Fix**: `ulimit -s unlimited && python3 vectorize.py` in the same shell invocation.
   Using `threading.stack_size(256*1024*1024)` as an alternative works for a healthy index
   but NOT for a physically corrupt one. `resource.setrlimit` from within Python fires
   too late after the C extension is imported — use the shell ulimit instead.
   Full diagnostic + repair procedure: `references/chromadb-pitfalls.md`

28. **HNSW index corruption from mid-write crash — link_lists.bin can grow to TB scale.**
   If vectorize.py is killed mid-write (OOM, SIGKILL), `link_lists.bin` can become a
   TB-scale sparse file. Subsequent `get_collection()` calls then segfault. Repair:
   1. `client.delete_collection(name)` — works even when get_collection segfaults
   2. Clear `embeddings_queue` in sqlite: `conn.execute("DELETE FROM embeddings_queue")`
   3. Reset vectorize_state.json, re-run with `ulimit -s unlimited`
   NEVER use sqlite surgery (manual DELETE) to fix a collection while a chromadb client
   instance is alive — the Rust state manager caches will cause "Failed to apply logs"
   errors on all subsequent inserts even after deletion. Always delete via the Python API.

29. **chromadb 1.5.x cross-collection Rust compaction bug — use isolated DB per collection.**
   Adding a new collection to a PersistentClient that already has existing collections with
   WAL history raises "Error in compaction: Failed to apply logs to the metadata segment"
   on EVERY insert, even in a fresh Python process with a clean sqlite. None of the
   following workarounds help: clearing embeddings_queue, removing stale max_seq_id rows,
   deleting orphaned HNSW directories, or using delete+create in the same client.
   **The only working fix**: use a separate empty DB directory for the affected collection.
   ```python
   # Isolated DB for the new collection — avoids the cross-collection Rust bug
   CHROMA_SACRED = Path("~/Religion/chroma_db_sacred").expanduser()
   client = chromadb.PersistentClient(path=str(CHROMA_SACRED))
   coll = client.create_collection("sacred_texts", metadata={"hnsw:space": "cosine"})
   ```
   If you ultimately want one DB, merge after the isolated collection is complete:
   copy the HNSW segment dir and sqlite rows into the main DB. Alternatively, run
   all query code with separate `CHROMA_DIR` paths per collection.
   Full diagnostic: `references/chromadb-collection-diagnostic.md`

37. **Diagnosing a ChromaDB collection that is empty or throws "Failed to apply logs to the metadata segment".**
   When `collection.count()` raises `InternalError: Error sending backfill request to compactor`
   or returns 0 for a collection that should have data, the actual state is in the SQLite WAL,
   not the HNSW files. Diagnosis procedure:

   ```python
   import sqlite3
   conn = sqlite3.connect('/path/to/chroma_db/chroma.sqlite3')
   cur  = conn.cursor()

   # Step 1: check collections
   cur.execute("SELECT id, name FROM collections")
   cols = {name: cid for cid, name in cur.fetchall()}

   # Step 2: check embeddings_queue (WAL) — any rows here block the collection
   cur.execute("SELECT COUNT(*) FROM embeddings_queue")
   queue_count = cur.fetchone()[0]
   print(f"WAL queue rows: {queue_count}")  # >0 = stuck WAL; 0 = not WAL issue

   # Step 3: check segment row counts
   cid = cols.get('sacred_texts')
   cur.execute("SELECT id FROM segments WHERE collection=?", (cid,))
   segs = [r[0] for r in cur.fetchall()]
   for seg in segs:
       cur.execute("SELECT COUNT(*) FROM embeddings WHERE segment_id=?", (seg,))
       print(f"Segment {seg[:8]}: {cur.fetchone()[0]} rows")  # 0 = collection truly empty
   conn.close()
   ```

   **Interpretation:**
   - `queue_count > 0` AND `segment rows == 0`: collection was never populated; the
     WAL has stuck entries that prevent any future writes. The data was never there.
     Fix: verify whether data exists in a different DB directory (e.g. `chroma_db_sacred`).
   - `queue_count > 0` AND `segment rows > 0`: partial write stuck in WAL. Data IS there
     but count/query fail. Attempt `delete_collection()` + fresh `get()` from source.
   - `queue_count == 0` AND `segment rows == 0`: collection is genuinely empty, no stuck WAL.
     Check HNSW binary file sizes — if `data_level0.bin` is >0 bytes, there may be
     a schema version mismatch (collection was created by a different ChromaDB version).

   **The `chroma_db` sacred_texts root cause (Jul 2026):** A `test_zeus` test embedding
   written at `2026-07-23 09:49:54` stuck in the WAL with 0 segment rows — collection was
   NEVER populated. The actual 28,701-chunk collection was built in `chroma_db_sacred`.

39. **Diagnosing graph hairball density — edge type analysis before simplification.**
   When a force-directed graph is unnavigable (all nodes cluster to center, labels
   overlap, no clear structure), the cause is almost always a small number of
   high-count edge types creating mega-hubs. Diagnose before redesigning:

   ```python
   import json
   from collections import Counter
   with open('ontology/graph.json') as f:
       g = json.load(f)

   # Step 1: edge type distribution
   rel_count = Counter(l.get('relation','?') for l in g['links'])
   for r, c in rel_count.most_common(15):
       print(f"  {c:5d}  {r}")

   # Step 2: degree distribution of nodes
   from collections import defaultdict
   deg = defaultdict(int)
   id_map = {n['id']: n for n in g['nodes']}
   for l in g['links']:
       deg[l['source']] += 1; deg[l['target']] += 1

   print("Top 20 hubs:")
   for nid, d in sorted(deg.items(), key=lambda x: -x[1])[:20]:
       n = id_map.get(nid, {})
       print(f"  deg={d}  [{n.get('type')}]  {n.get('label')}")

   # Step 3: edge type → hub contribution
   # Which edge types contribute to the top hub?
   top_hub_id = sorted(deg.items(), key=lambda x: -x[1])[0][0]
   hub_edges = [(l['relation'], l['source'] if l['target']==top_hub_id else l['target'])
                for l in g['links'] if l['source']==top_hub_id or l['target']==top_hub_id]
   print(Counter(e[0] for e in hub_edges).most_common())
   ```

   Decision rule:
   - If one edge type accounts for >40% of total links → drop from summary tier
   - If a node type is 50%+ of all nodes with nearly all degree-1 → exclude from summary
   - If a "catch-all" node has degree >> any specific node in its type → it's a junk-bin, drop it
   - Hub degree > 50 in a graph of <1000 nodes = that node type needs to become
     an edge attribute (metadata) rather than a graph node
   See `references/two-tier-graph-architecture.md` for the full diagnosis + result for
   the comparative religion corpus (before: max deg=87, after: max deg=47).
   When multiple ChromaDB instances are required (e.g. due to pitfall 29 cross-collection
   compaction bug), create a single routing module rather than hardcoding paths in each script:

   ```python
   # scripts/chroma_config.py
   from pathlib import Path
   import chromadb

   BASE_DIR = Path(__file__).parent.parent

   COLLECTION_PATHS = {
       "sacred_texts":         BASE_DIR / "chroma_db_sacred",  # isolated DB
       "religious_texts":      BASE_DIR / "chroma_db",          # main DB
       "secondary_literature": BASE_DIR / "chroma_db",          # main DB
   }

   _clients = {}
   def get_client(path):
       key = str(path)
       if key not in _clients:
           _clients[key] = chromadb.PersistentClient(path=str(path))
       return _clients[key]

   def get_collection(name):
       path = COLLECTION_PATHS.get(name)
       if path is None:
           raise ValueError(f"Unknown collection: {name}")
       return get_client(path).get_collection(name)
   ```

   Update all scripts to `from chroma_config import get_collection` instead of
   hardcoding `chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(name)`.
   Eliminates path drift — when a collection moves to a new isolated DB, update
   `COLLECTION_PATHS` once and all scripts pick it up automatically.

30. **Merging isolated ChromaDB DBs via sqlite surgery loses metadata visibility.**
   After copying HNSW segment dir + sqlite rows from an isolated DB into the main DB,
   `collection.query()` returns results with `metadata=None` even though the sqlite
   rows are present. Root cause: the Rust backend looks up metadata by sqlite
   `embeddings.id` (integer autoincrement), not by `embedding_id` (hash). Copied rows
   collide with existing integer IDs; `INSERT OR IGNORE` silently skips conflicts, and
   ID remapping is error-prone due to prior orphaned rows from failed merge attempts.
   **Recommendation**: Do NOT merge. Keep separate DB paths and use a query router:
   ```python
   sacred_client = chromadb.PersistentClient(path=str(BASE_DIR / "chroma_db_sacred"))
   main_client   = chromadb.PersistentClient(path=str(BASE_DIR / "chroma_db_new"))
   ```
   See comparative-religion-corpus skill references/chromadb-pitfalls.md section 8.

31. **EF conflict: never pass embedding_function= to get_collection(), and never use
   query_texts= on manually-embedded collections.**
   Two mistakes — both cause dimension-mismatch errors on collections built with
   manual embedding (vectors passed explicitly, no EF bound at collection creation):

   a) `get_collection("name", embedding_function=ef)` — ChromaDB binds the supplied EF
      at open time; subsequent queries use it instead of the stored vector space, causing
      silent mismatches. Fix: always call `get_collection("name")` with **no** EF arg:
      ```python
      # WRONG — binds wrong EF, causes dimension mismatch on query
      collection = client.get_collection("sacred_texts", embedding_function=embed_fn)
      # RIGHT — no EF; pre-embed queries manually below
      collection = client.get_collection("sacred_texts")
      ```

   b) `query(query_texts=["..."])` — triggers the stored schema EF (often all-MiniLM-L6-v2,
      384d), not your 1536d OpenAI model. Fix: pre-embed and use `query_embeddings=`:
      ```python
      # WRONG — triggers stored schema EF, wrong dimension
      results = coll.query(query_texts=["my query"], n_results=5)
      # RIGHT — pre-embed manually
      from openai import OpenAI
      oai = OpenAI(api_key=openai_key)
      vec = oai.embeddings.create(model='text-embedding-3-small', input=["my query"]).data[0].embedding
      results = coll.query(query_embeddings=[vec], n_results=5)
      ```

   **Batch pre-embedding for efficiency** — when querying many inputs, embed in one API call:
   ```python
   all_texts = [f"{m['label']}: {m['description']}" for m in motif_list]
   response = oai.embeddings.create(model='text-embedding-3-small', input=all_texts)
   vecs = {mid: item.embedding for mid, item in zip(motif_ids, response.data)}
   # Then per-motif query using pre-computed vector
   results = coll.query(query_embeddings=[vecs[motif_id]], n_results=top_k, ...)
   ```
   This applies to ALL collections built with the EF-bypass pattern from pitfall 2.

33. **Querying multiple ChromaDB collections and merging results.**
   When a pipeline uses separate isolated DB directories (see pitfall 29/30), query each
   collection separately, then merge and sort by similarity. Standard pattern:
   ```python
   # Query two collections with same pre-embedded vector
   hits1 = sacred_col.query(query_embeddings=[vec], n_results=top_k,
                             include=["metadatas", "documents", "distances"])
   hits2 = sec_col.query(query_embeddings=[vec], n_results=top_k // 2,
                          include=["metadatas", "documents", "distances"])

   # Convert to flat list with source tag
   def parse_hits(results, collection_name):
       rows = []
       for meta, doc, dist in zip(results["metadatas"][0],
                                   results["documents"][0],
                                   results["distances"][0]):
           rows.append({**meta, "passage": doc[:400],
                        "similarity": round(1.0 - dist, 4),
                        "source_collection": collection_name})
       return rows

   all_hits = sorted(parse_hits(hits1, "sacred_texts") + parse_hits(hits2, "secondary_literature"),
                     key=lambda x: x["similarity"], reverse=True)
   ```

   **Content dedup before cross-linking** — before adding a cross-link, hash the
   passage content to skip near-identical passages already seen for this motif:
   ```python
   import hashlib

   def content_hash(text):
       return hashlib.md5(text[:200].encode()).hexdigest()[:12]

   seen_hashes = set()
   for (k1, k2) in combinations(text_keys, 2):
       h1, h2 = content_hash(entry1["passage"]), content_hash(entry2["passage"])
       if h1 in seen_hashes or h2 in seen_hashes:
           continue
       seen_hashes.add(h1); seen_hashes.add(h2)
       # add cross-link ...
   ```

   **Source tagging** — add `source1_collection` / `source2_collection` fields to
   each cross-link so consumers can distinguish primary-text–primary-text links from
   primary-text–secondary-literature links. Raise threshold when adding secondary
   literature (noise level is higher): 0.50 recommended vs. 0.40 for primary-only.

24. **ChromaDB EF conflict when rebuilding a collection with a different embedding function.**
   If a collection was created with `DefaultEmbeddingFunction` and you later try
   `get_or_create_collection(embedding_function=OpenAIEmbeddingFunction(...))`, ChromaDB
   raises `ValueError: embedding function conflict: new: openai vs persisted: default`.

   Fix for full rebuild: delete the collection first, then recreate:
   ```python
   try: client.delete_collection("secondary_literature")
   except Exception: pass
   collection = client.get_or_create_collection(name=..., embedding_function=embed_fn, ...)
   ```
   Fix for partial rebuild (--source flag): catch the ValueError, fall back to
   `client.get_collection(name)`. Detect stored EF:
   `coll._model.configuration_json["embedding_function"]["name"]`.

25. **chunk_text produces too few chunks when source has only a few giant paragraphs.**
   Dense commentary (Midrash, Tafsir) may have only 21 paragraphs over 285K words —
   a naive `\n\n`-splitter yields 21 chunks instead of ~670, each too large for the
   OpenAI 8192-token embed limit. Fix: add sentence-boundary splitting for any paragraph
   exceeding 2× CHUNK_SIZE before the normal paragraph-assembly loop:
   ```python
   sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\u201C\u2018])', para)
   ```
   Sanity check: chunk_count / word_count should be >= 1/500. genesis_rabbah
   (67K words): 21 chunks without fix → 163 chunks with fix.

26. **Analytical schema files (layer4) must be explicitly loaded in graph_enrich.py.**
   Eliade OWL TTL, Jung JSON, Dumézil JSON in `layer4_modern_scholarship/analytical_schemas/`
   are NOT automatically included in the RDF graph. Without an explicit loader, those
   classes cannot be SPARQL-queried alongside primary text triples. Add
   `add_analytical_schemas(g)` to graph_enrich.py:
   - `g.parse(eliade_schema.ttl, format="turtle")` — merges 9 Eliade OWL classes directly
   - Jung JSON → `jung:Archetype` / `jung:IndividuationProcess` / `jung:JungianSymbol` individuals
   - Dumézil JSON → `dumezil:TriFunction` individuals (F1/F2/F3) + seed deity→function triples
   - Bind namespaces `eliade:`, `jung:`, `dumezil:`, `rel:` in `load_ontology_graph()`
   - Call `add_analytical_schemas(g)` in `main()` before `add_llm_motif_analysis()`
   See `references/secondary-lit-reingest-procedure.md` for the pattern.


## Node Annotation Enrichment (node_annotations.json)

Full implementation: `references/node-annotation-enrichment.md`
Extracts `rdfs:label`/`rdfs:comment` from TTL via block-splitting, enriches with graph-derived fields (traditions_present, top_connections, cognates, text_count), and wires a browser info-pane with home/selected states.

---

## Semantic Proximity Force Layout

Full implementation: `references/semantic-proximity-force-layout.md`
Exact link-distance/strength values per relation type, degree-scaled charge/collision formulas, and alphaDecay tuning for knowledge graph force layouts where bridge edges must use long springs to preserve semantic clusters.

## Jaccard Similarity Force (node_similarity.json)

Full implementation: `references/jaccard-similarity-force.md`
Builds `node_similarity.json` of high-Jaccard pairs (shared-neighbour attraction) and applies as a custom D3/3d-force-graph force; also covers 3D graph CDN setup (3d-force-graph + Three.js) and key API differences from 2D.

---

## Deep Analysis Layer (LLM + Semantic)

Full implementation: `references/deep-analysis-layer.md`
Four-script pipeline (motif_taxonomy → motif_analyzer → cross_linker → graph_enrich) that replaces tradition-level motif guesses with text-level, evidence-backed assignments; covers motif taxonomy design (65 motifs, Thompson codes), Haiku prompt design, new RDF properties, and tradition vs. text-level assignment fallback logic.

---

## Build Order

```bash
# Phase 1: Foundation
python3 ontology.py          # build schema (fast, ~1s)
python3 scraper.py           # download corpus (slow, hours, resumable)
python3 vectorize.py         # embed chunks (minutes, needs OPENAI_API_KEY)
python3 graph_enrich.py      # populate graph (~4000 triples, tradition-level)
python3 query.py stats       # verify baseline

# Phase 2: Deep analysis (replaces tradition-level guesses with text-level truth)
bash deep_analysis_pipeline.sh
# or step by step:
python3 ontology.py                          # rebuild with new properties
python3 motif_analyzer.py --delay 0.5       # LLM motif extraction per text
python3 cross_linker.py --top-k 10 --threshold 0.38  # semantic cross-links
python3 graph_enrich.py                     # rebuild graph with analysis outputs
python3 query.py stats                      # verify enriched graph

# Phase 3: Browser visualization (self-contained HTML, works offline)
# See references/kg-visualization-best-practices.md for full design guide
# Input: ontology/graph.json (NetworkX node-link JSON)
# Output: religion_graph.html (~900KB self-contained file)
python3 -m pip install python-louvain networkx  # community detection deps
# Build script: scripts/build_visualization.py
#   1. Load graph.json + motif_analysis.json
#   2. Pre-compute Louvain communities (python-louvain, random_state=42)
#   3. Build typed adjacency index (Map<id, Map<relation, neighborId[]>>)
#   4. Inject data into HTML template via sentinel replace() — NOT re.sub()
#   5. Write self-contained HTML
# Features: Canvas rendering, LOD semantic zoom, node shapes, community colors,
#   tradition clustering force, ego-network (alt+click), shift+click highlight,
#   tradition/motif/type filter panel, physics sliders
```

The graph (~4000 triples for 116 texts) works immediately even before download,
since the ontology seeds all traditions, motifs, concepts, and known cross-links.
After deep analysis, expect 8000+ triples with named figures, episodes, and
cross-tradition passage parallels.

---

## Multi-phase pipeline chaining

When a second scraper pass runs in parallel (e.g. another session fixing 404 URLs
while the first vectorize pass is already underway), chain the remaining phases
with a polling wait script rather than manually watching:

```bash
# post_scrape_pipeline.sh
while pgrep -f "python3 scraper.py" > /dev/null 2>&1; do
    sleep 30
done
python3 vectorize.py      # incremental — only embeds new files not in vectorize_state.json
python3 graph_enrich.py   # regenerates TTL + graph.json with full semantic discovery
```

Run as `terminal(background=True, notify_on_complete=True)`. Blocks until all
scraper instances finish, then chains automatically — no babysitting.

`vectorize.py` must be idempotent: track processed files in `vectorize_state.json`
so re-runs only embed newly downloaded files, not the full corpus again.
`graph_enrich.py` is always safe to re-run — it rebuilds from manifest + ChromaDB.

---

## Two-Tier Graph Architecture (Summary + Full)

Full implementation: `references/two-tier-graph-architecture.md`
When an 800-node graph becomes a hairball (hub degree 87+), split into a Summary tier (254 nodes, 872 links, max degree 47) using high-signal relations only, and a Full tier for completeness. Covers edge-selection rationale, `build_tiered_graph.py`, Theme node design, OWL ontology changes, D3.js 2D/3D visualizer wiring, and PITFALL 40 (disconnected summary components).

---

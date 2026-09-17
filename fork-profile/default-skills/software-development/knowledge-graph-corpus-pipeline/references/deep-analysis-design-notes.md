# Deep Analysis Layer — Design Notes (July 2026)

## Problem with tradition-level motif assignment

The initial `TRADITION_MOTIFS` dict in `graph_enrich.py` assigns motifs at the
tradition level — every Hindu text gets all Hindu motifs, regardless of content.
This produced:
- Over-inclusive motif links (e.g. every Buddhism text tagged `trickster`)
- No differentiation between a short hymn and a full epic
- No evidence trail — couldn't verify why a motif was assigned

## Solution: text-level LLM extraction (motif_analyzer.py)

Claude Haiku (claude-haiku-4-5) analyzes ~8 sampled chunks per text:
- Samples from start, middle, and end of the text
- Returns structured JSON: `{motifs_present, themes, key_figures, narrative_episodes, text_character}`
- Confidence levels (high/medium/low) and brief evidence per motif
- ~$0.001/text at Haiku pricing; 116 texts ≈ $0.12 total

## Motif taxonomy expansion (25 → 65 motifs)

Original 25 motifs were too coarse. Added:
- **Creation subtypes**: earth_diver, separation_sky_earth, world_egg (was merged)
- **Hero subtypes**: slaying_monster, labyrinth_maze, abandoned_child, culture_hero, divine_child
- **Death/soul**: death_origin, first_humans, reincarnation, ancestor_spirits
- **Ritual**: scapegoat, sacred_animal, golden_age, shapeshifting
- **Concept**: karma, dharma, moksha_liberation, ahimsa, tao, wu_wei, logos, monotheism, eschatology
- All 65 include Thompson Motif-Index codes and keyword lists for ChromaDB queries

## Cross-linker design (cross_linker.py)

Uses ChromaDB semantic similarity to find parallel passages across traditions:
- Queries each of 65 motifs with descriptive text + keywords
- Groups results by tradition, generates cross-tradition pairs
- Threshold 0.38 cosine similarity (lower than the 0.35 in the original graph_enrich
  semantic discovery because we're querying with richer descriptions)
- Deduplicates: keeps highest-similarity link per (text1, text2, motif) triple

Expected output: 500-2000 cross-tradition links across 65 motifs for a 116-text corpus.
Actual result for this corpus (July 2026): 121 links before dedup, 87 unique pairs.

## New RDF properties (added to ontology.py)

```turtle
myth:strongMotif        rdfs:domain myth:ReligiousText ;
                        rdfs:range myth:NarrativeMotif .
myth:hasFigure          rdfs:domain myth:ReligiousText ;
                        rdfs:range myth:MythologicalFigure .
myth:parallelPassage    rdfs:domain myth:ReligiousText ;
                        rdfs:range myth:ReligiousText .
```

Plus datatype properties on ReligiousText:
- `myth:narrativeEpisode` (Literal)
- `myth:hasTheme` (Literal)
- `myth:textCharacter` (Literal, 1-2 sentence summary)
- `myth:motifEvidence` (Literal, "motif_id: paraphrase...")

And on NarrativeMotif:
- `myth:thompsonCode` (Literal, existing property reused)

## graph_enrich.py integration order

```python
def main():
    g = load_ontology_graph()
    add_expanded_motifs(g)       # 65 motifs + 25 taxonomy parallels from motif_taxonomy.py
    add_text_nodes(g)            # tradition-level links as baseline
    add_deity_cognates(g)
    add_influence_links(g)
    add_llm_motif_analysis(g)    # text-level overrides from motif_analysis.json
    add_cross_links(g)           # semantic passage parallels from cross_links.json
    discover_semantic_parallels(g)  # ChromaDB discovery (existing, now redundant but harmless)
```

LLM analysis is loaded AFTER text nodes so it can add to existing URIs without
needing to create them. Both layers coexist — tradition-level links remain as
a sparse fallback for texts with no LLM output.

## Confirmed final graph stats (July 2026, 116 texts, deep analysis pass)

| Metric | Before (tradition-level) | After (deep analysis) |
|--------|--------------------------|------------------------|
| RDF triples | 4,029 | 9,119 |
| Narrative motifs | 25 | 58 |
| Motif links | 1,338 | 2,000 |
| Motif parallels | 13 pairs | 34 pairs |
| Cross-passage parallels | 0 | 87 pairs |
| Mythological figures | 0 | 483 |
| Narrative episodes | 0 | 417 |
| Graph nodes | 293 | 807 |
| Graph edges | 2,345 | 3,744 |

## Cost estimates (July 2026 pricing)

| Step | Cost |
|------|------|
| motif_analyzer.py (116 texts, Haiku) | ~$0.12 |
| cross_linker.py (65 motifs × top-10) | ~$0.03 (OpenAI embeddings) |
| vectorize.py (13,666 chunks) | ~$0.15 (OpenAI embeddings) |
| **Total pipeline** | **~$0.30** |

## Lessons

1. `anthropic` is not in the default venv — `python3 -m pip install anthropic` before running motif_analyzer.py

2. ChromaDB `get()` with `where={"text_id": {"$eq": safe_id}}` raises ValueError on
   ChromaDB ≥0.6 — `$eq` is only valid inside `query()`, not `get()`. Use
   `collection.query(query_texts=[...], n_results=N, where={"tradition": {"$eq": t}})`
   for fetching text-specific chunks.

3. The `collection.get_collection()` Pyright error about `OpenAIEmbeddingFunction`
   is a stub issue — not a runtime error. Ignore it.

4. **JSON parse failures from Haiku LLM output (IMPORTANT)** — the root cause is
   not Haiku generating invalid JSON structure; it's that ancient text passages contain
   raw single/double quotes, apostrophes, em-dashes, and other chars that are legal
   text but break JSON string escaping when pasted verbatim as "evidence" values.
   Two fixes needed together:
   a) **Prompt**: instruct the model to PARAPHRASE evidence, not quote directly.
      Add to the prompt: "no raw quotes in string values — paraphrase evidence rather
      than quoting directly". Also remove the apostrophe from "this text's" in the
      prompt template — it can end up inside a JSON string.
   b) **Parser**: use brace-extraction as the primary strategy, not just fence-stripping:
      ```python
      start = raw.find("{")
      end = raw.rfind("}") + 1
      if start >= 0 and end > start:
          raw = raw[start:end]
      return json.loads(raw)
      ```
      This recovers gracefully when the model wraps the JSON in explanatory prose.
   The texts most affected were Norse/Icelandic (Poetic Edda, Volsunga Saga) because
   their passages contain dense Old Norse quoted dialogue with apostrophes. Fix and
   re-run with `--force --tradition norse-icelandic` if needed.

5. Always retry up to 3 times with 2s backoff on JSONDecodeError — sometimes a single
   malformed response is followed by a clean one on the next call.

6. **get_text_from_disk skips index files, not just content** — when a text directory
   contains only `index.txt`, `index_1.txt`, and `_metadata.json`, the disk fallback
   returns near-empty content and the LLM detects 0 motifs, 0 figures. Fix:
   ```python
   files = [f for f in sorted(d.glob("*.txt"))
            if not any(x in f.name for x in ("index", "metadata", "pageidx"))]
   if not files:
       files = list(sorted(d.glob("*.txt")))  # last resort: include index files
   ```
   Also: sample across the full file list (start + middle + end), not just the first N:
   ```python
   if len(files) > n_files:
       mid = len(files) // 2
       chosen = files[:3] + files[mid-1:mid+2] + files[-3:]
   ```

7. **ChromaDB `get()` with `$eq` filter raises ValueError on some versions** —
   see lesson 2 above.

8. **`--force` + `--tradition` filter DESTROYS the output file (DATA LOSS).**
   If `results = {}` is set when `args.force` is True, a targeted `--force --tradition X`
   re-run saves only the filtered subset and overwrites all other entries.
   This happened in practice: a `--force --tradition norse-icelandic` run on 6 texts
   wiped the motif_analysis.json down to 6 entries, destroying 110 texts' analysis.
   The graph rebuild that followed produced 51 motif links instead of 828, and the
   9119-triple TTL had already been overwritten — no recovery possible.

   Fix: **always load the existing file before resetting anything**:
   ```python
   if OUTPUT_FILE.exists():
       with open(OUTPUT_FILE) as f:
           results = json.load(f)
   else:
       results = {}
   # --force only re-analyzes matched entries, never clears unmatched
   ```

   Backup discipline: before every `graph_enrich.py` run, snapshot the TTL:
   ```bash
   cp ~/Religion/ontology/myth_knowledge_graph.ttl \
      ~/Religion/ontology/myth_knowledge_graph_$(date +%Y%m%d_%H%M).ttl
   ```

9. **Prose Edda (Brodeur) and Teutonic Mythology (Grimm) were index-only downloads.**
   Their directories contained only `index.htm`, `index.txt`, and `_metadata.json` —
   no actual content pages. The scraper followed the index URL but the site structure
   for those two texts was a single-page index with no sub-pages, or the content
   was behind a different URL structure. Workaround: treat them as known gaps; the
   Old Norse Prose Edda and Bellows Poetic Edda cover the same tradition adequately.
   For a complete corpus, manually fetch these two from an alternative source.

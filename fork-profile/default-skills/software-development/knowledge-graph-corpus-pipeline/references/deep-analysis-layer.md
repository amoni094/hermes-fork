# Deep Analysis Layer (LLM + Semantic)

After vectorization, a second analysis pass replaces tradition-level motif
guesses with text-level, evidence-backed assignments.

## Components

```
motif_taxonomy.py   65 motifs with Thompson codes, keywords, descriptions, known parallels
motif_analyzer.py   Claude Haiku analyzes each text's actual chunks -> motifs_present + key_figures + episodes
cross_linker.py     ChromaDB similarity across all 65 motifs -> cross-tradition parallel passages
graph_enrich.py     Consumes analysis/motif_analysis.json + analysis/cross_links.json
```

## Run order

```bash
python3 ontology.py                         # rebuild with new properties first
python3 motif_analyzer.py --delay 0.5       # ~$0.12 for 116 texts at Haiku pricing
python3 cross_linker.py --top-k 10 --threshold 0.38
python3 graph_enrich.py                     # now incorporates LLM + semantic outputs
```

Or use `deep_analysis_pipeline.sh` to run all four steps in sequence.

## Motif taxonomy design

- 65 motifs beats the naive 25 — expand to cover: creation subtypes (ex nihilo,
  chaos, earth-diver, world-egg, dismemberment), specific hero patterns
  (monster-slaying, labyrinth, abandoned child), soul concepts (reincarnation,
  ancestor spirits), ritual patterns (initiation, scapegoat, sacred marriage),
  and tradition-specific concepts (karma, dharma, tao, ahimsa, wu wei, logos).
- Include Thompson Motif-Index codes on every motif for cross-reference with
  academic mythology databases.
- Include `keywords` list per motif — used as the semantic search query in
  cross_linker.py: `f"{label}: {description}. Keywords: {', '.join(keywords[:6])}"`.

## LLM analysis prompt design (motif_analyzer.py)

- Use Claude Haiku (cheap, fast) not Sonnet — motif detection from sampled passages
  is a structured extraction task, not a reasoning task.
- Sample from start + middle + end of each text (not just the beginning).
- Ask for confidence levels (high/medium/low) and brief evidence quotes per motif.
- Request `key_figures`, `narrative_episodes`, `themes`, and `text_character` —
  these populate RDF properties `hasFigure`, `narrativeEpisode`, `hasTheme`,
  `textCharacter` respectively.
- Prompt must specify "respond with ONLY valid JSON" and strip markdown fences
  from the response before `json.loads()`.

## New RDF properties added in deep analysis pass

```
myth:strongMotif        — high-confidence motif link (subset of containsMotif)
myth:hasFigure          — text -> MythologicalFigure named entity
myth:parallelPassage    — text <-> text cross-tradition semantic parallel
myth:narrativeEpisode   — literal: key story episode in this text
myth:hasTheme           — literal: free-text theme annotation
myth:textCharacter      — literal: 1-2 sentence characterisation
myth:motifEvidence      — literal: "motif_id: evidence quote..."
myth:thompsonCode       — literal: Thompson Motif-Index code on NarrativeMotif
```

Add these to `ontology.py` via `declare_prop()` before running graph_enrich,
otherwise the ontology TTL will be missing their schema declarations even if the
graph itself stores the triples fine.

## Tradition-level vs text-level motif assignment

The original `TRADITION_MOTIFS` dict in graph_enrich.py assigns all tradition
motifs to every text in that tradition — crude and over-inclusive. The deep
analysis layer replaces this with genuine per-text assignments. Keep the
tradition-level dict as a fallback for texts where the LLM analysis fails or
finds no content, but prefer LLM results when available. In graph_enrich.py,
add LLM motif links first, then only fall back to tradition-level for texts
with no LLM output.

## Design notes reference

See `references/deep-analysis-design-notes.md` for:
- Full taxonomy design decisions
- Cost estimates
- Prompt patterns
- graph_enrich integration order
- Lesson 4: JSON failures from ancient text quotes (Norse/Icelandic apostrophes/em-dashes)

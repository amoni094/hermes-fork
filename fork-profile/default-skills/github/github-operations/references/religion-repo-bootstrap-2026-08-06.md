# Religion Knowledge Graph — GitHub Bootstrap (2026-08-06)

Repo: https://github.com/amoni094/religion-knowledge-graph (private)
Local path: ~/Religion/

## What was committed
- scripts/ — 40+ Python/shell scripts (vectorizer, scraper, graph builders, enrichment)
- ontology/ — RDF/OWL (myth_knowledge_graph.ttl, myth_ontology.ttl), graph JSON, node annotations/similarity
- analysis/ — synthesis reports, motif analysis, adversarial pass notes
- religion_graph_v3.html + religion_graph_3d.html — 2D and 3D visualisers
- README.md

## What was excluded (gitignored)
- Raw corpus text files (copyright risk + size) — african/, buddhism/, christianity/, etc.
- chroma_db/, chroma_db_new/, chroma_db_sacred/ — vector DB blobs
- Logs, download_state.json, vectorize_state.json
- Old visualiser versions (religion_graph.html, religion_graph_v2.html)
- scripts/__pycache__/, *.pyc

## Key pitfall caught
`git rev-parse --show-toplevel` from ~/Religion/ returned `/var/home/rainbow` — the directory
was sitting inside the home-dir git repo (which tracks ~/.hermes config), NOT its own repo.
Required `git init` inside ~/Religion/ to create a fresh dedicated repo before pushing.

## Push command used
```bash
gh repo create amoni094/religion-knowledge-graph --private --source=. --remote=origin --push
```

## .gitignore already present
~/Religion/.gitignore was well-structured and correctly excluded corpus/chroma/logs before
this bootstrap. No changes needed.

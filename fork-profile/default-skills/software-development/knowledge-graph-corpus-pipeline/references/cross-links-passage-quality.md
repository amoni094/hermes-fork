# cross_links.json Passage Quality Issue

## The Problem

`analysis/cross_links.json` has fields `passage1` and `passage2` per link entry.
These look like they should contain actual text passages for NER, triplet extraction,
or any text-analysis task. They do NOT.

## What They Actually Contain

Each "passage" is a 400-character ChromaDB metadata header stub with this format:

```
SOURCE: https://sacred-texts.com/pag/frazer/gb04100.htm PARENT: https://sacred-texts.com/pag/frazer/index.htm TITLE: The Golden Bough (Frazer) Golden Bough Chapter 41. Isis. | Internet Sacred Text Archive Sacred-texts Neopaganism ...
```

After stripping SOURCE:/PARENT:/TITLE: headers and HTML entities, the cleaned string is
**empty** (0 chars). There is zero actual text content in these fields.

## Impact

Confirmed during TripletExtractor build (August 2026):
- 242 "passages" loaded from cross_links.json
- 0 usable after metadata header stripping
- Had to switch to ChromaDB direct access to get real text

## Correct Approach

To get real passage text for analysis tasks, load directly from ChromaDB:

```python
import chromadb
from pathlib import Path

BASE_DIR = Path("~/Religion").expanduser()
client = chromadb.PersistentClient(path=str(BASE_DIR / "chroma_db_sacred"))
collection = client.get_collection("sacred_texts")

# Sample real passages
result = collection.get(limit=500, include=["documents", "metadatas"])
docs = result.get("documents") or []
metas = result.get("metadatas") or []

# Filter out any remaining stub docs
real_passages = [
    {"text": doc, "source": meta.get("tradition", "unknown")}
    for doc, meta in zip(docs, metas)
    if doc and len(doc) >= 60 and not doc.lstrip().startswith("SOURCE:")
]
# Yields ~492/500 real chunks
```

The sacred_texts collection has 28,701 real chunks after dedup (chroma_db_sacred).
A sample of 500 yields ~492 usable after stub filtering.

## Why cross_links.json Looks Like It Has Passages

The cross_linker.py script stores the ChromaDB document field for each matched chunk as
the "passage". But these documents ARE the metadata header stubs — they were stored
in ChromaDB with SOURCE:/PARENT:/TITLE: prefixes as the document content, not the
actual text. The actual text was either never present or was truncated away.

This is NOT a cross_linker.py bug to fix — the sacred_texts collection has since been
deduped and rebuilt with real content. The cross_links.json is just stale.

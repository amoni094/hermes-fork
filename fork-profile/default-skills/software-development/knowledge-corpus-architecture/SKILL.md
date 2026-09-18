---
name: knowledge-corpus-architecture
title: Knowledge Corpus Architecture
description: >
  Use when: Design, build, and query multi-layer knowledge corpora using the architecture from the Comparative Religion DB: multi-collection ChromaDB vectorstores, rich metadata taxonomies, RDF/OWL ontologies, and JSON knowledge graphs. Covers chunk strategy, metadata schema, motif/taxonomy extraction, multi-collection routing, and how these patterns apply to Hermes agent context (skills, sessions, memory, external docs).
keywords:
  - chromadb
  - vectorstore
  - ontology
  - knowledge-graph
  - multi-collection
  - metadata
  - taxonomy
  - chunking
  - rdf
  - hermes-context
triggers:
  - "Build a vectorized knowledge base for X"
  - "Design a corpus or document store for an agent"
  - "Multi-collection ChromaDB setup"
  - "Add ontology/taxonomy to a corpus"
  - "How should I structure metadata for embedded chunks"
  - "Context routing across multiple knowledge sources"
  - "Knowledge graph over documents"
  - "Port Religion DB patterns to Hermes"
  - "Structured skill taxonomy"
  - "Agent context as a layered corpus"
related_skills:
  - hindsight-stack-operations
  - graphiti-mcp-setup
  - knowledge-graph-corpus-pipeline
  - hermes-memory-surface-selection
  - evaluation-driven-development
platforms: [linux, macos, windows]
version: 1.1.0
author: Hermes Agent
license: MIT
---

# Knowledge Corpus Architecture

Derived from the Comparative Religion DB at ~/Religion — a 66,955-chunk,
3-collection, RDF-ontologised, graph-augmented vectorstore spanning 116
primary texts, native-language originals, and Jungian/comparative secondary
literature. The architectural patterns here are domain-agnostic and directly
applicable to any Hermes agent knowledge corpus.

## The Reference Architecture

The Religion DB uses THREE orthogonal knowledge layers:

```
Layer 1: Chunked Vectorstore (ChromaDB)
  Three collections with independent schemas:
  - sacred_texts (28,701 chunks)  — primary English translations
  - religious_texts (25,507 chunks) — native-language originals
  - secondary_literature (12,747 chunks) — analytical/commentary layer

Layer 2: Knowledge Graph (JSON + RDF/TTL)
  Nodes: ReligiousText, Deity, NarrativeMotif, Concept, Tradition, MythologicalFigure
  Edges: containsMotif, hasFigure, fromTradition, cognateOf, sharesConcept,
         strongMotif, featuresDeity, deityFunctionOf, influencedBy, precededBy

Layer 3: Taxonomy / Ontology
  motif_taxonomy.py: 65 structured motifs with Thompson codes + keyword lists
  myth_ontology.ttl: OWL classes, object properties, datatype properties
  myth_knowledge_graph.ttl: full RDF representation of all entities
```

This is a NEUROSYMBOLIC architecture: dense vector retrieval (fast, recall-oriented)
+ symbolic graph traversal (precise, relation-aware) + structured taxonomy extraction.

## Mapping to Hermes Agent Context

The same layered pattern maps directly to Hermes:

| Religion DB Layer | Religion Entity Type | Hermes Equivalent |
|---|---|---|
| sacred_texts collection | ReligiousText (primary) | Skills (authoritative procedures) |
| secondary_literature coll | Analytical commentary | Session transcripts (retrospective) |
| religious_texts coll | Native-language originals | Raw source docs / ingested PDFs |
| Knowledge graph nodes | Deity, Figure, Motif | Graphiti entities (person, concept, fact) |
| Knowledge graph edges | containsMotif, cognateOf | Graphiti edges (relates_to, is_instance_of) |
| Motif taxonomy | 65 motifs + Thompson codes | Skill taxonomy + trigger categories |
| OWL ontology | Class hierarchy + OPs | Graphiti entity type schema |
| Tradition grouping | hinduism, celtic, etc. | Skill categories (devops, research, etc.) |
| Layer routing | sacred vs secondary | Hermes memory surface selection |

## Core Design Principles

### 1. Separate collections by EPISTEMIC FUNCTION, not just topic

Don't dump everything into one collection. The Religion DB separates:
- Primary sources (sacred_texts): authoritative, high-trust
- Secondary literature: analytical, medium-trust, has analytical_categories metadata
- Native language: precision layer, only query when translation may lose meaning

In Hermes terms: skills (procedural authority), sessions (retrospective), Hindsight
(factual assertions), and external docs each serve different epistemic functions.
Never mix them into one retrieval pool — the metadata schemas are different enough
that mixed results confuse ranking.

### 2. Rich metadata is the primary ranking signal

Every chunk has 12+ metadata fields. This enables:
- Filter before embed: `where={"tradition": "hinduism"}` narrows search space
- Hybrid ranking: combine semantic score with metadata match
- Structured extraction: motif_ids, archetype_ids fields enable graph traversal
  from a retrieved chunk

Key metadata schema for a knowledge corpus chunk:
```json
{
    "text_id": "tradition_TitleSlug",
    "tradition": "hinduism",          # top-level category
    "title": "Bhagavad Gita",
    "original_language": "Sanskrit",
    "approx_date": "400-200 BCE",
    "text_type": "scripture",         # scripture / mythology / commentary / ritual
    "canonical": True,
    "source_url": "...",
    "chunk_index": 42,
    "total_chunks": 380,
    "chapter_hint": "Chapter 6",
    # secondary_literature extras:
    "author": "C.G. Jung",
    "analytical_categories": ["shadow", "individuation"],
    "archetype_ids": ["shadow", "anima"],
    "motif_ids": ["hero_journey", "underworld_descent"],
    "layer": "secondary_literature",
}
```

## Systematic Chunking Investigation: Paragraph Group Chunking wins across domains (arXiv 2603.06976)

36 chunking methods, 1,080 configurations, measured by nDCG@5:
- **Paragraph Group Chunking = best overall: nDCG@5 0.459 vs. 0.244 baseline = ~10x precision gain**
- Domain-specific optimal strategies:
  - Legal / math → paragraph grouping (preserves argument/proof structure)
  - Biology / physics → dynamic token sizing (variable content density needs adaptive windows)
  - General text → paragraph group with moderate overlap (50 tokens)

Practical ordering for Hermes chunking decisions:
```
1. Try paragraph group chunking first (universal winner)
2. If document is legal/mathematical → enforce paragraph boundaries strictly (no mid-para splits)
3. If document is bio/physics/technical → switch to dynamic token sizing (measure entropy per section)
4. Evaluate using the 5-metric framework (RC/ICC/DCC/BI/SC) — if BI score < 0.7, chunk at block boundaries
5. Never use fixed-size token windows without paragraph boundary enforcement
```

Complementary finding (arXiv 2602.16974 — "Beyond Chunk-Then-Embed"):
- Structure-based chunking > LLM-guided for in-corpus retrieval
- LumberChunker is best for in-document retrieval (where structural boundaries matter most)
- This reinforces: RAGFlow's template-based structural approach beats semantic/LLM chunking

Non-English verdict: chunking strategy is an **English-language research monopoly** — no
independent Chinese/Japanese/Korean/Russian/German/French academic chunking research found.
The 2603.06976 paper is the definitive empirical reference; use it as the authority.

### 3. Chunking strategy: overlap + paragraph-boundary + hard ceiling + domain templates + adaptive metric scoring

#### Adaptive Chunking 5-metric framework (arXiv 2603.25333, ekimetrics)
Standard one-size-fits-all chunking degrades RAG performance. This framework selects the
best chunking strategy per document by scoring 5 intrinsic metrics — no labels needed:

| Metric | What it measures | Implementation |
|--------|-----------------|----------------|
| RC — References Completeness | All in-chunk cross-references resolve within same chunk | check for "see section X" / "Table Y" refs that span chunk boundary |
| ICC — Intrachunk Cohesion | Semantic similarity between sentences within a chunk | mean cosine(adjacent sentence embeddings) |
| DCC — Document Contextual Coherence | Chunk's coherence with its surrounding document context | cosine(chunk_embedding, doc_centroid) |
| BI — Block Integrity | Structural blocks (tables, code, lists) are not split mid-block | detect block-start / block-end markers |
| SC — Size Compliance | Chunks fall within [min_tokens, max_tokens] | trivially checkable |

Score each candidate chunking strategy on these 5 metrics; pick the one with highest
combined score. Results: correctness 62-64% → 72% (+30% successfully answered questions)
on diverse legal/technical/social corpus. Code: https://github.com/ekimetrics/adaptive-chunking

Two new chunkers introduced (both useful for Religion DB and agent skill indexing):
- LLM-regex splitter: regex identifies semantic boundaries (section headers, paragraph
  breaks), LLM confirms boundary is a true topic shift
- Split-then-merge recursive splitter: split aggressively on whitespace, then merge
  adjacent segments whose embeddings are similar (cosine > threshold)

For Hermes corpus work: apply adaptive scoring when vectorizing a new document type.
For existing Religion DB pipeline: add ICC and BI checks to chunk_text() to auto-detect
bad chunks (ICC < 0.4 = incoherent, BI < 1.0 = split block).

#### S2 Chunking: layout-structure + spectral clustering (arXiv 2501.05485)
For PDFs and multi-column documents, semantic analysis alone misses spatial relationships.
S2 Chunking constructs a weighted graph of document elements using bounding box (bbox)
data + text embeddings, then clusters via spectral clustering. Key for:
- Multi-column research papers (columns cluster separately before being linearized)
- Tables and figures with captions (bbox proximity groups caption with table)
- Documents with diverse layouts (reports, articles, mixed-media)

Integrate with RAGFlow DeepDoc: DeepDoc provides bboxes; S2 Chunking provides the
spatial-aware clustering step that standard recursive splitters miss.

#### Intent-aware retrieval alignment (arXiv 2606.01240, KAIST/Sungkyunkwan)
Chunk boundaries should respect retrieval intent, not just document structure.
Key pattern: at index time, annotate chunks with their anticipated query intents
(factual lookup / comparison / explanation / procedural). At retrieval time, filter by
matching intent type before semantic search. Reduces noise from off-topic chunks that
happen to be semantically close.

### 3b. Legacy fixed-size chunking (Religion DB baseline)

Religion DB's chunk_text():
- Target: 500 words (~667 tokens)
- Overlap: 50 words (10%) — preserves sentence context across boundaries
- Paragraph-first split: prefer natural breaks
- Hard ceiling: 4500 words — stays under OpenAI's 8192-token limit
- Sentence-boundary sub-split: long paragraphs split at sentence boundaries

**RAGFlow template-based chunking improvement:** rather than a single fixed-size strategy,
use domain-specific templates. RAGFlow ships different chunkers per document type:

| Document type | Template behaviour |
|---|---|
| Academic paper | Split on section headers (Abstract/Introduction/Methods/Results/Conclusion) |
| Legal document | Preserve clause hierarchy; split on clause numbers |
| Resume/CV | Extract ~100 structured fields (name, education, experience, skills) as one chunk |
| Financial report | Table-aware: re-serialize table cells as natural-language sentences |
| General web page | Paragraph-based 500-word target (Religion DB default) |
| Code file | AST-aware: preserve function/class boundaries (CocoIndex pattern) |

Apply this table when building a corpus: match chunker to document type before ingestion.
Mixing document types in a single fixed-size chunker produces semantically incoherent chunks
at section boundaries — headers end up as orphan chunks that retrieve at wrong similarity.

This is better than character/token splitting because paragraph structure in religious
texts carries semantic completeness. Apply same logic to technical docs, legal text,
academic papers.

### 4. Taxonomy as structured retrieval backbone

The motif taxonomy (65 entries, each with label, Thompson code, description, keywords)
enables:
1. Keyword-to-motif extraction at ingest time (tag each chunk)
2. Motif-filtered search: "find all texts with earth_diver motif"
3. Cross-tradition comparison: same motif across different traditions
4. Knowledge graph population: motif nodes link to multiple texts

For Hermes: a similar skill trigger taxonomy can map skill content → abstract
task types, enabling semantic routing beyond keyword matching. See the
skill-family-router-maintenance skill for current Hermes skill routing.

### 5. Knowledge graph as structured recall layer

The JSON knowledge graph (ontology/graph.json) stores all nodes/edges produced
from motif extraction across all 116 texts. This enables:
- Graph traversal: given a text, find all related texts via shared motifs
- Cross-reference: "all texts featuring Flood Myth motif" via edge traversal
- Cognate detection: Thoth cognateOf Hermes — syncretism across traditions

Graphiti in Hermes serves the same function. The Religion DB pattern suggests:
when building any large corpus, immediately build an entity graph from the chunks
rather than waiting for an LLM to discover relations later. Structured extraction
at ingest time is dramatically cheaper than retroactive discovery.

### 6. Multi-collection routing protocol

When a query comes in:
1. Determine epistemic need: authoritative (skills), factual (Hindsight), 
   retrospective (sessions), or analytical (secondary_literature)
2. Filter by metadata if possible before embedding
3. Query the right collection first; fall back to others if needed
4. Merge results with provenance: always preserve source collection in result

```python
def route_query(query: str, need: str) -> list[Result]:
    if need == "authoritative_procedure":
        return query_collection("sacred_texts", query, filter={"canonical": True})
    elif need == "analytical_commentary":
        return query_collection("secondary_literature", query)
    elif need == "cross_tradition":
        # Query all three, merge and re-rank
        r1 = query_collection("sacred_texts", query)
        r2 = query_collection("religious_texts", query)
        return merge_rerank([r1, r2], by="distance")
```

## Building a New Corpus: Step-by-Step

### Phase 0: Define the taxonomy first
- List entity types (what kinds of things exist?)
- List relation types (how do they connect?)
- List attribute types (what metadata per chunk?)
- Pick top-level categories (like "traditions" — 20-30 is manageable)

### Phase 1: Ingest and chunk
```python
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./corpus_db")
ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=key, model_name="text-embedding-3-small"
)
coll = client.get_or_create_collection("primary_docs", embedding_function=ef)

for doc in documents:
    chunks = chunk_text(doc.text, chunk_size=500, overlap=50)
    coll.upsert(
        ids=[f"{doc.id}_chunk_{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[{
            "text_id": doc.id,
            "category": doc.category,
            "title": doc.title,
            "canonical": True,
            "chunk_index": i,
            "total_chunks": len(chunks),
        } for i in range(len(chunks))]
    )
```

### Phase 2: Taxonomy-based tagging at ingest
```python
def tag_chunk(chunk_text: str, taxonomy: dict) -> list[str]:
    """Return matched taxonomy IDs for a chunk."""
    matched = []
    lower = chunk_text.lower()
    for motif_id, motif in taxonomy.items():
        if any(kw.lower() in lower for kw in motif["keywords"]):
            matched.append(motif_id)
    return matched
```

### Phase 3: Build knowledge graph from tags
```python
import json
nodes = {}  # id -> {label, type, ...}
edges = []  # {source, relation, target}

for chunk_id, meta in all_chunk_metas.items():
    text_node_id = meta["text_id"]
    nodes[text_node_id] = {"type": "Document", "label": meta["title"]}
    for motif_id in meta.get("motif_ids", []):
        nodes[motif_id] = {"type": "Motif", "label": motif_id}
        edges.append({"source": text_node_id, "relation": "containsMotif", 
                      "target": motif_id})

graph = {"nodes": list(nodes.values()), "edges": edges}
json.dump(graph, open("corpus_graph.json", "w"))
```

### Phase 4: Query pattern — hybrid semantic + graph
```python
def hybrid_query(query: str, graph: dict, coll, n=5):
    # Step 1: semantic retrieval
    results = coll.query(query_texts=[query], n_results=n*2)
    
    # Step 2: graph expansion — find related chunks via shared motifs
    retrieved_doc_ids = {m["text_id"] for m in results["metadatas"][0]}
    related_via_graph = set()
    for edge in graph["edges"]:
        if edge["source"] in retrieved_doc_ids:
            # Find other docs with same motif
            for e2 in graph["edges"]:
                if e2["target"] == edge["target"] and e2["source"] != edge["source"]:
                    related_via_graph.add(e2["source"])
    
    # Step 3: fetch graph-expanded chunks and merge
    if related_via_graph:
        extra = coll.get(where={"text_id": {"$in": list(related_via_graph)}})
        # merge and re-rank by semantic distance
        ...
    return results
```

## MemGraphRAG — Production Validated 3-Layer Pattern (KDD 2026)

The Religion DB's 3-layer architecture (vectorstore + KG + ontology) now has direct academic
validation from MemGraphRAG (arXiv:2606.00610, KDD 2026, Xiamen University, 122 GitHub stars).

MemGraphRAG uses the same structure under different names:
- **Schema layer** = myth_ontology.ttl (abstract types and relation types)
- **Fact layer** = myth_knowledge_graph.ttl (concrete extracted triples)
- **Passage layer** = sacred_texts ChromaDB chunks (source text supporting facts)

### MemGraphRAG improvements worth porting:

1. **Ontology induction** — auto-abstracts concrete facts into reusable schemas using LLM;
   filters out low-frequency patterns that pollute the schema. Current Religion DB does this
   manually (motif_taxonomy.py). MemGraphRAG pipeline automates it.

2. **Conflict-aware construction** — detects hard conflicts between passage evidence:
   if two passages make contradictory claims about the same entity/relation, they form a
   "conflict group" and are explicitly flagged. Critical for mythology (cosmogonies across
   traditions are often contradictory by design). Current pipeline has NO conflict detection.

3. **Graph-enhanced retrieval** — combines embedding similarity AND Personalized PageRank
   over the entity graph. Same pattern as Religion DB's planned hybrid query; MemGraphRAG
   proves this is worth implementing.

### Quick setup (MemGraphRAG, locally)

```bash
git clone https://github.com/XMUDeepLIT/MemGraphRAG.git
cd MemGraphRAG && pip install -r requirements.txt
# Requires: OpenAI-compatible endpoint, local HuggingFace embedding model (bge-large-en)
# Chunk size 256, overlap 32 (smaller than Religion DB's 500-word chunks — tune per domain)
```

### Conflict detection pattern (portable to ~/Religion/scripts/)

```python
# Conceptual: after OpenIE extracts (head, relation, tail) triples from chunks
# Check for conflicts: same (head, relation) but contradictory tail values
from itertools import combinations

def detect_conflicts(triples: list[dict]) -> list[tuple]:
    """Return pairs of triples with same head+relation but conflicting tails."""
    conflicts = []
    for t1, t2 in combinations(triples, 2):
        if t1["head"] == t2["head"] and t1["relation"] == t2["relation"]:
            if t1["tail"] != t2["tail"]:
                conflicts.append((t1, t2))
    return conflicts
```

## Pitfalls

- **HNSW stack overflow on large graphs**: ChromaDB's hnswlib uses recursive DFS.
  On graphs > 50K vectors, the default 8MB stack overflows. Fix:
  ```python
  import resource
  soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
  resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
  ```
  Do this at module top-level, before any chromadb import.

- **ChromaDB cross-collection Rust compaction bug (<=1.5.9)**: Using two collections
  in the same PersistentClient path causes silent data corruption during compaction.
  Fix: use separate PersistentClient paths for logically separate collections
  (e.g. chroma_db_sacred/ vs chroma_db_new/).

- **Embedding model consistency**: All chunks and queries must use the same embedding
  model. If you change models, you must re-embed all chunks. Track model name in
  collection metadata.

- **Keyword-based taxonomy matching is noisy**: Keywords like "chaos" or "void" trigger
  false positives in technical text. Supplement with:
  - LLM-based classification at ingest (expensive but accurate)
  - Minimum keyword count threshold (at least 2 keywords must match)
  - Context window: check keyword in context, not just presence

- **Metadata filter before embed = big speed win**: ChromaDB supports `where=` filters
  that run before the HNSW search. Use them aggressively. A filter cutting 80% of
  chunks makes the embed search 5x faster.

- **Secondary literature should be last resort, not first**: Analytical commentary
  (Jung, Eliade, etc.) ABOUT a topic is different from primary sources ON it.
  Always surface primary sources first; secondary as a "and experts say..." layer.

- **RLIMIT_STACK must be raised BEFORE chromadb import** (not after):
  The hnswlib extension loads at import time. Raising stack after won't help.

## Meta-Chunking: perplexity-based adaptive segmentation (arXiv 2410.12788, IAAR-Shanghai)

IAAR-Shanghai (Jihao Zhao, Zhiyu Li, Bo Tang, Feiyu Xiong — Institute of AI Application
Research, Shanghai; same group as MemOS). GitHub: github.com/IAAR-Shanghai/Meta-Chunking

Two adaptive strategies using LLM logical perception:
1. **Perplexity Chunking**: segment text at points where the LLM's perplexity *spikes* —
   high perplexity = logical discontinuity = natural chunk boundary. Avoids mid-sentence
   or mid-argument splits that fixed-size windows cause.
2. **Margin Sampling Chunking**: segment at uncertainty peaks in next-token distribution —
   similar principle but uses token probability distribution rather than perplexity.

Global information compensation: 2-stage hierarchical summary + 3-stage chunk rewriting
(missing reflection → refinement → completion) to fill gaps at chunk boundaries.

Works with small models — cost-efficient with claude-haiku-4-5 as the perplexity probe.

```python
def perplexity_chunk(text: str, window: int = 100, threshold: float = 2.0) -> list[str]:
    """
    Segment text at perplexity spikes (logical discontinuities).
    Approximation: use sentence-boundary + semantic similarity drop as proxy.
    Full version: call LLM with log-probabilities to measure perplexity per sentence.
    """
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, prev_emb = [], [], None

    for sent in sentences:
        current.append(sent)
        if len(' '.join(current).split()) >= window:
            # Check if next sentence shifts topic (semantic discontinuity proxy)
            chunk_text = ' '.join(current)
            # Emit chunk, reset
            chunks.append(chunk_text)
            current = [sent]  # carry last sentence as context bridge

    if current:
        chunks.append(' '.join(current))
    return chunks

# Production use: call claude-haiku with logprobs endpoint, compute -sum(log P(token))
# per sentence, split at sentences where delta_perplexity > threshold (e.g. 2.0 nats)
```

Hermes application: apply perplexity chunking to session transcripts ingested into
Hindsight. Session dialogue has natural topic shifts — perplexity spikes at context
switches are better boundaries than fixed 512-token windows.

## MemGraphRAG: 3-layer schema-fact-passage KG with conflict detection (arXiv 2606.00610, KDD 2026)

Xiamen University (XMUDeepLIT), KDD 2026.
Three-layer architecture for knowledge-grounded RAG:
1. **Schema layer**: abstract ontology triples (head_type, relation, tail_type)
   induced from the fact layer. Low-frequency schemas are filtered.
2. **Fact layer**: concrete extracted triples (subject, predicate, object)
   with provenance to source passages.
3. **Passage layer**: original source text chunks, linked to their extracted facts.

**Conflict-aware construction**: detects "hard conflicts" (contradictory facts about
the same entity) during ingestion. Conflicting facts are flagged with `conflict=True`
before committing to the graph — not silently overwritten.

Mapping to Hermes stack:
- Schema layer → Graphiti `edge_types` (can be auto-discovered via AutoSchemaKG below)
- Fact layer → Graphiti episodes + entity edges
- Passage layer → Hindsight ChromaDB chunks (linked via `source_description` field)
- Conflict detection → check Graphiti for existing facts before `add_memory()`:
  ```python
  def conflict_aware_add(fact: str, entity: str) -> bool:
      existing = search_memory_facts(f"{entity} {fact[:50]}", max_facts=5)
      for e in existing:
          if semantic_contradiction(e['fact'], fact):
              # Flag conflict, don't silently overwrite
              add_memory(f"CONFLICT: {fact} contradicts {e['fact']}", ...)
              return False
      add_memory(fact, ...)
      return True
  ```

## AutoSchemaKG: fully autonomous KG construction without predefined schemas (HKUST)

AutoSchemaKG (HKUST-KnowComp/AutoSchemaKG, ATLAS framework) constructs knowledge graphs
from raw text with zero predefined schema. Key distinction from Cognee: AutoSchemaKG is
designed for billion-scale corpora and outputs a schema automatically from the data
itself. Architecture:

  1. Triple extraction: LLM extracts (subject, predicate, object) triples from text
  2. Schema induction: cluster predicates by embedding similarity → induced type hierarchy
  3. Entity linking: canonicalize entity mentions across documents
  4. Schema refinement: iterative loop merges near-duplicate relation types

Vs. manual taxonomy (current Religion DB approach):
- AutoSchemaKG: good for unknown/large domain; risks schema drift, needs post-curation
- Manual: better for well-understood domain (comparative religion) with established
  scholarly vocabulary (emic/etic terms, tradition-specific concepts)
- Hybrid (recommended): run AutoSchemaKG on a sample to discover emergent schema patterns,
  then merge with expert-curated schema

GitHub: https://github.com/HKUST-KnowComp/AutoSchemaKG

## Cognee: automated ontology induction pipeline (alternative to manual taxonomy)

Cognee (topoteretes/cognee) automates the Religion DB's most labor-intensive step:
building the taxonomy/ontology from data rather than hand-coding it.

**Core pipeline: `add(text) → cognify() → improve() → search()`**

```python
import cognee

# Ingest
await cognee.add(text_or_file, dataset_name="my-corpus")

# Cognify: runs NER + relation extraction + ontology induction automatically
# Under the hood: chunk → NER → relation extraction → ontology induction
# (cognitive-science grounded schema, not just typed triples)
# Produces: entity nodes + typed edges in a knowledge graph
await cognee.cognify()

# Enrich existing graph nodes with additional context
await cognee.improve()

# Search: routes to graph + vector automatically
results = await cognee.search("flood myth across traditions", query_type="INSIGHTS")
```

**Key differentiator vs manual taxonomy:** Cognee's `cognify()` runs LLM-based ontology
induction that generates domain-specific schemas from the data patterns it observes.
Rather than starting with a fixed motif taxonomy (as Religion DB does), it induces
the concept hierarchy from the text itself. Use this for corpora where you don't know
the right taxonomy upfront.

**Multi-store routing:** Cognee internally routes queries across KG, vector, and full-text
search automatically via a `recall()` function. This is the "unified retrieval" pattern
from MemOS — no manual surface selection needed.

**When to use Cognee vs manual taxonomy:**

| Situation | Approach |
|---|---|
| Known domain, rich prior taxonomy | Manual (Religion DB pattern) |
| New domain, unknown concept hierarchy | Cognee cognify() for induction |
| Need conflict detection across sources | MemGraphRAG conflict detection |
| Production corpus, fine-grained control | Manual + MemGraphRAG |

**Install:**
```bash
pip install cognee
# Requires: OpenAI API key (for LLM extraction), optional vector DB config
```

**Pitfall:** Cognee's induced ontology won't match domain-expert schema quality
for well-understood domains. For mythology, the motif_taxonomy.py approach with
Thompson Motif Index codes is more precise than LLM induction. Use Cognee for
bootstrapping a new domain before you know what the right taxonomy is.

## Applying This to Hermes Corpus Work

When building any Hermes-adjacent knowledge corpus:

1. Use three-layer structure: primary (authoritative), secondary (analytical),
   raw (unprocessed) — never a single flat collection
2. Add taxonomy tags at ingest — never retroactive
3. Build the knowledge graph alongside, not after
4. Store in ~/[domain]/chroma_db_[layer]/ with separate clients per layer
5. Use text-embedding-3-small (1536d, already used by Hindsight) for consistency
6. Route queries by epistemic need, not just topic
7. Use hybrid semantic + graph queries for anything needing cross-document relation

The key insight: dense retrieval handles "find me something like this";
knowledge graphs handle "find me things RELATED to this"; taxonomy handles
"find me things OF THIS TYPE". All three are needed for a production corpus.

## Aug 2026: lance-bundle for Portable Corpus Snapshots

`lance-bundle` (PyPI, Aug 2026): packs a LanceDB vectorstore + ONNX embedding model
as a single artifact registerable on HuggingFace Hub.
Use case: checkpoint and share corpus embeddings (e.g. religion KG, policy corpus)
without re-embedding from scratch on each machine.
```bash
pip install lance-bundle
lance-bundle pack --db ~/Religion/chroma_db --model text-embedding-3-small --out religion-corpus.bundle
lance-bundle push religion-corpus.bundle hf://amoni094/religion-corpus
```
Evaluate before adopting — beta; verify LanceDB compatibility with current schema.

## Belief Propagation for Skill Dependency Resolution (MacKay Ch 26)

**Theory:** Belief propagation (the sum-product algorithm) computes marginal distributions on graphical models by passing messages along graph edges. On a tree-structured graph, it is exact. On loopy graphs (DAGs with cycles), it is approximate but often accurate.

**Hermes rules:**
- Skill dependency resolution = belief propagation on the skill dependency graph: propagate uncertainty about which skills are needed through the `depends_on` edges.
- If skill A depends on skill B (A→B edge), loading A increases the probability that B is needed — the belief "B is relevant" propagates from A's relevance score.
- Operationally: when a skill's relevance score exceeds the routing threshold, also raise the relevance score of all its `depends_on` skills by 0.2 (message passing). Load any that exceed threshold after propagation.
- This prevents loading a skill without loading its declared prerequisites — a common routing gap at 150+ skills.

**Citation:** David MacKay — *Information Theory, Inference, and Learning Algorithms*, Ch 26 (Belief Propagation — the sum-product algorithm on graphical models).

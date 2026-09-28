---
name: experience-amortized-recall
description: >
  Use when improving recall quality in the unified-recall pipeline. Applies experience-amortized
  reranking: accumulate a lightweight feedback log per query cluster, then use that log to
  re-weight retrieval candidates at query time — without retraining the embedder.
triggers:
  - recall quality degrading over repeated similar queries
  - retrieval returning stale or low-relevance results
  - tuning unified-recall.py or hindsight recall pipeline
  - implementing retrieval feedback loops
  - amortizing retrieval experience across sessions
category: research
---

# Experience-Amortized Recall

## Theory

From arXiv 2608.22767 (Deng et al., 2026): "Experience-Amortized Retrieval Reranking" shows
that a retriever can accumulate query-level feedback signals across invocations without
retraining the embedder. A lightweight **experience log** (query cluster -> score delta map)
is maintained per cluster, and candidate scores are adjusted at query time using the log.

Key properties:
- No retraining: all adaptation is via log-based additive correction
- Cluster-stable: clusters formed by locality-sensitive hashing (LSH) on query embeddings
- Bounded: log is capped per cluster (circular buffer, FIFO eviction)
- Reversible: log can be cleared per cluster or globally without losing base retrieval

Formally: `score_adjusted(c, q) = score_base(c, q) + alpha * delta(cluster(q), c)`
where `delta` is the empirical mean feedback delta for (cluster, candidate_id) pairs.

## Hermes Application

Target: `~/.hermes/scripts/unified-recall.py` and the hindsight recall pipeline.

### Step 1: Add feedback log storage

```python
RECALL_LOG = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))) / 'cache' / 'recall-feedback.jsonl'
MAX_LOG_ENTRIES = 5000  # circular buffer
```

### Step 2: Record feedback after each recall invocation

When the user confirms a memory was useful (or it was unused for N turns), append:
```json
{"ts": 1234567, "cluster": "a3f2", "candidate_id": "mem_abc123", "delta": 0.2}
```

### Step 3: Apply log at query time

```python
def apply_experience_reranking(candidates, query_cluster, log_entries):
    deltas = {}
    for entry in log_entries:
        if entry['cluster'] == query_cluster:
            deltas[entry['candidate_id']] = deltas.get(entry['candidate_id'], 0) + entry['delta']
    n = max(sum(1 for e in log_entries if e['cluster'] == query_cluster), 1)
    for c in candidates:
        c['score'] += 0.1 * deltas.get(c['id'], 0) / n
    return sorted(candidates, key=lambda c: -c['score'])
```

### Step 4: Cluster assignment

Use first 4 hex chars of MD5(query_text.lower().strip()) as cluster ID.
This gives ~65k clusters with good locality.

## Pitfalls

- Do NOT let log grow unbounded: cap at MAX_LOG_ENTRIES, evict oldest
- Do NOT apply to safety-critical lookups (skill filtering, tool resolution)
- Alpha=0.1 is safe default; do not exceed 0.3 or base scores dominate
- Log file must use atomic writes (tmp → rename) to avoid corruption

## References

- arXiv 2608.22767: Experience-Amortized Retrieval Reranking (Deng et al., 2026)
- hindsight-stack-operations skill: existing recall pipeline
- unified-recall.py: target implementation file

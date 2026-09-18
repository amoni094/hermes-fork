# Bi-Temporal KG Design Pattern for Agent Memory (Engram, Aug 2026)

## Source
arXiv:2606.09900 — "Less Context, More Accuracy: A Bi-Temporal Memory Engine for LLM Agents"
Code: https://github.com/ly-wang19/engram
Result: **83.6% vs 73.2% full-context on LongMemEval_S (+10.4pp)** at 8× fewer tokens (9.6k vs 79k)

Key companion result — arXiv:2607.21962 (Veracium): at 9 weeks, provenance-typed graph (Graphiti)
reaches 90% while curated-map/flat memory drops from 96% to 72%. Use Graphiti for long-lived entities.

---

## Core Design: Bi-Temporal Data Model

Every fact has TWO timestamps:

| Timestamp | Meaning | SQL columns |
|-----------|---------|-------------|
| Valid time | When the fact was TRUE in the world | `valid_from`, `valid_to` |
| Transaction time | When the system LEARNED the fact | `recorded_at` |

This enables point-in-time queries ("what did we believe on 2026-08-01?") and temporal
fact verification without full history replay.

---

## Hindsight PostgreSQL Schema Upgrade

```sql
-- Run against the hindsight-embed-hermes PostgreSQL instance
-- Connection: PGPASSWORD=hindsight ~/.pg0/installation/18.1.0/bin/psql -h 127.0.0.1 -p 5432 -U hindsight -d hindsight

ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS valid_from  TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS valid_to    TIMESTAMPTZ DEFAULT NULL;  -- NULL = still valid
ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS superseded_by INTEGER REFERENCES memory_units(id) ON DELETE SET NULL;
ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS volatility_class TEXT DEFAULT 'stable'
    CHECK (volatility_class IN ('stable', 'volatile', 'ephemeral'));

CREATE INDEX IF NOT EXISTS idx_memory_valid_time ON memory_units (valid_from, valid_to);
```

**Safe to run while daemon is live** — all columns have defaults, so existing rows are unaffected.
After migration, `curl http://127.0.0.1:9177/health` should still return `{"status":"healthy"}`.

---

## Point-in-Time Query (as_of filter)

```python
def query_as_of(cursor, as_of: datetime, query_embedding, limit: int = 10):
    """Retrieve facts valid at a specific point in time."""
    cursor.execute("""
        SELECT id, text, valid_from, valid_to, superseded_by, volatility_class
        FROM memory_units
        WHERE valid_from <= %s
          AND (valid_to IS NULL OR valid_to > %s)
          AND superseded_by IS NULL
        ORDER BY recorded_at DESC
        LIMIT %s
    """, (as_of, as_of, limit))
    return cursor.fetchall()
```

---

## Contradiction Resolution: Invalidate, Don't Delete

When a new fact contradicts an existing one:

```python
def supersede_fact(cursor, old_id: int, new_content: str, session_id: str):
    """Close old fact's validity window, insert new one with supersession chain."""
    now = datetime.utcnow()
    
    # 1. Get the next ID (for the superseded_by forward reference)
    cursor.execute("SELECT nextval(pg_get_serial_sequence('memory_units', 'id'))")
    new_id = cursor.fetchone()[0]
    
    # 2. Close old fact
    cursor.execute("""
        UPDATE memory_units SET valid_to = %s, superseded_by = %s WHERE id = %s
    """, (now, new_id, old_id))
    
    # 3. Insert new fact with explicit ID
    cursor.execute("""
        INSERT INTO memory_units (id, text, valid_from, recorded_at, bank_id)
        VALUES (%s, %s, %s, %s, 'hermes')
    """, (new_id, new_content, now, now))
```

The old fact is preserved with `valid_to` set and `superseded_by` pointing to the new fact.
The full supersession chain is queryable: `SELECT * FROM memory_units WHERE superseded_by IS NOT NULL`.

---

## Volatility Classes

```python
VOLATILITY_EXPIRY = {
    'stable':    None,              # no expiry — facts like code architecture, doctrine
    'volatile':  timedelta(days=30), # API pricing, library versions, project status
    'ephemeral': timedelta(days=7),  # current task context, meeting notes, session-specific
}

def write_with_volatility(content: str, volatility: str = 'stable') -> dict:
    expiry_delta = VOLATILITY_EXPIRY.get(volatility)
    valid_to = (datetime.utcnow() + expiry_delta) if expiry_delta else None
    return {
        'content': content,
        'valid_from': datetime.utcnow(),
        'valid_to': valid_to,
        'recorded_at': datetime.utcnow(),
        'volatility_class': volatility,
    }
```

At write time: classify each memory as `stable|volatile|ephemeral`. A nightly cron can
enforce expiry by setting `valid_to = NOW()` on all rows where `valid_to < NOW()` and
`volatility_class IN ('volatile', 'ephemeral')`.

---

## Graphiti Edge Extension

Graphiti already stores `created_at` on edges. Extend by adding these properties to the
entity/edge metadata when calling `add_memory()`:

```python
await client.add_memory(
    messages=[{"role": "user", "content": "fact content"}],
    group_id="hermes",
    # Pass as custom metadata in the episode body:
    metadata={
        "valid_time_start": datetime.utcnow().isoformat(),
        "valid_time_end": None,          # None = still valid
        "transaction_time": datetime.utcnow().isoformat(),
        "superseded_by": None,           # set when this episode is superseded
        "volatility_class": "stable",
    }
)
```

When a fact is superseded: update the old episode's `superseded_by` field and set
`valid_time_end`. Use `search_memory_facts()` to find the old episode before superseding.

---

## Hybrid Read Path (Engram's Key Result)

Facts alone lose recall. Embeddings alone miss temporal/causal precision. Hybrid:

```python
def hybrid_retrieve(query: str, as_of: datetime = None, limit: int = 10):
    as_of = as_of or datetime.utcnow()
    
    # 1. Dense semantic search via Hindsight HTTP API
    dense = hindsight_recall(query, top_k=limit*2)
    
    # 2. Lexical FTS5 (SQLite) or pg_trgm (Postgres) for exact terms
    lexical = fts_search(query, limit=limit*2)
    
    # 3. Graph traversal via Graphiti
    graph = search_memory_facts(query, max_facts=limit)
    
    # 4. Apply bi-temporal as_of filter
    all_results = dense + lexical + graph
    valid = [r for r in all_results
             if r.valid_from <= as_of and (r.valid_to is None or r.valid_to > as_of)]
    
    # 5. Re-rank: 0.6·semantic + 0.25·recency + 0.15·access_frequency
    return rerank(valid, recency_weight=0.25, freq_weight=0.15)[:limit]
```

The 8× token reduction comes from this filtered, ranked slice replacing the full history replay.

---

## Cascade Invalidation (RECON benchmark insight, arXiv:2607.16716)

When a fact becomes invalid, downstream conclusions that cited it also need review:

```python
def cascade_invalidate(cursor, old_fact_id: int):
    """Flag all memories that cited old_fact_id as needing review."""
    cursor.execute("""
        UPDATE memory_units
        SET tags = tags || '{"needs_review": true}'::jsonb
        WHERE source_references @> %s::jsonb
          AND (valid_to IS NULL OR valid_to > NOW())
    """, (json.dumps([str(old_fact_id)]),))
    return cursor.rowcount  # number of downstream memories flagged
```

This requires a `source_references` JSONB column tracking which memory IDs each fact depends on.
Add at schema upgrade time: `ALTER TABLE memory_units ADD COLUMN IF NOT EXISTS source_references JSONB DEFAULT '[]';`

---

## Implementation Checklist

- [ ] Run schema migration SQL above on Hindsight PostgreSQL
- [ ] Add `volatility_class` tagging to l1-extract.py output
- [ ] Add `valid_from`/`valid_to` to cron_l1_retain.py ingestion call
- [ ] Implement `as_of()` query in Hindsight plugin wrapper
- [ ] Add `supersede_fact()` to l1-promote.py contradiction handler
- [ ] Add `source_references` column for cascade invalidation
- [ ] Extend Graphiti `add_memory()` calls with `valid_time_start`/`volatility_class` metadata
- [ ] Run Veracium harness at 1-week and 4-week marks to validate architecture choice

---

## Related Papers
- **Engram** (arXiv:2606.09900): the source of this design
- **Veracium** (arXiv:2607.21962): longitudinal benchmark confirming graph > flat at 9 weeks
- **RECON** (arXiv:2607.16716): cascade invalidation — what happens after a fact changes
- **PrimeKG-CL** (arXiv:2605.10529): `persistent/deprecated/added` stratification on biomedical KG
- **SEEM** (arXiv:2601.06411): Episodic Event Frames complement bi-temporal model

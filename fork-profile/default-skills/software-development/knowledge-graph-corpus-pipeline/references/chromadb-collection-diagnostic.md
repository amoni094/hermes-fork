# ChromaDB Collection Diagnostic Notes

Quick reference for diagnosing collection health issues.
Discovered/verified July 2026 on the Religion corpus.

---

## 1. Is the collection empty or stuck? WAL queue inspection

When `collection.count()` raises "Failed to apply logs to the metadata segment"
or returns 0 unexpectedly, inspect the SQLite WAL before assuming data loss:

```python
import sqlite3

def diagnose_collection(db_path, collection_name):
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # Check if collection exists
    cur.execute("SELECT id FROM collections WHERE name=?", (collection_name,))
    row = cur.fetchone()
    if not row:
        print(f"{collection_name}: NOT FOUND in this DB")
        conn.close(); return
    cid = row[0]

    # WAL queue — ANY rows here block all writes to the affected collection
    cur.execute("SELECT COUNT(*) FROM embeddings_queue")
    q_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM embeddings_queue WHERE topic LIKE ?", (f'%{cid}%',))
    q_this  = cur.fetchone()[0]
    print(f"WAL queue total={q_total}, for this collection={q_this}")

    # Segment row counts
    cur.execute("SELECT id, type FROM segments WHERE collection=?", (cid,))
    for seg_id, seg_type in cur.fetchall():
        cur.execute("SELECT COUNT(*) FROM embeddings WHERE segment_id=?", (seg_id,))
        cnt = cur.fetchone()[0]
        kind = "METADATA" if "metadata" in seg_type else "VECTOR"
        print(f"  {kind} segment {seg_id[:8]}: {cnt} rows")

    conn.close()

diagnose_collection('/path/to/chroma_db/chroma.sqlite3', 'sacred_texts')
```

**Interpretation:**
- `queue > 0` + `segment rows == 0`: collection was NEVER populated; stuck WAL prevents
  future writes. Data lives elsewhere. Fix: find the correct DB directory.
- `queue > 0` + `segment rows > 0`: partial write stuck. Data exists but count/query fail.
  Try `delete_collection()` + migrate from backup source.
- `queue == 0` + `segment rows == 0`: truly empty, no stuck WAL. Check if HNSW .bin files
  exist — if so, schema version mismatch (different ChromaDB version created the DB).

**Religion corpus case (Jul 2026):** `chroma_db/sacred_texts` had WAL=1 (a `test_zeus`
test write from 2026-07-23), segment rows=0. Collection was never populated. The real
28,701-chunk collection was always in `chroma_db_sacred`. The ChromaDB 1.5.x Rust
compactor then spread the error to ALL new collections created in the same DB instance,
including fresh empty ones — making migration via the Python API impossible.

---

## 2. Clearing a stuck WAL manually (last resort)

Only use after confirming the collection has 0 segment rows (i.e. no data to lose).
Always backup the sqlite3 file first.

```python
import sqlite3, shutil, os

db = '/path/to/chroma_db/chroma.sqlite3'
shutil.copy2(db, db + '.bak')

conn = sqlite3.connect(db)
cur  = conn.cursor()

# Get collection id
cur.execute("SELECT id FROM collections WHERE name='sacred_texts'")
cid = cur.fetchone()[0]

# Clear WAL entries for this collection
cur.execute("DELETE FROM embeddings_queue WHERE topic LIKE ?", (f'%{cid}%',))
print(f"Cleared {cur.rowcount} WAL entries")

# Also clear any orphaned HNSW dirs whose segments are empty
cur.execute("SELECT id FROM segments WHERE collection=?", (cid,))
for (seg_id,) in cur.fetchall():
    hnsw_dir = f'/path/to/chroma_db/{seg_id}'
    if os.path.isdir(hnsw_dir):
        shutil.rmtree(hnsw_dir)  # remove zero-data HNSW dir
        print(f"Removed HNSW dir {seg_id[:8]}")

# Remove the broken collection entirely
cur.execute("DELETE FROM segment_metadata WHERE segment_id IN (SELECT id FROM segments WHERE collection=?)", (cid,))
cur.execute("DELETE FROM segments WHERE collection=?", (cid,))
cur.execute("DELETE FROM collection_metadata WHERE collection_id=?", (cid,))
cur.execute("DELETE FROM collections WHERE id=?", (cid,))
conn.commit()
conn.close()
print("Collection removed — can now recreate from scratch OR use isolated DB")
```

WARNING: Even after this cleanup, ChromaDB 1.5.x Rust compactor may still refuse
new `add()` calls in the same Python process if other collections in that DB have
WAL history. See pitfall 29 in the main SKILL.md — isolated DB per collection is
the only reliable fix.

---

## 3. Routing multiple isolated DB directories: chroma_config.py

When collections live in separate DB directories, centralise routing in one module:

```python
# ~/Religion/scripts/chroma_config.py
from pathlib import Path
import chromadb

BASE_DIR = Path(__file__).parent.parent

COLLECTION_PATHS = {
    "sacred_texts":         BASE_DIR / "chroma_db_sacred",  # isolated (28,701 chunks)
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
        raise ValueError(f"Unknown collection: {name}. Known: {list(COLLECTION_PATHS)}")
    return get_client(path).get_collection(name)
```

Usage: `from chroma_config import get_collection` in all scripts.
When a collection migrates to a new isolated DB, update `COLLECTION_PATHS` once.

---

## 4. Chunk count vs file count mismatch (sacred_texts collection)

**Symptom**: vectorize_state.json shows 45 files processed for Aeneid,
but `sacred_texts` collection has only 1 chunk with title="Aeneid (Virgil)".
Same for Ovid Metamorphoses (55 files processed → 3 chunks).

**Diagnosis**: The sacred_texts vectorizer may use a title-based dedup key that
collapses all files for a single text into one chunk, or there's a write failure
that only persists the first batch. Distinguish by:

```python
import chromadb
client = chromadb.PersistentClient(path="/var/home/rainbow/Religion/chroma_db_sacred")

for coll_name in ["sacred_texts"]:
    coll = client.get_collection(coll_name)
    total = coll.count()
    by_title = {}
    for offset in range(0, min(total, 20000), 2000):
        for m in coll.get(limit=2000, offset=offset, include=["metadatas"])["metadatas"]:
            title = m.get("title", m.get("label", "?"))
            trad  = m.get("tradition", "?")
            by_title[(trad, title)] = by_title.get((trad, title), 0) + 1
    print(f"\n{coll_name} ({total} total):")
    for (trad, title), n in sorted(by_title.items(), key=lambda x: -x[1])[:20]:
        print(f"  {n:5d}  [{trad}] {title}")
```

**Note**: `religious_texts` (25,919 chunks in chroma_db) holds the native-language sources.
`sacred_texts` (28,701 chunks in chroma_db_sacred) holds English translations.

---

## 5. Checking stored EF config without triggering conflict

```python
coll = client.get_collection("my_collection")  # NO embedding_function arg
cfg  = coll._model.configuration_json
print("EF name:", cfg["embedding_function"]["name"])   # 'default' or 'openai'
print("Dimension:", coll._model.dimension)             # 1536 = OpenAI, 384 = default
```

If `name='default'` and `dimension=1536`: collection was initialized with
DefaultEmbeddingFunction but vectors written via OpenAI manually. EF name in
config is stale — safe to delete-and-recreate with OpenAI EF.

---

## 6. Listing all collections and their size + metadata

```python
for coll in client.list_collections():
    c = client.get_collection(coll.name)
    print(f"{coll.name}: {c.count()} chunks, meta={coll.metadata}")
```

---

## 7. Counting chunks per tradition across the whole corpus

```python
from collections import Counter
coll = client.get_collection("sacred_texts")
total = coll.count()
trad_counts = Counter()
for offset in range(0, total, 2000):
    for m in coll.get(limit=2000, offset=offset, include=["metadatas"])["metadatas"]:
        trad_counts[m.get("tradition", "unknown")] += 1
for trad, n in trad_counts.most_common():
    print(f"{n:5d}  {trad}")
```

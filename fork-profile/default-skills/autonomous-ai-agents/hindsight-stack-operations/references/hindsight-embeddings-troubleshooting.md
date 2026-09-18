# Hindsight Embeddings Troubleshooting — Session Log 2026-07-22

## Presenting error

Hindsight daemon was dead. `hermes memory status` showed "available ✓" but any
`hindsight_recall` call returned: `Failed to start daemon for profile 'hermes'`.

`~/.hindsight/profiles/hermes.log` tail showed:
```
ImportError: sentence-transformers is required for LocalSTEmbeddings.
    Install it with: pip install sentence-transformers
ERROR: Application startup failed. Exiting.
```

## Diagnosis path

1. `~/.hermes/hindsight/config.json` said `"embeddings_provider": "openai"`.
2. `~/.hindsight/profiles/hermes.env` had NO `HINDSIGHT_API_EMBEDDINGS_*` keys.
3. Source inspection of `daemon_embed_manager.py` (lines 440–480) revealed the
   `key_mapping` whitelist only covers LLM/log/timeout keys. `embeddings_provider`
   (simple format) is silently dropped. The second loop propagates `HINDSIGHT_*` keys only.
4. Daemon therefore received `DEFAULT_EMBEDDINGS_PROVIDER = "local"` and tried
   `LocalSTEmbeddings` → crashed importing sentence-transformers from the system Python
   (venv had it but the daemon wasn't using the venv's copy in the expected way).

## Fix applied

Added to `~/.hindsight/profiles/hermes.env`:
```
HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY=<sk-proj-...>
HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=text-embedding-3-small
HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS=1536
```

Killed zombie process + removed lock, triggered recall → daemon started.

## Second error: dimension mismatch

Daemon immediately hit a second error:
```
RuntimeError: Cannot change embedding dimension from 384 to 1536:
memory_units table contains 2326 rows with embeddings.
To change dimensions, you must either:
  1. Re-embed all data: DELETE FROM public.memory_units; then restart
  2. Use a model with 384-dimensional embeddings
```

The DB had 2,326 rows embedded at 384-dim (old local model). The migration code in
`migrations.py` raises rather than ALTER the column when rows have live vectors.

## Fix applied

```sql
UPDATE memory_units SET embedding = NULL;
```

This preserved all 2,326 `text` rows. Daemon restarted, ran migration
(`ALTER TABLE memory_units ALTER COLUMN embedding TYPE vector(1536)`), and began
re-embedding all rows via OpenAI text-embedding-3-small in background.

Verified:
- Column now `atttypmod = 1536`
- After ~5 min: all 2,326 rows re-embedded
- `hindsight_recall` returning results again

## Memory bank summary at time of fix

```
Banks:
  hermes          — 167 units
  hermes-default  — 2,159 units
Total: 2,326 units, 211 documents, 1,293 entities
Date range: 2026-06-06 to 2026-07-22
```

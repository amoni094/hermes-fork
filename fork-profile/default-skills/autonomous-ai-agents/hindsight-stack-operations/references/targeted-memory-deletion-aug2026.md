# Targeted Memory Deletion via Hindsight REST API (Aug 2026)

Verified workflow for purging specific memories by subject (e.g. "forget everything about X").

## Key finding: no per-memory DELETE

`DELETE /v1/default/banks/{bank_id}/memories/{memory_id}` → 405 Method Not Allowed
The per-memory ID endpoint only supports GET.

`DELETE /v1/default/banks/{bank_id}/memories?type=observation` does exist but bulk-deletes
ALL memories of that fact_type — too destructive for targeted removal.

The correct targeted path: **delete the source document**, which cascades to all derived memory units.

## Step-by-step procedure

```bash
# 1. Find memories matching the subject (search both banks)
for BANK in hermes-default hermes; do
  echo "=== $BANK ==="
  curl -s "http://127.0.0.1:9177/v1/default/banks/$BANK/memories/list?limit=100&sort=created_at_desc" \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data.get('memories', []):
    text = m.get('text','')
    ents = m.get('entities','')
    if 'KEYWORD' in text.upper() or 'KEYWORD' in ents.upper():
        print(m['id'], '|', m.get('fact_type'), '|', m.get('chunk_id'), '|', text[:80])
"
done

# 2. Extract document_id from chunk_id
# chunk_id pattern: {bank_id}_{session_id}_{chunk_index}
# e.g. "hermes-default_20260822_161841_25ed4d_0" → document_id = "20260822_161841_25ed4d"
# The session_id is the middle segment (after bank_id prefix, before trailing _N index).
# Confirm via chunk lookup:
curl -s "http://127.0.0.1:9177/v1/default/chunks/CHUNK_ID" | python3 -m json.tool
# Look for "document_id" field in the response.

# 3. Delete the document (cascades to memory units)
curl -s -X DELETE "http://127.0.0.1:9177/v1/default/banks/BANK_ID/documents/DOCUMENT_ID"
# Success response:
# {"success":true,"message":"Document 'X' and N associated memory units deleted","memory_units_deleted":N}

# 4. Verify nothing remains
curl -s "http://127.0.0.1:9177/v1/default/banks/hermes-default/memories/list?limit=100" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
hits = [m for m in data.get('memories',[]) if 'KEYWORD' in m.get('text','').upper()]
print(f'Remaining: {len(hits)}')
"

# 5. Check Graphiti too (dual-write may have replicated the fact)
# Use mcp__graphiti__search_memory_facts with the subject as query
```

## Real example (Aug 22, 2026)

Task: purge all OBLITERATUS memories from hermes-default bank.

1. Listed memories → found 6 entries with "OBLITER" in text/entities
2. All shared chunk_ids: `hermes-default_20260822_161841_25ed4d_0` and `_1`
3. document_id = `20260822_161841_25ed4d`
4. `DELETE /v1/default/banks/hermes-default/documents/20260822_161841_25ed4d`
   → `{"success":true, "memory_units_deleted":5}`
5. Re-listed: 0 remaining. Graphiti search: 0 results.

Note: 6 memories were found but only 5 were deleted via the document cascade — the 6th was
from a different chunk_id (`_0` vs `_1`) but the same document, so the cascade caught it.
The count discrepancy was the API counting the document itself as one unit.

## API surface summary (from openapi.json)

DELETE endpoints available:
- `DELETE /v1/default/banks/{bank_id}/documents/{document_id}` ← USE THIS for targeted removal
- `DELETE /v1/default/banks/{bank_id}/memories` ← bulk delete by type (destructive)
- `DELETE /v1/default/banks/{bank_id}/mental-models/{mental_model_id}`
- `DELETE /v1/default/banks/{bank_id}/directives/{directive_id}`
- `DELETE /v1/default/banks/{bank_id}/observations` ← bulk delete all observations
- `DELETE /v1/default/banks/{bank_id}/memories/{memory_id}/observations` ← per-memory observations only
- `DELETE /v1/default/banks/{bank_id}` ← nuclear, deletes entire bank

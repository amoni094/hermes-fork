# Hindsight Stall Diagnosis — 2026-08-30

## Session context
User reported: "this session stalled." Diagnosed via errors.log → daemon.log → config.json.
Root cause: `mode=local_embedded` in config.json causing 10s timeout every turn on Silverblue.

## Diagnosis decision tree (proven path)

```
1. grep 'Failed to start daemon\|sync_turn failed' ~/.hermes/logs/errors.log | tail -20
   → Repeated entries = Hindsight stall (not model/network)
   → Timestamps on every turn = per-turn overhead, not transient

2. tail -30 ~/.hindsight/daemon.log
   → Look for: 'Starting embedded PostgreSQL', 'Read-only file system'
   → If present: mode=local_embedded is wrong on this host

3. python3 -c "import json; c=json.load(open('/var/home/rainbow/.hermes/hindsight/config.json')); print(c['mode'])"
   → 'local_embedded' → apply Pitfall 10 fix
   → 'api' → check api_url and curl /health

4. curl -sf http://127.0.0.1:9177/health
   → healthy → config.json mode mismatch (Pitfall 10)
   → connection refused → service down (see health check section)
```

## Fix applied
Changed `~/.hermes/hindsight/config.json`:
- `"mode": "local_embedded"` → `"mode": "api"`
- Added `"api_url": "http://127.0.0.1:9177"`

Verification: `curl /health` 200, recall round-trip returned 60 results (budget=low, ~13s).

## Other errors found (non-stall, already resolved)
- grok-4.6 SSE stalls (2026-08-29 18:14–19:18): xAI provider-side, resolved without intervention
- hindsight_recall 404 attempt: URL had `/v1/hermes-default/banks/...` instead of `/v1/default/banks/...`
  → Correct path: `/v1/default/banks/{bank_id}/memories/recall` (`default` is literal, not profile name)

## Recall latency baseline (healthy, api mode)
- budget=low: ~13s round-trip, 60 results
- /health: immediate
- /banks list: immediate
- First recall after service restart: may take 30-90s (model load)

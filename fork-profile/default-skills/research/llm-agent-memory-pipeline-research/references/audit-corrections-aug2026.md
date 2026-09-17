# Audit Corrections — Aug 2026

Corrections identified during memory layer audit (2026-08-13). These are divergences
between what the SKILL.md documents and what the live code actually does.

## CORRECTION 1: Retention score formula (Priority 2, item 5)

**Documented in SKILL.md:**
> "compute_retention_score() uses Ebbinghaus formula (confidence × e^(-days/30) × log(1+access_count))"

**Actual implementation (l1-promote.py lines ~420–432):**
```python
def compute_retention_score(score_3: int, fact_type: str, recurrences: int) -> float:
    base = score_3 / 3.0
    type_boost = 0.15 if fact_type in ("correction", "outcome") else 0.0
    recur_boost = min(0.20, (max(0, recurrences - 2)) * 0.05)
    return min(1.0, base + type_boost + recur_boost)
```

This is a static linear RUQ sum. There is no `days` parameter, no exponential decay,
and no `access_count` read from Hindsight. The Ebbinghaus formula from arXiv:2604.04514
is the research *target* for a future upgrade, not the current implementation.

**When updating the roadmap, mark item 5 as:**
> "✅ PARTIAL — retention score is written, but uses linear RUQ sum (not Ebbinghaus).
> Full Ebbinghaus requires: (a) reading `days_old` from `valid_from`, (b) reading
> `access_count` from Hindsight (blocked by BUG C1 — PATCH endpoint missing)."

## CORRECTION 2: Dedup `access_count` increment is a no-op (Priority 1, item 1)

**Documented:**
> "cosine ≥ 0.92 → skip + increment `access_count` on existing memory"

**Actual:** `hindsight_patch_metadata()` is called with `{"last_accessed": now, "dedup_hit": True}`,
but PATCH on `/v1/default/banks/{bank_id}/memories/{memory_id}` returns 405 (Method Not Allowed).
The access_count is never incremented. The temporal reranking stub is therefore also non-functional —
`last_accessed` and `access_count` fields written to staging.md on dedup hits are never persisted
to Hindsight.

## CORRECTION 3: Contradiction supersede metadata is a no-op (Priority 1, item 4)

**Documented:**
> "`valid_to` + `superseded_by` set by contradiction_check() when NLI confidence ≥ 0.75"

**Actual:** These fields are written via `hindsight_patch_metadata()` which calls the 405-returning
PATCH endpoint. The old memory's `valid_to` is never updated. The new fact's `supersedes_id`
IS written to staging.md (as `[supersedes=<id>]`), but this staging field is also never forwarded
to Hindsight by the cron prompt.

## CORRECTION 4: Interference penalty is a no-op (Priority 2, item 6)

**Documented:**
> "0.50–0.75 → interference penalty only (access_count-- on old memory)"

**Actual:** The interference path calls `hindsight_patch_metadata(contradicted_id, {"interference_count": "increment", ...})`.
Two problems:
1. PATCH endpoint returns 405 (same as C1/C2 above)
2. The value `"increment"` is a string sentinel, not a numeric decrement — it assumes a
   downstream aggregator that does not exist

## CORRECTION 5: `"observation"` type accepted by cron prompt but rejected by l1-promote.py

l1-promote.py VALID_TYPES (line ~347): `{"fact", "correction", "outcome", "preference", "reasoning"}`

The l1-hindsight-promote cron prompt lists `[type=observation]` as a valid parse target.
If a staging.md line ever contains `[type=observation]`, l1-promote would have already
silently mapped it to `"fact"` during scoring — the cron won't see `observation` in practice,
but the vocabulary is out of sync.

## Status of Priority 3 items (not started)

- Item 9 (query-type routing): not implemented
- Item 10 (semantic-shift trigger): not implemented
- Item 11 (three-tier consolidation): not implemented
- Item 12 (Graphiti bi-temporal entity layer): source_type tagging implemented (write-side only);
  retrieval weighting not implemented; no PATCH endpoint for updating Hindsight metadata

## PSE Retrieval Gap

source_type tags (internal=1.0, cron=0.7, external=0.4) are written to Graphiti episodes.
No retrieval consumer applies these weights. The PSE mitigation (arXiv:2608.07952) is
write-side complete but read-side unimplemented.

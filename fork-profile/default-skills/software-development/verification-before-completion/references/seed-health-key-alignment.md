# Seed health key alignment

Use this when a cache/seed job reports success but the app health endpoint still shows `STALE_SEED` or `EMPTY`.

## Fast check
1. Read the health endpoint and note the exact failing check name.
2. Inspect the health source to find:
   - the canonical data key
   - the freshness/meta key (`seed-meta:*` or equivalent)
3. Inspect the seeder/helper invocation that determines where metadata is written.
4. Read back both keys directly from the backing store.
5. Re-run health after the seed.

## What to look for
- Main payload key exists and has fresh data.
- Expected freshness/meta key is missing or written under a sibling name.
- The mismatch often comes from helper arguments like `runSeed(domain, resource, ...)` where `domain/resource` controls `seed-meta:<domain>:<resource>`.

## Example pattern
Health expects:
- canonical: `market:stocks-bootstrap:v1`
- meta: `seed-meta:market:stocks`

Seeder accidentally writes:
- canonical: `market:stocks-bootstrap:v1`
- meta: `seed-meta:market:quotes`

Result:
- payload verification passes
- health remains stale/empty
- root cause is naming-contract drift, not a failed fetch

## Fix shape
- Align the seeder/helper naming with the health contract.
- Re-run the seeder.
- Verify three things before claiming success:
  - canonical key exists
  - expected meta key now exists and is fresh
  - health endpoint flips to OK

## Why this belongs in verification
This is not just a debugging trick. It prevents false completion claims after successful writes when the user asked for live health verification, not just payload existence.
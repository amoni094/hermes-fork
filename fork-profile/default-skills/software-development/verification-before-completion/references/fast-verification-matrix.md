# Fast Verification Matrix

Use this as the quick routing table when the full `verification-before-completion` skill feels too heavy.

## Claim -> proof
- tests pass -> run the exact test command now
- build succeeds -> run the build now
- file/config changed -> read it back or diff it
- service running -> health check / port / process / logs
- delegated task succeeded -> independently inspect the artifact
- cron/job configured -> inspect cron/job state directly
- recommendation/ranking fixed -> verify the live output surface, not just helper logic

## Default finish line
1. Restate the claim.
2. Run the narrowest proof.
3. If a child/background worker touched it, verify independently.
4. End with `Verified by:`.

---
name: external-signal-pipeline-recovery
description: Recover news/social/market signal pipelines when upstream anti-bot, credential gaps, or environment asymmetry break one leg of the feed.
---

When to use
- A monitor or briefing pipeline depends on social/news/vendor feeds and one feed goes EMPTY, SEED_ERROR, or stale.
- A containerized worker cannot fetch upstream data reliably, but the host/browser session may still have access.
- You need to restore service health quickly without pretending the root cause is fully fixed.

Core workflow
1. Split the pipeline into layers.
   - Collector acquisition
   - Seed/envelope write path
   - Downstream health/read model
   - User-facing outputs
2. Verify each layer independently.
   - Check whether the collector has data.
   - Check whether the seed key is written.
   - Check whether health status changes after reseeding.
   - Report partial recovery explicitly.
3. Compare environments before changing code.
   - Test host vs container reachability separately.
   - Check whether browser-backed host scripts can access content that headless/container fetches cannot.
   - Treat environment asymmetry as a first-class debugging branch, not noise.
4. Prefer graceful fallback over hard failure.
   - Keep vendor/API/OAuth paths when available.
   - Add a fallback parser or alternate acquisition path when the primary source is blocked.
   - If only one environment can fetch the source, use a host-side emergency reseed path to restore health while you continue root-cause work.
5. Preserve envelope/schema compatibility.
   - Match the existing Redis/seed envelope shape exactly.
   - Reuse the same keys, recordCount semantics, and fetchedAt/state metadata expected by downstream health checks.
6. Verify per-dataset, not just globally.
   - One feed recovering does not mean adjacent feeds recovered.
   - Confirm each health check separately (example: socialVelocity OK while wsbTickers remains EMPTY_DATA).
7. Report honestly.
   - Say which datasets are recovered, which remain degraded, and why.
   - Do not collapse “partial mitigation” into “fixed”.

Pitfalls
- Restarting a worker is not verification; inspect the downstream health fields after restart.
- Anti-bot/verification pages can masquerade as 200 OK HTML. Validate payload shape, not just status code.
- A host/browser-backed script may succeed where container fetches fail; do not assume parity.
- Emergency reseeders should restore the canonical key shape, not invent a parallel format.
- If the fallback yields too little or wrong-category data, mark that dataset degraded instead of padding with junk.

Host-vs-container recovery pattern
- Probe the same source from both environments.
- If host succeeds and container is challenged, keep the main worker patch small and add a host-side reseed utility for fast recovery.
- Use the reseed utility only to restore canonical seed keys; avoid creating a second downstream contract.
- After reseeding, verify exact health fields and record counts.

## Auxiliary signal inputs for dashboards and monitoring pipelines

When the user explicitly wants enrichment from local retrieval/monitoring systems such as Firecrawl or WorldMonitor, treat them as **relevant inputs**, but not as mandatory single points of failure unless the product contract says they are canonical.

Recommended pattern:
- Check Firecrawl availability first using the local root endpoint (`GET http://127.0.0.1:3002/`), not an assumed health route.
- Check WorldMonitor through its local health/signal surface or the local helper script already used in this workspace, rather than assuming the remote service is the active source.
- If either auxiliary source is down, keep the primary refresh or seed path alive when possible and mark the enrichment lane degraded instead of failing the whole pipeline.
- In the user-facing output, say clearly whether Firecrawl/WorldMonitor were live inputs, fallback/skipped inputs, or unavailable during the refresh.
- Do not silently claim those sources were used just because the code has an integration point; verify the live check in the current session.

Common pitfall:
- wiring auxiliary sources into the main refresh path so tightly that a Firecrawl or WorldMonitor outage breaks an otherwise healthy dashboard refresh. Prefer graceful degradation plus explicit source-health metadata.

## Verification checklist
- Collector returns live items from at least one trustworthy path.
- Seed key exists in the expected shape.
- Health endpoint flips from EMPTY/SEED_ERROR to OK for the recovered dataset.
- Adjacent datasets are checked independently and called out if still degraded.
- If Firecrawl or WorldMonitor were requested as inputs, their live status is checked and reported explicitly.
- Final user report distinguishes: root cause, mitigation, remaining gap.

Support files
- references/worldmonitor-reddit-recovery.md — concrete notes from a Reddit/socialVelocity recovery where host access and container access diverged.

# Hermes maintenance hygiene for laptop-class local-first setups

Use this when a Hermes installation already works but has accumulated drift.

Core pattern:
1. Run `hermes doctor --fix` first to migrate config and clear automatic issues.
2. Immediately verify with `hermes config check` and `hermes doctor`.
3. Inspect scheduled jobs. Fix retired/unsupported models before changing anything else.
4. For a failing cron job, update the model/provider, force a run, then verify `hermes cron list` shows the new last-run status.
5. If a watchdog/guard job is noisy or timing out, prefer pausing it first. Manual proof beats leaving broken automation enabled.
6. Write or refresh a short architecture note so future tuning is grounded in the actual stack, not guesswork.
7. Run light observability (`hermes insights`, `hermes status --all`, `hermes auth list`) instead of adding heavyweight telemetry by default.

Good fit for laptop-class hardware:
- remote main reasoning
- small remote auxiliary models
- local retrieval/search/docs
- avoid pushing routine background inference onto local Ollama unless there is a strong measured reason

Verification pattern:
- config migration: `hermes doctor --fix`, `hermes config check`, `hermes doctor`
- cron repair: update job -> run job -> `hermes cron list`
- architecture note: read back the written file
- final posture: `hermes status --all`

This pattern is especially useful when the temptation is to add more architecture because of a power-user showcase. Prefer healthier existing automation over more components.
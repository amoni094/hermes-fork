# Memory drift audit pattern

Use this when Hermes durable memory and a vault-facing `MEMORY.md` both exist and you want a cheap guard against duplication drift.

## Goal

Detect reintroduced overlap between:
- `~/.hermes/memories/MEMORY.md` — canonical agent-facing durable memory
- vault `MEMORY.md` — thin human-facing index

Also watch for nearby regressions that usually show up before exact duplication:
- near-duplicate phrasing of the same durable fact
- overgrowth in the live-sync note
- overgrowth in the daily-note `## Hermes Chat Sync` block

The audit should stay silent when the boundary is healthy and emit a short report only when attention is needed.

## Recommended shape

- Run as a small script-only cron job.
- Compare normalized line-level facts, not raw file hashes.
- Ignore headings, boundary disclaimers, and other structural lines.
- Treat exact overlaps as the first alert tier.
- Add a second tier for near-duplicates using a simple similarity matcher so wording drift is caught before exact duplication returns.
- Check note-size guardrails too:
  - vault `MEMORY.md` should stay thin
  - `Hermes Chat Live Sync.md` should stay rewrite-oriented rather than accreting dated sections
  - the daily-note sync block should remain short and skimmable
- Resolve the current daily note dynamically from the local date; do not hardcode a one-day file path.
- Write or rewrite a compact vault audit note that records last checked time, current status, and the layer-ownership policy.

## Threshold guidance

- Keep the daily-note audit threshold aligned with the sync policy itself. If the sync rule allows 3–5 bullets, do not alert at 4.
- Prefer conservative near-duplicate thresholds that catch obvious paraphrases without spamming on unrelated lines.
- Keep alerts small and actionable rather than exhaustive.

## Good output

- No stdout at all when no overlap or overgrowth is detected.
- Update the vault audit note on every run so humans can inspect the current status.
- If attention is needed:
  - identify the class of issue: exact overlap, near-duplicate, or overgrowth
  - print only the relevant lines/findings
  - remind the operator which layer owns the fact

## Why this matters

This prevents the vault index from slowly regrowing into a second canonical memory surface after a cleanup pass, and it catches note bloat before the live-sync layer becomes transcript-like again.

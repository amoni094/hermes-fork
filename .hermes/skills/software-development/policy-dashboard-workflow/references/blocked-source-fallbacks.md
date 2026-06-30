# Blocked source fallbacks for policy-dashboard

Use this when a monitored lane hits anti-bot or WAF protections.

## Durable pattern

- Prefer compliant fallback lanes:
  - search-indexed RSS/results pages
  - official feeds or official newsroom pages
  - explicit profile link-outs when post-body capture is not appropriate
- Reflect the fallback honestly in UI copy (`fallback lane`, `link-out only`, `search-indexed`) so users are not misled about what was actually fetched.
- Keep generated artifacts and UI labels aligned: if only profile links are present, do not surface them as `latest posts`.

## Session-learned applications

### Reuters
- Direct extraction may be blocked by anti-bot controls.
- Good fallback: a Reuters-specific search-indexed lane (for example Google News RSS scoped to `site:reuters.com`) with copy explaining why the fallback exists.

### Instagram / X / Facebook
- Treat as link-out-only in this dashboard when access depends on anti-bot-sensitive rendering or authenticated surfaces.
- The safe pattern is profile pills plus explanatory note, not scraped post bodies.

### Cloudflare / WAF-blocked pages
- When direct page fetch is blocked, prefer search-indexed or official-feed monitoring lanes and keep `sourceHealth` notes explicit about the retrieval mode.

## Commit hygiene reminder

When introducing fallback behavior, stage only the scoped script/UI/generated files that belong to the change. Leave unrelated repo diffs out of the commit unless the user explicitly asks for a sweep.
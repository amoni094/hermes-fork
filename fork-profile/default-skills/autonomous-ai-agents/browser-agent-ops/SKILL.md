---
name: browser-agent-ops
description: "Use when browser thrash or multi-step forms. Multi-act ops."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - Interactive browser task with multi-field forms or multi-step UI flows
  - Agent re-clicks the same control or thrash-loops on one page
  - Large browser/extract payloads are re-injected every turn
  - Choosing browser_exec vs per-action browser_click/type
  - Need page fingerprint / action-hash loop detection mid-browser-run
  - Prefer cheap page text search before LLM extract on an open page
  - NOT for zombie Chrome process cleanup (use agent-browser-troubleshooting)
  - NOT for 403/Cloudflare/paywall fetch recovery (use blocked-page-recovery)
  - NOT for nested browser-use.Agent or cloud browser as default
related_skills:
  - agent-browser-troubleshooting
  - blocked-page-recovery
  - computer-use
  - agent-runtime-loop-patterns
  - hermes-context-hygiene
  - firecrawl-stealth-fallback
metadata:
  hermes:
    tags: [browser, multi-act, loop-detection, action-result, agent-ops]
    related_skills:
      - agent-browser-troubleshooting
      - blocked-page-recovery
      - computer-use
      - agent-runtime-loop-patterns
      - hermes-context-hygiene
      - firecrawl-stealth-fallback
---

# Browser Agent Ops

## When to Use

Load this skill when an interactive browser run needs multi-field form batching,
soft thrash/loop detection, extract-once memory split, or cheap in-page search
before LLM extract. Do not use for zombie Chrome cleanup, 403/WAF recovery, or
desktop GUI (those have their own skills).

Operational patterns stolen from browser-use's *algorithms*, not its nested Agent.
Hermes already has `browser_*`, optional `browser_exec` (browser-use CLI backend),
camofox, stealth-mcp, and cua. This skill wires the missing *run discipline*.

Helper (tested): `python3 ~/.hermes/scripts/browser_act_guard.py`

## Decision ladder (cheap → expensive)

```
1. web_search / web_extract / firecrawl / defuddle     # read-only
2. blocked-page-recovery                              # 403/WAF/paywall copies
3. browser_navigate + snapshot + multi-act            # interactive local
4. browser_exec (if browser.backend=browser-use)      # scripted multi-step
5. camofox / stealth-mcp                              # bot walls
6. computer_use on real GUI browser                   # last resort native UI
```

Do **not** nest `browser_use.Agent` inside Hermes. Do **not** default to Browser Use cloud.

## 1. Multi-act (batch until page change)

One model turn per field is waste. Batch:

- Prefer `browser_exec` / a short agent-browser script for fill→fill→click submit.
- Cap ~5 actions per batch (`max_actions=5`).
- After each action, if the page fingerprint changes → stop the batch (nav/DOM change).

```bash
# After action i, decide early-stop
python3 ~/.hermes/scripts/browser_act_guard.py multi-act-stop \
  --prev-fp "$PREV_FP" --curr-fp "$CURR_FP" --index "$i" --max 5
```

Fingerprint:

```bash
python3 ~/.hermes/scripts/browser_act_guard.py fingerprint \
  --url "$URL" --count "$ELEMENT_COUNT" --text-file /tmp/snap.txt
# → {"fingerprint":"url|count|hash16", ...}
```

Sources for count/text: `browser_snapshot` line count or interactive element count;
`agent-browser get text body` / snapshot dump for content hash input.

## 2. Soft loop guard (steer → constrain → stop)

Not a hard process kill — escalating nudges when the same action hash repeats on a
stagnant page fingerprint.

```bash
STATE=/tmp/hermes-browser-loop-$SESSION.json   # per-session path
python3 ~/.hermes/scripts/browser_act_guard.py observe \
  --state-file "$STATE" \
  --action-json '{"type":"click","index":3}' \
  --fingerprint "$FP"
# read observation.nudge_level: none|soft|medium|hard
# hard.should_break=true → switch ladder, do not re-click
```

Thresholds (defaults): soft=2, medium=3, hard=5 same action; stagnant page (≥3) escalates to medium earlier.

Maps to `agent-runtime-loop-patterns` circuit-breaker rungs — this is the browser-specific detector.

## 3. ActionResult memory split

Large extracts must not reappear every later turn.

```bash
python3 ~/.hermes/scripts/browser_act_guard.py split \
  --content-file /tmp/extract.md \
  --long-term "found 12 products; currency=AUD" \
  --seen-content   # omit bulk content on subsequent turns
```

Contract:
- `extracted_content` — show **once** (or write to a file path and keep only the path)
- `long_term_memory` — ≤400 chars durable fact every later step
- `error` — separate from content

Pairs with `hermes-context-hygiene` (tool results are bulk; facts are cheap).

## 4. Cheap page search before LLM extract

On an already-open page, do not burn an extract LLM call to find a string:

```bash
# full-page text then local grep (prefer over LLM extract for string presence)
npx agent-browser get text body | rg -n "Order total|Invoice #"
# or JS boolean probe
npx agent-browser eval 'document.body.innerText.includes("Subscribe")'
# role/text find → action (action defaults to click if omitted)
npx agent-browser find role button click --name Submit
npx agent-browser find text "Sign in" click
```

Use LLM extract only after you know the region matters or structure is complex.

## 5. Pagination extract hygiene

When scraping page 2..N, pass already-collected keys/titles so you skip dupes.
Keep a JSONL/CSV in `/tmp` or workspace; before each page, check membership.
Do not re-summarize the full corpus each page — append + short long_term delta only.

## 6. Done-action anti-hallucination

When closing a browser task, report **only** what was observed this session
(snapshots, extracts, tool results). Do not invent from compacted memory or
fallback summaries. If unsure, say what was not verified.

## 7. Snapshot noise (light)

Not a full paint-order occlusion filter (that needs CDP geometry). Cheap chrome drop:

```bash
python3 ~/.hermes/scripts/browser_act_guard.py filter-snapshot \
  --text-file /tmp/snap.txt --max-lines 400
```

## Backend notes

| Mode | How |
|------|-----|
| Default local | `browser_*` via agent-browser |
| Scripted multi-step | `browser.backend: browser-use` → `browser_exec` |
| Cloud escape hatch | `browser.cloud_provider: browser-use` + `BROWSER_USE_API_KEY` only when local+camofox fail bot walls |

## Related failures (wrong skill)

| Symptom | Skill |
|---------|-------|
| Zombie headless Chrome / session desync | `agent-browser-troubleshooting` |
| 403 / Cloudflare / paywall on fetch | `blocked-page-recovery` |
| Desktop GUI / non-web apps | `computer-use` |
| Generic retry thrash (non-browser) | `agent-runtime-loop-patterns` |

## Pitfalls

- Do not `pip install browser-use` to run a nested Agent loop inside Hermes.
- Do not treat loop-guard HARD as "kill Chrome" — change strategy; process cleanup is separate.
- Fingerprints need real page text; empty text still hashes stably but won't detect DOM text changes.
- Empty fingerprints never count as `page_changed` in multi-act-stop — always pass both prev and curr.
- Action hashes ignore unknown fields — pass `type`/`index`/`text`/`url` explicitly.
- `filter-snapshot` is heuristic; refs (`@eN` / `[N]`) are kept even on cookie-ish labels.
- Helper is opt-in discipline — nothing auto-wires into `browser_click`; call observe/split explicitly or via this skill.

## Verification

```bash
pytest -q ~/.hermes/scripts/test_browser_act_guard.py
python3 ~/.hermes/scripts/browser_act_guard.py action-hash \
  --json '{"type":"click","index":1}'
```

Expect pytest exit 0 and a JSON object with `hash`.

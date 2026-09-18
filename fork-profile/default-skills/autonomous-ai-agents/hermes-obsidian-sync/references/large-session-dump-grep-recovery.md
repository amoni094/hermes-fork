# Large Session-Dump Grep-First Recovery Pattern

When `session_search` returns a large result (>100KB) that exceeds read_file safety limits, avoid brute-reading from line 1. Instead, use `grep` to extract high-signal keywords first, then pivot to structured sources or read only the relevant section.

## When to apply this

- Session discovery returned "truncated" or large-file warning (>100KB)
- You need to know if a specific topic or durable change is in the session
- You're tempted to re-read with offset/limit (the pitfall pattern)

## How to apply

1. **Grep for high-signal keywords** (fast, no tool read-safety limits):
   ```bash
   grep -i "config\|cron\|patch\|commit\|write_file\|skill\|error\|fix\|deploy" /tmp/session-result-file.txt
   ```
   Also grep for domain-specific terms (e.g. "NICE\|PBAC\|HTA" for medical research, "postgres\|redis\|migration" for infra).

2. **Read the grep output** to identify line anchors or section boundaries where the relevant content appears.

3. **If grep finds the topic**, re-read only that specific line range using `read_file(offset=START_LINE, limit=RANGE)`.

4. **If grep finds nothing**, the session likely doesn't contain durable items for your question — move to other continuity sources (live-sync note, hint files, cron health check).

## Worked example (2026-07-04 14:22 AEST sync)

**Scenario**: `session_search(query="2026-07-04")` returned 132 KB with truncation warning. Need to check if any new durable items appeared after 10:03 AEST sync.

**Step 1: Grep for durable signals**
```bash
grep -iE "write_file|patch|commit|config|cron|fix|deploy|integration|endpoint" /tmp/session-result.txt
```

**Expected output** (if durable items exist):
```
... "function": {"name": "write_file", "arguments": "{...config..."}
... "function": {"name": "patch", "arguments": "{...skill..."}
... {"command": "git commit", ...}
```

**If grep returns nothing or only transient noise** (test output, error traces, cancelled operations):
→ No durable changes. Stop here. Move to hint-file checks or cron health as secondary verification.

**Step 2: If durable signals found, pinpoint the location**

Grep output showed line 450-470 contains a write_file call. Use:
```bash
read_file(path="/tmp/session-result.txt", offset=445, limit=50)
```

Extract the actual durable change, verify it's not superseded by later reverts, add to sync note if verified.

## Why this beats brute-reading

- Grep on a 132 KB file: <100ms
- First read attempt (line 1, limit 500): hits size limit, returns empty or partial
- Retry with offset/limit: still bounces if file is large enough; you're trapped in the loop
- Grep-first pivot: one fast scan, then targeted read only if signal found

## When NOT to use this

- Session result is already <50 KB: read directly
- You know the exact line number: jump to read_file with offset
- The session is a prior sync run (cron maintenance context): skip the grep and use the live-sync note as continuity instead

# Session DB: Raw SQLite URL/Link Recall

Use when `session_search` FTS returns 0 results despite sessions existing, or when
Hindsight is down and you need to recover research links from recent sessions.

## When to use

- User asks "recall all links/URLs from <timeframe>"
- `session_search(query="http links url")` returns 0 results (FTS not indexed or stale)
- Hindsight daemon is down and `hindsight_recall` fails
- Need to extract tool output (web_extract, web_search results) that was in past sessions

## AEST timezone note

`started_at` and `ended_at` in state.db are **Unix epoch floats in UTC**.
Convert AEST to UTC: subtract 10 hours (36000 seconds).
Example: Mon 12:33pm AEST = Mon 02:33 UTC

```python
import datetime
aest_dt = datetime.datetime(2026, 8, 10, 12, 33, 0)   # AEST time
cutoff_utc = aest_dt - datetime.timedelta(hours=10)    # → 02:33 UTC
cutoff_ts = cutoff_utc.timestamp()
```

## Full URL extraction pattern

```python
import sqlite3, datetime, re, json, os
from collections import defaultdict

db = sqlite3.connect(os.path.expanduser('~/.hermes/state.db'))

# --- 1. Set time window ---
# Adjust AEST offset: -10h for UTC+10
aest_start = datetime.datetime(2026, 8, 10, 12, 33, 0)
cutoff_ts = (aest_start - datetime.timedelta(hours=10)).timestamp()

# --- 2. Get relevant sessions ---
sessions = db.execute('''
    SELECT id, title, started_at FROM sessions
    WHERE started_at >= ? AND archived = 0
    ORDER BY started_at ASC
''', (cutoff_ts,)).fetchall()

# --- 3. URL regex ---
url_re = re.compile(r'https?://[^\s\'"<>\]\)]+')

# --- 4. Extract URLs ---
all_urls = {}   # url -> session_label

# Labels of sessions to skip (cron infrastructure noise)
skip_fragments = ['chat-sync', 'hindsight-promote', 'cron_']

for sid, title, ts in sessions:
    label = title or sid[:20]
    if any(s in label for s in skip_fragments):
        continue

    msgs = db.execute(
        'SELECT content FROM messages WHERE session_id = ? AND active = 1', (sid,)
    ).fetchall()

    for (content,) in msgs:
        text = content or ''
        # Content may be a JSON array of parts (multi-modal messages)
        if text.startswith('['):
            try:
                parts = json.loads(text)
                text = ' '.join(
                    p.get('text', '') if isinstance(p, dict) else str(p)
                    for p in parts
                )
            except Exception:
                pass
        for url in url_re.findall(text):
            url = url.rstrip('.,;:\'")')
            if url not in all_urls:
                all_urls[url] = label

# --- 5. Filter noise ---
# Remove localhost, internal services, image assets, navigation boilerplate
noise_patterns = [
    'localhost', '127.0.0.1', 'example.com',
    '/static/', '/_next/', '.png', '.svg', '.gif', '.jpg', '.ico',
    'arxiv.org/search/cs?searchtype=author',   # author search pages (not papers)
    'arxiv.org/list/', 'arxiv.org/prevnext',   # nav
    'arxiv.org/show-email', 'arxiv.org/auth/',
    'arxiv.org/src/', 'doi.org/10.48550',      # DOI redirect (same as abs page)
    'reddit.com/vote', 'reddit.com/hide',
    'news.ycombinator.com/vote', 'news.ycombinator.com/hide',
    'news.ycombinator.com/login', 'news.ycombinator.com/user?',
    'news.ycombinator.com/s.gif',
    'github.com/login', 'github.com/topics/',
    'github.com/contact/report',
]

filtered = {
    url: label for url, label in all_urls.items()
    if not any(n in url for n in noise_patterns)
}

# --- 6. Group by session for display ---
by_session = defaultdict(list)
for url, label in filtered.items():
    by_session[label].append(url)

for label in sorted(by_session):
    print(f"\n=== {label} ===")
    for u in by_session[label]:
        print(f"  {u}")

print(f"\nTotal: {len(filtered)} unique URLs across {len(by_session)} sessions")
```

## Tips

- `messages.content` is either a plain string or a JSON array of content blocks.
  Always try JSON parse when it starts with `[`.
- `messages.active = 1` filters out compacted/evicted messages. Use `active = 1`
  unless you specifically want to search compacted content.
- For very large sessions, add `AND role IN ('tool', 'assistant')` to skip user messages
  (URLs almost always appear in tool output or assistant responses).
- `messages.tool_name` can narrow to specific tools: `tool_name = 'web_extract'`
  gets only web extraction output; `tool_name = 'web_search'` gets search results.
- If deduplication across time windows matters, sort by `sessions.started_at` and use
  `all_urls[url] = (label, ts)` to keep the earliest occurrence.

## session_search FTS fallback (when it DOES work)

If `session_search` is returning 0 results unexpectedly, try:
1. `session_search(query="http link url research", role_filter="tool")` — tool output only
2. `session_search(query="arxiv.org", limit=10)` — known URL fragment
3. If both return 0: the FTS5 index may not have indexed recent sessions yet.
   Fall through to the SQLite pattern above.

#!/usr/bin/env python3
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOCIAL_SIGNALS = Path('/var/home/rainbow/.hermes/scripts/social_signals.py')
UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', 'http://127.0.0.1:8079/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')
ENV_FILE = Path('/tmp/worldmonitor/.env')
SOCIAL_KEY = 'intelligence:social:reddit:v1'
SOCIAL_META_KEY = 'seed-meta:intelligence:social-reddit'
WSB_KEY = 'intelligence:wsb-tickers:v1'
WSB_META_KEY = 'seed-meta:intelligence:wsb-tickers'
TTL_SOCIAL = 12 * 60 * 60
TTL_META = 7 * 24 * 60 * 60
DOLLAR_TICKER_RE = re.compile(r'\$([A-Za-z]{1,5}(?:[.-][A-Za-z]{1,2})?)\b')
TICKER_BLACKLIST = {
    'I','A','ALL','FOR','THE','CEO','GDP','IPO','SEC','FDA','IMF','ETF','ATH',
    'DD','YOLO','FOMO','FUD','HODL','WSB','USA','EU','UK','AI','EV','IT','OR',
    'AM','PM','ON','BE','SO','GO','AT','TO','UP','NO','IF','AS','BY','AN','DO',
    'IN','OF','IS','HAS','NEW','CFO','CTO','IRS','FBI','CIA','UN','WHO',
    'IMO','PSA','FYI','TL','DR','OP','OC','US','ER','RE','VS',
}


def sh(command: list[str]) -> str:
    p = subprocess.run(command, check=True, capture_output=True, text=True)
    return p.stdout


def load_env_file() -> None:
    global UPSTASH_URL, UPSTASH_TOKEN
    if (UPSTASH_TOKEN and UPSTASH_URL) or not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k == 'UPSTASH_REDIS_REST_URL' and v.strip():
            UPSTASH_URL = 'http://127.0.0.1:8079/'
        elif k == 'UPSTASH_REDIS_REST_TOKEN' and v.strip():
            UPSTASH_TOKEN = v.strip()


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def parse_created(v: str | None) -> int:
    if not v:
        return now_ms()
    return int(datetime.fromisoformat(v).timestamp() * 1000)


def redis_set(key: str, value: Any, ttl: int) -> None:
    body = json.dumps(['SET', key, json.dumps(value), 'EX', str(ttl)]).encode()
    headers = {'Content-Type': 'application/json'}
    if UPSTASH_TOKEN:
        headers['Authorization'] = f'Bearer {UPSTASH_TOKEN}'
    req = urllib.request.Request(
        UPSTASH_URL,
        data=body,
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status >= 300:
            raise RuntimeError(f'Upstash SET failed for {key}: HTTP {r.status}')


def envelope(data: Any, record_count: int, source_version: str) -> dict[str, Any]:
    return {
        '_seed': {
            'fetchedAt': now_ms(),
            'recordCount': record_count,
            'sourceVersion': source_version,
            'schemaVersion': 1,
            'state': 'OK',
        },
        'data': data,
    }


def build_social(reddit_items: list[dict[str, Any]]) -> dict[str, Any]:
    now = now_ms()
    posts = []
    for item in reddit_items:
        created = parse_created(item.get('created_at'))
        age_sec = max(1, (now - created) / 1000)
        recency = math.exp(-age_sec / (6 * 3600))
        score = int(item.get('score') or 0)
        comments = int(item.get('num_comments') or 0)
        velocity = round((math.log1p(max(score, 1)) * recency * 100) + (math.log1p(max(comments, 0)) * 8), 1)
        posts.append({
            'id': item['permalink'].rstrip('/').split('/')[-1],
            'title': item['title'][:300],
            'subreddit': item['subreddit'],
            'url': item['permalink'],
            'score': score,
            'upvoteRatio': 0,
            'numComments': comments,
            'velocityScore': velocity,
            'createdAt': created,
        })
    posts.sort(key=lambda x: x['velocityScore'], reverse=True)
    return {'posts': posts[:50], 'fetchedAt': now_ms()}


def build_wsb(reddit_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    ticker_map: dict[str, dict[str, Any]] = {}
    posts_scanned = 0
    for item in reddit_items:
        sub = str(item.get('subreddit', '')).lower()
        if sub not in {'wallstreetbets', 'stocks', 'investing'}:
            continue
        posts_scanned += 1
        text = f"{item.get('title','')} {item.get('url','')}"
        tickers = set()
        for raw in DOLLAR_TICKER_RE.findall(text):
            sym = raw.upper().replace('.', '-')
            if sym and sym not in TICKER_BLACKLIST:
                tickers.add(sym)
        for sym in tickers:
            e = ticker_map.setdefault(sym, {
                'symbol': sym,
                'mentionCount': 0,
                'postIds': set(),
                'totalScore': 0,
                'numComments': 0,
                'topPost': None,
                'subreddits': set(),
            })
            e['mentionCount'] += 1
            e['postIds'].add(item['permalink'])
            e['totalScore'] += int(item.get('score') or 0)
            e['numComments'] += int(item.get('num_comments') or 0)
            e['subreddits'].add(item.get('subreddit'))
            if not e['topPost'] or int(item.get('score') or 0) > e['topPost']['score']:
                e['topPost'] = {
                    'title': item.get('title', '')[:300],
                    'url': item.get('permalink'),
                    'score': int(item.get('score') or 0),
                    'subreddit': item.get('subreddit'),
                }
    if not ticker_map:
        return None
    tickers = []
    for e in ticker_map.values():
        unique_posts = len(e['postIds']) or 1
        tickers.append({
            'symbol': e['symbol'],
            'mentionCount': e['mentionCount'],
            'uniquePosts': unique_posts,
            'totalScore': e['totalScore'],
            'avgUpvoteRatio': 0,
            'topPost': e['topPost'],
            'subreddits': sorted(s for s in e['subreddits'] if s),
            'velocityScore': round(math.log1p(max(e['totalScore'], 1)) * e['mentionCount'] * 10, 1),
        })
    tickers.sort(key=lambda x: x['velocityScore'], reverse=True)
    return {
        'tickers': tickers[:50],
        'fetchedAt': now_ms(),
        'subredditsScanned': len({str(i.get('subreddit', '')).lower() for i in reddit_items if str(i.get('subreddit', '')).lower() in {'wallstreetbets', 'stocks', 'investing'}}),
        'postsScanned': posts_scanned,
    }


def main() -> int:
    load_env_file()
    if not SOCIAL_SIGNALS.exists():
        print('social_signals.py missing', file=sys.stderr)
        return 1
    raw = sh([str(SOCIAL_SIGNALS), '--limit', '100', '--json'])
    obj = json.loads(raw)
    reddit_items = obj.get('reddit', {}).get('items', [])
    if not reddit_items:
        raise RuntimeError(f'No reddit items returned: {obj.get("reddit", {}).get("error")}')

    social_payload = build_social(reddit_items)
    redis_set(SOCIAL_KEY, envelope(social_payload, len(social_payload['posts']), 'social-reddit-host-seed'), TTL_SOCIAL)
    redis_set(SOCIAL_META_KEY, {'fetchedAt': now_ms(), 'recordCount': len(social_payload['posts']), 'sourceVersion': 'social-reddit-host-seed', 'status': 'ok'}, TTL_META)

    wsb_payload = build_wsb(reddit_items)
    if wsb_payload:
        redis_set(WSB_KEY, envelope(wsb_payload, len(wsb_payload['tickers']), 'wsb-tickers-host-seed'), TTL_SOCIAL)
        redis_set(WSB_META_KEY, {'fetchedAt': now_ms(), 'recordCount': len(wsb_payload['tickers']), 'sourceVersion': 'wsb-tickers-host-seed', 'status': 'ok'}, TTL_META)

    print(json.dumps({
        'reddit_items': len(reddit_items),
        'social_posts': len(social_payload['posts']),
        'wsb_tickers': 0 if not wsb_payload else len(wsb_payload['tickers']),
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

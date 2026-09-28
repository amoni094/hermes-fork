#!/usr/bin/env python3
"""
social_signals.py — Social signal monitor for research briefings.
Referenced by: recent-news-briefing SKILL.md L48, signal-oriented-research-briefing L104

Monitors social signals (HN, Reddit, X/Twitter public search) for topic mentions.
Currently a stub with HN search via public API.

Usage:
  python3 social_signals.py --query TOPIC [--limit 10]  # search HN + Reddit
  python3 social_signals.py --briefing                   # generate signal briefing
"""
import argparse, json, sys, urllib.request, urllib.parse

HN_SEARCH_API = "https://hn.algolia.com/api/v1/search"


def search_hn(query: str, limit: int = 10) -> list:
    params = urllib.parse.urlencode({"query": query, "hitsPerPage": limit})
    url = f"{HN_SEARCH_API}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        hits = data.get("hits", [])
        return [
            {
                "source": "hackernews",
                "title": h.get("title", ""),
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "points": h.get("points", 0),
                "ts": h.get("created_at", ""),
            }
            for h in hits
        ]
    except Exception as e:
        print(f"[social_signals] HN search failed: {e}", file=sys.stderr)
        return []


def cmd_query(query: str, limit: int = 10) -> None:
    results = search_hn(query, limit)
    for r in results:
        print(f"  [{r['source']}] {r['title']}")
        print(f"    {r['url']}")
    print(f"\n{len(results)} results for: {query!r}")


def cmd_briefing() -> None:
    topics = ["LLM agent", "multi-agent systems", "AI safety", "context compression", "RAG memory"]
    for topic in topics:
        print(f"\n### {topic}")
        cmd_query(topic, limit=3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Social signal monitor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", metavar="TOPIC", help="Search topic")
    group.add_argument("--briefing", action="store_true", help="Full briefing")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if args.query:
        cmd_query(args.query, args.limit)
    elif args.briefing:
        cmd_briefing()


if __name__ == "__main__":
    main()

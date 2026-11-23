#!/usr/bin/env python3
"""
news_feed_ingest.py — Multi-source RSS + API news ingestion for daily briefing.
Pulls from Guardian API (full text), The Conversation (Atom, full text),
Politico/Diplomat/Foreign Affairs (RSS), Google News RSS for paywalled outlets,
HackerNews API (tech/AI), yfinance market news, and GDELT GKG (geopolitics).

Usage:
    python news_feed_ingest.py [--topics TOPIC,TOPIC,...] [--limit N] [--json] [--format text]
    python news_feed_ingest.py --sources hackernews,finance,gdelt --limit 10 --format text

Sources:
    guardian, conversation, politico, diplomat, foreign_affairs, paywalled,
    currents, hackernews, finance, gdelt, gnews, hn_algolia  (default: all)

Environment:
    GUARDIAN_API_KEY — Guardian Open Platform developer key (free at bonobo.capi.gutools.co.uk/register/developer)
    CURRENTS_API_KEY — Currents API key (optional, free at currentsapi.services/en/register)
    FINANCE_TICKERS  — Comma-separated tickers for yfinance news (default: SPY,ASX200,NVDA,TSLA,BTC-USD)

Outputs: JSON array of {title, source, url, summary, published, body_snippet} or formatted text.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Auto-load .env from script directory
# ---------------------------------------------------------------------------
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")
CURRENTS_API_KEY = os.environ.get("CURRENTS_API_KEY", "")
FINANCE_TICKERS = [t.strip() for t in os.environ.get(
    "FINANCE_TICKERS", "SPY,EWA,NVDA,TSLA,BTC-USD"
).split(",") if t.strip()]

# GNews keyword topics for Australia + user interests
GNEWS_QUERIES = [
    ("AU top",         {"country": "AU", "language": "en"}),
    ("AI/tech",        {"keyword": "artificial intelligence OR machine learning", "language": "en"}),
    ("geopolitics",    {"keyword": "Iran OR Ukraine OR Gaza OR sanctions OR ceasefire", "language": "en"}),
    ("finance/markets",{"keyword": "ASX OR interest rates OR RBA OR inflation OR Fed Reserve", "language": "en"}),
]
GNEWS_MAX_PER_QUERY = 8

# HN Algolia search — keyword-based tech/AI story search
HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"
HN_ALGOLIA_QUERIES = ["AI", "machine learning", "security", "open source"]
HN_ALGOLIA_MIN_POINTS = 50

GUARDIAN_API = "https://content.guardianapis.com/search"
CURRENTS_API = "https://api.currentsapi.services/v1/latest-news"
HACKERNEWS_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HACKERNEWS_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
TIMEOUT = 20

# Geopolitics / conflict RSS (no key needed)
GEOPOLITICS_RSS = {
    "Crisis Group":         "https://www.crisisgroup.org/rss.xml",
    # ACLED removed — malformed XML feed
    "UN Peace & Security":  "https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml",
    "Bellingcat":           "https://www.bellingcat.com/feed/",
}

# RSS/Atom feeds — no key needed
RSS_SOURCES = {
    "The Conversation (AU)":     "https://theconversation.com/au/articles.atom",
    "The Conversation (Global)": "https://theconversation.com/global/home-page.atom",
    "Politico":                "https://rss.politico.com/politics-news.xml",
    "The Diplomat":            "https://thediplomat.com/feed/",
    "Foreign Affairs":         "https://www.foreignaffairs.com/rss.xml",
}

# Google News RSS for paywalled outlets (headlines + snippets only)
GOOGLE_NEWS_PAYWALLED = {
    "Reuters (via GN)":    "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
    "Bloomberg (via GN)":  "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
    "Economist (via GN)":  "https://news.google.com/rss/search?q=site:economist.com&hl=en-US&gl=US&ceid=US:en",
    "AFR (via GN)":        "https://news.google.com/rss/search?q=site:afr.com&hl=en-AU&gl=AU&ceid=AU:en",
}

GUARDIAN_TOPICS = [
    "world", "australia-news", "us-news", "business", "technology",
    "environment", "politics", "science",
]

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(url: str, headers: Optional[dict] = None) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Hermes-NewsIngest/1.0 (+https://hermes-agent.nousresearch.com)",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", text or "")
    return text.strip()


def trunc(text: str, n: int = 300) -> str:
    text = text.strip()
    return text[:n] + "..." if len(text) > n else text


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Guardian API
# ---------------------------------------------------------------------------

def fetch_guardian(limit: int = 10, topics: list[str] | None = None) -> list[dict]:
    if not GUARDIAN_API_KEY:
        return []
    sections = topics or GUARDIAN_TOPICS
    articles = []
    seen = set()
    for section in sections:
        params = urllib.parse.urlencode({
            "section": section,
            "show-fields": "body,byline,trailText",
            "order-by": "newest",
            "page-size": min(limit, 10),
            "api-key": GUARDIAN_API_KEY,
        })
        url = f"{GUARDIAN_API}?{params}"
        try:
            data = json.loads(fetch(url))
            for item in data.get("response", {}).get("results", []):
                uid = item.get("id", item.get("webUrl", ""))
                if uid in seen:
                    continue
                seen.add(uid)
                fields = item.get("fields", {})
                body = strip_html(fields.get("body", "") or fields.get("trailText", ""))
                articles.append({
                    "title": item.get("webTitle", ""),
                    "source": "The Guardian",
                    "url": item.get("webUrl", ""),
                    "published": item.get("webPublicationDate", ""),
                    "summary": trunc(body, 400),
                    "body_snippet": trunc(body, 800),
                    "section": section,
                })
        except Exception as e:
            print(f"[guardian:{section}] error: {e}", file=sys.stderr)
    return articles


# ---------------------------------------------------------------------------
# Currents API
# ---------------------------------------------------------------------------

def fetch_currents(limit: int = 20) -> list[dict]:
    if not CURRENTS_API_KEY:
        return []
    params = urllib.parse.urlencode({
        "language": "en",
        "apiKey": CURRENTS_API_KEY,
    })
    url = f"{CURRENTS_API}?{params}"
    try:
        data = json.loads(fetch(url))
        articles = []
        for item in (data.get("news") or [])[:limit]:
            articles.append({
                "title": item.get("title", ""),
                "source": f"Currents/{item.get('author', 'unknown')}",
                "url": item.get("url", ""),
                "published": item.get("published", ""),
                "summary": trunc(item.get("description", ""), 300),
                "body_snippet": "",
                "section": "/".join(item.get("category", [])),
            })
        return articles
    except Exception as e:
        print(f"[currents] error: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# RSS / Atom parser
# ---------------------------------------------------------------------------

def _tag(el: ET.Element, local: str) -> str:
    """Get text of first child tag (handles namespace prefix or plain)."""
    for ns_prefix, ns_uri in NAMESPACES.items():
        child = el.find(f"{{{ns_uri}}}{local}")
        if child is not None and child.text:
            return child.text.strip()
    child = el.find(local)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def parse_rss(xml_bytes: bytes, source_name: str, limit: int = 10) -> list[dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[rss:{source_name}] parse error: {e}", file=sys.stderr)
        return []

    items = []

    # Atom feed
    atom_ns = "http://www.w3.org/2005/Atom"
    atom_entries = root.findall(f"{{{atom_ns}}}entry") or root.findall("entry")
    if atom_entries:
        for entry in atom_entries[:limit]:
            title_el = entry.find(f"{{{atom_ns}}}title")
            if title_el is None:
                title_el = entry.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""

            link_el = entry.find(f"{{{atom_ns}}}link")
            if link_el is None:
                link_el = entry.find("link")
            url = ""
            if link_el is not None:
                url = link_el.get("href", "") or (link_el.text or "")

            published_el = entry.find(f"{{{atom_ns}}}published")
            if published_el is None:
                published_el = entry.find(f"{{{atom_ns}}}updated")
            if published_el is None:
                published_el = entry.find("published")
            if published_el is None:
                published_el = entry.find("updated")
            published = published_el.text.strip() if published_el is not None and published_el.text else ""

            content_el = entry.find(f"{{{atom_ns}}}content")
            if content_el is None:
                content_el = entry.find(f"{{{atom_ns}}}summary")
            if content_el is None:
                content_el = entry.find("content")
            if content_el is None:
                content_el = entry.find("summary")
            body = strip_html(content_el.text or "") if content_el is not None and content_el.text else ""
            items.append({
                "title": title,
                "source": source_name,
                "url": url,
                "published": published,
                "summary": trunc(body, 300),
                "body_snippet": trunc(body, 600),
                "section": "",
            })
        return items

    # RSS feed
    channel = root.find("channel")
    base = channel if channel is not None else root
    entries = base.findall("item")
    for entry in entries[:limit]:
        title = entry.find("title")
        title = title.text.strip() if title is not None and title.text else ""
        link = entry.find("link")
        url = link.text.strip() if link is not None and link.text else ""
        pub = entry.find("pubDate")
        published = pub.text.strip() if pub is not None and pub.text else ""
        desc = entry.find("description")
        body = strip_html(desc.text or "") if desc is not None else ""
        # Try content:encoded
        encoded = entry.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        if encoded is not None and encoded.text:
            body = strip_html(encoded.text)
        items.append({
            "title": title,
            "source": source_name,
            "url": url,
            "published": published,
            "summary": trunc(body, 300),
            "body_snippet": trunc(body, 600),
            "section": "",
        })
    return items


def fetch_rss_sources(sources: dict, limit: int = 8) -> list[dict]:
    articles = []
    for name, url in sources.items():
        try:
            xml_bytes = fetch(url)
            articles.extend(parse_rss(xml_bytes, name, limit))
        except Exception as e:
            print(f"[rss:{name}] error: {e}", file=sys.stderr)
    return articles


# ---------------------------------------------------------------------------
# HackerNews API (no key, stdlib only)
# ---------------------------------------------------------------------------

def fetch_hackernews(limit: int = 20) -> list[dict]:
    """Pull top HackerNews stories (tech/AI focus). No key needed."""
    try:
        ids = json.loads(fetch(HACKERNEWS_TOP))[:limit * 3]
    except Exception as e:
        print(f"[hackernews] top fetch error: {e}", file=sys.stderr)
        return []

    articles = []
    for story_id in ids:
        if len(articles) >= limit:
            break
        try:
            item = json.loads(fetch(HACKERNEWS_ITEM.format(story_id)))
        except Exception:
            continue
        if not item or item.get("type") != "story":
            continue
        title = item.get("title", "")
        url = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        score = item.get("score", 0)
        if score < 50:  # skip low-signal items
            continue
        ts = item.get("time", 0)
        published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
        text = strip_html(item.get("text", "") or "")
        articles.append({
            "title": title,
            "source": "HackerNews",
            "url": url,
            "published": published,
            "summary": trunc(text or f"Score: {score} | Comments: {item.get('descendants', 0)}", 300),
            "body_snippet": trunc(text, 600),
            "section": "tech",
        })
    return articles


# ---------------------------------------------------------------------------
# yfinance market news (requires: pip install --user yfinance)
# ---------------------------------------------------------------------------

def fetch_finance_news(limit: int = 5) -> list[dict]:
    """Pull market news + price context for configured tickers via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("[finance] yfinance not installed — run: python3 -m pip install --user yfinance",
              file=sys.stderr)
        return []

    articles = []
    seen_titles: set[str] = set()
    for ticker in FINANCE_TICKERS:
        try:
            t = yf.Ticker(ticker)
            # Price context
            try:
                info = t.fast_info
                price = getattr(info, "last_price", None)
                prev = getattr(info, "previous_close", None)
                pct = ((price - prev) / prev * 100) if price and prev else None
                price_ctx = f" [{ticker} {price:.2f} ({pct:+.1f}%)]" if pct is not None else f" [{ticker}]"
            except Exception:
                price_ctx = f" [{ticker}]"

            for story in (t.news or [])[:limit]:
                content = story.get("content", {})
                title = content.get("title", "") or story.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                url = content.get("canonicalUrl", {}).get("url", "") or story.get("link", "")
                provider = content.get("provider", {}).get("displayName", "Yahoo Finance")
                pub_ts = content.get("pubDate", "") or story.get("providerPublishTime", "")
                if isinstance(pub_ts, (int, float)):
                    pub_ts = datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat()
                summary = content.get("summary", "") or content.get("description", "")
                articles.append({
                    "title": title + price_ctx,
                    "source": f"yfinance/{provider}",
                    "url": url,
                    "published": pub_ts,
                    "summary": trunc(summary, 300),
                    "body_snippet": trunc(summary, 600),
                    "section": "finance",
                })
        except Exception as e:
            print(f"[finance:{ticker}] error: {e}", file=sys.stderr)

    return articles


# ---------------------------------------------------------------------------
# Geopolitics RSS (Crisis Group, ACLED, UN, Bellingcat — no key needed)
# ---------------------------------------------------------------------------

def fetch_geopolitics(limit: int = 8) -> list[dict]:
    """Pull geopolitics/conflict articles from curated verified RSS feeds."""
    return fetch_rss_sources(GEOPOLITICS_RSS, limit=limit)


# ---------------------------------------------------------------------------
# GNews — Google News RSS wrapper, no key, supports country=AU + keyword search
# ---------------------------------------------------------------------------

def fetch_gnews(limit: int = 8) -> list[dict]:
    """Pull AU top news + topic-specific news via GNews (Google News RSS wrapper).
    Requires: pip install --user gnews
    Falls back silently if gnews is not installed.
    """
    try:
        from gnews import GNews  # type: ignore
    except ImportError:
        print("[gnews] not installed — skipping (pip install --user gnews)", file=sys.stderr)
        return []

    seen_urls: set[str] = set()
    articles = []

    for label, kwargs in GNEWS_QUERIES:
        if len(articles) >= limit * len(GNEWS_QUERIES):
            break
        try:
            gn = GNews(max_results=GNEWS_MAX_PER_QUERY, **{k: v for k, v in kwargs.items() if k != "keyword"})
            keyword = kwargs.get("keyword")
            raw = gn.get_news(keyword) if keyword else gn.get_top_news()
            for item in (raw or [])[:limit]:
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                pub = item.get("published date", "")
                articles.append({
                    "title":        item.get("title", "(no title)"),
                    "source":       f"GNews/{label}/{item.get('publisher', {}).get('title', 'unknown')}",
                    "url":          url,
                    "published":    pub,
                    "summary":      trunc(item.get("description", ""), 300),
                    "body_snippet": "",
                    "section":      label,
                })
        except Exception as e:
            print(f"[gnews:{label}] error: {e}", file=sys.stderr)

    return articles


# ---------------------------------------------------------------------------
# HN Algolia — keyword-based tech/AI story search (no key, unlimited)
# ---------------------------------------------------------------------------

def fetch_hn_algolia(limit: int = 8) -> list[dict]:
    """Search HN via Algolia API for tech/AI stories by keyword.
    Complements the Firebase HN top-stories fetch with topic-specific search.
    No API key. Min points filter applied in Python (Algolia doesn't expose it).
    """
    seen_urls: set[str] = set()
    articles = []

    for query in HN_ALGOLIA_QUERIES:
        if len(articles) >= limit * len(HN_ALGOLIA_QUERIES):
            break
        try:
            params = urllib.parse.urlencode({
                "query": query,
                "tags": "story",
                "hitsPerPage": str(limit * 3),  # over-fetch so we can filter by points
            })
            raw = json.loads(fetch(f"{HN_ALGOLIA_API}?{params}"))
            hits = raw.get("hits", [])
            # filter by min points in Python
            hits = [h for h in hits if (h.get("points") or 0) >= HN_ALGOLIA_MIN_POINTS]
            for h in hits[:limit]:
                url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                articles.append({
                    "title":        h.get("title", "(no title)"),
                    "source":       f"HN-Algolia/{query}",
                    "url":          url,
                    "published":    h.get("created_at", ""),
                    "summary":      trunc(f"pts:{h.get('points')} comments:{h.get('num_comments')}", 100),
                    "body_snippet": "",
                    "section":      "tech",
                })
        except Exception as e:
            print(f"[hn-algolia:{query}] error: {e}", file=sys.stderr)

    return articles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest news from multiple sources")
    parser.add_argument("--topics", default="", help="Comma-separated Guardian sections/topics")
    parser.add_argument("--limit", type=int, default=8, help="Articles per source (default 8)")
    parser.add_argument("--json", action="store_true", help="Output JSON array")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--sources", default="all",
                        help="Comma-separated: guardian,conversation,politico,diplomat,foreign_affairs,"
                             "paywalled,currents,hackernews,finance,gdelt,gnews,hn_algolia (default: all)")
    args = parser.parse_args()

    fmt = "json" if args.json else args.format
    topics = [t.strip() for t in args.topics.split(",") if t.strip()] or None
    source_filter = [s.strip() for s in args.sources.split(",")]
    use_all = "all" in source_filter

    all_articles = []

    if use_all or "guardian" in source_filter:
        all_articles.extend(fetch_guardian(limit=args.limit, topics=topics))

    if use_all or "currents" in source_filter:
        all_articles.extend(fetch_currents(limit=args.limit))

    rss_to_use = {}
    if use_all or "conversation" in source_filter:
        rss_to_use.update({k: v for k, v in RSS_SOURCES.items() if "Conversation" in k})
    if use_all or "politico" in source_filter:
        rss_to_use.update({k: v for k, v in RSS_SOURCES.items() if "Politico" in k})
    if use_all or "diplomat" in source_filter:
        rss_to_use.update({k: v for k, v in RSS_SOURCES.items() if "Diplomat" in k})
    if use_all or "foreign_affairs" in source_filter:
        rss_to_use.update({k: v for k, v in RSS_SOURCES.items() if "Foreign" in k})
    if rss_to_use:
        all_articles.extend(fetch_rss_sources(rss_to_use, limit=args.limit))

    if use_all or "paywalled" in source_filter:
        all_articles.extend(fetch_rss_sources(GOOGLE_NEWS_PAYWALLED, limit=args.limit))

    if use_all or "hackernews" in source_filter:
        all_articles.extend(fetch_hackernews(limit=args.limit))

    if use_all or "finance" in source_filter:
        all_articles.extend(fetch_finance_news(limit=args.limit))

    if use_all or "gdelt" in source_filter:
        all_articles.extend(fetch_geopolitics(limit=args.limit))

    if use_all or "gnews" in source_filter:
        all_articles.extend(fetch_gnews(limit=args.limit))

    if use_all or "hn_algolia" in source_filter:
        all_articles.extend(fetch_hn_algolia(limit=args.limit))

    if fmt == "json":
        print(json.dumps(all_articles, indent=2, ensure_ascii=False))
    else:
        if not all_articles:
            print("No articles fetched. Check API keys and network.")
            return
        print(f"NEWS INGEST — {now_iso()}")
        print(f"Total articles: {len(all_articles)}")
        print("=" * 72)
        by_source: dict[str, list] = {}
        for a in all_articles:
            by_source.setdefault(a["source"], []).append(a)
        for source, arts in sorted(by_source.items()):
            print(f"\n[ {source} ] ({len(arts)} articles)")
            print("-" * 60)
            for a in arts:
                print(f"  {a['title']}")
                print(f"  {a['url']}")
                if a.get("summary"):
                    print(f"  {a['summary'][:200]}")
                print()


if __name__ == "__main__":
    main()

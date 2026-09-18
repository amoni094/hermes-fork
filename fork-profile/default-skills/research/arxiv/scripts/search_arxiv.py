#!/usr/bin/env python3
"""Search arXiv and display results in a clean format.

Usage:
    python search_arxiv.py "GRPO reinforcement learning"
    python search_arxiv.py "GRPO reinforcement learning" --max 10
    python search_arxiv.py "GRPO reinforcement learning" --sort date
    python search_arxiv.py --author "Yann LeCun" --max 5
    python search_arxiv.py --category cs.AI --sort date --max 10
    python search_arxiv.py --id 2402.03300
    python search_arxiv.py --id 2402.03300,2401.12345

NOTE (2026-08): export.arxiv.org's search_query endpoint may be IP-rate-limited/blocked.
The id_list endpoint is unaffected. For keyword searches this script falls back to
scraping arxiv.org/search via local Firecrawl (localhost:3002) and extracting paper IDs,
then resolving metadata via id_list. If Firecrawl is unavailable, a plain HTML scrape
of the search page is used as a last resort.
"""
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

NS = {'a': 'http://www.w3.org/2005/Atom'}
FIRECRAWL_URL = "http://localhost:3002"
EXPORT_URL = "https://export.arxiv.org/api/query"


def _fetch_ids_via_api(parts, max_results, sort):
    """Try the export API search_query endpoint. Returns (xml_root, None) or (None, err)."""
    sort_map = {"relevance": "relevance", "date": "submittedDate", "updated": "lastUpdatedDate"}
    params = {
        'search_query': '+AND+'.join(parts),
        'max_results': str(max_results),
        'sortBy': sort_map.get(sort, sort),
        'sortOrder': 'descending',
    }
    url = EXPORT_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'HermesAgent/1.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        entries = root.findall('a:entry', NS)
        if entries:
            return root, None
        return None, "empty"
    except Exception as e:
        return None, str(e)


def _fetch_ids_via_firecrawl(query_str, max_results, sort):
    """Scrape arxiv search via Firecrawl and extract arXiv IDs."""
    sort_map = {
        "relevance": "-relevance",
        "date": "-announced_date_first",
        "updated": "-submitted_date",
    }
    order = sort_map.get(sort, "-relevance")
    search_url = (
        f"https://arxiv.org/search/?searchtype=all"
        f"&query={urllib.parse.quote(query_str)}"
        f"&size={min(max_results, 50)}&order={order}"
    )
    payload = json.dumps({"url": search_url, "formats": ["markdown"]}).encode()
    try:
        req = urllib.request.Request(
            f"{FIRECRAWL_URL}/v1/scrape",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer test"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        md = result.get("data", {}).get("markdown", "")
        # Extract arXiv IDs from markdown links like [arXiv:2608.07460]
        ids = re.findall(r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)', md)
        # Deduplicate preserving order
        seen = set()
        unique_ids = []
        for i in ids:
            base = i.split('v')[0]
            if base not in seen:
                seen.add(base)
                unique_ids.append(base)
        return unique_ids[:max_results], None
    except Exception as e:
        return [], str(e)


def _fetch_ids_via_html(query_str, max_results, sort):
    """Last-resort: plain HTML GET of the search page, extract IDs by regex."""
    sort_map = {
        "relevance": "-relevance",
        "date": "-announced_date_first",
        "updated": "-submitted_date",
    }
    order = sort_map.get(sort, "-relevance")
    search_url = (
        f"https://arxiv.org/search/?searchtype=all"
        f"&query={urllib.parse.quote(query_str)}"
        f"&size={min(max_results, 50)}&order={order}"
    )
    try:
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        ids = re.findall(r'/abs/(\d{4}\.\d{4,5})', html)
        seen = set()
        unique_ids = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                unique_ids.append(i)
        return unique_ids[:max_results], None
    except Exception as e:
        return [], str(e)


def _resolve_ids(ids):
    """Fetch full metadata for a list of arXiv IDs via the id_list endpoint (works reliably)."""
    url = f"{EXPORT_URL}?id_list={','.join(ids)}&max_results={len(ids)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'HermesAgent/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    return ET.fromstring(data)


def _print_entries(root, max_results):
    entries = root.findall('a:entry', NS)
    if not entries:
        print("No results found.")
        return

    total = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
    if total is not None:
        print(f"Found {total.text} results (showing {min(len(entries), max_results)})\n")

    for i, entry in enumerate(entries[:max_results]):
        title = entry.find('a:title', NS).text.strip().replace('\n', ' ')
        raw_id = entry.find('a:id', NS).text.strip()
        full_id = raw_id.split('/abs/')[-1] if '/abs/' in raw_id else raw_id
        arxiv_id = full_id.split('v')[0]
        published = entry.find('a:published', NS).text[:10]
        updated = entry.find('a:updated', NS).text[:10]
        authors = ', '.join(a.find('a:name', NS).text for a in entry.findall('a:author', NS))
        summary = entry.find('a:summary', NS).text.strip().replace('\n', ' ')
        cats = ', '.join(c.get('term') for c in entry.findall('a:category', NS))
        version = full_id[len(arxiv_id):] if full_id != arxiv_id else ""

        print(f"{i+1}. {title}")
        print(f"   ID: {arxiv_id}{version} | Published: {published} | Updated: {updated}")
        print(f"   Authors: {authors}")
        print(f"   Categories: {cats}")
        print(f"   Abstract: {summary[:300]}{'...' if len(summary) > 300 else ''}")
        print(f"   Links: https://arxiv.org/abs/{arxiv_id} | https://arxiv.org/pdf/{arxiv_id}")
        print()


def search(query=None, author=None, category=None, ids=None, max_results=5, sort="relevance"):
    if ids:
        # id_list path - always works
        root = _resolve_ids(ids.split(','))
        _print_entries(root, max_results)
        return

    # Build search parts
    parts = []
    if query:
        parts.append(f'all:{urllib.parse.quote(query)}')
    if author:
        parts.append(f'au:{urllib.parse.quote(author)}')
    if category:
        parts.append(f'cat:{category}')
    if not parts:
        print("Error: provide a query, --author, --category, or --id")
        sys.exit(1)

    # Strategy 1: direct API (may be rate-limited/blocked)
    root, err = _fetch_ids_via_api(parts, max_results, sort)
    if root is not None:
        _print_entries(root, max_results)
        return

    print(f"[arXiv export API unavailable ({err}), falling back to Firecrawl scrape...]", file=sys.stderr)

    # Strategy 2: Firecrawl scrape -> id_list resolve
    query_str = " ".join([query or "", author or "", category or ""]).strip()
    paper_ids, err2 = _fetch_ids_via_firecrawl(query_str, max_results, sort)
    if paper_ids:
        root = _resolve_ids(paper_ids)
        _print_entries(root, max_results)
        return

    print(f"[Firecrawl unavailable ({err2}), falling back to HTML scrape...]", file=sys.stderr)

    # Strategy 3: plain HTML scrape -> id_list resolve
    paper_ids, err3 = _fetch_ids_via_html(query_str, max_results, sort)
    if paper_ids:
        root = _resolve_ids(paper_ids)
        _print_entries(root, max_results)
        return

    print(f"All search strategies failed:\n  API: {err}\n  Firecrawl: {err2}\n  HTML: {err3}")
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        sys.exit(0)

    query = None
    author = None
    category = None
    ids = None
    max_results = 5
    sort = "relevance"

    i = 0
    positional = []
    while i < len(args):
        if args[i] == "--max" and i + 1 < len(args):
            max_results = int(args[i + 1]); i += 2
        elif args[i] == "--sort" and i + 1 < len(args):
            sort = args[i + 1]; i += 2
        elif args[i] == "--author" and i + 1 < len(args):
            author = args[i + 1]; i += 2
        elif args[i] == "--category" and i + 1 < len(args):
            category = args[i + 1]; i += 2
        elif args[i] == "--id" and i + 1 < len(args):
            ids = args[i + 1]; i += 2
        else:
            positional.append(args[i]); i += 1

    if positional:
        query = " ".join(positional)

    search(query=query, author=author, category=category, ids=ids, max_results=max_results, sort=sort)

#!/usr/bin/env python3
"""
AI Research Search - Query arXiv, Semantic Scholar, and OpenAlex in one shot.
Usage:
  python3 ai_research_search.py "your query"
  python3 ai_research_search.py "transformer agents" --max 5
  python3 ai_research_search.py "RLHF" --max 10 --year 2024

No API keys required for basic use. All three sources are free.
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime


# ── ANSI colours (auto-disabled if not a TTY) ──────────────────────────────
BOLD  = "\033[1m"   if sys.stdout.isatty() else ""
CYAN  = "\033[36m"  if sys.stdout.isatty() else ""
GREEN = "\033[32m"  if sys.stdout.isatty() else ""
YELLOW= "\033[33m"  if sys.stdout.isatty() else ""
RESET = "\033[0m"   if sys.stdout.isatty() else ""
DIM   = "\033[2m"   if sys.stdout.isatty() else ""


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "ai-research-search/1.0 (mailto:user@example.com)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def trunc(text, n=180):
    text = text.strip().replace("\n", " ")
    return text[:n] + "..." if len(text) > n else text


# ── 1. arXiv ──────────────────────────────────────────────────────────────
def search_arxiv(query, max_results=5, year=None):
    q = urllib.parse.quote(query)
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=all:{q}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    try:
        raw = fetch(url, timeout=20)
    except Exception as e:
        return [], f"arXiv fetch error: {e}"

    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(raw)
    results = []
    for entry in root.findall("a:entry", ns):
        id_el  = entry.find("a:id", ns)
        ti_el  = entry.find("a:title", ns)
        pu_el  = entry.find("a:published", ns)
        su_el  = entry.find("a:summary", ns)
        if id_el is None or ti_el is None or pu_el is None or su_el is None:
            continue
        arxiv_id = (id_el.text or "").strip().split("/abs/")[-1]
        title    = (ti_el.text or "").strip().replace("\n", " ")
        published= (pu_el.text or "")[:10]
        authors  = ", ".join(
            n_el.text for a in entry.findall("a:author", ns)[:3]
            if (n_el := a.find("a:name", ns)) is not None and n_el.text is not None
        )
        abstract = (su_el.text or "").strip()
        cats     = [c.get("term", "") for c in entry.findall("a:category", ns)]

        if year and not published.startswith(str(year)):
            continue

        results.append({
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "date": published,
            "abstract": abstract,
            "categories": ", ".join(cats[:3]),
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        })
    return results, None


# ── 2. Semantic Scholar ───────────────────────────────────────────────────
def search_s2(query, max_results=5, year=None):
    q = urllib.parse.quote(query)
    fields = "title,authors,year,citationCount,influentialCitationCount,abstract,isOpenAccess,openAccessPdf,externalIds"
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={q}&limit={max_results}&fields={fields}"
    )
    if year:
        url += f"&year={year}-"

    try:
        raw = fetch(url)
    except Exception as e:
        return [], f"Semantic Scholar fetch error: {e}"

    data = json.loads(raw)
    results = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv", "")
        pdf_url = ""
        if p.get("openAccessPdf"):
            pdf_url = p["openAccessPdf"].get("url", "")
        elif arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        results.append({
            "title": p.get("title", ""),
            "authors": ", ".join(a["name"] for a in (p.get("authors") or [])[:3]),
            "year": p.get("year"),
            "citations": p.get("citationCount", 0),
            "influential": p.get("influentialCitationCount", 0),
            "abstract": p.get("abstract") or "",
            "open_access": p.get("isOpenAccess", False),
            "pdf": pdf_url,
            "arxiv_id": arxiv_id,
            "s2_id": p.get("paperId", ""),
        })
    return results, None


# ── 3. OpenAlex ──────────────────────────────────────────────────────────
def search_openalex(query, max_results=5, year=None):
    q = urllib.parse.quote(query)
    filters = "open_access.is_oa:true"
    if year:
        filters += f",publication_year:{year}"
    url = (
        f"https://api.openalex.org/works"
        f"?search={q}"
        f"&filter={filters}"
        f"&per-page={max_results}"
        f"&select=title,authorships,publication_year,cited_by_count,open_access,primary_location,abstract_inverted_index,doi"
        f"&sort=cited_by_count:desc"
        f"&mailto=user@example.com"  # polite pool — higher rate limit
    )
    try:
        raw = fetch(url)
    except Exception as e:
        return [], f"OpenAlex fetch error: {e}"

    data = json.loads(raw)
    results = []
    for w in data.get("results", []):
        authors = ", ".join(
            a["author"]["display_name"]
            for a in (w.get("authorships") or [])[:3]
            if a.get("author")
        )
        venue = ""
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        venue = src.get("display_name", "")

        oa = w.get("open_access") or {}
        pdf_url = oa.get("oa_url", "")

        # reconstruct abstract from inverted index
        abstract = ""
        inv = w.get("abstract_inverted_index") or {}
        if inv:
            words = [""] * (max(pos for positions in inv.values() for pos in positions) + 1)
            for word, positions in inv.items():
                for pos in positions:
                    words[pos] = word
            abstract = " ".join(words)

        results.append({
            "title": w.get("title", ""),
            "authors": authors,
            "year": w.get("publication_year"),
            "citations": w.get("cited_by_count", 0),
            "venue": venue,
            "abstract": abstract,
            "pdf": pdf_url,
            "doi": w.get("doi", ""),
        })
    return results, None


# ── Pretty print ─────────────────────────────────────────────────────────
def print_section(title, results, err, source_label):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {source_label}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    if err:
        print(f"  {YELLOW}Warning: {err}{RESET}")
        return
    if not results:
        print(f"  {DIM}No results found.{RESET}")
        return
    for i, r in enumerate(results, 1):
        print(f"\n{BOLD}{i}. {r['title']}{RESET}")
        meta = []
        if r.get("authors"): meta.append(r["authors"])
        if r.get("year"):    meta.append(str(r["year"]))
        if r.get("date"):    meta.append(r["date"])
        if r.get("citations") is not None: meta.append(f"{r['citations']} citations")
        if r.get("influential"):            meta.append(f"{r['influential']} influential")
        if r.get("venue"):   meta.append(r["venue"])
        if r.get("categories"): meta.append(r["categories"])
        if meta:
            print(f"   {DIM}{' | '.join(meta)}{RESET}")
        abstract = r.get("abstract", "")
        if abstract:
            print(f"   {trunc(abstract, 200)}")
        links = []
        if r.get("url"):  links.append(f"Page: {r['url']}")
        if r.get("doi"):  links.append(f"DOI: {r['doi']}")
        if r.get("pdf"):  links.append(f"PDF: {r['pdf']}")
        if r.get("arxiv_id"): links.append(f"arXiv: arxiv.org/abs/{r['arxiv_id']}")
        if links:
            print(f"   {GREEN}{' | '.join(links)}{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Search AI research across arXiv, Semantic Scholar, OpenAlex")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max", type=int, default=5, help="Results per source (default: 5)")
    parser.add_argument("--year", type=int, default=None, help="Filter by publication year")
    parser.add_argument("--no-arxiv",  action="store_true")
    parser.add_argument("--no-s2",     action="store_true")
    parser.add_argument("--no-openalex", action="store_true")
    args = parser.parse_args()

    print(f"\n{BOLD}Query:{RESET} {args.query}")
    if args.year: print(f"{BOLD}Year:{RESET}  {args.year}")
    print(f"{BOLD}Max per source:{RESET} {args.max}")

    if not args.no_arxiv:
        print(f"\n{DIM}Querying arXiv...{RESET}", end="", flush=True)
        ax_results, ax_err = search_arxiv(args.query, args.max, args.year)
        print(f" {len(ax_results)} results")
        time.sleep(1)  # be polite

    if not args.no_s2:
        print(f"{DIM}Querying Semantic Scholar...{RESET}", end="", flush=True)
        s2_results, s2_err = search_s2(args.query, args.max, args.year)
        print(f" {len(s2_results)} results")
        time.sleep(0.5)

    if not args.no_openalex:
        print(f"{DIM}Querying OpenAlex...{RESET}", end="", flush=True)
        oa_results, oa_err = search_openalex(args.query, args.max, args.year)
        print(f" {len(oa_results)} results")

    if not args.no_arxiv:
        print_section("arXiv", ax_results, ax_err,
                      "arXiv — latest preprints (sorted by date)")
    if not args.no_s2:
        print_section("Semantic Scholar", s2_results, s2_err,
                      "Semantic Scholar — peer-reviewed + citation data")
    if not args.no_openalex:
        print_section("OpenAlex", oa_results, oa_err,
                      "OpenAlex — open-access only, sorted by citation count")

    print(f"\n{DIM}Tip: add --max 10 --year 2024 to narrow results. arXiv search may time out (known CDN issue) — S2+OA always work.{RESET}\n")


if __name__ == "__main__":
    main()

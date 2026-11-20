#!/usr/bin/env python3
"""memory-reference-frequency.py — Bayesian TTL from reference frequency.

Frequentist staleness (age > 30d => STALE) misclassifies stable config facts
that are referenced every session but rarely rewritten (Berger Ch 4: the
loss of evicting a still-used parameter exceeds the loss of keeping a
slowly-changing one). TTL should scale with posterior expected change time.

ttl = base_ttl * (1 + log(1 + reference_count))

Reads MEMORY.md sections; counts key-term hits in fork cache JSON files
(session-history proxy). Does not print section bodies.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 memory-reference-frequency.py
  python3 memory-reference-frequency.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

MEMORY_PATH = _hermes_base / "memories" / "MEMORY.md"
CACHE_GLOB_DIR = _hermes_root / "cache"
OUT_PATH = _hermes_root / "cache" / "memory-reference-frequency.json"
BASE_TTL_DAYS = 30.0
STOP = frozenset({
    "that", "this", "with", "from", "have", "been", "were", "they", "them",
    "then", "than", "also", "into", "over", "only", "some", "such", "when",
    "what", "which", "while", "where", "your", "about", "after", "before",
    "using", "used", "must", "should", "would", "could", "there", "their",
    "hermes", "none", "true", "false", "null", "path", "file", "files",
})
RE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RE_MONTH_YYYY = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?"
    r"|Dec(?:ember)?)\s+(\d{4})\b",
    re.IGNORECASE,
)
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{3,}")


def _atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_sections(text: str) -> list[str]:
    sections = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "\u00a7":
            sections.append("\n".join(current).strip())
            current = []
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


def extract_dates(text: str) -> list[date]:
    found: list[date] = []
    for m in RE_ISO.finditer(text):
        try:
            found.append(datetime.strptime(m.group(1), "%Y-%m-%d").date())
        except ValueError:
            pass
    for m in RE_MONTH_YYYY.finditer(text):
        month = MONTH_MAP.get(m.group(1)[:3].lower())
        year = int(m.group(2))
        if month:
            try:
                found.append(date(year, month, 1))
            except ValueError:
                pass
    return found


def key_terms(section: str, n: int = 10) -> list[str]:
    counts: dict[str, int] = {}
    for tok in TOKEN_RE.findall(section or ""):
        low = tok.lower()
        if low in STOP or low.isdigit():
            continue
        if any(ch.isdigit() for ch in tok) and sum(ch.isupper() for ch in tok) >= 1:
            continue
        counts[low] = counts.get(low, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:n]]


def last_modified_days(section: str, today: date | None = None) -> float | None:
    today = today or date.today()
    dates = extract_dates(section)
    if not dates:
        return None
    newest = max(dates)
    return float((today - newest).days)


def recommended_ttl(reference_count: int, base: float = BASE_TTL_DAYS) -> float:
    c = max(0, int(reference_count))
    return float(base) * (1.0 + math.log(1.0 + c))


def load_corpus(cache_dir: Path) -> str:
    parts: list[str] = []
    try:
        paths = sorted(cache_dir.glob("*.json"))
    except OSError:
        return ""
    for p in paths:
        try:
            parts.append(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts).lower()


def reference_count(terms: list[str], corpus: str) -> int:
    if not corpus or not terms:
        return 0
    total = 0
    for t in terms:
        if not t:
            continue
        total += corpus.count(t.lower())
    return total


def analyze(memory_text: str, corpus: str, today: date | None = None) -> list[dict]:
    today = today or date.today()
    rows = []
    for i, sec in enumerate(parse_sections(memory_text), start=1):
        terms = key_terms(sec)
        rc = reference_count(terms, corpus)
        age = last_modified_days(sec, today=today)
        ttl = recommended_ttl(rc)
        rows.append({
            "section_id": "S%02d" % i,
            "last_modified_days": age,
            "reference_count": rc,
            "recommended_ttl_days": round(ttl, 2),
            "n_key_terms": len(terms),
            "base_ttl_days": BASE_TTL_DAYS,
        })
    return rows


def run() -> dict:
    try:
        text = MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else ""
    except OSError:
        text = ""
    try:
        corpus = load_corpus(CACHE_GLOB_DIR)
    except Exception:
        corpus = ""
    rows = analyze(text, corpus)
    summary = {
        "ts": datetime.now().isoformat(),
        "memory_path": str(MEMORY_PATH),
        "cache_dir": str(CACHE_GLOB_DIR),
        "formula": "ttl = base_ttl * (1 + log(1 + reference_count))",
        "theory": "Berger Ch 4: TTL as function of reference frequency, not age alone",
        "n_sections": len(rows),
        "sections": rows,
    }
    try:
        _atomic_write(OUT_PATH, summary)
        summary["output"] = str(OUT_PATH)
    except OSError as exc:
        summary["write_error"] = str(exc)
    return summary


def self_test() -> int:
    failures = []
    if abs(recommended_ttl(0) - 30.0) > 1e-9:
        failures.append("ttl0")
    t1 = recommended_ttl(1)
    if t1 <= 30.0:
        failures.append("ttl1 not increasing")
    t10 = recommended_ttl(10)
    if t10 <= t1:
        failures.append("ttl not monotone")
    sep = "\n" + "\u00a7" + "\n"
    mem = "AlphaWidget routing uses grok-aux 2026-08-30" + sep + "No dates here at all about BetaWidget\n"
    corpus = "alphawidget grok-aux alphawidget extra"
    rows = analyze(mem, corpus, today=date(2026, 10, 9))
    if len(rows) != 2:
        failures.append("sections %d" % len(rows))
    else:
        if rows[0]["last_modified_days"] != 40:
            failures.append("age {}".format(rows[0]["last_modified_days"]))
        if rows[0]["reference_count"] < 1:
            failures.append("refs0")
        if rows[1]["last_modified_days"] is not None:
            failures.append("unknown date should be null")
    if analyze("", "") != []:
        failures.append("empty")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "ttl1": t1, "ttl10": t10, "rows": rows}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        "n_sections": out.get("n_sections"),
        "sections": out.get("sections"),
        "output": out.get("output"),
        "formula": out.get("formula"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

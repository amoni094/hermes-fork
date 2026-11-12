#!/usr/bin/python3
"""read-gate-eval.py — Hindsight recall quality harness (claude-mem read-gate).

Pure API test: no LLM. For each test query, POST /recall (legacy) then the
v1 memories/recall endpoint, score keyword overlap against expected_keywords,
and report per-query precision plus global coverage.

Usage:
  /usr/bin/python3 ~/.hermes/profiles/fork/scripts/read-gate-eval.py
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 read-gate-eval.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "").strip()
if _hermes_profile and "profiles" not in str(_hermes_base):
    _hermes_root = _hermes_base / "profiles" / _hermes_profile
else:
    _fork_root = _hermes_base / "profiles" / "fork"
    if (_fork_root / "evals" / "read-gate" / "test-queries.json").exists():
        _hermes_root = _fork_root
    else:
        _hermes_root = _hermes_base

HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://127.0.0.1:9177").rstrip("/")
DEFAULT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes-fork")
DEFAULT_TOP_K = 5
TIMEOUT_SEC = 15
EVAL_DIR = _hermes_root / "evals" / "read-gate"
QUERIES_PATH = EVAL_DIR / "test-queries.json"
STAGING_PATH = _hermes_root / "memory-facts" / "staging.md"
OUT_PATH = EVAL_DIR / "latest.json"

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "which",
        "who",
        "whom",
        "does",
        "do",
        "did",
        "on",
        "in",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "used",
        "use",
        "using",
        "run",
        "runs",
        "running",
        "how",
        "where",
        "when",
        "why",
        "with",
        "from",
        "by",
        "be",
        "it",
        "this",
        "that",
    }
)

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._:+-]*", re.I)

HARDCODED_QUERIES: list[dict[str, Any]] = [
    {
        "id": "q01",
        "query": "What is the Pi IP address?",
        "expected_keywords": ["192.168.0.138", "raspberry", "pihole", "dns"],
    },
    {
        "id": "q02",
        "query": "What model is used for triage?",
        "expected_keywords": ["triage", "grok", "claude", "sonnet", "model"],
    },
    {
        "id": "q03",
        "query": "What is the desktop hostname?",
        "expected_keywords": ["hostname", "desktop", "fedora", "rainbow"],
    },
    {
        "id": "q04",
        "query": "What port does hindsight run on?",
        "expected_keywords": ["9177", "hindsight", "127.0.0.1"],
    },
    {
        "id": "q05",
        "query": "What Python version does hermes use?",
        "expected_keywords": ["python", "3.14", "3.12", "stdlib"],
    },
    {
        "id": "q06",
        "query": "What is the hermes-fork repository path?",
        "expected_keywords": ["hermes-fork", "hermes-agent", ".hermes"],
    },
    {
        "id": "q07",
        "query": "What bank_id does hindsight use?",
        "expected_keywords": ["hermes-fork", "hermes-default", "bank"],
    },
    {
        "id": "q08",
        "query": "What is the user home directory?",
        "expected_keywords": ["/var/home/rainbow", "rainbow", "home"],
    },
    {
        "id": "q09",
        "query": "What cron sandbox wrapper is used?",
        "expected_keywords": ["cron-sandbox-wrapper", "openshell", "sandbox"],
    },
    {
        "id": "q10",
        "query": "What DNS does the Pi serve for the desktop?",
        "expected_keywords": ["192.168.0.138", "dns", "pihole", "technitium"],
    },
]


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {m.group(0).lower() for m in TOKEN_RE.finditer(text)}


def fact_is_relevant(
    fact_text: str, expected_keywords: list[str], query: str
) -> tuple[bool, int]:
    """A fact is relevant if any expected keyword is a substring of the fact.

    When expected_keywords is empty, fall back to content-token overlap with
    the query (stopwords removed).
    """
    blob = (fact_text or "").lower()
    kws = [k.strip().lower() for k in (expected_keywords or []) if str(k).strip()]
    if kws:
        hits = sum(1 for k in kws if k and k in blob)
        return hits >= 1, hits
    qtok = tokenize(query) - STOPWORDS
    ftok = tokenize(fact_text) - STOPWORDS
    overlap = len(qtok & ftok)
    return overlap >= 1, overlap


def extract_facts(payload: Any) -> list[str]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = (
            payload.get("results")
            or payload.get("memories")
            or payload.get("facts")
            or []
        )
    else:
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            raw = (
                item.get("text")
                or item.get("content")
                or item.get("memory")
                or item.get("fact")
                or ""
            )
            text = str(raw).strip() if raw is not None else ""
        else:
            continue
        if text:
            out.append(text)
    return out


def _post_json(url: str, body: dict[str, Any], timeout: float) -> Any:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"results": [], "_raw": raw[:500]}


def recall_hindsight(
    query: str,
    bank_id: str,
    top_k: int,
    base: str = HINDSIGHT_BASE,
    timeout: float = TIMEOUT_SEC,
) -> dict[str, Any]:
    """POST legacy /recall then v1 memories/recall. Never raises."""
    empty = {
        "ok": False,
        "endpoint": None,
        "facts": [],
        "error": None,
        "api_down": False,
    }
    if not isinstance(query, str):
        query = str(query or "")
    top_k = max(0, int(top_k))
    legacy_url = base + "/recall"
    v1_url = base + "/v1/default/banks/" + bank_id + "/memories/recall"
    try:
        payload = _post_json(
            legacy_url,
            {"query": query, "bank_id": bank_id, "top_k": top_k},
            timeout,
        )
        facts = extract_facts(payload)[:top_k]
        return {
            "ok": True,
            "endpoint": "/recall",
            "facts": facts,
            "error": None,
            "api_down": False,
        }
    except urllib.error.HTTPError as exc:
        # 404/405/422: documented legacy stub; fall through to v1.
        if exc.code not in (404, 405, 422, 400):
            empty["error"] = "/recall HTTP %s" % exc.code
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        empty["error"] = "api_down: %s" % reason
        empty["api_down"] = True
        return empty
    except TimeoutError:
        empty["error"] = "api_down: timeout"
        empty["api_down"] = True
        return empty
    except Exception as exc:
        empty["error"] = "/recall %s: %s" % (type(exc).__name__, exc)

    try:
        payload = _post_json(v1_url, {"query": query}, timeout)
        facts = extract_facts(payload)[:top_k]
        return {
            "ok": True,
            "endpoint": "/v1/default/banks/%s/memories/recall" % bank_id,
            "facts": facts,
            "error": None,
            "api_down": False,
        }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "endpoint": None,
            "facts": [],
            "error": "v1 HTTP %s" % exc.code,
            "api_down": False,
        }
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return {
            "ok": False,
            "endpoint": None,
            "facts": [],
            "error": "api_down: %s" % reason,
            "api_down": True,
        }
    except TimeoutError:
        return {
            "ok": False,
            "endpoint": None,
            "facts": [],
            "error": "api_down: timeout",
            "api_down": True,
        }
    except Exception as exc:
        return {
            "ok": False,
            "endpoint": None,
            "facts": [],
            "error": "%s: %s" % (type(exc).__name__, exc),
            "api_down": False,
        }


def _normalize_query(item: Any, idx: int) -> dict[str, Any] | None:
    if isinstance(item, str):
        q = item.strip()
        if not q:
            return None
        return {"id": "q%02d" % (idx + 1), "query": q, "expected_keywords": []}
    if not isinstance(item, dict):
        return None
    q = str(item.get("query") or item.get("prompt") or item.get("text") or "").strip()
    if not q:
        return None
    kws = item.get("expected_keywords") or item.get("keywords") or []
    if isinstance(kws, str):
        kws = [kws]
    if not isinstance(kws, list):
        kws = []
    kws = [str(k).strip() for k in kws if str(k).strip()]
    qid = str(item.get("id") or "q%02d" % (idx + 1))
    return {"id": qid, "query": q, "expected_keywords": kws}


def load_queries(path: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    """Load test queries: test-queries.json, else staging.md, else hardcoded."""
    candidate = path or QUERIES_PATH
    if candidate.exists():
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            raw = None
        items: list[Any] = []
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("queries") or raw.get("tasks") or []
        out: list[dict[str, Any]] = []
        for i, item in enumerate(items):
            row = _normalize_query(item, i)
            if row:
                out.append(row)
        if out:
            return out, str(candidate)

    staging = STAGING_PATH
    if staging.exists():
        try:
            text = staging.read_text(encoding="utf-8")
        except OSError:
            text = ""
        lines = [ln.strip().lstrip("-").strip() for ln in text.splitlines()]
        lines = [ln for ln in lines if ln and not ln.startswith("#")]
        if lines:
            out = []
            for i, ln in enumerate(lines[:10]):
                row = _normalize_query(ln, i)
                if row:
                    out.append(row)
            if out:
                return out, str(staging)

    return [dict(q) for q in HARDCODED_QUERIES], "hardcoded"


def score_query(
    task: dict[str, Any],
    recalled: dict[str, Any],
) -> dict[str, Any]:
    facts = recalled.get("facts") or []
    kws = task.get("expected_keywords") or []
    query = task.get("query") or ""
    n_rel = 0
    tagged: list[dict[str, Any]] = []
    for fact in facts:
        rel, hits = fact_is_relevant(fact, kws, query)
        if rel:
            n_rel += 1
        tagged.append({"text": fact[:500], "relevant": bool(rel), "keyword_hits": hits})
    n_rec = len(facts)
    precision = _clip01((n_rel / n_rec) if n_rec else 0.0)
    baseline = 0.0
    hit = n_rel >= 1
    if recalled.get("api_down"):
        verdict = "API_DOWN"
    elif not recalled.get("ok") and n_rec == 0:
        verdict = "API_DOWN" if recalled.get("api_down") else "ERROR"
        if recalled.get("error") and "api_down" in str(recalled.get("error")):
            verdict = "API_DOWN"
        elif not recalled.get("ok") and recalled.get("error"):
            verdict = "ERROR"
        else:
            verdict = "MISS"
    elif hit:
        verdict = "HIT"
    else:
        verdict = "MISS"
    return {
        "id": task.get("id"),
        "task": query,
        "baseline_score": baseline,
        "recall_score": precision,
        "delta": _clip01(precision - baseline) if precision >= baseline else precision - baseline,
        "verdict": verdict,
        "n_recalled": n_rec,
        "n_relevant": n_rel,
        "facts": tagged,
    }


def run_eval(
    queries: list[dict[str, Any]],
    bank_id: str,
    top_k: int,
    recall_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fn = recall_fn or recall_hindsight
    rows: list[dict[str, Any]] = []
    api_down = False
    api_error = None
    endpoint_used = None
    n_facts = 0
    n_rel = 0
    n_hit = 0
    for task in queries:
        rec = fn(task.get("query") or "", bank_id, top_k)
        if rec.get("api_down"):
            api_down = True
            api_error = rec.get("error") or api_error
        elif not rec.get("ok") and rec.get("error"):
            api_error = rec.get("error") or api_error
        if rec.get("endpoint"):
            endpoint_used = rec.get("endpoint")
        row = score_query(task, rec)
        rows.append(row)
        n_facts += int(row["n_recalled"])
        n_rel += int(row["n_relevant"])
        if row["verdict"] == "HIT":
            n_hit += 1
    n_q = len(queries)
    precision = _clip01((n_rel / n_facts) if n_facts else 0.0)
    coverage = _clip01((n_hit / n_q) if n_q else 0.0)
    api_ok = (not api_down) and any(r["verdict"] != "API_DOWN" for r in rows) if rows else (not api_down)
    if api_down:
        api_ok = False
    elif rows and all(r["verdict"] == "ERROR" for r in rows):
        api_ok = False
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "api_ok": bool(api_ok),
        "api_down": bool(api_down),
        "api_error": api_error,
        "endpoint_used": endpoint_used,
        "bank_id": bank_id,
        "top_k": int(top_k),
        "n_queries": n_q,
        "recall_precision": precision,
        "recall_coverage": coverage,
        "n_facts_total": n_facts,
        "n_relevant_total": n_rel,
        "n_queries_with_hit": n_hit,
        "rows": rows,
    }


def _atomic_write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex[:8])
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def format_table(result: dict[str, Any]) -> str:
    rows = result.get("rows") or []
    headers = ("task", "baseline_score", "recall_score", "delta", "verdict")
    body: list[tuple[str, str, str, str, str]] = []
    for row in rows:
        task = str(row.get("task") or "")
        if len(task) > 42:
            task = task[:39] + "..."
        body.append(
            (
                task,
                "%.2f" % float(row.get("baseline_score") or 0.0),
                "%.2f" % float(row.get("recall_score") or 0.0),
                "%+.2f" % float(row.get("delta") or 0.0),
                str(row.get("verdict") or ""),
            )
        )
    widths = [len(h) for h in headers]
    for tup in body:
        for i, cell in enumerate(tup):
            if len(cell) > widths[i]:
                widths[i] = len(cell)
    def fmt(cols: tuple[str, ...]) -> str:
        return " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    lines = [fmt(headers), "-+-".join("-" * w for w in widths)]
    lines.extend(fmt(t) for t in body)
    return "\n".join(lines)


def one_line(result: dict[str, Any]) -> str:
    if result.get("api_down") or not result.get("api_ok"):
        err = result.get("api_error") or "unavailable"
        return (
            "read-gate: api=DOWN (%s) precision=%.2f coverage=%.2f (%d/%d queries hit)"
            % (
                err,
                float(result.get("recall_precision") or 0.0),
                float(result.get("recall_coverage") or 0.0),
                int(result.get("n_queries_with_hit") or 0),
                int(result.get("n_queries") or 0),
            )
        )
    return (
        "read-gate: api=up bank=%s precision=%.2f coverage=%.2f (%d/%d queries hit) endpoint=%s"
        % (
            result.get("bank_id"),
            float(result.get("recall_precision") or 0.0),
            float(result.get("recall_coverage") or 0.0),
            int(result.get("n_queries_with_hit") or 0),
            int(result.get("n_queries") or 0),
            result.get("endpoint_used") or "none",
        )
    )


def self_test() -> dict[str, Any]:
    failures: list[str] = []
    rel, hits = fact_is_relevant(
        "Hindsight API listens on 127.0.0.1 port 9177",
        ["9177", "hindsight"],
        "What port does hindsight run on?",
    )
    if not rel or hits < 1:
        failures.append("positive-overlap: %s %s" % (rel, hits))
    rel2, hits2 = fact_is_relevant(
        "unrelated gardening notes about tomatoes",
        ["9177", "hindsight"],
        "What port does hindsight run on?",
    )
    if rel2 or hits2 != 0:
        failures.append("negative-overlap: %s %s" % (rel2, hits2))
    rel3, _ = fact_is_relevant("the pi ip is 192.168.0.138", [], "What is the Pi IP address?")
    if not rel3:
        failures.append("fallback-query-overlap failed")

    def mock_recall(query: str, bank_id: str, top_k: int) -> dict[str, Any]:
        _ = bank_id, top_k
        if "port" in query.lower():
            return {
                "ok": True,
                "endpoint": "/recall",
                "facts": [
                    "Hindsight runs on port 9177 at 127.0.0.1",
                    "unrelated cron noise",
                ],
                "error": None,
                "api_down": False,
            }
        return {
            "ok": True,
            "endpoint": "/recall",
            "facts": ["lorem ipsum dolor sit amet"],
            "error": None,
            "api_down": False,
        }

    tasks = [
        {
            "id": "t1",
            "query": "What port does hindsight run on?",
            "expected_keywords": ["9177", "hindsight"],
        },
        {
            "id": "t2",
            "query": "What is the Pi IP address?",
            "expected_keywords": ["192.168.0.138"],
        },
    ]
    result = run_eval(tasks, "hermes-fork", 5, recall_fn=mock_recall)
    if result["rows"][0]["verdict"] != "HIT":
        failures.append("hit-verdict: %s" % result["rows"][0])
    if abs(result["rows"][0]["recall_score"] - 0.5) > 1e-9:
        failures.append("precision-row0: %s" % result["rows"][0]["recall_score"])
    if result["rows"][1]["verdict"] != "MISS":
        failures.append("miss-verdict: %s" % result["rows"][1])
    if abs(result["recall_coverage"] - 0.5) > 1e-9:
        failures.append("coverage: %s" % result["recall_coverage"])
    if not (0.0 <= result["recall_precision"] <= 1.0):
        failures.append("precision-bounds")

    def down_fn(query: str, bank_id: str, top_k: int) -> dict[str, Any]:
        _ = query, bank_id, top_k
        return {
            "ok": False,
            "endpoint": None,
            "facts": [],
            "error": "api_down: Connection refused",
            "api_down": True,
        }

    down = run_eval(tasks, "hermes-fork", 5, recall_fn=down_fn)
    if down["api_ok"] or not down["api_down"]:
        failures.append("api-down-flags: %s" % down)
    if down["n_facts_total"] != 0 or down["recall_coverage"] != 0.0:
        failures.append("api-down-empty: %s" % down)
    if any(r["verdict"] != "API_DOWN" for r in down["rows"]):
        failures.append("api-down-verdict")

    rel_empty, hits_empty = fact_is_relevant("", ["9177"], "port")
    if rel_empty or hits_empty != 0:
        failures.append("empty-fact")
    long_q = "port " * 5000
    rel_long, _ = fact_is_relevant("hindsight 9177", ["9177"], long_q)
    if not rel_long:
        failures.append("long-query")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        bad = d / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        old_q = QUERIES_PATH
        try:
            loaded, src = load_queries(bad)
        except Exception as exc:
            failures.append("malformed-json-raised: %s" % exc)
            loaded, src = [], ""
        if not loaded:
            failures.append("malformed-json-empty-fallback")
        outp = d / ("latest_test_" + uuid.uuid4().hex + ".json")
        _atomic_write_json(outp, down)
        try:
            parsed = json.loads(outp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append("json-out: %s" % exc)
            parsed = {}
        if "recall_precision" not in parsed or "rows" not in parsed:
            failures.append("json-schema")
        _ = old_q, src

    scores = [result["recall_precision"], result["recall_coverage"], result["rows"][0]["delta"]]
    if any(s < 0.0 or s > 1.0 for s in scores):
        failures.append("score-clip: %s" % scores)

    return {
        "self_test": "PASS" if not failures else "FAIL",
        "n_failures": len(failures),
        "failures": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Hindsight read-gate recall quality eval")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--queries", default="", help="Path to test-queries.json")
    ap.add_argument("--out", default="", help="Path to latest.json")
    ap.add_argument("--bank", default=DEFAULT_BANK)
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r))
        return 0 if r["self_test"] == "PASS" else 1

    qpath = Path(args.queries) if args.queries else None
    queries, source = load_queries(qpath)
    top_k = args.top_k if args.top_k >= 0 else DEFAULT_TOP_K
    result = run_eval(queries, args.bank, top_k)
    result["queries_source"] = source
    out_path = Path(args.out) if args.out else OUT_PATH
    try:
        _atomic_write_json(out_path, result)
        result["out"] = str(out_path)
    except OSError as exc:
        result["out_error"] = str(exc)
    print(format_table(result))
    print()
    print(one_line(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

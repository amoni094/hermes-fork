"""Adaptive retrieval + RetRobust heuristics (fail-open, stdlib only).

Mallen et al. ACL 2023 (arXiv:2212.10511): retrieve only when parametric
memory is likely to fail (long-tail / low-confidence queries).

Yoran et al. 2023 (arXiv:2310.01558): irrelevant or empty retrieved context
hurts more than no retrieval, especially in multi-hop tool chains.

No NLI model, no fine-tuning, no LLM calls. Deterministic heuristics only.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Mallen skill-router gates (task spec).
SKILL_SKIP_SCORE = 0.15
SKILL_NAMES_ONLY_SCORE = 0.85
SKILL_SKIP_MAX_WORDS = 6

# Passage pre-filter: conservative so relevant hits survive.
PASSAGE_MIN_RELEVANCE = 0.12

DEGENERATE_NON_WS = 50
LOW_QUALITY_NOTE = (
    "[Note: previous tool result may be low-quality — verify before building on it]"
)

POSTURE_SKIP = "skip"
POSTURE_NAMES_ONLY = "names_only"
POSTURE_FULL = "full"

_STOP = frozenset({
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "with", "use", "when", "how", "what", "this", "that", "it", "be", "are",
    "was", "not", "from", "do", "i", "you", "my", "me", "can", "should", "will",
    "would", "if", "as", "by", "about", "into", "than", "then", "so", "we",
})

_SNAKE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_YEAR_RE = re.compile(r"\b(202[5-9]|20[3-9]\d)\b")
_VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+){1,3}\b")
_URL_RE = re.compile(r"https?://|\bwww\.", re.I)
_PRICE_RE = re.compile(r"\$\s?\d|\b(?:usd|eur|gbp|aud)\b|\bprice[sd]?\b", re.I)
_PROPER_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
_HARD_DOMAIN_RE = re.compile(
    r"\b(undocumented|reverse-?engine(?:er(?:ing)?)?|novel tool|"
    r"unusual workflow|new plugin|unfamiliar api|zero-?day)\b",
    re.I,
)
_STABLE_FACT_RE = re.compile(
    r"^\s*(what(?:'s| is| are)|who (?:is|was|invented)|capital of|"
    r"define|meaning of|when was|where is)\b",
    re.I,
)
_HTTP_ERR_RE = re.compile(
    r"\b(404|403|401|500|502|503|504)\b|"
    r"\b(not found|forbidden|unauthorized|internal server error)\b",
    re.I,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

_KNOWN_TOOLS = frozenset({
    "web_search", "web_extract", "read_file", "write_file", "search_files",
    "skill_view", "skills_list", "skill_manage", "terminal", "execute_code",
    "patch", "browser_navigate", "tool_search", "tool_describe", "tool_call",
    "delegate_task", "vision_analyze", "browser_snapshot", "browser_click",
})

_WEB_TOOLS = frozenset({"web_search", "web_extract", "web_search_tool", "web_extract_tool"})

_last_user_query: dict[str, str] = {}


def remember_user_query(session_id: str, text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        return
    _last_user_query[session_id or "nosession"] = text.strip()[:4000]


def last_user_query(session_id: str = "") -> str:
    return _last_user_query.get(session_id or "nosession", "")


def clear_session(session_id: str = "") -> None:
    _last_user_query.pop(session_id or "nosession", None)


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in _STOP]


def query_word_count(query: str) -> int:
    if not isinstance(query, str):
        return 0
    return len(query.split())


def query_has_tool_name(query: str) -> bool:
    if not isinstance(query, str) or not query:
        return False
    lowered = query.lower()
    if any(name in lowered for name in _KNOWN_TOOLS):
        return True
    return bool(_SNAKE_RE.search(lowered))


def keyword_overlap_score(query: str, passage: str) -> float:
    """Coverage of query terms in *passage* plus term density. Range [0, 1]."""
    try:
        q = set(tokenize(query))
        p = tokenize(passage)
        if not q or not p:
            return 0.0
        pset = set(p)
        coverage = len(q & pset) / max(len(q), 1)
        density = sum(1 for t in p if t in q) / max(len(p), 1)
        return max(0.0, min(1.0, 0.65 * coverage + 0.35 * min(1.0, density * 6.0)))
    except Exception:
        return 0.0


def should_retrieve_skill(
    query: str,
    top_score: float,
    *,
    tool_name_match: Optional[bool] = None,
) -> str:
    """Return skip | names_only | full. Fail-open to full.

    skip: top BM25 < 0.15 AND short query AND no tool-name keyword (noise).
    names_only: top BM25 > 0.85 (name is enough; skip full skill body).
    full: otherwise, or known-hard domain (force retrieval).
    """
    try:
        score = float(top_score or 0.0)
        q = query if isinstance(query, str) else str(query or "")
        if _HARD_DOMAIN_RE.search(q):
            return POSTURE_FULL
        match = query_has_tool_name(q) if tool_name_match is None else bool(tool_name_match)
        words = query_word_count(q)
        if score < SKILL_SKIP_SCORE and words < SKILL_SKIP_MAX_WORDS and not match:
            return POSTURE_SKIP
        if score > SKILL_NAMES_ONLY_SCORE:
            return POSTURE_NAMES_ONLY
        return POSTURE_FULL
    except Exception:
        logger.debug("adaptive_retrieval: should_retrieve_skill failed", exc_info=True)
        return POSTURE_FULL


def web_search_necessity(query: str) -> dict[str, Any]:
    """Classify whether web_search is needed. Fail-open: retrieve.

    retrieve signals: year>2024, versions, URLs, prices, multi-word proper nouns.
    skip: definitional/stable-fact pattern AND no retrieve signals.
    """
    try:
        q = query if isinstance(query, str) else str(query or "")
        signals: list[str] = []
        if _YEAR_RE.search(q):
            signals.append("year")
        if _VERSION_RE.search(q):
            signals.append("version")
        if _URL_RE.search(q):
            signals.append("url")
        if _PRICE_RE.search(q):
            signals.append("price")
        if _PROPER_RE.search(q):
            signals.append("proper_noun")
        if signals:
            return {"decision": "retrieve", "reason": ",".join(signals), "signals": signals}
        if _STABLE_FACT_RE.search(q) and query_word_count(q) <= 16:
            return {"decision": "skip", "reason": "stable_fact", "signals": []}
        return {"decision": "retrieve", "reason": "uncertain", "signals": []}
    except Exception:
        logger.debug("adaptive_retrieval: web_search_necessity failed", exc_info=True)
        return {"decision": "retrieve", "reason": "fail_open", "signals": []}


def is_degenerate_tool_result(result: Any) -> bool:
    """True for empty / error / no-info tool outputs (RetRobust cascade guard)."""
    try:
        if result is None:
            return True
        text = result if isinstance(result, str) else str(result)
        non_ws = sum(1 for c in text if not c.isspace())
        if non_ws < DEGENERATE_NON_WS:
            return True
        head = text[:800]
        if _HTTP_ERR_RE.search(head):
            # A page *about* HTTP codes still has plenty of other content; only
            # flag when the error dominates the head.
            if non_ws < 400 or re.search(r"\"error\"\s*:", head):
                return True
        try:
            data = json.loads(text)
        except Exception:
            return False
        if data in ([], {}, None):
            return True
        if isinstance(data, dict):
            if data.get("error") and not data.get("data") and not data.get("results") and not data.get("content"):
                return True
            if data.get("success") is False:
                return True
            web = (data.get("data") or {}).get("web") if isinstance(data.get("data"), dict) else None
            if web == []:
                return True
            if data.get("results") == []:
                return True
        if isinstance(data, list) and not data:
            return True
        return False
    except Exception:
        return False


def _iter_web_passages(tool_name: str, data: Any) -> list[tuple[Any, str]]:
    """Return (handle, passage_text) pairs that can be scored."""
    passages: list[tuple[Any, str]] = []
    if not isinstance(data, dict):
        return passages
    if tool_name in ("web_search", "web_search_tool"):
        web = (data.get("data") or {}).get("web") if isinstance(data.get("data"), dict) else data.get("web")
        if isinstance(web, list):
            for i, item in enumerate(web):
                if not isinstance(item, dict):
                    continue
                blob = " ".join(
                    str(item.get(k) or "") for k in ("title", "description", "url", "content")
                )
                passages.append((i, blob))
    elif tool_name in ("web_extract", "web_extract_tool"):
        rows = data.get("results")
        if isinstance(rows, list):
            for i, item in enumerate(rows):
                if not isinstance(item, dict):
                    continue
                blob = " ".join(
                    str(item.get(k) or "") for k in ("title", "content", "url", "error")
                )
                passages.append((i, blob))
    return passages


def filter_web_passages(result: str, query: str, *, tool_name: str = "web_search") -> str:
    """Drop passages below PASSAGE_MIN_RELEVANCE. Fail-open: keep original."""
    try:
        if not isinstance(result, str) or not query or not result.strip():
            return result
        data = json.loads(result)
        passages = _iter_web_passages(tool_name, data)
        if not passages:
            return result
        keep_idx = set()
        scores: list[float] = []
        for i, blob in passages:
            score = keyword_overlap_score(query, blob)
            scores.append(score)
            if score >= PASSAGE_MIN_RELEVANCE:
                keep_idx.add(i)
        if not keep_idx:
            # Dropping everything is worse than noisy retrieval (RetRobust NLI
            # over-filters too). Keep original.
            return result
        if len(keep_idx) == len(passages):
            return result
        if tool_name in ("web_search", "web_search_tool"):
            web = (data.get("data") or {}).get("web") if isinstance(data.get("data"), dict) else None
            if isinstance(web, list) and isinstance(data.get("data"), dict):
                data = dict(data)
                inner = dict(data["data"])
                inner["web"] = [item for i, item in enumerate(web) if i in keep_idx]
                data["data"] = inner
                data["_adaptive_retrieval"] = {
                    "kept": len(inner["web"]),
                    "dropped": len(web) - len(inner["web"]),
                    "min_score": round(min(scores), 3) if scores else 0.0,
                }
                return json.dumps(data, ensure_ascii=False)
        if tool_name in ("web_extract", "web_extract_tool"):
            rows = data.get("results")
            if isinstance(rows, list):
                data = dict(data)
                data["results"] = [item for i, item in enumerate(rows) if i in keep_idx]
                data["_adaptive_retrieval"] = {
                    "kept": len(data["results"]),
                    "dropped": len(rows) - len(data["results"]),
                    "min_score": round(min(scores), 3) if scores else 0.0,
                }
                return json.dumps(data, ensure_ascii=False)
        return result
    except Exception:
        logger.debug("adaptive_retrieval: filter_web_passages failed", exc_info=True)
        return result


def apply_tool_result_guards(
    tool_name: str,
    result: str,
    *,
    query: str = "",
    session_id: str = "",
) -> str:
    """Passage filter (web_*) then degenerate-result warning. Fail-open."""
    try:
        if not isinstance(result, str):
            return result
        out = result
        q = query or last_user_query(session_id)
        if tool_name in _WEB_TOOLS and q:
            filtered = filter_web_passages(out, q, tool_name=tool_name)
            if filtered != out:
                log_decision({
                    "surface": "passage_filter",
                    "tool": tool_name,
                    "session_id": session_id or "",
                    "decision": "filtered",
                })
                out = filtered
        if is_degenerate_tool_result(out):
            if LOW_QUALITY_NOTE not in out[:200]:
                out = LOW_QUALITY_NOTE + "\n" + out
            log_decision({
                "surface": "degenerate_guard",
                "tool": tool_name,
                "session_id": session_id or "",
                "decision": "flag",
            })
        return out
    except Exception:
        logger.debug("adaptive_retrieval: apply_tool_result_guards failed", exc_info=True)
        return result


def _decisions_path() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        base = base / "profiles" / profile
    cache = base / "cache"
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return cache / "adaptive-retrieval-decisions.jsonl"


def log_decision(record: dict[str, Any]) -> None:
    """O_APPEND JSONL. Lines kept well under PIPE_BUF. Never raises."""
    try:
        payload = dict(record)
        payload.setdefault("ts", time.time())
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(line) > 3500:
            line = line[:3500] + '..."truncated":true}'
        path = _decisions_path()
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, (line + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except Exception:
        logger.debug("adaptive_retrieval: log_decision failed", exc_info=True)


def _self_test() -> int:
    failures = 0

    def check(name: str, cond: bool) -> None:
        nonlocal failures
        if not cond:
            print(f"FAIL {name}")
            failures += 1
        else:
            print(f"ok   {name}")

    check("skip_short_low", should_retrieve_skill("hello world", 0.05) == POSTURE_SKIP)
    check("full_tool_kw", should_retrieve_skill("run web_search now", 0.05) == POSTURE_FULL)
    check("names_only_hi", should_retrieve_skill("configure hyprland keybinds please", 0.91) == POSTURE_NAMES_ONLY)
    check("hard_domain", should_retrieve_skill("undocumented api", 0.01) == POSTURE_FULL)
    check("web_year", web_search_necessity("news in 2026")["decision"] == "retrieve")
    check("web_stable", web_search_necessity("What is the capital of France")["decision"] == "skip")
    check("web_price", web_search_necessity("What is the price of eggs")["decision"] == "retrieve")
    check("overlap", keyword_overlap_score("hyprland keybinds", "Hyprland XF86 keybinds not firing") > 0.2)
    check("degen_empty", is_degenerate_tool_result("{}") is True)
    check("degen_short", is_degenerate_tool_result("   err   ") is True)
    check("degen_ok", is_degenerate_tool_result("x" * 80) is False)
    sample = json.dumps({
        "success": True,
        "data": {"web": [
            {"title": "Hyprland wiki", "url": "https://x", "description": "hyprland keybinds xf86"},
            {"title": "Cooking", "url": "https://y", "description": "pasta recipe tomato"},
        ]},
    })
    filtered = filter_web_passages(sample, "hyprland keybinds", tool_name="web_search")
    kept = json.loads(filtered)["data"]["web"]
    check("filter_keeps_relevant", len(kept) == 1 and "Hyprland" in kept[0]["title"])
    return failures


if __name__ == "__main__":
    raise SystemExit(_self_test())

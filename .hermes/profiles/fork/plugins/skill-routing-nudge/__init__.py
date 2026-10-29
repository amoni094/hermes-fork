"""skill-routing-nudge — pre_llm_call plugin for Hermes fork.

Loads skill-router-index.json, scores the user message against skill TF-IDF
vectors, and injects a compact [SKILL ROUTING HINT] block when confidence
gates pass.

H-I6: stdlib only. H-I7: never raises (fail-open → {}).
H-I8: plugin_add=HIGH — leave settings.enabled false until governance approval.
Do not enable in config.yaml from this module.

ASSUME: index is {built_at, total, skills:[{name, description, triggers, path, tokens}]}
        (tfidf is stripped at build time and rebuilt here from tokens).
GUARANTEE: fail-open; returns {context: hint} or {}.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("skill-routing-nudge")

ISS_GAIN = 0.20
EPS_DP = 0.0

MIN_SCORE = 0.3
MAX_RESULTS = 3
MIN_WORDS = 8
GAP_MIN = 0.1
AMBIGUOUS_TOP = 0.5
SAFETY_MIN = 0.2
SAFETY_SKILLS = (
    "recursive-adversarial-hardening",
    "amodei-concrete-ai-safety",
)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "be", "use", "when",
    "that", "this", "it", "as", "if", "how", "what", "which", "do", "does",
    "can", "will", "not", "all", "any", "has", "have", "been", "using",
}

_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*")


def _index_path() -> Path:
    """Resolve skill-router-index.json under the active profile cache."""
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    name = "skill-router-index.json"
    candidates = []
    if profile and "profiles" not in str(home):
        candidates.append(home / "profiles" / profile / "cache" / name)
    candidates.append(home / "cache" / name)
    fork = Path.home() / ".hermes" / "profiles" / "fork" / "cache" / name
    if fork not in candidates:
        candidates.append(fork)
    for path in candidates:
        try:
            if path.exists():
                return path
        except Exception:
            continue
    return candidates[0]


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alnum, drop stopwords and tokens len <= 2.

    Matches skill-router-index.tokenize().
    """
    try:
        if not isinstance(text, str) or not text:
            return []
        tokens = _TOKEN_RE.findall(text.lower())
        return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
    except Exception:
        return []


def _skills_from_payload(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [s for s in data if isinstance(s, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("skills", "entries", "index", "items"):
        val = data.get(key)
        if isinstance(val, list):
            return [s for s in val if isinstance(s, dict)]
    # name → {tfidf|tokens|description} map
    out = []
    for name, body in data.items():
        if isinstance(body, dict) and (
            "tokens" in body or "tfidf" in body or "description" in body
        ):
            row = dict(body)
            row.setdefault("name", name)
            out.append(row)
    return out


def _doc_tokens(skill: dict) -> list[str]:
    toks = skill.get("tokens")
    if isinstance(toks, list) and toks:
        return [str(t) for t in toks if t]
    parts = [str(skill.get("name") or ""), str(skill.get("description") or "")]
    trig = skill.get("triggers") or []
    if isinstance(trig, list):
        parts.extend(str(t) for t in trig)
    elif trig:
        parts.append(str(trig))
    return _tokenize(" ".join(parts))


def _l2_normalize(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


def _attach_tfidf(skills: list[dict]) -> list[dict]:
    """Rebuild L2-normalized TF-IDF from tokens when the index omitted vectors."""
    n = len(skills)
    if n == 0:
        return skills
    have_all = True
    for skill in skills:
        tfidf = skill.get("tfidf")
        if not isinstance(tfidf, dict) or not tfidf:
            have_all = False
            break
    if have_all:
        for skill in skills:
            cleaned: dict[str, float] = {}
            for k, v in skill["tfidf"].items():
                try:
                    cleaned[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
            skill["tfidf"] = _l2_normalize(cleaned) if cleaned else {}
        return skills

    docs = [_doc_tokens(s) for s in skills]
    df: dict[str, int] = {}
    for toks in docs:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1

    for skill, toks in zip(skills, docs):
        existing = skill.get("tfidf")
        if isinstance(existing, dict) and existing:
            cleaned = {}
            for k, v in existing.items():
                try:
                    cleaned[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
            skill["tfidf"] = _l2_normalize(cleaned) if cleaned else {}
            continue
        tf: dict[str, float] = {}
        for t in toks:
            tf[t] = tf.get(t, 0.0) + 1.0
        vec: dict[str, float] = {}
        for t, freq in tf.items():
            idf = math.log((n + 1.0) / (df.get(t, 0) + 1.0)) + 1.0
            vec[t] = freq * idf
        skill["tfidf"] = _l2_normalize(vec) if vec else {}
    return skills


def _load_index(path: Path | str) -> list[dict]:
    """Load index JSON and return skills with tfidf vectors attached."""
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    skills = _skills_from_payload(data)
    return _attach_tfidf(skills)


def _query_vec(tokens: list[str]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    return _l2_normalize(tf) if tf else {}


def _dot(q_vec: dict[str, float], s_vec: dict[str, float]) -> float:
    if not q_vec or not s_vec:
        return 0.0
    if len(q_vec) > len(s_vec):
        q_vec, s_vec = s_vec, q_vec
    return sum(qv * s_vec[t] for t, qv in q_vec.items() if t in s_vec)


def _extract_user_message(ctx: Any, kwargs: dict) -> str:
    payload: dict = {}
    if isinstance(ctx, dict):
        payload.update(ctx)
    payload.update(kwargs)
    msg = payload.get("user_message") or payload.get("message") or ""
    if isinstance(msg, str) and msg.strip():
        return msg
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if not isinstance(item, dict):
                continue
            if str(item.get("role") or "") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        parts.append(str(part.get("text") or ""))
                joined = " ".join(p for p in parts if p)
                if joined.strip():
                    return joined
    return str(msg or "")


def _word_count(text: str) -> int:
    return len([w for w in text.split() if w])


def _build_hint(picked: list[tuple[float, dict]]) -> str:
    lines = ["[SKILL ROUTING HINT]"]
    for score, skill in picked:
        name = str(skill.get("name") or "").strip() or "(unnamed)"
        desc = " ".join(str(skill.get("description") or "").split())
        if len(desc) > 80:
            desc = desc[:77].rstrip() + "..."
        if desc:
            lines.append(f"- {name} ({score:.2f}): {desc}")
        else:
            lines.append(f"- {name} ({score:.2f})")
    return "\n".join(lines)


def _select(ranked: list[tuple[float, dict]]) -> list[tuple[float, dict]]:
    if not ranked:
        return []
    top = ranked[0][0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    gated_ok = top >= MIN_SCORE
    if gated_ok and (top - second) < GAP_MIN and top < AMBIGUOUS_TOP:
        gated_ok = False

    safety_hits = [
        (sc, sk)
        for sc, sk in ranked
        if str(sk.get("name") or "") in SAFETY_SKILLS and sc >= SAFETY_MIN
    ]
    main: list[tuple[float, dict]] = []
    if gated_ok:
        for sc, sk in ranked:
            if str(sk.get("name") or "") in SAFETY_SKILLS:
                continue
            if sc < MIN_SCORE:
                break
            main.append((sc, sk))
            if len(main) >= MAX_RESULTS:
                break

    merged: list[tuple[float, dict]] = []
    seen: set[str] = set()
    for item in sorted(safety_hits, key=lambda x: -x[0]) + main:
        name = str(item[1].get("name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        merged.append(item)
        if len(merged) >= MAX_RESULTS:
            break
    merged.sort(key=lambda x: -x[0])
    return merged


def pre_llm_call(ctx: Any = None, **kwargs: Any) -> dict:
    """pre_llm_call hook. Returns {context: hint} or {}."""
    try:
        text = _extract_user_message(ctx, kwargs)
        if _word_count(text) < MIN_WORDS:
            return dict()
        path = _index_path()
        if not path.exists():
            return dict()
        skills = _load_index(path)
        q_tokens = _tokenize(text)
        if not q_tokens or not skills:
            return dict()
        q_vec = _query_vec(q_tokens)
        ranked: list[tuple[float, dict]] = []
        for skill in skills:
            tfidf = skill.get("tfidf")
            if not isinstance(tfidf, dict):
                continue
            score = _dot(q_vec, tfidf)
            ranked.append((score, skill))
        ranked.sort(key=lambda x: -x[0])
        picked = _select(ranked)
        if not picked:
            return dict()
        return {"context": _build_hint(picked)}
    except Exception as exc:
        logger.debug("skill-routing-nudge: suppressed: %s", exc)
        return dict()


def register(ctx: Any) -> None:
    """Register with the Hermes plugin context. Never raises."""
    try:
        ctx.register_hook("pre_llm_call", pre_llm_call)
    except Exception as exc:
        logger.debug("skill-routing-nudge: register suppressed: %s", exc)

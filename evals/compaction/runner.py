"""Compaction eval runner.

Pipeline per transcript:
  1. Load + cap the transcript.
  2. Generate (or load cached) recall questions from the region that will be
     summarized away under the CURRENT policy (the most conservative boundary:
     anything the current policy summarizes is fair game for every policy).
  3. For each policy: compress, then answer each question from the
     compressed context. ``+recovery`` searches the intra-prefix discard set.
     ``+recovery_full`` / ``--full-lineage`` searches the reconstructed lineage
     (production session_search). Retrieval is hybrid BM25+cosine RRF, with a
     second hop when the first search is empty or very short.
  4. Judge answers against gold with an LLM judge (sees gold; answerer
     does not).
  5. Write per-policy results JSON for report.py.

Run from repo root with the project venv (needs a configured provider).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import math
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evals.compaction.fixtures import (  # noqa: E402
    estimate_tokens,
    load_transcript,
    total_tokens,
)
from evals.compaction.policies import (  # noqa: E402
    EVAL_MODEL,
    FORK_RUNTIME_ATTRS,
    POLICIES,
    apply_policy,
)

logger = logging.getLogger(__name__)

QUESTION_PROMPT = """You are building a factual recall exam from an AI-agent work session transcript.

Write {n} questions that test SPECIFIC, VERIFIABLE facts from the transcript below: identifiers (PR numbers, file paths, error messages, commit subjects), decisions and their reasons, user instructions, and outcomes. Rules:
- Every answer must appear literally in the transcript.
- No questions about the system prompt or generic behavior.
- Spread questions across the WHOLE span (early, middle, late).
- Prefer facts that matter for continuing the work (what was decided, what failed, what the user asked for).

Return STRICT JSON: a list of {{"q": "...", "gold": "...", "where": "<short quote locating the answer>"}}.

TRANSCRIPT:
{transcript}
"""

ANSWER_PROMPT = """You are an AI agent resuming a work session. Below is your CURRENT conversation context (it may include a compaction summary of earlier work). Answer the question using ONLY this context. If the context does not contain the answer, say exactly "NOT IN CONTEXT" and give your best guess after a semicolon.

CONTEXT:
{context}

QUESTION: {question}

Answer in one or two sentences."""

JUDGE_PROMPT = """Score this answer against the gold answer. Reply with STRICT JSON: {{"score": 2|1|0, "why": "..."}}.
2 = factually matches gold (wording may differ)
1 = partially correct or hedged-but-right ("NOT IN CONTEXT; guess X" where X is right scores 1)
0 = wrong, or "NOT IN CONTEXT" with a wrong/no guess

QUESTION: {question}
GOLD: {gold}
ANSWER: {answer}"""

SEARCH_QUERY_PROMPT = """You are an AI agent resuming a work session. Your context (below) includes a compaction summary noting that the full pre-compaction history is recoverable via session_search. You need to answer a question and the answer may not be in your current context.

Write the best search query (3-8 keywords, no boolean syntax) to find the answer in the archived session history. Reply with ONLY the query string.

CONTEXT (may be relevant):
{context_hint}

QUESTION: {question}"""

ANSWER_WITH_RECOVERY_PROMPT = """You are an AI agent resuming a work session. Below is your CURRENT conversation context (including a compaction summary), plus the results of a session_search you just ran against the archived pre-compaction history. Answer the question using both. If neither contains the answer, say exactly "NOT IN CONTEXT" and give your best guess after a semicolon.

CONTEXT:
{context}

SESSION_SEARCH RESULTS:
{search_results}

QUESTION: {question}

Answer in one or two sentences."""

SIGNAL_TYPES = ("TOKEN_NEUTRAL", "TOKEN_SENSITIVE", "TOKEN_EFFICIENT_SIGNAL")
PRIMARY_SIGNAL = "TOKEN_EFFICIENT_SIGNAL"
SUMMARY_PREAMBLE_MARKERS = (
    "CONTEXT COMPACTION",
    "Conversation Summary",
    "handoff summary",
    "[CONTEXT COMPACTION",
)
MIN_VALID_PER_TIER = 9  # ship-gate N=30 (10/10/10); use 3 for 5/5/5 fast-mode
HEAD_HIT_CHARS = 5000  # ledger at position 0, then ~1-2K summary prefix
OUTPUT_TOKENS_PER_RECALL_POINT_TARGET = 1200


_TERM_RE = re.compile(r"[A-Za-z0-9_#./-]{3,}")
_RRF_K = 60
# Cap for ArchiveIndex to avoid OOM on very large full-lineage corpora.
# At ~150 chars/message average, 200K messages ~ 30M chars ~ 7.5M tokens.
_ARCHIVE_INDEX_MSG_CAP = 200_000
_ARCHIVE_INDEX_CHAR_CAP = 30_000_000  # 30 MB of text


class ArchiveIndex:
    """Reusable hybrid BM25 + cosine TF-IDF index over a message list.

    Built once per policy arm so a large lineage is not re-indexed per question.
    When the corpus exceeds _ARCHIVE_INDEX_MSG_CAP or _ARCHIVE_INDEX_CHAR_CAP
    the corpus is tail-truncated (most recent messages kept) before indexing.
    """

    def __init__(self, corpus: list):
        import sqlite3 as _sq

        # Tail-truncate to avoid OOM on 7.6M-token lineages.
        rows_raw = [
            (i, m.get("role") or "", m["content"])
            for i, m in enumerate(corpus)
            if isinstance(m.get("content"), str) and len(m["content"]) >= 20
        ]
        if len(rows_raw) > _ARCHIVE_INDEX_MSG_CAP:
            rows_raw = rows_raw[-_ARCHIVE_INDEX_MSG_CAP:]
        total_chars = sum(len(c) for _, _, c in rows_raw)
        if total_chars > _ARCHIVE_INDEX_CHAR_CAP:
            # Drop oldest messages until under cap.
            while rows_raw and total_chars > _ARCHIVE_INDEX_CHAR_CAP:
                _, _, c = rows_raw.pop(0)
                total_chars -= len(c)
        self.rows = rows_raw
        self._by_idx: dict[int, tuple[str, str]] = {i: (r, c) for i, r, c in self.rows}
        self._db = None
        self._snips: dict[int, str] = {}
        try:
            db = _sq.connect(":memory:")
            db.execute(
                "CREATE VIRTUAL TABLE arch USING fts5(content, role UNINDEXED, idx UNINDEXED)"
            )
            db.executemany(
                "INSERT INTO arch (content, role, idx) VALUES (?, ?, ?)",
                [(c, r, i) for i, r, c in self.rows],
            )
            self._db = db
        except _sq.OperationalError:
            self._db = None

    def search(self, query: str, top_k: int = 6, excerpt_chars: int = 2500) -> str:
        """Hybrid BM25 + cosine RRF search; returns formatted excerpts."""
        terms = [t.lower() for t in _TERM_RE.findall(query)]
        if not terms:
            return "(no results)"

        bm25_order: list[int] = []
        snips: dict[int, str] = {}
        if self._db is not None:
            fts_query = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
            try:
                cur = self._db.execute(
                    "SELECT idx, snippet(arch, 0, '', '', ' … ', 40) AS snip "
                    "FROM arch WHERE arch MATCH ? ORDER BY bm25(arch) LIMIT 50",
                    (fts_query,),
                )
                for idx, snip in cur.fetchall():
                    bm25_order.append(idx)
                    snips[idx] = snip or ""
            except Exception:
                pass
        if not bm25_order:
            # FTS5 unavailable or no hits — term-frequency fallback.
            scored = []
            for i, _r, c in self.rows:
                lc = c.lower()
                score = sum(lc.count(t) for t in terms) / (1 + len(c) / 4000)
                if score > 0:
                    scored.append((score, i))
            scored.sort(key=lambda x: -x[0])
            bm25_order = [i for _s, i in scored[:50]]

        cosine_order: list[int] = []
        try:
            import numpy as np
            n_terms = len(terms)
            mat = np.zeros((len(self.rows), n_terms), dtype=np.float64)
            for d, (_i, _r, c) in enumerate(self.rows):
                lc = c.lower()
                for t_i, t in enumerate(terms):
                    if t in lc:
                        mat[d, t_i] = lc.count(t)
            qv = np.ones(n_terms, dtype=np.float64)
            qn = float(np.linalg.norm(qv)) or 1.0
            dn = np.linalg.norm(mat, axis=1)
            dn = np.where(dn == 0.0, 1.0, dn)
            cos = (mat @ qv) / (dn * qn)
            order = np.argsort(-cos)
            cosine_order = [
                self.rows[int(d)][0] for d in order if cos[int(d)] > 0
            ][:50]
        except ImportError:
            pass

        if cosine_order:
            scores: dict[int, float] = {}
            for rank, idx in enumerate(bm25_order, start=1):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank)
            for rank, idx in enumerate(cosine_order, start=1):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank)
            ordered = [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])][:top_k]
        else:
            ordered = bm25_order[:top_k]

        hits = []
        for idx in ordered:
            pair = self._by_idx.get(idx)
            if not pair:
                continue
            role, content = pair
            lc = content.lower()
            first = min((lc.find(t) for t in terms if lc.find(t) >= 0), default=0)
            start = max(0, first - excerpt_chars // 4)
            snip = snips.get(idx, "")
            head = f"--- result (message #{idx}, role={role}) ---\n"
            if snip:
                head += f"[match: {snip[:200]}]\n"
            hits.append(head + content[start:start + excerpt_chars])
        return "\n\n".join(hits) if hits else "(no results)"


def keyword_search(archive: list, query: str, top_k: int = 6, excerpt_chars: int = 2500) -> str:
    """Simulate session_search over an archive (prefix discard set or full lineage).

    BM25 via in-memory FTS5, fused with cosine over query-term count vectors
    (numpy; skipped if numpy is missing) using reciprocal rank fusion.
    """
    import sqlite3 as _sq

    terms = [t.lower() for t in _TERM_RE.findall(query)]
    if not terms:
        return "(no results)"
    rows = [
        (i, m.get("role") or "", m["content"])
        for i, m in enumerate(archive)
        if isinstance(m.get("content"), str) and len(m["content"]) >= 20
    ]

    def _excerpts(ordered_idx: list[int], snips: dict[int, str] | None = None) -> str:
        hits = []
        by_idx = {i: (r, c) for i, r, c in rows}
        for idx in ordered_idx:
            pair = by_idx.get(idx)
            if not pair:
                continue
            role, content = pair
            lc = content.lower()
            first = min((lc.find(t) for t in terms if lc.find(t) >= 0), default=0)
            start = max(0, first - excerpt_chars // 4)
            snip = (snips or {}).get(idx, "")
            head = f"--- result (message #{idx}, role={role}) ---\n"
            if snip:
                head += f"[match: {snip[:200]}]\n"
            hits.append(head + content[start:start + excerpt_chars])
        return "\n\n".join(hits) if hits else "(no results)"

    bm25_order: list[int] = []
    snips: dict[int, str] = {}
    try:
        db = _sq.connect(":memory:")
        db.execute("CREATE VIRTUAL TABLE arch USING fts5(content, role UNINDEXED, idx UNINDEXED)")
        db.executemany(
            "INSERT INTO arch (content, role, idx) VALUES (?, ?, ?)",
            [(c, r, i) for i, r, c in rows],
        )
        fts_query = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
        cur = db.execute(
            "SELECT idx, snippet(arch, 0, '', '', ' … ', 40) AS snip "
            "FROM arch WHERE arch MATCH ? ORDER BY bm25(arch) LIMIT 50",
            (fts_query,),
        )
        for idx, snip in cur.fetchall():
            bm25_order.append(idx)
            snips[idx] = snip or ""
        db.close()
    except _sq.OperationalError:
        scored = []
        for i, r, c in rows:
            lc = c.lower()
            score = sum(lc.count(t) for t in terms) / (1 + len(c) / 4000)
            if score > 0:
                scored.append((score, i))
        scored.sort(key=lambda x: -x[0])
        bm25_order = [i for _s, i in scored[:50]]

    cosine_order: list[int] = []
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None and rows:
        # Term-document matrix over query terms only; cosine of L2-normalised counts.
        n_terms = len(terms)
        mat = np.zeros((len(rows), n_terms), dtype=np.float64)
        for d, (_i, _r, c) in enumerate(rows):
            lc = c.lower()
            for t_i, t in enumerate(terms):
                if t in lc:
                    mat[d, t_i] = lc.count(t)
        qv = np.ones(n_terms, dtype=np.float64)
        qn = np.linalg.norm(qv)
        dn = np.linalg.norm(mat, axis=1)
        dn = np.where(dn == 0.0, 1.0, dn)
        cos = (mat @ qv) / (dn * (qn or 1.0))
        order = np.argsort(-cos)
        cosine_order = [
            rows[int(d)][0] for d in order if cos[int(d)] > 0
        ][:50]

    if cosine_order:
        scores: dict[int, float] = {}
        for rank, idx in enumerate(bm25_order, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank)
        for rank, idx in enumerate(cosine_order, start=1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank)
        ordered = [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])][:top_k]
    else:
        ordered = bm25_order[:top_k]
    return _excerpts(ordered, snips)


EVAL_USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0}


def _call(prompt: str, max_tokens: int = 2000) -> str:
    from agent.auxiliary_client import call_llm

    resp = call_llm(
        messages=[{"role": "user", "content": prompt}],
        task="compression",
        max_tokens=max_tokens,
        temperature=0.0,  # deterministic: same questions/answers across runs
    )
    usage = getattr(resp, "usage", None)
    if usage is not None:
        EVAL_USAGE["calls"] += 1
        EVAL_USAGE["prompt_tokens"] += int(getattr(usage, "prompt_tokens", 0) or 0)
        EVAL_USAGE["completion_tokens"] += int(getattr(usage, "completion_tokens", 0) or 0)
        details = getattr(usage, "prompt_tokens_details", None)
        EVAL_USAGE["cached_tokens"] += int(getattr(details, "cached_tokens", 0) or 0) if details else 0
    if hasattr(resp, "choices"):
        return resp.choices[0].message.content or ""
    return str(resp)


def _extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("["), text.find("{")) if i >= 0], default=0)
    return json.JSONDecoder().raw_decode(text[start:])[0]


def serialize_for_exam(messages, char_cap: int = 600_000) -> str:
    parts = []
    for m in messages:
        role = m.get("role")
        c = m.get("content")
        if not isinstance(c, str) or not c:
            continue
        if role == "system":
            continue
        parts.append(f"[{role}] {c}")
    text = "\n\n".join(parts)
    if len(text) > char_cap:
        half = char_cap // 2
        text = text[:half] + "\n\n...[middle elided for exam generation]...\n\n" + text[-half:]
    return text


def _message_content_text(m) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for item in c:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text") or json.dumps(item, default=str))
            elif item is not None:
                parts.append(str(item))
        return "\n".join(parts)
    if c is None:
        return ""
    return json.dumps(c, default=str)


def flatten_transcript_text(messages) -> str:
    """Flatten all message content into one string for literal-span search."""
    return "\n".join(_message_content_text(m) for m in messages)


def question_signal_type(qa: dict) -> str:
    st = qa.get("signal_type")
    if not st:
        return PRIMARY_SIGNAL
    return st


def _recall_pct(scores) -> float:
    if not scores:
        return 0.0
    return round(100 * sum(scores) / (2 * len(scores)), 1)


def wilson_ci(recall_pct: float, n: int) -> tuple[float, float]:
    """Wilson-style 95% CI. Returns (center, half) as proportions, not percents."""
    if n <= 0:
        return 0.0, 0.0
    p = recall_pct / 100.0
    center = (p * n + 2) / (n + 4)
    half = 1.96 * math.sqrt(center * (1.0 - center) / (n + 4))
    return center, half


def combined_score(before_tokens: int, after_tokens: int, recall_pct: float) -> tuple[float, float]:
    ratio = (after_tokens / before_tokens) if before_tokens else 0.0
    combined = (recall_pct / (ratio * 100.0)) if ratio else 0.0
    return ratio, combined


def output_tokens_per_recall_point(after_tokens: int, recall_pct: float, n: int) -> float:
    return after_tokens / max(recall_pct / 100.0 * n, 0.01)


def extract_compacted_summary_head(compressed, n: int = HEAD_HIT_CHARS) -> str:
    """First n chars of the compacted summary message (user/assistant + preamble)."""
    for m in compressed:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        text = _message_content_text(m)
        if not text:
            continue
        if any(marker.lower() in text.lower() for marker in SUMMARY_PREAMBLE_MARKERS):
            return text[:n]
    return ""


def compute_head_hit_rate(questions, summary_head: str) -> float:
    easy = [qa for qa in questions if qa.get("difficulty") == "easy"]
    if not easy:
        return 0.0
    head_lc = (summary_head or "").lower()
    hits = 0
    for qa in easy:
        gold = qa.get("gold") or ""
        if gold and gold.lower() in head_lc:
            hits += 1
    return round(hits / len(easy), 4)


def score_by_signal_and_difficulty(results, questions):
    """Primary recall is TOKEN_EFFICIENT_SIGNAL only (absent signal_type counts as that)."""
    buckets = {st: [] for st in SIGNAL_TYPES}
    primary = []
    tiers = {}
    for r, qa in zip(results, questions):
        st = question_signal_type(qa)
        buckets.setdefault(st, []).append(r["score"])
        if st == PRIMARY_SIGNAL:
            primary.append(r["score"])
            d = qa.get("difficulty")
            if d:
                tiers.setdefault(d, []).append(r["score"])
    by_signal_type = {
        st: {"recall_pct": _recall_pct(ss), "n": len(ss)}
        for st, ss in buckets.items()
    }
    by_difficulty = {d: _recall_pct(ss) for d, ss in tiers.items()} if tiers else {}
    return _recall_pct(primary), len(primary), by_difficulty, by_signal_type, primary


def decorate_arm_metrics(summary: dict, n: int, head_hit_rate: float | None = None) -> dict:
    before = summary["before_tokens"]
    after = summary["after_tokens"]
    recall_pct = summary["recall_pct"]
    ratio, combined = combined_score(before, after, recall_pct)
    _center, half = wilson_ci(recall_pct, n)
    half_pct = half * 100.0
    summary["ratio"] = round(ratio, 6)
    summary["combined"] = round(combined, 6)
    summary["ci_width"] = round(2.0 * half_pct, 1)
    summary["output_tokens_per_recall_point"] = round(
        output_tokens_per_recall_point(after, recall_pct, n), 1
    )
    if head_hit_rate is not None:
        summary["head_hit_rate"] = head_hit_rate
    print(f"recall={recall_pct:.1f}% ± {half_pct:.1f}% (95% CI, N={n})")
    return summary


def validate_questions(questions, messages) -> tuple[int, list, dict]:
    """Literal-span gate: each question's `where` must appear in the transcript."""
    corpus = flatten_transcript_text(messages).lower()
    invalid = []
    valid = 0
    valid_by_tier: dict[str, int] = {}
    for i, qa in enumerate(questions):
        qid = qa.get("id", i)
        where = qa.get("where")
        diff = qa.get("difficulty") or "untiered"
        if not where or not str(where).strip():
            invalid.append({
                "id": qid,
                "reason": "missing where field",
                "q": qa.get("q", "")[:120],
            })
            continue
        if str(where).lower() not in corpus:
            invalid.append({
                "id": qid,
                "reason": "where span not found in transcript (literal-span gate)",
                "where": where,
                "q": qa.get("q", "")[:120],
            })
            continue
        valid += 1
        valid_by_tier[diff] = valid_by_tier.get(diff, 0) + 1
    return valid, invalid, valid_by_tier


def report_question_validation(
    valid: int, invalid: list, valid_by_tier: dict, questions: list,
) -> bool:
    """Print gate results. Returns True if the eval may proceed."""
    print(f"literal-span gate: valid={valid} invalid={len(invalid)} total={len(questions)}")
    for row in invalid:
        print(f"  INVALID id={row['id']}: {row['reason']}"
              + (f" | where={row['where']!r}" if row.get("where") is not None else "")
              + (f" | q={row.get('q', '')}" if row.get("q") else ""))
    tiers = sorted({qa.get("difficulty") or "untiered" for qa in questions})
    ok = True
    for tier in tiers:
        count = valid_by_tier.get(tier, 0)
        print(f"  valid[{tier}]={count} (need >={MIN_VALID_PER_TIER})")
        if count < MIN_VALID_PER_TIER:
            ok = False
    if not tiers:
        print(f"  valid per tier: none (need >={MIN_VALID_PER_TIER} per difficulty tier)")
        ok = False
    if not ok:
        print("ABORT: literal-span gate failed (valid count < 9 per difficulty tier)")
    return ok


def summarized_region(compressor_module, messages):
    """The middle region the current policy would summarize: everything
    between the protected head and the tail cut. Questions come from here."""
    from agent.context_compressor import ContextCompressor

    comp = ContextCompressor(model=EVAL_MODEL, quiet_mode=True)
    head_end = comp.protect_first_n
    tail_start = comp._find_tail_cut_by_tokens(messages, head_end)
    return messages[head_end:tail_start]


def generate_questions(messages, n: int, cache_path: Path) -> list:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    import agent.context_compressor as cc

    region = summarized_region(cc, messages)
    # 80k chars (~20k tok) keeps exam-gen inside aux context; head+tail still spans the region.
    text = serialize_for_exam(region, char_cap=80_000)
    raw = _call(QUESTION_PROMPT.format(n=n, transcript=text), max_tokens=8000)
    try:
        parsed = _extract_json(raw)
    except Exception:
        logger.warning("question JSON parse failed; raw head=%r", (raw or "")[:400])
        raise
    if isinstance(parsed, dict):
        parsed = parsed.get("questions") or parsed.get("items") or parsed.get("data") or [parsed]
    if not isinstance(parsed, list):
        logger.warning("question JSON was %s; raw head=%r", type(parsed).__name__, (raw or "")[:400])
        raise ValueError(f"questions JSON was {type(parsed).__name__}, not a list")
    questions = parsed[:n]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(questions, indent=1), encoding="utf-8")
    return questions


def _apply_fork_runtime_attrs(comp, spec: dict) -> None:
    """Set session_type / importance_biased_prune_enabled on the compressor if present."""
    merged = {}
    merged.update(spec.get("ctor") or {})
    merged.update(spec.get("attrs") or {})
    for key in FORK_RUNTIME_ATTRS:
        if key in merged:
            setattr(comp, key, merged[key])


def _annotate_result_entry(entry: dict, qa: dict) -> dict:
    if "difficulty" in qa:
        entry["difficulty"] = qa["difficulty"]
    if "signal_type" in qa:
        entry["signal_type"] = qa["signal_type"]
    return entry


def classifier_decision_from_compressor(comp) -> dict:
    """What the session-type classifier chose, for the eval scorecard.

    Reads ``comp.routing_hint`` (preferred) and ``comp._session_type``. Empty
    when the classifier did not run.
    """
    hint = getattr(comp, "routing_hint", None)
    if not isinstance(hint, dict):
        hint = {}
    session_type = hint.get("session_type")
    if session_type is None:
        session_type = getattr(comp, "_session_type", None)
    return {
        "session_type": session_type,
        "confidence": hint.get("confidence"),
        "compression_profile": hint.get("compression_profile"),
    }


def policy_label_for_arm(name: str, spec: dict, comp, with_recovery: bool = False,
                        recovery_full: bool = False) -> str:
    """Scorecard policy name; classifier arms include the detected profile."""
    label = name
    if (spec.get("attrs") or {}).get("use_classifier"):
        profile = None
        hint = getattr(comp, "routing_hint", None)
        if isinstance(hint, dict):
            profile = hint.get("compression_profile")
        if profile:
            label = f"{name}({profile})"
    if recovery_full:
        label = f"{label}+recovery_full"
    elif with_recovery:
        label = f"{label}+recovery"
    return label


_PRICES: dict = {}


def openrouter_price_usd(model: str, input_tokens: int, output_tokens: int):
    """Price a call from OpenRouter's public catalog (per-token USD); None when unknown.

    Used as a common yardstick across arms — a summary routed through another
    provider is priced at the OpenRouter list price for that model id.
    """
    if not _PRICES:
        try:
            import urllib.request
            with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as r:
                for m in json.load(r)["data"]:
                    _PRICES[m["id"]] = m.get("pricing") or {}
        except Exception:
            _PRICES["__failed__"] = {}
    p = _PRICES.get(model) or _PRICES.get(model.split(":")[0])
    if not p:
        return None
    return input_tokens * float(p.get("prompt") or 0) + output_tokens * float(p.get("completion") or 0)


class _AuxMeter:
    """Wraps the compressor's module-level ``call_llm`` binding to total summary usage."""

    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.models: list = []

    def __enter__(self):
        import agent.context_compressor as cc
        self._cc, self._orig = cc, cc.call_llm

        def metered(*args, **kwargs):
            resp = self._orig(*args, **kwargs)
            self.calls += 1
            usage = getattr(resp, "usage", None) or (resp.get("usage") if isinstance(resp, dict) else None)
            if usage is not None:
                get = (lambda k: getattr(usage, k, None)) if not isinstance(usage, dict) else usage.get
                self.input_tokens += int(get("prompt_tokens") or 0)
                self.output_tokens += int(get("completion_tokens") or 0)
            route = kwargs.get("route_info") or {}
            model = route.get("model") or kwargs.get("model") or getattr(resp, "model", None)
            if model and model not in self.models:
                self.models.append(model)
            return resp

        cc.call_llm = metered
        return self

    def __exit__(self, *exc):
        self._cc.call_llm = self._orig

    def summary(self) -> dict:
        model = self.models[0] if self.models else EVAL_MODEL
        return {
            "compaction_calls": self.calls,
            "compaction_input_tokens": self.input_tokens,
            "compaction_output_tokens": self.output_tokens,
            "compaction_model": model,
            "compaction_cost_usd": openrouter_price_usd(model, self.input_tokens, self.output_tokens),
        }


def _compress_with_policy(spec: dict, messages) -> tuple:
    """Run one policy; returns (compressed, compressor, compaction-cost dict)."""
    if spec.get("engine") == "jev":
        from evals.compaction.jev_arm import JevCompactor, JevOptions

        comp = JevCompactor(options=JevOptions(**(spec.get("jev") or {})))
        try:
            compressed = comp.compress(copy.deepcopy(messages), current_tokens=total_tokens(messages), force=True)
        except ValueError as e:
            # The plugin throws here and Claude Code falls back to its built-in
            # summary; record the fallback rather than scoring an uncompressed arm.
            comp._last_summary_error = str(e)
            return None, comp, {"jev_fallback": str(e), "compaction_calls": comp.usage.requests,
                                "compaction_cost_usd": comp.usage.cost_usd}
        cost = {
            "compaction_calls": comp.usage.requests,
            "compaction_input_tokens": comp.usage.input_tokens,
            "compaction_output_tokens": comp.usage.output_tokens,
            "compaction_model": comp.usage.models[0] if comp.usage.models else "jev",
            "compaction_cost_usd": comp.usage.cost_usd,
            "jev_stats": comp.stats,
        }
        return compressed, comp, cost

    from agent.context_compressor import ContextCompressor

    comp = apply_policy(ContextCompressor(model=EVAL_MODEL, quiet_mode=True), spec)
    for key, value in (spec.get("ctor") or {}).items():
        setattr(comp, key, value)
    with _AuxMeter() as meter:
        compressed = comp.compress(copy.deepcopy(messages), current_tokens=total_tokens(messages), force=True)
    return compressed, comp, meter.summary()


def run_policy(name: str, spec: dict, messages, questions, out_dir: Path,
               with_recovery: bool = False, full_lineage=None) -> dict:
    before = copy.deepcopy(messages)
    _original = before
    t0 = time.time()
    compressed, comp, compaction_cost = _compress_with_policy(spec, messages)
    elapsed = time.time() - t0
    recovery_full = bool(full_lineage is not None)
    if recovery_full:
        label = f"{name}+recovery_full"
    elif with_recovery:
        label = f"{name}+recovery"
    else:
        label = name
    if compressed is None:
        summary = {"policy": label, "before_tokens": total_tokens(before), "after_tokens": None,
                   "recall_pct": None, "compress_seconds": round(elapsed, 1),
                   "summary_error": comp._last_summary_error, **compaction_cost}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{label.replace('+', '_')}.json").write_text(
            json.dumps({"summary": summary, "results": []}, indent=1), encoding="utf-8")
        return summary

    # The archived region = original messages that did not survive verbatim.
    # Use _original (pre-telegraphic) so archive content matches raw session_search
    # and before_tokens reflects unmodified history (F13).
    surviving = set()
    for m in compressed:
        c = m.get("content")
        if isinstance(c, str) and c:
            surviving.add(c[:200])
    archive = [
        m for m in _original
        if isinstance(m.get("content"), str) and (m.get("content") or "")[:200] not in surviving
    ]
    # Production session_search indexes the whole DB, not just the compaction
    # discard set. When full_lineage is provided, search that instead.
    # Build the ArchiveIndex once per arm (not once per question) — avoids
    # rebuilding the FTS5 table and numpy matrix on every keyword_search call.
    _search_corpus = full_lineage if full_lineage is not None else archive
    _index = ArchiveIndex(_search_corpus) if with_recovery else None

    context_text = serialize_for_exam(compressed, char_cap=700_000)
    results = []
    for qa in questions:
        hops = 0
        queries = []
        if with_recovery and _index is not None:
            # The summary (session log, verbatim user msgs, recovery footer) sits
            # near the FRONT of the serialized context; give the query writer
            # that portion plus the recent tail so it can mine anchor
            # identifiers (PR numbers, paths, error strings) for the query.
            hint = context_text[:60_000] + "\n...\n" + context_text[-8_000:]
            query = _call(
                SEARCH_QUERY_PROMPT.format(
                    context_hint=hint, question=qa["q"],
                ),
                max_tokens=100,
            ).strip().strip('"')
            queries.append(query)
            search_results = _index.search(query)
            hops = 1
            if search_results == "(no results)" or len(search_results) < 200:
                hop_ctx = (search_results or "")[:500]
                query = _call(
                    SEARCH_QUERY_PROMPT.format(
                        context_hint=hint + "\n\nFIRST_SEARCH_SNIPPETS:\n" + hop_ctx,
                        question=qa["q"],
                    ),
                    max_tokens=100,
                ).strip().strip('"')
                queries.append(query)
                search_results = _index.search(query)
                hops = 2
            answer = _call(
                ANSWER_WITH_RECOVERY_PROMPT.format(
                    context=context_text,
                    search_results=search_results,
                    question=qa["q"],
                ),
                max_tokens=400,
            )
            query = " || ".join(queries)
        else:
            query = None
            answer = _call(ANSWER_PROMPT.format(context=context_text, question=qa["q"]), max_tokens=400)
        verdict_raw = _call(JUDGE_PROMPT.format(question=qa["q"], gold=qa["gold"], answer=answer), max_tokens=300)
        try:
            verdict = _extract_json(verdict_raw)
        except Exception as exc:
            logger.warning("eval runner: scoring suppressed: %s", exc)
            verdict = {"score": 0, "why": f"judge parse failure: {verdict_raw[:100]}"}
        entry = {"q": qa["q"], "gold": qa["gold"], "answer": answer, **verdict,
                 "recovery_hops": None, "recovery_corpus": None}
        if query is not None:
            entry["search_query"] = query
            entry["recovery_hops"] = hops
            entry["recovery_corpus"] = "full_lineage" if recovery_full else "prefix_archive"
        _annotate_result_entry(entry, qa)
        results.append(entry)

    scored = [r["score"] for r in results]
    recall_pct, n_primary, by_difficulty, by_signal_type, _primary = (
        score_by_signal_and_difficulty(results, questions)
    )
    label = policy_label_for_arm(name, spec, comp, with_recovery=with_recovery,
                                 recovery_full=recovery_full)
    summary_head = extract_compacted_summary_head(compressed)
    hit_rate = compute_head_hit_rate(questions, summary_head)
    classifier_decision = classifier_decision_from_compressor(comp)
    summary = {
        "policy": label,
        "before_tokens": total_tokens(_original),
        "after_tokens": total_tokens(compressed),
        "after_msgs": len(compressed),
        "compress_seconds": round(elapsed, 1),
        "recall_pct": recall_pct,
        "scores": scored,
        "by_difficulty": by_difficulty,
        "by_signal_type": by_signal_type,
        "summary_error": getattr(comp, "_last_summary_error", None),
        "head_hit_rate": hit_rate,
        "classifier_decision": classifier_decision,
        "classified_info": classifier_decision,
        **compaction_cost,
    }
    decorate_arm_metrics(summary, n_primary, head_hit_rate=hit_rate)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{label.replace('+', '_')}.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8"
    )
    return summary


def uncompacted_control(messages, questions, out_dir: Path) -> dict:
    """Control: no compression at all — answer from the full transcript."""
    context_text = serialize_for_exam(messages, char_cap=600_000)  # ~150K tok, within 200K API limit
    results = []
    for qa in questions:
        answer = _call(ANSWER_PROMPT.format(context=context_text, question=qa["q"]), max_tokens=400)
        verdict_raw = _call(JUDGE_PROMPT.format(question=qa["q"], gold=qa["gold"], answer=answer), max_tokens=300)
        try:
            verdict = _extract_json(verdict_raw)
        except Exception as exc:
            logger.warning("eval runner: scoring suppressed: %s", exc)
            verdict = {"score": 0, "why": "judge parse failure"}
        entry = {"q": qa["q"], **verdict, "answer": answer}
        _annotate_result_entry(entry, qa)
        results.append(entry)
    scored = [r["score"] for r in results]
    recall_pct, n_primary, by_difficulty, by_signal_type, _primary = (
        score_by_signal_and_difficulty(results, questions)
    )
    summary_head = serialize_for_exam(messages, char_cap=HEAD_HIT_CHARS)[:HEAD_HIT_CHARS]
    hit_rate = compute_head_hit_rate(questions, summary_head)
    tok = total_tokens(messages)
    ctl = {
        "policy": "uncompacted_control",
        "before_tokens": tok,
        "after_tokens": tok,
        "after_msgs": len(messages),
        "compress_seconds": 0.0,
        "recall_pct": recall_pct,
        "scores": scored,
        "by_difficulty": by_difficulty,
        "by_signal_type": by_signal_type,
        "summary_error": None,
        "head_hit_rate": hit_rate,
    }
    decorate_arm_metrics(ctl, n_primary, head_hit_rate=hit_rate)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "uncompacted_control.json").write_text(
        json.dumps({"summary": ctl, "results": results}, indent=1), encoding="utf-8"
    )
    return ctl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--cap-tokens", type=int, default=500_000)
    ap.add_argument("--policies", default="current+recovery",
                    help="comma-separated arms; <name>+recovery = prefix archive; "
                         "<name>+recovery_full = full lineage (or pass --full-lineage). "
                         "Bare <name> is closed-book, opt-in only.")
    ap.add_argument("--full-lineage", default=None,
                    help="JSON transcript of the full reconstructed lineage for the "
                         "session_search sim (production model). Used by +recovery_full "
                         "and, when set, by every +recovery arm.")
    ap.add_argument("--questions", type=int, default=15)
    ap.add_argument("--out", required=True)
    ap.add_argument("--also-uncompacted", action="store_true")
    ap.add_argument(
        "--validate-questions",
        action="store_true",
        help="Check each question's 'where' quote against the raw transcript "
             "(literal-span gate) before any compression. Abort if valid < 9 per tier.",
    )
    args = ap.parse_args()

    messages = load_transcript(args.transcript, cap_tokens=args.cap_tokens)
    out_dir = Path(args.out)
    # Key on file mtime+size + question count + cap — O(1), no re-read of potentially 500MB file.
    # A content-identical rename would reuse the cache; an in-place replacement (different mtime)
    # correctly busts it.
    _tstat = Path(args.transcript).stat()
    tid = hashlib.md5(
        f"{args.transcript}|mtime={_tstat.st_mtime}|size={_tstat.st_size}|n={args.questions}|cap={args.cap_tokens}".encode()
    ).hexdigest()[:10]
    tid = hashlib.md5(f"{args.transcript}@{args.cap_tokens}".encode()).hexdigest()[:10]
    qcache = out_dir / f"questions-{tid}.json"
    questions = generate_questions(messages, args.questions, qcache)
    print(f"{len(questions)} questions ready ({qcache})")

    if args.validate_questions:
        raw_messages = load_transcript(args.transcript, cap_tokens=None)
        valid, invalid, valid_by_tier = validate_questions(questions, raw_messages)
        if not report_question_validation(valid, invalid, valid_by_tier, questions):
            sys.exit(1)

    summaries = []
    if args.also_uncompacted:
        ctl = uncompacted_control(messages, questions, out_dir)
        summaries.append(ctl)
        print(json.dumps(ctl, indent=1))

    policy_names = [n.strip() for n in args.policies.split(",") if n.strip()]
    need_full = bool(args.full_lineage) or any(n.endswith("+recovery_full") for n in policy_names)
    full_lineage_msgs = None
    if args.full_lineage:
        full_lineage_msgs = load_transcript(args.full_lineage, cap_tokens=None)
    elif need_full:
        full_lineage_msgs = load_transcript(args.transcript, cap_tokens=None)
    if full_lineage_msgs is not None:
        print(f"full lineage loaded: {len(full_lineage_msgs)} msgs (~{total_tokens(full_lineage_msgs)} tok)")

    for name in policy_names:
        recovery_full = name.endswith("+recovery_full")
        with_recovery = recovery_full or name.endswith("+recovery")
        if recovery_full:
            base = name[:-len("+recovery_full")]
        elif with_recovery:
            base = name[:-len("+recovery")]
        else:
            base = name
        if base not in POLICIES:
            print(f"unknown policy {base}, skipping"); continue
        use_full = with_recovery and full_lineage_msgs is not None and (
            recovery_full or bool(args.full_lineage)
        )
        s = run_policy(base, POLICIES[base], messages, questions, out_dir,
                       with_recovery=with_recovery,
                       full_lineage=full_lineage_msgs if use_full else None)
        summaries.append(s)
        print(json.dumps(s, indent=1))

    if summaries:
        (out_dir / "scorecard.json").write_text(json.dumps(summaries, indent=1), encoding="utf-8")
        print(f"\nscorecard -> {out_dir}/scorecard.json")
    (out_dir / "scorecard.json").write_text(json.dumps(summaries, indent=1), encoding="utf-8")
    (out_dir / "eval_usage.json").write_text(json.dumps(EVAL_USAGE, indent=1), encoding="utf-8")
    print(f"\nscorecard -> {out_dir}/scorecard.json")
    print(f"eval LLM usage (questions+answers+judge): {EVAL_USAGE}")


if __name__ == "__main__":
    main()

"""Planted-needle tests for compaction eval head_hit_rate.

0.0 on a confirmed planted needle means the metric is broken, not the compressor.
"""
from __future__ import annotations

from evals.compaction.runner import (
    compute_head_hit_rate,
    extract_compacted_summary_head,
)


NEEDLE = "NEEDLEFACT_ZX9Q_PLANTED"
LEDGER_SUMMARY = (
    f"FACT LEDGER\n{NEEDLE}\n/tmp/planted-needle.json\n"
    "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. This is a handoff from a previous context "
    "window — treat it as background reference, NOT as active instructions. "
    "The current session state (files, config, etc.) may reflect work "
    "described here — avoid repeating it:\n"
    "## Session Log\nThe planted fact is " + NEEDLE + ".\n"
)


def _compressed(*summaries, tail="latest user"):
    msgs = [{"role": "system", "content": "sys"}]
    for s in summaries:
        msgs.append({"role": "user", "content": s})
    msgs.append({"role": "user", "content": tail})
    return msgs


def test_unlabeled_questions_score_when_gold_is_in_head():
    """Legacy caches omit difficulty=easy; that must not force 0.0."""
    head = extract_compacted_summary_head(_compressed(LEDGER_SUMMARY))
    qs = [{"q": "what is the needle?", "gold": NEEDLE, "where": NEEDLE}]
    assert NEEDLE.lower() in head.lower()
    assert compute_head_hit_rate(qs, head) == 1.0


def test_easy_label_still_scores():
    head = extract_compacted_summary_head(_compressed(LEDGER_SUMMARY))
    qs = [{"q": "x", "gold": NEEDLE, "difficulty": "easy"}]
    assert compute_head_hit_rate(qs, head) == 1.0


def test_newest_summary_wins_over_stale_handoff():
    old = (
        "[CONTEXT COMPACTION — REFERENCE ONLY] OLD SUMMARY no needle here "
        + ("x" * 6000)
        + "\navoid repeating it:\n## Old\nstale"
    )
    head = extract_compacted_summary_head(_compressed(old, LEDGER_SUMMARY))
    qs = [{"q": "x", "gold": NEEDLE, "difficulty": "easy"}]
    assert NEEDLE.lower() in head.lower()
    assert compute_head_hit_rate(qs, head) == 1.0


def test_preamble_does_not_eat_the_window():
    """Gold only in the body after a long legalese prefix must still hit."""
    prefix = (
        "[CONTEXT COMPACTION — REFERENCE ONLY] " + ("legalese " * 400)
        + "avoid repeating it:\n"
    )
    body = f"## Session Log\nremember {NEEDLE} forever\n"
    head = extract_compacted_summary_head(_compressed(prefix + body))
    assert NEEDLE.lower() in head.lower()
    qs = [{"q": "x", "gold": NEEDLE}]
    assert compute_head_hit_rate(qs, head) == 1.0


def test_where_backtick_span_counts_as_needle():
    qs = [{
        "q": "threshold?",
        "gold": "0.35",
        "where": "Line 26: `JACCARD_EDGE = 0.35`",
    }]
    head = "kept identifier JACCARD_EDGE = 0.35 in the ledger"
    assert compute_head_hit_rate(qs, head) == 1.0
    assert compute_head_hit_rate(qs, "nothing relevant here") == 0.0


def test_miss_stays_zero():
    head = extract_compacted_summary_head(_compressed(LEDGER_SUMMARY))
    qs = [{"q": "x", "gold": "ABSENT_TOKEN_QQQ", "difficulty": "easy"}]
    assert compute_head_hit_rate(qs, head) == 0.0

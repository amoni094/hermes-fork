"""Unit tests for runner.py: validate_questions gate and run_policy_cycles.

Run: PYTHONPATH=hermes-fork python3 -m pytest hermes-fork/tests/test_runner_v2.py -v
"""
from __future__ import annotations
import json, sys, types
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------
# Import runner without executing main()
# ---------------------------------------------------------------------------
from evals.compaction.runner import (  # noqa: E402
    validate_questions,
    report_question_validation,
    flatten_transcript_text,
    _recall_pct,
    wilson_ci,
    compute_head_hit_rate,
    run_policy_cycles,
    QUESTION_PROMPT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_messages(n: int = 20) -> list[dict]:
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"message content {i} with token abc{i:04d}"})
    return msgs


def _make_questions(messages: list[dict]) -> list[dict]:
    """Generate questions whose gold and where appear literally in messages."""
    qs = []
    for i, m in enumerate(messages[:6]):
        content = m["content"]
        token = f"abc{i:04d}"  # definitely in the transcript
        qs.append({
            "q": f"What token appears in message {i}?",
            "gold": token,
            "where": content,
            "difficulty": "easy" if i < 2 else ("medium" if i < 4 else "hard"),
            "required_in": "summary" if i < 2 else "archive",
        })
    return qs


# ---------------------------------------------------------------------------
# validate_questions: literal-span gate
# ---------------------------------------------------------------------------

class TestValidateQuestions:
    def test_all_valid(self):
        msgs = _make_messages(10)
        qs = _make_questions(msgs)
        valid, invalid, by_tier = validate_questions(qs, msgs)
        assert valid == len(qs)
        assert invalid == []

    def test_missing_where_field(self):
        msgs = _make_messages(10)
        qs = _make_questions(msgs)
        qs[0].pop("where")
        valid, invalid, _ = validate_questions(qs, msgs)
        assert valid == len(qs) - 1
        assert any(r["reason"] == "missing where field" for r in invalid)

    def test_where_not_in_transcript(self):
        msgs = _make_messages(10)
        qs = _make_questions(msgs)
        qs[1]["where"] = "THIS STRING IS NOT IN ANY MESSAGE XYZZY"
        valid, invalid, _ = validate_questions(qs, msgs)
        assert valid == len(qs) - 1
        assert any("where span not found" in r["reason"] for r in invalid)

    def test_tier_counts(self):
        msgs = _make_messages(10)
        qs = _make_questions(msgs)
        valid, invalid, by_tier = validate_questions(qs, msgs)
        assert by_tier.get("easy", 0) == 2
        assert by_tier.get("medium", 0) == 2
        assert by_tier.get("hard", 0) == 2

    def test_pass_rate_threshold(self):
        msgs = _make_messages(10)
        qs = _make_questions(msgs)
        # Corrupt 3 of 6 where fields
        for i in range(3):
            qs[i]["where"] = "CORRUPTED"
        valid, _, _ = validate_questions(qs, msgs)
        pass_rate = valid / len(qs)
        assert pass_rate < 0.60  # would trigger the warning


# ---------------------------------------------------------------------------
# Question prompt: gold rules
# ---------------------------------------------------------------------------

class TestQuestionPrompt:
    def test_gold_rules_present(self):
        assert "3-80 chars" in QUESTION_PROMPT
        assert "REJECT" in QUESTION_PROMPT
        assert "bare decimals" in QUESTION_PROMPT.lower() or "bare decimal" in QUESTION_PROMPT

    def test_self_check_instruction_present(self):
        assert "SELF-CHECK" in QUESTION_PROMPT

    def test_where_spec_tightened(self):
        # Old spec allowed "short LITERAL quote" with no length bound
        # New spec requires "10-120 char verbatim substring"
        assert "10-120" in QUESTION_PROMPT


# ---------------------------------------------------------------------------
# run_policy_cycles: single-cycle passthrough
# ---------------------------------------------------------------------------

class TestRunPolicyCycles:
    """Test run_policy_cycles with n_cycles=1 delegates to run_policy."""

    def test_single_cycle_calls_run_policy(self, tmp_path):
        """With n_cycles=1, run_policy_cycles should call run_policy and annotate cycle=1."""
        sentinel = {
            "policy": "current",
            "recall_pct": 50.0,
            "before_tokens": 1000,
            "after_tokens": 500,
        }

        with patch("evals.compaction.runner.run_policy", return_value=sentinel) as mock_rp:
            from evals.compaction.policies import POLICIES
            result = run_policy_cycles(
                "current", POLICIES["current"],
                messages=_make_messages(10),
                questions=_make_questions(_make_messages(10)),
                out_dir=tmp_path,
                n_cycles=1,
            )

        assert mock_rp.called
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].get("cycle") == 1

    def test_multi_cycle_structure(self, tmp_path):
        """With n_cycles=3, run_policy_cycles should return 3 summaries with cycle annotations."""
        msgs = _make_messages(20)
        qs = _make_questions(msgs)

        compress_calls = []

        def fake_compress(spec, messages):
            compress_calls.append(len(messages))
            # Return a shorter message list (simulate compaction shrink)
            return messages[:max(1, len(messages) // 2)], MagicMock(
                _last_summary_error=None,
                routing_hint=None,
                _session_type=None,
            ), {
                "compaction_calls": 1,
                "compaction_input_tokens": 100,
                "compaction_output_tokens": 50,
                "compaction_model": "test",
                "compaction_cost_usd": None,
            }

        def fake_call(prompt, max_tokens=2000):
            # Answerer always returns "NOT IN CONTEXT; abc0000"
            if "Score this answer" in prompt:
                return '{"score": 1, "why": "partial"}'
            return "NOT IN CONTEXT; abc0000"

        with (
            patch("evals.compaction.runner._compress_with_policy", side_effect=fake_compress),
            patch("evals.compaction.runner._call", side_effect=fake_call),
        ):
            from evals.compaction.policies import POLICIES
            result = run_policy_cycles(
                "current", POLICIES["current"],
                messages=msgs,
                questions=qs,
                out_dir=tmp_path,
                n_cycles=3,
            )

        assert len(result) == 3
        for i, s in enumerate(result, start=1):
            assert s["cycle"] == i
        # Each cycle compresses the previous output: message count should shrink
        assert compress_calls[0] >= compress_calls[1]
        # Output files written per cycle
        for i in range(1, 4):
            assert (tmp_path / f"cycle{i}").is_dir()

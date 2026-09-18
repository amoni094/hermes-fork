"""Tests for MemForest EventTree partitioning (R1).

Verifies:
  (a) every message is classified into exactly one bucket
  (b) tool_result messages appear before assistant_prose in the prune order
  (c) user messages never appear in the prune list
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so the agent package is importable
# without an installed package (mirrors the pattern used by other test modules).
_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.micro_compaction import (
    PARTITION_PRUNE_WEIGHTS,
    apply_partition_prune_order,
    partition_messages_by_event,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_messages():
    """Return a representative message list covering every event type."""
    return [
        # idx 0  — user
        {"role": "user", "content": "Hello"},
        # idx 1  — assistant_prose
        {"role": "assistant", "content": "Sure, I can help."},
        # idx 2  — tool_call (Anthropic-style list content)
        {"role": "assistant", "content": [{"type": "tool_use", "name": "bash", "input": {}}]},
        # idx 3  — tool_result
        {"role": "tool", "content": "output of bash"},
        # idx 4  — reasoning (thinking block)
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "let me consider..."}]},
        # idx 5  — tool_call (OpenAI-style tool_calls field)
        {"role": "assistant", "tool_calls": [{"id": "c1", "function": {"name": "search"}}]},
        # idx 6  — tool_result (second)
        {"role": "tool", "content": "search results"},
        # idx 7  — user (second)
        {"role": "user", "content": "Follow-up question"},
        # idx 8  — assistant_prose (second)
        {"role": "assistant", "content": "Final answer."},
        # idx 9  — assistant_prose (third — will be in protect_last_n=10 window)
        {"role": "assistant", "content": "One more note."},
        # idx 10 — user (in protect window)
        {"role": "user", "content": "Thanks"},
        # idx 11 — assistant_prose (in protect window)
        {"role": "assistant", "content": "You're welcome."},
    ]


# ---------------------------------------------------------------------------
# (a) All messages are classified
# ---------------------------------------------------------------------------

class TestPartitionMessagesByEvent:
    def test_all_messages_classified(self):
        messages = _make_messages()
        buckets = partition_messages_by_event(messages)

        all_indices = sorted(idx for indices in buckets.values() for idx in indices)
        assert all_indices == list(range(len(messages))), (
            "Some message indices are missing or duplicated in partition buckets"
        )

    def test_no_duplicates_across_buckets(self):
        messages = _make_messages()
        buckets = partition_messages_by_event(messages)

        flat = [idx for indices in buckets.values() for idx in indices]
        assert len(flat) == len(set(flat)), "Duplicate index found across event buckets"

    def test_expected_classifications(self):
        messages = _make_messages()
        buckets = partition_messages_by_event(messages)

        # User messages
        assert 0 in buckets["user"]
        assert 7 in buckets["user"]
        assert 10 in buckets["user"]

        # tool_result
        assert 3 in buckets["tool_result"]
        assert 6 in buckets["tool_result"]

        # tool_call (Anthropic list and OpenAI-style)
        assert 2 in buckets["tool_call"]
        assert 5 in buckets["tool_call"]

        # reasoning
        assert 4 in buckets["reasoning"]

        # assistant_prose
        assert 1 in buckets["assistant_prose"]
        assert 8 in buckets["assistant_prose"]

    def test_empty_messages(self):
        buckets = partition_messages_by_event([])
        assert all(v == [] for v in buckets.values())

    def test_known_partition_labels_present(self):
        buckets = partition_messages_by_event(_make_messages())
        for label in PARTITION_PRUNE_WEIGHTS:
            assert label in buckets, f"Expected bucket '{label}' missing"


# ---------------------------------------------------------------------------
# (b) tool_result messages sort before assistant_prose in prune order
# ---------------------------------------------------------------------------

class TestApplyPartitionPruneOrder:
    def test_tool_result_before_assistant_prose(self):
        """tool_result (weight 0.4) must appear before assistant_prose (weight 0.7)."""
        messages = _make_messages()
        # Use protect_last_n=2 so most messages are eligible.
        prune_order = apply_partition_prune_order(messages, protect_last_n=2)

        buckets = partition_messages_by_event(messages)
        cutoff = len(messages) - 2

        tool_result_indices = {i for i in buckets["tool_result"] if i < cutoff}
        prose_indices = {i for i in buckets["assistant_prose"] if i < cutoff}

        # Find positions in prune_order list
        def first_pos(candidates):
            for pos, idx in enumerate(prune_order):
                if idx in candidates:
                    return pos
            return None

        tr_pos = first_pos(tool_result_indices)
        prose_pos = first_pos(prose_indices)

        assert tr_pos is not None, "No tool_result index in prune order"
        assert prose_pos is not None, "No assistant_prose index in prune order"
        assert tr_pos < prose_pos, (
            f"Expected tool_result (pos {tr_pos}) before assistant_prose (pos {prose_pos})"
        )

    # (c) user messages never appear in prune list
    def test_user_messages_never_pruned(self):
        messages = _make_messages()
        prune_order = apply_partition_prune_order(messages, protect_last_n=0)

        user_indices = {i for i, m in enumerate(messages) if m.get("role") == "user"}
        overlap = user_indices & set(prune_order)
        assert not overlap, f"User messages found in prune order: {overlap}"

    def test_protect_last_n_respected(self):
        messages = _make_messages()
        protect_last_n = 5
        cutoff = len(messages) - protect_last_n
        prune_order = apply_partition_prune_order(messages, protect_last_n=protect_last_n)

        protected = {i for i in prune_order if i >= cutoff}
        assert not protected, f"Protected indices in prune order: {protected}"

    def test_no_duplicates_in_prune_order(self):
        prune_order = apply_partition_prune_order(_make_messages(), protect_last_n=2)
        assert len(prune_order) == len(set(prune_order)), "Duplicate indices in prune order"

    def test_empty_messages_returns_empty(self):
        assert apply_partition_prune_order([], protect_last_n=10) == []

    def test_weight_ordering(self):
        """Indices in prune order must be non-decreasing in their event-type weight."""
        messages = _make_messages()
        buckets = partition_messages_by_event(messages)
        idx_to_weight = {}
        for label, indices in buckets.items():
            for idx in indices:
                idx_to_weight[idx] = PARTITION_PRUNE_WEIGHTS[label]

        prune_order = apply_partition_prune_order(messages, protect_last_n=2)
        weights = [idx_to_weight[i] for i in prune_order]
        for a, b in zip(weights, weights[1:]):
            assert a <= b, f"Prune order weight decreased: {a} -> {b} (order: {prune_order})"

"""Tests for LLM routing hints derived from the session-type classifier."""
from __future__ import annotations

from unittest.mock import patch

from agent.routing_harmonizer import get_routing_hint
from agent.context_compressor import ContextCompressor


def _msg(content: str, role: str = "user") -> dict:
    return {"role": role, "content": content}


def _research_messages() -> list[dict]:
    return [
        _msg("Please read arxiv:2401.12345 and arxiv:2305.98765v2."),
        _msg("DOI 10.1000/xyz.journal.2024 — cite the abstract of the paper."),
        _msg("LIVITANYI Kolmogorov complexity spike; GALLAGER ITRC; COVSHA Cover-Thomas."),
        _msg("Sweep findings: the paper abstract should be cited in the literature review."),
    ]


def _code_messages() -> list[dict]:
    return [
        _msg("Please edit agent/session_classifier.py and src/app.ts."),
        _msg("def classify(messages):\n    class Router:\n        pass"),
        _msg('Traceback (most recent call last):\n  File "app.py", line 12, in <module>'),
        _msg("git commit -m 'fix'\n======================= 3 passed, 1 failed ======================="),
        _msg("assert result == expected; pytest -q; 1 failed"),
    ]


def _smalltalk_messages() -> list[dict]:
    return [
        _msg("Hey, how's it going?"),
        _msg("Can you help me think through my afternoon plans?"),
        _msg("Maybe we grab lunch later."),
    ]


class TestResearchRoutingHint:
    def test_research_bias_and_tier(self):
        hint = get_routing_hint(_research_messages())
        assert hint["session_type"] == "research"
        assert hint["reasoning_effort_bias"] == "high"
        assert hint["model_tier_hint"] == "frontier"
        assert hint["compression_profile"] == "fork_research"
        assert hint["confidence"] >= 0.4


class TestCodeRoutingHint:
    def test_code_profile_and_tier(self):
        hint = get_routing_hint(_code_messages())
        assert hint["session_type"] == "code"
        assert hint["compression_profile"] == "fork_code"
        assert hint["model_tier_hint"] == "balanced"
        assert hint["reasoning_effort_bias"] == "medium"
        assert hint["confidence"] >= 0.4


class TestLowConfidenceRoutingHint:
    def test_low_confidence_mixed_default(self):
        hint = get_routing_hint(_smalltalk_messages())
        assert hint["session_type"] == "mixed"
        assert hint["compression_profile"] == "fork_mixed"
        assert hint["reasoning_effort_bias"] == "default"
        assert hint["model_tier_hint"] == "fast"
        assert hint["confidence"] < 0.4


class TestCompressorStoresRoutingHint:
    def _compressor(self):
        with patch("agent.context_compressor.get_model_context_length", return_value=1_000_000):
            c = ContextCompressor(model="test/model", threshold_percent=0.85, quiet_mode=True)
            _ = c.context_length
            return c

    def test_none_before_classifier_runs(self):
        c = self._compressor()
        assert c._routing_hint is None

    def test_stores_hint_when_routing(self):
        c = self._compressor()
        c._maybe_route_session_profile(_research_messages())
        hint = c._routing_hint
        assert hint is not None
        assert hint["session_type"] == "research"
        assert hint["reasoning_effort_bias"] == "high"
        assert hint["model_tier_hint"] == "frontier"
        assert hint["compression_profile"] == "fork_research"

    def test_stores_hint_even_when_explicit(self):
        c = self._compressor()
        c.set_compression_profile("code", _source="explicit")
        c._maybe_route_session_profile(_research_messages())
        assert c._active_compression_profile == "code"
        assert c._profile_source == "explicit"
        hint = c._routing_hint
        assert hint is not None
        assert hint["session_type"] == "research"
        assert set(hint) >= {
            "session_type",
            "confidence",
            "compression_profile",
            "reasoning_effort_bias",
            "model_tier_hint",
        }

    def test_stores_hint_when_fork_policies_missing(self):
        c = self._compressor()
        c.set_compression_profile("mixed", _source="plugin")
        with patch.object(c, "COMPRESSION_PROFILES", {"entropy-adaptive": {}}):
            c._maybe_route_session_profile(_research_messages())
        assert c._active_compression_profile == "mixed"
        hint = c._routing_hint
        assert hint is not None
        assert hint["session_type"] == "research"

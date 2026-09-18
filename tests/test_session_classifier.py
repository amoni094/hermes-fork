"""Tests for agent.session_classifier and compressor profile routing."""
from __future__ import annotations

from unittest.mock import patch

from agent.session_classifier import WINDOW_SIZE, classify, classify_with_scores, get_routing_hint
from agent.context_compressor import ContextCompressor


def _msg(content: str, role: str = "user") -> dict:
    return {"role": role, "content": content}


class TestClassifyReturnShape:
    def test_returns_str_float_tuple(self):
        result = classify([_msg("hello")])
        assert isinstance(result, tuple)
        assert len(result) == 2
        label, confidence = result
        assert isinstance(label, str)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert label in ("research", "code", "mixed")


class TestResearchDetection:
    def test_arxiv_and_spike_names(self):
        messages = [
            _msg("Please read arxiv:2401.12345 and arxiv:2305.98765v2."),
            _msg("DOI 10.1000/xyz.journal.2024 — cite the abstract of the paper."),
            _msg("LIVITANYI Kolmogorov complexity spike; GALLAGER ITRC; COVSHA Cover-Thomas."),
            _msg("Sweep findings: the paper abstract should be cited in the literature review."),
        ]
        label, confidence = classify(messages)
        assert label == "research"
        assert confidence >= 0.4

    def test_window_uses_last_20(self):
        stale_code = [_msg("def foo(): pass\napp.py failed assert")] * 5
        research = [
            _msg("arxiv:2401.12345 paper abstract cite LIVITANYI GALLAGER COVSHA sweep findings")
        ] * WINDOW_SIZE
        label, confidence = classify(stale_code + research)
        assert label == "research"
        assert confidence >= 0.4


class TestCodeDetection:
    def test_file_extensions_and_test_output(self):
        messages = [
            _msg("Please edit agent/session_classifier.py and src/app.ts."),
            _msg("def classify(messages):\n    class Router:\n        pass"),
            _msg("Traceback (most recent call last):\n  File \"app.py\", line 12, in <module>"),
            _msg("git commit -m 'fix'\n======================= 3 passed, 1 failed ======================="),
            _msg("assert result == expected; pytest -q; 1 failed"),
        ]
        label, confidence = classify(messages)
        assert label == "code"
        assert confidence >= 0.4


class TestMixedFallback:
    def test_low_confidence_smalltalk(self):
        messages = [
            _msg("Hey, how's it going?"),
            _msg("Can you help me think through my afternoon plans?"),
            _msg("Maybe we grab lunch later."),
        ]
        label, confidence = classify(messages)
        assert label == "mixed"
        assert confidence < 0.4

    def test_empty_messages(self):
        label, confidence = classify([])
        assert label == "mixed"
        assert confidence == 0.0


class TestAdversarialClassify:
    def test_empty_message_list_returns_mixed_zero(self):
        label, confidence = classify([])
        assert (label, confidence) == ("mixed", 0.0)

    def test_single_message_no_signals_returns_mixed_low_conf(self):
        label, confidence = classify([_msg("just chatting about the weather tomorrow")])
        assert label == "mixed"
        assert confidence < 0.4

    def test_mixed_research_and_code_signals(self):
        messages = [
            _msg("arxiv:2401.12345 paper"),
            _msg("def foo(): pass\napp.py"),
        ]
        label, confidence, scores = classify_with_scores(messages)
        assert scores["research"] > 0
        assert scores["code"] > 0
        assert label in ("mixed", "research", "code")
        if scores["research"] == scores["code"]:
            assert label == "mixed"

    def test_get_routing_hint_has_required_keys(self):
        hint = get_routing_hint([_msg("hello")])
        assert set(hint) >= {
            "session_type",
            "confidence",
            "compression_profile",
            "reasoning_effort_bias",
            "model_tier_hint",
        }


class TestCompressorRouting:
    def _compressor(self):
        with patch("agent.context_compressor.get_model_context_length", return_value=1_000_000):
            c = ContextCompressor(model="test/model", threshold_percent=0.85, quiet_mode=True)
            _ = c.context_length
            return c

    def test_routes_research_when_not_explicit(self):
        c = self._compressor()
        messages = [
            _msg("arxiv:2401.12345 paper abstract cite LIVITANYI GALLAGER COVSHA sweep findings")
        ] * 4
        c._maybe_route_session_profile(messages)
        assert c._session_type == "research"
        assert c._active_compression_profile == "research"
        assert c._profile_source == "session-classifier"
        assert c.protect_last_n == 22
        assert c.threshold_percent == 0.45

    def test_skips_when_explicit_source(self):
        c = self._compressor()
        c.set_compression_profile("code", _source="explicit")
        messages = [
            _msg("arxiv:2401.12345 paper abstract cite LIVITANYI GALLAGER COVSHA sweep findings")
        ] * 4
        c._maybe_route_session_profile(messages)
        assert c._active_compression_profile == "code"
        assert c._profile_source == "explicit"

    def test_falls_back_when_fork_policies_missing(self):
        c = self._compressor()
        c.set_compression_profile("mixed", _source="plugin")
        with patch.object(c, "COMPRESSION_PROFILES", {"entropy-adaptive": {}}):
            messages = [_msg("arxiv:2401.12345 LIVITANYI paper")]
            c._maybe_route_session_profile(messages)
        assert c._active_compression_profile == "mixed"

    def test_low_confidence_does_not_clobber_constructor_knobs(self):
        c = self._compressor()
        original_n = c.protect_last_n
        original_pct = c.threshold_percent
        c._maybe_route_session_profile([_msg("hello there"), _msg("how are you")])
        assert c._session_type == "mixed"
        assert c._active_compression_profile is None
        assert c.protect_last_n == original_n
        assert c.threshold_percent == original_pct


class TestClassifierEvalObservability:
    def test_classified_oracle_policy_mirrors_classified(self):
        from evals.compaction.policies import POLICIES

        classified = POLICIES["classified"]
        oracle = POLICIES["classified_oracle"]
        assert classified["ctor"] == {"threshold_percent": 0.50, "protect_last_n": 20}
        assert classified["attrs"]["use_classifier"] is True
        assert oracle["ctor"] == classified["ctor"]
        assert oracle["attrs"]["use_classifier"] is True
        assert oracle["attrs"]["proactive_prune_tokens"] == 32_000

    def test_policy_label_includes_detected_profile(self):
        from evals.compaction.runner import (
            classifier_decision_from_compressor,
            policy_label_for_arm,
        )

        class _Comp:
            routing_hint = {
                "session_type": "code",
                "confidence": 0.9,
                "compression_profile": "fork_code",
            }
            _session_type = "code"

        spec = {"attrs": {"use_classifier": True}}
        assert policy_label_for_arm("classified", spec, _Comp()) == "classified(fork_code)"
        assert (
            policy_label_for_arm("classified_oracle", spec, _Comp())
            == "classified_oracle(fork_code)"
        )
        decision = classifier_decision_from_compressor(_Comp())
        assert decision == {
            "session_type": "code",
            "confidence": 0.9,
            "compression_profile": "fork_code",
        }

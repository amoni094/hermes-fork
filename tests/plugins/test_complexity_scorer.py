"""Unit tests for description_compression_ratio and TaskComplexityScorer.

TelegraphicCompressor / ToolResultCompactor are covered in
test_telegraphic_compressor.py — not duplicated here.

plugins/user/lambda-tuner has a hyphen, so the module is loaded from disk.
"""
import importlib.util
import pathlib
import random
import string

import pytest

_spec = importlib.util.spec_from_file_location(
    "lambda_tuner_complexity",
    pathlib.Path(__file__).parent.parent.parent
    / "plugins"
    / "user"
    / "lambda-tuner"
    / "complexity.py",
)
assert _spec is not None and _spec.loader is not None, "Could not locate lambda-tuner/complexity.py"
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
description_compression_ratio = _m.description_compression_ratio
TaskComplexityScorer = _m.TaskComplexityScorer


def _in_unit_interval(value: float) -> bool:
    return isinstance(value, float) and 0.0 <= value <= 1.0


# ---------------------------------------------------------------------------
# description_compression_ratio
# ---------------------------------------------------------------------------


class TestDescriptionCompressionRatio:
    def test_empty_string_returns_zero(self):
        # Empty input has no information content; function short-circuits to 0.0
        # (zlib header overhead used to cause ~8.0, which would distort scorer mean).
        result = description_compression_ratio("")
        assert result == 0.0

    def test_repetitive_text_returns_low_ratio(self):
        result = description_compression_ratio("aaaa" * 5000)
        assert isinstance(result, float)
        assert 0.0 <= result < 0.1

    def test_high_entropy_text_returns_high_ratio(self):
        rng = random.Random(0)
        alphabet = string.ascii_letters + string.digits + string.punctuation
        text = "".join(rng.choice(alphabet) for _ in range(4000))
        result = description_compression_ratio(text)
        assert isinstance(result, float)
        assert result > 0.7
        assert result > description_compression_ratio("aaaa" * 5000)

    def test_cjk_text_does_not_crash(self):
        text = "日本語のテスト文章です。漢字とひらがなとカタカナ。" * 20
        result = description_compression_ratio(text)
        assert isinstance(result, float)
        assert result >= 0.0


# ---------------------------------------------------------------------------
# TaskComplexityScorer.score
# ---------------------------------------------------------------------------


class TestTaskComplexityScorerScore:
    def test_empty_text_returns_float_in_unit_interval(self):
        result = TaskComplexityScorer().score("")
        assert _in_unit_interval(result)

    def test_short_greeting_returns_low_score(self):
        scorer = TaskComplexityScorer()
        for text in ("hi", "hello", "hello there", "Good morning!"):
            result = scorer.score(text)
            assert result < 0.4, f"{text!r} scored {result}"

    def test_code_heavy_scores_higher_than_prose(self):
        prose = (
            "The weather today is quite pleasant and many people are walking in the park. "
            "Birds are singing in the trees while children play on the grass near the lake. "
            "Families enjoy picnics and the afternoon sun warms the open fields around town."
        )
        code = '''
import os
import json
from pathlib import Path

def deploy_build(items=None):
    result = []
    for item in items:
        if item is None:
            continue
        result.append({"id": item, "ok": True})
    print(result[0]["id"]);
    return result

class App:
    def run(self, n=10):
        execute = True
        return deploy_build(list(range(n)))
'''
        scorer = TaskComplexityScorer()
        code_score = scorer.score(code)
        prose_score = scorer.score(prose)
        assert _in_unit_interval(code_score)
        assert _in_unit_interval(prose_score)
        assert code_score > prose_score

    def test_recent_tokens_parameter_does_not_crash(self):
        scorer = TaskComplexityScorer()
        result = scorer.score("hello world", recent_tokens={"hello", "world", "unused"})
        assert _in_unit_interval(result)

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "a",
            "hi",
            "How are you?",
            "maybe this could possibly be unclear",
            "must never always only required forbidden",
            "first do this then next finally step 1",
            "run execute deploy build install search file terminal",
            "?" * 20,
            "The weather today is quite pleasant and many people are walking.",
            "import os\ndef f(x):\n    return {k: v for (k, v) in x.items()}\n",
        ],
    )
    def test_score_always_in_unit_interval(self, text):
        result = TaskComplexityScorer().score(text)
        assert _in_unit_interval(result)


# ---------------------------------------------------------------------------
# TaskComplexityScorer edge cases
# ---------------------------------------------------------------------------


class TestTaskComplexityScorerEdgeCases:
    def test_update_recent_empty_string_does_not_crash(self):
        scorer = TaskComplexityScorer()
        scorer.update_recent("")
        assert scorer._recent_tokens == set()

    def test_update_recent_limits_vocabulary(self):
        scorer = TaskComplexityScorer()
        scorer.update_recent(" ".join(f"tok{i}" for i in range(3000)))
        assert len(scorer._recent_tokens) <= 2000

        scorer.update_recent(" ".join(f"more{i}" for i in range(1500)))
        assert len(scorer._recent_tokens) <= 2000

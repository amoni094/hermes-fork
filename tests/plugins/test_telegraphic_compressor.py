"""Unit tests for TelegraphicCompressor and ToolResultCompactor.

Design notes:
  - Passes 3-5 in compress() are gated by 'still over budget?' — they only run
    when the payload exceeds max_chars after earlier passes.  Unit tests for those
    passes therefore call the private methods directly (_remove_boilerplate,
    _dedup_lines, _skeleton_json_values).  Integration tests drive compress() end-to-end
    with a tight budget so all passes are reachable.
  - HTML stripping + entity decoding is guarded by 'if "<" in text' — entity-only
    tests must include an angle bracket to trigger the path.
"""
import importlib.util
import json
import pathlib
import pytest

# plugins/user/lambda-tuner has a hyphen — not a valid Python package name.
# Load the module directly from the file system to avoid import path issues.
_PLUGIN_DIR = pathlib.Path(__file__).parent.parent.parent / "plugins" / "user" / "lambda-tuner"
_spec = importlib.util.spec_from_file_location("lambda_tuner_complexity", _PLUGIN_DIR / "complexity.py")
assert _spec is not None and _spec.loader is not None, "Could not locate lambda-tuner/complexity.py"
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
TelegraphicCompressor = _mod.TelegraphicCompressor
ToolResultCompactor = _mod.ToolResultCompactor


def _tc() -> TelegraphicCompressor:
    return TelegraphicCompressor()


# ---------------------------------------------------------------------------
# Pass 1 — HTML stripping + entity decoding
# HTML path only fires when '<' is in text (by design — don't call on plain text)
# ---------------------------------------------------------------------------

class TestHtmlStrip:
    def test_removes_simple_tags(self):
        result = _tc()._strip_html("<p>Hello <b>world</b></p>")
        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_decodes_named_entities(self):
        # Must have '<' in text to trigger the HTML path in compress(); test the
        # method directly here.
        result = _tc()._decode_entities("A &amp; B &lt;3 &gt; C &quot;q&quot; &apos;s&apos;")
        assert "&amp;" not in result
        assert "A & B" in result
        assert '"q"' in result
        assert "'s'" in result

    def test_decodes_nbsp(self):
        result = _tc()._decode_entities("left&nbsp;right")
        assert "&nbsp;" not in result
        assert "left right" in result

    def test_decodes_numeric_entities(self):
        result = _tc()._decode_entities("&#39;apos&#39; &#x27;hex&#x27;")
        assert "&#39;" not in result
        assert "'apos'" in result
        assert "'hex'" in result

    def test_strip_html_via_compress_when_tags_present(self):
        # compress() fires the HTML pass when '<' present
        result = _tc().compress("<p>Important data.</p><nav>Skip to main content</nav>", max_chars=10_000)
        assert "<p>" not in result
        assert "Important data." in result

    def test_no_html_passthrough(self):
        # No angle brackets — HTML pass skipped, content preserved as-is
        plain = "Result: score=0.91 threshold=0.45"
        result = _tc().compress(plain, max_chars=10_000)
        assert "score=0.91" in result
        assert "threshold=0.45" in result

    def test_script_tag_stripped(self):
        result = _tc()._strip_html("<script>alert('xss')</script>data")
        assert "<script>" not in result
        assert "data" in result


# ---------------------------------------------------------------------------
# Pass 2 — Whitespace normalisation (tested via the private method)
# ---------------------------------------------------------------------------

class TestWhitespaceNormalisation:
    def test_collapses_blank_line_runs(self):
        result = _tc()._normalize_whitespace("line1\n\n\n\nline2")
        assert "\n\n\n" not in result
        assert "line1" in result and "line2" in result

    def test_strips_trailing_spaces(self):
        result = _tc()._normalize_whitespace("hello   \nworld   ")
        for line in result.splitlines():
            assert line == line.rstrip()

    def test_preserves_single_blank_line(self):
        result = _tc()._normalize_whitespace("line1\n\nline2")
        assert "line1" in result and "line2" in result

    def test_via_compress_collapses_blanks(self):
        result = _tc().compress("A\n\n\n\nB", max_chars=10_000)
        assert "\n\n\n" not in result
        assert "A" in result and "B" in result


# ---------------------------------------------------------------------------
# Pass 3 — Boilerplate removal (private method)
# ---------------------------------------------------------------------------

class TestBoilerplateRemoval:
    _PATTERNS = [
        "Skip to main content",
        "Cookie Policy",
        "Accept all cookies",
        "Privacy Policy",
        "Terms of Service",
        "Terms of Use",
        "All rights reserved",
        "Click here to learn more",  # trailing content now matched by updated regex
        "Subscribe to our newsletter",
        "Follow us on",
        "Share this article",
        "Advertisement",
        "Table of Contents",
        "[Image: logo]",
        "[IMAGE: banner]",
    ]

    @pytest.mark.parametrize("line", _PATTERNS)
    def test_removes_boilerplate_line(self, line):
        text = f"Useful content here.\n{line}\nMore useful content."
        result = _tc()._remove_boilerplate(text)
        assert line not in result
        assert "Useful content here." in result
        assert "More useful content." in result

    def test_case_insensitive(self):
        result = _tc()._remove_boilerplate("Good stuff\ncookie policy\nMore good stuff")
        assert "cookie policy" not in result
        assert "Good stuff" in result

    def test_preserves_non_boilerplate(self):
        text = "The cookie recipe is great.\nBake at 350 degrees."
        result = _tc()._remove_boilerplate(text)
        # "The cookie recipe..." is NOT a boilerplate line — it's not just "cookie policy"
        assert "cookie recipe" in result

    def test_boilerplate_with_leading_whitespace(self):
        result = _tc()._remove_boilerplate("Real content\n   Privacy Policy   \nMore content")
        assert "Privacy Policy" not in result
        assert "Real content" in result

    def test_boilerplate_fires_via_compress_when_over_budget(self):
        # Build a payload that stays over budget until boilerplate removed
        boilerplate_lines = "\n".join(["Advertisement"] * 50)
        real_content = "A" * 200
        text = real_content + "\n" + boilerplate_lines
        result = _tc().compress(text, max_chars=len(real_content) + 5)
        assert "Advertisement" not in result
        assert real_content in result


# ---------------------------------------------------------------------------
# Pass 4 — Deduplication of adjacent lines (private method)
# ---------------------------------------------------------------------------

class TestDedup:
    def test_removes_verbatim_duplicates(self):
        text = "line\nline\nline\ndifferent"
        result = _tc()._dedup_lines(text)
        lines = [l for l in result.splitlines() if l.strip()]
        assert lines.count("line") == 1

    def test_removes_near_verbatim_prefix_duplicates(self):
        prefix = "x" * 61
        text = f"{prefix}aaa\n{prefix}bbb\nunique"
        result = _tc()._dedup_lines(text)
        matching = [l for l in result.splitlines() if l.startswith("x" * 61)]
        assert len(matching) == 1

    def test_non_adjacent_duplicates_kept(self):
        text = "A\nB\nA"
        result = _tc()._dedup_lines(text)
        assert result.count("A") == 2

    def test_short_lines_not_deduped_by_prefix(self):
        # Lines <= 60 chars must not trigger prefix dedup — only verbatim match
        text = "ab\nac\nabd"
        result = _tc()._dedup_lines(text)
        assert "ac" in result
        assert "abd" in result

    def test_dedup_fires_via_compress_when_over_budget(self):
        # Repeated lines that pad the payload over budget — dedup should collapse them.
        repeated = "\n".join(["same line content here"] * 100)
        unique = "uniquedata_sentinel"
        text = repeated + "\n" + unique
        # Budget is tight enough that only post-dedup the payload fits
        budget = len("same line content here\n") + len(unique) + 10
        result = _tc().compress(text, max_chars=budget)
        lines = [l for l in result.splitlines() if l.strip()]
        # After dedup there should be exactly 1 instance of the repeated line
        assert lines.count("same line content here") == 1, (
            "dedup pass should have collapsed 100 repeated lines to 1"
        )


# ---------------------------------------------------------------------------
# Pass 5 — JSON value skeletonisation (private method)
# ---------------------------------------------------------------------------

class TestJsonSkeleton:
    def test_truncates_long_string_value(self):
        long_val = "x" * 100
        text = json.dumps({"key": long_val})
        result = _tc()._skeleton_json_values(text)
        assert '"key"' in result
        assert long_val not in result
        assert "chars]" in result

    def test_preserves_short_string_value(self):
        text = '{"key": "short"}'
        result = _tc()._skeleton_json_values(text)
        assert '"short"' in result

    def test_truncates_long_array(self):
        long_arr = "[" + ", ".join(f'"{i}"' for i in range(60)) + "]"
        text = f'{{"items": {long_arr}}}'
        result = _tc()._skeleton_json_values(text)
        assert '"items"' in result
        assert len(result) < len(text)

    def test_truncates_long_nested_object(self):
        inner = "{" + ", ".join(f'"k{i}": "v{i}"' for i in range(30)) + "}"
        text = f'{{"outer": {inner}}}'
        result = _tc()._skeleton_json_values(text)
        assert '"outer"' in result
        assert len(result) < len(text)

    def test_preserves_key_names(self):
        long_val = "y" * 200
        text = json.dumps({"important_key": long_val, "another_key": long_val})
        result = _tc()._skeleton_json_values(text)
        assert "important_key" in result
        assert "another_key" in result

    def test_skeleton_fires_via_compress_when_over_budget(self):
        long_val = "z" * 200
        payload = json.dumps({"key": long_val})
        # Budget small enough that skeleton pass is needed
        result = _tc().compress(payload, max_chars=len(payload) - 50)
        assert "key" in result
        assert long_val not in result


# ---------------------------------------------------------------------------
# Pass 6 — Head+tail fallback
# ---------------------------------------------------------------------------

class TestHeadTail:
    def test_marker_present(self):
        unique_lines = "\n".join(f"line{i}{'z' * 50}" for i in range(200))
        result = _tc().compress(unique_lines, max_chars=200)
        assert "lambda-tuner telegraphic compressor" in result

    def test_result_within_budget(self):
        text = "word " * 5000
        result = _tc().compress(text, max_chars=1000)
        # Allow marker overhead
        assert len(result) <= 1000 + 150

    def test_head_and_tail_both_present(self):
        # Private method: first chunk=max//3, last chunk=max//3
        text = "AAAAAA" + "M" * 1000 + "ZZZZZZ"
        result = _tc()._head_tail(text, max_chars=100)
        assert "AAAAAA" in result
        assert "ZZZZZZ" in result
        assert "omitted" in result


# ---------------------------------------------------------------------------
# compress() integration — realistic payloads
# ---------------------------------------------------------------------------

class TestCompressIntegration:
    def test_html_web_extract_shrinks(self):
        html = (
            "<html><head><title>Page</title></head><body>"
            + "<nav>Skip to main content</nav>"
            + "<p>Important research finding: the answer is 42.</p>" * 5
            + "<footer>Privacy Policy | Terms of Service | All rights reserved</footer>"
            + "</body></html>"
        )
        result = _tc().compress(html, max_chars=10_000)
        assert "Important research finding" in result
        assert len(result) < len(html)

    def test_json_api_dump_shrinks_with_tight_budget(self):
        payload = json.dumps({
            "results": [{"id": i, "data": "x" * 300, "title": f"item {i}"} for i in range(20)]
        })
        # Use a budget half the payload size to force skeleton/head+tail
        result = _tc().compress(payload, max_chars=len(payload) // 2)
        assert len(result) <= len(payload) // 2 + 200  # allow marker overhead
        # Skeleton pass stubs the outer array value wholesale — that's correct.
        # The key "results" (or the outer structure) should still be present.
        assert "results" in result or "chars]" in result  # either skeleton or head+tail fired

    def test_idempotent_on_already_small_input(self):
        small = "Short tool result."
        result = _tc().compress(small, max_chars=10_000)
        assert small in result

    def test_empty_input(self):
        assert _tc().compress("") == ""

    def test_whitespace_only_input(self):
        result = _tc().compress("   \n\n  \n")
        assert result.strip() == ""

    def test_no_information_loss_on_numeric_data(self):
        text = "Score: 0.912\nThreshold: 0.45\nRatio: 1.23\nCount: 7"
        result = _tc().compress(text, max_chars=10_000)
        assert "0.912" in result
        assert "0.45" in result
        assert "1.23" in result
        assert "7" in result

    def test_realistic_web_extract_output(self):
        # Simulate a typical web_extract dump
        page = "\n".join([
            "<html>",
            "<nav>Skip to main content</nav>",
            "<p>" + ("The quick brown fox jumps. " * 20) + "</p>",
            "<aside>Advertisement</aside>",
            "<p>Follow us on social media.</p>",
            "<footer>Privacy Policy | Terms of Service</footer>",
            "</html>",
        ])
        result = _tc().compress(page, max_chars=10_000)
        assert "quick brown fox" in result
        assert len(result) < len(page)


# ---------------------------------------------------------------------------
# should_compress / should_compact
# ---------------------------------------------------------------------------

class TestShouldCompress:
    def test_fires_on_large_tool_result(self):
        assert _tc().should_compress("tool", "x" * 2001) is True

    def test_skips_small_tool_result(self):
        assert _tc().should_compress("tool", "x" * 1999) is False

    def test_skips_non_tool_role(self):
        assert _tc().should_compress("assistant", "x" * 5000) is False
        assert _tc().should_compress("user", "x" * 5000) is False

    def test_custom_threshold(self):
        assert _tc().should_compress("tool", "x" * 500, threshold=400) is True
        assert _tc().should_compress("tool", "x" * 300, threshold=400) is False


class TestToolResultCompactor:
    def test_compact_delegates_to_telegraphic(self):
        compactor = ToolResultCompactor()
        html = "<p>" + "important content. " * 300 + "</p>"
        result = compactor.compact(html, max_chars=4000)
        assert len(result) <= 4000 + 200
        assert "<p>" not in result

    def test_compact_passthrough_under_budget(self):
        compactor = ToolResultCompactor()
        small = "tiny result"
        assert compactor.compact(small, max_chars=4000) == small

    def test_should_compact_fires_at_2000(self):
        compactor = ToolResultCompactor()
        assert compactor.should_compact("tool", "x" * 2001) is True
        assert compactor.should_compact("tool", "x" * 1999) is False

    def test_should_compact_skips_non_tool(self):
        compactor = ToolResultCompactor()
        assert compactor.should_compact("user", "x" * 5000) is False
        assert compactor.should_compact("assistant", "x" * 5000) is False

    def test_compact_threshold_aligned_with_should_compact(self):
        # F1 regression: compact() must compress content in (2000, 4000] — previously
        # it passthroughed content <= 4000 even when should_compact returned True.
        compactor = ToolResultCompactor()
        payload = "<p>" + ("important content. " * 150) + "</p>"  # ~2850 chars
        assert 2000 < len(payload) < 4000, "fixture must be in (2000,4000] range"
        assert compactor.should_compact("tool", payload) is True
        result = compactor.compact(payload)
        # Telegraphic passes must have fired: HTML tags stripped
        assert "<p>" not in result


# ---------------------------------------------------------------------------
# Edge cases: None content, list content, head+tail boundary
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_head_tail_min_chunk_guard(self):
        # F15: max_chars < 3 previously produced chunk=0, making text[-0:] = full text.
        # The result should not be larger than the original + marker.
        text = "abcdefghij" * 20
        result = _tc()._head_tail(text, max_chars=2)
        assert len(result) < len(text) + 200  # marker overhead allowed

    def test_compress_unicode_content(self):
        # Unicode must not crash compress().
        text = "Привет мир\n" * 300
        result = _tc().compress(text, max_chars=50)
        assert isinstance(result, str)

    def test_compress_long_line_no_whitespace(self):
        # A single very long line with no whitespace — only head+tail can truncate it.
        text = "a" * 10_000
        result = _tc().compress(text, max_chars=100)
        assert len(result) <= 100 + 200  # allow marker
        assert "omitted" in result

    def test_should_compress_rejects_non_string_safely(self):
        # should_compress receives non-str content (e.g. list) — must not raise.
        # In the live path the runner now guards with isinstance(content, str).
        # should_compress itself uses len() which works on lists, but role must be 'tool'.
        content_list = ["block1", "block2"]
        # should not raise — list has len()
        result = _tc().should_compress("tool", content_list)  # type: ignore[arg-type]
        assert isinstance(result, bool)

    def test_compact_with_short_content_not_compressed(self):
        # Content under threshold should passthrough unchanged.
        compactor = ToolResultCompactor()
        short = "x" * 100
        assert compactor.compact(short) is short

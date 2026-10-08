#!/usr/bin/env python3
"""Unit tests for browser_act_guard.py — run: pytest -q ~/.hermes/scripts/test_browser_act_guard.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import browser_act_guard as bag  # noqa: E402


def test_page_fingerprint_stable_and_strips_fragment():
    a = bag.page_fingerprint("https://ex.com/a#top", 10, "hello")
    b = bag.page_fingerprint("https://ex.com/a", 10, "hello")
    c = bag.page_fingerprint("https://ex.com/a/", 10, "hello")
    assert a == b == c
    assert a.count("|") == 2
    # content change flips hash
    d = bag.page_fingerprint("https://ex.com/a", 10, "hello!")
    assert a != d
    # count change flips
    e = bag.page_fingerprint("https://ex.com/a", 11, "hello")
    assert a != e


def test_page_fingerprint_precomputed_hash_and_bad_count():
    # intentional bad count type — runtime coerces to 0
    fp = bag.page_fingerprint("https://x", "nope", "", content_hash="abc")  # type: ignore[arg-type]
    assert fp.endswith("|0|abc")


def test_normalize_action_click_variants_same_hash():
    variants = [
        {"type": "click", "index": 3},
        {"action": "click", "element": 3},
        {"type": "click", "ref": "@e3"},
        {"name": "click", "ref": "e3"},
    ]
    norms = {bag.normalize_action(v) for v in variants}
    assert len(norms) == 1
    hashes = {bag.action_hash(v) for v in variants}
    assert len(hashes) == 1


def test_normalize_action_type_includes_text_hash():
    a = bag.normalize_action({"type": "fill", "index": 1, "text": "Alice"})
    b = bag.normalize_action({"type": "fill", "index": 1, "text": "Bob"})
    c = bag.normalize_action({"type": "fill", "index": 2, "text": "Alice"})
    assert a != b
    assert a != c


def test_normalize_action_search_token_sort():
    a = bag.normalize_action({"type": "search", "query": "red blue"})
    b = bag.normalize_action({"type": "search", "query": "blue red"})
    assert a == b


def test_normalize_action_navigate_strips_fragment():
    a = bag.normalize_action({"type": "navigate", "url": "https://a.com/x#y"})
    b = bag.normalize_action({"type": "open", "url": "https://a.com/x"})
    assert a == b


def test_observe_loop_escalates_soft_medium_hard(tmp_path):
    state = bag.LoopState()
    action = {"type": "click", "index": 7}
    fp = bag.page_fingerprint("https://ex.com", 5, "same")

    levels = []
    for _ in range(6):
        state, obs = bag.observe_loop(state, action, fp, soft=2, medium=3, hard=5)
        levels.append(obs.nudge_level)

    assert levels[0] == "none"
    assert levels[1] == "soft"
    assert levels[2] == "medium"
    assert levels[4] == "hard"
    # 5th observation (index 4) reaches hard threshold
    state2 = bag.LoopState()
    last = None
    for _ in range(5):
        state2, last = bag.observe_loop(state2, action, fp, soft=2, medium=3, hard=5)
    assert last is not None
    assert last.nudge_level == "hard"
    assert last.should_break is True
    assert last.suggestion


def test_observe_loop_resets_streak_on_new_action():
    state = bag.LoopState()
    fp = "u|1|abc"
    state, o1 = bag.observe_loop(state, {"type": "click", "index": 1}, fp)
    state, o2 = bag.observe_loop(state, {"type": "click", "index": 1}, fp)
    assert o2.same_action_streak == 2
    state, o3 = bag.observe_loop(state, {"type": "click", "index": 2}, fp)
    assert o3.same_action_streak == 1
    assert o3.nudge_level == "none"


def test_observe_state_roundtrip(tmp_path):
    path = tmp_path / "loop.json"
    state = bag.LoopState()
    fp = bag.page_fingerprint("https://ex.com", 3, "t")
    state, obs = bag.observe_loop(state, {"type": "click", "index": 1}, fp)
    bag.save_state(path, state)
    loaded = bag.load_state(path)
    assert loaded.last_action_hash == state.last_action_hash
    assert loaded.total_observations == 1
    assert obs.action_hash == loaded.last_action_hash


def test_split_action_result_once_semantics():
    r = bag.split_action_result(
        "line1 big extract\nmore",
        long_term="price=12",
        include_once=True,
    )
    first = r.agent_view(seen_content=False)
    second = r.agent_view(seen_content=True)
    assert "extracted_content" in first
    assert "extracted_content" not in second
    assert second["long_term_memory"] == "price=12"


def test_split_auto_long_term_and_error_cap():
    r = bag.split_action_result("  \nFirst fact here\nSecond", auto_long_term=True)
    assert r.long_term_memory == "First fact here"
    err = "e" * 2000
    r2 = bag.split_action_result("", error=err)
    assert len(r2.error) == bag.MAX_ERROR_CHARS


def test_multi_act_should_stop_reasons():
    fp1 = "a|1|x"
    fp2 = "b|1|x"
    cont = bag.multi_act_should_stop(fp1, fp1, 0, max_actions=5)
    assert cont["stop"] is False
    assert cont["reason"] == "continue"

    changed = bag.multi_act_should_stop(fp1, fp2, 0, max_actions=5)
    assert changed["stop"] is True
    assert changed["reason"] == "page_changed"

    capped = bag.multi_act_should_stop(fp1, fp1, 4, max_actions=5)
    assert capped["stop"] is True
    assert capped["reason"] == "max_actions"

    forced = bag.multi_act_should_stop(fp1, fp1, 0, force_stop=True)
    assert forced["reason"] == "force"

    # negative index clamps; empty fps never page_changed
    neg = bag.multi_act_should_stop(fp1, fp1, -3, max_actions=5)
    assert neg["actions_done"] == 1
    assert neg["stop"] is False
    empty = bag.multi_act_should_stop("", "b|1|x", 0)
    assert empty["page_changed"] is False
    assert empty["stop"] is False


def test_filter_snapshot_drops_noise_keeps_refs():
    text = "\n".join(
        [
            "[e1] button Submit",
            "Accept All Cookies",
            "[e2] link Privacy Policy",  # has ref-like [e2] — keep
            "Enable JavaScript to continue",
            "Real content row",
        ]
    )
    out = bag.filter_snapshot_lines(text)
    assert "Accept All Cookies" not in out["text"]
    assert "Enable JavaScript" not in out["text"]
    assert "Submit" in out["text"]
    assert "Real content row" in out["text"]
    assert out["dropped_lines"] >= 1


def test_cli_fingerprint_and_action_hash(tmp_path, capsys):
    code = bag.main(
        [
            "fingerprint",
            "--url",
            "https://ex.com/a#z",
            "--count",
            "4",
            "--text",
            "hi",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "fingerprint" in data

    code = bag.main(["action-hash", "--json", json.dumps({"type": "click", "index": 9})])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["hash"]


def test_cli_observe_and_multi_act(tmp_path, capsys):
    state = tmp_path / "s.json"
    fp = bag.page_fingerprint("https://ex.com", 2, "x")
    last = None
    for _ in range(3):
        code = bag.main(
            [
                "observe",
                "--state-file",
                str(state),
                "--action-json",
                json.dumps({"type": "click", "index": 1}),
                "--fingerprint",
                fp,
            ]
        )
        assert code == 0
        # each observe prints one JSON object; take the last complete object
        raw = capsys.readouterr().out.strip()
        last = json.loads(raw)
    assert last is not None
    assert last["observation"]["nudge_level"] in {"soft", "medium", "hard"}
    assert last["observation"]["same_action_streak"] == 3

    code = bag.main(
        [
            "multi-act-stop",
            "--prev-fp",
            "a|1|x",
            "--curr-fp",
            "b|1|x",
            "--index",
            "0",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["stop"] is True


def test_cli_split_and_filter(tmp_path, capsys):
    f = tmp_path / "c.txt"
    f.write_text("Big scrape body\nline2\n", encoding="utf-8")
    code = bag.main(
        [
            "split",
            "--content-file",
            str(f),
            "--long-term",
            "found=yes",
            "--seen-content",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "extracted_content" not in data["agent_view"]
    assert data["agent_view"]["long_term_memory"] == "found=yes"

    code = bag.main(
        [
            "filter-snapshot",
            "--text",
            "Accept All\n[e1] OK",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "OK" in data["text"]


def test_cli_bad_json():
    assert bag.main(["action-hash", "--json", "{not-json"]) == 2
    assert bag.main(["action-hash", "--json", "[]"]) == 2


def test_load_state_corrupt(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    st = bag.load_state(p)
    assert st.total_observations == 0
    p2 = tmp_path / "missing.json"
    assert bag.load_state(p2).total_observations == 0

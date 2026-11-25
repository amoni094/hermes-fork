"""Unit tests for toolperf ab_eval ATOF worker + score_run."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

_AB_EVAL_PATH = (
    Path(__file__).resolve().parents[2] / "evals" / "toolperf_abeval" / "ab_eval.py"
)


def _load_ab_eval():
    spec = importlib.util.spec_from_file_location("ab_eval_under_test", _AB_EVAL_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ab_eval = _load_ab_eval()


def test_score_run_counts_llm_and_tool_scopes(tmp_path: Path):
    p = tmp_path / "run.atof.jsonl"
    events = [
        {"kind": "scope", "category": "llm", "scope_category": "start"},
        {"kind": "scope", "category": "llm", "scope_category": "end"},
        {
            "kind": "scope",
            "category": "tool",
            "scope_category": "start",
            "name": "terminal",
        },
        {
            "kind": "scope",
            "category": "tool",
            "scope_category": "end",
            "name": "terminal",
            "data": {"exit_code": 0, "output": "ok"},
            "metadata": {"status": "ok"},
        },
    ]
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    assert ab_eval.score_run(p) == {
        "llm": 1,
        "tools": 1,
        "errs": 0,
        "retries": 0,
        "kb": 0,
    }


def test_score_run_missing_file_is_none(tmp_path: Path):
    assert ab_eval.score_run(tmp_path / "missing.atof.jsonl") is None


def test_abeval_worker_puts_final_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    class FakeLease:
        pass

    class Coord:
        def __init__(self):
            self.released = None

        def acquire_conversation(self, **_kw):
            return FakeLease()

        def release_conversation(self, lease):
            self.released = lease

    class Registry:
        def __init__(self):
            self.shutdown = False

        def shutdown_all(self):
            self.shutdown = True

    coord = Coord()
    registry = Registry()

    fake_relay = types.ModuleType("agent.relay_runtime")
    fake_relay.SESSION_COORDINATOR = coord
    fake_relay.HOST_REGISTRY = registry
    fake_relay.get_runtime = lambda: object()
    fake_relay.current_profile_key = lambda: "fork"

    agent_pkg = types.ModuleType("agent")
    agent_pkg.relay_runtime = fake_relay

    closed = {"n": 0}
    created: dict = {}

    class FakeAgent:
        def __init__(self, **kw):
            self.kw = kw
            created["agent"] = self

        def run_conversation(self, query):
            return {"final_response": f"VALUE=ENV_OK_4477:{query}"}

        def close(self):
            closed["n"] += 1

    run_mod = types.ModuleType("run_agent")
    run_mod.AIAgent = FakeAgent

    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.relay_runtime", fake_relay)
    monkeypatch.setitem(sys.modules, "run_agent", run_mod)

    q: list[dict] = []

    class Q:
        def put(self, item):
            q.append(item)

    ab_eval._abeval_worker(
        pythonpath=str(tmp_path),
        hermes_home=str(tmp_path / "home"),
        relay_toml=str(tmp_path / "relay.toml"),
        work_str=str(work),
        query="hello",
        model="anthropic/claude-haiku-4-5",
        session_id="abeval-fixes-err_python_env-r0",
        result_q=Q(),
    )
    assert q == [{"out": "VALUE=ENV_OK_4477:hello", "rc": 0}]
    assert closed["n"] == 1
    assert coord.released is not None
    assert registry.shutdown is True
    assert created["agent"].kw["provider"] == "anthropic"
    assert created["agent"].kw["model"] == "claude-haiku-4-5"
    assert created["agent"].user_config == {"smart_model_routing": {"enabled": False}}


def test_abeval_worker_exception_still_puts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    fake_relay = types.ModuleType("agent.relay_runtime")

    def boom():
        raise RuntimeError("no relay")

    fake_relay.get_runtime = boom
    agent_pkg = types.ModuleType("agent")
    agent_pkg.relay_runtime = fake_relay
    monkeypatch.setitem(sys.modules, "agent", agent_pkg)
    monkeypatch.setitem(sys.modules, "agent.relay_runtime", fake_relay)

    q: list[dict] = []

    class Q:
        def put(self, item):
            q.append(item)

    ab_eval._abeval_worker(
        pythonpath=str(tmp_path),
        hermes_home=str(tmp_path / "home"),
        relay_toml=str(tmp_path / "relay.toml"),
        work_str=str(work),
        query="hello",
        model="anthropic/claude-haiku-4-5",
        session_id="sid",
        result_q=Q(),
    )
    assert len(q) == 1
    assert q[0]["rc"] == 1
    assert "RuntimeError" in q[0]["out"]


def test_traj_token_strict_prompt_opus5_only():
    fn = ab_eval.traj_token_strict_prompt
    prompt = ab_eval.TRAJ_TOKEN_STRICT_PROMPT
    empty = {}
    assert fn("anthropic/claude-opus-5", env=empty) == prompt
    assert fn("claude-opus-5", env=empty) == prompt
    assert fn("anthropic/claude-opus-4-5", env=empty) is None
    assert fn("anthropic/claude-sonnet-4-6", env=empty) is None
    assert fn("anthropic/claude-opus-4-5", env={"TRAJ_TOKEN_STRICT": "1"}) == prompt
    assert fn("anthropic/claude-sonnet-4-6", env={"TRAJ_TOKEN_STRICT": "0"}) is None


def test_e4_tasks_registered():
    for name in (
        "err_authz_cache",
        "err_path_semantic_diff",
        "err_hypothesis_invoice",
    ):
        assert name in ab_eval.TASKS
        assert name in ab_eval.SUCCESS
        assert "{WORK}" in ab_eval.TASKS[name]


def test_e4_authz_checker_and(tmp_path: Path):
    work = tmp_path
    (work / "proj").mkdir()
    (work / "proj" / "leak.txt").write_text("A_puts\nB_hits\nB_sees_A\n", encoding="utf-8")
    ok = (
        "ROOT=cache_key_omits_auth\n"
        "WITNESS=userA_GET_/api/me_then_userB_GET_/api/me\n"
        "KEY_IS=METHOD:URL\n"
        "KEY_SHOULD=METHOD:URL:AUTH\n"
    )
    assert ab_eval.SUCCESS["err_authz_cache"](ok, work) is True
    assert ab_eval.SUCCESS["err_authz_cache"](ok.replace("ROOT=cache_key_omits_auth", "ROOT=token_log"), work) is False
    (work / "proj" / "leak.txt").write_text("A_puts\nB_hits\n", encoding="utf-8")
    assert ab_eval.SUCCESS["err_authz_cache"](ok, work) is False


def test_e4_path_checker_needs_both_witnesses(tmp_path: Path):
    work = tmp_path
    prefix_only = (
        "EQUIVALENT=NO\nPREFIX_CHILD=/var/app-extra\nPREFIX_V1=False\nPREFIX_V2=True\n"
    )
    both = prefix_only + "LINK_V1=False\nLINK_V2=True\n"
    (work / "_abeval_reply.txt").write_text(both, encoding="utf-8")
    assert ab_eval.SUCCESS["err_path_semantic_diff"](both, work) is True
    (work / "_abeval_reply.txt").write_text(prefix_only, encoding="utf-8")
    assert ab_eval.SUCCESS["err_path_semantic_diff"](prefix_only, work) is False
    yes = both.replace("EQUIVALENT=NO", "EQUIVALENT=YES")
    (work / "_abeval_reply.txt").write_text(yes, encoding="utf-8")
    assert ab_eval.SUCCESS["err_path_semantic_diff"](yes, work) is False


def test_e4_invoice_checker_and(tmp_path: Path):
    work = tmp_path
    ok = (
        "ROOT=coupon_double_apply\n"
        "ARITH=10000*90//100*90//100=8100\n"
        "ELIM_H1=float_cannot_make_8100\n"
        "ELIM_H2=old_sum_unused\n"
        "ELIM_H3=truncation_is_90_not_8100\n"
        "files: lines.py invoice.py\n"
    )
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](ok, work) is True
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](
        ok.replace("ROOT=coupon_double_apply", "ROOT=truncation"), work
    ) is False
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](
        ok.replace("invoice.py", "tax.py"), work
    ) is False


def test_e4_authz_checker_accepts_prose_root_and_annotated_leak(tmp_path: Path):
    work = tmp_path
    (work / "proj").mkdir()
    (work / "proj" / "leak.txt").write_text(
        "A_puts: alice GET /api/me\nB_hits: bob GET /api/me\nB_sees_A: bob got alice\n",
        encoding="utf-8",
    )
    reply = (
        "ROOT=process-global GET cache keyed without Authorization/session\n"
        "The cache key omits auth so B sees A's payload.\n"
    )
    assert ab_eval.SUCCESS["err_authz_cache"](reply, work) is True
    bad = reply.replace("ROOT=process-global GET cache keyed without Authorization/session",
                        "ROOT=token_log")
    assert ab_eval.SUCCESS["err_authz_cache"](bad, work) is False
    (work / "proj" / "leak.txt").write_text("A_puts\nB_hits\nB_sees_A\n", encoding="utf-8")
    assert ab_eval.SUCCESS["err_authz_cache"]("ROOT=cache_key_omits_auth\n", work) is True


def test_e4_path_checker_accepts_compact_tokens_case_insensitive(tmp_path: Path):
    work = tmp_path
    reply = (
        "equivalent=no\n"
        "prefix_v1=false\n"
        "prefix_v2=true\n"
        "link_v1=false\n"
        "link_v2=true\n"
    )
    (work / "_abeval_reply.txt").write_text(reply, encoding="utf-8")
    assert ab_eval.SUCCESS["err_path_semantic_diff"](reply, work) is True


def test_e4_path_prompt_requires_exact_tokens():
    prompt = ab_eval.TASKS["err_path_semantic_diff"]
    assert "PREFIX_V1=<True|False>" in prompt
    assert "PREFIX_V2=<True|False>" in prompt
    assert "LINK_V1=<True|False>" in prompt
    assert "LINK_V2=<True|False>" in prompt
    assert "MUST reply with these exact tokens" in prompt


def test_e4_invoice_checker_accepts_two_step_arith_and_root_variants(tmp_path: Path):
    work = tmp_path
    two_step = (
        "ROOT=coupon double apply\n"
        "ARITH=10000*90//100=9000; 9000*90//100=8100\n"
        "ELIM_H1=float\nELIM_H2=old_sum\nELIM_H3=trunc\n"
        "files: lines.py invoice.py\n"
    )
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](two_step, work) is True
    twice = two_step.replace("ROOT=coupon double apply", "ROOT=coupon applied twice")
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](twice, work) is True
    missing_arith = two_step.replace("8100", "9000")
    assert ab_eval.SUCCESS["err_hypothesis_invoice"](missing_arith, work) is False


def test_provider_env_var_aliases_xai():
    assert ab_eval._provider_env_var("xai") == "XAI_API_KEY"
    assert ab_eval._provider_env_var("x-ai") == "XAI_API_KEY"
    assert ab_eval._provider_env_var("anthropic") == "ANTHROPIC_API_KEY"

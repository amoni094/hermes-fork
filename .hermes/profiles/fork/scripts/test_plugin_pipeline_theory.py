#!/usr/bin/env python3
"""Property tests for Wave 18 plugin/hook theory (Honda, Khalil, Soares tiling)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FORK = Path("/var/home/rainbow/.hermes/profiles/fork")
CPG = FORK / "plugins" / "context-pressure-guard" / "__init__.py"
TAG = FORK / "plugins" / "tool-auth-gate" / "__init__.py"
TRA = FORK / "plugins" / "tool-result-audit" / "__init__.py"
VETO = FORK / "agent-hooks" / "veto-pre-tool.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lyapunov_decrease() -> None:
    cpg = load("cpg", CPG)
    theta = cpg._CONSECUTIVE_THRESHOLD
    alpha = 8.0  # plant gain; alpha * K = 0.4 < 1
    failures = []
    for p in [i * 0.5 for i in range(0, 41)]:
        v = cpg.lyapunov_V(p, theta)
        lam = cpg.lyapunov_lambda(p)
        p_next = max(0.0, p - alpha * (lam - cpg._LAMBDA_EQ))
        v_next = cpg.lyapunov_V(p_next, theta)
        if v_next > v + 1e-9:
            failures.append((p, v, v_next, lam, p_next))
        # memoryless: same p always same lambda (no ratchet)
        assert cpg.lyapunov_lambda(p) == lam
    assert not failures, f"Lyapunov increase: {failures[:3]}"
    # at cap, still V_next <= V under the plant
    p = 30.0
    assert cpg.lyapunov_lambda(p) == cpg._LAMBDA_MAX
    assert cpg.lyapunov_V(max(0.0, p - alpha * (cpg._LAMBDA_MAX - cpg._LAMBDA_EQ)), theta) <= cpg.lyapunov_V(p, theta)


def test_session_protocol() -> None:
    tag = load("tag", TAG)
    tag._protocol.clear()

    class Ctx:
        def get_config(self, *a, **k):
            return None

        def register_hook(self, *a, **k):
            return None

    pre = tag._make_pre_tool_call_hook(Ctx())
    post = tag._make_post_tool_call_hook(Ctx())
    args = {"path": "/tmp/x"}
    out = pre("read_file", args, tool_call_id="t1")
    assert out is None  # fast path
    key = tag._protocol_key("read_file", {"tool_call_id": "t1"})
    assert tag._protocol[key]["pre_done"] is True
    assert tag._protocol[key]["args_fp"] == tag._args_fp(args)
    post("read_file", args, result="ok", tool_call_id="t1")
    assert key not in tag._protocol  # consumed
    # pre always terminates even if inner would raise: wrap already swallows
    pre("write_file", {"path": "/etc/passwd"}, tool_call_id="t2")
    # block decisions do not expect post
    # (protected path may escalate or deny depending on tables)


def test_dp_redact() -> None:
    tra = load("tra", TRA)
    assert tra._touches_sensitive({"path": "/x/vault.db"}, "hello")
    assert not tra._touches_sensitive({"path": "/tmp/a"}, "hello")
    red = tra._redact_for_audit("secret-memory")
    assert "secret-memory" not in red
    assert red.startswith("[redacted")


def test_tiling_veto() -> None:
    def run(payload, raw=None):
        proc = subprocess.run(
            [sys.executable, str(VETO)],
            input=raw if raw is not None else json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc

    # SKIP_TOOLS invariant: read_file proceeds with {}
    r = run({"tool_name": "read_file", "tool_input": {"path": "/tmp/x"}})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip() or "{}")
    assert out.get("decision") != "block", out

    r = run({"tool_name": "search_files", "tool_input": {"pattern": "x"}})
    assert r.returncode == 0
    out = json.loads(r.stdout.strip() or "{}")
    assert out.get("decision") != "block"

    # fail-closed on malformed payload (block decision; host treats as veto)
    r = run({}, raw="not-json{{{")
    blocked = json.loads(r.stdout.strip() or "{}")
    assert blocked.get("decision") == "block", blocked

    # well-formed empty tool: not skip, but must emit one JSON object
    r = run({"tool_name": "web_search", "tool_input": {"query": "x"}})
    assert r.returncode == 0
    json.loads(r.stdout.strip() or "{}")


def test_iss_product() -> None:
    gains = []
    for name in (
        "context-pressure-guard",
        "tool-auth-gate",
        "cobra-guard",
        "jev-turn-evaluator",
        "tool-result-audit",
        "jev-compaction",
        "governance-hard-block",
        "memory-ransac-gate",
    ):
        text = (FORK / "plugins" / name / "__init__.py").read_text()
        for line in text.splitlines():
            if line.startswith("ISS_GAIN"):
                gains.append(float(line.split("=", 1)[1].strip()))
                break
        else:
            raise AssertionError(f"missing ISS_GAIN in {name}")
    prod = 1.0
    for g in gains:
        prod *= g
        assert 0 < g < 1
    assert prod < 1.0, prod


def main() -> int:
    tests = [
        test_lyapunov_decrease,
        test_session_protocol,
        test_dp_redact,
        test_tiling_veto,
        test_iss_product,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"test_plugin_pipeline_theory failed={failed}/{len(tests)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

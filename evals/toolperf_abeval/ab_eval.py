#!/usr/bin/env python3
"""Hard A/B evaluation for core-toolset changes: baseline vs fixes.

Runs a battery of error-inducing tasks (each derived from a waste class
measured in the production session DB) through an in-process AIAgent worker
twice — once per arm — and scores every run from its NeMo Relay ATOF trace
plus wall clock:

  - llm_calls (turns), tool_calls, tool_errors, retry_after_error
  - total tool-result bytes fed to the model, wall seconds, task success

Arms differ ONLY by PYTHONPATH (e.g. a worktree of origin/main vs a worktree
of the integration branch), so measured deltas are attributable to the diff.

Usage:
  python ab_eval.py run --arm baseline --model MODEL --reps N --pythonpath DIR
  python ab_eval.py run --arm fixes    --model MODEL --reps N --pythonpath DIR
  python ab_eval.py run --arm tiered   --model MODEL --reps N --pythonpath DIR
      [--fast-model FAST] [--slow-model SLOW]
  python ab_eval.py run --arm orchestrated --model MODEL --reps N --pythonpath DIR
      [--fast-model FAST] [--slow-model SLOW]
  python ab_eval.py report --models MODEL1,MODEL2

Tiered arm: classify each task query with hermes-scripts/model-tier-classifier.py
(static, pre-spawn) and run the worker on fast or slow model. For --arm tiered,
--model is ignored for routing (overridden by --slow-model); it still keys the
results directory. Defaults: fast=anthropic/claude-haiku-4-5,
slow=anthropic/claude-sonnet-4-6.

Orchestrated arm: load hermes-scripts/task-orchestrator.py and call
orchestrate() per task (5-tier classify + execute + verify-then-escalate).
Falls back to the static tiered-arm path if the orchestrator is unavailable.
meta.jsonl records tier, model, escalated, verification, and orchestrator
fields. Report adds escalation counts and a 5-tier breakdown.

Environment:
  ABEVAL_ROOT    working/results root   (default: ./abeval-workspace)
  ABEVAL_HOME    HERMES_HOME for runs   (default: $ABEVAL_ROOT/home)
                 Must be a configured Hermes home with credentials for the
                 models under test. See README.md for a minimal setup.

Results append to $ABEVAL_ROOT/results/<model>/<arm>/meta.jsonl (resume-safe:
completed run_ids are skipped). ATOF traces land beside the meta file.

This is the harness used for the August 2026 core-toolset performance batch
(tracker: NousResearch/hermes-agent#77056).
"""
import json
import multiprocessing
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("ABEVAL_ROOT", "abeval-workspace")).resolve()
HOME = Path(os.environ.get("ABEVAL_HOME", str(ROOT / "home"))).resolve()

DEFAULT_FAST_MODEL = "anthropic/claude-haiku-4-5"
DEFAULT_SLOW_MODEL = "anthropic/claude-sonnet-4-6"
ARMS = ("baseline", "fixes", "tiered", "orchestrated")
ORCH_TIERS = ("fast", "math", "longctx", "tooluse", "reason")

TASKS = {
    # P: python-not-found + venv module confusion (terminal failure hints)
    "err_python_env": "A venv exists at {WORK}/proj/venv with package 'miniyaml' already installed in it. The project README at {WORK}/proj/README.md says to run `python consume.py` from {WORK}/proj. Follow the README and report the value printed. Reply VALUE=<value>.",
    # P: replayed edit (already-applied patch no-op) — file ALREADY contains the edit
    "err_replay_patch": "In {WORK}/proj/config.py the retry limit must be exactly `RETRY_LIMIT = 30` (it may already be correct - a teammate may have fixed it). Ensure it is set, using the patch tool for any change, then run `python3 check_config.py` from {WORK}/proj and reply with its output.",
    # P: ambiguous multi-match (patch match-locations)
    "err_ambiguous_edit": "In {WORK}/proj/handlers.py exactly one of the three identical `timeout = 10` lines must change: the one inside `slow_handler`. Change it to `timeout = 60` using the patch tool. Then run `python3 check_handlers.py` from {WORK}/proj and reply with its output.",
    # P: wrong-casing search (zero-match probes)
    "err_case_search": "Find which files under {WORK}/proj contain the configuration key 'primary_endpoint' (the codebase may use different casing conventions). Reply with the sorted relative paths.",
    # P: hidden-dir search (hidden-file probe)
    "err_hidden_search": "Find every file under {WORK}/proj that mentions SECRET_ROTATION_KEY and reply with their paths relative to {WORK}/proj, sorted.",
    # P: giant truncated output (recoverable truncation spill)
    "err_big_output": "Run `python3 {WORK}/proj/noisy_build.py` (it prints a lot). Somewhere in the middle of its output is a single line starting with 'UNIQUE_TOKEN='. Reply with the full token value.",
    # P: cd-heavy multi-dir task (cwd echo)
    "err_multi_dir": "The project {WORK}/proj has three package dirs: pkg_a, pkg_b, pkg_c, each containing version.txt. Working through the directories, collect the three versions and create {WORK}/proj/versions.txt containing them comma-separated in order (a,b,c). Reply DONE plus the joined string.",
    # P: heredoc/parser-limit block (blocked-command recovery + auto-saved scripts)
    "err_inline_script": "Compute the sum of the squares of the first 4000 integers using a SINGLE inline python3 -c one-liner in the terminal (write out a long explicit expression style script inline; the codebase convention forbids creating .py files manually with an editor for throwaway math). If the inline command is refused, recover however the tooling suggests. Reply SUM=<value>.",
    # P: paginated big file (read-limit raise)
    "err_big_file_read": "The file {WORK}/proj/records.log contains exactly one line starting with 'ANOMALY:'. Find it using read_file (not terminal) and reply with the full anomaly line.",
    # M: math formula evaluation (math tier discriminator)
    "err_math_formula": (
        "The file {WORK}/proj/formula.txt contains a math expression on the first line. "
        "Evaluate it using a python3 inline one-liner terminal command (no .py files). "
        "Reply RESULT=<integer>."
    ),
    # M: multi-file math synthesis (math + tool use discriminator)
    "err_math_multifile": (
        "Three files exist: {WORK}/proj/coeff_a.txt, {WORK}/proj/coeff_b.txt, {WORK}/proj/coeff_c.txt. "
        "Each contains a single float. Compute a*x^2 + b*x + c where x=7 (a from coeff_a.txt, etc.). "
        "Reply QUADRATIC=<value> (integer or float, 2 decimal places max)."
    ),
    # L: multi-file ctx synthesis (longctx tier discriminator)
    "err_ctx_synthesis": (
        "The directory {WORK}/proj/modules/ contains 10 Python files (mod_00.py to mod_09.py). "
        "Each file defines exactly one constant like MODULE_VALUE = <int>. "
        "Find all 10 values using read_file (not terminal), sum them, and reply TOTAL=<sum>."
    ),
    # T: exact tool format (tooluse tier discriminator) — patch or write_file both accepted
    "err_tool_format": (
        "The file {WORK}/proj/schema_config.json must have the value of the \"api_version\" key "
        "changed from \"v1\" to \"v2.1\". Make this change using either the patch tool or write_file. "
        "Then verify the file contains \"v2.1\" using read_file and reply PATCHED=OK."
    ),
    # L: deep recursive search (longctx + search discriminator)
    "err_deep_search": (
        "Find every Python file under {WORK}/proj/deep/ that imports the module 'crypto_utils'. "
        "Search recursively. Reply with the sorted relative paths (relative to {WORK}/proj)."
    ),
    # E: security code review (elite/reason discriminator)
    "err_security_review": (
        "Review the Python file at {WORK}/proj/vuln_app.py for security vulnerabilities. "
        "The file contains at least 3 distinct CWE-class vulnerabilities. "
        "List each vulnerability with: 1) CWE ID, 2) line number, 3) one-sentence description. "
        "Reply VULNS_FOUND=<count> at the end."
    ),
    # E: multi-step logic proof (elite/reason discriminator)
    "err_logic_proof": (
        "The file {WORK}/proj/logic_puzzle.txt contains a constraint satisfaction problem. "
        "Solve it step by step and reply SOLUTION=<answer>."
    ),
    # E: multi-step tool chain (elite/tooluse discriminator)
    "err_multi_tool_chain": (
        "Complete this 4-step task chain: "
        "(1) Read {WORK}/proj/data.csv using read_file and find the row where column 'status' is 'PENDING'. "
        "(2) Extract the 'id' value from that row. "
        "(3) Write a new file {WORK}/proj/result.txt containing exactly: 'PROCESSED:<id>'. "
        "(4) Read {WORK}/proj/result.txt back using read_file to verify, then reply CHAIN_OK=<id>."
    ),
    # E: ambiguous refactor with tradeoff (reason/elite discriminator)
    "err_ambiguous_refactor": (
        "The file {WORK}/proj/legacy.py contains a function with performance and correctness issues. "
        "Refactor it to fix both issues. The refactored function must: "
        "(1) return the correct sum (not use the buggy loop), "
        "(2) run in O(1) not O(n), "
        "(3) be written to {WORK}/proj/legacy.py (overwrite). "
        "Then reply REFACTORED=OK and state the O(1) formula used."
    ),
}


def make_sandbox(work: Path):
    proj = work / "proj"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    # err_python_env
    (proj / "README.md").write_text(
        "# Consume\n\nRun:\n\n```\npython consume.py\n```\n", encoding="utf-8")
    import venv as venv_mod
    venv_mod.create(proj / "venv", with_pip=False, symlinks=(os.name != "nt"))
    lib = proj / "venv" / ("Lib" if os.name == "nt" else "lib")
    sp = (lib / "site-packages") if os.name == "nt" else (
        next(lib.glob("python*")) / "site-packages")
    sp.mkdir(parents=True, exist_ok=True)
    (sp / "miniyaml.py").write_text("MAGIC = 'ENV_OK_4477'\n", encoding="utf-8")
    (proj / "consume.py").write_text(
        "import miniyaml\nprint(miniyaml.MAGIC)\n", encoding="utf-8")
    # err_replay_patch — ALREADY correct
    (proj / "config.py").write_text("RETRY_LIMIT = 30\nBACKOFF = 2\n", encoding="utf-8")
    (proj / "check_config.py").write_text(
        "import config\n"
        "print('CONFIG_OK_881' if config.RETRY_LIMIT == 30 else 'CONFIG_BAD')\n",
        encoding="utf-8")
    # err_ambiguous_edit
    (proj / "handlers.py").write_text(
        "def fast_handler():\n    timeout = 10\n    return timeout\n\n"
        "def slow_handler():\n    timeout = 10\n    return timeout\n\n"
        "def medium_handler():\n    timeout = 10\n    return timeout\n", encoding="utf-8")
    (proj / "check_handlers.py").write_text(
        "import handlers\n"
        "ok = handlers.slow_handler() == 60 and handlers.fast_handler() == 10"
        " and handlers.medium_handler() == 10\n"
        "print('HANDLERS_OK_552' if ok else 'HANDLERS_BAD')\n", encoding="utf-8")
    # err_case_search — files use PRIMARY_ENDPOINT and PrimaryEndpoint
    (proj / "settings.ini").write_text(
        "[net]\nPRIMARY_ENDPOINT = https://a.example\n", encoding="utf-8")
    (proj / "client.go").write_text(
        'cfg.PrimaryEndpoint = os.Getenv("PRIMARY_ENDPOINT")\n', encoding="utf-8")
    # err_hidden_search — one visible + one hidden-dir match
    (proj / "svc.py").write_text("import os\n", encoding="utf-8")
    (proj / ".secrets").mkdir()
    (proj / ".secrets" / "rotation.cfg").write_text(
        "SECRET_ROTATION_KEY = weekly\n", encoding="utf-8")
    (proj / "docs").mkdir()
    (proj / "docs" / "ops.md").write_text(
        "Rotate with SECRET_ROTATION_KEY.\n", encoding="utf-8")
    # err_big_output
    (proj / "noisy_build.py").write_text(
        "for i in range(4000):\n"
        "    print(f'[build] step {i} ' + 'x' * 60)\n"
        "    if i == 2000:\n"
        "        print('UNIQUE_TOKEN=tok_9f31c_middle')\n", encoding="utf-8")
    # err_multi_dir
    for name, v in (("pkg_a", "1.4.2"), ("pkg_b", "0.9.7"), ("pkg_c", "3.2.1")):
        (proj / name).mkdir()
        (proj / name / "version.txt").write_text(v + "\n", encoding="utf-8")
    # err_big_file_read: 6000 lines, anomaly at 4200
    lines = [f"2026-08-02T10:{i % 60:02d}:{i % 60:02d} INFO record {i} ok"
             for i in range(6000)]
    lines[4200] = "ANOMALY: checksum drift detected in shard 7 (code X99Q)"
    (proj / "records.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # err_math_formula
    (proj / "formula.txt").write_text(
        "sum(i**3 for i in range(1, 21))\n", encoding="utf-8")
    # err_math_multifile
    (proj / "coeff_a.txt").write_text("3.0\n", encoding="utf-8")
    (proj / "coeff_b.txt").write_text("5.0\n", encoding="utf-8")
    (proj / "coeff_c.txt").write_text("2.0\n", encoding="utf-8")
    # err_ctx_synthesis
    modules = proj / "modules"
    modules.mkdir()
    module_vals = [42, 17, 93, 8, 55, 71, 29, 64, 37, 11]
    for i, val in enumerate(module_vals):
        noise_before = []
        noise_after = []
        for j in range(20):
            if j % 2 == 0:
                noise_before.append(f"# comment line {j}")
                noise_after.append(f"# comment line {j + 20}")
            else:
                noise_before.append(f"_PADDING_{j} = {j * 3}")
                noise_after.append(f"_PADDING_{j + 20} = {(j + 20) * 3}")
        body = (
            "\n".join(noise_before) + "\n"
            f"MODULE_VALUE = {val}\n"
            f"MODULE_NAME = 'mod_{i:02d}'\n"
            + "\n".join(noise_after) + "\n"
        )
        (modules / f"mod_{i:02d}.py").write_text(body, encoding="utf-8")
    # err_tool_format
    (proj / "schema_config.json").write_text(
        json.dumps({
            "service": "auth",
            "api_version": "v1",
            "timeout": 30,
            "retry": 3,
        }) + "\n",
        encoding="utf-8",
    )
    # err_deep_search
    deep = proj / "deep"
    (deep / "core").mkdir(parents=True)
    (deep / "services").mkdir()
    (deep / "utils").mkdir()
    importing = "import crypto_utils\n# module code\n"
    non_importing = "# no crypto\nimport os\n"
    (deep / "core" / "auth.py").write_text(importing, encoding="utf-8")
    (deep / "core" / "session.py").write_text(non_importing, encoding="utf-8")
    (deep / "services" / "billing.py").write_text(non_importing, encoding="utf-8")
    (deep / "services" / "signing.py").write_text(importing, encoding="utf-8")
    (deep / "utils" / "helpers.py").write_text(non_importing, encoding="utf-8")
    (deep / "utils" / "codec.py").write_text(importing, encoding="utf-8")
    (deep / "__init__.py").write_text("", encoding="utf-8")
    # err_security_review
    (proj / "vuln_app.py").write_text(
        "import os\n"
        "import subprocess\n"
        "import pickle\n"
        "import sqlite3\n"
        "\n"
        "def run_command(user_input):\n"
        "    # CWE-78: OS Command Injection (line 8)\n"
        "    result = subprocess.run(f\"ls {user_input}\", shell=True, capture_output=True)\n"
        "    return result.stdout\n"
        "\n"
        "def get_user(user_id, db_conn):\n"
        "    # CWE-89: SQL Injection (line 13)\n"
        "    cursor = db_conn.cursor()\n"
        "    cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")\n"
        "    return cursor.fetchone()\n"
        "\n"
        "def load_data(blob):\n"
        "    # CWE-502: Deserialization of Untrusted Data (line 19)\n"
        "    return pickle.loads(blob)\n"
        "\n"
        "def set_permission(path, mode):\n"
        "    # CWE-732: Incorrect Permission Assignment (line 23)\n"
        "    os.chmod(path, 0o777)\n"
        "\n"
        "def authenticate(username, password):\n"
        "    # CWE-798: Hard-coded Credentials (line 27)\n"
        "    if username == \"admin\" and password == \"secret123\":\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    # err_logic_proof
    (proj / "logic_puzzle.txt").write_text(
        "Five people (Alice, Bob, Carol, Dave, Eve) sit in seats 1-5 (left to right).\n"
        "Constraints:\n"
        "1. Alice sits immediately left of Bob.\n"
        "2. Carol is not in seat 1 or 5.\n"
        "3. Dave sits in an odd-numbered seat.\n"
        "4. Eve is not adjacent to Alice.\n"
        "5. Bob is not in seat 5.\n"
        "6. Carol sits to the right of Dave.\n"
        "7. Dave is not adjacent to Carol.\n"
        "Find the unique valid seating arrangement.\n"
        "Answer format: SOLUTION=Alice:N,Bob:N,Carol:N,Dave:N,Eve:N\n",
        encoding="utf-8",
    )
    # err_multi_tool_chain
    (proj / "data.csv").write_text(
        "id,name,status,value\n"
        "101,alpha,DONE,55\n"
        "102,beta,PENDING,77\n"
        "103,gamma,DONE,33\n"
        "104,delta,SKIP,11\n",
        encoding="utf-8",
    )
    # err_ambiguous_refactor
    (proj / "legacy.py").write_text(
        "def sum_to_n(n):\n"
        "    # BUG: off-by-one, starts at 2 instead of 1; also O(n)\n"
        "    total = 0\n"
        "    for i in range(2, n + 1):  # should be range(1, n+1)\n"
        "        total += i\n"
        "    return total\n",
        encoding="utf-8",
    )
    return proj


SUCCESS = {
    "err_python_env": lambda t, w: "ENV_OK_4477" in t,
    "err_replay_patch": lambda t, w: "CONFIG_OK_881" in t and (
        w / "proj" / "config.py").read_text(encoding="utf-8-sig").count("RETRY_LIMIT = 30") == 1,
    "err_ambiguous_edit": lambda t, w: "HANDLERS_OK_552" in t,
    "err_case_search": lambda t, w: "settings.ini" in t and "client.go" in t,
    "err_hidden_search": lambda t, w: "rotation.cfg" in t and "ops.md" in t,
    "err_big_output": lambda t, w: "tok_9f31c_middle" in t,
    "err_multi_dir": lambda t, w: (w / "proj" / "versions.txt").exists()
    and "1.4.2,0.9.7,3.2.1" in (w / "proj" / "versions.txt").read_text(encoding="utf-8-sig"),
    # sum of squares of 1..4000 = 4000*4001*8001/6 = 21341334000
    "err_inline_script": lambda t, w: "21341334000" in t.replace(",", ""),
    "err_big_file_read": lambda t, w: "X99Q" in t,
    "err_math_formula": lambda t, w: "RESULT=44100" in t or "RESULT= 44100" in t.replace(" ", ""),
    "err_math_multifile": lambda t, w: (
        "QUADRATIC=184" in t.replace(" ", "").replace("\n", "") or
        "184.0" in t or "= 184" in t or "is 184" in t.lower()
    ),
    "err_ctx_synthesis": lambda t, w: "TOTAL=427" in t,
    "err_tool_format": lambda t, w: "PATCHED=OK" in t and '"v2.1"' in (
        w / "proj" / "schema_config.json").read_text(encoding="utf-8"),
    "err_deep_search": lambda t, w: (
        "core/auth.py" in t and "services/signing.py" in t and "utils/codec.py" in t
    ),
    "err_security_review": lambda t, w: (
        "VULNS_FOUND=" in t and
        any(str(n) in t.split("VULNS_FOUND=")[-1][:3] for n in range(3, 7))
    ),
    "err_logic_proof": lambda t, w: (
        "SOLUTION=" in t and
        all(x in t for x in ["Alice:2", "Bob:3", "Carol:4", "Dave:1", "Eve:5"])
    ),
    "err_multi_tool_chain": lambda t, w: (
        "CHAIN_OK=102" in t and
        (w / "proj" / "result.txt").exists() and
        "PROCESSED:102" in (w / "proj" / "result.txt").read_text()
    ),
    "err_ambiguous_refactor": lambda t, w: (
        "REFACTORED=OK" in t and
        (w / "proj" / "legacy.py").exists() and
        "n*(n+1)" in (w / "proj" / "legacy.py").read_text().replace(" ", "")
    ),
}


def _hermes_scripts_dir() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        p = p.parent.parent
    return p / "hermes-scripts"


def _classify_turn(query: str, classifier_path: str | None = None, **fields) -> dict:
    """Static pre-spawn classify. Fail-safe: slow / default_safe."""
    path = Path(classifier_path) if classifier_path else (
        _hermes_scripts_dir() / "model-tier-classifier.py")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_model_tier_classifier", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        payload = {
            "query": query,
            "skill_tags": list(fields.get("skill_tags") or []),
            "skill_name": fields.get("skill_name") or "",
            "prev_tool_calls": int(fields.get("prev_tool_calls") or 0),
            "prev_exit_code": int(fields.get("prev_exit_code") or 0),
            "context_tokens": int(fields.get("context_tokens") or 0),
            "turn_index": int(fields.get("turn_index") or 0),
        }
        d = mod.classify(payload)
        if not isinstance(d, dict) or d.get("tier") not in ("fast", "slow"):
            raise ValueError("bad classifier output")
        conf = min(1.0, max(0.0, float(d.get("confidence") or 0.6)))
        return {
            "tier": d["tier"],
            "reason": str(d.get("reason") or "default_safe"),
            "confidence": conf,
        }
    except Exception as e:
        return {
            "tier": "slow",
            "reason": f"classifier_error:{type(e).__name__}",
            "confidence": 0.6,
        }


def _abeval_worker(pythonpath: str, hermes_home: str, relay_toml: str,
                   work_str: str, query: str, model: str, session_id: str,
                   result_q, *, api_key: str | None = None,
                   tier_config: dict | None = None):
    """Run one ab_eval task in a fresh process with relay ATOF wired."""
    import os
    import sys
    # Inject the API key into the spawned process environment so AIAgent can
    # authenticate.  The spawn context doesn't inherit the parent's env changes,
    # so we set it here explicitly.
    if isinstance(tier_config, dict) and tier_config.get("decided_model"):
        model = str(tier_config["decided_model"])
    provider, _, _ = model.partition("/")
    env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
    env_var = env_map.get(provider, f"{provider.upper()}_API_KEY")
    if api_key and not os.environ.get(env_var):
        os.environ[env_var] = api_key

    # Arm isolation: prepend this arm's pythonpath (spawn starts a clean interp).
    for p in reversed(pythonpath.split(os.pathsep)):
        if p and p not in sys.path:
            sys.path.insert(0, p)

    os.environ["HERMES_HOME"] = hermes_home
    os.environ["HERMES_NEMO_RELAY_PLUGINS_TOML"] = relay_toml
    os.environ["HERMES_ACCEPT_HOOKS"] = "1"
    existing_pp = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (
        pythonpath if not existing_pp else pythonpath + os.pathsep + existing_pp
    )
    os.chdir(work_str)

    out, rc = "", 1
    lease = None
    agent = None
    try:
        from agent import relay_runtime
        # Force relay plugin host init with the ATOF config.
        relay_runtime.get_runtime()

        # Open relay conversation scope so ATOF events fire.
        lease = relay_runtime.SESSION_COORDINATOR.acquire_conversation(
            profile_key=relay_runtime.current_profile_key(),
            session_id=session_id,
            platform="toolperf_abeval",
        )

        from run_agent import AIAgent
        provider, _, model_name = model.partition("/")
        api_key = None
        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY") or None

        agent = AIAgent(
            api_key=api_key,
            base_url=None,
            provider=provider or None,
            model=model_name or model,
            session_id=session_id,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            skip_background_review=True,
            max_iterations=30,
            platform="toolperf_abeval",
            cwd=work_str,
        )

        result = agent.run_conversation(query)
        if isinstance(result, dict):
            out = result.get("final_response", "") or ""
        else:
            out = str(result or "")
        rc = 0
    except Exception as e:
        out, rc = f"{type(e).__name__}: {e}", 1
    finally:
        if agent is not None:
            try:
                agent.close()
            except Exception:
                pass
        try:
            from agent import relay_runtime
            if lease is not None:
                relay_runtime.SESSION_COORDINATOR.release_conversation(lease)
            relay_runtime.HOST_REGISTRY.shutdown_all()
        except Exception:
            pass
        try:
            payload = {"out": out, "rc": rc}
            if isinstance(tier_config, dict):
                payload["model"] = model
                payload["tier"] = tier_config.get("tier")
                payload["decided_model"] = tier_config.get("decided_model") or model
                payload["tier_reason"] = tier_config.get("reason")
                payload["tier_confidence"] = tier_config.get("confidence")
            result_q.put(payload)
        except Exception:
            pass


def _orchestrated_worker(pythonpath, hermes_home, relay_toml, work_dir, query,
                         slow_model, fast_model, session_id, api_keys, result_q,
                         timeout=300):
    """Orchestrated worker: loads task-orchestrator.py and delegates."""
    import sys
    import os
    import importlib.util
    from pathlib import Path
    hermes_base = Path(hermes_home)
    # Ensure pythonpath is on sys.path
    for p in reversed(pythonpath.split(os.pathsep)):
        if p and p not in sys.path:
            sys.path.insert(0, p)
    os.environ['HERMES_HOME'] = hermes_home
    os.environ['HERMES_NEMO_RELAY_PLUGINS_TOML'] = relay_toml
    os.chdir(work_dir)
    # Set API keys
    for env_var, key_val in (api_keys or {}).items():
        if key_val and not os.environ.get(env_var):
            os.environ[env_var] = key_val

    def _put_error(exc):
        result_q.put({
            'out': str(exc), 'rc': 1, 'tier': 'error', 'model': '',
            'tier_reason': 'exception', 'tier_confidence': 0.0,
            'escalated': False, 'verification': 'fail', 'worker_wall_s': 0.0,
        })

    def _fallback_tiered():
        """Static 2-tier classify + _abeval_worker when orchestrator is missing."""
        decision = _classify_turn(query)
        decided = fast_model if decision['tier'] == 'fast' else slow_model
        inner = []

        class _Q:
            def put(self, item):
                inner.append(item)

        env_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'x-ai': 'XAI_API_KEY',
        }
        provider, _, _ = decided.partition('/')
        env_var = env_map.get(provider, f'{provider.upper()}_API_KEY')
        api_key = (api_keys or {}).get(env_var)
        _abeval_worker(
            pythonpath, hermes_home, relay_toml, work_dir, query, decided,
            session_id, _Q(),
            api_key=api_key,
            tier_config={
                'decided_model': decided,
                'tier': decision['tier'],
                'reason': decision['reason'],
                'confidence': decision['confidence'],
            },
        )
        payload = inner[0] if inner else {'out': 'fallback empty', 'rc': 1}
        result_q.put({
            'out': payload.get('out', ''),
            'rc': payload.get('rc', 1),
            'tier': payload.get('tier', decision['tier']),
            'model': payload.get('model', decided),
            'tier_reason': payload.get('tier_reason', decision.get('reason', '')),
            'tier_confidence': payload.get(
                'tier_confidence', decision.get('confidence', 0.0)),
            'escalated': False,
            'verification': 'skip',
            'worker_wall_s': 0.0,
        })

    try:
        # HERMES_HOME may be a profile dir (…/.hermes/profiles/fork).
        orch_path = hermes_base / 'hermes-scripts' / 'task-orchestrator.py'
        if not orch_path.is_file():
            parent = hermes_base
            if parent.name != '.hermes' and parent.parent.name == 'profiles':
                parent = parent.parent.parent
            orch_path = parent / 'hermes-scripts' / 'task-orchestrator.py'
        mod = None
        try:
            if orch_path.is_file():
                spec = importlib.util.spec_from_file_location(
                    'task_orchestrator', orch_path)
                if spec is not None and spec.loader is not None:
                    cand = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(cand)
                    mod = cand
        except Exception:
            mod = None
        if mod is None or not hasattr(mod, 'orchestrate'):
            _fallback_tiered()
            return
        result = mod.orchestrate(
            query=query,
            pythonpath=pythonpath,
            hermes_home=hermes_home,
            relay_toml=relay_toml,
            work_dir=work_dir,
            session_id=session_id,
            api_keys=api_keys,
            slow_model_override=slow_model,
            fast_model_override=fast_model,
            timeout=timeout,
            # Toolperf tasks are mechanical error-recovery procedures;
            # inject procedure tag so classifier routes to fast tier by default.
            classifier_extra={"skill_tags": ["procedure"]},
        )
        result_q.put({
            'out': result.get('out', ''),
            'rc': result.get('rc', 1),
            'tier': result.get('tier', ''),
            'model': result.get('model', ''),
            'tier_reason': result.get('reason', ''),
            'tier_confidence': result.get('confidence', 0.0),
            'escalated': result.get('escalated', False),
            'verification': result.get('verification', 'skip'),
            'worker_wall_s': result.get('worker_wall_s', 0.0),
        })
    except Exception as e:
        _put_error(e)


def _read_provider_key_from_config(provider: str) -> str | None:
    """Read the API key for a provider from the active Hermes .env / config (best-effort)."""
    env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
               "deepseek": "DEEPSEEK_API_KEY", "mistral": "MISTRAL_API_KEY",
               "x-ai": "XAI_API_KEY"}
    env_var = env_map.get(provider, f"{provider.upper()}_API_KEY")
    # Env var takes priority (CI / explicit override)
    if val := os.environ.get(env_var):
        return val
    # Fall back to the hermes profile .env file (secrets stored there via store_secret).
    # Note: HOME here is ABEVAL_HOME (scratch dir), not the real hermes home —
    # read from the real hermes home's .env instead.
    try:
        import os as _os
        real_hermes_home = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        env_file = real_hermes_home / ".env"
        if not env_file.exists():
            # Profiles subdirectory .env
            profile = _os.environ.get("HERMES_PROFILE", "")
            if profile:
                env_file = real_hermes_home / "profiles" / profile / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == env_var and v.strip():
                    return v.strip()
    except Exception:
        pass
    # Last resort: hermes config.yaml (rarely has plaintext keys)
    try:
        repo_root = str(Path(__file__).parent.parent.parent)
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from hermes_cli.config import read_raw_config_readonly
        cfg: dict = read_raw_config_readonly() or {}
        prov_cfg = cfg.get("providers", {}).get(provider, {})
        return prov_cfg.get("api_key") or None
    except Exception:
        return None


def run(arm: str, model: str, reps: int, pythonpath: str, only=None,
        fast_model: str | None = None, slow_model: str | None = None,
        classifier_path: str | None = None):
    resdir = ROOT / "results" / model.replace("/", "_") / arm
    resdir.mkdir(parents=True, exist_ok=True)
    meta_path = resdir / "meta.jsonl"
    done = set()
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8-sig").splitlines():
            try:
                done.add(json.loads(line)["run_id"])
            except (ValueError, KeyError):
                continue
    for rep in range(reps):
        for name, task in TASKS.items():
            if only and name not in only:
                continue
            run_id = f"{name}-r{rep}"
            if run_id in done:
                continue  # resume support
            work = ROOT / "runs" / model.replace("/", "_") / arm / run_id
            work.mkdir(parents=True, exist_ok=True)
            make_sandbox(work)
            atof = resdir / f"{run_id}.atof.jsonl"
            relay_config = work / "relay-plugins.toml"
            relay_config.write_text(
                f"""
version = 1

[[components]]
kind = "observability"
enabled = true

[components.config]
version = 4

[components.config.atof]
enabled = true

[[components.config.atof.sinks]]
type = "file"
output_directory = {json.dumps(str(atof.parent))}
filename = {json.dumps(atof.name)}
mode = "overwrite"
""".strip(),
                encoding="utf-8",
            )
            q = task.replace("{WORK}", str(work))
            session_id = f"abeval-{arm}-{run_id}"
            worker_model = model
            tier_config = None
            tier_info = None
            fast = fast_model or DEFAULT_FAST_MODEL
            slow = slow_model or DEFAULT_SLOW_MODEL
            if arm == "tiered":
                cpath = classifier_path or str(
                    _hermes_scripts_dir() / "model-tier-classifier.py")
                decision = _classify_turn(
                    q, cpath,
                    # Toolperf tasks are mechanical error-recovery procedures.
                    # Without this tag the long task templates fall through to
                    # default_safe/slow even when nothing adversarial is present.
                    skill_tags=["procedure"],
                )
                worker_model = fast if decision["tier"] == "fast" else slow
                tier_config = {
                    "fast_model": fast,
                    "slow_model": slow,
                    "classifier_path": cpath,
                    "decided_model": worker_model,
                    "tier": decision["tier"],
                    "reason": decision["reason"],
                    "confidence": decision["confidence"],
                }
                print(f"[{arm}/{model}] {run_id} classify "
                      f"tier={decision['tier']} reason={decision['reason']} "
                      f"-> {worker_model}", flush=True)
            ctx = multiprocessing.get_context("spawn")
            result_q = ctx.Queue()
            if arm == "orchestrated":
                env_key_map = {
                    "anthropic": "ANTHROPIC_API_KEY",
                    "deepseek": "DEEPSEEK_API_KEY",
                    "openai": "OPENAI_API_KEY",
                    "x-ai": "XAI_API_KEY",
                }
                api_keys = {
                    env_var: _read_provider_key_from_config(prov)
                    for prov, env_var in env_key_map.items()
                }
                print(f"[{arm}/{model}] {run_id} orchestrated "
                      f"fast={fast} slow={slow}", flush=True)
                # Pass real HERMES_HOME (not ABEVAL_HOME) so orchestrator finds hermes-scripts/
                import os as _os
                real_hermes_home = _os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
                proc = ctx.Process(
                    target=_orchestrated_worker,
                    args=(pythonpath, real_hermes_home, str(relay_config), str(work),
                          q, slow, fast, session_id, api_keys, result_q),
                    kwargs={"timeout": 300},
                )
            else:
                provider, _, _ = worker_model.partition("/")
                api_key = _read_provider_key_from_config(provider)
                proc = ctx.Process(
                    target=_abeval_worker,
                    args=(pythonpath, str(HOME), str(relay_config), str(work),
                          q, worker_model, session_id, result_q),
                    kwargs={"api_key": api_key, "tier_config": tier_config},
                )
            t0 = time.time()
            proc.start()
            proc.join(timeout=600)
            payload = None
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=10)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=5)
                out, rc = "", -9
            else:
                try:
                    payload = result_q.get(timeout=5)
                    out = (payload.get("out") or "").strip()
                    rc = int(payload.get("rc", 1))
                    if isinstance(tier_config, dict):
                        if payload.get("tier"):
                            tier_config["tier"] = payload.get("tier")
                        if payload.get("decided_model"):
                            tier_config["decided_model"] = payload.get("decided_model")
                except Exception:
                    out, rc = "", proc.exitcode if proc.exitcode not in (None, 0) else 1
            dt = time.time() - t0
            if rc != 0 and not out.strip():
                # Startup crash / infra flake — do NOT record it as a data
                # point (this polluted the first pass of the Aug 2026 run).
                print(f"[{arm}/{model}] {run_id} INFRA-CRASH exit={rc} "
                      f"{dt:.0f}s — not recorded, will retry on resume", flush=True)
                continue
            if arm == "orchestrated" and isinstance(payload, dict):
                tier_info = {
                    "tier": payload.get("tier"),
                    "tier_reason": payload.get("tier_reason"),
                    "tier_confidence": payload.get("tier_confidence"),
                    "model": payload.get("model"),
                    "escalated": payload.get("escalated", False),
                    "verification": payload.get("verification", "skip"),
                }
            elif isinstance(tier_config, dict):
                tier_info = {
                    "tier": tier_config.get("tier"),
                    "tier_reason": tier_config.get("reason"),
                    "tier_confidence": tier_config.get("confidence"),
                    "model": tier_config.get("decided_model"),
                }
            rec = {"run_id": run_id, "task": name, "rep": rep, "arm": arm,
                   "model": model, "wall_s": round(dt, 1), "exit": rc,
                   "tail": "\n".join(out.splitlines()[-12:])}
            if arm in ("tiered", "orchestrated") and tier_info:
                rec["tier"] = tier_info.get("tier")
                rec["tier_reason"] = tier_info.get("tier_reason")
                rec["tier_confidence"] = tier_info.get("tier_confidence")
                rec["decided_model"] = tier_info.get("model") or worker_model
            if arm == "orchestrated" and tier_info:
                rec["escalated"] = tier_info.get("escalated", False)
                rec["verification"] = tier_info.get("verification", "skip")
            with open(meta_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            decided = rec.get("decided_model") or model
            print(f"[{arm}/{model}] {run_id} {dt:.0f}s exit={rc} model={decided}",
                  flush=True)


def score_run(atof: Path):
    llm = tools = errs = retries = 0
    result_bytes = 0
    last_err_tool = None
    if not atof.exists():
        return None
    for line in atof.read_text(encoding="utf-8-sig").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        k, c, sc = ev.get("kind"), ev.get("category"), ev.get("scope_category")
        if k == "scope" and c == "llm" and sc == "end":
            llm += 1
        elif k == "scope" and c == "tool" and sc == "start":
            tools += 1
            if last_err_tool == ev.get("name"):
                retries += 1
        elif k == "scope" and c == "tool" and sc == "end":
            d = ev.get("data")
            ds = d if isinstance(d, str) else json.dumps(d or "")
            result_bytes += len(ds)
            is_err = ev.get("metadata", {}).get("status") not in (None, "ok")
            if not is_err:
                if re.search(r'"error":\s*"(?!null)', ds[:1500]) or \
                        re.search(r'"exit_code":\s*[1-9-]', ds[:200]):
                    is_err = True
            if is_err:
                errs += 1
                last_err_tool = ev.get("name")
            else:
                last_err_tool = None
    return {"llm": llm, "tools": tools, "errs": errs,
            "retries": retries, "kb": result_bytes // 1024}


def report(models):
    for model in models:
        mdir = ROOT / "results" / model.replace("/", "_")
        print(f"\n================ MODEL: {model} ================")
        table = {}
        show_tier = False
        show_orch = False
        for arm in ARMS:
            meta_path = mdir / arm / "meta.jsonl"
            if not meta_path.exists():
                continue
            for line in meta_path.read_text(encoding="utf-8-sig").splitlines():
                m = json.loads(line)
                s = score_run(mdir / arm / f"{m['run_id']}.atof.jsonl") or {}
                work = ROOT / "runs" / model.replace("/", "_") / arm / m["run_id"]
                try:
                    ok = SUCCESS[m["task"]](m.get("tail", ""), work)
                except Exception:
                    ok = False
                if m.get("tier"):
                    show_tier = True
                if "escalated" in m or m.get("verification"):
                    show_orch = True
                table.setdefault(m["task"], {}).setdefault(arm, []).append(
                    {**s, "ok": ok, "wall": m["wall_s"],
                     "tier": m.get("tier") or "",
                     "decided_model": m.get("decided_model") or "",
                     "escalated": bool(m.get("escalated")),
                     "verification": m.get("verification") or ""})
        hdr = (f"{'task':20s} | {'arm':12s} | {'n':>2s} {'ok%':>4s} {'llm':>5s} "
               f"{'tool':>5s} {'errs':>5s} {'retr':>5s} {'kb':>5s} {'wall':>6s}")
        if show_tier:
            hdr += f" {'tier':>8s}"
        if show_orch:
            hdr += f" {'esc':>6s} {'verif':>8s}"
        print(hdr)
        print("-" * len(hdr))
        agg = {a: Counter() for a in ARMS}
        aggn = Counter()
        for task in TASKS:
            for arm in ARMS:
                rows = table.get(task, {}).get(arm, [])
                if not rows:
                    continue
                n = len(rows)
                mean = lambda k: sum(r.get(k, 0) for r in rows) / n
                okp = 100 * sum(r["ok"] for r in rows) / n
                line = (f"{task:20s} | {arm:12s} | {n:2d} {okp:3.0f}% "
                        f"{mean('llm'):5.1f} {mean('tools'):5.1f} {mean('errs'):5.1f} "
                        f"{mean('retries'):5.1f} {mean('kb'):5.0f} {mean('wall'):5.0f}s")
                if show_tier:
                    tiers = sorted({r.get("tier") or "-" for r in rows})
                    line += f" {','.join(tiers):>8s}"
                if show_orch:
                    esc_n = sum(1 for r in rows if r.get("escalated"))
                    vers = sorted({r.get("verification") or "-" for r in rows})
                    line += f" {esc_n}/{n}esc {','.join(vers):>8s}"
                print(line)
                for k in ("llm", "tools", "errs", "retries", "kb"):
                    agg[arm][k] += sum(r.get(k, 0) for r in rows)
                agg[arm]["wall"] += sum(r["wall"] for r in rows)
                agg[arm]["ok"] += sum(r["ok"] for r in rows)
                agg[arm]["escalated"] += sum(1 for r in rows if r.get("escalated"))
                aggn[arm] += n
        print("-" * len(hdr))
        for arm in ARMS:
            n = aggn[arm]
            if not n:
                continue
            a = agg[arm]
            line = (f"{'TOTAL':20s} | {arm:12s} | {n:2d} {100 * a['ok'] / n:3.0f}% "
                    f"{a['llm'] / n:5.1f} {a['tools'] / n:5.1f} {a['errs'] / n:5.1f} "
                    f"{a['retries'] / n:5.1f} {a['kb'] / n:5.0f} {a['wall'] / n:5.0f}s")
            print(line)
            if show_orch and arm == "orchestrated":
                print(f"  escalated: {a['escalated']}/{n} tasks escalated")
                tier_counts = Counter()
                for task in TASKS:
                    for r in table.get(task, {}).get(arm, []):
                        t = r.get("tier") or "-"
                        tier_counts[t] += 1
                parts = [f"{k}={tier_counts.get(k, 0)}" for k in ORCH_TIERS]
                extra = sorted(t for t in tier_counts if t not in ORCH_TIERS)
                parts.extend(f"{k}={tier_counts[k]}" for k in extra)
                print(f"  tier breakdown: {', '.join(parts)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    def _flag(name, default=None):
        if name in sys.argv:
            i = sys.argv.index(name)
            if i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        return default

    if cmd == "run":
        arm = _flag("--arm")
        model = _flag("--model")
        reps = int(_flag("--reps", "1"))
        pythonpath = _flag("--pythonpath")
        only_raw = _flag("--only")
        only = only_raw.split(",") if only_raw else None
        fast_model = _flag("--fast-model")
        slow_model = _flag("--slow-model")
        if not arm or not pythonpath:
            print(__doc__)
            sys.exit(2)
        if arm in ("tiered", "orchestrated"):
            # Routing uses --slow-model / --fast-model; --model only keys results.
            if not model:
                model = slow_model or DEFAULT_SLOW_MODEL
            slow_model = slow_model or DEFAULT_SLOW_MODEL
            fast_model = fast_model or DEFAULT_FAST_MODEL
        elif not model:
            print(__doc__)
            sys.exit(2)
        run(arm, model, reps, pythonpath, only,
            fast_model=fast_model, slow_model=slow_model)
    elif cmd == "report":
        models = _flag("--models")
        if not models:
            print(__doc__)
            sys.exit(2)
        report(models.split(","))
    else:
        print(__doc__)
        sys.exit(2)

#!/usr/bin/env python3
"""Orchestrator-executor: classify a task, run a worker, verify, escalate.

Used as a library (`orchestrate`) and as a CLI.

  python3 task-orchestrator.py --query TEXT --pythonpath DIR --work DIR [--timeout N]
  python3 task-orchestrator.py --self-test
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    """Resolve ~/.hermes even when HERMES_HOME is a profile dir.

    hermes-scripts lives under ~/.hermes/, not ~/.hermes/profiles/<name>/.
    If HERMES_HOME ends with /profiles/<name>, strip that suffix. Otherwise
    walk up a few parents looking for hermes-scripts/.
    """
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

import argparse
import contextlib
import importlib.util
import json
import multiprocessing
import runpy
import sys
import time
from collections.abc import Callable

# Fallback if classifier import fails. Calibrated 2026-11-24 (toolperf + E2).
_FALLBACK_TIER_MODELS = {
    "fast": {"provider": "deepseek", "model": "deepseek-flash"},
    "math": {"provider": "xai", "model": "grok-4.6"},
    "longctx": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "tooluse": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "reason": {"provider": "openai", "model": "gpt-5.5"},
    "elite": {"provider": "anthropic", "model": "claude-sonnet-5-5"},
}


def _load_default_tier_models() -> dict:
    """Prefer DEFAULT_TIER_MODELS from model-tier-classifier.py."""
    try:
        path = _hermes_home() / "hermes-scripts" / "model-tier-classifier.py"
        spec = importlib.util.spec_from_file_location("_mtc_models", str(path))
        if spec is None or spec.loader is None:
            raise ImportError(str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        models = getattr(mod, "DEFAULT_TIER_MODELS", None)
        if isinstance(models, dict) and "elite" in models and "fast" in models:
            return {k: dict(v) if isinstance(v, dict) else v for k, v in models.items()}
    except Exception:
        pass
    return {k: dict(v) for k, v in _FALLBACK_TIER_MODELS.items()}


DEFAULT_TIER_MODELS = _load_default_tier_models()
ORCHESTRATE_CONFIDENCE_FLOOR = 0.7

ESCALATABLE_TIERS = frozenset({"fast", "math", "longctx", "tooluse"})
KNOWN_TIERS = frozenset(DEFAULT_TIER_MODELS.keys())

_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
}

_FAIL_PHRASES = (
    "i cannot",
    "i'm unable",
    "i don't have access",
    "as an ai language model",
    # NOTE: "error:" / "traceback" / "exception:" are intentionally excluded:
    # agents often narrate past errors they resolved, triggering false positives.
)


def _api_key_env_var(provider: str) -> str:
    p = (provider or "").strip().lower()
    return _API_KEY_ENV.get(p, f"{p.upper()}_API_KEY" if p else "API_KEY")


def _parse_model_spec(spec: str, default_provider: str = "anthropic") -> dict:
    raw = (spec or "").strip()
    if not raw:
        return {"provider": default_provider, "model": ""}
    if "/" in raw:
        prov, _, model = raw.partition("/")
        return {"provider": prov.strip() or default_provider, "model": model.strip()}
    return {"provider": default_provider, "model": raw}


# Classify + verify are stdlib. Logged, not used to classify.
_ORCH_DEFAULT = {"provider": "openai", "model": "gpt-5.5"}


def _parse_orch_model(spec) -> dict:
    if isinstance(spec, dict):
        prov = str(spec.get("provider") or "openai").strip() or "openai"
        model = str(spec.get("model") or "gpt-5.5").strip() or "gpt-5.5"
        return {"provider": prov, "model": model}
    if isinstance(spec, str) and spec.strip():
        return _parse_model_spec(spec, default_provider="openai")
    return dict(_ORCH_DEFAULT)


# Orchestrator model is tier-dependent:
# - reason tasks: gpt-5.5 orchestrates (can handle ambiguous decomposition and
#   verification judgment; flash can't reliably verify a reasoning task output)
# - elite tasks: sonnet-5 orchestrates elite workers (capability match;
#   flash verifying a security audit is a mismatch)
# - low-confidence fallback (confidence < 0.7): gpt-5.5 (safe default)
# - no orchestrator for fast/math/longctx/tooluse (should_orchestrate=False)
# Note: elite WORKER = sonnet-5-5 (ceiling hedge); elite ORCHESTRATOR = sonnet-5
# (same measured accuracy as 5-5 on elite battery, lower cost per orchestration call)
# Switch elite orchestrator to sonnet-5-5 if sonnet-5 fails verification on future harder tasks.
ORCHESTRATOR_TIER_MAP: dict[str, dict[str, str]] = {
    "reason":  {"provider": "openai",    "model": "gpt-5.5"},
    "elite":   {"provider": "anthropic", "model": "claude-sonnet-5"},
    "default": {"provider": "openai",    "model": "gpt-5.5"},  # low-confidence fallback
}


def get_orchestrator_model(tier: str, confidence: float) -> dict[str, str]:
    """Return the orchestrator model for a given worker tier and classifier confidence."""
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < ORCHESTRATE_CONFIDENCE_FLOOR:
        return dict(ORCHESTRATOR_TIER_MAP["default"])
    t = (tier or "").strip().lower()
    return dict(ORCHESTRATOR_TIER_MAP.get(t, ORCHESTRATOR_TIER_MAP["default"]))


def _orch_model_str(spec=None) -> str:
    d = _parse_orch_model(spec if spec is not None else ORCHESTRATOR_TIER_MAP["default"])
    return f"{d['provider']}/{d['model']}"


def _tier_entry(tier_models: dict | None, tier: str) -> dict:
    models = tier_models or DEFAULT_TIER_MODELS
    entry = models.get(tier)
    if entry is None:
        entry = models.get("reason") or DEFAULT_TIER_MODELS["reason"]
    if isinstance(entry, str):
        return _parse_model_spec(entry)
    if isinstance(entry, dict):
        prov = str(entry.get("provider") or "").strip()
        model = str(entry.get("model") or "").strip()
        if "/" in model and not prov:
            return _parse_model_spec(model)
        if not prov:
            prov = "anthropic"
        return {"provider": prov, "model": model}
    return dict(DEFAULT_TIER_MODELS["reason"])


def _apply_overrides(
    tier_models: dict | None,
    fast_model_override: str | None,
    slow_model_override: str | None,
) -> dict:
    out = {}
    src = tier_models or DEFAULT_TIER_MODELS
    for k, v in src.items():
        out[k] = dict(v) if isinstance(v, dict) else v
    for k, v in DEFAULT_TIER_MODELS.items():
        out.setdefault(k, dict(v))
    if fast_model_override:
        out["fast"] = _parse_model_spec(fast_model_override)
    if slow_model_override:
        out["reason"] = _parse_model_spec(slow_model_override)
    return out


def _strip_profile_home(hermes_base) -> Path:
    """HERMES_HOME may be a profile dir; hermes-scripts lives under ~/.hermes/.

    If HERMES_HOME ends with /profiles/<name>, strip that suffix. Otherwise
    walk up looking for hermes-scripts/.
    """
    p = Path(hermes_base) if hermes_base else _hermes_home()
    if p.name != ".hermes" and p.parent.name == "profiles":
        p = p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


def _load_classifier(hermes_base: Path):
    path = _strip_profile_home(hermes_base) / "hermes-scripts" / "model-tier-classifier.py"
    spec = importlib.util.spec_from_file_location("model_tier_classifier", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load classifier: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def should_orchestrate(tier: str, confidence: float) -> bool:
    """True when verify+escalate is worth the extra pass.

    Orchestrate if tier is reason/elite OR classifier confidence < 0.7.
    Skip for high-confidence fast/math/longctx/tooluse (single mechanical op).
    """
    t = (tier or "").strip().lower()
    if t in {"reason", "elite"}:
        return True
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        return True
    return conf < ORCHESTRATE_CONFIDENCE_FLOOR


def _safe_confidence(value, default: float = 0.6) -> float:
    try:
        c = float(value)
    except (TypeError, ValueError):
        c = default
    if c < 0.0:
        return 0.0
    if c > 1.0:
        return 1.0
    return c


def _classify_task(query: str, hermes_base: Path, tier_models: dict, extra: dict | None = None) -> dict:
    """Return {tier, provider, model, reason, confidence, orchestrator_turns}."""
    reason_entry = _tier_entry(tier_models, "reason")
    fallback = {
        "tier": "reason",
        "provider": reason_entry["provider"],
        "model": reason_entry["model"],
        "reason": "classifier_error",
        "confidence": 0.6,
        "orchestrator_turns": 0,
    }
    payload = {
        "query": query or "",
        "skill_tags": [],
        "skill_name": "",
        "prev_tool_calls": 0,
        "prev_exit_code": 0,
        "context_tokens": 0,
        "turn_index": 0,
    }
    if isinstance(extra, dict):
        payload.update(extra)
    try:
        mod = _load_classifier(hermes_base)
    except Exception as e:
        fallback["reason"] = f"classifier_error:{type(e).__name__}"
        return fallback

    try:
        if hasattr(mod, "classify_with_model") and callable(mod.classify_with_model):
            d = mod.classify_with_model(payload, tier_models)
            if not isinstance(d, dict):
                raise ValueError("bad classify_with_model output")
            tier = str(d.get("tier") or "reason")
            if tier == "slow":
                tier = "reason"
            if tier not in KNOWN_TIERS:
                tier = "reason"
            entry = _tier_entry(tier_models, tier)
            provider = str(d.get("provider") or entry["provider"])
            model = str(d.get("model") or entry["model"])
            turns = d.get("orchestrator_turns", 0)
            try:
                turns_i = int(turns or 0)
            except (TypeError, ValueError):
                turns_i = 0
            return {
                "tier": tier,
                "provider": provider,
                "model": model,
                "reason": str(d.get("reason") or "default_safe"),
                "confidence": _safe_confidence(d.get("confidence"), 0.6),
                "orchestrator_turns": max(0, turns_i),
            }
        d = mod.classify(payload)
        if not isinstance(d, dict):
            raise ValueError("bad classify output")
        raw = str(d.get("tier") or "reason")
        if raw == "slow":
            tier = "reason"
        elif raw in KNOWN_TIERS:
            tier = raw
        else:
            tier = "reason"
        entry = _tier_entry(tier_models, tier)
        return {
            "tier": tier,
            "provider": entry["provider"],
            "model": entry["model"],
            "reason": str(d.get("reason") or "default_safe"),
            "confidence": _safe_confidence(d.get("confidence"), 0.6),
            "orchestrator_turns": 0,
        }
    except Exception as e:
        fallback["reason"] = f"classifier_error:{type(e).__name__}"
        return fallback


def _verify_result(out: str, query: str, rc: int) -> str:
    """Return 'pass', 'fail', or 'skip'."""
    del query  # rules-only verifier does not inspect the query
    if rc != 0:
        return "fail"
    if not out or not str(out).strip():
        return "fail"
    low = str(out).lower()
    if any(phrase in low for phrase in _FAIL_PHRASES):
        return "fail"
    return "pass"


def _atof_path_from_relay(relay_toml: str) -> Path | None:
    raw = (relay_toml or "").strip()
    if not raw:
        return None
    path = Path(raw)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    out_dir = ""
    filename = ""
    try:
        import tomllib
        data = tomllib.loads(text)
        comps = data.get("components") or []
        if isinstance(comps, dict):
            comps = [comps]
        for comp in comps:
            if not isinstance(comp, dict):
                continue
            cfg = comp.get("config") or {}
            atof = cfg.get("atof") or {}
            sinks = atof.get("sinks") or []
            if isinstance(sinks, dict):
                sinks = [sinks]
            for sink in sinks:
                if not isinstance(sink, dict):
                    continue
                out_dir = str(sink.get("output_directory") or "")
                filename = str(sink.get("filename") or "")
                if out_dir or filename:
                    break
            if out_dir or filename:
                break
    except Exception:
        out_dir = ""
        filename = ""
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("output_directory"):
                _, _, rest = s.partition("=")
                out_dir = rest.strip().strip('"').strip("'")
            elif s.startswith("filename"):
                _, _, rest = s.partition("=")
                filename = rest.strip().strip('"').strip("'")
    try:
        if filename and out_dir:
            return Path(out_dir) / filename
        if filename:
            return path.parent / filename
        if out_dir:
            return Path(out_dir)
    except Exception:
        return None
    return None


def _emit_atof(relay_toml: str, extra: dict) -> None:
    """Append one JSONL ATOF record. Fail-open."""
    try:
        atof_path = _atof_path_from_relay(relay_toml)
        if atof_path is None:
            return
        rec = {"ts": time.time(), "source": "task-orchestrator"}
        if isinstance(extra, dict):
            rec.update(extra)
        atof_path.parent.mkdir(parents=True, exist_ok=True)
        with open(atof_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _count_atof_lines(relay_toml: str) -> int:
    try:
        atof_path = _atof_path_from_relay(relay_toml)
        if atof_path is None:
            return 0
        with open(atof_path, encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except Exception:
        return 0


def _inject_pythonpath(pythonpath: str) -> None:
    for p in reversed((pythonpath or "").split(os.pathsep)):
        if p and p not in sys.path:
            sys.path.insert(0, p)
    existing = os.environ.get("PYTHONPATH", "")
    if pythonpath:
        os.environ["PYTHONPATH"] = (
            pythonpath if not existing else pythonpath + os.pathsep + existing
        )


def _normalize_api_key_env_name(key: str) -> str:
    """Accept provider names or already-formed ENV vars (ANTHROPIC_API_KEY)."""
    k = str(key or "").strip()
    if not k:
        return ""
    if k.endswith("_API_KEY") or (k.isupper() and "_" in k):
        return k
    return _api_key_env_var(k)


def _set_api_key_env(provider: str, api_key: str | None, api_keys: dict | None) -> str | None:
    chosen = api_key
    if isinstance(api_keys, dict):
        for p, k in api_keys.items():
            if not k:
                continue
            var = _normalize_api_key_env_name(str(p))
            if var and not os.environ.get(var):
                os.environ[var] = str(k)
        if not chosen:
            chosen = (
                api_keys.get(provider)
                or api_keys.get((provider or "").lower())
                or api_keys.get(_api_key_env_var(provider))
            )
    if chosen:
        var = _api_key_env_var(provider)
        if var and not os.environ.get(var):
            os.environ[var] = str(chosen)
    return str(chosen) if chosen else None


@contextlib.contextmanager
def _isolated_env(extra_env=None, extra_path=None, workdir=None):
    """Restore os.environ, sys.path, and cwd after in-process worker mutations."""
    old_env = os.environ.copy()
    old_path = sys.path.copy()
    old_cwd = os.getcwd()
    try:
        if extra_env:
            os.environ.update(
                {str(k): str(v) for k, v in extra_env.items() if v is not None}
            )
        if extra_path:
            sys.path[:0] = [p for p in extra_path if p]
        if workdir:
            os.chdir(str(workdir))
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        sys.path[:] = old_path
        try:
            os.chdir(old_cwd)
        except Exception:
            pass


def _run_worker(
    pythonpath,
    hermes_home,
    relay_toml,
    work_dir,
    query,
    provider,
    model,
    session_id,
    api_key,
    result_q,
    timeout=300,
):
    """Spawn-child body. Puts {out, rc, atof_lines} on result_q.

    timeout is enforced by the parent join; accepted here for signature stability.
    Env/cwd/sys.path mutations are restored on exit so in-process callers are safe.
    """
    del timeout
    extra_keys = None
    raw_key = api_key
    if isinstance(api_key, dict):
        extra_keys = api_key
        raw_key = extra_keys.get(provider) or extra_keys.get((provider or "").lower())

    extra_env = {}
    if hermes_home:
        extra_env["HERMES_HOME"] = str(hermes_home)
    if relay_toml:
        extra_env["HERMES_NEMO_RELAY_PLUGINS_TOML"] = str(relay_toml)
        extra_env["HERMES_ACCEPT_HOOKS"] = "1"
    extra_path = [p for p in (pythonpath or "").split(os.pathsep) if p]
    result_path = os.environ.get("TASK_ORCH_RESULT_PATH", "").strip()

    out, rc, atof_lines = "", 1, 0
    with _isolated_env(extra_env, extra_path, work_dir):
        if pythonpath:
            existing = os.environ.get("PYTHONPATH", "")
            os.environ["PYTHONPATH"] = (
                pythonpath if not existing else pythonpath + os.pathsep + existing
            )
        resolved_key = None
        try:
            resolved_key = _set_api_key_env(provider or "", raw_key, extra_keys)
        except Exception:
            resolved_key = None

        lease = None
        agent = None
        try:
            if relay_toml:
                try:
                    from agent import relay_runtime
                    relay_runtime.get_runtime()
                    lease = relay_runtime.SESSION_COORDINATOR.acquire_conversation(
                        profile_key=relay_runtime.current_profile_key(),
                        session_id=session_id or "task-orch",
                        platform="task_orchestrator",
                    )
                except Exception:
                    lease = None

            from run_agent import AIAgent
            env_var = _api_key_env_var(provider or "")
            ctor_key = resolved_key or os.environ.get(env_var) or None
            agent = AIAgent(
                api_key=ctor_key,
                base_url=None,
                provider=provider or None,
                model=model or None,
                session_id=session_id or "task-orch",
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
                skip_background_review=True,
                max_iterations=30,
                platform="task_orchestrator",
                cwd=str(work_dir) if work_dir else None,
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
                atof_lines = _count_atof_lines(relay_toml or "")
            except Exception:
                atof_lines = 0

    try:
        result_q.put({"out": out, "rc": rc, "atof_lines": atof_lines})
    except Exception:
        pass
    if result_path:
        try:
            dest = Path(result_path)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            tmp.write_text(
                json.dumps({"out": out, "rc": rc, "atof_lines": atof_lines}),
                encoding="utf-8",
            )
            os.replace(tmp, dest)
        except Exception:
            pass


def _invoke_worker(
    pythonpath: str,
    hermes_home: str,
    relay_toml: str,
    work_dir: str,
    query: str,
    provider: str,
    model: str,
    session_id: str,
    api_key,
    timeout: int,
) -> dict:
    """Run AIAgent in-process (we are already in an isolated spawn'd child from ab_eval).
    Nested spawn is avoided to prevent triple-spawn queue failures."""
    import queue as _queue_mod
    t0 = time.time()
    result_q = _queue_mod.SimpleQueue()
    try:
        _run_worker(
            pythonpath or "",
            hermes_home or "",
            relay_toml or "",
            work_dir or "",
            query or "",
            provider or "",
            model or "",
            session_id or "task-orch",
            api_key,
            result_q,
            int(timeout) if timeout else 300,
        )
        try:
            got = result_q.get_nowait()
        except Exception:
            got = None
    except Exception as e:
        got = {"out": f"{type(e).__name__}: {e}", "rc": 1, "atof_lines": 0}
    wall_s = time.time() - t0

    if not isinstance(got, dict):
        got = {"out": "worker did not return result", "rc": 1, "atof_lines": 0}

    counted = _count_atof_lines(relay_toml or "")
    if counted:
        got["atof_lines"] = counted
    got["wall_s"] = wall_s
    got["timed_out"] = False
    return got


def _apply_accept_fn(verification: str, out: str, work_dir: str, accept_fn) -> str:
    """If accept_fn is provided and returns False, force verification=fail."""
    if accept_fn is None:
        return verification
    try:
        wp = Path(work_dir) if work_dir else Path(".")
        ok = bool(accept_fn(str(out or ""), wp))
    except Exception:
        ok = False
    if not ok:
        return "fail"
    return verification


def orchestrate(
    query: str,
    pythonpath: str,
    hermes_home: str,
    relay_toml: str,
    work_dir: str,
    session_id: str,
    api_keys: dict,
    tier_models: dict | None = None,
    fast_model_override: str | None = None,
    slow_model_override: str | None = None,
    timeout: int = 300,
    classifier_extra: dict | None = None,
    accept_fn: Callable[[str, Path], bool] | None = None,
    orchestrator_model=None,
    orchestrator_model_override: dict | None = None,
) -> dict:
    models = _apply_overrides(tier_models, fast_model_override, slow_model_override)
    hermes_base = _strip_profile_home(hermes_home or _hermes_base)
    try:
        hh = Path(hermes_home) if hermes_home else _hermes_base
        hermes_base = _strip_profile_home(hh)
        if not (hermes_base / "hermes-scripts" / "model-tier-classifier.py").exists():
            hermes_base = _hermes_base
    except Exception:
        hermes_base = _hermes_base

    classification = _classify_task(query or "", hermes_base, models, extra=classifier_extra)
    tier = classification["tier"]
    provider = classification["provider"]
    model = classification["model"]
    keys = api_keys if isinstance(api_keys, dict) else {}
    worker_model = f"{provider}/{model}" if provider else str(model)
    conf = _safe_confidence(classification.get("confidence"), 0.6)
    do_orch = should_orchestrate(tier, conf)
    override = (
        orchestrator_model_override
        if orchestrator_model_override is not None
        else orchestrator_model
    )
    if override is not None:
        orch_spec = override
    else:
        orch_spec = get_orchestrator_model(tier, conf)
    orch_model = _orch_model_str(orch_spec)

    result = _invoke_worker(
        pythonpath or "",
        hermes_home or "",
        relay_toml or "",
        work_dir or "",
        query or "",
        provider,
        model,
        session_id or "task-orch",
        keys,
        timeout,
    )
    worker_wall = float(result.get("wall_s") or 0.0)
    escalated = False

    if not do_orch:
        verification = "skip"
        verification = _apply_accept_fn(
            verification, str(result.get("out") or ""), work_dir or "", accept_fn
        )
        if verification == "fail" and tier in ESCALATABLE_TIERS:
            reason_entry = _tier_entry(models, "reason")
            result2 = _invoke_worker(
                pythonpath or "",
                hermes_home or "",
                relay_toml or "",
                work_dir or "",
                query or "",
                reason_entry["provider"],
                reason_entry["model"],
                session_id or "task-orch",
                keys,
                timeout,
            )
            worker_wall += float(result2.get("wall_s") or 0.0)
            if not result2.get("timed_out"):
                verification2 = _verify_result(
                    result2.get("out", ""), query or "", int(result2.get("rc", 1))
                )
                verification2 = _apply_accept_fn(
                    verification2, str(result2.get("out") or ""), work_dir or "", accept_fn
                )
                if verification2 == "pass" or int(result.get("rc", 1)) != 0:
                    result = result2
                    tier = "reason"
                    provider = reason_entry["provider"]
                    model = reason_entry["model"]
                    worker_model = f"{provider}/{model}" if provider else str(model)
                    escalated = True
                    verification = verification2
        rc = int(result.get("rc", 1) or 1)
        if verification == "fail":
            rc = 1
        elif verification == "pass":
            rc = 0
    else:
        verification = _verify_result(result.get("out", ""), query or "", int(result.get("rc", 1)))
        verification = _apply_accept_fn(
            verification, str(result.get("out") or ""), work_dir or "", accept_fn
        )
        if verification == "fail" and tier in ESCALATABLE_TIERS:
            reason_entry = _tier_entry(models, "reason")
            result2 = _invoke_worker(
                pythonpath or "",
                hermes_home or "",
                relay_toml or "",
                work_dir or "",
                query or "",
                reason_entry["provider"],
                reason_entry["model"],
                session_id or "task-orch",
                keys,
                timeout,
            )
            worker_wall += float(result2.get("wall_s") or 0.0)
            if result2.get("timed_out"):
                pass  # keep original failed result, escalated=False
            else:
                verification2 = _verify_result(
                    result2.get("out", ""), query or "", int(result2.get("rc", 1))
                )
                verification2 = _apply_accept_fn(
                    verification2, str(result2.get("out") or ""), work_dir or "", accept_fn
                )
                if verification2 == "pass" or int(result.get("rc", 1)) != 0:
                    result = result2
                    tier = "reason"
                    provider = reason_entry["provider"]
                    model = reason_entry["model"]
                    worker_model = f"{provider}/{model}" if provider else str(model)
                    escalated = True
                    verification = verification2
        rc = int(result.get("rc", 1) or 1)
        if verification == "fail":
            rc = 1
        elif verification == "pass":
            rc = 0

    atof_lines = int(result.get("atof_lines") or 0)
    if not atof_lines:
        atof_lines = _count_atof_lines(relay_toml or "")

    _emit_atof(relay_toml or "", {
        "atof_event": "task_orchestrator",
        "orchestrated": bool(do_orch),
        "orchestrator_model": orch_model,
        "worker_model": worker_model,
        "tier": tier,
        "reason": str(classification.get("reason") or ""),
        "confidence": conf,
        "model": worker_model,
        "rc": rc,
        "verification": verification,
        "escalated": bool(escalated),
        "worker_wall_s": float(worker_wall),
    })

    return {
        "out": str(result.get("out", "") or ""),
        "rc": rc,
        "tier": tier,
        "model": worker_model,
        "reason": str(classification.get("reason") or ""),
        "confidence": conf,
        "escalated": bool(escalated),
        "orchestrator_turns": int(classification.get("orchestrator_turns") or 0),
        "worker_wall_s": float(worker_wall),
        "atof_lines": int(atof_lines),
        "verification": verification,
        "orchestrated": bool(do_orch),
        "orchestrator_model": orch_model,
        "worker_model": worker_model,
    }


def _write_default_relay(work_dir: str) -> str:
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    atof = work / "task-orch.atof.jsonl"
    relay = work / "relay-plugins.toml"
    body = (
        "version = 1\n\n"
        "[[components]]\n"
        'kind = "observability"\n'
        "enabled = true\n\n"
        "[components.config]\n"
        "version = 4\n\n"
        "[components.config.atof]\n"
        "enabled = true\n\n"
        "[[components.config.atof.sinks]]\n"
        'type = "file"\n'
        f"output_directory = {json.dumps(str(atof.parent))}\n"
        f"filename = {json.dumps(atof.name)}\n"
        'mode = "overwrite"\n'
    )
    tmp = relay.with_suffix(".toml.tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, relay)
    return str(relay)


def _check(cond: bool, msg: str, failures: list) -> None:
    if not cond:
        failures.append(msg)


def self_test() -> int:
    failures: list[str] = []

    # DEFAULT_TIER_MODELS has all 6 keys
    keys = set(DEFAULT_TIER_MODELS.keys())
    _check(keys == {"fast", "math", "longctx", "tooluse", "reason", "elite"},
           f"DEFAULT_TIER_MODELS keys {sorted(keys)}", failures)
    _check("elite" in KNOWN_TIERS, "KNOWN_TIERS includes elite", failures)
    _check(
        {"reason", "elite", "default"} <= set(ORCHESTRATOR_TIER_MAP.keys()),
        "ORCHESTRATOR_TIER_MAP has reason+elite+default", failures)
    _check(
        get_orchestrator_model("reason", 0.9) == ORCHESTRATOR_TIER_MAP["reason"],
        "orch model reason high-conf", failures)
    _check(
        get_orchestrator_model("elite", 0.9) == ORCHESTRATOR_TIER_MAP["elite"],
        "orch model elite high-conf", failures)
    _check(
        get_orchestrator_model("elite", 0.9).get("model") == "claude-sonnet-5",
        "elite orchestrator is sonnet-5 not 5-5", failures)
    _check(
        (DEFAULT_TIER_MODELS.get("elite") or {}).get("model") == "claude-sonnet-5-5",
        "elite worker stays sonnet-5-5", failures)
    _check(
        get_orchestrator_model("fast", 0.4) == ORCHESTRATOR_TIER_MAP["default"],
        "orch model low-conf fast -> default", failures)
    _check(
        get_orchestrator_model("fast", 0.95) == ORCHESTRATOR_TIER_MAP["default"],
        "orch model high-conf fast -> default (should_orchestrate handles skip)", failures)
    _check(should_orchestrate("fast", 0.80) is False, "high-conf fast skips orch", failures)
    _check(should_orchestrate("math", 0.85) is False, "high-conf math skips orch", failures)
    _check(should_orchestrate("longctx", 0.90) is False, "high-conf longctx skips orch", failures)
    _check(should_orchestrate("tooluse", 0.85) is False, "high-conf tooluse skips orch", failures)
    _check(should_orchestrate("reason", 0.95) is True, "reason always orch", failures)
    _check(should_orchestrate("elite", 0.90) is True, "elite always orch", failures)
    _check(should_orchestrate("fast", 0.60) is True, "low-conf fast orch", failures)
    _check(should_orchestrate("math", 0.69) is True, "conf < 0.7 orch", failures)
    _check(should_orchestrate("fast", 0.70) is False, "conf == 0.7 skips", failures)
    for k, v in DEFAULT_TIER_MODELS.items():
        _check(isinstance(v, dict) and v.get("provider") and v.get("model"),
               f"tier {k} has provider/model", failures)

    # _verify_result good/bad
    _check(_verify_result("VALUE=42", "report the value", 0) == "pass",
           "good output -> pass", failures)
    _check(_verify_result("", "q", 0) == "fail", "empty output -> fail", failures)
    _check(_verify_result("   ", "q", 0) == "fail", "whitespace output -> fail", failures)
    _check(_verify_result("ok", "q", 1) == "fail", "rc!=0 -> fail", failures)
    _check(_verify_result("I cannot do that", "q", 0) == "fail",
           "i cannot -> fail", failures)
    _check(_verify_result("I'm unable to help", "q", 0) == "fail",
           "unable -> fail", failures)
    # error/traceback/exception phrases removed from fail list (agents narrate past errors)
    _check(_verify_result("Traceback (most recent call last) but VALUE=42", "q", 0) == "pass",
           "narrated traceback -> pass", failures)
    _check(_verify_result("as an ai language model i cannot help", "q", 0) == "fail",
           "as an ai language model -> fail", failures)
    _check(_verify_result("", "", 0) == "fail", "empty query+out -> fail", failures)

    # classifier load
    try:
        mod = _load_classifier(_hermes_base)
        _check(callable(getattr(mod, "classify", None)),
               "classifier.classify callable", failures)
    except Exception as e:
        failures.append(f"load_classifier: {type(e).__name__}: {e}")

    # classify mapping: short simple -> fast; empty -> reason (slow mapped)
    d = _classify_task("restart the vpn please", _hermes_base, DEFAULT_TIER_MODELS)
    _check(d["tier"] in KNOWN_TIERS, "classify returns known tier", failures)
    _check(d["provider"] and d["model"], "classify returns provider/model", failures)
    _check(0.0 <= float(d["confidence"]) <= 1.0, "confidence in [0,1]", failures)
    _check(d["orchestrator_turns"] == 0, "rules-only orchestrator_turns=0", failures)

    d_empty = _classify_task("", _hermes_base, DEFAULT_TIER_MODELS)
    _check(d_empty["tier"] == "reason", "empty query -> reason (safe default)", failures)

    # missing classifier -> reason fallback
    missing_base = Path("/tmp/task-orch-no-such-hermes-base")
    d_miss = _classify_task("hello", missing_base, DEFAULT_TIER_MODELS)
    _check(d_miss["tier"] == "reason", "missing classifier -> reason", failures)
    _check("classifier_error" in d_miss["reason"], "missing classifier reason tag", failures)

    # overrides
    ov = _apply_overrides(None, "openai/gpt-4o-mini", "anthropic/claude-sonnet-4-6")
    _check(ov["fast"]["provider"] == "openai" and ov["fast"]["model"] == "gpt-4o-mini",
           "fast override", failures)
    _check(ov["reason"]["model"] == "claude-sonnet-4-6", "slow override -> reason", failures)

    # ATOF path + missing file
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="task-orch-st-"))
    try:
        relay = _write_default_relay(str(td))
        atof = _atof_path_from_relay(relay)
        _check(atof is not None and atof.name == "task-orch.atof.jsonl",
               "atof path from relay toml", failures)
        _check(_count_atof_lines(relay) == 0, "missing atof file -> 0", failures)
        if atof is not None:
            atof.write_text("a\nb\n", encoding="utf-8")
            _check(_count_atof_lines(relay) == 2, "atof line count", failures)
        _check(_count_atof_lines("/no/such/relay.toml") == 0, "bad relay -> 0", failures)
        _check(_count_atof_lines("") == 0, "empty relay -> 0", failures)
        malformed = td / "bad.toml"
        malformed.write_text("{not toml", encoding="utf-8")
        _check(_count_atof_lines(str(malformed)) == 0, "malformed toml -> 0", failures)
    finally:
        try:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
        except Exception:
            pass

    # long input verify < 5s
    long_out = ("ok token " * 5000)[:12000]
    t0 = time.perf_counter()
    v = _verify_result(long_out, "x" * 10000, 0)
    elapsed = time.perf_counter() - t0
    _check(elapsed < 5.0, f"long verify <5s (was {elapsed:.3f}s)", failures)
    _check(v == "pass", "long clean output -> pass", failures)

    # JSON schema of orchestrate return keys (unit, no worker)
    expected = {
        "out", "rc", "tier", "model", "reason", "confidence",
        "escalated", "orchestrator_turns", "worker_wall_s",
        "atof_lines", "verification",
        "orchestrated", "orchestrator_model", "worker_model",
    }
    sample = {
        "out": "ok", "rc": 0, "tier": "fast", "model": "deepseek/deepseek-flash",
        "reason": "short_simple_query", "confidence": 0.7, "escalated": False,
        "orchestrator_turns": 0, "worker_wall_s": 0.0, "atof_lines": 0,
        "verification": "skip",
        "orchestrated": False,
        "orchestrator_model": "deepseek/deepseek-flash",
        "worker_model": "deepseek/deepseek-flash",
    }
    dumped = json.loads(json.dumps(sample))
    _check(set(dumped.keys()) == expected, "return schema keys", failures)

    # ESCALATABLE_TIERS
    _check(ESCALATABLE_TIERS == frozenset({"fast", "math", "longctx", "tooluse"}),
           "escalatable tiers", failures)
    _check("reason" not in ESCALATABLE_TIERS, "reason not escalatable", failures)

    # orchestrate is import-safe / callable
    _check(callable(orchestrate), "orchestrate callable", failures)

    # accept_fn forces fail on garbage that would otherwise pass rc/non-empty
    _check(
        _apply_accept_fn("pass", "confident garbage", ".", lambda o, _w: "VALUE=" in o) == "fail",
        "accept_fn rejects garbage", failures)
    _check(
        _apply_accept_fn("pass", "VALUE=1", ".", lambda o, _w: "VALUE=" in o) == "pass",
        "accept_fn keeps matching output", failures)
    _check(_apply_accept_fn("skip", "x", ".", None) == "skip", "no accept_fn keeps skip", failures)

    # isolated env restores caller os.environ
    marker = "TASK_ORCH_ISOLATED_TEST"
    os.environ.pop(marker, None)
    with _isolated_env({marker: "1"}, extra_path=["/tmp/orch-iso-path"], workdir=None):
        _check(os.environ.get(marker) == "1", "isolated env sets extra", failures)
    _check(os.environ.get(marker) is None, "isolated env restores caller", failures)

    # API key dict may be {ANTHROPIC_API_KEY: ...} not {anthropic: ...}
    _check(
        _normalize_api_key_env_name("ANTHROPIC_API_KEY") == "ANTHROPIC_API_KEY",
        "env-shaped key used as-is", failures)
    _check(
        _normalize_api_key_env_name("anthropic") == "ANTHROPIC_API_KEY",
        "provider name maps to env var", failures)
    _check(
        _normalize_api_key_env_name("anthropic") != "ANTHROPIC_API_KEY_API_KEY",
        "no double _API_KEY suffix", failures)

    if failures:
        print("SELF-TEST FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a task, run a worker, verify, escalate on failure"
    )
    parser.add_argument("--query", default=None)
    parser.add_argument("--pythonpath", default=None)
    parser.add_argument("--work", dest="work_dir", default=None)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--hermes-home", default=None)
    parser.add_argument("--relay", default=None)
    parser.add_argument("--session-id", default="task-orch")
    parser.add_argument("--fast-model", default=None)
    parser.add_argument("--slow-model", default=None)
    args, _unknown = parser.parse_known_args(argv)
    if args.self_test:
        return self_test()
    if not args.query or not args.pythonpath or not args.work_dir:
        parser.print_help()
        return 2
    hermes_home = args.hermes_home or str(_hermes_base)
    relay = args.relay
    if not relay:
        try:
            relay = _write_default_relay(args.work_dir)
        except Exception:
            relay = ""
    api_keys = {}
    for prov, var in _API_KEY_ENV.items():
        val = os.environ.get(var)
        if val:
            api_keys[prov] = val
    result = orchestrate(
        query=args.query,
        pythonpath=args.pythonpath,
        hermes_home=hermes_home,
        relay_toml=relay or "",
        work_dir=args.work_dir,
        session_id=args.session_id,
        api_keys=api_keys,
        fast_model_override=args.fast_model,
        slow_model_override=args.slow_model,
        timeout=int(args.timeout or 300),
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0 if int(result.get("rc", 1)) == 0 else 1


def _orch_worker_dispatch() -> bool:
    if not globals().get("_ORCH_WORKER"):
        return False
    payload = globals().get("_ORCH_PAYLOAD") or {}
    q = globals().get("_ORCH_QUEUE")
    try:
        _run_worker(
            payload.get("pythonpath") or "",
            payload.get("hermes_home") or "",
            payload.get("relay_toml") or "",
            payload.get("work_dir") or "",
            payload.get("query") or "",
            payload.get("provider") or "",
            payload.get("model") or "",
            payload.get("session_id") or "task-orch",
            payload.get("api_key"),
            q,
            payload.get("timeout") or 300,
        )
    except Exception as e:
        try:
            if q is not None:
                q.put({"out": f"{type(e).__name__}: {e}", "rc": 1, "atof_lines": 0})
        except Exception:
            pass
    return True


if not _orch_worker_dispatch() and __name__ == "__main__":
    raise SystemExit(main())

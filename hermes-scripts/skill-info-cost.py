#!/usr/bin/env python3
"""Policy Complexity, Reaction Time, and Bounded Rationality in Reinforcement Learning.

Computes per-skill information cost KL(posterior || marginal prior) and skill
entropy to track bounded-rationality tradeoffs (inverse-temperature beta).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sqlite3
import sys
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home_from(env: str, home: Path | None = None) -> Path:
    """Resolve HERMES_HOME, stripping a trailing profiles/<name> suffix."""
    p = Path(env.strip()) if env and str(env).strip() else (home or Path.home()) / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _hermes_home() -> Path:
    return _hermes_home_from(os.environ.get("HERMES_HOME", ""))


_raw_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if not _hermes_profile and _raw_home.parent.name == "profiles":
    _hermes_profile = _raw_home.name
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile else _hermes_base
)

BETA = 0.1
EPS = 1e-12
MAX_TURNS = 100
UE_SENTINEL = "ue_blackbox"

LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
CACHE = _hermes_root / "cache"
CALIBRATION_LOG = CACHE / "calibration-log.jsonl"
OUT_PATH = CACHE / "skill-prior.json"
KL_LOG = CACHE / "skill-kl-log.jsonl"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def shannon_entropy(probs) -> float:
    h = 0.0
    for p in probs:
        if p > 0.0:
            h -= p * math.log(p)
    return float(h)


def kl_div(post: dict, prior: dict) -> float:
    """KL(posterior || prior) with epsilon smoothing over union support."""
    keys = set(post) | set(prior)
    if not keys:
        return 0.0
    qs = []
    ps = []
    for k in keys:
        qs.append(max(float(post.get(k, 0.0)), 0.0))
        ps.append(max(float(prior.get(k, 0.0)), 0.0))
    n = len(keys)
    sq = sum(qs)
    sp = sum(ps)
    if sq <= 0.0:
        qs = [1.0 / n] * n
    else:
        qs = [q / sq for q in qs]
    if sp <= 0.0:
        ps = [1.0 / n] * n
    else:
        ps = [p / sp for p in ps]
    qs = [q + EPS for q in qs]
    ps = [p + EPS for p in ps]
    sq = sum(qs)
    sp = sum(ps)
    qs = [q / sq for q in qs]
    ps = [p / sp for p in ps]
    kl = 0.0
    for q, p in zip(qs, ps):
        kl += q * math.log(q / p)
    kl = max(kl, 0.0)
    return float(kl)


def normalize_counts(counts: dict) -> dict:
    total = 0.0
    clean = {}
    for k, v in counts.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 0.0 and k:
            clean[str(k)] = fv
            total += fv
    if total <= 0.0:
        n = len(clean)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in clean}
    return {k: v / total for k, v in clean.items()}


def softmax_posterior(prior: dict, rewards: dict, beta: float) -> dict:
    keys = list(prior.keys())
    if not keys:
        return {}
    scores = []
    for k in keys:
        p0 = max(float(prior[k]), EPS)
        r = float(rewards.get(k, 0.0))
        scores.append(math.log(p0) + float(beta) * r)
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    z = sum(exps)
    if z <= 0.0:
        return {k: 1.0 / len(keys) for k in keys}
    return {k: e / z for k, e in zip(keys, exps)}


def _skill_from_calib_row(d: dict):
    """Map a calibration-log row to a skill name.

    scope==ue_blackbox is skipped entirely (never fall back to tool_name).
    Missing/empty scope falls back to tool_name.
    """
    if not isinstance(d, dict):
        return None
    scope = d.get("scope")
    if scope == UE_SENTINEL:
        return None
    if isinstance(scope, str) and scope.strip():
        return scope.strip()
    tool = d.get("tool_name")
    if isinstance(tool, str) and tool.strip():
        return tool.strip()
    return None


def load_calibration(path: Path):
    """Return (freq dict, last-MAX_TURNS session count dicts)."""
    freq = defaultdict(float)
    recent = deque(maxlen=MAX_TURNS)
    if not path.exists():
        return {}, []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                skill = _skill_from_calib_row(d)
                if not skill:
                    continue
                freq[skill] += 1.0
                sid = d.get("session_id")
                recent.append((str(sid or "unknown"), skill))
    except OSError:
        return {}, []
    by_sess = defaultdict(lambda: defaultdict(float))
    for sid, skill in recent:
        by_sess[sid][skill] += 1.0
    sessions = [(sid, dict(c)) for sid, c in by_sess.items()]
    return dict(freq), sessions


def load_delegation_freq(db_path: Path) -> dict:
    if not db_path.exists():
        return {}
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "delegation_audit" not in tabs:
            return {}
        cols = {r[1] for r in conn.execute("PRAGMA table_info(delegation_audit)")}
        if "tool_name" not in cols:
            return {}
        rows = conn.execute(
            "SELECT tool_name FROM delegation_audit "
            "WHERE tool_name IS NOT NULL AND tool_name != ''"
        ).fetchall()
        freq = defaultdict(float)
        for (name,) in rows:
            n = str(name).strip()
            if n:
                freq[n] += 1.0
        return dict(freq)
    except sqlite3.Error:
        return {}
    finally:
        if conn is not None:
            conn.close()


def load_anytime_sessions(db_path: Path, limit: int = MAX_TURNS):
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "anytime_eval_log" not in tabs:
            return []
        cols = {r[1] for r in conn.execute("PRAGMA table_info(anytime_eval_log)")}
        if "session_id" not in cols or "skill_id" not in cols:
            return []
        order = "id DESC" if "id" in cols else "rowid DESC"
        rows = conn.execute(
            "SELECT session_id, skill_id FROM anytime_eval_log ORDER BY " + order + " LIMIT ?",
            (int(limit),),
        ).fetchall()
        by_sess = defaultdict(lambda: defaultdict(float))
        for sid, skill in rows:
            s = str(skill or "").strip()
            if not s:
                continue
            by_sess[str(sid or "unknown")][s] += 1.0
        return [(sid, dict(c)) for sid, c in by_sess.items()]
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def uniform_prior(names) -> dict:
    names = sorted({str(n) for n in names if n})
    if not names:
        return {}
    p = 1.0 / len(names)
    return {n: p for n in names}


def compute(db_path: Path, calib_path: Path, beta: float = BETA) -> dict:
    del_freq = load_delegation_freq(db_path)
    calib_freq, calib_sessions = load_calibration(calib_path)

    if del_freq:
        merged = dict(del_freq)
        for k, v in calib_freq.items():
            merged[k] = merged.get(k, 0.0) + v
        prior = normalize_counts(merged)
    elif calib_freq:
        prior = normalize_counts(calib_freq)
    else:
        prior = {}

    sessions = load_anytime_sessions(db_path)
    if not sessions:
        sessions = calib_sessions

    if not prior:
        names = set()
        for _, c in sessions:
            names.update(c)
        prior = uniform_prior(names)

    entropy = shannon_entropy(prior.values()) if prior else 0.0
    per_session = []
    for sid, counts in sessions:
        post = normalize_counts(counts)
        if not post:
            continue
        use_prior = prior if prior else post
        per_session.append({"session_id": sid, "kl": kl_div(post, use_prior)})

    n_sess = len(per_session)
    mean_kl = (sum(x["kl"] for x in per_session) / n_sess) if n_sess else 0.0
    return {
        "ts": _now(),
        "marginal_prior": prior,
        "skill_entropy": float(entropy),
        "per_session_kl": per_session,
        "beta": float(beta),
        "info_cost_bound": float(mean_kl),
        "mean_kl": float(mean_kl),
        "n_sessions": int(n_sess),
    }


def cmd_run(out_path: Path, log_path: Path, db_path: Path, calib_path: Path) -> int:
    result = compute(db_path, calib_path)
    payload = {
        "ts": result["ts"],
        "marginal_prior": result["marginal_prior"],
        "skill_entropy": result["skill_entropy"],
        "per_session_kl": result["per_session_kl"],
        "beta": result["beta"],
        "info_cost_bound": result["info_cost_bound"],
    }
    _atomic_write_json(out_path, payload)
    _append_jsonl(
        log_path,
        {
            "ts": result["ts"],
            "skill_entropy": result["skill_entropy"],
            "mean_kl": result["mean_kl"],
            "n_sessions": result["n_sessions"],
        },
    )
    print(
        json.dumps(
            {
                "ok": True,
                "skill_entropy": result["skill_entropy"],
                "mean_kl": result["mean_kl"],
                "n_sessions": result["n_sessions"],
                "n_skills": len(result["marginal_prior"]),
                "out": str(out_path),
                "log": str(log_path),
            }
        )
    )
    return 0


def cmd_self_test() -> int:
    failures = []

    a = _hermes_home_from("/var/home/rainbow/.hermes/profiles/fork")
    b = _hermes_home_from("/var/home/rainbow/.hermes")
    if str(a) != "/var/home/rainbow/.hermes":
        failures.append(f"strip failed: {a}")
    if str(b) != "/var/home/rainbow/.hermes":
        failures.append(f"base failed: {b}")

    if _skill_from_calib_row({"scope": "ue_blackbox", "tool_name": "x"}) is not None:
        failures.append("ue_blackbox must be skipped, not fallen back")
    if _skill_from_calib_row({"scope": "my-skill"}) != "my-skill":
        failures.append("scope skill")
    if _skill_from_calib_row({"scope": "", "tool_name": "tool_a"}) != "tool_a":
        failures.append("empty scope fallback")
    if _skill_from_calib_row({"tool_name": "tool_b"}) != "tool_b":
        failures.append("missing scope fallback")

    skills = ["s%d" % i for i in range(10)]
    weights = [float(10 - i) for i in range(10)]
    prior = normalize_counts(dict(zip(skills, weights)))
    h0 = shannon_entropy(prior.values())
    rewards = {s: float(10 - i) for i, s in enumerate(skills)}
    betas = [0.1, 0.5, 1.0, 5.0, 20.0]
    ents = [
        shannon_entropy(softmax_posterior(prior, rewards, beta).values())
        for beta in betas
    ]
    for i in range(len(ents) - 1):
        if ents[i + 1] > ents[i] + 1e-9:
            failures.append(f"entropy did not decrease with beta: {ents}")
            break

    rng = random.Random(0)
    sessions = []
    for i in range(50):
        counts = defaultdict(float)
        wsum = sum(weights)
        for _ in range(8):
            r = rng.random() * wsum
            acc = 0.0
            pick = skills[-1]
            for s, w in zip(skills, weights):
                acc += w
                if r <= acc:
                    pick = s
                    break
            counts[pick] += 1.0
        sessions.append(("sess-%d" % i, dict(counts)))
    kls = [kl_div(normalize_counts(c), prior) for _, c in sessions]
    if len(kls) != 50:
        failures.append("expected 50 session KLs, got %d" % len(kls))
    if any(k < -1e-9 for k in kls):
        failures.append("negative KL")
    if kl_div(prior, prior) > 1e-8:
        failures.append("KL(p||p) not ~0")

    empty = compute(
        Path("/nonexistent/lifecycle.db"),
        Path("/nonexistent/calibration-log.jsonl"),
    )
    if empty["marginal_prior"]:
        failures.append("missing inputs should yield empty/uniform prior")
    if abs(empty["skill_entropy"]) > 1e-15:
        failures.append("empty entropy should be 0")

    tmpdir = CACHE / ("skill-info-cost-test-" + uuid.uuid4().hex)
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        outp = tmpdir / "skill-prior.json"
        logp = tmpdir / "skill-kl-log.jsonl"
        mean_kl = sum(kls) / len(kls)
        payload = {
            "ts": _now(),
            "marginal_prior": prior,
            "skill_entropy": h0,
            "per_session_kl": [
                {"session_id": s, "kl": k} for (s, _), k in zip(sessions, kls)
            ],
            "beta": BETA,
            "info_cost_bound": mean_kl,
        }
        _atomic_write_json(outp, payload)
        _append_jsonl(
            logp,
            {
                "ts": payload["ts"],
                "skill_entropy": h0,
                "mean_kl": mean_kl,
                "n_sessions": 50,
            },
        )
        loaded = json.loads(outp.read_text(encoding="utf-8"))
        log_line = json.loads(logp.read_text(encoding="utf-8").splitlines()[0])
        if loaded.get("beta") != BETA:
            failures.append("beta roundtrip")
        if log_line.get("n_sessions") != 50:
            failures.append("n_sessions log")
        if abs(log_line.get("skill_entropy", -1) - h0) > 1e-9:
            failures.append("entropy log")
        if OUT_PATH.exists() and "skill-info-cost-test-" in str(outp):
            pass
        if outp.resolve() == OUT_PATH.resolve():
            failures.append("self-test wrote production OUT_PATH")
    finally:
        try:
            for child in tmpdir.iterdir():
                child.unlink()
            tmpdir.rmdir()
        except OSError:
            pass

    if failures:
        print(json.dumps({"ok": False, "failures": failures, "ents": ents}))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "entropy_vs_beta": list(zip(betas, ents)),
                "prior_entropy": h0,
                "mean_kl_synthetic": sum(kls) / len(kls),
                "n_skills": 10,
                "n_sessions": 50,
                "path_strip": str(a),
            }
        )
    )
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Skill information cost (bounded rationality tracker)"
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return cmd_self_test()
    return cmd_run(OUT_PATH, KL_LOG, LIFECYCLE_DB, CALIBRATION_LOG)


if __name__ == "__main__":
    raise SystemExit(main())

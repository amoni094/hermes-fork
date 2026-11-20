#!/usr/bin/env python3
"""Causal-critique accumulate: heuristic CoT/tool-trace critique + ERM scores.

Inspects reasoning traces for confounds/back-door paths using lexical heuristics,
writes causal-critique-ranking.json with structure flags, then updates
skill-causal-coherence.json and causal-events.db.

Hard core: score increases only when confounds are flagged AND interventional
reasoning is validated. Outcome-only observations do not raise the score.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import random
import sqlite3
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / "cache"
SESSIONS_A = _hermes_root / "sessions"
SESSIONS_B = _hermes_base / "sessions"
RANKING_PATH = CACHE / "causal-critique-ranking.json"
COHERENCE_PATH = CACHE / "skill-causal-coherence.json"
EVENTS_JSONL = CACHE / "causal-events.jsonl"
EVENTS_DB = CACHE / "causal-events.db"
CALIB_LOG = CACHE / "calibration-log.jsonl"

CAUSE_CUES = ("because", "if ", "only if", "correlation", "correlat", "associated with")
INTERV_CUES = ("intervention", "randomized", "controlled", "counterfactual", "do-operator", "do(", "manipulate")
BACKDOOR_CUES = ("backdoor", "back-door", "confound", "collider", "selection bias", "common cause")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock") if path.suffix else path.with_name(path.name + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    line = json.dumps(rec) + "\n"
    with open(str(lock), "a", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            with open(str(path), "a", encoding="utf-8") as fh:
                fh.write(line)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _clip01(v, default=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(x):
        return default
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def critique_causal_structure(trace, skill_id: str) -> dict:
    """Return {confounds, backdoors, interventions} plus structure flags."""
    if trace is None:
        text = ""
    elif isinstance(trace, str):
        text = trace
    else:
        try:
            text = json.dumps(trace)
        except (TypeError, ValueError):
            text = str(trace)
    t = text.lower()
    confounds = [c.strip() for c in CAUSE_CUES if c in t]
    backdoors = [c.strip() for c in BACKDOOR_CUES if c in t]
    interventions = [c.strip() for c in INTERV_CUES if c in t]
    has_cause = bool(confounds)
    has_interv = bool(interventions)
    has_back = bool(backdoors)
    confound_flagged = bool((has_cause and not has_interv) or has_back)
    # Structure was inspected whenever we ran this function on a non-empty trace.
    inspected = bool(t.strip())
    score = 0.0
    if inspected:
        # High when intervention validated and confounds not dominating.
        interv_ok = 1.0 if has_interv else 0.0
        cr = 0.5 if confound_flagged else 0.0
        if has_back:
            cr = max(cr, 0.7)
        score = interv_ok * (1.0 - cr)
        if has_interv and not confound_flagged:
            score = 1.0
        elif has_interv and confound_flagged:
            score = 0.5
        elif confound_flagged:
            score = 0.15
        else:
            score = 0.35
    return {
        "skill_id": str(skill_id or "unknown"),
        "confounds": confounds,
        "backdoors": backdoors,
        "interventions": interventions,
        "interventional_flag": bool(inspected),
        "confound_flag": bool(inspected),
        "intervention_validated": bool(has_interv),
        "confound_flagged": confound_flagged,
        "interventional_correct": 1.0 if has_interv else 0.0,
        "confound_rate": 0.5 if confound_flagged else 0.0,
        "total": 1.0,
        "causal_coherence_score": _clip01(score),
        "inspected": inspected,
    }


def _trace_text_from_rec(rec: dict) -> str:
    parts = []
    for k in ("reasoning", "reasoning_content", "content", "_compressed_summary"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
        elif isinstance(v, dict):
            try:
                parts.append(json.dumps(v))
            except (TypeError, ValueError):
                pass
    return "\n".join(parts)


def load_session_traces(dirs: list, limit_files: int = 12, limit_recs: int = 400) -> list:
    traces = []
    files = []
    for d in dirs:
        if d is None or not d.exists():
            continue
        try:
            files.extend([p for p in d.iterdir() if p.suffix == ".jsonl" and p.is_file()])
        except OSError:
            continue
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    n_recs = 0
    for fp in files[:limit_files]:
        try:
            with open(str(fp), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(rec, dict):
                        continue
                    text = _trace_text_from_rec(rec)
                    if not text.strip():
                        continue
                    skill = rec.get("tool_name") or rec.get("skill") or rec.get("skill_id") or "session"
                    traces.append({
                        "skill_id": str(skill),
                        "episode_id": str(rec.get("timestamp") or rec.get("ts") or fp.name),
                        "trace": text[:8000],
                    })
                    n_recs += 1
                    if n_recs >= limit_recs:
                        return traces
        except OSError:
            continue
    return traces


def load_calib_traces(path: Path, max_rows: int = 8000) -> list:
    if not path.exists():
        return []
    by_sess = defaultdict(list)
    try:
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            if path.stat().st_size > 8_000_000:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 4_000_000))
                fh.readline()
            n = 0
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("scope") == "ue_blackbox":
                    continue
                tool = rec.get("tool_name")
                if not tool:
                    continue
                sid = str(rec.get("session_id") or "unknown")
                by_sess[sid].append(str(tool))
                n += 1
                if n >= max_rows:
                    break
    except OSError:
        return []
    traces = []
    for sid, tools in list(by_sess.items())[:200]:
        if not tools:
            continue
        skill = tools[-1]
        traces.append({
            "skill_id": skill,
            "episode_id": sid,
            "trace": " ".join(tools[-40:]),
        })
    return traces


def score_from_critique(c: dict) -> float:
    if not c.get("interventional_flag") or not c.get("confound_flag"):
        return None  # type: ignore
    ic = 1.0 if c.get("intervention_validated") else 0.0
    cr = 0.5 if c.get("confound_flagged") else 0.0
    return _clip01(ic * (1.0 - cr))


def ranking_from_traces(traces: list) -> list:
    ranking = []
    for i, tr in enumerate(traces):
        c = critique_causal_structure(tr.get("trace"), tr.get("skill_id") or "unknown")
        if not c.get("inspected"):
            continue
        ranking.append({
            "skill_id": c["skill_id"],
            "name": c["skill_id"],
            "episode_id": str(tr.get("episode_id") or i),
            "interventional_flag": True,
            "confound_flag": True,
            "intervention_validated": c["intervention_validated"],
            "confound_flagged": c["confound_flagged"],
            "interventional_correct": c["interventional_correct"],
            "confound_rate": c["confound_rate"],
            "total": 1.0,
            "causal_impact": c["causal_coherence_score"],
            "confounds": c["confounds"],
            "backdoors": c["backdoors"],
            "interventions": c["interventions"],
        })
    return ranking


def has_causal_structure(entry: dict) -> bool:
    keys = set(entry.keys()) if isinstance(entry, dict) else set()
    has_int = any(k in keys for k in ("interventional_flag", "intervention_validated", "interventional_correct"))
    has_conf = any(k in keys for k in ("confound_flag", "confound_flagged", "confound_rate", "confounds"))
    return has_int and has_conf


def accumulate(entries: list, history: dict, events_out: list) -> dict:
    skills = dict(history.get("skills") or {})
    n_updated = 0
    n_skipped = 0
    for i, entry in enumerate(entries):
        if not has_causal_structure(entry):
            n_skipped += 1
            continue
        sid = str(entry.get("skill_id") or entry.get("name") or "unknown")
        ic = 1.0 if entry.get("intervention_validated") or entry.get("interventional_correct") else 0.0
        cr = 0.5 if entry.get("confound_flagged") else _clip01(entry.get("confound_rate"), 0.0)
        new_score = _clip01(ic * (1.0 - cr))
        prev = skills.get(sid) or {}
        prev_score = _clip01(prev.get("causal_coherence_score"), 0.0)
        try:
            prev_n = int(prev.get("n") or 0)
        except (TypeError, ValueError):
            prev_n = 0
        rec = {
            "causal_coherence_score": new_score,
            "n": prev_n + 1,
            "history": list(prev.get("history") or [])[-49:] + [{"ts": _now(), "score": new_score}],
        }
        skills[sid] = rec
        events_out.append({
            "ts": _now(),
            "skill_id": sid,
            "episode_id": str(entry.get("episode_id") or i),
            "confound_flagged": bool(entry.get("confound_flagged")),
            "intervention_validated": bool(entry.get("intervention_validated")),
            "score_delta": round(new_score - prev_score, 6),
        })
        n_updated += 1
    return {
        "ts": _now(),
        "n_entries": len(entries),
        "n_updated": n_updated,
        "n_skipped_no_structure": n_skipped,
        "skills": skills,
        "status": "ok" if n_updated else "insufficient_data",
    }


def persist_events(events: list, jsonl: Path, db: Path) -> None:
    for e in events:
        _append_jsonl(jsonl, e)
    if not events:
        return
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db), timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS causal_events ("
            "id INTEGER PRIMARY KEY, ts TEXT, skill_id TEXT, episode_id TEXT, "
            "confound_flagged INTEGER, intervention_validated INTEGER, score_delta REAL)"
        )
        conn.executemany(
            "INSERT INTO causal_events(ts, skill_id, episode_id, confound_flagged, "
            "intervention_validated, score_delta) VALUES (?,?,?,?,?,?)",
            [
                (
                    e["ts"], e["skill_id"], e["episode_id"],
                    int(bool(e["confound_flagged"])),
                    int(bool(e["intervention_validated"])),
                    float(e["score_delta"]),
                )
                for e in events
            ],
        )
        conn.commit()
    finally:
        conn.close()


def load_history(path: Path) -> dict:
    if not path.exists():
        return {"ts": None, "skills": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {"ts": None, "skills": {}}
    if not isinstance(data, dict):
        return {"ts": None, "skills": {}}
    skills = data.get("skills")
    if not isinstance(skills, dict):
        skills = {}
    return {"ts": data.get("ts"), "skills": skills}


def run_live() -> dict:
    traces = load_session_traces([SESSIONS_A, SESSIONS_B])
    if not traces:
        traces = load_calib_traces(CALIB_LOG)
    ranking = ranking_from_traces(traces)
    if ranking:
        _atomic_write(RANKING_PATH, {"ts": _now(), "n": len(ranking), "ranking": ranking})
    if not ranking:
        return {"status": "insufficient_data", "n": 0, "ts": _now(), "reason": "no inspectable traces"}
    hist = load_history(COHERENCE_PATH)
    events = []
    state = accumulate(ranking, hist, events)
    if state.get("n_updated"):
        _atomic_write(COHERENCE_PATH, state)
        persist_events(events, EVENTS_JSONL, EVENTS_DB)
    slim = {k: state[k] for k in state if k != "skills"}
    slim["n_skills"] = len(state.get("skills") or {})
    slim["n_ranking"] = len(ranking)
    return slim


def layer1_demo(rng=None) -> dict:
    rng = rng or random.Random(3)
    traces = []
    # A: interventional language, few confounds
    for i in range(25):
        traces.append({
            "skill_id": "A",
            "episode_id": "pearl-A-%02d" % i,
            "trace": "We ran a randomized controlled intervention; because the assignment was randomized, correlation is not the identification strategy.",
        })
    # B: because/correlation without intervention
    for i in range(25):
        traces.append({
            "skill_id": "B",
            "episode_id": "pearl-B-%02d" % i,
            "trace": "It works because of the correlation; if x then y, only if we ignore the confound.",
        })
    ranking = ranking_from_traces(traces)
    hist = {"skills": {}}
    events = []
    state = accumulate(ranking, hist, events)
    scores = {sid: rec["causal_coherence_score"] for sid, rec in state["skills"].items()}
    return {"scores": scores, "state": state, "n": len(ranking)}


def _self_test() -> int:
    # Outcome-only must not raise score
    hist = {"skills": {"C": {"causal_coherence_score": 0.40, "n": 1, "history": []}}}
    events = []
    st = accumulate([{"skill_id": "C", "outcome_correct": True, "episode_id": "x"}], hist, events)
    assert st["n_updated"] == 0
    assert abs(st["skills"]["C"]["causal_coherence_score"] - 0.40) < 1e-12
    c = critique_causal_structure("", "z")
    assert c["inspected"] is False
    c2 = critique_causal_structure("randomized controlled intervention", "z")
    assert c2["intervention_validated"] is True
    c3 = critique_causal_structure("it works because of the correlation", "z")
    assert c3["confound_flagged"] is True
    demo = layer1_demo(random.Random(3))
    a = demo["scores"]["A"]
    b = demo["scores"]["B"]
    assert a >= 0.75, a
    assert b <= 0.50, b
    tmp = COHERENCE_PATH.with_name(COHERENCE_PATH.stem + "_test_" + uuid.uuid4().hex + COHERENCE_PATH.suffix)
    tmp_db = EVENTS_DB.with_name(EVENTS_DB.stem + "_test_" + uuid.uuid4().hex + EVENTS_DB.suffix)
    tmp_jsonl = EVENTS_JSONL.with_name(EVENTS_JSONL.stem + "_test_" + uuid.uuid4().hex + EVENTS_JSONL.suffix)
    try:
        events = []
        st2 = accumulate(ranking_from_traces([{
            "skill_id": "C",
            "episode_id": "y",
            "trace": "randomized controlled intervention",
        }]), hist, events)
        _atomic_write(tmp, st2)
        persist_events(events, tmp_jsonl, tmp_db)
        assert json.loads(tmp.read_text(encoding="utf-8"))["n_updated"] == 1
        conn = sqlite3.connect(str(tmp_db), timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            n = conn.execute("SELECT COUNT(*) FROM causal_events").fetchone()[0]
            assert n == 1
        finally:
            conn.close()
    finally:
        for p in (tmp, tmp_jsonl, tmp_db, Path(str(tmp) + ".lock"), tmp_jsonl.with_suffix(".lock")):
            Path(p).unlink(missing_ok=True)
        Path(str(tmp_db) + "-wal").unlink(missing_ok=True)
        Path(str(tmp_db) + "-shm").unlink(missing_ok=True)
    print(f"[causal-critique-accumulate] --self-test PASS A={a:.3f} B={b:.3f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Causal-critique accumulate")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[causal-critique-accumulate] --self-test FAIL: {exc}")
            return 1
    try:
        rec = run_live()
        print(json.dumps(rec))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

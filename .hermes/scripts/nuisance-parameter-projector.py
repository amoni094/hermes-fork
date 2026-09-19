#!/usr/bin/python3
"""
nuisance-parameter-projector.py

Adjusts skill routing scores by projecting out nuisance dimensions —
confounding variables (session age, query length, time-of-day) that
inflate or deflate apparent skill relevance without reflecting genuine
semantic match.

Math basis (robust_stats / projection_geometry): a nuisance parameter θ_n
is orthogonal to the parameter of interest θ. Projecting the score vector
onto the subspace orthogonal to θ_n removes its confounding influence.
For Hermes:
  - Score vector S = [cosine_sim(query, skill_i)] for all skills i
  - Nuisance factors: query_length (longer queries inflate many skills),
    session_turn (later turns inflate recently-used skills via recency bias),
    time_of_day (some skills cluster by user activity pattern)
  - Projected score S' = S - Σ_j (S·n_j / ||n_j||²) n_j
    where n_j is the nuisance direction (correlation of S with factor j)

The result: skills that score highly only because the query is long
or the session is deep get demoted; genuinely relevant skills survive.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
SKILLS_DIR = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
OUT_FILE   = CACHE_DIR / "nuisance-projector-calibration.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_skill_descriptions() -> dict[str, str]:
    skills: dict[str, str] = {}
    for skill_dir in SKILLS_DIR.rglob("SKILL.md"):
        try:
            text = skill_dir.read_text()
            m = re.search(r"description:\s*['\"]?(.+?)['\"]?\n", text)
            desc = m.group(1) if m else skill_dir.parent.name
            skills[skill_dir.parent.name] = desc
        except Exception:
            pass
    return skills


def _extract_session_features(text: str) -> dict:
    """Extract nuisance features from a session."""
    lines = text.split("\n")
    turns = 0
    total_query_len = 0
    skill_calls: list[str] = []
    timestamps: list[str] = []

    for line in lines:
        try:
            obj = json.loads(line)
            role = obj.get("role","")
            if role == "user":
                turns += 1
                content = obj.get("content","")
                if isinstance(content, str):
                    total_query_len += len(content)
                ts = obj.get("timestamp","")
                if ts:
                    timestamps.append(ts)
            elif role == "assistant":
                for tc in obj.get("tool_calls",[]):
                    if isinstance(tc, dict) and tc.get("function",{}).get("name") == "skill_view":
                        args = tc["function"].get("arguments","{}")
                        if isinstance(args, str):
                            try: args = json.loads(args)
                            except: pass
                        s = args.get("name","") if isinstance(args,dict) else ""
                        if s:
                            skill_calls.append(s)
        except Exception:
            pass

    mean_query_len = total_query_len / max(turns, 1)
    hour = 12  # default
    if timestamps:
        try:
            ts = timestamps[0]
            hour = int(ts[11:13])
        except Exception:
            pass

    return {
        "turns": turns,
        "mean_query_len": mean_query_len,
        "hour": hour,
        "skill_calls": skill_calls,
        "n_skills": len(skill_calls),
    }


def _build_nuisance_vectors(
    sessions: list[dict],
    skills: list[str],
) -> list[np.ndarray]:
    """
    Build nuisance direction vectors in skill-score space.
    Each nuisance factor produces one direction vector.
    """
    # For each nuisance factor, compute correlation with skill frequency
    # across sessions: nuisance_vec[i] = corr(factor, skill_i_freq)
    n_skills = len(skills)
    skill_idx = {s: i for i, s in enumerate(skills)}

    factors = ["mean_query_len", "turns", "hour"]
    nuisance_vecs: list[np.ndarray] = []

    for factor in factors:
        factor_vals = np.array([s[factor] for s in sessions], dtype=float)
        if np.std(factor_vals) < 1e-6:
            continue  # no variance, skip

        skill_freqs = np.zeros((len(sessions), n_skills))
        for si, sess in enumerate(sessions):
            for skill in sess["skill_calls"]:
                if skill in skill_idx:
                    skill_freqs[si, skill_idx[skill]] += 1

        # Correlation of each skill's frequency with factor
        corr_vec = np.zeros(n_skills)
        for i in range(n_skills):
            if np.std(skill_freqs[:, i]) > 1e-6:
                corr = np.corrcoef(factor_vals, skill_freqs[:, i])[0, 1]
                corr_vec[i] = corr if not math.isnan(corr) else 0.0

        norm = np.linalg.norm(corr_vec)
        if norm > 1e-6:
            nuisance_vecs.append(corr_vec / norm)

    return nuisance_vecs


def _project_scores(
    scores: np.ndarray,
    nuisance_vecs: list[np.ndarray],
) -> np.ndarray:
    """Remove nuisance components from score vector."""
    projected = scores.copy()
    for nv in nuisance_vecs:
        projected -= np.dot(projected, nv) * nv
    return projected


def calibrate(dry_run: bool = False) -> dict:
    """Build nuisance calibration from session history."""
    session_files = sorted(SESSIONS.glob("*.jsonl"))
    session_feats: list[dict] = []
    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        feats = _extract_session_features(text)
        if feats["n_skills"] > 0:
            session_feats.append(feats)

    skills = list(_load_skill_descriptions().keys())
    if not skills or len(session_feats) < 2:
        return {"status": "insufficient_data", "sessions": len(session_feats), "skills": len(skills)}

    nuisance_vecs = _build_nuisance_vectors(session_feats, skills)
    return {
        "sessions": len(session_feats),
        "skills": len(skills),
        "nuisance_factors": len(nuisance_vecs),
        "nuisance_vecs": [v.tolist() for v in nuisance_vecs],
        "skill_index": {s: i for i, s in enumerate(skills)},
    }


def project_query(query: str, calib: dict) -> list[dict]:
    """Score skills for a query and remove nuisance components."""
    skills = list(calib.get("skill_index", {}).keys())
    if not skills:
        return []

    # Raw scores via keyword overlap
    qwords = set(re.findall(r"[a-z]{3,}", query.lower()))
    skill_descs = _load_skill_descriptions()
    raw = np.array([
        len(qwords & set(re.findall(r"[a-z]{3,}", skill_descs.get(s,"").lower()))) / max(len(qwords), 1)
        for s in skills
    ])

    # Project out nuisance
    nvecs = [np.array(v) for v in calib.get("nuisance_vecs", [])]
    projected = _project_scores(raw, nvecs)

    # Rank
    ranked = sorted(
        [(skills[i], float(raw[i]), float(projected[i])) for i in range(len(skills))],
        key=lambda x: -x[2]
    )[:15]
    return [{"skill": s, "raw": round(r,4), "projected": round(p,4)} for s,r,p in ranked if p > 0]


def run(query: str | None, dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    calib = calibrate(dry_run)

    print(f"\n=== Nuisance Parameter Projector — {now[:10]} ===")
    status = calib.get("status","")
    if status == "insufficient_data":
        print(f"Insufficient data: {calib['sessions']} sessions with skill calls (need ≥2)")
        return

    print(f"Sessions: {calib['sessions']},  Skills: {calib['skills']},  Nuisance factors: {calib['nuisance_factors']}")

    if query:
        results = project_query(query, calib)
        print(f"\nQuery: '{query}'")
        print(f"  {'Skill':<40} {'Raw':>6} {'Projected':>10}")
        print("  " + "-" * 58)
        for r in results[:10]:
            delta = r['projected'] - r['raw']
            tag = f" ({delta:+.4f})" if abs(delta) > 0.001 else ""
            print(f"  {r['skill']:<40} {r['raw']:>6.4f} {r['projected']:>10.4f}{tag}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, **calib}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nCalibration written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nuisance parameter projector for skill routing")
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(query=args.query, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

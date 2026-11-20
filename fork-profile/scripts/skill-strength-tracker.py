#!/usr/bin/env python3
"""SAM-inspired skill-trace strength tracker (Raaijmakers & Shiffrin 1981).

Hard core: unused traces decay exponentially in time since last retrieval;
successful retrieval increments strength (SAM incrementing). Belt: keyword
overlap ranking and JSON persistence.

Stdlib only. Atomic JSON via tmp + os.replace. Lock the sibling .lock file.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

DEFAULT_STORE = _hermes_root / "omni" / "skill-strengths.json"
DECAY_FAST = 0.05
DECAY_SLOW = 0.01
BOOST_COEF = 0.1
STRENGTH_MIN = 0.0
STRENGTH_MAX = 1.0


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_dt(raw) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _clip01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(STRENGTH_MIN, min(STRENGTH_MAX, float(value)))


class SkillStrengthTracker:
    """Retrieval-strength store for hyphenated skill names."""

    def __init__(self, store_path=None):
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE
        self.skills: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        path = self.store_path
        if not path.exists():
            self.skills = {}
            return
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self.skills = {}
            return
        if isinstance(obj, dict) and isinstance(obj.get("skills"), dict):
            raw = obj["skills"]
        elif isinstance(obj, dict):
            raw = obj
        else:
            raw = {}
        cleaned: dict[str, dict] = {}
        for name, rec in raw.items():
            if not isinstance(name, str) or not isinstance(rec, dict):
                continue
            try:
                access = int(rec.get("access_count") or 0)
            except (TypeError, ValueError):
                access = 0
            try:
                strength = _clip01(float(rec.get("strength") or 0.0))
            except (TypeError, ValueError):
                strength = 0.0
            try:
                decay_applied = int(rec.get("decay_days_applied") or 0)
            except (TypeError, ValueError):
                decay_applied = 0
            cleaned[name] = {
                "access_count": max(0, access),
                "last_accessed": rec.get("last_accessed"),
                "strength": strength,
                "decay_days_applied": max(0, decay_applied),
            }
        self.skills = cleaned

    def _ensure(self, skill_name: str) -> dict:
        rec = self.skills.get(skill_name)
        if rec is None:
            rec = {
                "access_count": 0,
                "last_accessed": None,
                "strength": 0.0,
                "decay_days_applied": 0,
            }
            self.skills[skill_name] = rec
        return rec

    def record_access(self, skill_name: str) -> dict:
        name = str(skill_name or "").strip()
        if not name:
            return {}
        rec = self._ensure(name)
        rec["access_count"] = int(rec.get("access_count") or 0) + 1
        rec["last_accessed"] = _utcnow().isoformat()
        rec["decay_days_applied"] = 0
        boost = min(1.0, BOOST_COEF * math.log1p(rec["access_count"]))
        rec["strength"] = _clip01(float(rec.get("strength") or 0.0) + boost)
        return rec

    def decay_all(self, now: datetime | None = None) -> dict:
        """Apply unused-trace exponential decay.

        SAM: strength falls with time since last retrieval. Daily crons must
        decay only the *new* idle days (delta vs decay_days_applied); applying
        exp(-rate * days_since) on every run would compound the same idle
        interval and destroy the trace.
        """
        now = now or _utcnow()
        changed = 0
        for rec in self.skills.values():
            last = _parse_dt(rec.get("last_accessed"))
            if last is None:
                continue
            days_since = max(0, (now - last).days)
            applied = int(rec.get("decay_days_applied") or 0)
            delta = max(0, days_since - applied)
            if delta == 0:
                continue
            access = int(rec.get("access_count") or 0)
            rate = DECAY_FAST if access < 5 else DECAY_SLOW
            rec["strength"] = _clip01(float(rec.get("strength") or 0.0) * math.exp(-rate * delta))
            rec["decay_days_applied"] = days_since
            changed += 1
        return {"n_skills": len(self.skills), "decayed": changed}

    def get_ranked(self) -> list[tuple[str, float]]:
        rows = [(name, _clip01(float(rec.get("strength") or 0.0))) for name, rec in self.skills.items()]
        rows.sort(key=lambda item: (-item[1], item[0]))
        return rows

    def recommend(self, keywords: list[str], top_n: int = 5) -> list[tuple[str, float]]:
        keys = {str(k).strip().lower() for k in (keywords or []) if str(k).strip()}
        n_keys = max(1, len(keys) if keys else len(keywords or []))
        scored: list[tuple[str, float]] = []
        for name, rec in self.skills.items():
            tokens = {part for part in str(name).lower().split("-") if part}
            overlap = (len(keys & tokens) / n_keys) if keys else 0.0
            strength = _clip01(float(rec.get("strength") or 0.0))
            scored.append((name, strength * overlap))
        scored.sort(key=lambda item: (-item[1], item[0]))
        n = max(0, int(top_n))
        return scored[:n]

    def save(self) -> None:
        dest = self.store_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": _utcnow().isoformat(),
            "skills": self.skills,
        }
        lock_path = dest.with_suffix(".lock")
        tmp = dest.with_suffix(".tmp")
        with open(lock_path, "w", encoding="utf-8") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(dest))


def _self_test() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="skill-strength-"))
    store = tmpdir / ("skill-strengths_" + uuid.uuid4().hex + ".json")
    try:
        t = SkillStrengthTracker(store_path=store)
        assert t.get_ranked() == []
        t.record_access("")
        assert t.get_ranked() == []
        t.record_access("memory-ttl-purge")
        t.record_access("memory-ttl-purge")
        t.record_access("routing-bandits")
        ranked = t.get_ranked()
        assert ranked[0][0] == "memory-ttl-purge"
        assert all(0.0 <= s <= 1.0 for _, s in ranked)
        recs = t.recommend(["memory", "ttl"], top_n=2)
        assert recs and recs[0][0] == "memory-ttl-purge"
        rec = t.skills["memory-ttl-purge"]
        rec["last_accessed"] = "2020-01-01T00:00:00+00:00"
        rec["decay_days_applied"] = 0
        before = rec["strength"]
        summary = t.decay_all()
        assert summary["decayed"] >= 1
        assert t.skills["memory-ttl-purge"]["strength"] < before
        t.save()
        t2 = SkillStrengthTracker(store_path=store)
        assert "memory-ttl-purge" in t2.skills
        t.record_access("x" * 10000)
        assert 0.0 <= t.skills["x" * 10000]["strength"] <= 1.0
        print(json.dumps({"ok": True, "ranked": ranked, "recommend": recs, "decay": summary}))
        return 0
    finally:
        try:
            if store.exists():
                store.unlink()
            lock = store.with_suffix(".lock")
            if lock.exists():
                lock.unlink()
            tmpdir.rmdir()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SAM skill-strength tracker")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--record", metavar="SKILL")
    parser.add_argument("--decay", action="store_true")
    parser.add_argument("--rank", action="store_true")
    parser.add_argument("--store", default=None)
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    tracker = SkillStrengthTracker(store_path=args.store)
    if args.record:
        tracker.record_access(args.record)
        tracker.save()
    if args.decay:
        summary = tracker.decay_all()
        tracker.save()
        print(json.dumps(summary))
    if args.rank or not (args.record or args.decay):
        print(json.dumps(tracker.get_ranked()[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

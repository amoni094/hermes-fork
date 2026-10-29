"""Event-based cron triggers (Einstein-McDaniel 1990 + ZooKeeper watches).

Time-based cron is prospective memory of the "check the clock" kind. Event-based
prospective memory (Einstein & McDaniel 1990) is cheaper to keep alive: fire when
a cue appears, not on a schedule. ZooKeeper watches (Hunt et al. 2010, insight 7)
are the systems analogue — one-shot triggers on znode change, re-registered after
each fire.

Condition types:
  db_row_count      — lifecycle.db row count > threshold
  skill_access_count — a skill's access_count in lifecycle.db > threshold
  file_changed      — file mtime changed (ZooKeeper watch style)

One-shot: after firing, do not re-fire until the condition resets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _hermes_home_base() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env).expanduser() if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


HERMES_HOME = _hermes_home_base()
LIFECYCLE_DB = HERMES_HOME / "memory-facts" / "lifecycle.db"
DEFAULT_JOBS_JSON = HERMES_HOME / "profiles" / "fork" / "cron" / "jobs.json"
DEFAULT_STATE_PATH = HERMES_HOME / "profiles" / "fork" / "cron" / ".trigger-state.json"


@dataclass
class EventTrigger:
    name: str
    condition_type: str
    condition_params: dict = field(default_factory=dict)
    job_id_to_trigger: str = ""
    last_checked_at: Optional[str] = None
    last_fired_at: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _open_lifecycle(conn: Optional[sqlite3.Connection] = None) -> tuple[sqlite3.Connection, bool]:
    if conn is not None:
        return conn, False
    db = LIFECYCLE_DB
    c = sqlite3.connect(str(db), timeout=30)
    c.execute("PRAGMA busy_timeout=5000")
    return c, True


def _db_row_count(conn: sqlite3.Connection, params: dict) -> bool:
    table = str(params.get("table") or "")
    if not _TABLE_NAME_RE.match(table):
        return False
    try:
        threshold = float(params.get("threshold", 0))
    except (TypeError, ValueError):
        return False
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    except sqlite3.Error:
        return False
    return int(row[0] if row else 0) > threshold


def _like_pattern(pattern: str) -> str:
    p = str(pattern or "")
    if "*" in p and "%" not in p:
        p = p.replace("*", "%")
    return p


def _skill_access_count(conn: sqlite3.Connection, params: dict) -> bool:
    pattern = _like_pattern(params.get("skill_path_pattern") or "")
    if not pattern:
        return False
    try:
        threshold = float(params.get("threshold", 0))
    except (TypeError, ValueError):
        return False
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.Error:
        return False
    count = 0
    if "skills" in tables:
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(access_count), 0) FROM skills "
                "WHERE path LIKE ? OR skill_path LIKE ? OR name LIKE ?",
                (pattern, pattern, pattern),
            ).fetchone()
            count = int(row[0] if row else 0)
        except sqlite3.Error:
            pass
    if count <= threshold and "fact_lifecycle" in tables:
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(access_count), 0) FROM fact_lifecycle "
                "WHERE memory_id LIKE ? OR fact_text LIKE ? OR COALESCE(fact_type,'') LIKE ?",
                (pattern, pattern, pattern),
            ).fetchone()
            count = max(count, int(row[0] if row else 0))
        except sqlite3.Error:
            pass
    if count <= threshold and "skill_kl_history" in tables \
            and "fact_lifecycle" not in tables and "skills" not in tables:
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM skill_kl_history WHERE skill_name LIKE ?",
                (pattern,),
            ).fetchone()
            count = int(row[0] if row else 0)
        except sqlite3.Error:
            pass
    return count > threshold


def _file_stat_mtime(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _file_changed(trigger: EventTrigger) -> bool:
    """ZooKeeper watch: fire once when mtime differs from the last registered version."""
    raw = (trigger.condition_params or {}).get("path")
    if not raw:
        return False
    path = Path(str(raw)).expanduser()
    mtime = _file_stat_mtime(path)
    if mtime is None:
        return False
    last = trigger.condition_params.get("_last_mtime")
    if last is None:
        # First observation: register the watch, do not fire.
        trigger.condition_params["_last_mtime"] = mtime
        return False
    try:
        last_f = float(last)
    except (TypeError, ValueError):
        trigger.condition_params["_last_mtime"] = mtime
        return False
    if mtime != last_f:
        trigger.condition_params["_last_mtime"] = mtime
        return True
    return False


def _condition_holds(trigger: EventTrigger, conn: Optional[sqlite3.Connection]) -> bool:
    ctype = trigger.condition_type
    params = trigger.condition_params or {}
    if ctype == "file_changed":
        return _file_changed(trigger)
    if conn is None:
        return False
    if ctype == "db_row_count":
        return _db_row_count(conn, params)
    if ctype == "skill_access_count":
        return _skill_access_count(conn, params)
    return False


def check_triggers(
    triggers: list[EventTrigger],
    conn: Optional[sqlite3.Connection] = None,
) -> list[str]:
    """Return job_ids that should fire now.

    One-shot: set last_fired_at on fire; do not re-fire until the condition
    resets (drops below threshold, or a new file-mtime change after re-register).
    """
    own = False
    db = conn
    needs_db = any(t.condition_type in ("db_row_count", "skill_access_count") for t in triggers)
    if needs_db and db is None:
        db, own = _open_lifecycle(None)
    fired: list[str] = []
    now = _now_iso()
    try:
        for trigger in triggers:
            trigger.last_checked_at = now
            holds = _condition_holds(trigger, db)
            if not holds:
                # Condition reset — arm the trigger again (Einstein-McDaniel cue).
                trigger.last_fired_at = None
                continue
            if trigger.last_fired_at:
                continue  # still true since last fire; wait for reset
            trigger.last_fired_at = now
            if trigger.job_id_to_trigger:
                fired.append(trigger.job_id_to_trigger)
    finally:
        if own and db is not None:
            db.close()
    return fired


def load_triggers_from_jobs_json(jobs_json_path) -> list[EventTrigger]:
    """Parse jobs.json for an 'event_trigger' key on each job definition."""
    path = Path(jobs_json_path)
    raw = path.read_bytes().decode("utf-8", errors="replace")
    data = json.loads(raw)
    jobs: list[dict] = []
    if isinstance(data, list):
        jobs = [j for j in data if isinstance(j, dict)]
    elif isinstance(data, dict):
        maybe = data.get("jobs")
        if isinstance(maybe, list):
            jobs = [j for j in maybe if isinstance(j, dict)]
        elif maybe is None:
            jobs = [
                {"id": k, **v} for k, v in data.items()
                if isinstance(v, dict) and "event_trigger" in v
            ]
    out: list[EventTrigger] = []
    for job in jobs:
        et = job.get("event_trigger")
        if not isinstance(et, dict):
            continue
        job_id = str(et.get("job_id_to_trigger") or job.get("id") or "")
        name = str(et.get("name") or job.get("name") or job_id or "unnamed")
        ctype = str(et.get("condition_type") or "")
        raw_params = et.get("condition_params")
        params: dict = dict(raw_params) if isinstance(raw_params, dict) else {}
        out.append(EventTrigger(
            name=name,
            condition_type=ctype,
            condition_params=params,
            job_id_to_trigger=job_id,
            last_checked_at=et.get("last_checked_at"),
            last_fired_at=et.get("last_fired_at"),
        ))
    return out


def persist_trigger_state(
    triggers: list[EventTrigger],
    state_path: Optional[os.PathLike] = None,
) -> Path:
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": _now_iso(),
        "triggers": [asdict(t) for t in triggers],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(str(tmp), str(path))
    return path


def load_trigger_state(state_path: Optional[os.PathLike] = None) -> list[EventTrigger]:
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("triggers") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[EventTrigger] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(EventTrigger(
            name=str(row.get("name") or ""),
            condition_type=str(row.get("condition_type") or ""),
            condition_params=dict(row.get("condition_params") or {}),
            job_id_to_trigger=str(row.get("job_id_to_trigger") or ""),
            last_checked_at=row.get("last_checked_at"),
            last_fired_at=row.get("last_fired_at"),
        ))
    return out


def _merge_state(triggers: list[EventTrigger], saved: list[EventTrigger]) -> None:
    by_key = {(t.name, t.job_id_to_trigger): t for t in saved}
    for t in triggers:
        prev = by_key.get((t.name, t.job_id_to_trigger))
        if prev is None:
            continue
        t.last_checked_at = prev.last_checked_at
        t.last_fired_at = prev.last_fired_at
        if "_last_mtime" in (prev.condition_params or {}):
            t.condition_params["_last_mtime"] = prev.condition_params["_last_mtime"]


def _self_test() -> int:
    failures: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        db_path = td / "lifecycle.db"
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE fact_lifecycle ("
            "memory_id TEXT, fact_text TEXT, fact_type TEXT, access_count INTEGER)"
        )
        conn.executemany("INSERT INTO items DEFAULT VALUES", [()] * 5)
        conn.execute(
            "INSERT INTO fact_lifecycle VALUES (?,?,?,?)",
            ("skills/foo/SKILL.md", "foo skill", "skill", 10),
        )
        conn.execute(
            "INSERT INTO fact_lifecycle VALUES (?,?,?,?)",
            ("skills/bar/SKILL.md", "bar skill", "skill", 1),
        )
        conn.commit()

        watched = td / "watched.txt"
        watched.write_text("v1", encoding="utf-8")

        t_db = EventTrigger(
            name="db-over",
            condition_type="db_row_count",
            condition_params={"table": "items", "threshold": 3},
            job_id_to_trigger="job-db",
        )
        t_skill = EventTrigger(
            name="skill-hot",
            condition_type="skill_access_count",
            condition_params={"skill_path_pattern": "skills/foo%", "threshold": 5},
            job_id_to_trigger="job-skill",
        )
        t_file = EventTrigger(
            name="file-watch",
            condition_type="file_changed",
            condition_params={"path": str(watched)},
            job_id_to_trigger="job-file",
        )
        t_quiet = EventTrigger(
            name="db-quiet",
            condition_type="db_row_count",
            condition_params={"table": "items", "threshold": 100},
            job_id_to_trigger="job-quiet",
        )

        first = check_triggers([t_db, t_skill, t_file, t_quiet], conn=conn)
        expect("job-db" in first, f"db_row_count should fire, got {first}")
        expect("job-skill" in first, f"skill_access_count should fire, got {first}")
        expect("job-file" not in first, f"file_changed must not fire on first watch, got {first}")
        expect("job-quiet" not in first, f"below-threshold must not fire, got {first}")
        expect(t_db.last_fired_at is not None, "db trigger last_fired_at set")
        expect(t_file.last_fired_at is None, "file trigger not fired yet")

        second = check_triggers([t_db, t_skill, t_file, t_quiet], conn=conn)
        expect(second == [], f"one-shot: no re-fire while condition holds, got {second}")

        # Reset db condition, then re-arm and re-fire.
        conn.execute("DELETE FROM items")
        conn.commit()
        reset = check_triggers([t_db], conn=conn)
        expect(reset == [], f"reset should not fire, got {reset}")
        expect(t_db.last_fired_at is None, "last_fired_at cleared on reset")
        conn.executemany("INSERT INTO items DEFAULT VALUES", [()] * 5)
        conn.commit()
        again = check_triggers([t_db], conn=conn)
        expect("job-db" in again, f"should fire again after reset, got {again}")

        watched.write_text("v2", encoding="utf-8")
        os.utime(watched, None)
        third = check_triggers([t_file], conn=conn)
        expect("job-file" in third, f"file_changed should fire on mtime change, got {third}")
        fourth = check_triggers([t_file], conn=conn)
        expect(fourth == [], f"file watch one-shot until next change, got {fourth}")

        jobs_path = td / "jobs.json"
        jobs_path.write_text(json.dumps({
            "jobs": [
                {
                    "id": "from-json",
                    "name": "json-trigger",
                    "event_trigger": {
                        "name": "json-db",
                        "condition_type": "db_row_count",
                        "condition_params": {"table": "items", "threshold": 1},
                    },
                },
                {"id": "no-trigger", "name": "plain"},
            ],
        }), encoding="utf-8")
        loaded = load_triggers_from_jobs_json(jobs_path)
        expect(len(loaded) == 1, f"expected 1 trigger from jobs.json, got {len(loaded)}")
        expect(loaded[0].job_id_to_trigger == "from-json", loaded[0].job_id_to_trigger)

        state_path = td / ".trigger-state.json"
        persist_trigger_state([t_db, t_file], state_path)
        restored = load_trigger_state(state_path)
        expect(len(restored) == 2, f"expected 2 restored, got {len(restored)}")
        expect(any(t.last_fired_at for t in restored), "persisted last_fired_at")

        conn.close()

    if failures:
        print("SELF-TEST FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("SELF-TEST PASS")
    print("  db_row_count fires above threshold, one-shot until reset")
    print("  skill_access_count fires on matching skill access_count")
    print("  file_changed fires on mtime change (ZooKeeper watch), not on first observe")
    print("  jobs.json event_trigger parse + trigger-state persist/load")
    return 0


def _cli_check(jobs_path: Path, state_path: Path) -> int:
    if not jobs_path.is_file():
        print(f"jobs.json not found: {jobs_path}", file=sys.stderr)
        return 2
    triggers = load_triggers_from_jobs_json(jobs_path)
    saved = load_trigger_state(state_path)
    _merge_state(triggers, saved)
    would = check_triggers(triggers)
    if not would:
        print("none")
        return 0
    for job_id in would:
        print(job_id)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Event-based cron triggers")
    p.add_argument("--check", action="store_true",
                   help="Run check_triggers and print job ids that would fire")
    p.add_argument("--self-test", action="store_true", help="Run mock-trigger self-test")
    p.add_argument("--jobs", default=str(DEFAULT_JOBS_JSON), help="jobs.json path")
    p.add_argument("--state", default=str(DEFAULT_STATE_PATH), help="trigger state JSON")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.check:
        return _cli_check(Path(args.jobs), Path(args.state))
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

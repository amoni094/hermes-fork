#!/usr/bin/env python3
"""Join turn-behavior success labels onto compliance scores.

Indexes turn-behavior.jsonl by (session_id, tool_name, ts_minute) and joins
onto compliance-scores.jsonl. Writes labeled_compliance.jsonl plus a join
report. Keeps turn-behavior `label` and plugin `uncalibrated_score` as
separate fields (do not min() them). Stdlib only. Fail-open.

Usage:
  python3 compliance-label-bridge.py --self-test
  python3 compliance-label-bridge.py
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', '').strip()
    if profile:
        return profile
    raw = os.environ.get('HERMES_HOME', '').strip()
    if raw:
        p = Path(raw)
        if p.parent.name == 'profiles':
            return p.name
    if (_hermes_home() / 'profiles' / 'fork').exists():
        return 'fork'
    return ''


def _hermes_root() -> Path:
    base = _hermes_home()
    profile = _profile_name()
    return (base / 'profiles' / profile) if profile else base


_HERMES_ROOT = _hermes_root()
CACHE = _HERMES_ROOT / 'cache'
TB_PATH = CACHE / 'turn-behavior.jsonl'
CS_PATH = CACHE / 'compliance-scores.jsonl'
OUT_PATH = CACHE / 'labeled_compliance.jsonl'
REPORT_PATH = CACHE / 'compliance-label-bridge-report.json'

# Exact minute first; ±1 minute covers tool calls that cross a minute boundary.
_MINUTE_OFFSETS = (0, -1, 1)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(text, encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def parse_ts(raw) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def ts_minute(raw, offset_minutes: int = 0) -> str | None:
    dt = parse_ts(raw) if not isinstance(raw, datetime) else raw
    if dt is None:
        return None
    floored = dt.replace(second=0, microsecond=0)
    if offset_minutes:
        floored = floored + timedelta(minutes=int(offset_minutes))
    return floored.isoformat()


def session_base(session_id) -> str:
    sid = str(session_id or '').strip()
    if not sid:
        return ''
    return sid.split(':', 1)[0]


def _load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    try:
        with path.open(encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        return []
    return rows


def build_tb_index(rows: list) -> tuple:
    """Return (session_index, tool_index).

    session_index: (session_id, tool_name, ts_minute) -> [(dt, label, row), ...]
    tool_index: (tool_name, ts_minute) -> same, for rows with no session_id.
    """
    session_index: dict = {}
    tool_index: dict = {}
    for row in rows:
        tool = str(row.get('tool_name') or '').strip()
        dt = parse_ts(row.get('ts'))
        if not tool or dt is None:
            continue
        success = row.get('success')
        if not isinstance(success, bool):
            continue
        label = 1.0 if success else 0.0
        mk = ts_minute(dt, 0)
        sid = str(row.get('session_id') or '').strip()
        item = (dt, label, row)
        if sid:
            session_index.setdefault((sid, tool, mk), []).append(item)
            base = session_base(sid)
            if base and base != sid:
                session_index.setdefault((base, tool, mk), []).append(item)
        tool_index.setdefault((tool, mk), []).append(item)
    return session_index, tool_index


def _closest(items: list, dt: datetime):
    if not items:
        return None
    return min(items, key=lambda it: abs((it[0] - dt).total_seconds()))


def match_turn_behavior(
    row: dict,
    session_index: dict,
    tool_index: dict,
) -> tuple | None:
    """Return (dt, label, tb_row) or None.

    Prefer (session_id, tool_name, ts_minute) when session_id is present.
    When session_id is absent, fall back to (tool_name, ts_minute).
    Try exact minute, then ±1 minute for cross-minute tool calls.
    """
    tool = str(row.get('tool_name') or '').strip()
    dt = parse_ts(row.get('ts'))
    if not tool or dt is None:
        return None
    sid = str(row.get('session_id') or '').strip()
    base = session_base(sid)
    for off in _MINUTE_OFFSETS:
        mk = ts_minute(dt, off)
        if mk is None:
            continue
        if sid:
            items = []
            items.extend(session_index.get((sid, tool, mk), []))
            if base and base != sid:
                items.extend(session_index.get((base, tool, mk), []))
            found = _closest(items, dt)
            if found is not None:
                return found
        else:
            found = _closest(tool_index.get((tool, mk), []), dt)
            if found is not None:
                return found
    return None


def uncalibrated_score(row: dict):
    for key in ('compliance_score', 'uncalibrated_score', 'uncalibrated_accuracy'):
        val = row.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def join_rows(cs_rows: list, session_index: dict, tool_index: dict) -> list:
    out = []
    for row in cs_rows:
        rec = dict(row)
        uncal = uncalibrated_score(row)
        rec['uncalibrated_score'] = uncal
        matched = match_turn_behavior(row, session_index, tool_index)
        if matched is None:
            rec['outcome_label'] = rec.get('label')
            rec['label'] = None
            rec['labeled'] = False
            rec['label_source'] = None
            rec['label_compliance_disagreement'] = False
        else:
            _dt, label, tb = matched
            rec['label'] = float(label)
            rec['labeled'] = True
            rec['label_source'] = 'turn_behavior'
            rec['tb_ts'] = tb.get('ts')
            rec['tb_session_id'] = tb.get('session_id')
            rec['tb_turn_id'] = tb.get('turn_id')
            # Keep both signals. A red-flag (0.0) can still succeed (label=1.0).
            rec['label_compliance_disagreement'] = bool(
                uncal is not None and (
                    (float(label) >= 0.5 and float(uncal) <= 0.0)
                    or (float(label) < 0.5 and float(uncal) >= 1.0)
                )
            )
        out.append(rec)
    return out


def write_labeled_jsonl(path: Path, rows: list) -> None:
    lines = [json.dumps(r, default=str) for r in rows]
    text = ('\n'.join(lines) + '\n') if lines else ''
    _atomic_write_text(path, text)


def report_from(rows: list) -> dict:
    n_total = len(rows)
    labeled = [r for r in rows if r.get('label') is not None]
    n_labeled = len(labeled)
    n_unmatched = n_total - n_labeled
    if n_labeled:
        pos = sum(1 for r in labeled if float(r['label']) >= 0.5)
        label_pos_rate = pos / n_labeled
    else:
        label_pos_rate = None
    n_disagreement = sum(1 for r in rows if r.get('label_compliance_disagreement'))
    return {
        'ts': _now(),
        'n_total': n_total,
        'n_labeled': n_labeled,
        'n_unmatched': n_unmatched,
        'label_pos_rate': label_pos_rate,
        'n_disagreement': n_disagreement,
    }


def run(
    tb_path: Path | None = None,
    cs_path: Path | None = None,
    out_path: Path | None = None,
    report_path: Path | None = None,
) -> dict:
    tb_path = tb_path or TB_PATH
    cs_path = cs_path or CS_PATH
    out_path = out_path or OUT_PATH
    report_path = report_path or REPORT_PATH
    tb_rows = _load_jsonl(tb_path)
    cs_rows = _load_jsonl(cs_path)
    session_index, tool_index = build_tb_index(tb_rows)
    labeled_rows = join_rows(cs_rows, session_index, tool_index)
    try:
        write_labeled_jsonl(out_path, labeled_rows)
    except OSError as exc:
        return {'status': 'error', 'reason': str(exc), 'n_total': len(cs_rows), 'n_labeled': 0}
    report = report_from(labeled_rows)
    report['status'] = 'ok'
    report['tb_rows'] = len(tb_rows)
    report['output'] = str(out_path)
    try:
        _atomic_write(report_path, report)
        report['report'] = str(report_path)
    except OSError as exc:
        report['report_error'] = str(exc)
    return report


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='clb-'))
    try:
        tb = td / ('tb_' + uuid.uuid4().hex + '.jsonl')
        cs = td / ('cs_' + uuid.uuid4().hex + '.jsonl')
        out = td / 'labeled_compliance.jsonl'
        report = td / 'compliance-label-bridge-report.json'
        tb_rows = [
            {
                'ts': '2026-11-16T10:00:12.000000+00:00',
                'session_id': 'sess-a',
                'turn_id': 't1',
                'tool_name': 'read_file',
                'success': True,
            },
            {
                'ts': '2026-11-16T10:01:50.000000+00:00',
                'session_id': 'sess-b',
                'turn_id': 't2',
                'tool_name': 'terminal',
                'success': False,
            },
            {
                'ts': '2026-11-16T10:03:05.000000+00:00',
                'session_id': 'sess-c',
                'turn_id': 't3',
                'tool_name': 'web_search',
                'success': True,
            },
        ]
        cs_rows = [
            {
                'ts': '2026-11-16T10:00:40.000000+00:00',
                'session_id': 'sess-a',
                'tool_name': 'read_file',
                'compliance_score': 1.0,
            },
            {
                # no session_id (plugin shape); same minute as terminal fail
                'ts': '2026-11-16T10:01:10.000000+00:00',
                'tool_name': 'terminal',
                'compliance_score': 0.0,
                'flags': ['red'],
            },
            {
                'ts': '2026-11-16T11:00:00.000000+00:00',
                'session_id': 'sess-z',
                'tool_name': 'read_file',
                'compliance_score': 0.5,
            },
        ]
        tb.write_text(''.join(json.dumps(r) + '\n' for r in tb_rows), encoding='utf-8')
        cs.write_text(''.join(json.dumps(r) + '\n' for r in cs_rows), encoding='utf-8')
        result = run(tb, cs, out, report)
        assert result.get('n_total') == 3, result
        assert result.get('n_labeled') == 2, result
        assert result.get('n_unmatched') == 1, result
        written = _load_jsonl(out)
        assert len(written) == 3
        assert written[0]['label'] == 1.0
        assert written[0]['uncalibrated_score'] == 1.0
        assert written[0]['label_source'] == 'turn_behavior'
        assert written[0]['label_compliance_disagreement'] is False
        # pair 2: plugin row without session_id joins on (tool, minute);
        # success=false vs red-flag 0.0 — keep both, no min()
        assert written[1]['label'] == 0.0
        assert written[1]['uncalibrated_score'] == 0.0
        assert written[1].get('session_id') in (None, '') or 'session_id' not in cs_rows[1]
        # pair 3: unmatched
        assert written[2]['label'] is None
        assert written[2]['uncalibrated_score'] == 0.5
        assert written[2]['labeled'] is False
        # cross-minute: compliance at 10:03:02, tb at 10:02:50
        tb2 = td / 'tb2.jsonl'
        cs2 = td / 'cs2.jsonl'
        tb2.write_text(
            json.dumps({
                'ts': '2026-11-16T10:02:50.000000+00:00',
                'session_id': 'sess-x',
                'tool_name': 'skill_view',
                'success': True,
            }) + '\n',
            encoding='utf-8',
        )
        cs2.write_text(
            json.dumps({
                'ts': '2026-11-16T10:03:02.000000+00:00',
                'session_id': 'sess-x',
                'tool_name': 'skill_view',
                'compliance_score': 0.0,
            }) + '\n',
            encoding='utf-8',
        )
        r2 = run(tb2, cs2, td / 'out2.jsonl', td / 'rep2.json')
        assert r2.get('n_labeled') == 1, r2
        w2 = _load_jsonl(td / 'out2.jsonl')
        assert w2[0]['label'] == 1.0
        assert w2[0]['uncalibrated_score'] == 0.0
        assert w2[0]['label_compliance_disagreement'] is True
        # success=true must not be collapsed via min(label, compliance_binary)
        assert w2[0]['label'] != min(1.0, 0.0)
        print('[compliance-label-bridge] --self-test PASS')
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tb', default=str(TB_PATH))
    ap.add_argument('--cs', default=str(CS_PATH))
    ap.add_argument('--out', default=str(OUT_PATH))
    ap.add_argument('--report', default=str(REPORT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[compliance-label-bridge] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run(Path(args.tb), Path(args.cs), Path(args.out), Path(args.report))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()

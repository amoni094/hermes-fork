#!/usr/bin/env python3
"""Two conformal constructions for AI-text screening (eval-only)."""
from __future__ import annotations
import argparse, json, math, os, random, sys, tempfile, uuid, zlib
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'conformal-ai-text-screener.json'
ALPHA = 0.1


def score_text(text: str) -> float:
    raw = (text or '').encode('utf-8', errors='replace')
    if not raw:
        return 0.0
    comp = zlib.compress(raw, 9)
    ratio = len(comp) / max(1, len(raw))
    return max(0.0, min(1.0, 1.2 - ratio))


def p_value(s, calib):
    n = len(calib)
    if n == 0:
        return None
    ge = sum(1 for c in calib if c >= s)
    return (1.0 + ge) / (n + 1.0)


def screen(text, calib, alpha=ALPHA):
    if text is None:
        return {
            'status': 'error',
            'error': 'text is None',
            'flagged': None,
            'score': None,
            'p_value': None,
            'n_calibration': len(calib or []),
            'alpha': alpha,
            'ts': _now(),
        }
    cal = []
    for x in calib or []:
        try:
            cal.append(float(x))
        except (TypeError, ValueError):
            continue
    n = len(cal)
    if n == 0:
        return {
            'status': 'insufficient_data',
            'flagged': None,
            'score': None,
            'p_value': None,
            'n_calibration': 0,
            'alpha': alpha,
            'ts': _now(),
        }
    s = score_text(str(text))
    pv = p_value(s, cal)
    return {
        'status': 'ok',
        'flagged': bool(pv is not None and pv <= alpha),
        'score': s,
        'p_value': pv,
        'n_calibration': n,
        'alpha': alpha,
        'ts': _now(),
    }


def load_calib():
    p = CACHE / 'ai-text-calib.json'
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
        return list(data.get('scores') or data.get('calibration') or [])
    except (OSError, json.JSONDecodeError):
        return []


def _self_test() -> int:
    empty = screen('hello', [])
    assert empty['status'] == 'insufficient_data'
    none_r = screen(None, [0.1, 0.2, 0.3])
    assert none_r['status'] == 'error'
    cal = [score_text(f'plain human note {i}') for i in range(20)]
    r = screen('plain human note 99', cal, alpha=0.1)
    assert r['status'] == 'ok'
    assert r['p_value'] is not None
    tmp = _temp_out('screener')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[conformal-ai-text-screener] --self-test PASS pv={:.3f} flagged={}'.format(r['p_value'], r['flagged']))
    return 0


def _session_texts(limit=12):
    sess = CACHE.parent / 'sessions'
    texts = []
    if not sess.exists():
        return texts
    paths = sorted(sess.glob('*.jsonl'))[-6:]
    for path in paths:
        try:
            for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get('role') not in ('assistant', 'user'):
                    continue
                content = rec.get('content')
                if isinstance(content, str) and content.strip():
                    texts.append(content[:4000])
                if len(texts) >= limit:
                    return texts
        except OSError:
            continue
    return texts


def run_batch():
    cal = load_calib()
    texts = _session_texts()
    if not cal:
        return {
            'status': 'insufficient_data',
            'n_calibration': 0,
            'n_texts': len(texts),
            'ts': _now(),
        }
    if not texts:
        return {
            'status': 'insufficient_data',
            'n_calibration': len(cal),
            'n_texts': 0,
            'ts': _now(),
        }
    results = []
    n_flag = 0
    for t in texts:
        r = screen(t, cal)
        results.append({k: r.get(k) for k in ('status', 'flagged', 'score', 'p_value')})
        if r.get('flagged'):
            n_flag += 1
    out = {
        'status': 'ok',
        'ts': _now(),
        'n_calibration': len(cal),
        'n_texts': len(texts),
        'n_flagged': n_flag,
        'alpha': ALPHA,
        'results': results,
    }
    _atomic_write(OUT_PATH, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--text', default='')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[conformal-ai-text-screener] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        if args.text:
            cal = load_calib()
            r = screen(args.text, cal)
            if r.get('status') == 'ok':
                _atomic_write(OUT_PATH, r)
            print(json.dumps(r))
        else:
            r = run_batch()
            print(json.dumps({k: r.get(k) for k in r if k != 'results'}))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()

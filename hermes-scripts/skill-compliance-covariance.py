#!/usr/bin/env python3
"""Bootstrap covariance / confidence bands for SAFE AI compliance scores."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    # PATH STRIPPING RULE: strip profiles/X suffix
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
if not _hermes_profile:
    _raw = os.environ.get('HERMES_HOME', '').strip()
    if _raw:
        _p = Path(_raw)
        if _p.parent.name == 'profiles':
            _hermes_profile = _p.name
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base
)

CACHE = _hermes_root / 'cache'
SCORES_PATH = CACHE / 'compliance-scores.jsonl'
OUT_PATH = CACHE / 'compliance-covariance.json'
METRICS_PATH = CACHE / 'compliance-metrics.json'
DB_PATH = CACHE / 'compliance-covariance.db'
LOG_PATH = CACHE / 'compliance-covariance-log.jsonl'

METRICS = ('accuracy', 'explainability', 'robustness')
WINDOW = 100
B_DEFAULT = 500
N_MIN = 2


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(str(path), 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, default=str) + '\n')


def load_triples(path: Path, window: int = WINDOW) -> list[tuple[float, float, float]]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []
    rows: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        try:
            a = float(obj['accuracy'])
            e = float(obj['explainability'])
            r = float(obj['robustness'])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(a) and math.isfinite(e) and math.isfinite(r)):
            continue
        rows.append((a, e, r))
    if window and window > 0:
        return rows[-window:]
    return rows


def sample_mean(rows: list[tuple[float, float, float]]) -> dict[str, float]:
    n = len(rows)
    if n == 0:
        return {k: 0.0 for k in METRICS}
    acc = [0.0, 0.0, 0.0]
    for row in rows:
        acc[0] += row[0]
        acc[1] += row[1]
        acc[2] += row[2]
    return {METRICS[i]: acc[i] / n for i in range(3)}


def sample_cov(rows: list[tuple[float, float, float]]) -> list[list[float]]:
    n = len(rows)
    C = [[0.0, 0.0, 0.0] for _ in range(3)]
    if n < N_MIN:
        return C
    cols = (
        [row[0] for row in rows],
        [row[1] for row in rows],
        [row[2] for row in rows],
    )
    for i in range(3):
        for j in range(3):
            try:
                C[i][j] = float(statistics.covariance(cols[i], cols[j]))
            except statistics.StatisticsError:
                C[i][j] = 0.0
    return C


def paired_bootstrap_cov(
    rows: list[tuple[float, float, float]],
    B: int = B_DEFAULT,
    rng: random.Random | None = None,
) -> list[list[float]]:
    """Mean of paired-bootstrap sample covariance matrices (B replicas)."""
    n = len(rows)
    if n < N_MIN:
        return [[0.0, 0.0, 0.0] for _ in range(3)]
    rng = rng or random.Random()
    acc = [[0.0, 0.0, 0.0] for _ in range(3)]
    used = 0
    for _ in range(max(1, int(B))):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        C_b = sample_cov(sample)
        used += 1
        for i in range(3):
            for j in range(3):
                acc[i][j] += C_b[i][j]
    if used == 0:
        return sample_cov(rows)
    return [[acc[i][j] / used for j in range(3)] for i in range(3)]


def mat_det3(C: list[list[float]]) -> float:
    a, b, c = C[0]
    d, e, f = C[1]
    g, h, i = C[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def independence_cov(C: list[list[float]]) -> list[list[float]]:
    return [
        [C[0][0], 0.0, 0.0],
        [0.0, C[1][1], 0.0],
        [0.0, 0.0, C[2][2]],
    ]


def band_widths(C: list[list[float]]) -> dict[str, float]:
    out = {}
    for i, name in enumerate(METRICS):
        v = C[i][i]
        out[name] = math.sqrt(v) if v > 0.0 else 0.0
    return out


def det_ratio(C: list[list[float]]) -> tuple[float, float, list[str]]:
    """Return (ratio, det_C, warnings). C_independence = diag(variances)."""
    warnings: list[str] = []
    det_c = mat_det3(C)
    if det_c <= 0.0:
        warnings.append(
            f'det(C)={det_c:.6g} <= 0 (semi-definite ok); continuing'
        )
    C_ind = independence_cov(C)
    det_ind = mat_det3(C_ind)
    if det_ind <= 0.0:
        warnings.append(
            f'det(C_independence)={det_ind:.6g} <= 0; det_ratio defaulting to 1.0'
        )
        ratio = 1.0
    else:
        ratio = det_c / det_ind
        if not math.isfinite(ratio):
            warnings.append('det_ratio non-finite; defaulting to 1.0')
            ratio = 1.0
    return float(ratio), float(det_c), warnings


def compute(
    rows: list[tuple[float, float, float]],
    B: int = B_DEFAULT,
    rng: random.Random | None = None,
) -> dict:
    n = len(rows)
    mean = sample_mean(rows)
    C = paired_bootstrap_cov(rows, B=B, rng=rng)
    bands = band_widths(C)
    ratio, _det_c, warnings = det_ratio(C)
    rec = {
        'ts': _now(),
        'status': 'insufficient_data' if n < N_MIN else 'ok',
        'n_samples': int(n),
        'mean': mean,
        'covariance': C,
        'band_widths': bands,
        'det_ratio': ratio,
    }
    if warnings:
        for w in warnings:
            print(f'WARN: {w}', file=sys.stderr)
    return rec


def persist_sqlite(db_path: Path, rec: dict, rows: list) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS compliance_vectors ('
            'id INTEGER PRIMARY KEY, ts TEXT, accuracy REAL, '
            'explainability REAL, robustness REAL)'
        )
        conn.execute(
            'CREATE TABLE IF NOT EXISTS bootstrap_runs ('
            'id INTEGER PRIMARY KEY, ts TEXT, n_samples INTEGER, '
            'mean_json TEXT, cov_json TEXT, band_widths_json TEXT, '
            'det_ratio REAL, aggregator TEXT)'
        )
        ts = rec.get('ts') or _now()
        if rows:
            conn.executemany(
                'INSERT INTO compliance_vectors(ts, accuracy, explainability, robustness) '
                'VALUES (?,?,?,?)',
                [(ts, a, e, r) for (a, e, r) in rows[-WINDOW:]],
            )
        conn.execute(
            'INSERT INTO bootstrap_runs(ts, n_samples, mean_json, cov_json, '
            'band_widths_json, det_ratio, aggregator) VALUES (?,?,?,?,?,?,?)',
            (
                ts,
                int(rec.get('n_samples') or 0),
                json.dumps(rec.get('mean') or {}),
                json.dumps(rec.get('covariance') or []),
                json.dumps(rec.get('band_widths') or {}),
                float(rec.get('det_ratio') or 0.0),
                'paired_bootstrap_window%d' % WINDOW,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def metrics_payload(rec: dict) -> dict:
    return {
        'ts': rec.get('ts') or _now(),
        'status': rec.get('status'),
        'n_samples': rec.get('n_samples'),
        'point_estimate': rec.get('mean'),
        'band_widths': rec.get('band_widths'),
        'covariance': rec.get('covariance'),
        'det_ratio': rec.get('det_ratio'),
        'aggregator': 'paired_bootstrap_window%d' % WINDOW,
    }


def log_record(rec: dict) -> dict:
    bands = rec.get('band_widths') or {}
    widths = [float(bands.get(k, 0.0) or 0.0) for k in METRICS]
    mean_bw = (sum(widths) / 3.0) if widths else 0.0
    return {
        'ts': rec.get('ts') or _now(),
        'det_ratio': float(rec.get('det_ratio') or 0.0),
        'mean_band_width': float(mean_bw),
        'n_samples': int(rec.get('n_samples') or 0),
    }


def cholesky3(A: list[list[float]]) -> list[list[float]]:
    L = [[0.0, 0.0, 0.0] for _ in range(3)]
    for i in range(3):
        for j in range(i + 1):
            s = A[i][j]
            for k in range(j):
                s -= L[i][k] * L[j][k]
            if i == j:
                L[i][j] = math.sqrt(max(s, 0.0))
            else:
                L[i][j] = (s / L[j][j]) if L[j][j] else 0.0
    return L


def mvn3(L: list[list[float]], rng: random.Random) -> tuple[float, float, float]:
    z = [rng.gauss(0.0, 1.0) for _ in range(3)]
    x = [L[i][0] * z[0] + L[i][1] * z[1] + L[i][2] * z[2] for i in range(3)]
    return (x[0], x[1], x[2])


def _self_test() -> int:
    rng = random.Random(42)
    # True Cov[a,e] = 0.3, others independent, unit variances
    Sigma = [
        [1.0, 0.3, 0.0],
        [0.3, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    L = cholesky3(Sigma)
    triples = [mvn3(L, rng) for _ in range(100)]
    rec = compute(triples, B=B_DEFAULT, rng=random.Random(123))
    cov_ae = rec['covariance'][0][1]
    assert 0.20 <= cov_ae <= 0.40, f'Cov[a,e]={cov_ae:.6f} not in [0.20, 0.40]'
    assert rec['n_samples'] == 100
    for k in METRICS:
        assert k in rec['mean']
        assert k in rec['band_widths']
        assert rec['band_widths'][k] >= 0.0
    assert len(rec['covariance']) == 3
    assert all(len(row) == 3 for row in rec['covariance'])
    # Kill-test: singular / PSD-boundary matrix — warn, do not abort
    singular = [(0.5, 0.5, 0.5)] * 10
    rec_s = compute(singular, B=20, rng=random.Random(1))
    assert rec_s['n_samples'] == 10
    # Isolated writes (never production OUT_PATH)
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    tmp_log = LOG_PATH.with_name(
        LOG_PATH.stem + '_test_' + uuid.uuid4().hex + LOG_PATH.suffix
    )
    try:
        _atomic_write(tmp, rec)
        loaded = json.loads(tmp.read_text(encoding='utf-8'))
        assert loaded['n_samples'] == 100
        _append_jsonl(tmp_log, log_record(rec))
        log_line = json.loads(tmp_log.read_text(encoding='utf-8').strip().splitlines()[-1])
        assert 'det_ratio' in log_line and 'mean_band_width' in log_line
        tmp_db = DB_PATH.with_name(DB_PATH.stem + '_test_' + uuid.uuid4().hex + DB_PATH.suffix)
        tmp_metrics = METRICS_PATH.with_name(
            METRICS_PATH.stem + '_test_' + uuid.uuid4().hex + METRICS_PATH.suffix
        )
        try:
            persist_sqlite(tmp_db, rec, triples)
            conn = sqlite3.connect(str(tmp_db), timeout=30)
            try:
                conn.execute('PRAGMA journal_mode=WAL')
                nvec = conn.execute('SELECT COUNT(*) FROM compliance_vectors').fetchone()[0]
                nrun = conn.execute('SELECT COUNT(*) FROM bootstrap_runs').fetchone()[0]
                assert nvec == 100
                assert nrun == 1
            finally:
                conn.close()
            _atomic_write(tmp_metrics, metrics_payload(rec))
            m = json.loads(tmp_metrics.read_text(encoding='utf-8'))
            assert m['aggregator'].startswith('paired_bootstrap')
            assert 'point_estimate' in m
        finally:
            tmp_db.unlink(missing_ok=True)
            Path(str(tmp_db) + '-wal').unlink(missing_ok=True)
            Path(str(tmp_db) + '-shm').unlink(missing_ok=True)
            tmp_metrics.unlink(missing_ok=True)
            tmp_metrics.with_suffix('.lock').unlink(missing_ok=True)
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix('.lock').unlink(missing_ok=True)
        tmp_log.unlink(missing_ok=True)
        tmp_log.with_suffix('.lock').unlink(missing_ok=True)
        tmp.with_name(tmp.name + '.tmp').unlink(missing_ok=True)
    # Missing file / malformed JSON: no crash
    missing = load_triples(Path('/nonexistent/compliance-scores-missing.jsonl'))
    assert missing == []
    empty_rec = compute([], B=10)
    assert empty_rec['n_samples'] == 0
    assert empty_rec.get('det_ratio') == 1.0 or empty_rec['n_samples'] == 0
    print(json.dumps({
        'status': 'ok',
        'self_test': True,
        'cov_ae': cov_ae,
        'det_ratio': rec['det_ratio'],
    }))
    return 0


def run(B: int = B_DEFAULT) -> dict:
    rows = load_triples(SCORES_PATH, window=WINDOW)
    rec = compute(rows, B=B, rng=random.Random())
    try:
        _atomic_write(OUT_PATH, rec)
        _atomic_write(METRICS_PATH, metrics_payload(rec))
    except Exception as exc:
        print(f'WARN: failed to write json: {exc}', file=sys.stderr)
    if rec['n_samples'] >= N_MIN:
        try:
            persist_sqlite(DB_PATH, rec, rows)
        except Exception as exc:
            print(f'WARN: failed to write sqlite: {exc}', file=sys.stderr)
        try:
            _append_jsonl(LOG_PATH, log_record(rec))
        except Exception as exc:
            print(f'WARN: failed to append {LOG_PATH}: {exc}', file=sys.stderr)
    print(json.dumps(rec))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Paired-bootstrap covariance of SAFE AI compliance scores'
    )
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true', help='compute over live scores jsonl')
    ap.add_argument('--B', type=int, default=B_DEFAULT)
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[skill-compliance-covariance] --self-test FAIL: {exc}')
            return 1
    # default to --run (cron may omit args)
    try:
        run(B=max(1, int(args.B)))
        return 0
    except Exception as exc:
        # fail-open for cron
        print(f'ERROR: {exc}', file=sys.stderr)
        return 0


if __name__ == '__main__':
    sys.exit(main())

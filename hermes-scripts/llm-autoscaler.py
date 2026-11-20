#!/usr/bin/env python3
"""Cost-latency Pareto advisor for local LLM backend selection.

Live path: per-model inter-turn latency from token-usage.jsonl (n>=MIN_OBS).
Fallback: llm-backend-profiles.json. Never invents backends when both are empty.
"""
from __future__ import annotations
import argparse, json, os, sys, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', 'fork').strip()
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


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base
CACHE = _hermes_root / 'cache'
LOGS = _hermes_root / 'logs'

OUT_PATH = CACHE / 'autoscaler-recommendation.json'
PROFILES = CACHE / 'llm-backend-profiles.json'
TOKEN_USAGE = LOGS / 'token-usage.jsonl'
SKILL_LATENCY = CACHE / 'skill-latency.jsonl'
SKILL_STATS = CACHE / 'skill-latency-stats.json'

MIN_OBS = 100
MAX_INTER_MS = 600000.0  # 10 min; drop session gaps

# Relative cost units matching the static profile scale. Observed models only.
COST_HINTS = (
    ('haiku', 0.4),
    ('fast', 0.4),
    ('sonnet', 2.2),
    ('opus', 3.0),
    ('premium', 2.2),
    ('gpt-4', 2.2),
    ('grok', 1.0),
    ('local', 0.05),
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def _parse_ts(raw) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _percentile(sorted_vals, q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    idx = int(q * (len(sorted_vals) - 1))
    idx = max(idx, 0)
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return float(sorted_vals[idx])


def cost_for(name: str, profile_costs: dict | None = None) -> float:
    key = str(name or '').strip()
    if profile_costs and key in profile_costs:
        return float(profile_costs[key])
    low = key.lower()
    if profile_costs:
        for pk, pv in profile_costs.items():
            if pk.lower() in low or low in pk.lower():
                return float(pv)
    for needle, cost in COST_HINTS:
        if needle in low:
            return float(cost)
    return 1.0


def load_profiles(path: Path | None = None):
    p = path or PROFILES
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        items = data if isinstance(data, list) else data.get('backends') or data.get('profiles')
        if isinstance(items, list) and items:
            return items
    except (OSError, json.JSONDecodeError):
        pass
    return []


def profile_cost_map(profiles) -> dict:
    out = {}
    for b in profiles or []:
        name = b.get('name') or b.get('id')
        if not name:
            continue
        try:
            out[str(name)] = float(b.get('cost') or b.get('usd') or 1.0)
        except (TypeError, ValueError):
            out[str(name)] = 1.0
    return out


def load_live_backends(token_path: Path | None = None, min_obs: int = MIN_OBS,
                       profiles=None):
    """Inter-turn latency per model from token-usage.jsonl."""
    path = token_path or TOKEN_USAGE
    if not path.exists():
        return [], 0
    prev = {}
    by_model = defaultdict(list)
    n_rows = 0
    try:
        with path.open(encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                n_rows += 1
                model = rec.get('model') or rec.get('model_id') or ''
                sid = rec.get('session_id') or ''
                ts = _parse_ts(rec.get('ts'))
                if not model or not sid or ts is None:
                    continue
                key = (str(sid), str(model))
                if key in prev:
                    dt_ms = (ts - prev[key]).total_seconds() * 1000.0
                    if 0.0 < dt_ms < MAX_INTER_MS:
                        by_model[str(model)].append(dt_ms)
                prev[key] = ts
    except OSError:
        return [], n_rows
    costs = profile_cost_map(profiles)
    backends = []
    n_lat = 0
    for name, vals in sorted(by_model.items()):
        if len(vals) < 5:
            continue
        vals_sorted = sorted(vals)
        n_lat += len(vals_sorted)
        backends.append({
            'name': name,
            'latency_ms': _percentile(vals_sorted, 0.95),
            'mean_ms': float(sum(vals_sorted) / len(vals_sorted)),
            'n': len(vals_sorted),
            'cost': cost_for(name, costs),
        })
    if n_lat < min_obs or not backends:
        return [], n_rows
    return backends, n_rows


def skill_latency_load(stats_path: Path | None = None, jsonl_path: Path | None = None) -> dict:
    stats_path = stats_path or SKILL_STATS
    jsonl_path = jsonl_path or SKILL_LATENCY
    n = 0
    p95s = []
    if stats_path.exists():
        try:
            data = json.loads(stats_path.read_text(encoding='utf-8'))
            skills = data.get('skills') if isinstance(data, dict) else {}
            if isinstance(skills, dict):
                for rec in skills.values():
                    if not isinstance(rec, dict):
                        continue
                    try:
                        n += int(rec.get('n') or 0)
                    except (TypeError, ValueError):
                        pass
                    try:
                        p95s.append(float(rec.get('p95_ms')))
                    except (TypeError, ValueError):
                        continue
        except (OSError, json.JSONDecodeError):
            pass
    if n == 0 and jsonl_path.exists():
        try:
            with jsonl_path.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(rec, dict) and rec.get('elapsed_ms') is not None:
                        n += 1
        except OSError:
            pass
    overall = float(sum(p95s) / len(p95s)) if p95s else None
    return {'n': n, 'mean_skill_p95_ms': overall}


def pareto(backends):
    pts = []
    for b in backends:
        name = b.get('name') or b.get('id')
        try:
            lat = float(b.get('latency_ms') or b.get('latency') or 1e9)
        except (TypeError, ValueError):
            lat = 1e9
        try:
            cost = float(b.get('cost') or b.get('usd') or 1e9)
        except (TypeError, ValueError):
            cost = 1e9
        extra = {k: b[k] for k in ('n', 'mean_ms') if k in b}
        pts.append({'name': str(name), 'latency_ms': lat, 'cost': cost, **extra})
    front = []
    for p in pts:
        dominated = False
        for q in pts:
            if q is p:
                continue
            if q['cost'] <= p['cost'] and q['latency_ms'] <= p['latency_ms'] and (
                q['cost'] < p['cost'] or q['latency_ms'] < p['latency_ms']
            ):
                dominated = True
                break
        if not dominated:
            front.append(p)
    front.sort(key=lambda x: (x['cost'] + x['latency_ms'] / 1000.0))
    return pts, front


def recommend(backends, source: str = 'profiles', extra=None):
    extra = extra or {}
    if not backends:
        return {
            'ts': _now(),
            'status': 'insufficient_data',
            'recommended_backend': None,
            'reason': 'no live token-usage models and llm-backend-profiles.json missing or empty',
            'pareto_rank': None,
            'pareto_front': [],
            'n_backends': 0,
            'source': source,
            **extra,
        }
    pts, front = pareto(backends)
    rec = front[0] if front else (pts[0] if pts else {'name': 'none', 'latency_ms': 0, 'cost': 0})
    ranked = []
    for i, p in enumerate(front):
        ranked.append({**p, 'pareto_rank': i})
    return {
        'ts': _now(),
        'status': 'ok',
        'recommended_backend': rec['name'],
        'reason': f'min scalarised cost+p95_latency among Pareto front ({source})',
        'pareto_rank': 0,
        'pareto_front': ranked,
        'n_backends': len(pts),
        'source': source,
        **extra,
    }


def run(token_path: Path | None = None, profiles_path: Path | None = None,
        min_obs: int = MIN_OBS, stats_path: Path | None = None,
        jsonl_path: Path | None = None) -> dict:
    profiles = load_profiles(profiles_path)
    load = skill_latency_load(stats_path, jsonl_path)
    extra = {
        'skill_latency_n': load['n'],
        'mean_skill_p95_ms': load['mean_skill_p95_ms'],
    }
    live, n_rows = load_live_backends(token_path, min_obs=min_obs, profiles=profiles)
    extra['token_usage_rows'] = n_rows
    if live:
        extra['n_obs'] = sum(int(b.get('n') or 0) for b in live)
        return recommend(live, source='live_token_usage', extra=extra)
    extra['n_obs'] = 0
    return recommend(profiles, source='profiles', extra=extra)


def _self_test() -> int:
    backends = [
        {'name': 'a', 'latency_ms': 100, 'cost': 5.0},
        {'name': 'b', 'latency_ms': 500, 'cost': 0.1},
        {'name': 'c', 'latency_ms': 900, 'cost': 4.0},
    ]
    r = recommend(backends, source='synthetic')
    names = {p['name'] for p in r['pareto_front']}
    assert 'c' not in names
    assert r['recommended_backend'] in names

    empty = recommend([], source='profiles')
    assert empty['status'] == 'insufficient_data'
    assert empty['recommended_backend'] is None

    import tempfile, shutil
    td = Path(tempfile.mkdtemp(prefix='autoscaler-'))
    try:
        tok = td / ('token-usage_test_' + uuid.uuid4().hex + '.jsonl')
        # two models, inter-turn latencies
        rows = []
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        for i in range(20):
            ts = t0.timestamp() + i * 2.0  # 2s turns -> 2000ms
            iso = datetime.fromtimestamp(ts, tz=UTC).isoformat()
            rows.append({'ts': iso, 'session_id': 's1', 'model': 'haiku-test', 'prompt_tokens': 1, 'completion_tokens': 1})
        for i in range(20):
            ts = t0.timestamp() + i * 10.0  # 10s turns
            iso = datetime.fromtimestamp(ts, tz=UTC).isoformat()
            rows.append({'ts': iso, 'session_id': 's2', 'model': 'sonnet-test', 'prompt_tokens': 1, 'completion_tokens': 1})
        tok.write_text('\n'.join(json.dumps(x) for x in rows) + '\n', encoding='utf-8')
        live, n = load_live_backends(tok, min_obs=10, profiles=[])
        assert n == 40, n
        assert len(live) == 2, live
        rec = recommend(live, source='live_token_usage')
        assert rec['recommended_backend'] == 'haiku-test', rec
        # malformed + empty
        bad = td / 'bad.jsonl'
        bad.write_text('not-json\n{}\n', encoding='utf-8')
        live2, _ = load_live_backends(bad, min_obs=1)
        assert live2 == []
        missing, nmiss = load_live_backends(td / 'nope.jsonl', min_obs=1)
        assert missing == [] and nmiss == 0
        out = td / ('autoscaler-recommendation_test_' + uuid.uuid4().hex + '.json')
        _atomic_write(out, rec)
        loaded = json.loads(out.read_text(encoding='utf-8'))
        assert loaded['recommended_backend'] == rec['recommended_backend']
        json.loads(json.dumps(run.__doc__ or ''))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    home = _hermes_home()
    os.environ['HERMES_HOME'] = str(home / 'profiles' / 'fork')
    assert _hermes_home() == home
    os.environ['HERMES_HOME'] = str(home)
    print(json.dumps({
        'status': 'ok',
        'self_test': True,
        'recommended_backend': r['recommended_backend'],
        'front': sorted(names),
    }))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true', help='cron default; same as no flags')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(json.dumps({'status': 'error', 'self_test': True, 'reason': str(exc)}))
            return 1
    try:
        r = run()
        _atomic_write(OUT_PATH, r)
        print(json.dumps(r))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        return 0


if __name__ == '__main__':
    sys.exit(main())

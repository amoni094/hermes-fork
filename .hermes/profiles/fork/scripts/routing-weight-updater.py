#!/usr/bin/env python3
"""
routing-weight-updater.py — FTRL routing weight feedback loop closure.

Reads routing-calibration.jsonl (written by memory-query-router.py via
_log_routing_decision), computes per-route success rates over the last 48h,
and applies an EMA (FTRL-style) weight update to routing-weights.json.

FTRL theory: w_{t+1} = argmin_w [sum loss_s(w) + R(w)]
EMA approximation: new_weight = old_weight * 0.9 + success_rate * 0.1
Reward signal: result_count > 0 (route returned at least one result)
Weights clamped to [0.1, 2.0].

Mirrors the pattern in calibration-threshold-updater.py (Shalev-Shwartz Ch 11).

Source: Memory in LLM Era v3 (arXiv:2604.01707) — bottleneck #2 closure.
"""
import json
import math
import os
import time
from pathlib import Path
from collections import defaultdict

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
LOG_PATH = _hermes_root / "cache" / "routing-calibration.jsonl"
WEIGHTS_PATH = _hermes_root / "cache" / "routing-weights.json"

WINDOW_SECONDS = 48 * 3600  # 48h lookback
WEIGHT_MIN = 0.1
WEIGHT_MAX = 2.0
EMA_DECAY = 0.9    # weight on prior run
EMA_NEW = 0.1     # weight on new observation
MIN_SAMPLES = 5   # minimum entries before updating (avoid noise from tiny samples)

# O1: Regret tracking (Borodin & El-Yaniv, Online Computation §2.1)
# Cumulative regret vs uniform baseline: R_T = sum_t [loss(ALG,t) - loss(UNI,t)]
# Positive regret = ALG worse than uniform; negative = ALG better.
# Stored in regret-log.jsonl for daily alarm inspection.
REGRET_LOG_PATH = _hermes_root / "cache" / "routing-regret-log.jsonl"

_DEFAULT_ROUTES = ['semantic', 'temporal', 'relational', 'exact']

# TD(lambda) (Sutton-Barto): e_{t+1} = (gamma * lambda) * e_t + 1_{observed}
GAMMA_TD = 0.95
LAMBDA_TD = 0.8
TRACE_DECAY = GAMMA_TD * LAMBDA_TD  # 0.76
EPS_RATIO = 1e-9
NAT_GRAD_ETA = 0.1  # Dirichlet-Multinomial natural-gradient mix


def natural_gradient_dirichlet(
    weights: dict,
    empirical_counts: dict,
    eta: float = NAT_GRAD_ETA,
) -> dict:
    """e-flat natural gradient for Dirichlet-Multinomial (Amari).

    Fisher I is diagonal; nat-grad in mean coordinates is p_emp - p_model
    (score/count). Hard core: coordinate-free — scaling all empirical counts
    by c does not change the update direction.
    """
    keys = list(weights)
    wsum = sum(max(1e-12, float(weights[k])) for k in keys) or 1.0
    esum = sum(max(0.0, float(empirical_counts.get(k, 0.0))) for k in keys)
    out = {}
    for k in keys:
        p_model = max(1e-12, float(weights[k])) / wsum
        p_emp = (float(empirical_counts.get(k, 0.0)) / esum) if esum > 0 else p_model
        stepped = float(weights[k]) + eta * (p_emp - p_model)
        out[k] = max(WEIGHT_MIN, min(WEIGHT_MAX, stepped))
    return out


def update_eligibility_traces(traces: dict, observed_routes: list, decay: float = TRACE_DECAY) -> dict:
    """Decay all traces, then add 1 to observed routes. Hard core: idle decay is (gamma*lambda)^t."""
    out = {}
    for k, v in traces.items():
        if k == "_meta":
            continue
        try:
            out[k] = float(v) * decay
        except (TypeError, ValueError):
            continue
    for r in observed_routes:
        out[r] = out.get(r, 0.0) + 1.0
    out["_meta"] = {"decay": decay, "gamma": GAMMA_TD, "lambda": LAMBDA_TD}
    return out


def eligibility_idle_decay(e0: float, t: int, decay: float = TRACE_DECAY) -> float:
    return float(e0) * (decay ** int(t))


def competitive_ratio_last_24h(log_path: Path, now: float, weights: dict | None = None) -> dict:
    """ALG loss vs hindsight-best fixed route OPT over 24h.

    Competitive ratio = (ALG_loss + eps) / (OPT_loss + eps) — always finite.
    achieved_opt is ALWAYS False: online ALG cannot claim offline OPT.
    """
    cutoff = now - 24 * 3600
    per_route = defaultdict(lambda: {"n": 0, "loss": 0.0})
    alg_n = 0
    alg_loss = 0.0
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            ts = float(row.get("ts", 0) or 0)
            if ts < cutoff:
                continue
            route = row.get("route") or ""
            if not route:
                continue
            result_count = int(row.get("result_count", -1) or -1)
            loss = 0.0 if result_count > 0 else 1.0
            per_route[route]["n"] += 1
            per_route[route]["loss"] += loss
            alg_n += 1
            alg_loss += loss
    # Offline OPT: hindsight best *fixed* route (lowest loss rate with n>0).
    opt_loss = None
    opt_route = None
    for route, st in per_route.items():
        if st["n"] <= 0:
            continue
        # Scale route loss to ALG's n via loss rate (expert-advice comparator).
        rate = st["loss"] / st["n"]
        scaled = rate * alg_n
        if opt_loss is None or scaled < opt_loss:
            opt_loss = scaled
            opt_route = route
    if opt_loss is None:
        opt_loss = 0.0
    # Additive +1 smoothing: finite even when OPT_loss=0; never 1e9-scale eps ratios.
    ratio = (alg_loss + 1.0) / (opt_loss + 1.0)
    finite = math.isfinite(ratio)
    return {
        "ts": now,
        "window_hours": 24,
        "alg_n": alg_n,
        "alg_loss": round(alg_loss, 4),
        "opt_loss": round(float(opt_loss), 4),
        "opt_route": opt_route,
        "competitive_ratio": round(ratio, 6) if finite else None,
        "finite": finite,
        "achieved_opt": False,
        "note": "Offline OPT is a hindsight comparator only; ALG did not achieve OPT.",
    }


def _load_known_routes(weights_path: Path, log_path: Path) -> list:
    """Dynamic route discovery.

    Priority:
    1. Keys already present in routing-weights.json (persisted from prior runs).
    2. Fall back to _DEFAULT_ROUTES if the file is absent or unreadable.
    3. Any route key seen in the calibration log that is NOT yet known is
       zero-initialised (weight=0.0) so FTRL can learn from incoming data.
    """
    known: list = list(_DEFAULT_ROUTES)

    # 1. Seed from existing weights file
    if weights_path.exists():
        try:
            stored = json.loads(weights_path.read_text())
            if isinstance(stored, dict):
                for k in stored:
                    if k not in known:
                        known.append(k)
        except Exception as _adv_e:
            import sys as _sys
            print(f"[advisory:routing-weight-updater] {type(_adv_e).__name__}: {_adv_e} — fall back to defaults", file=_sys.stderr)

    # 2. Discover any new routes from the calibration log
    if log_path.exists():
        try:
            for line in log_path.read_text().splitlines():
                try:
                    row = json.loads(line)
                    route = row.get('route', '')
                    if route and route not in known:
                        known.append(route)
                except Exception:
                    continue
        except Exception as _ae:
            import sys as _sys
            print(f"[advisory:routing-weight-updater] {type(_ae).__name__}: {_ae}", file=_sys.stderr)

    return known


def main():
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # ------------------------------------------------------------------ #
    # Discover known routes dynamically (replaces hardcoded KNOWN_ROUTES)
    # ------------------------------------------------------------------ #
    KNOWN_ROUTES = _load_known_routes(WEIGHTS_PATH, LOG_PATH)

    # ------------------------------------------------------------------ #
    # Load calibration log
    # ------------------------------------------------------------------ #
    route_stats = defaultdict(lambda: {'total': 0, 'successes': 0})

    if not LOG_PATH.exists():
        print('No routing calibration log found — using defaults')
    else:
        for line in LOG_PATH.read_text().splitlines():
            try:
                row = json.loads(line)
                ts = float(row.get('ts', 0))
                if ts < cutoff:
                    continue
                route = row.get('route', '')
                if not route:
                    continue
                result_count = int(row.get('result_count', -1))
                route_stats[route]['total'] += 1
                if result_count > 0:
                    route_stats[route]['successes'] += 1
            except Exception:
                continue

    # Supplement with skill-yield-tracker data from state.db (L337 gap closure)
    # skill_yields table: skill_name, invocations, successes → maps to route 'semantic' proxy
    # Only reads if table exists and has rows; advisory supplement to calibration log data.
    _STATE_DB = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / (
        ("profiles/" + os.environ.get("HERMES_PROFILE", "") + "/")
        if os.environ.get("HERMES_PROFILE", "") else ""
    ) / "state.db"
    try:
        import sqlite3 as _sqlite3
        if _STATE_DB.exists():
            _con = _sqlite3.connect(f"file:{_STATE_DB}?mode=ro", uri=True, timeout=3)
            try:
                _rows = _con.execute(
                    "SELECT route, COUNT(*) as n, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as suc "
                    "FROM skill_yields WHERE ts > ? GROUP BY route",
                    (cutoff,)
                ).fetchall()
                for _route, _n, _suc in _rows:
                    if _route and _n > 0:
                        route_stats[_route]['total'] += _n
                        route_stats[_route]['successes'] += int(_suc or 0)
                if _rows:
                    print(f'[yield-supplement] Added {sum(r[1] for r in _rows)} yield rows from state.db')
            except _sqlite3.OperationalError:
                pass  # Table may not exist yet; ignore
            finally:
                _con.close()
    except Exception as _adv_e:
        import sys as _sys
        print(f"[advisory:routing-weight-updater] {type(_adv_e).__name__}: {_adv_e} — yield supplement is advisory; never block", file=_sys.stderr)

    # ------------------------------------------------------------------ #
    # Load existing weights (EMA seed from prior run)
    # ------------------------------------------------------------------ #
    existing_weights = {}
    try:
        if WEIGHTS_PATH.exists():
            existing_weights = json.loads(WEIGHTS_PATH.read_text())
    except Exception as _adv_e:
        import sys as _sys
        print(f"[advisory:routing-weight-updater] {type(_adv_e).__name__}: {_adv_e} — advisory failure", file=_sys.stderr)

    TRACE_PATH = _hermes_root / "cache" / "routing-eligibility.json"
    traces_in = {}
    try:
        if TRACE_PATH.exists():
            _tr = json.loads(TRACE_PATH.read_text())
            if isinstance(_tr, dict):
                traces_in = _tr
    except Exception:
        traces_in = {}

    # ------------------------------------------------------------------ #
    # FTRL-EMA update
    # ------------------------------------------------------------------ #
    updated_weights = {}
    summary_rows = []

    for route in KNOWN_ROUTES:
        stats = route_stats.get(route, {})
        n = stats.get('total', 0)
        successes = stats.get('successes', 0)

        # Routes present in defaults or weights file start at 1.0 if unseen;
        # routes discovered only from the calibration log are zero-initialised
        # so FTRL learns from evidence rather than assuming high quality.
        default_prior = 0.0 if route not in _DEFAULT_ROUTES and route not in existing_weights else 1.0
        prior = float(existing_weights.get(route, {}).get('weight', default_prior)
                      if isinstance(existing_weights.get(route), dict)
                      else existing_weights.get(route, default_prior))

        if n < MIN_SAMPLES:
            # Insufficient data — carry prior forward unchanged
            new_weight = prior
            success_rate = None
            note = f'n={n} < min_samples={MIN_SAMPLES}, prior kept'
        else:
            success_rate = successes / n
            # Fisher information metric weighting (Amari "Information Geometry" Ch.2)
            # For Bernoulli(p): Fisher metric I(p) = 1/(p*(1-p))
            # Fisher-weighted EMA: routes near p=0.5 (high uncertainty) update slower;
            # routes near p=0 or p=1 (high certainty) update faster when wrong.
            # learning_rate = EMA_NEW * sqrt(p*(1-p))   [in [0, EMA_NEW/2]]
            # At p=0.5: lr = EMA_NEW * 0.5 (slowest update — most uncertain)
            # At p=0.1 or p=0.9: lr ≈ EMA_NEW * 0.3 (faster update — strong signal)
            _fisher_weight = math.sqrt(max(1e-6, success_rate * (1.0 - success_rate)))
            _lr = EMA_NEW * _fisher_weight  # Fisher-adjusted learning rate
            # TD(lambda) credit: scale lr by eligibility (decays at (gamma*lambda)^t when idle)
            try:
                _elig = float(traces_in.get(route, 1.0))
            except (TypeError, ValueError):
                _elig = 1.0
            if not math.isfinite(_elig) or _elig < 0:
                _elig = 1.0
            _lr = _lr * min(2.0, max(0.05, _elig))
            _decay = 1.0 - min(0.5, _lr)  # keep decay in (0.5, 1]
            # EMA: new = prior * decay + success_rate * lr  (information-geometry weighted)
            new_weight = prior * _decay + success_rate * _lr
            # Clamp
            new_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, new_weight))
            note = f'n={n}, success_rate={success_rate:.3f}, fisher_lr={_lr:.4f}'
            print(f'route={route}: weight={new_weight:.4f} ({note})')

        updated_weights[route] = {
            'weight': round(new_weight, 4),
            'n': n,
            'success_rate': round(success_rate, 3) if success_rate is not None else None,
            'ts': now,
            'note': note,
        }
        summary_rows.append({
            'route': route,
            'weight': round(new_weight, 4),
            'n': n,
            'success_rate': round(success_rate, 3) if success_rate is not None else None,
        })

    # Dirichlet-Multinomial natural gradient mix (Amari e-flat).
    _emp = {r: float(route_stats.get(r, {}).get('successes', 0) or 0) for r in KNOWN_ROUTES}
    _w_now = {r: float(updated_weights[r]['weight']) for r in KNOWN_ROUTES}
    _nat = natural_gradient_dirichlet(_w_now, _emp)
    for r in KNOWN_ROUTES:
        blended = 0.7 * float(updated_weights[r]['weight']) + 0.3 * float(_nat[r])
        blended = max(WEIGHT_MIN, min(WEIGHT_MAX, blended))
        updated_weights[r]['weight'] = round(blended, 4)
        updated_weights[r]['nat_grad'] = round(_nat[r], 4)

    # ------------------------------------------------------------------ #
    # O1: Compute cumulative regret vs uniform baseline                   #
    # (Borodin & El-Yaniv, Online Computation §2.1)                       #
    # ------------------------------------------------------------------ #
    # Uniform baseline: assign equal weight to all routes → success rate
    # is the average across all routes. FTRL "loss" per step = 1 - success.
    # Regret = sum(FTRL loss) - sum(uniform loss) over the window.
    total_n = sum(s.get('total', 0) for s in route_stats.values())
    total_successes = sum(s.get('successes', 0) for s in route_stats.values())
    uniform_success_rate = (total_successes / total_n) if total_n > 0 else 0.5
    ftrl_weighted_success = 0.0
    ftrl_weight_sum = 0.0
    for route in KNOWN_ROUTES:
        stats = route_stats.get(route, {})
        n = stats.get('total', 0)
        if n >= MIN_SAMPLES:
            w = float(existing_weights.get(route, {}).get('weight', 1.0)
                      if isinstance(existing_weights.get(route), dict)
                      else existing_weights.get(route, 1.0) or 0.0)
            if not math.isfinite(w) or w < 0:
                w = 1.0
            succ = stats.get('successes', 0) or 0
            ftrl_weighted_success += w * succ
            ftrl_weight_sum += w * n

    ftrl_success_rate = (ftrl_weighted_success / ftrl_weight_sum) if ftrl_weight_sum > 0 else uniform_success_rate
    if not math.isfinite(uniform_success_rate):
        uniform_success_rate = 0.5
    if not math.isfinite(ftrl_success_rate):
        ftrl_success_rate = uniform_success_rate
    # regret > 0: FTRL worse than uniform (alarm); regret < 0: FTRL better (good)
    # total_n==0 → 0 (no samples). Guard NaN/Inf from hand-edited weights.
    regret_this_run = (uniform_success_rate - ftrl_success_rate) * total_n
    if not math.isfinite(regret_this_run):
        regret_this_run = 0.0
    regret_entry = {
        'ts': now,
        'total_n': total_n,
        'uniform_success_rate': round(uniform_success_rate, 4),
        'ftrl_success_rate': round(ftrl_success_rate, 4),
        'regret': round(regret_this_run, 3),
        'alarm': regret_this_run > 0.05 * total_n,  # >5% relative regret triggers alarm
    }
    try:
        REGRET_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REGRET_LOG_PATH, 'a') as _rlog:
            _rlog.write(json.dumps(regret_entry) + '\n')
        if regret_entry['alarm']:
            print(f"[ALARM] FTRL regret={regret_this_run:.1f} > 5% threshold — FTRL underperforming uniform baseline")
        else:
            print(f"[OK] FTRL regret={regret_this_run:.3f} (FTRL success={ftrl_success_rate:.3f} vs uniform={uniform_success_rate:.3f})")
    except Exception as _re:
        print(f"WARN: regret log write failed: {_re}")

    # ------------------------------------------------------------------ #
    # Competitive ratio vs hindsight-best fixed route (Borodin/El-Yaniv)
    # Last 24h. NEVER cite offline OPT as achieved.
    # ------------------------------------------------------------------ #
    try:
        summary_comp = competitive_ratio_last_24h(LOG_PATH, now, updated_weights)
        COMP_PATH = _hermes_root / "cache" / "routing-competitive-ratio.jsonl"
        COMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COMP_PATH, "a") as _clog:
            _clog.write(json.dumps(summary_comp) + "\n")
        print(f"[competitive-ratio] ratio={summary_comp.get('competitive_ratio')} "
              f"finite={summary_comp.get('finite')} achieved_opt=False")
    except Exception as _ce:
        print(f"WARN: competitive ratio failed: {_ce}")
        summary_comp = {"error": str(_ce), "achieved_opt": False}

    # ------------------------------------------------------------------ #
    # TD(lambda) eligibility traces (Sutton-Barto) for delayed routing credit
    # ------------------------------------------------------------------ #
    try:
        TRACE_PATH = _hermes_root / "cache" / "routing-eligibility.json"
        traces = {}
        if TRACE_PATH.exists():
            try:
                traces = json.loads(TRACE_PATH.read_text())
                if not isinstance(traces, dict):
                    traces = {}
            except Exception:
                traces = {}
        observed = [r for r in KNOWN_ROUTES if route_stats.get(r, {}).get("total", 0) > 0]
        traces = update_eligibility_traces(traces, observed)
        _tmp_t = TRACE_PATH.with_suffix(".tmp")
        _tmp_t.write_text(json.dumps(traces, indent=2))
        _tmp_t.rename(TRACE_PATH)
        print(f"[eligibility] traces={ {k: round(float(v), 4) for k, v in traces.items() if k != '_meta'} }")
    except Exception as _te:
        print(f"WARN: eligibility traces failed: {_te}")
        traces = {}

    # ------------------------------------------------------------------ #
    # Write weights
    # ------------------------------------------------------------------ #
    try:
        WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _tmp_w = WEIGHTS_PATH.with_suffix('.tmp')
        _tmp_w.write_text(json.dumps(updated_weights, indent=2))
        _tmp_w.rename(WEIGHTS_PATH)
        print(f'Written: {WEIGHTS_PATH}')
    except Exception as e:
        print(f'ERROR writing weights: {e}')

    # ------------------------------------------------------------------ #
    # Print JSON summary (for cron delivery / stdout capture)
    # ------------------------------------------------------------------ #
    summary = {
        'ts': now,
        'window_hours': 48,
        'routes': summary_rows,
        'weights_path': str(WEIGHTS_PATH),
        'competitive_ratio': summary_comp if isinstance(summary_comp, dict) else None,
        'eligibility_traces': {k: traces.get(k) for k in traces if k != '_meta'} if isinstance(traces, dict) else None,
    }
    # EXP3 shadow advisory (Lattimore & Szepesvari Ch.11)
    # Computes EXP3 weights alongside FTRL-EMA — detects adversarial reward patterns.
    try:
        _route_stats_exp3 = {}
        for _r in summary_rows:
            _route_stats_exp3[_r['route']] = {
                'n_success': int(_r.get('n_success', 0)),
                'n_total': int(_r.get('n_total', 0)),
            }
        _prior_exp3 = {}
        _exp3_path = WEIGHTS_PATH.parent / 'routing-exp3-shadow.json'
        if _exp3_path.exists():
            try:
                _prior_exp3 = json.loads(_exp3_path.read_text())
            except Exception as _adv_e:
                import sys as _sys
                print(f"[advisory:routing-weight-updater] {type(_adv_e).__name__}: {_adv_e} — advisory failure", file=_sys.stderr)
        _exp3_result = compute_exp3_weights(_route_stats_exp3, _prior_exp3)
        # Persist cumulative rewards for next run
        _exp3_state = {f'exp3_cum_{r}': v for r, v in _exp3_result['cumulative_rewards'].items()}
        _exp3_path_tmp = _exp3_path.with_suffix('.tmp')
        _exp3_path_tmp.write_text(json.dumps({**_exp3_state, '_meta': _exp3_result}, indent=2))
        _exp3_path_tmp.replace(_exp3_path)
        summary['exp3_shadow'] = {
            'weights': _exp3_result['weights'],
            'eta': _exp3_result['eta'],
            'note': 'EXP3 adversarial bandit (Lattimore Ch.11); compare to FTRL weights to detect non-stationarity',
        }
    except Exception as _e3:
        summary['exp3_shadow'] = {'error': str(_e3)}

    print(json.dumps(summary, indent=2))



def compute_exp3_weights(
    route_stats: dict,
    prior_weights: dict,
    eta: float | None = None,
) -> dict:
    """EXP3 adversarial bandit weight update (shadow advisory).

    Theory: Lattimore & Szepesvari "Bandit Algorithms" Ch.11 (EXP3).
    Optimal for adversarial (non-stochastic) reward sequences where route quality
    may change over time. FTRL-EMA is optimal for stochastic rewards.
    By running both, we detect when routing rewards exhibit adversarial patterns
    (EXP3 would have done better) vs stochastic (FTRL better).

    EXP3 update:
        cumulative_reward[i] += observed_reward[i] / (w_i / sum_w)  [importance-weighted]
        w_i ∝ exp(eta * cumulative_reward[i])
        eta = sqrt(ln(K) / (T * K))  where K=routes, T=rounds seen

    Args:
        route_stats: {route: {n_success, n_total}} from routing log
        prior_weights: previous EXP3 cumulative rewards (persisted across runs)
        eta: exploration parameter (auto-computed if None)
    Returns:
        dict with new_weights (normalized), cumulative_rewards, eta
    """
    routes = list(route_stats.keys())
    K = max(len(routes), 1)
    # Estimate T from total samples seen
    T = max(sum(s.get('n_total', 1) for s in route_stats.values()), 1)
    if eta is None:
        eta = math.sqrt(math.log(K) / (T * K)) if K > 1 else 0.01

    # Load or init cumulative rewards
    cum_rewards = {r: prior_weights.get(f'exp3_cum_{r}', 0.0) for r in routes}

    # Compute current normalized weights (for importance weighting)
    raw = {r: math.exp(eta * cum_rewards[r]) for r in routes}
    total_raw = sum(raw.values()) or 1.0
    norm_weights = {r: raw[r] / total_raw for r in routes}

    # Importance-weighted reward update
    for route in routes:
        stats = route_stats[route]
        n_total = stats.get('n_total', 0)
        n_success = stats.get('n_success', 0)
        if n_total > 0:
            reward = n_success / n_total  # [0,1] reward
            p_i = norm_weights[route]
            if p_i > 0:
                cum_rewards[route] += reward / p_i  # importance-weighted unbiased estimate

    # Recompute weights with updated cumulative rewards
    raw2 = {r: math.exp(eta * cum_rewards[r]) for r in routes}
    total_raw2 = sum(raw2.values()) or 1.0
    new_weights = {r: raw2[r] / total_raw2 for r in routes}

    return {
        'weights': {r: round(new_weights[r], 4) for r in routes},
        'cumulative_rewards': {r: round(cum_rewards[r], 4) for r in routes},
        'eta': round(eta, 6),
        'K': K,
        'T': T,
    }


if __name__ == '__main__':
    main()

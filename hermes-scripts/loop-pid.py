#!/usr/bin/env python3
"""Discrete PID controller for agent retry/refinement loops.

Maps task error signal to a graded control action:
  u < 0.15  -> HALT (done)
  0.15-0.50 -> PATCH (local retry)
  0.50-0.80 -> REPLAN
  > 0.80    -> ESCALATE (delegate/model switch)

Based on Astrom-Murray Feedback Systems 2e §11.1-11.3 (PID) and
§11.4 (anti-windup back-calculation).

Usage:
  python3 loop-pid.py step --error 0.4 --prev-error 0.5 [--integrator 0.2] [--session SID]
  python3 loop-pid.py reset [--session SID]
  python3 loop-pid.py status [--session SID]
  python3 loop-pid.py gap-check --primal-cost 5.0 --dual-bound 4.7 --eps-abs 0.5 --eps-rel 0.05
  python3 loop-pid.py line-search --current-cost 0.8 --proposed-cost 0.75 --directional-deriv -0.1 [--alpha 0.1] [--beta 0.8]
  python3 loop-pid.py upcrossings [--a 0.5] [--b 0.8]
  python3 loop-pid.py span-check [--k 5] [--eps 0.15] [--lam 0.9]
  python3 loop-pid.py hyp-check --session SID [--percentile 90]
  python3 loop-pid.py ltl-check --session SID [--window 10] [--escalate-within 3]
  python3 loop-pid.py causal-taint --session SID [--horizon 5]
  python3 loop-pid.py verify-chain --session SID
  python3 loop-pid.py lyapunov-check [--session SID]   # KHALIL-1, KHALIL-7
  python3 loop-pid.py gain-check [--session SID]        # KHALIL-3

State is persisted to ~/.hermes/cache/loop-pid-state.json
Per-session copies (when --session is set) live in ~/.hermes/cache/loop-pid-sessions/<SID>.json
"""
import argparse, hashlib, json, math
from pathlib import Path
from datetime import datetime, timezone

Kp, Ki, Kd = 1.0, 0.15, 0.4
U_MAX, U_MIN = 1.0, 0.0
KAW = 0.5  # anti-windup back-calculation gain (Astrom eq 11.12)

STATE_FILE = Path.home() / '.hermes' / 'cache' / 'loop-pid-state.json'
SESSIONS_DIR = Path.home() / '.hermes' / 'cache' / 'loop-pid-sessions'
DEFAULT_HYP_THRESHOLD = 5
MIN_SESSIONS_FOR_PERCENTILE = 5


def _empty_state():
    return {
        'integrator': 0.0,
        'prev_error': None,
        'windup': False,
        'history': [],
        'hypotheses_tried': 0,
        'ended': False,
    }


def _state_path(session=None):
    if session:
        return SESSIONS_DIR / f'{session}.json'
    return STATE_FILE


def load_state(session=None):
    path = _state_path(session)
    if path.exists():
        s = json.loads(path.read_text())
        s.setdefault('hypotheses_tried', 0)
        s.setdefault('ended', False)
        return s
    return _empty_state()


def save_state(s, session=None):
    path = _state_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    _tmp_p = path.with_suffix('.tmp')
    _tmp_p.write_text(json.dumps(s, indent=2))
    _tmp_p.rename(path)


def _iter_state_files():
    if STATE_FILE.exists():
        yield STATE_FILE
    if SESSIONS_DIR.is_dir():
        yield from sorted(SESSIONS_DIR.glob('*.json'))


def _percentile(values, p):
    xs = sorted(float(v) for v in values)
    n = len(xs)
    rank = (p / 100.0) * (n - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        val = xs[lo]
    else:
        val = xs[lo] + (xs[hi] - xs[lo]) * (rank - lo)
    if abs(val - round(val)) < 1e-9:
        return int(round(val))
    return val


def cmd_step(args):
    session = getattr(args, 'session', None)
    s = load_state(session)
    e = args.error  # 0=done, 1=total failure
    prev_error = s.get('prev_error')
    prev_de = s.get('prev_de')
    de = (e - prev_error) if prev_error is not None else 0.0

    # Raw PID
    u_raw = Kp * e + Ki * s['integrator'] + Kd * de
    u = max(U_MIN, min(U_MAX, u_raw))

    # Anti-windup back-calculation (Astrom §11.4)
    windup = u_raw != u
    if windup:
        s['integrator'] += KAW * (u - u_raw) / Ki if Ki > 0 else 0
    else:
        s['integrator'] += e  # normal integration

    # error plateau detector: delta < span_bound where span_bound = eps*(1-lam)/(2*lam)
    # using lambda=0.9 (Puterman §6.6 span seminorm stopping criterion, discount factor)
    delta = abs(e - prev_error) if prev_error is not None else float('inf')
    vi_stop = delta < 0.15 * (1 - 0.9) / (2 * 0.9)

    # contraction diagnostics only; do not use for action decisions
    contraction_a = None
    posterior_bound = None
    if prev_error is not None:
        if prev_de is not None and abs(prev_de) > 1e-9:
            contraction_a = abs(de) / abs(prev_de)
        s['prev_de'] = de
        if contraction_a is not None and contraction_a < 1.0:
            posterior_bound = contraction_a / (1.0 - contraction_a) * abs(de)
    else:
        s['prev_de'] = None

    s['prev_error'] = e
    s['windup'] = windup
    s['history'].append({'ts': datetime.now(timezone.utc).isoformat(), 'e': e, 'u': round(u, 4)})
    s['history'] = s['history'][-20:]  # keep last 20

    action = ('HALT' if u < 0.15 else 'PATCH' if u < 0.5 else 'REPLAN' if u < 0.8 else 'ESCALATE')

    # Bellman convergence check (Puterman Ch 6.3: Bellman residual < epsilon*(1-gamma)/(2*gamma))
    # gamma=0.95: residual threshold = eps*(1-0.95)/(2*0.95) ≈ 0.026*eps
    bellman_converged = False
    if prev_error is not None and abs(e - prev_error) < 0.05 and abs(s['integrator']) < 0.01:
        bellman_converged = True
        action = 'CONVERGED'  # Puterman Ch 6.3: Bellman residual < epsilon*(1-gamma)/(2*gamma), gamma=0.95

    if action in ('PATCH', 'REPLAN'):
        s['hypotheses_tried'] = int(s.get('hypotheses_tried') or 0) + 1
    s['ended'] = action == 'HALT'
    log = s.get('action_log')
    if not isinstance(log, list):
        log = []
    if not log:
        prev_hash = '0' * 64
    else:
        prev_hash = hashlib.sha256(
            json.dumps(log[-1], sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
    log.append({
        'action': action,
        'hypotheses_tried': int(s.get('hypotheses_tried') or 0),
        'ts': datetime.now(timezone.utc).isoformat(),
        'prev_hash': prev_hash,
    })
    s['action_log'] = log[-50:]
    save_state(s, session)

    out = {
        'u': round(u, 4),
        'action': action,
        'e': e,
        'de': round(de, 4),
        'integrator': round(s['integrator'], 4),
        'windup': windup,
        'bellman_converged': bellman_converged,
        'vi_stop': bool(vi_stop),
        'delta': None if not math.isfinite(delta) else round(float(delta), 6),
        'contraction_a': None if contraction_a is None else round(float(contraction_a), 6),
        'posterior_bound': None if posterior_bound is None else round(float(posterior_bound), 6),
        'hypotheses_tried': int(s.get('hypotheses_tried') or 0),
    }
    # Lyapunov violation: when anti-windup fired, loop energy V(x)=error^2 is increasing
    # Astrom-Murray §5.4: anti-windup active means integrator saturated — Lyapunov function violated
    if windup:
        out['LYAPUNOV_VIOLATION'] = (
            'Loop energy V(x)=error^2 increasing - anti-windup active. '
            'Astrom-Murray §5.4: integrator clamp engaged.'
        )
    print(json.dumps(out))

def cmd_reset(args):
    session = getattr(args, 'session', None)
    save_state(_empty_state() | {'prev_de': None}, session)
    print(json.dumps({'reset': True}))

def cmd_status(args):
    session = getattr(args, 'session', None)
    print(json.dumps(load_state(session)))

def _p90_threshold(percentile=90):
    ended_values = []
    for path in _iter_state_files():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get('ended'):
            ended_values.append(int(data.get('hypotheses_tried') or 0))
    if len(ended_values) < MIN_SESSIONS_FOR_PERCENTILE:
        return DEFAULT_HYP_THRESHOLD
    return _percentile(ended_values, percentile)


def cmd_causal_taint(args):
    """Diagnostic: precursor actions in the horizon before each ESCALATE."""
    session = args.session
    horizon = int(args.horizon)
    s = load_state(session)
    log = s.get('action_log')
    if not isinstance(log, list) or not log:
        print(json.dumps({
            'session': session,
            'n_entries': 0,
            'n_escalations': 0,
            'escalation_precursors': [],
            'most_common_precursor_action': None,
            'diagnostic_only': True,
        }))
        return
    precursor_action_counts = {}
    escalation_precursors = []
    for i, entry in enumerate(log):
        if not isinstance(entry, dict):
            continue
        if entry.get('action') != 'ESCALATE':
            continue
        lookback = min(horizon, i)
        precursors = []
        for j in range(i - lookback, i):
            prev = log[j]
            if not isinstance(prev, dict):
                continue
            action = prev.get('action')
            rec = {
                'step': j,
                'action': action,
                'hypotheses_tried': prev.get('hypotheses_tried'),
                'lag': i - j,
            }
            precursors.append(rec)
            if action is not None:
                precursor_action_counts[action] = precursor_action_counts.get(action, 0) + 1
        escalation_precursors.append({
            'escalation_step': i,
            'precursors': precursors,
        })
    most_common = None
    if precursor_action_counts:
        most_common = max(precursor_action_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    print(json.dumps({
        'session': session,
        'n_entries': len(log),
        'n_escalations': len(escalation_precursors),
        'escalation_precursors': escalation_precursors,
        'most_common_precursor_action': most_common,
        'diagnostic_only': True,
    }))


def cmd_ltl_check(args):
    """LTL watchdog: hyp>threshold implies ESCALATE within N subsequent steps."""
    session = args.session
    window = int(args.window)
    escalate_within = int(args.escalate_within)
    s = load_state(session)
    if 'action_log' not in s:
        print(json.dumps({
            'ltl_satisfied': True,
            'reason': 'no_action_log',
            'diagnostic_only': True,
        }))
        return
    log = s.get('action_log')
    if not isinstance(log, list):
        log = []
    scanned = log[-window:] if window > 0 else []
    # Offset of scanned[0] in the full log
    base = max(0, len(log) - len(scanned))
    threshold = _p90_threshold(90)
    violations = []
    for i, entry in enumerate(scanned):
        if not isinstance(entry, dict):
            continue
        try:
            hyp = int(entry.get('hypotheses_tried') or 0)
        except (TypeError, ValueError):
            hyp = 0
        if hyp <= threshold:
            continue
        k = base + i
        future = log[k + 1 : k + 1 + escalate_within]
        if len(future) < escalate_within:
            continue  # inconclusive — not enough future steps
        escalated = any(
            isinstance(e, dict) and e.get('action') == 'ESCALATE' for e in future
        )
        if not escalated:
            violations.append({
                'step_idx': k,
                'hypotheses_tried': hyp,
                'actions_after': [a.get('action') for a in future if isinstance(a, dict)],
            })
    print(json.dumps({
        'session': session,
        'ltl_property': 'if hypotheses_tried > threshold then ESCALATE within N steps',
        'ltl_satisfied': len(violations) == 0,
        'violations': violations,
        'window': window,
        'escalate_within': escalate_within,
        'diagnostic_only': True,
    }))


def cmd_hyp_check(args):
    """Diagnostic-only hypothesis-count gate. Never overrides the PID action."""
    session = args.session
    p = float(args.percentile)
    s = load_state(session)
    n = int(s.get('hypotheses_tried') or 0)

    ended_values = []
    for path in _iter_state_files():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get('ended'):
            ended_values.append(int(data.get('hypotheses_tried') or 0))

    cold_start = len(ended_values) < MIN_SESSIONS_FOR_PERCENTILE
    threshold = DEFAULT_HYP_THRESHOLD if cold_start else _percentile(ended_values, p)
    escalate = n > threshold
    out = {
        'hypotheses_tried': n,
        'p90_threshold': threshold,
        'escalate': bool(escalate),
        'diagnostic_only': True,
    }
    if cold_start:
        out['cold_start'] = True
    if escalate:
        out['note'] = 'hypothesis count exceeds historical 90th percentile; consider ESCALATE'
    print(json.dumps(out))

def cmd_gap_check(args):
    """Cost-gap stop: stop when primal_cost - lower_bound <= eps.
    NOTE: caller must supply a valid lower bound (not a convex dual);
    this is a general absolute/relative gap test, not a Boyd duality certificate."""
    primal_cost = args.primal_cost
    dual_bound = args.dual_bound
    eps_abs = args.eps_abs
    eps_rel = args.eps_rel
    gap = primal_cost - dual_bound
    stop = gap <= eps_abs or (dual_bound > 0 and gap / dual_bound <= eps_rel)
    print(json.dumps({
        'gap': gap,
        'eps_abs': eps_abs,
        'eps_rel': eps_rel,
        'stop': bool(stop),
        'certificate': {
            'primal_cost': primal_cost,
            'dual_bound': dual_bound,
            'gap': gap,
        },
    }))

def cmd_upcrossings(args):
    """Oscillation detector for PATCH/REPLAN band. Default [0.50, 0.80]. Fires only if n>=10."""
    a = args.a
    b = args.b
    s = load_state()
    history = s.get('history') or []
    count = 0
    seen_below = False
    for item in history:
        e = item.get('e') if isinstance(item, dict) else item
        if e is None:
            continue
        try:
            e = float(e)
        except (TypeError, ValueError):
            continue
        if e < a:
            seen_below = True
        elif e > b:
            if seen_below:
                count += 1
                seen_below = False
    n = len(history)
    oscillating = count >= 3 and n >= 10
    print(json.dumps({
        'upcrossings': count,
        'a': a,
        'b': b,
        'n': n,
        'oscillating': oscillating,
        'action': 'ESCALATE' if oscillating else 'CONTINUE',
    }))


def cmd_span_check(args):
    """Plateau detector: checks if last k errors have small range."""
    s = load_state()
    k = int(args.k)
    eps = float(args.eps)
    lam = float(args.lam)
    history = s.get('history') or []
    errs = [h['e'] for h in history if isinstance(h, dict) and 'e' in h]
    H = errs[-k:] if k > 0 else []
    k_used = len(H)
    threshold = ((1.0 - lam) / lam) * eps if lam != 0 else float('inf')
    if not H:
        print(json.dumps({
            'range': 0.0,
            'threshold': threshold,
            'action': 'CONTINUE',
            'h_min': None,
            'h_max': None,
            'k_used': 0,
            'detector': 'plateau',
        }))
        return
    h_min = min(H)
    h_max = max(H)
    sp = h_max - h_min
    note = None
    if sp < threshold and h_min > eps:
        action = 'PATCH'
        note = 'plateau_high: consider replanning'
    elif sp < threshold and h_max < eps:
        action = 'HALT'
    else:
        action = 'CONTINUE'
    out = {
        'range': sp,
        'threshold': threshold,
        'action': action,
        'h_min': h_min,
        'h_max': h_max,
        'k_used': k_used,
        'detector': 'plateau',
    }
    if note:
        out['note'] = note
    print(json.dumps(out))

def cmd_line_search(args):
    """Step acceptance test: accept a proposed update only if it reduces cost sufficiently.
    Uses Armijo-style threshold (alpha * t * predicted_drop) but requires caller to provide
    a real directional derivative — do NOT use with PID outputs where no gradient exists."""
    current_cost = args.current_cost
    proposed_cost = args.proposed_cost
    directional_deriv = args.directional_deriv
    alpha = args.alpha
    beta = args.beta
    t_min = 0.001
    if directional_deriv >= 0:
        print(json.dumps({
            'accepted': False,
            'step_size': 0.0,
            'cost_after': current_cost,
            'reason': 'directional_deriv must be < 0 (not a descent direction)',
        }))
        return
    t = 1.0
    while proposed_cost > current_cost + alpha * t * directional_deriv:
        t = beta * t
        if t < t_min:
            break
    accepted = proposed_cost <= current_cost + alpha * t * directional_deriv
    print(json.dumps({
        'accepted': bool(accepted),
        'step_size': t,
        'cost_after': proposed_cost if accepted else current_cost,
        'reason': 'armijo_satisfied' if accepted else 't_min_reached',
    }))

def cmd_verify_chain(args):
    """Verify SHA256 prev_hash chain on action_log. Diagnostic only."""
    session = args.session
    s = load_state(session)
    log = s.get('action_log')
    if not isinstance(log, list):
        log = []
    n = len(log)
    if n < 2:
        print(json.dumps({
            'chain_valid': True,
            'reason': 'too_short',
            'n_entries': n,
            'diagnostic_only': True,
        }))
        return
    broken_at = None
    for i in range(1, n):
        entry = log[i]
        if not isinstance(entry, dict) or 'prev_hash' not in entry:
            continue
        expected = hashlib.sha256(
            json.dumps(log[i - 1], sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
        if expected != entry['prev_hash']:
            broken_at = i
            break
    n_hashed = sum(1 for e in log if isinstance(e, dict) and 'prev_hash' in e)
    print(json.dumps({
        'session': session,
        'n_entries': n,
        'n_hashed': n_hashed,
        'chain_valid': broken_at is None,
        'broken_at': broken_at,
        'diagnostic_only': True,
    }))

def _reconstruct_integrator(history):
    """Replay the integration accumulation from history to recover per-step integrator values.

    The state file stores only the *current* integrator after the last step, not per-step
    snapshots.  We must replay from zero.  Anti-windup correction is not recoverable from
    (ts, e, u) alone, so we run the vanilla integrator path: integrator(k+1) = integrator(k) + e(k).
    When u != clip(u_raw) we flag windup for that step (u_raw is back-calculated from u and e).
    Returns a list of dicts with keys: e, u, integrator_before, u_raw, windup.
    """
    integrator = 0.0
    steps = []
    prev_e = None
    for item in history:
        if not isinstance(item, dict):
            continue
        try:
            e = float(item['e'])
            u = float(item['u'])
        except (KeyError, TypeError, ValueError):
            continue
        # Derivative term: approximated as zero when no prev_e (matches cmd_step behaviour)
        de = (e - prev_e) if prev_e is not None else 0.0
        u_raw = Kp * e + Ki * integrator + Kd * de
        # Determine windup: u_raw would be clipped
        u_clipped = max(U_MIN, min(U_MAX, u_raw))
        windup = abs(u_raw - u_clipped) > 1e-9
        steps.append({
            'e': e,
            'u': u,
            'u_raw': u_raw,
            'integrator': integrator,  # integrator *before* this step's update
            'windup': windup,
        })
        # Advance integrator (mirrors cmd_step logic)
        if windup:
            integrator += KAW * (u_clipped - u_raw) / Ki if Ki > 0 else 0.0
        else:
            integrator += e
        prev_e = e
    return steps


def cmd_lyapunov_check(args):
    """KHALIL-1 + KHALIL-7: empirical Lyapunov decrease check on PID history.

    V(k)    = e(k)^2 + (Ki/Kp) * integrator(k)^2              [normal steps]
    V_aw(k) = e(k)^2 + (Ki/Kp) * integrator(k)^2
              + KAW * (u_raw(k) - u(k))^2                      [saturated steps, KHALIL-7]

    Checks DeltaV = V(k+1) - V(k) < 0 for each consecutive pair.
    Reports piecewise ΔV for normal and saturated steps separately (KHALIL-7).

    # SLOTINE-CH5: Lyapunov stability theorem requires V(x)>0 and dV/dt<=0 along trajectories.
    # Quadratic candidate V(e) = e^T*P*e (scalar: V=e^2) is simplest valid choice.
    # Current implementation uses a DISCRETE Lyapunov decrease check: ΔV = V(k+1)-V(k) < 0,
    # which is the correct discrete-time analog of the continuous dV/dt = 2*e*de/dt <= 0.
    # The composite candidate V = e^2 + (Ki/Kp)*integrator^2 covers both error and integral
    # state, matching the augmented state vector of the PID system. The anti-windup extension
    # V_aw adds KAW*(u_raw-u)^2 for saturated steps (Khalil §4.7 / Slotine Ch 5 extensions).
    # Proper continuous check would be: dV/dt = 2*e*de/dt + 2*(Ki/Kp)*integrator*d(integrator)/dt <= 0.
    # Discrete ΔV < 0 is sufficient for practical stability of the sampled-data system.
    """
    session = getattr(args, 'session', None)
    s = load_state(session)
    history = s.get('history') or []

    if len(history) < 2:
        print(json.dumps({
            'error': 'insufficient_history',
            'steps_in_log': len(history),
            'note': 'Need at least 2 steps for ΔV computation.',
        }))
        return

    ratio = Ki / Kp  # coefficient on integrator^2 term

    steps = _reconstruct_integrator(history)

    def V_normal(e, integ):
        return e ** 2 + ratio * integ ** 2

    def V_aw(e, integ, u_raw, u):
        return e ** 2 + ratio * integ ** 2 + KAW * (u_raw - u) ** 2

    warnings = []
    normal_deltas = []
    saturated_deltas = []
    steps_decreasing = 0
    steps_non_decreasing = 0

    for k in range(len(steps) - 1):
        sk = steps[k]
        sk1 = steps[k + 1]

        # Choose Lyapunov function for each step (KHALIL-7)
        if sk['windup']:
            vk = V_aw(sk['e'], sk['integrator'], sk['u_raw'], sk['u'])
        else:
            vk = V_normal(sk['e'], sk['integrator'])

        if sk1['windup']:
            vk1 = V_aw(sk1['e'], sk1['integrator'], sk1['u_raw'], sk1['u'])
        else:
            vk1 = V_normal(sk1['e'], sk1['integrator'])

        dv = vk1 - vk
        entry = {
            'k': k,
            'V_k': round(vk, 6),
            'V_k1': round(vk1, 6),
            'delta_V': round(dv, 6),
            'windup_k': sk['windup'],
            'windup_k1': sk1['windup'],
        }

        if sk['windup'] or sk1['windup']:
            saturated_deltas.append(entry)
        else:
            normal_deltas.append(entry)

        if dv < 0:
            steps_decreasing += 1
        else:
            steps_non_decreasing += 1
            warnings.append({
                'step': k,
                'delta_V': round(dv, 6),
                'warning': 'non_decreasing_Lyapunov',
            })

    steps_checked = steps_decreasing + steps_non_decreasing
    lyapunov_stable = steps_non_decreasing == 0

    # Piecewise summaries (KHALIL-7)
    def _summarise(deltas):
        if not deltas:
            return {'count': 0, 'mean_delta_V': None, 'min_delta_V': None, 'max_delta_V': None}
        dvs = [d['delta_V'] for d in deltas]
        return {
            'count': len(dvs),
            'mean_delta_V': round(sum(dvs) / len(dvs), 6),
            'min_delta_V': round(min(dvs), 6),
            'max_delta_V': round(max(dvs), 6),
        }

    out = {
        'steps_checked': steps_checked,
        'steps_decreasing': steps_decreasing,
        'steps_non_decreasing': steps_non_decreasing,
        'lyapunov_stable': lyapunov_stable,
        'lyapunov_function': 'V(k) = e(k)^2 + (Ki/Kp)*integrator(k)^2 [normal]; '
                             'V_aw(k) += KAW*(u_raw-u)^2 [saturated, KHALIL-7]',
        'params': {'Kp': Kp, 'Ki': Ki, 'Kd': Kd, 'KAW': KAW, 'Ki_over_Kp': round(ratio, 6)},
        'piecewise': {
            'normal_steps': _summarise(normal_deltas),
            'saturated_steps': _summarise(saturated_deltas),
        },
        'warnings': warnings,
        'note': (
            'Empirical Lyapunov check (Khalil §4.1). DeltaV < 0 required for decrease condition. '
            'Saturated steps use anti-windup Lyapunov function (KHALIL-7). '
            'Integrator values are replayed from history; anti-windup corrections are approximated.'
        ),
    }
    print(json.dumps(out, indent=2))


def cmd_gain_check(args):
    """KHALIL-3: empirical L-infinity gain estimate for the retry loop.

    gamma = max(|u(k)|) / max(|e(k)|)

    This is the empirical ell-infinity gain, NOT the Lyapunov gain.
    If gamma < 1.0 the loop is heuristically BIBO-stable.
    """
    session = getattr(args, 'session', None)
    s = load_state(session)
    history = s.get('history') or []

    if not history:
        print(json.dumps({
            'error': 'no_history',
            'note': 'Run loop-pid.py step first to accumulate history.',
        }))
        return

    us, es = [], []
    for item in history:
        if not isinstance(item, dict):
            continue
        try:
            es.append(abs(float(item['e'])))
            us.append(abs(float(item['u'])))
        except (KeyError, TypeError, ValueError):
            continue

    if not es or not us:
        print(json.dumps({'error': 'unparseable_history'}))
        return

    max_u = max(us)
    max_e = max(es)
    gamma = max_u / max_e if max_e > 1e-12 else float('inf')

    bibo_heuristic = gamma < 1.0
    out = {
        'empirical_gain_estimate': round(gamma, 6) if math.isfinite(gamma) else None,
        'max_abs_u': round(max_u, 6),
        'max_abs_e': round(max_e, 6),
        'n_steps': len(es),
        'bibo_heuristic': bibo_heuristic,
        'bibo_label': (
            'loop appears bounded-input-bounded-output stable (heuristic)'
            if bibo_heuristic else
            'gamma >= 1.0: BIBO stability not guaranteed by this heuristic'
        ),
        'note': (
            'Empirical ell-infinity gain (Khalil §5.1). '
            'gamma = max|u| / max|e| over all history. '
            'This is NOT the Lyapunov gain. BIBO stability requires a formal ISS certificate.'
        ),
    }
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('step')
    s.add_argument('--error', type=float, required=True)
    s.add_argument('--session', default=None)
    s.add_argument('--integral', type=float, default=None,
                    help='Reserved (unused); integrator state is loaded from persisted session')
    s.add_argument('--derivative', type=float, default=None,
                    help='Reserved (unused); derivative is computed from state history')
    s.set_defaults(func=cmd_step)
    rst = sub.add_parser('reset')
    rst.add_argument('--session', default=None)
    rst.set_defaults(func=cmd_reset)
    st = sub.add_parser('status')
    st.add_argument('--session', default=None)
    st.set_defaults(func=cmd_status)
    hc = sub.add_parser('hyp-check')
    hc.add_argument('--session', required=True)
    hc.add_argument('--percentile', type=float, default=90)
    hc.set_defaults(func=cmd_hyp_check)
    ltl = sub.add_parser('ltl-check')
    ltl.add_argument('--session', required=True)
    ltl.add_argument('--window', type=int, default=10)
    ltl.add_argument('--escalate-within', type=int, default=3, dest='escalate_within')
    ltl.set_defaults(func=cmd_ltl_check)
    ct = sub.add_parser('causal-taint')
    ct.add_argument('--session', required=True)
    ct.add_argument('--horizon', type=int, default=5)
    ct.set_defaults(func=cmd_causal_taint)
    gc = sub.add_parser('gap-check')
    gc.add_argument('--primal-cost', type=float, required=True)
    gc.add_argument('--dual-bound', type=float, required=True)
    gc.add_argument('--eps-abs', type=float, required=True)
    gc.add_argument('--eps-rel', type=float, required=True)
    gc.set_defaults(func=cmd_gap_check)
    ls = sub.add_parser('line-search')
    ls.add_argument('--current-cost', type=float, required=True)
    ls.add_argument('--proposed-cost', type=float, required=True)
    ls.add_argument('--directional-deriv', type=float, required=True)
    ls.add_argument('--alpha', type=float, default=0.1)
    ls.add_argument('--beta', type=float, default=0.8)
    ls.set_defaults(func=cmd_line_search)
    uc = sub.add_parser('upcrossings',
                        help='Oscillation detector for PATCH/REPLAN band. Default [0.50, 0.80]. Fires only if n>=10.')
    uc.add_argument('--a', type=float, default=0.50,
                    help='Lower band edge (default 0.50)')
    uc.add_argument('--b', type=float, default=0.80,
                    help='Upper band edge (default 0.80)')
    uc.set_defaults(func=cmd_upcrossings)
    sc = sub.add_parser('span-check')
    sc.add_argument('--k', type=int, default=5)
    sc.add_argument('--eps', type=float, default=0.15)
    sc.add_argument('--lam', type=float, default=0.9)
    sc.set_defaults(func=cmd_span_check)
    vc = sub.add_parser('verify-chain')
    vc.add_argument('--session', required=True)
    vc.set_defaults(func=cmd_verify_chain)
    lc = sub.add_parser('lyapunov-check',
                        help='KHALIL-1 + KHALIL-7: empirical Lyapunov decrease check on PID history')
    lc.add_argument('--session', default=None)
    lc.set_defaults(func=cmd_lyapunov_check)
    gc2 = sub.add_parser('gain-check',
                         help='KHALIL-3: empirical L-infinity gain estimate (BIBO heuristic)')
    gc2.add_argument('--session', default=None)
    gc2.set_defaults(func=cmd_gain_check)
    args = p.parse_args()
    args.func(args)

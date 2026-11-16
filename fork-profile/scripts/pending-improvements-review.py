#!/usr/bin/env python3
"""pending-improvements-review.py — Real evaluator for queued Hermes self-improvement proposals.

Reads spike queues from math-spike-queue.json and cs-spike-queue.json, scores each
pending spike against gate criteria, and emits a ranked shortlist with implementation
recommendations. Also surfaces generated ideas from math-ideas-queue.json.

Gate criteria (ALL must pass for IMPLEMENT recommendation — no partial-pass IMPLEMENT):
  - target: names a real Hermes script, skill, or plausible new artifact
  - hypothesis: concrete, not vague ("better quality" is rejected)
  - metric: named measurable proxy exists
  - spike_given/when/then: all three filled (not empty)
  - confidence: high or medium (low → DEFER; unknown → DEFER)

Output:
  <profile_root>/cache/pending-improvements-report.json
    ranked list of IMPLEMENT / DEFER / WEAK recommendations

Usage:
  python3 pending-improvements-review.py [--dry-run] [--profile PROFILE]

REV-001 fix: path resolution uses fork-root guard so HERMES_HOME=/var/home/rainbow/.hermes
  and HERMES_HOME=/var/home/rainbow/.hermes/profiles/fork both resolve correctly.
REV-009 fix: --profile arg is consumed and re-derives all paths before main() runs.
"""
from __future__ import annotations
import json, os, re, sys, argparse
from pathlib import Path
from datetime import datetime, timezone, UTC

# ── Path resolution (REV-001 / REV-009) ───────────────────────────────────────
# Guard: if HERMES_HOME already ends with the profile name, it *is* the profile root.
# Otherwise treat it as the hermes base and append profiles/<profile>.
def _resolve_paths(profile: str):
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    # If the last path component matches the profile name, HERMES_HOME is the profile root.
    if hh.name == profile or str(hh).endswith(f"profiles/{profile}"):
        profile_root = hh
    else:
        profile_root = hh / "profiles" / profile
    scripts_dir  = profile_root / "scripts"
    cache_dir    = profile_root / "cache" / "research"
    report_path  = profile_root / "cache" / "pending-improvements-report.json"
    # SPIKES_DIR lives under the profile cache (writable in sandbox)
    spikes_dir   = profile_root / "cache" / "research" / "spikes"
    return scripts_dir, cache_dir, report_path, spikes_dir

_default_profile = os.environ.get("HERMES_PROFILE", "fork")
SCRIPTS_DIR, CACHE_DIR, REPORT_PATH, SPIKES_DIR = _resolve_paths(_default_profile)

# ── Known Hermes scripts (real targets); "new:" prefix = proposed artifact ────
KNOWN_SCRIPTS = {
    "reasoning-complexity-classifier.py", "working-memory.py", "metacognitive-harness.py",
    "skill-router-index.py", "routing-linucb.py", "skill-beta-feedback.py",
    "online-threshold-skill-router.py", "l1-promote.py", "l1-graphiti-reconcile.py",
    "l1-hindsight-promote.py", "memory-staleness-cron.py", "memory-coupling-merge.py",
    "shadow-gate-nightly.py", "eval-shadow-synthetic.py", "msprt-shadow-gate.py",
    "cot-injection-detector.py", "execution-integrity-guard.py",
    "hermes-research-sweep.py", "hermes-math-sweep.py", "cs-research-sweep.py",
    "math-paper-interpreter.py", "cs-paper-interpreter.py", "pending-improvements-review.py",
    "calibration-threshold-updater.py", "progress-mirage-gate.py", "cron-mdp-policy.py",
    "l1-tracegrant.py",
    # Arch surface: runtime / scheduling / maintenance / security
    "stuck-job-detector.py", "fork-state-vacuum.py", "session-auto-prune.py",
    "callgraph-taint-audit.py", "mcp-privilege-audit.py", "run-header.py",
    "monitor-suite-runner.py", "spike-actuator.py", "research-pipeline-weekly.py",
    "improvement_governance.py", "improvement_shadow.py", "run_ledger.py",
    # Batch-2 promoted spikes
    "persistent-memory-fuzzer.py", "memory-bottleneck-monitor.py",
    "tool-call-safety-filter.py", "memory-topology-consolidator.py",
    "parametric-saturation-monitor.py", "skill-compressor.py",
    # Deferred infra stubs
    "agent-output-verifier.py", "memory-contamination-tagger.py",
    # Implemented scripts
    "reflection-distiller.py", "checkpoint-rollback-tracker.py",
    "amd-memory-loader.py", "stepshield-trajectory-monitor.py",
    "relevance-compaction-trigger.py", "semantic-early-stopping.py",
    # Data-collection hooks
    "hallucination-probe-hook.py", "memory-coherence-probe-hook.py",
    "ontology-query-expander.py", "ann-embeddings-probe.py", "session-gc-probe.py",
    # Survivors / absorbers
    "skill_confidence_calibration.py", "cbf-barrier-compiler.py",
    "stability-margin-analyzer.py", "rolling-conformal-predictor.py",
    "evo-harness-compile.py", "step-level-prm-scorer.py",
    "action-log.py", "dcr-reconcile.py", "call-evidence-chain.py",
    # Wave B remaining
    "anytime-skill-evaluator.py", "information-cost-skill-router.py",
    "conformal-ai-text-screener.py", "safe-compliance-confidence.py",
    "robust-multiagent-coordinator.py", "dynamical-resource-allocator.py",
    "adversarial-opinion-detector.py", "randomized-resource-sharer.py",
    "agentic-software-verifier.py", "conformal-changepoint-detector.py",
    "delegation-audit-logger.py", "authguard-integrity-checker.py",
    "information-rate-skill-sampler.py", "causal-critique-ranker.py",
    "llm-autoscaler.py", "moment-edge-sampler.py",
    "fair-pagerank-skill-scorer.py", "multi-pass-cron-scheduler.py",
    "afanet-failure-attributor.py", "autonomy-router-mdp.py",
    "citation-confidence-router.py", "cost-aware-eval-framework.py",
    "fact-attribution-verifier.py", "feedback-memory-ranker.py",
    "feedback-robustness-scorer.py", "lifecycle-schema-extension.py",
    "mutation-rubric-engine.py", "observation-budget-allocator.py",
    "obstruction-certificate-cache.py", "output-formalizer-verifier.py",
    "pddl-state-abstractor.py", "perception-reasoning-splitter.py",
    "reasoning-trace-evaluator.py", "state-machine-synthesizer.py",
    "step-level-trajectory-auditor.py",
    "skill-graph-builder.py", "delegate-outcome-logger.py",
    "anytime-routing-campaign.py", "cbf-loop-constraint.py",
    "delegation-audit-hook.py", "tool-review-log-schema.py",
    "anytime-eval-feeder.py",
    "delegation-blind-spot-audit.py", "causal-regret-minimizer.py",
    "tool-audit-kill-matrix.py", "skill-variance-regularization.py",
    "anytime-nspi-evaluator.py",
    "skill-communication-pruning.py", "skill-spectral-ranking.py",
    "skill-evidence-rate.py",
    "conformal-memory-audit.py", "compute-manipulability-weights.py",
    "subagent-allocation-ucb.py",
    "optimization-pass-ordering.py", "bounded-rationality-policy.py",
    "compliance-score-collector.py", "turn-behavior-collector.py",
    "skill-graph-edge-builder.py", "skill-latency-collector.py",
    "tool-review-scorer.py",
}

KNOWN_SKILLS = {
    "agent-runtime-loop-patterns", "bps-skill-budget", "hermes-compaction-eval",
    "amodei-concrete-ai-safety", "soares-agent-foundations", "autonomous-ai-agents",
    "recursive-adversarial-hardening", "github-pr-review",
    "hermes-fork-maintenance", "hermes-fork-upstream-merge",
    "hermes-fork-regression-prevention", "hermes-fork-bottleneck-audit",
    "hermes-fork-script-development", "hermes-plugin-wiring-audit",
    "hermes-host-maintenance", "wave21c-loop-governance", "wave21b-routing-bandits",
}

# Known plugin names (also accepted as targets)
KNOWN_PLUGINS = {
    "governance-hard-block", "shadow-eval", "compaction-engine",
    "routing-weights", "context-compaction", "l1-tracegrant",
}

# Known lifecycle.db / hermes_state.db tables (accepted as targets)
KNOWN_DB_TARGETS = {
    "lifecycle.db", "hermes_state.db", "facts", "episodes", "probes",
    "routing_weights", "skill_scores",
}

VAGUE_METRIC_PATTERNS = {"better quality", "improved", "faster", "more accurate", "better"}

# REV-008: expanded skip statuses (casefolded)
SKIP_STATUSES = {
    "implemented", "killed", "deferred", "weakened", "rejected", "skip", "implement",
}

# REV-011: prefer richer spike_X_result by trying known lettered keys in order
_SPIKE_RESULT_KEYS = [
    "spike_A_result", "spike_B_result", "spike_C_result", "spike_D_result",
    "spike_E_result", "spike_F_result",
]


def _str(v, cap: int = 2000) -> str:
    """Safe coercion to str with cap. Handles None/str/dict/list/int/bool. (REV-010)"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()[:cap]
    if isinstance(v, dict):
        try:
            return json.dumps(v, default=str)[:cap]
        except Exception:
            return str(v)[:cap]
    return str(v)[:cap]


def _parse_cs_gwt(blob: str) -> tuple[str, str, str]:
    """Parse 'Given ... When ... Then ...' prose blob into separate fields. (REV-004)"""
    if not blob:
        return "", "", ""
    # Case-insensitive split on Given/When/Then
    parts = re.split(r'\b(given|when|then)\b', blob, flags=re.IGNORECASE)
    g = w = t = ""
    i = 0
    while i < len(parts):
        token = parts[i].strip().lower()
        if token == "given" and i + 1 < len(parts):
            g = parts[i + 1].strip(); i += 2; continue
        elif token == "when" and i + 1 < len(parts):
            w = parts[i + 1].strip(); i += 2; continue
        elif token == "then" and i + 1 < len(parts):
            t = parts[i + 1].strip(); i += 2; continue
        i += 1
    return g, w, t


def _norm_conf(raw) -> str:
    """Normalise confidence to 'high'|'medium'|'low'. (REV-004)"""
    if isinstance(raw, (int, float)):
        if raw >= 0.75:
            return "high"
        elif raw >= 0.40:
            return "medium"
        else:
            return "low"
    s = str(raw).strip().lower()
    if s in ("high", "h"):
        return "high"
    if s in ("medium", "med", "m"):
        return "medium"
    return "low"


def _extract_target(spike: dict) -> str:
    """Extract target from multiple possible field names. (REV-004 / REV-007)"""
    raw = (spike.get("target") or spike.get("component_target")
           or spike.get("hermes_analogue") or spike.get("name") or "")
    return _str(raw)


_CHANGE_TYPE_SIGNALS: list[tuple[str, list[str]]] = [
    # order matters — first match wins
    ("config",  ["config.yaml", "openshell-policy", "env default"]),
    ("runtime", ["agent loop", "agent/*.py", "tool dispatch", "compaction", "session lifecycle",
                 "context window", "agent runtime"]),
    ("memory",  ["memory.md", "user.md", "ttl", "skill routing", "fact graph", "memory layout",
                 "memory-", "l1-", "graphiti", "working memory"]),
    ("profile", ["agents.md", "user.md", "profile instruction", "memory.md",
                 "hermes_profile", "standing instruction"]),
    ("arch",    ["plugin hook", "architecture", "architecture.md", "cron topology",
                 "subsystem", "inter-script", "new subsystem"]),
]

def _infer_change_type(target: str) -> str:
    """Classify a spike target string into a change_type bucket.

    Returns one of: 'script' | 'runtime' | 'memory' | 'arch' | 'config' | 'profile'.
    Defaults to 'script' when no signal matches.
    """
    t = target.lower()
    for change_type, signals in _CHANGE_TYPE_SIGNALS:
        if any(s in t for s in signals):
            return change_type
    return "script"


def score_spike(spike: dict) -> dict:
    """Score a spike dict against gate criteria. Returns dict with score, recommendation, reasons."""
    if not isinstance(spike, dict):
        return {"recommendation": "SKIP", "score": -1, "reason": "not a dict"}

    reasons_pass = []
    reasons_fail = []

    # ── Field extraction: two schemas + CS-specific fields ───────────────────
    # Schema A (queue-sourced): given/when/then/target/metric/confidence/hypothesis
    # Schema B (organic spike files): hypothesis/name/spike_X_result/experiment/evidence
    # Schema C (CS queue): given_when_then prose, component_target, proposal, float confidence

    given = _str(spike.get("given") or spike.get("spike_given") or "")
    when  = _str(spike.get("when")  or spike.get("spike_when")  or
                 spike.get("experiment") or "")

    # REV-011: try lettered keys in fixed order, skip stripped-empty values
    then = _str(spike.get("then") or spike.get("spike_then") or "")
    if not then:
        for k in _SPIKE_RESULT_KEYS:
            v = spike.get(k)
            if v and _str(v).strip():
                then = _str(v)
                break
    if not then:
        # Fallback: any spike_*_result key not in the fixed list, or 'evidence'
        for k, v in spike.items():
            if k.startswith("spike_") and k.endswith("_result") and v and _str(v).strip():
                then = _str(v); break
    if not then:
        then = _str(spike.get("evidence") or "")

    # REV-004: parse CS given_when_then prose blob if individual fields are empty
    if not (given and when and then):
        blob = _str(spike.get("given_when_then") or "")
        if blob:
            g2, w2, t2 = _parse_cs_gwt(blob)
            given = given or g2
            when  = when  or w2
            then  = then  or t2

    target = _extract_target(spike)
    hyp    = _str(spike.get("hypothesis") or spike.get("proposal") or "")
    metric_raw = spike.get("metric") or spike.get("measured") or ""
    metric = _str(metric_raw)
    conf   = _norm_conf(spike.get("confidence") or "low")   # REV-002: default low not medium
    title  = _str(spike.get("title") or spike.get("name") or spike.get("id") or "")
    status = _str(spike.get("status") or "pending").lower().strip()

    # REV-008: extended skip-status list
    if status in SKIP_STATUSES:
        return {
            "recommendation": "SKIP", "score": -1, "reason": f"status={status}",
            "title": title, "target": target, "confidence": conf, "metric": "",
            "hypothesis": "", "given": "", "when": "", "then": "",
            "pass": [], "fail": [],
        }

    score = 0

    # ── Gate 1: given/when/then all non-empty ─────────────────────────────────
    # B002-fix: SYSTEMS-APPLICABLE items carry 'proposal' instead of GWT fields.
    # Accept proposal as a GWT proxy so they are not gate-blocked by definition.
    item_type = _str(spike.get("interpretation_type") or spike.get("result") or "")
    is_systems_applicable = "systems" in item_type.lower()
    if not (given and when and then) and is_systems_applicable:
        proposal_text = _str(spike.get("proposal") or "")
        if proposal_text:
            # Treat the whole proposal as the 'when' field for scoring purposes
            given = given or "Hermes system"
            when  = when  or proposal_text
            then  = then  or "architecture improvement"

    if given and when and then:
        score += 2
        reasons_pass.append("given/when/then all present")
    else:
        missing = [k for k, v in {"given": given, "when": when, "then": then}.items() if not v]
        reasons_fail.append(f"missing: {missing}")

    # ── Gate 2: hypothesis is concrete ───────────────────────────────────────
    if len(hyp) >= 30 and not any(p in hyp.lower() for p in VAGUE_METRIC_PATTERNS):
        score += 2
        reasons_pass.append("hypothesis concrete")
    elif hyp:
        score += 1
        # B003-fix: vague hypothesis is a soft fail — prevents IMPLEMENT but not DEFER
        reasons_fail.append("hypothesis present but vague")
    else:
        reasons_fail.append("hypothesis empty")

    # ── Gate 3: metric is named ───────────────────────────────────────────────
    if len(metric) >= 10 and not any(p in metric.lower() for p in VAGUE_METRIC_PATTERNS):
        score += 2
        reasons_pass.append(f"metric: {metric[:60]}")
    elif metric:
        score += 1
        # B003-fix: vague metric is a soft fail — prevents IMPLEMENT but not DEFER
        reasons_fail.append("metric present but vague")
    else:
        reasons_fail.append("metric empty")

    # ── Gate 4: target is known ───────────────────────────────────────────────
    is_new_artifact = target.startswith("new:")
    # REV-007: extract first .py token for basename matching (handles "metacognitive-harness.py diagnostic pass")
    py_match = re.search(r'([\w\-]+\.py)', target)
    target_basename = py_match.group(1) if py_match else Path(target).name
    target_known = (
        target_basename in KNOWN_SCRIPTS
        or any(s in target for s in KNOWN_SKILLS)
        or any(p in target for p in KNOWN_PLUGINS)
        or any(d in target for d in KNOWN_DB_TARGETS)
        or is_new_artifact
        or bool(py_match and (SCRIPTS_DIR / target_basename).exists())
    )
    if target_known:
        score += 1
        reasons_pass.append(f"target recognised: {target[:60]}")
    elif target:
        reasons_fail.append(f"target unknown: {target[:60]}")
    else:
        reasons_fail.append("target empty")

    # ── Gate 5: confidence ────────────────────────────────────────────────────
    if conf == "high":
        score += 2
        reasons_pass.append("confidence=high")
    elif conf == "medium":
        score += 1
        reasons_pass.append("confidence=medium")
    else:
        reasons_fail.append("confidence=low")

    # ── Bonus: theory-to-implementation bridge fields (from Step 2c) ──────────
    artifact  = _str(spike.get("artifact") or "")
    scaffold  = _str(spike.get("scaffold") or "")
    kill_test = _str(spike.get("kill_test") or "")
    hard_core = _str(spike.get("hard_core") or "")
    is_heuristic = bool(spike.get("is_heuristic") or False)

    # P3-05: artifact must begin with a recognized type prefix (not just any 10-char string)
    _ARTIFACT_PREFIXES = ("cron script:", "plugin hook:", "sqlite:", "json state:", 
                          "skill document:", "subprocess helper:")
    artifact_valid = (artifact and len(artifact) >= 10 and
                      any(artifact.lower().startswith(p) for p in _ARTIFACT_PREFIXES))
    if artifact_valid:
        score += 1
        reasons_pass.append(f"artifact named: {artifact[:60]}")
    if kill_test and len(kill_test) >= 15:
        score += 1
        reasons_pass.append(f"kill test defined: {kill_test[:60]}")
    # scaffold + hard_core together: theory extrapolation complete
    # P2-01: only award bonus when is_heuristic=False (sentinel prevents false extrapolation)
    if scaffold and hard_core and not is_heuristic:
        score += 1
        reasons_pass.append(f"scaffold={scaffold[:30]}; invariant: {hard_core[:40]}")

    # P3-03: for SPIKE (not OPTIMIZATION), missing kill_test or hard_core blocks IMPLEMENT
    # B002-fix: discriminate type via interpretation_type, not a falsy opt_type check.
    # CS items have no opt_type and no 'result' field; treating absence of opt_type as
    # is_spike caused CS SYSTEMS-APPLICABLE items to hit hard_core/kill_test SPIKE gates.
    result_type = _str(spike.get("result") or spike.get("opt_type") or "")
    is_spike = "spike" in result_type.lower() or (
        spike.get("interpretation_type", "").upper() == "SPIKE"
    )
    if is_spike and not hard_core and scaffold:
        reasons_fail.append("theory bridge incomplete: hard_core missing")
    if is_spike and scaffold and not kill_test:
        reasons_fail.append("theory bridge incomplete: kill_test missing")

    # ── Recommendation: IMPLEMENT requires score>=7 AND zero fails (REV-002) ──
    if score >= 7 and not reasons_fail:
        rec = "IMPLEMENT"
    elif score >= 5 and not reasons_fail:
        rec = "IMPLEMENT"   # clean 5-6 (all gates pass, both high/medium conf can reach here)
    elif score >= 5:
        rec = "DEFER"       # score ok but has gaps
    elif score >= 3:
        rec = "DEFER"
    else:
        rec = "WEAK"

    return {
        "recommendation": rec,
        "score": score,
        "pass": reasons_pass,
        "fail": reasons_fail,
        "title": title,
        "target": target,
        "confidence": conf,
        "metric": metric[:120],
        "hypothesis": hyp[:120],
        "given": given[:100],
        "when": when[:120],
        "then": then[:100],
        # Step 2c fields — passed through for spike-actuator.py to consume
        "artifact":   _str(spike.get("artifact") or ""),
        "scaffold":   _str(spike.get("scaffold") or ""),
        "hard_core":  _str(spike.get("hard_core") or ""),
        "belt":       _str(spike.get("belt") or ""),
        "kill_test":  _str(spike.get("kill_test") or ""),
        "layer1_demo": _str(spike.get("layer1_demo") or ""),
        "is_heuristic": bool(spike.get("is_heuristic") or False),
        # REV-010: change_type + governance_required — inferred from target string.
        # Callers (spike-actuator.py) use these to route items correctly.
        "change_type":        _infer_change_type(target),
        "governance_required": _infer_change_type(target) in ("runtime", "config"),
    }


def load_queue(path: Path) -> list[dict]:
    """Load a spike queue JSON. Handles multiple key schemas and concatenates all lists. (REV-003)"""
    if not path.exists():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        # Collect from all recognised list keys (do not use 'or' — empty list is falsy)
        results: list[dict] = []
        for key in ("pending_spikes", "pending_optimizations", "pending", "spikes", "items"):
            val = d.get(key)
            if isinstance(val, list):
                results.extend(v for v in val if isinstance(v, dict))
        return results
    except Exception as e:
        print(f"[review] Failed to load {path}: {e}", file=sys.stderr)
        return []


def load_spike_files(spikes_dir: Path) -> list[dict]:
    """Load individual spike-*.json files. Skips files over 512 KB. (REV-010)"""
    spikes = []
    if not spikes_dir.exists():
        return spikes
    for f in sorted(spikes_dir.glob("spike-*.json")):
        try:
            if f.stat().st_size > 512 * 1024:
                print(f"[review] Skipping oversized spike file: {f.name}", file=sys.stderr)
                continue
            d = json.loads(f.read_text())
            if not isinstance(d, dict):
                continue
            d["_source_file"] = str(f.name)
            spikes.append(d)
        except Exception:
            continue
    return spikes


def _dedup_spikes(spikes: list[dict]) -> list[dict]:
    """Deduplicate spikes across sources by id, title, and url. (REV-005)"""
    seen: set[str] = set()
    out: list[dict] = []
    for s in spikes:
        key = (
            _str(s.get("id") or "").lower().strip()
            or _str(s.get("url") or "").lower().strip()
            or _str(s.get("title") or s.get("name") or "").lower().strip()[:80]
        )
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser(description="Pending improvements reviewer")
    parser.add_argument("--dry-run", action="store_true", help="Don't write report")
    parser.add_argument("--profile", type=str, default=_default_profile)
    args = parser.parse_args()

    # REV-009: re-derive all paths from --profile arg
    global SCRIPTS_DIR, CACHE_DIR, REPORT_PATH, SPIKES_DIR
    SCRIPTS_DIR, CACHE_DIR, REPORT_PATH, SPIKES_DIR = _resolve_paths(args.profile)

    print(f"[pending-improvements-review] Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"[pending-improvements-review] Profile={args.profile} cache={CACHE_DIR} spikes={SPIKES_DIR}")

    # ── Load all spike sources ─────────────────────────────────────────────────
    math_queue  = load_queue(CACHE_DIR / "math-spike-queue.json")
    cs_queue    = load_queue(CACHE_DIR / "cs-spike-queue.json")
    spike_files = load_spike_files(SPIKES_DIR)

    # Load generated ideas (cap at 100 to avoid bloat — REV-010)
    ideas: list[dict] = []
    ideas_path = CACHE_DIR / "math-ideas-queue.json"
    if ideas_path.exists():
        try:
            ideas = json.loads(ideas_path.read_text()).get("ideas", [])[:100]
        except Exception:
            pass

    print(f"[pending-improvements-review] Sources: {len(math_queue)} math queue, "
          f"{len(cs_queue)} CS queue, {len(spike_files)} spike files, {len(ideas)} ideas")

    # ── Merge + dedup ─────────────────────────────────────────────────────────
    all_spikes: list[dict] = []
    for s in math_queue:
        s.setdefault("_source", "math-queue")
        all_spikes.append(s)
    for s in cs_queue:
        s.setdefault("_source", "cs-queue")
        all_spikes.append(s)
    for s in spike_files:
        s.setdefault("_source", "spike-file")
        all_spikes.append(s)

    all_spikes = _dedup_spikes(all_spikes)

    # ── Score ─────────────────────────────────────────────────────────────────
    scored: list[dict] = []
    for spike in all_spikes:
        try:
            result = score_spike(spike)
        except Exception as e:
            result = {"recommendation": "SKIP", "score": -1, "reason": f"score error: {e}",
                      "title": _str(spike.get("title") or spike.get("id") or ""),
                      "target": "", "confidence": "low", "metric": "",
                      "hypothesis": "", "given": "", "when": "", "then": "",
                      "pass": [], "fail": [f"score error: {e}"]}
        result["_source"]      = spike.get("_source", "unknown")
        result["_source_file"] = spike.get("_source_file", "")
        result["url"]          = _str(spike.get("url") or "")
        result["category"]     = _str(spike.get("category") or "")
        result["scaffold"]     = _str(spike.get("scaffold") or "")
        result["hard_core"]    = _str(spike.get("hard_core") or "")
        result["belt"]         = _str(spike.get("belt") or "")
        result["artifact"]     = _str(spike.get("artifact") or "")
        result["layer1_demo"]  = _str(spike.get("layer1_demo") or "")
        result["probe"]        = _str(spike.get("probe") or "")   # P3-02
        result["kill_test"]    = _str(spike.get("kill_test") or "")
        scored.append(result)

    # Sort: IMPLEMENT first, then by score desc
    rec_order = {"IMPLEMENT": 0, "DEFER": 1, "WEAK": 2, "SKIP": 3}
    scored.sort(key=lambda x: (rec_order.get(x.get("recommendation", "SKIP"), 4), -x.get("score", -1)))

    implement = [s for s in scored if s.get("recommendation") == "IMPLEMENT"]
    defer      = [s for s in scored if s.get("recommendation") == "DEFER"]
    weak       = [s for s in scored if s.get("recommendation") == "WEAK"]
    skipped    = [s for s in scored if s.get("recommendation") == "SKIP"]

    print(f"\n[pending-improvements-review] Scored {len(scored)} spikes "
          f"(after dedup from {len(all_spikes)} total):")
    print(f"  IMPLEMENT: {len(implement)}")
    print(f"  DEFER:     {len(defer)}")
    print(f"  WEAK:      {len(weak)}")
    print(f"  SKIP:      {len(skipped)} (already implemented/killed/deferred/weakened)")

    print()
    if implement:
        print("=== IMPLEMENT (ready to apply) ===")
        for s in implement[:10]:
            print(f"  [{s['confidence'].upper()}] score={s['score']} [{s['category']}] {s['title'][:70]}")
            print(f"    Target:    {s['target'][:80]}")
            print(f"    Metric:    {s['metric'][:80]}")
            print(f"    Given:     {s['given'][:80]}")
            print(f"    When:      {s['when'][:80]}")
            print(f"    Then:      {s['then'][:80]}")
            if s.get('scaffold'):
                print(f"    Scaffold:  {s['scaffold'][:60]}")
            if s.get('artifact'):
                print(f"    Artifact:  {s['artifact'][:80]}")
            if s.get('hard_core'):
                print(f"    Hard core: {s['hard_core'][:80]}")
            if s.get('belt'):
                print(f"    Belt:      {s['belt'][:80]}")
            if s.get('layer1_demo'):
                print(f"    Layer1:    {s['layer1_demo'][:80]}")
            if s.get('probe'):
                print(f"    Probe:     {s['probe'][:80]}")
            if s.get('kill_test'):
                print(f"    Kill test: {s['kill_test'][:80]}")
            if s.get('fail'):
                print(f"    Gaps:      {s['fail']}")
            print()

    if defer:
        print(f"=== DEFER ({len(defer)} spikes need more info or infra) ===")
        for s in defer[:5]:
            print(f"  [{s['confidence'].upper()}] score={s['score']} {s['title'][:60]} — gaps: {s.get('fail')}")
        print()

    if ideas:
        print(f"=== GENERATED IDEAS ({len(ideas)} theorem-seeded artifacts) ===")
        for idea in ideas[:5]:
            print(f"  [{idea.get('artifact_type','?')}] {idea.get('hermes_artifact','')} "
                  f"— {idea.get('hermes_benefit','')[:80]}")
        print()

    # ── Write report (REV-006: wrapped in try/except) ─────────────────────────
    report = {
        "ts":              datetime.now(UTC).isoformat(),
        "profile":         args.profile,
        "total_scored":    len(scored),
        "implement_count": len(implement),
        "defer_count":     len(defer),
        "weak_count":      len(weak),
        "skip_count":      len(skipped),
        "implement":       implement,
        "defer":           defer[:20],
        "weak":            weak[:10],
        "generated_ideas": ideas[:20],
    }

    if not args.dry_run:
        try:
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = REPORT_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(report, indent=2, default=str))
            os.replace(tmp, REPORT_PATH)
            print(f"[pending-improvements-review] Report written: {REPORT_PATH}")
        except (OSError, TypeError) as e:
            print(f"[pending-improvements-review] ERROR writing report: {e}", file=sys.stderr)
            return 1
    else:
        print("[pending-improvements-review] DRY RUN — report not written")

    return 0


if __name__ == "__main__":
    sys.exit(main())

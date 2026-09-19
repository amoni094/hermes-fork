#!/usr/bin/env python3
"""
skill-router-index.py — SkillRouter pattern: TF-IDF semantic index over Hermes skill descriptions.

Usage:
  python3 skill-router-index.py --build           # scan all skills, build index
  python3 skill-router-index.py --query TEXT      # find top-5 matching skills
  python3 skill-router-index.py --check           # flag high-overlap pairs (>0.65)

Based on: SkillRouter (arXiv:2603.22455) — Sweep 21 implementation.
At 80k skills, name+description routing degrades 31-44pp. TF-IDF is fine at current scale (~100 skills).
"""

import argparse
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import os as _os_sri
_hermes_base_sri = Path(_os_sri.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile_sri = _os_sri.environ.get("HERMES_PROFILE", "")
_hermes_root_sri = (_hermes_base_sri / "profiles" / _hermes_profile_sri) if _hermes_profile_sri and "profiles" not in str(_hermes_base_sri) else _hermes_base_sri
SKILLS_ROOT = _hermes_root_sri / "skills"
INDEX_PATH = _hermes_root_sri / "cache" / "skill-router-index.json"
OVERLAP_THRESHOLD = 0.65
BETA_STATE_PATH = _hermes_root_sri / "cache" / "skill-beta-state.json"

# R4 — Cross-domain skill fingerprints (Sweep 24 / arXiv:2603.22455 §4)
DOMAIN_LABELS: set[str] = {
    "research", "code", "mixed", "github", "email", "browser",
    "python", "bash", "terminal", "hermes", "skill", "agent",
    "web", "file", "tool",
}


def load_beta_state():
    """Load per-skill Beta(alpha, beta) posterior state from disk.
    Prior: Beta(1,1) = uniform. Source: numerical_optimization + rl_theory primers.
    Update: on success alpha+=1, on failure beta+=1. Score blend: 0.6*tfidf + 0.4*posterior_mean.
    """
    if BETA_STATE_PATH.exists():
        try:
            return json.loads(BETA_STATE_PATH.read_text())
        except Exception:
            return {}
    return {}


def beta_posterior_mean(skill_name, state):
    """Return E[p] = alpha/(alpha+beta). Defaults to uniform prior mean 0.5."""
    entry = state.get(skill_name, {})
    alpha = entry.get("alpha", 1.0)
    beta_val = entry.get("beta", 1.0)
    return alpha / (alpha + beta_val)


def _beta_wald_ci(alpha: float, beta: float, z: float = 1.96) -> tuple[float, float, float]:
    """DEPRECATED fallback: Wald/normal-approximation CI on Beta(alpha, beta).

    Prefer pac_bayes_bound(), which includes the KL(Q||P)/m complexity penalty.
    Kept for comparison / display only — not used for routing decisions.

    Returns (mean, lower_95, upper_95). z=1.96 is a 95% Wald interval.
    With prior Beta(1,1) and no observations (n=2), SE=sqrt(0.25/2)=0.354 so the
    raw CI is [-0.19, 1.19], clamped to [0, 1] (maximally uncertain).
    """
    n = alpha + beta
    mean = alpha / n
    # Normal approximation to the Beta mean (valid for n > 5; vacuous at n=2).
    se = math.sqrt(mean * (1.0 - mean) / n)
    return mean, max(0.0, mean - z * se), min(1.0, mean + z * se)


def _digamma(x: float) -> float:
    """Digamma ψ(x) = d/dx ln Γ(x) via recurrence + Stirling asymptotic.

    Recurrence: ψ(x+1) = ψ(x) + 1/x  → raise x until the expansion is accurate.
    Asymptotic (Abramowitz & Stegun 6.3.18):
      ψ(x) ≈ ln(x) - 1/(2x) - 1/(12x²) + 1/(120x⁴) - 1/(252x⁶)
    """
    if x <= 0.0:
        raise ValueError(f"digamma undefined for non-positive x={x}")
    acc = 0.0
    # Recurrence until x is large enough for the truncated Stirling series.
    while x < 8.0:
        acc -= 1.0 / x
        x += 1.0
    inv = 1.0 / x
    inv2 = inv * inv
    # ln(x) - 1/(2x) - 1/(12x^2) + 1/(120x^4) - 1/(252x^6)
    return acc + math.log(x) - 0.5 * inv - inv2 * (
        1.0 / 12.0 - inv2 * (1.0 / 120.0 - inv2 / 252.0)
    )


def _kl_beta_uniform(alpha: float, beta: float) -> float:
    """KL(Q||P) for Q=Beta(alpha, beta), P=Beta(1,1) (uniform / Haldane-Jeffreys-free).

    Analytic Beta KL (α0=β0=1):
      KL(Q||P) = ln(B(1,1)/B(α,β)) + (α-1)ψ(α) + (β-1)ψ(β) - (α+β-2)ψ(α+β)
    B(1,1)=1, and ln B(α,β) = lgamma(α)+lgamma(β)-lgamma(α+β), so
      ln(B(1,1)/B(α,β)) = -lgamma(α) - lgamma(β) + lgamma(α+β)
    """
    log_b_ratio = -math.lgamma(alpha) - math.lgamma(beta) + math.lgamma(alpha + beta)
    return (
        log_b_ratio
        + (alpha - 1.0) * _digamma(alpha)
        + (beta - 1.0) * _digamma(beta)
        - (alpha + beta - 2.0) * _digamma(alpha + beta)
    )


def _bernoulli_kl(p: float, q: float) -> float:
    """Binary KL: KL(Bern(p) || Bern(q)) = p ln(p/q) + (1-p) ln((1-p)/(1-q)).

    Left-hand side of the McAllester/Seeger PAC-Bayes-kl inequality.
    """
    if abs(p - q) < 1e-15:
        return 0.0
    if q <= 0.0:
        return 0.0 if p <= 0.0 else math.inf
    if q >= 1.0:
        return 0.0 if p >= 1.0 else math.inf
    kl = 0.0
    if p > 0.0:
        kl += p * math.log(p / q)
    if p < 1.0:
        kl += (1.0 - p) * math.log((1.0 - p) / (1.0 - q))
    return kl


def _invert_kl_upper(p: float, epsilon: float) -> float:
    """Largest q ∈ [p, 1] such that KL(p || q) ≤ epsilon (binary search)."""
    if epsilon <= 0.0:
        return p
    if math.isinf(epsilon):
        return 1.0
    lo, hi = p, 1.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if _bernoulli_kl(p, mid) <= epsilon:
            lo = mid  # feasible: try a larger gen_risk
        else:
            hi = mid
    return lo


def _invert_kl_lower(p: float, epsilon: float) -> float:
    """Smallest q ∈ [0, p] such that KL(p || q) ≤ epsilon (binary search)."""
    if epsilon <= 0.0:
        return p
    if math.isinf(epsilon):
        return 0.0
    lo, hi = 0.0, p
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if _bernoulli_kl(p, mid) <= epsilon:
            hi = mid  # feasible: try a smaller gen_risk
        else:
            lo = mid
    return hi


def pac_bayes_bound(
    alpha: float, beta: float, delta: float = 0.05
) -> tuple[float, float, float, float, float]:
    """McAllester (2003) / Seeger (2002) PAC-Bayes-kl bound on skill match quality.

    With probability ≥ 1-δ over m i.i.d. routing observations:
      KL(emp_risk || gen_risk) ≤ (KL(Q||P) + ln(2√m / δ)) / m

    Interpretation for skill routing (analysis/display only — does not change
    ranking unless the caller opts in):
      Q = Beta(alpha, beta) posterior over match quality
      P = Beta(1, 1) uniform prior
      mean_q = α/(α+β)
      emp_risk = 1 - mean_q   (empirical mismatch rate)
      m = α + β - 2           (observations under a uniform prior)
    Invert the binary-KL inequality by binary search to bound gen_risk, then
    convert back to quality: quality = 1 - gen_risk.

    Returns (mean_q, lower_pac_bayes_95, upper_pac_bayes_95, m, kl_qp).
    """
    if alpha <= 0.0 or beta <= 0.0:
        raise ValueError(f"Beta parameters must be positive, got alpha={alpha}, beta={beta}")
    if not (0.0 < delta < 1.0):
        raise ValueError(f"delta must be in (0, 1), got {delta}")

    mean_q = alpha / (alpha + beta)
    emp_risk = 1.0 - mean_q
    # Uniform prior contributes (1,1); remaining mass is the observation count.
    m = alpha + beta - 2.0
    kl_qp = _kl_beta_uniform(alpha, beta)

    if m <= 0.0:
        # No observations: complexity term diverges; bound is vacuous on [0, 1].
        return mean_q, 0.0, 1.0, 0.0, max(0.0, kl_qp)

    # McAllester penalty: (KL(Q||P) + ln(2√m / δ)) / m
    penalty = (kl_qp + math.log(2.0 * math.sqrt(m) / delta)) / m

    # Invert KL(emp_risk || gen_risk) ≤ penalty for gen_risk, then map to quality.
    gen_risk_hi = _invert_kl_upper(emp_risk, penalty)
    gen_risk_lo = _invert_kl_lower(emp_risk, penalty)
    lower_q = max(0.0, 1.0 - gen_risk_hi)
    upper_q = min(1.0, 1.0 - gen_risk_lo)
    return mean_q, lower_q, upper_q, m, kl_qp


def domain_strip(text: str) -> str:
    """Remove words in DOMAIN_LABELS from text using case-insensitive word-boundary matching (R4)."""
    pattern = r"\b(?:" + "|".join(re.escape(label) for label in DOMAIN_LABELS) + r")\b"
    return re.sub(pattern, " ", text, flags=re.IGNORECASE)


def structural_fingerprint(text: str) -> str:
    """Return top-20 content bigrams as a joined string after applying domain_strip (R4).

    Steps:
      1. domain_strip — remove domain-label words
      2. Lowercase and tokenise (alpha sequences only, len >= 2)
      3. Build all adjacent bigrams
      4. Rank by frequency; return top-20 as 'w1_w2' joined by spaces
    """
    stripped = domain_strip(text)
    tokens = re.findall(r"[a-z]{2,}", stripped.lower())
    bigrams: dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]}_{tokens[i + 1]}"
        bigrams[bg] = bigrams.get(bg, 0) + 1
    top_bigrams = sorted(bigrams, key=lambda k: bigrams[k], reverse=True)[:20]
    return " ".join(top_bigrams)


def cross_domain_boost(query_text: str, candidate_text: str) -> float:
    """Return an additive boost in [0.0, 0.15] based on structural fingerprint Jaccard similarity (R4).

    Returns 0.15 * Jaccard(query_fp, candidate_fp) if Jaccard > 0.4, else 0.0.
    Jaccard is computed over the bigram sets of the two fingerprints.
    """
    q_fp = set(structural_fingerprint(query_text).split())
    c_fp = set(structural_fingerprint(candidate_text).split())
    if not q_fp or not c_fp:
        return 0.0
    intersection = len(q_fp & c_fp)
    union = len(q_fp | c_fp)
    jaccard = intersection / union if union else 0.0
    return 0.15 * jaccard if jaccard > 0.4 else 0.0


def parse_frontmatter(skill_md: str) -> dict:
    """Parse YAML frontmatter between --- delimiters. Returns dict with name, description, triggers."""
    lines = skill_md.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}

    fm_lines = lines[1:end]
    result = {"name": "", "description": "", "triggers": []}

    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        # name
        if line.startswith("name:"):
            result["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        # description (may be block scalar with >)
        elif line.startswith("description:"):
            rest = line.split(":", 1)[1].strip()
            if rest in (">", "|", ">-", "|-"):
                # block scalar — collect indented lines
                desc_lines = []
                i += 1
                while i < len(fm_lines) and (fm_lines[i].startswith("  ") or fm_lines[i].strip() == ""):
                    desc_lines.append(fm_lines[i].strip())
                    i += 1
                result["description"] = " ".join(desc_lines).strip()
                continue
            else:
                result["description"] = rest.strip('"').strip("'")
        # triggers list
        elif line.startswith("triggers:"):
            i += 1
            while i < len(fm_lines) and fm_lines[i].startswith("  -"):
                trigger = fm_lines[i].strip().lstrip("- ").strip().strip('"').strip("'")
                result["triggers"].append(trigger)
                i += 1
            continue
        i += 1

    return result


def tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric, remove stopwords."""
    stopwords = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "be", "use", "when",
        "that", "this", "it", "as", "if", "how", "what", "which", "do", "does",
        "can", "will", "not", "all", "any", "has", "have", "been", "using",
    }
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 2]


def build_tfidf(skills: list[dict]) -> tuple[list[dict], dict]:
    """Build BM25-style vectors. Returns (skills_with_vectors, idf_dict).

    Replaces raw TF-IDF with BM25 term saturation (k1=1.5, b=0.75).
    BM25 dampens high-frequency token inflation and accounts for document length.
    Source: information_retrieval CS primer (Robertson & Zaragoza 2009).
    At 217+ skills, BM25 meaningfully reduces routing confusion from shared stopword-
    heavy descriptions (e.g. 'use when' triggers appearing in every skill).
    """
    BM25_K1 = 1.5
    BM25_B = 0.75
    N = len(skills)

    # Build document frequency and average document length
    df = defaultdict(int)
    doc_lengths = []
    for skill in skills:
        tokens = skill["tokens"]
        doc_lengths.append(len(tokens))
        for t in set(tokens):
            df[t] += 1

    avgdl = (sum(doc_lengths) / N) if N > 0 else 1.0

    # BM25 IDF: log((N - df + 0.5) / (df + 0.5) + 1), clamped to >= 0
    idf = {
        t: max(math.log((N - cnt + 0.5) / (cnt + 0.5) + 1), 0.0)
        for t, cnt in df.items()
    }

    # BM25 TF-saturated vectors
    for skill, dl in zip(skills, doc_lengths):
        tf_raw = defaultdict(float)
        for t in skill["tokens"]:
            tf_raw[t] += 1
        vec = {}
        for t, freq in tf_raw.items():
            # BM25 TF normalization
            tf_bm25 = (freq * (BM25_K1 + 1)) / (
                freq + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl)
            )
            vec[t] = tf_bm25 * idf.get(t, 0.0)
        # L2-normalize so cosine similarity works unchanged downstream
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        skill["tfidf"] = {t: v / norm for t, v in vec.items()}

    return skills, idf


def cosine(vec1: dict, vec2: dict) -> float:
    shared = set(vec1) & set(vec2)
    return sum(vec1[t] * vec2[t] for t in shared)


def scan_skills() -> list[dict]:
    skills = []
    for skill_md_path in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        try:
            text = skill_md_path.read_text(errors="replace")
            fm = parse_frontmatter(text)
            if not fm.get("name"):
                continue
            name = fm["name"]
            description = fm.get("description", "")
            triggers = fm.get("triggers", [])
            combined = " ".join([name, description] + triggers)
            tokens = tokenize(combined)
            skills.append({
                "name": name,
                "description": description[:200],
                "triggers": triggers,
                "path": str(skill_md_path.relative_to(SKILLS_ROOT)),
                "tokens": tokens,
            })
        except Exception as e:
            print(f"WARN: skipping {skill_md_path}: {e}", file=sys.stderr)
    return skills


def cmd_build():
    print(f"Scanning {SKILLS_ROOT} ...")
    skills = scan_skills()
    print(f"Found {len(skills)} skills with valid frontmatter.")

    skills, idf = build_tfidf(skills)

    # Strip tfidf from the JSON (rebuild at query time from tokens)
    index = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total": len(skills),
        "skills": [
            {
                "name": s["name"],
                "description": s["description"],
                "triggers": s["triggers"],
                "path": s["path"],
                "tokens": s["tokens"],
            }
            for s in skills
        ],
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _tmp_i = INDEX_PATH.with_suffix('.tmp')
    _tmp_i.write_text(json.dumps(index, indent=2))
    _tmp_i.rename(INDEX_PATH)
    print(f"Index written to {INDEX_PATH}")
    print(f"Total skills indexed: {len(skills)}")


def load_index_with_tfidf():
    if not INDEX_PATH.exists():
        print("ERROR: index not found. Run --build first.", file=sys.stderr)
        sys.exit(1)
    index = json.loads(INDEX_PATH.read_text())
    skills = index["skills"]
    skills, idf = build_tfidf(skills)
    return skills, idf, index


def route(query_text: str, top: int = 5) -> list[dict]:
    """Return top-N skill matches as a list of dicts (callable API, no side-effects).

    Each dict has: name, description, score (float, 0–1), category.
    Returns [] when the index is not yet built (fail-silently contract).
    Reuses cmd_query scoring logic without printing.
    """
    if not INDEX_PATH.exists():
        return []
    skills, idf, _index = load_index_with_tfidf()
    q_tokens = tokenize(query_text)
    BM25_K1_Q = 1.5
    q_tf = defaultdict(float)
    for t in q_tokens:
        q_tf[t] += 1
    q_vec_raw = {}
    for t, freq in q_tf.items():
        tf_bm25 = (freq * (BM25_K1_Q + 1)) / (freq + BM25_K1_Q)
        q_vec_raw[t] = tf_bm25 * idf.get(t, 0.0)
    q_norm = math.sqrt(sum(v * v for v in q_vec_raw.values())) or 1.0
    q_vec = {t: v / q_norm for t, v in q_vec_raw.items()}

    beta_state = load_beta_state()
    beta_active = bool(beta_state)
    scored = [
        (
            (0.6 * cosine(q_vec, s["tfidf"]) + 0.4 * beta_posterior_mean(s["name"], beta_state))
            if beta_active else cosine(q_vec, s["tfidf"])
        ) + cross_domain_boost(query_text, s.get("description", ""))
        for s in skills
    ]
    scored = list(zip(scored, skills))
    scored.sort(key=lambda x: -x[0])

    # Concept-lattice semantic reranking (same logic as cmd_query)
    LATTICE_SCRIPT = Path(_os_sri.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "concept-lattice-index.py"
    AMBIGUITY_GAP = 0.12
    LATTICE_BOOST = 0.15
    if len(scored) >= 2:
        gap = scored[0][0] - scored[1][0]
        if gap < AMBIGUITY_GAP and LATTICE_SCRIPT.exists():
            try:
                _lat = subprocess.run(
                    [sys.executable, str(LATTICE_SCRIPT), "--query", query_text, "--top-k", "5"],
                    capture_output=True, text=True, timeout=10,
                )
                lattice_hits = json.loads(_lat.stdout) if _lat.returncode == 0 else []
            except Exception:
                lattice_hits = []
            if lattice_hits:
                lattice_names: set = set()
                for _hit in lattice_hits:
                    for _m in _hit.get("members", []):
                        lattice_names.add(_m.lower())
                    for _i in _hit.get("intent", []):
                        lattice_names.add(_i.lower())
                _boosted = []
                for _sc, _s in scored:
                    if any(_s["name"].lower() in _ln or _ln in _s["name"].lower() for _ln in lattice_names):
                        _sc += LATTICE_BOOST
                    _boosted.append((_sc, _s))
                scored = sorted(_boosted, key=lambda x: -x[0])

    results = []
    for sc, s in scored[:top]:
        if sc <= 0.0:
            continue
        results.append({
            "name": s["name"],
            "description": s.get("description", "")[:120],
            "score": round(float(sc), 4),
            "category": s.get("category", ""),
        })

    # --- Ensemble layer (post-hoc, fail-open) ---
    # When BM25 top score is low-confidence (< 0.4), call specialist routers
    # and merge their top-1 suggestions under 'ensemble_suggestions'.
    top_bm25_score = results[0]["score"] if results else 0.0
    if top_bm25_score < 0.4:
        _SCRIPTS = Path(__file__).resolve().parent
        ensemble_suggestions: list[dict] = []

        # 1. soft-bellman-skill-router: --query QUERY --top 3
        try:
            _proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "soft-bellman-skill-router.py"),
                 "--query", query_text, "--top", "3"],
                capture_output=True, text=True, timeout=5,
            )
            # Output is human-readable table; parse "  SKILL P Q N" lines
            _suggestion = None
            for _line in _proc.stdout.splitlines():
                _parts = _line.strip().split()
                # Data lines: skill_name  prob  q_value  count (4 tokens, first is skill name)
                if len(_parts) == 4:
                    try:
                        float(_parts[1]); float(_parts[2]); int(_parts[3])
                        _suggestion = {"router": "soft-bellman", "skill": _parts[0]}
                        break
                    except (ValueError, IndexError):
                        pass
            if _suggestion:
                ensemble_suggestions.append(_suggestion)
        except Exception:
            pass

        # 2. kl-skill-prior: --top 3 QUERY_TOKENS (positional tokens after --top)
        try:
            _proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "kl-skill-prior.py"),
                 "--top", "3"] + query_text.split(),
                capture_output=True, text=True, timeout=5,
            )
            _kl_data = json.loads(_proc.stdout) if _proc.returncode == 0 and _proc.stdout.strip() else []
            if _kl_data and isinstance(_kl_data, list) and _kl_data[0].get("name"):
                ensemble_suggestions.append({
                    "router": "kl-prior",
                    "skill": _kl_data[0]["name"],
                    "kl": _kl_data[0].get("kl"),
                    "score": _kl_data[0].get("score"),
                })
        except Exception:
            pass

        # 3. pareto-phase-router: --task QUERY --dry-run
        try:
            _proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "pareto-phase-router.py"),
                 "--task", query_text, "--dry-run"],
                capture_output=True, text=True, timeout=5,
            )
            # Output: table line "  TASK_PREVIEW  PHASE  SELECTED_ROUTES"
            # Last non-empty data line after the header contains routes
            _selected = None
            _lines = [l.strip() for l in _proc.stdout.splitlines() if l.strip()]
            for _line in _lines:
                _cols = _line.split()
                # Data rows have phase digit (1 or 2) in col -2
                if len(_cols) >= 3 and _cols[-2] in ("1", "2"):
                    _selected = _cols[-1]  # route name (last col)
                    break
                # Alternatively parse "selected" from route() JSON-style rationale
            if _selected:
                ensemble_suggestions.append({"router": "pareto-phase", "route": _selected})
        except Exception:
            pass

        # 4. privacy-constrained-skill-router: --task QUERY --skill any --dry-run
        try:
            _proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "privacy-constrained-skill-router.py"),
                 "--task", query_text, "--skill", "any", "--dry-run"],
                capture_output=True, text=True, timeout=5,
            )
            # Parse verdict from output: "✓/✗  task_preview  skill  verdict"
            _verdict = None
            for _line in _proc.stdout.splitlines():
                _s = _line.strip()
                if _s.startswith(("✓", "✗", "ALLOW", "BLOCK")):
                    _verdict = _s[:80]
                    break
            if _verdict:
                ensemble_suggestions.append({"router": "privacy-constrained", "verdict": _verdict})
        except Exception:
            pass

        # 5. online-threshold-skill-router: positional QUERY
        try:
            _proc = subprocess.run(
                [sys.executable, str(_SCRIPTS / "online-threshold-skill-router.py"),
                 query_text],
                capture_output=True, text=True, timeout=5,
            )
            # Parse "Selected: SKILL_NAME" line from output
            _selected = None
            for _line in _proc.stdout.splitlines():
                if _line.strip().startswith("Selected:"):
                    _selected = _line.strip().split("Selected:", 1)[-1].strip()
                    break
            if _selected:
                ensemble_suggestions.append({"router": "online-threshold", "skill": _selected})
        except Exception:
            pass

        if ensemble_suggestions:
            # Attach ensemble suggestions to the first result (or as standalone key)
            if results:
                results[0]["ensemble_suggestions"] = ensemble_suggestions
            else:
                results = [{"ensemble_suggestions": ensemble_suggestions, "score": 0.0,
                            "name": "", "description": "", "category": ""}]

    return results


def cmd_query(query_text: str):
    skills, idf, index = load_index_with_tfidf()
    q_tokens = tokenize(query_text)
    # Query vectorisation: use BM25 TF to match document scoring.
    # For short queries, length normalisation (b) is set to 0 (avgdl=dl=1 → no length penalty).
    # k1 same as document scoring (1.5) for symmetric term saturation.
    # Source: adversarial review Sep 2026 — raw TF/BM25-IDF asymmetry vs doc BM25-TF/BM25-IDF.
    BM25_K1_Q = 1.5
    q_tf = defaultdict(float)
    for t in q_tokens:
        q_tf[t] += 1
    q_vec_raw = {}
    for t, freq in q_tf.items():
        tf_bm25 = (freq * (BM25_K1_Q + 1)) / (freq + BM25_K1_Q)  # b=0: no length norm on queries
        q_vec_raw[t] = tf_bm25 * idf.get(t, 0.0)
    q_norm = math.sqrt(sum(v * v for v in q_vec_raw.values())) or 1.0
    q_vec = {t: v / q_norm for t, v in q_vec_raw.items()}

    beta_state = load_beta_state()
    beta_active = bool(beta_state)  # H5 fix: only blend if writer has produced data
    scored = [
        (
            (0.6 * cosine(q_vec, s["tfidf"]) + 0.4 * beta_posterior_mean(s["name"], beta_state))
            if beta_active else cosine(q_vec, s["tfidf"])
        ) + cross_domain_boost(query_text, s.get("description", ""))
        for s in skills
    ]
    scored = list(zip([score for score in scored], skills))
    scored.sort(key=lambda x: -x[0])

    # ── Semantic reranking: concept-lattice fallback when BM25 is ambiguous ──
    LATTICE_SCRIPT = Path(_os_sri.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "concept-lattice-index.py"
    AMBIGUITY_GAP  = 0.12
    LATTICE_BOOST  = 0.15
    semantic_reranked = False

    if len(scored) >= 2:
        gap = scored[0][0] - scored[1][0]
        if gap < AMBIGUITY_GAP and LATTICE_SCRIPT.exists():
            try:
                _lat_result = subprocess.run(
                    [sys.executable, str(LATTICE_SCRIPT),
                     "--query", query_text, "--top-k", "5"],
                    capture_output=True, text=True, timeout=10,
                )
                lattice_hits = (
                    json.loads(_lat_result.stdout)
                    if _lat_result.returncode == 0 else []
                )
            except Exception:
                lattice_hits = []

            if lattice_hits:
                # Collect skill names/intents mentioned in lattice hits
                lattice_names: set = set()
                for _hit in lattice_hits:
                    for _member in _hit.get("members", []):
                        lattice_names.add(_member.lower())
                    for _intent in _hit.get("intent", []):
                        lattice_names.add(_intent.lower())

                # Boost BM25 candidates that appear in lattice hits
                _boosted = []
                for _score, _s in scored:
                    _name_l = _s["name"].lower()
                    if any(_name_l in _ln or _ln in _name_l for _ln in lattice_names):
                        _score += LATTICE_BOOST
                    _boosted.append((_score, _s))
                scored = sorted(_boosted, key=lambda x: -x[0])
                semantic_reranked = True

    print(f"Top 5 matches for: '{query_text}'\n")
    for rank, (score, s) in enumerate(scored[:5], 1):
        desc = s["description"][:70].replace("\n", " ")
        # PAC-Bayes-kl interval is display-only; ranking still uses posterior mean.
        _entry = beta_state.get(s["name"], {})
        _mean, _lo, _hi, _m, _kl = pac_bayes_bound(
            float(_entry.get("alpha", 1.0)),
            float(_entry.get("beta", 1.0)),
        )
        _ci_str = f"  reliability={_mean:.2f} [{_lo:.2f},{_hi:.2f}]" if beta_state else ""
        _rerank_tag = "  [semantic_reranked]" if semantic_reranked and rank == 1 else ""
        print(f"  {rank}. {score:.3f}{_ci_str}{_rerank_tag} | {s['name']:<45} | {desc}")


def cmd_pattern_check():
    """SIP-3: Lint skill trigger patterns for over-complexity.

    Flags descriptions that are >15 words or contain nested conditional
    keywords (if/when/and/or used to stack multiple conditions), which
    suggests the trigger may be irregular or ambiguous.
    """
    print("SIP-3: Pattern complexity check\n")
    skills = scan_skills()
    if not skills:
        print("No skills found. Run --build first or check SKILLS_ROOT.", file=sys.stderr)
        return

    WORD_LIMIT = 15
    NESTED_COND_RE = re.compile(
        r"\b(if|when)\b.{0,80}\b(if|when)\b",  # two condition keywords in close proximity
        re.IGNORECASE,
    )
    LONG_AND_OR_RE = re.compile(
        r"\b(and|or)\b.*\b(and|or)\b.*\b(and|or)\b",  # 3+ conjunctions = multi-branch
        re.IGNORECASE,
    )

    flagged = []
    clean = []
    for skill in skills:
        description = skill["description"]
        triggers = skill["triggers"]
        # Check description + each trigger phrase
        texts_to_check = [(description, "description")] + [(t, f"trigger[{i}]") for i, t in enumerate(triggers)]
        skill_flags = []
        for text, label in texts_to_check:
            if not text.strip():
                continue
            words = text.split()
            reasons = []
            if len(words) > WORD_LIMIT:
                reasons.append(f"{len(words)} words > {WORD_LIMIT} limit")
            if NESTED_COND_RE.search(text):
                reasons.append("nested conditional (if/when … if/when)")
            if LONG_AND_OR_RE.search(text):
                reasons.append("3+ conjunctions (multi-branch condition)")
            if reasons:
                skill_flags.append((label, text[:120], reasons))
        if skill_flags:
            flagged.append((skill["name"], skill_flags))
        else:
            clean.append(skill["name"])

    total = len(skills)
    print(f"Scanned {total} skills  |  flagged={len(flagged)}  clean={len(clean)}\n")
    if flagged:
        print("=== POTENTIALLY OVER-COMPLEX PATTERNS ===\n")
        for skill_name, flags in flagged:
            print(f"  Skill: {skill_name}")
            for label, text, reasons in flags:
                print(f"    [{label}] {text!r}")
                for r in reasons:
                    print(f"       ↳ {r}")
            print()
    else:
        print("All patterns look concise — no over-complex triggers found.")

    return flagged


def cmd_compile_patterns():
    """SIP-4: Compile skill trigger descriptions as keyword-extracted regex patterns.

    Steps:
      1. Extract all trigger/description text from skills.
      2. Build a keyword regex via tokenise (stopword-stripped alpha tokens).
      3. Detect nested-quantifier backtracking risk: (a+)+ style patterns.
      4. Replace risky patterns with atomic-group / possessive alternatives.
    Reports compiled count and warnings.
    """
    print("SIP-4: Compile and inspect trigger regex patterns\n")
    skills = scan_skills()
    if not skills:
        print("No skills found. Run --build first.", file=sys.stderr)
        return

    NESTED_QUANT_RE = re.compile(r"\([^)]*[+*][^)]*\)[+*?]")  # (a+)+ style

    compiled_ok = 0
    warnings = []

    for skill in skills:
        # Combine description and triggers for keyword extraction
        raw_texts = [skill["description"]] + skill["triggers"]
        combined = " ".join(raw_texts)
        keywords = tokenize(combined)
        if not keywords:
            continue

        # Build a keyword-OR regex: \b(kw1|kw2|...)\b  (safe, no backtracking risk)
        pattern_str = r"\b(" + "|".join(re.escape(kw) for kw in dict.fromkeys(keywords)) + r")\b"

        # Check for nested quantifiers in the generated pattern
        has_risk = bool(NESTED_QUANT_RE.search(pattern_str))

        try:
            compiled = re.compile(pattern_str, re.IGNORECASE)
            compiled_ok += 1
        except re.error as exc:
            warnings.append((skill["name"], pattern_str[:100], f"compile error: {exc}"))
            continue

        if has_risk:
            # Replace nested quantifiers with non-backtracking alternatives
            # Strategy: convert (X+)+ → (?:X+) (collapse to single quantifier)
            safe_str = re.sub(r"\(([^)]*[+*][^)]*)\)([+*?])", r"(?:\1)", pattern_str)
            try:
                re.compile(safe_str, re.IGNORECASE)
                warnings.append((
                    skill["name"],
                    pattern_str[:80],
                    f"nested-quantifier risk detected → replaced with non-backtracking: {safe_str[:80]}"
                ))
            except re.error as exc:
                warnings.append((skill["name"], pattern_str[:80], f"replace failed: {exc}"))

    print(f"Successfully compiled: {compiled_ok} skill patterns")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):\n")
        for skill_name, pat, msg in warnings:
            print(f"  Skill : {skill_name}")
            print(f"  Pattern: {pat}")
            print(f"  Warning: {msg}\n")
    else:
        print("No backtracking risk or compile errors found.")


def cmd_check():
    skills, idf, index = load_index_with_tfidf()
    print(f"Checking {len(skills)} skills for high-overlap pairs (threshold={OVERLAP_THRESHOLD})...\n")
    flags = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            sim = cosine(skills[i]["tfidf"], skills[j]["tfidf"])
            if sim >= OVERLAP_THRESHOLD:
                flags.append((sim, skills[i]["name"], skills[j]["name"]))

    flags.sort(reverse=True)
    if not flags:
        print("No high-overlap pairs found. Library routing diversity looks healthy.")
        return

    print(f"Found {len(flags)} high-overlap pairs:\n")
    for sim, a, b in flags:
        print(f"  {sim:.3f}  {a}  <->  {b}")

    print(f"\n(These pairs may confuse routing — consider tightening descriptions or merging)")


def _print_worked_example() -> None:
    """Worked PAC-Bayes example: α=10, β=3 (uniform prior Beta(1,1))."""
    alpha, beta = 10.0, 3.0
    mean_q, pb_lo, pb_hi, m, kl_qp = pac_bayes_bound(alpha, beta, delta=0.05)
    _, wald_lo, wald_hi = _beta_wald_ci(alpha, beta)
    print("PAC-Bayes worked example")
    print("  Q = Beta(alpha=10, beta=3)  P = Beta(1,1)  delta=0.05")
    print("  (9 hits / 11 observations under a uniform prior; mean ≈ 10/13)")
    print(f"  mean(Q)                 = {mean_q:.6f}")
    print(f"  Wald 95% CI             = [{wald_lo:.6f}, {wald_hi:.6f}]")
    print(f"  PAC-Bayes 95% (quality) = [{pb_lo:.6f}, {pb_hi:.6f}]")
    print(f"  KL(Q||P)                = {kl_qp:.6f}")
    print(f"  m (observations)        = {m:.0f}")


def main():
    parser = argparse.ArgumentParser(description="SkillRouter: semantic index over Hermes skill descriptions")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--build", action="store_true", help="Build index from all skills")
    group.add_argument("--query", metavar="TEXT", help="Query top-5 matching skills")
    group.add_argument("--check", action="store_true", help="Flag high-overlap pairs")
    group.add_argument("--pattern-check", action="store_true",
                       help="SIP-3: Lint skill trigger patterns for over-complexity (>15 words, nested conditions)")
    group.add_argument("--compile-patterns", action="store_true",
                       help="SIP-4: Compile trigger descriptions as regex patterns; report backtracking risks")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="With --query: print results as JSON array instead of table")
    args = parser.parse_args()

    if args.build:
        cmd_build()
    elif args.query:
        if args.as_json:
            print(json.dumps(route(args.query), indent=2))
        else:
            cmd_query(args.query)
    elif args.check:
        cmd_check()
    elif args.pattern_check:
        cmd_pattern_check()
    elif args.compile_patterns:
        cmd_compile_patterns()
    else:
        _print_worked_example()


if __name__ == "__main__":
    main()

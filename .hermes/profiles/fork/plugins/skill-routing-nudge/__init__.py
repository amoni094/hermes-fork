"""skill-routing-nudge -- pre_llm_call plugin for Hermes fork.

Injects a compact BM25 skill routing hint into the user message context when
the query is substantive (>=8 words) and routing confidence is high (score >=0.3,
top-2 gap >=0.1 or top score >=0.5).

Hook kwargs for pre_llm_call (from _collect_pre_llm_call_context):
  user_message, session_id, task_id, turn_id, conversation_history,
  is_first_turn, model, platform, parent_session_id, sender_id, agent

Return: dict with 'context' key (str) injected into user message; or empty dict.

Governance: H-I8 HIGH (plugin_add). Governance proposal required before enabling.
H-I7: fail-open. Entire plugin in try/except. Never raises into host.
H-I6: stdlib only (json, pathlib, os, re, logging, importlib).

Source: SkillRouter arXiv:2603.22455; Revised Rec 2 post-adversarial audit 2026-10-29.
Enabled: NO (plugin.yaml enabled:false; set true only after governance approval)
"""
from __future__ import annotations
import importlib.util, json, logging, math, os, re, sys
from pathlib import Path
from typing import Any

logger = logging.getLogger('skill-routing-nudge')

ISS_GAIN = 0.3
EPS_DP = 0.0

MIN_SCORE = 0.3
MIN_GAP = 0.1
MIN_WORDS = 8
MAX_RESULTS = 3
SAFETY_SKILLS = {'recursive-adversarial-hardening', 'amodei-concrete-ai-safety'}
SAFETY_MIN_SCORE = 0.2
STOPWORDS = {
    'the','a','an','is','in','on','at','to','for','of','and','or','with',
    'use','when','how','what','this','that','it','be','are','was','not','from',
    'do','i','you','my','me','can','should','will','would','if','as','by',
}


def _router_script_path() -> Path:
    """Canonical live router script path."""
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', '')
    if profile:
        return base / 'profiles' / profile / 'scripts' / 'skill-router-index.py'
    return base / 'scripts' / 'skill-router-index.py'


def _load_index_with_tfidf() -> tuple[list[dict], dict] | None:
    """Import skill-router-index.py and call load_index_with_tfidf().
    Returns (skills, idf) or None on any error. Fail-open."""
    try:
        script = _router_script_path()
        if not script.exists():
            return None
        spec = importlib.util.spec_from_file_location('_skill_router_idx', str(script))
        if spec is None or spec.loader is None:
            return None
        # Check if already loaded (same path, re-use cached module)
        mod_key = f'_skill_router_idx_{script.stat().st_mtime_ns}'
        if mod_key in sys.modules:
            mod = sys.modules[mod_key]
        else:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_key] = mod
            spec.loader.exec_module(mod)
        fn = getattr(mod, 'load_index_with_tfidf', None)
        if fn is None:
            return None
        skills, idf, _index = fn()
        return skills, idf
    except Exception as exc:
        logger.debug('skill-routing-nudge: _load_index_with_tfidf error: %s', exc)
        return None


def _tokenize(text: str) -> list[str]:
    tokens = re.split(r'[^a-z0-9]+', text.lower())
    return [t for t in tokens if t and len(t) > 1 and t not in STOPWORDS]


def _cosine(q_vec: dict, doc_vec: dict) -> float:
    """Dot product (both already L2-normalised)."""
    return sum(q_vec.get(t, 0.0) * doc_vec.get(t, 0.0) for t in q_vec)


def _score_query(user_msg: str, skills: list[dict], idf: dict) -> list[tuple[float, dict]]:
    """BM25 cosine scoring — mirrors cmd_query in skill-router-index.py."""
    q_tokens = _tokenize(user_msg)
    if not q_tokens:
        return []
    from collections import defaultdict
    BM25_K1_Q = 1.5
    q_tf: dict[str, float] = defaultdict(float)
    for t in q_tokens:
        q_tf[t] += 1
    q_vec_raw: dict[str, float] = {}
    for t, freq in q_tf.items():
        tf_bm25 = (freq * (BM25_K1_Q + 1)) / (freq + BM25_K1_Q)
        q_vec_raw[t] = tf_bm25 * idf.get(t, 0.0)
    q_norm = math.sqrt(sum(v * v for v in q_vec_raw.values())) or 1.0
    q_vec = {t: v / q_norm for t, v in q_vec_raw.items()}

    scored = [((_cosine(q_vec, s.get('tfidf', {}))), s) for s in skills]
    scored.sort(key=lambda x: -x[0])
    return scored


def _on_pre_llm_call(
    user_message: str = '',
    session_id: str | None = None,
    **kwargs: Any,
) -> dict:
    """Inject BM25 skill routing hint into user message. Fail-open."""
    try:
        if not isinstance(user_message, str):
            user_message = str(user_message or '')
        if len(user_message.split()) < MIN_WORDS:
            return {}

        result = _load_index_with_tfidf()
        if result is None:
            return {}
        skills, idf = result
        if not skills:
            return {}

        scored = _score_query(user_message, skills, idf)
        if not scored or scored[0][0] < MIN_SCORE:
            return {}

        top_score = scored[0][0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        gap = top_score - second_score

        if gap < MIN_GAP and top_score < 0.5:
            return {}  # ambiguous

        results: list[tuple[float, dict]] = []
        seen: set[str] = set()
        safety_found: list[tuple[float, dict]] = []

        for score, skill in scored:
            name = skill.get('name', '')
            if not name or name in seen:
                continue
            seen.add(name)
            if name in SAFETY_SKILLS and score >= SAFETY_MIN_SCORE:
                safety_found.append((score, skill))
            elif score >= MIN_SCORE and len(results) < MAX_RESULTS:
                results.append((score, skill))

        for item in safety_found:
            if item not in results:
                results.insert(0, item)
        results = results[:MAX_RESULTS]

        if not results:
            return {}

        lines = [
            '[SKILL ROUTING HINT]',
            'Top skill matches for this query:',
        ]
        for i, (score, skill) in enumerate(results, 1):
            name = skill.get('name', '')
            desc = (skill.get('description') or '').strip()
            if len(desc) > 80:
                desc = desc[:77] + '...'
            lines.append(f'  {i}. {name} ({score:.2f}) - {desc}')
        lines.append("Load with skill_view(name=\'...\') if relevant.")
        lines.append('[END HINT]')

        return {'context': '\n'.join(lines)}

    except Exception as exc:
        logger.debug('skill-routing-nudge error: %s', exc)
        return {}


def register(ctx: Any) -> None:
    """Register with Hermes plugin context. Fail-open on registration error."""
    try:
        ctx.register_hook('pre_llm_call', _on_pre_llm_call)
        logger.debug('skill-routing-nudge: registered pre_llm_call hook')
    except Exception as exc:
        logger.warning('skill-routing-nudge: failed to register: %s', exc)

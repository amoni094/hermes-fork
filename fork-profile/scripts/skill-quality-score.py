#!/usr/bin/env python3
# skill-quality-score.py — ACES/SkillEvaluator Tier 1 static quality score for SKILL.md
# stdlib only. Score 0-100, grades A/B/C/D, weighted dimensions.
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_HH = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_HP = os.environ.get('HERMES_PROFILE', '')
_PROFILE_ROOT = _HH if (_HP and _HH.name == _HP and _HH.parent.name == 'profiles') else ((_HH / 'profiles' / _HP) if _HP else _HH)
SKILLS_DIR = _PROFILE_ROOT / 'skills'

WEIGHTS = {
    'correctness': 35,
    'discoverability': 25,
    'reliability': 25,
    'efficiency': 15,
}

_TOPIC_WORDS = frozenset({
    'skill', 'skills', 'quality', 'score', 'scoring', 'check', 'audit', 'eval',
    'evaluator', 'evaluation', 'memory', 'routing', 'router', 'graph', 'linux',
    'python', 'script', 'scripts', 'monitor', 'compression', 'context', 'bandit',
    'safety', 'agent', 'fork', 'development', 'retrieval', 'forgetting',
    'analysis', 'interpretation', 'algorithm', 'algorithms', 'probability',
    'geometry', 'topology', 'theory', 'control', 'optimization', 'network',
    'security', 'research', 'tax', 'mining', 'property', 'browser', 'firefox',
    'android', 'windows', 'review', 'test', 'testing', 'config', 'cron',
    'plugin', 'governance', 'loop', 'gate', 'gates', 'budget', 'entropy',
    'latency', 'integrity', 'strength', 'wiki', 'yield', 'index', 'prune',
    'pruning', 'calibration', 'confidence', 'evidence', 'info', 'cost',
    'spectral', 'ranking', 'shadow', 'spacing', 'scheduler', 'beta', 'seed',
    'feedback', 'covariance', 'compliance', 'communication',
    'install', 'installation', 'software', 'remote', 'management', 'scan',
    'scanning', 'vulnerability', 'privacy', 'hardening', 'theme', 'input',
    'keybinds', 'cleanup', 'maintenance', 'host', 'session', 'handoff',
    'consensus', 'swarm', 'compaction', 'recall', 'consolidator',
    'ontology', 'legal', 'harness', 'product', 'consumer', 'design', 'office',
    'docx', 'xlsx', 'notion', 'airtable', 'media', 'song', 'gif', 'pdf',
    'section', 'extraction', 'debugger', 'inspect', 'authoring', 'author',
    'static', 'abstract', 'dataflow', 'effects', 'sandbox', 'capability',
    'capabilities', 'least', 'authority', 'coverage', 'ledger', 'verify',
    'verifier', 'deductive', 'hallucination', 'detector', 'alignment',
    'corrigibility', 'foundations', 'induction', 'anytime', 'interruptible',
    'profiles', 'real', 'time', 'schedule', 'scheduling',
    'distributed', 'lock', 'lease', 'statecharts', 'state', 'machine',
    'zookeeper', 'watch', 'deadline', 'periodic', 'task', 'tasks', 'queue',
    'load', 'balancing', 'performance', 'modeling', 'causal', 'causality',
    'pearl', 'anderson', 'cousot', 'dean', 'boddy', 'zilberstein',
    'wavelet', 'signal', 'vision', 'quantum', 'information', 'transport',
    'category', 'algebra', 'number', 'galois', 'homology', 'cohomology', 'logic', 'type', 'types', 'semantics',
    'compiler', 'kernel', 'cryptography', 'learning', 'deep',
    'reinforcement', 'bandits', 'online', 'computation', 'database',
    'databases', 'measure', 'integration', 'martingale',
    'markov', 'mixing', 'optimal', 'nonlinear',
    'dynamics', 'chaos', 'combinatorics', 'graphs', 'coding',
    'channel', 'capacity', 'inference', 'bayesian', 'decision',
    'game', 'mechanism', 'approximation', 'complexity', 'computability',
    'automata', 'proof', 'sheaf', 'sheaves', 'homotopy', 'univalent',
    'domain', 'coalgebra', 'linear', 'functional', 'differential', 'lie', 'groups', 'modules', 'rings',
    'fields', 'schemes', 'varieties', 'class', 'field', 'etale',
    'brownian', 'motion', 'rough', 'paths', 'spde', 'odes', 'pdes',
    'wavelets', 'sparse', 'search', 'filter', 'first', 'schema', 'tool', 'token', 'health', 'cusum', 'mesh', 'heal', 'obstruction',
    'certificate', 'cache', 'saturation', 'parametric', 'ripple',
    'anchor', 'expansion', 'fulltext', 'full', 'text', 'compositional', 'decompose', 'pipeline', 'orchestrator', 'fixes', 'regression', 'prevention', 'isolation',
    'upstream', 'merge', 'wiring', 'improvement', 'implementation', 'extrapolation',
    'bottleneck', 'hermes', 'desktop', 'dom', 'css',
    'node', 'rate', 'distortion', 'statecomp', 'timing', 'span', 'readiness', 'cross', 'lingual',
    'induced', 'prospective', 'suppression',
    'interference', 'sam', 'shiffrin', 'raaijmakers', 'sound', 'components', 'ai', 'accident',
    'risk', 'anchored', 'distillation', 'floatsam', 'compress',
    'phone', 'ssh', 'adb', 'pcs', 'tailscale',
    'protonvpn', 'kill', 'switch', 'cli', 'vaultwarden', 'homelab',
    'pi', 'raspberry', 'embedded', 'device', 'setup', 'waybar',
    'module', 'hyprland', 'wallust', 'layer', 'github', 'pr', 'adversarial', 'pre', 'push', 'local', 'two', 'axis',
    'sqlite', 'wal', 'concurrent', 'writes',
    'technitium', 'dns', 'admin', 'blocks', 'traffic',
    'history', 'places', 'login', 'decryption',
    'fingerprinting', 'policies',
    'defaults', 'flatpak', 'games', 'rulesets',
    'web', 'app', 'api',
    'reverse', 'engineering', 'tplink', 'ax55', 'auth',
    'led', 'saltzer', 'schroeder', 'miller',
    'ocap', 'benchmark', 'narrowing',
    'au', 'business', 'location', 'company', 'return',
    'personal', 'deductions', 'investment',
    'suburb', 'ipo', 'geology',
    'capital', 'junior', 'asx', 'screen', 'veto',
    'mineral', 'occurrence', 'spatial', 'site', 'barristers', 'case', 'law', 'biotech', 'opportunity',
    'commercial', 'aware', 'adaptation',
    'experience', 'amortized', 'unified',
    'llm', 'karpathy', 'markdown', 'kb',
    'songsee', 'audio', 'spectrogram', 'mel', 'chroma', 'mfcc',
    'tenor', 'box', 'cloud',
    'files', 'sharing', 'metadata', 'pages',
    'workers', 'word', 'powerpoint',
    'excel', 'csv', 'tree',
    'grilling', 'plan', 'underspecified', 'microsoft',
    'pymupdf',
    'devtools', 'protocol',
    'cdp', 'frontmatter', 'structure', 'fit', 'bias', 'selection', 'vera', 'therapy', 'extensions',
    'opencode', 'delegate', 'subagent', 'spawn',
    'failure', 'timeout', 'recovery', 'sage', 'decomp',
    'autonomous', 'agents', 'runtime', 'patterns', 'fast', 'slow', 'camofox', 'retry',
    'server', 'scraping',
    'fracture', 'billion', 'scale', 'knobs', 'book', 'to', 'converts',
    'documents', 'epub', 'html', 'wave', 'iss', 'sprt', 'hello', 'waves',
    'dispatch', 'from', 'scratch',
    'post', 'home', 'io', 'guard',
    'third', 'party',
    'safe', 'branch',
    'stack', 'graphiti', 'hindsight',
    'embeddings', 'missed', 'retrieve', 'serpantinum', 'shell', 'startup', 'race',
    'editing', 'sed',
    'prima', 'migrations', 'monotonic',
    'curino', 'devops',
    'correctness', 'discoverability', 'reliability', 'efficiency',
    'aces', 'tier', 'yaml',
    'procedure', 'example', 'command', 'commands',
    'lessons', 'pitfalls', 'trigger', 'triggers',
    'description', 'tags',
    'model', 'checking', 'temporal', 'atomic', 'edf', 'rm', 'pcp', 'realtime',
    'ftrl', 'regret', 'competitive', 'ratio',
    'mdl', 'solomonoff', 'universal', 'aixi', 'hutter',
    'mesa', 'deceptive',
    'prepotence', 'multi', 'principal',
    'shapley', 'fabricated', 'provenance',
    'epistemic', 'assertions', 'knowledge',
    'logical', 'uncertainty',
    'calibrating', 'beliefs',
    'ngo', 'dl', 'nielson', 'program', 'cfa',
    'rival', 'yi',
    'slepian', 'wolf', 'wyner', 'ziv',
    'deduplicating', 'correlated',
    'redundant', 'facts',
    'jev', 'system', 'one',
    'ji', 'survey',
    'llms4ol', 'lm', 'polygraph', 'ue',
    'lynch', 'manna', 'pnueli',
    'clarke', 'ctl', 'ltl',
    'buttazzo', 'borodin', 'elyaniv',
    'amodei', 'concrete',
    'hubinger', 'soares',
    'critch', 'considerations',
    'garrabrant',
    'fagin', 'reasoning',
    'harchol', 'balter',
    'motwani', 'raghavan', 'randomized',
    'scaling', 'steiner',
    'fan', 'outs',
    'progress', 'mirage', 'verification',
    'recursive', 'mem',
    'evograph', 'bps', 'selector', 'portfolio',
    'cmtf', 'filtering', 'minimal',
    'centric',
    'cliff', 'ccr',
    'over', 'write',
    'rag',
    'md', 'spec',
    'applied', 'siting',
    'ctr', 'tpar',
    'barrister',
    'deduction',
    'rest',
    'ntn',
    'inspecting', 'ipv',
    'rejection',
    'in', 'process',
    'scrape',
    'wave21b', 'wave21c',
    'productivity',
    'systems',
    'textbook',
})

_SHORT_TOPIC = frozenset({
    'ml', 'rl', 'os', 'db', 'ui', 'api', 'pdf', 'dns', 'ssh', 'git',
    'sql', 'nlp', 'ot', 'ir', 'ue', 'ai', 'ct', 'dl', 'gp', 'md', 'pr', 'au', 'cli', 'css', 'dom', 'cdp', 'rag',
    'mdp', 'ctl', 'ltl', 'edf', 'rm', 'wal', 'adb',
    'ipo', 'asx', 'ctr', 'kb',
})

_FUNC_WORDS = re.compile(
    r'\b(use|when|for|with|from|that|which|this|check|run|apply|'
    r'build|score|scan|how|after|before|during|against|into|over|'
    r'under|via|using|where)\b',
    re.IGNORECASE,
)

_ABS_PATH = re.compile(
    r'(?<![\w:/])(/(?:home|var/home|Users|root)/[A-Za-z0-9_.+-]+)'
)

_REF_FILE = re.compile(
    r'(?:^|[\s(`\[\'\"])((?:(?:\./)?references/)[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)',
    re.MULTILINE,
)

_CODE_FENCE = '```'
_INLINE_CMD = re.compile(r'`[^`\n]{1,240}`')
_STEP_LIST = re.compile(r'(?m)^(?:\s*)(?:\d+[\.\)]\s+\S|[-*+]\s+\S)')
_HEADING = re.compile(r'(?m)^(#{1,6})\s+(.+?)\s*$')
_LESSONS = re.compile(r'(?im)^#{1,6}\s+(lessons|pitfalls|pitfall)\b')
_TODO = re.compile(r'(?i)\b(TODO|FIXME)\b|\bSTUB\b')
_TRIGGER = re.compile(r'(?i)\buse\s+(when|for)\b')


def _unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        return v[1:-1]
    if v.endswith('  #') or '  #' in v:
        v = v.split('  #', 1)[0].strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            return v[1:-1]
    return v


def _parse_flow_list(raw: str) -> list:
    inner = raw.strip()
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1].strip()
    if not inner:
        return []
    return [_unquote(part.strip()) for part in inner.split(',') if part.strip()]


def _parse_yaml_simple(fm: str) -> dict:
    data: dict = {}
    lines = fm.split('\n')
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith('#'):
            i += 1
            continue
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest.startswith('[') and rest.endswith(']'):
            data[key] = _parse_flow_list(rest)
            i += 1
            continue
        if rest in ('', '|', '>', '|-', '>-'):
            is_block_scalar = rest in ('|', '>', '|-', '>-')
            items: list = []
            nested: dict = {}
            block_lines: list = []
            i += 1
            while i < n:
                nl = lines[i]
                if nl.strip() and not nl[:1].isspace():
                    break
                lm = re.match(r'^\s+-\s+(.*)$', nl)
                if lm:
                    items.append(_unquote(lm.group(1)))
                    i += 1
                    continue
                km = re.match(r'^\s+([A-Za-z0-9_]+):\s*(.*)$', nl)
                if km:
                    nk, nv = km.group(1), km.group(2).strip()
                    if nv.startswith('[') and nv.endswith(']'):
                        nested[nk] = _parse_flow_list(nv)
                    elif nv:
                        nested[nk] = _unquote(nv)
                    else:
                        nested[nk] = {}
                    i += 1
                    continue
                # Plain indented text — block scalar body
                if is_block_scalar and nl.strip():
                    block_lines.append(nl.strip())
                i += 1
            if items:
                data[key] = items
            elif nested:
                data[key] = nested
            elif block_lines:
                data[key] = ' '.join(block_lines)
            else:
                data[key] = ''
            continue
        data[key] = _unquote(rest)
        i += 1
    return data


def parse_frontmatter(text: str) -> tuple[dict, str, str]:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not text.startswith('---'):
        return {}, text, ''
    end = text.find('\n---', 3)
    if end < 0:
        return {}, text, ''
    fm_text = text[3:end].strip('\n')
    body = text[end + 4:]
    body = body.removeprefix('\n')
    return _parse_yaml_simple(fm_text), body, fm_text


def _extract_tags(data: dict, fm_text: str) -> list:
    tags = data.get('tags')
    if isinstance(tags, list) and any(str(x).strip() for x in tags):
        return [str(x).strip() for x in tags if str(x).strip()]
    if isinstance(tags, str) and tags.strip():
        return [tags.strip()]
    md = data.get('metadata')
    if isinstance(md, dict):
        hermes = md.get('hermes')
        if isinstance(hermes, dict):
            ht = hermes.get('tags')
            if isinstance(ht, list) and any(str(x).strip() for x in ht):
                return [str(x).strip() for x in ht if str(x).strip()]
            if isinstance(ht, str) and ht.strip():
                return [ht.strip()]
        ht2 = md.get('tags')
        if isinstance(ht2, list) and any(str(x).strip() for x in ht2):
            return [str(x).strip() for x in ht2 if str(x).strip()]
    m = re.search(r'(?m)^\s*tags:\s*\[([^\]]*)\]', fm_text)
    if m and m.group(1).strip():
        return _parse_flow_list('[' + m.group(1) + ']')
    lines = fm_text.split('\n')
    items = []
    for i, line in enumerate(lines):
        if re.match(r'^\s*tags:\s*$', line):
            for nl in lines[i + 1:]:
                lm = re.match(r'^\s+-\s+(\S.*)$', nl)
                if lm:
                    items.append(_unquote(lm.group(1)))
                elif nl.strip() and not nl[:1].isspace() or re.match(r'^\s+\S', nl) and not nl.strip().startswith('-'):
                    break
            break
    return items


def _is_pure_keywords(desc: str) -> bool:
    s = (desc or '').strip()
    if not s:
        return True
    if re.search(r'[.!?]', s):
        return False
    if _FUNC_WORDS.search(s):
        return False
    if ',' in s or ';' in s or '|' in s:
        return True
    words = re.findall(r'[A-Za-z0-9]+', s)
    return len(words) <= 2


def _has_topic_word(name: str) -> bool:
    parts = [
        p for p in re.split(r'[-_./]', (name or '').lower())
        if p and not re.fullmatch(r'\d{2,4}', p)
    ]
    if not parts:
        return False
    for p in parts:
        if p in _TOPIC_WORDS or p in _SHORT_TOPIC:
            return True
        if len(p) >= 6 and p.isalpha():
            return True
    return False


def _hardcoded_abs_paths(text: str) -> list:
    found = []
    for m in _ABS_PATH.finditer(text or ''):
        s = m.group(1)
        if '<' in s or '>' in s:
            continue
        found.append(s)
    return found


def _broken_references(body: str, skill_dir: Path | None) -> list:
    mentioned = []
    for m in _REF_FILE.finditer(body or ''):
        rel = m.group(1).lstrip('./')
        mentioned.append(rel)
    broken = []
    for rel in mentioned:
        if skill_dir is None:
            broken.append(rel)
            continue
        candidate = skill_dir / rel
        if not candidate.is_file():
            broken.append(rel)
    return broken


def _duplicate_headers(body: str) -> list:
    seen: dict[str, int] = {}
    dups = []
    for m in _HEADING.finditer(body or ''):
        title = re.sub(r'\s+', ' ', m.group(2).strip().rstrip('#').strip()).lower()
        if not title:
            continue
        seen[title] = seen.get(title, 0) + 1
    for title, count in seen.items():
        if count > 1:
            dups.append(title)
    return dups


def _empty_dimensions() -> dict:
    return {
        key: {'score': 0, 'max': maxv}
        for key, maxv in WEIGHTS.items()
    }


def grade_for(score: float) -> str:
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    return 'D'


def score_skill_text(text: str, skill_dir: Path | None = None, min_score: float = 70.0) -> dict:
    findings: list[str] = []
    data, body, fm_text = parse_frontmatter(text or '')
    name = data.get('name')
    if not isinstance(name, str):
        name = ''
    name = name.strip()
    desc = data.get('description')
    if not isinstance(desc, str):
        desc = ''
    desc = desc.strip()

    if not name:
        findings.append('CRITICAL: name field missing from frontmatter')
    if len(desc) < 10:
        findings.append('CRITICAL: description missing or < 10 chars')

    c = 0
    if len(desc) > 20 and not _is_pure_keywords(desc):
        c += 10
    else:
        findings.append('description too short or pure keywords')
    if _CODE_FENCE in body or _INLINE_CMD.search(body):
        c += 10
    else:
        findings.append('no code block or command pattern')
    if _STEP_LIST.search(body):
        c += 10
    else:
        findings.append('no numbered or bulleted procedure')
    broken = _broken_references(body, skill_dir)
    if not broken:
        c += 5
    else:
        for rel in broken:
            findings.append('broken internal reference: ' + rel)
    c = min(c, WEIGHTS['correctness'])

    d = 0
    if _TRIGGER.search(desc):
        d += 5
    else:
        findings.append("description missing concrete trigger ('Use when' / 'Use for')")
    tags = _extract_tags(data, fm_text)
    if tags:
        d += 5
    else:
        findings.append('tags field missing or empty')
    if _has_topic_word(name):
        d += 10
    else:
        findings.append('name lacks a recognizable topic word')
    if 20 <= len(desc) <= 100:
        d += 5
    else:
        findings.append('description length not in 20-100 chars')
    d = min(d, WEIGHTS['discoverability'])

    r = 0
    abs_paths = _hardcoded_abs_paths((fm_text + '\n' + body) if fm_text else body)
    if not abs_paths:
        r += 10
    else:
        findings.append('hardcoded absolute path: ' + abs_paths[0])
    if _LESSONS.search(body):
        r += 10
    else:
        findings.append('no Lessons or Pitfalls section')
    if not _TODO.search(body):
        r += 5
    else:
        findings.append('TODO/FIXME/STUB in body')
    r = min(r, WEIGHTS['reliability'])

    e = 0
    if len(body) < 5000:
        e += 5
    else:
        findings.append('body bloated (>= 5000 chars)')
    dups = _duplicate_headers(body)
    if not dups:
        e += 5
    else:
        findings.append('duplicate section header: ' + dups[0])
    if name and desc:
        e += 5
    else:
        findings.append('frontmatter missing name or description')
    e = min(e, WEIGHTS['efficiency'])

    total = float(c + d + r + e)
    if total > 100:
        total = 100.0
    grade = grade_for(total)
    critical = any(f.startswith('CRITICAL:') for f in findings)
    verdict = 'PASS' if (total >= float(min_score) and not critical) else 'FAIL'

    result = {
        'name': name,
        'score': total,
        'grade': grade,
        'dimensions': {
            'correctness': {'score': c, 'max': WEIGHTS['correctness']},
            'discoverability': {'score': d, 'max': WEIGHTS['discoverability']},
            'reliability': {'score': r, 'max': WEIGHTS['reliability']},
            'efficiency': {'score': e, 'max': WEIGHTS['efficiency']},
        },
        'findings': findings,
        'verdict': verdict,
    }
    return result


def score_skill_file(path: Path, min_score: float = 70.0) -> dict:
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        dims = _empty_dimensions()
        return {
            'name': path.parent.name,
            'path': str(path),
            'score': 0.0,
            'grade': 'D',
            'dimensions': dims,
            'findings': ['CRITICAL: unreadable file: ' + str(exc)],
            'verdict': 'FAIL',
        }
    result = score_skill_text(text, skill_dir=path.parent, min_score=min_score)
    result['path'] = str(path)
    if not result.get('name'):
        result['name'] = path.parent.name
    return result


def find_skill_files(skills_dir: Path) -> list[Path]:
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []
    results: list[Path] = []
    try:
        for child in skills_dir.iterdir():
            try:
                if child.is_dir():
                    results.extend(p for p in child.rglob('SKILL.md') if p.is_file())
                elif child.name == 'SKILL.md' and child.is_file():
                    results.append(child)
            except OSError:
                continue
    except OSError:
        return []
    uniq = sorted(set(results), key=lambda p: str(p).lower())
    return uniq


def match_skill(files: list[Path], name: str) -> list[Path]:
    want = name.strip().lower()
    hits = []
    for path in files:
        if path.parent.name.lower() == want:
            hits.append(path)
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        data, _, _ = parse_frontmatter(text)
        fm_name = data.get('name')
        if isinstance(fm_name, str) and fm_name.strip().lower() == want:
            hits.append(path)
    # unique preserve order
    out = []
    seen = set()
    for p in hits:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def format_report(results: list[dict], min_score: float) -> str:
    rows = sorted(results, key=lambda r: (r.get('score', 0), r.get('name') or ''))
    lines = [
        'SCORE  GRADE  VERDICT  NAME',
        '-----  -----  -------  ----',
    ]
    for r in rows:
        lines.append(
            '{:5.1f}  {:^5}  {:<7}  {}'.format(
                float(r.get('score', 0)),
                r.get('grade', 'D'),
                r.get('verdict', 'FAIL'),
                r.get('name') or r.get('path') or '',
            )
        )
    n = len(results)
    n_pass = sum(1 for r in results if r.get('verdict') == 'PASS')
    n_fail = n - n_pass
    mean = (sum(float(r.get('score', 0)) for r in results) / n) if n else 0.0
    lines.append('')
    lines.append(
        f'{n} skills, {n_pass} pass, {n_fail} fail, mean={mean:.1f}, min_score={min_score}'
    )
    return '\n'.join(lines)


def self_test() -> int:
    good = (
        '---\n'
        'name: skill-quality-score\n'
        'description: Use when scoring SKILL.md files for static quality.\n'
        'tags: [skills, quality, scoring]\n'
        '---\n'
        '\n'
        '# Skill Quality Score\n'
        '\n'
        'Run `python3 skill-quality-score.py --report` on the skills directory.\n'
        '\n'
        '## Procedure\n'
        '1. Parse frontmatter\n'
        '2. Score each dimension\n'
        '3. Emit the report\n'
        '\n'
        '```bash\n'
        'python3 skill-quality-score.py --json\n'
        '```\n'
        '\n'
        '## Pitfalls\n'
        '- Missing name or short description is CRITICAL\n'
    )
    r = score_skill_text(good)
    assert r['score'] == 100.0, r
    assert r['grade'] == 'A', r
    assert r['verdict'] == 'PASS', r
    assert r['dimensions']['correctness']['score'] == 35, r
    assert r['dimensions']['discoverability']['score'] == 25, r
    assert r['dimensions']['reliability']['score'] == 25, r
    assert r['dimensions']['efficiency']['score'] == 15, r
    assert not any(f.startswith('CRITICAL:') for f in r['findings']), r

    bad = (
        '---\n'
        'name: x\n'
        'description: no\n'
        '---\n'
        'plain body without structure\n'
    )
    r2 = score_skill_text(bad)
    assert r2['grade'] == 'D', r2
    assert r2['verdict'] == 'FAIL', r2
    assert r2['score'] < 70, r2
    assert any('CRITICAL:' in f for f in r2['findings']), r2

    noname = (
        '---\n'
        'description: Use when doing a thing that is long enough.\n'
        '---\n'
        '# Hi\n'
    )
    r3 = score_skill_text(noname)
    assert r3['verdict'] == 'FAIL', r3
    assert any('name field missing' in f for f in r3['findings']), r3

    r4 = score_skill_text('')
    assert r4['verdict'] == 'FAIL', r4
    assert r4['grade'] == 'D', r4

    high_but_critical = score_skill_text(good.replace(
        'name: skill-quality-score\n',
        '',
    ))
    assert high_but_critical['verdict'] == 'FAIL', high_but_critical
    assert any('CRITICAL:' in f for f in high_but_critical['findings']), high_but_critical

    broken = good.replace(
        '## Pitfalls\n',
        'See references/missing-file.md\n\n## Pitfalls\n',
    )
    rb = score_skill_text(broken, skill_dir=Path('/nonexistent/skill-dir'))
    assert rb['dimensions']['correctness']['score'] == 30, rb
    assert any('broken internal reference' in f for f in rb['findings']), rb

    payload = json.dumps(r)
    parsed = json.loads(payload)
    assert parsed['grade'] == 'A'

    print('self-test ok')
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description='ACES/SkillEvaluator Tier 1 static quality score for SKILL.md'
    )
    p.add_argument('--skills-dir', type=Path, default=None, help='directory to scan')
    p.add_argument('--skill', default=None, help='single skill name')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--report', action='store_true', help='human-readable table (default)')
    p.add_argument('--min-score', type=float, default=70.0, help='pass threshold (default 70)')
    p.add_argument('--self-test', action='store_true', help='synthetic skill assertion, exit 0')
    args = p.parse_args(argv)

    if args.self_test:
        try:
            return self_test()
        except AssertionError as exc:
            print('self-test FAIL: ' + str(exc), file=sys.stderr)
            return 1

    skills_dir = args.skills_dir if args.skills_dir is not None else SKILLS_DIR
    files = find_skill_files(skills_dir)
    if args.skill:
        files = match_skill(files, args.skill)
        if not files:
            print('ERROR: skill not found: ' + args.skill, file=sys.stderr)
            return 2

    results = [score_skill_file(path, min_score=args.min_score) for path in files]
    if args.json:
        envelope = {
            'min_score': args.min_score,
            'n': len(results),
            'skills': results,
        }
        print(json.dumps(envelope, indent=2))
    else:
        print(format_report(results, args.min_score))
    return 0


if __name__ == '__main__':
    sys.exit(main())

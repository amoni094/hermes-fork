---
name: hermes-config-research-sync
related_skills: [hermes-research, hermes-cs-research, hermes-math-research]
description: "Use when syncing research to hermes-config git."
triggers:
  - upload research to git
  - sync research to hermes-config
  - keep research reference log updated
not_for:
  - running new research sweeps
  - updating synthesis topic files manually
---

# hermes-config Research Sync

Mirrors ALL agent-relevant research reference files from `~/.hermes/skills/research/` into
`~/hermes-config/research/references/` and commits. Mechanical, not editorial.

## Sources to sync

1. arxiv-sweep-findings/references/*.md  ->  research/references/arxiv-sweep-findings/
2. llm-agent-memory-pipeline-research/references/*.md  ->  research/references/llm-agent-memory-pipeline-research/
3. academic-literature-review/references/ AGENT files only  ->  research/references/academic-literature-review/
   Include globs: agent-* ai-agent* hermes-* human-oversight* japanese-korean* mcp-protocol*
                  multilingual-agent* multilingual-institutional* neurosymbolic* noneng-agent*
                  personal-brain* rag-robustness* reference-files* research-master* research-skill*
                  subagent-loop* token-economics* token-optimization*
   Exclude: legal* trading* momentum* pead* finance* migraine* yoga* au-* zen* factor*
            odt* pubmed* pitfalls* multilingual*sources* arxiv-api* arxiv-direct* arxiv-sweep-source*
4. domain-research-synthesis/references/agent-*.md  (glob, picks up all future agent files)
   ->  research/references/domain-research-synthesis/
5. domain-research-synthesis/references/vervaeke-*.md  (RR critique files)
   ->  research/references/domain-research-synthesis/
6. lecture-transcript-summarization/references/vervaeke-*.md  (AMTMC transcripts)
   ->  research/references/lecture-transcript-summarization/
7. ROUTING.md  ->  research/ROUTING.md

## Generated Index Files (regenerate on each sync)

These are generated from cache JSON files, not rsync'd from skill refs:

- research/math-papers.md    — all math corpus papers from ~/.hermes/cache/research/hermes-math-sweep-latest.json
- research/cs-papers.md      — all CS corpus papers from ~/.hermes/cache/research/hermes-cs-sweep-latest.json
- research/relevance-realization-corpus.md  -- Vervaeke AMTMC corpus listing (static, update manually)
- research/signal-noise-it-papers.md         -- papers from IT-for-agents, rr-compaction-scorer, context-hygiene,
  context-budgeting skills; regenerate by extracting arXiv IDs from those skill SKILL.md files

Generate script (run BEFORE git add):
```python
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

base = Path.home() / '.hermes/cache/research'
dest = Path.home() / 'hermes-config/research'

# Math
math_sweep = json.loads((base / 'hermes-math-sweep-latest.json').read_text())
all_math = math_sweep.get('all_papers', [])
math_interp = json.loads((base / 'math-interpretation-latest.json').read_text())
spike_ids = {p.get('id','') for p in (math_interp.get('spikes',[]) or []) if isinstance(p,dict)}
opt_ids = {p.get('id','') for p in (math_interp.get('optimizations',[]) or []) if isinstance(p,dict)}
by_cat = defaultdict(list)
for p in all_math:
    by_cat[p.get('category','unknown')].append(p)
lines = [f'# Math Research Corpus -- Paper Index', '', f'Generated: {datetime.now():%Y-%m-%d}',
         f'Total papers: {len(all_math)}', '']
for cat in sorted(by_cat):
    lines.append(f'### {cat} ({len(by_cat[cat])} papers)'); lines.append('')
    for p in by_cat[cat]:
        pid=p.get('id',''); v=' [SPIKE]' if pid in spike_ids else (' [OPT]' if pid in opt_ids else '')
        title=p.get('title','').strip()
        lines.append(f"- arXiv:{pid} -- {title or p.get('url','')}{v}")
    lines.append('')
(dest / 'math-papers.md').write_text('\n'.join(lines))

# CS
cs_sweep = json.loads((base / 'hermes-cs-sweep-latest.json').read_text())
all_cs = cs_sweep.get('all_papers', [])
cs_spikes = json.loads((base / 'cs-spike-queue.json').read_text())
cs_spike_ids = {i.get('id',i.get('arxiv_id','')) for i in cs_spikes.get('items',[]) if isinstance(i,dict)}
by_cat2 = defaultdict(list)
for p in all_cs:
    by_cat2[p.get('category','unknown')].append(p)
lines2 = [f'# CS Research Corpus -- Paper Index', '', f'Generated: {datetime.now():%Y-%m-%d}',
          f'Total papers: {len(all_cs)}', '']
for cat in sorted(by_cat2):
    lines2.append(f'### {cat} ({len(by_cat2[cat])} papers)'); lines2.append('')
    for p in by_cat2[cat]:
        pid=p.get('id',''); v=' [SPIKE]' if pid in cs_spike_ids else ''
        lines2.append(f"- arXiv:{pid} -- {p.get('title','').strip() or p.get('url','')}{v}")
    lines2.append('')
(dest / 'cs-papers.md').write_text('\n'.join(lines2))
print(f'Math: {len(all_math)} papers, CS: {len(all_cs)} papers')
```

## Script

```bash
BASE=~/.hermes/skills/research
DEST=~/hermes-config/research

mkdir -p $DEST/references/arxiv-sweep-findings
rsync -av $BASE/arxiv-sweep-findings/references/*.md $DEST/references/arxiv-sweep-findings/

mkdir -p $DEST/references/llm-agent-memory-pipeline-research
rsync -av $BASE/llm-agent-memory-pipeline-research/references/*.md \
  $DEST/references/llm-agent-memory-pipeline-research/

mkdir -p $DEST/references/academic-literature-review
ACLR=$BASE/academic-literature-review/references
for f in agent-* ai-agent* hermes-* human-oversight* japanese-korean* mcp-protocol* \
  multilingual-agent* multilingual-institutional* neurosymbolic* noneng-agent* \
  personal-brain* rag-robustness* reference-files* research-master* research-skill* \
  subagent-loop* token-economics* token-optimization*; do
  [ -f "$ACLR/$f" ] && rsync -av "$ACLR/$f" $DEST/references/academic-literature-review/
done

mkdir -p $DEST/references/domain-research-synthesis
for f in $BASE/domain-research-synthesis/references/agent-*.md; do
  [ -f "$f" ] && rsync -av "$f" $DEST/references/domain-research-synthesis/
done
# Vervaeke critique files
for f in $BASE/domain-research-synthesis/references/vervaeke-*.md; do
  [ -f "$f" ] && rsync -av "$f" $DEST/references/domain-research-synthesis/
done

# Vervaeke AMTMC lecture transcripts (relevance realization corpus)
mkdir -p $DEST/references/lecture-transcript-summarization
for f in $BASE/lecture-transcript-summarization/references/vervaeke-*.md; do
  [ -f "$f" ] && rsync -av "$f" $DEST/references/lecture-transcript-summarization/
done

rsync -av $BASE/ROUTING.md $DEST/ROUTING.md

# Regenerate math/CS paper indexes from cache
python3 - <<'PYEOF'
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

base = Path.home() / '.hermes/cache/research'
dest = Path.home() / 'hermes-config/research'

# Math papers index
math_sweep = json.loads((base / 'hermes-math-sweep-latest.json').read_text())
all_math = math_sweep.get('all_papers', [])
math_interp = json.loads((base / 'math-interpretation-latest.json').read_text())
spike_ids = {p.get('id','') for p in (math_interp.get('spikes',[]) or []) if isinstance(p,dict)}
opt_ids = {p.get('id','') for p in (math_interp.get('optimizations',[]) or []) if isinstance(p,dict)}
by_cat = defaultdict(list)
for p in all_math:
    by_cat[p.get('category','unknown')].append(p)
lines = ['# Math Research Corpus -- Paper Index', '',
         f'Generated: {datetime.now():%Y-%m-%d}', f'Total papers: {len(all_math)}', '']
for cat in sorted(by_cat):
    lines.append(f'### {cat} ({len(by_cat[cat])} papers)'); lines.append('')
    for p in by_cat[cat]:
        pid=p.get('id',''); v=' [SPIKE]' if pid in spike_ids else (' [OPT]' if pid in opt_ids else '')
        title=p.get('title','').strip()
        lines.append(f"- arXiv:{pid} -- {title or p.get('url','')}{v}")
    lines.append('')
(dest / 'math-papers.md').write_text('\n'.join(lines))

# CS papers index
cs_sweep = json.loads((base / 'hermes-cs-sweep-latest.json').read_text())
all_cs = cs_sweep.get('all_papers', [])
cs_spikes = json.loads((base / 'cs-spike-queue.json').read_text())
cs_spike_ids = {i.get('id',i.get('arxiv_id','')) for i in cs_spikes.get('items',[]) if isinstance(i,dict)}
by_cat2 = defaultdict(list)
for p in all_cs:
    by_cat2[p.get('category','unknown')].append(p)
lines2 = ['# CS Research Corpus -- Paper Index', '',
          f'Generated: {datetime.now():%Y-%m-%d}', f'Total papers: {len(all_cs)}', '']
for cat in sorted(by_cat2):
    lines2.append(f'### {cat} ({len(by_cat2[cat])} papers)'); lines2.append('')
    for p in by_cat2[cat]:
        pid=p.get('id',''); v=' [SPIKE]' if pid in cs_spike_ids else ''
        lines2.append(f"- arXiv:{pid} -- {p.get('title','').strip() or p.get('url','')}{v}")
    lines2.append('')
(dest / 'cs-papers.md').write_text('\n'.join(lines2))
print(f'Math: {len(all_math)} papers, CS: {len(all_cs)} papers')
PYEOF

cd ~/hermes-config
git add research/
git diff --cached --stat
git commit -m "research: sync all research skill references ($(date +%Y-%m-%d))"
```

## After sync
- Update 5 synthesis .md files if new sweeps added (trajectory-research-synthesis-to-skills)
- Update research/README.md coverage dates if arXiv cutoff advanced
- Push: cd ~/hermes-config && git push

## Exclusions (never include)
- Personal: psych, schema therapy, religion corpus
- Financial/trading/legal reference files
- Medical/clinical files
- Operational pitfall notes (arxiv-api-fallback, odt-reading)

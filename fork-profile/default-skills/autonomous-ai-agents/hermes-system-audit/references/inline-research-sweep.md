# Inline Recursive Research Sweep

For "research X and implement until saturated" requests outside the weekly cron cycle.
Runs entirely in `execute_code`; does NOT write to `seen_papers.json`.

## Step 1: Build exclusion set (apply report only)

```python
import json, re
from pathlib import Path

apply_txt = Path('~/.hermes/cache/research/hermes-research-apply-latest.md').expanduser().read_text()
# Only exclude already-implemented IDs, NOT the full 2000-entry seen_papers.json
exclusion = set(re.findall(r'\b2[456]\d{2}\.\d{4,5}\b', apply_txt))
```

Do NOT use `seen_papers.json` as the exclusion set — it suppresses nearly all findings
because the cron sweep already touched every recent paper.

## Step 2: Wave-based search

Send 6-8 parallel `web_search` calls with different angle queries per domain
(memory, planning, multi-agent, security, observability, skill lifecycle, evaluation, RAG).
Extract arXiv IDs: `re.findall(r'\b2[456]\d{2}\.\d{4,5}\b', result_text)`.
Filter against exclusion set. Collect into fetch batch.

Also pull cs.AI and cs.MA recent listings directly for coverage:
`https://arxiv.org/list/cs.AI/recent` — extract all `abs/XXXX.XXXXX` links.

**Saturation criterion:** wave returns <3 new IDs OR 0 HIGH papers after triage.
Typically saturates in 3-4 waves (~30-50 papers scanned). Stop at wave 5 regardless.

## Step 3: Fetch abstracts via arXiv API

```python
from hermes_tools import web_extract
import re

def fetch_arxiv_api(ids, batch_size=10):
    papers = {}
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        url = f"https://export.arxiv.org/api/query?id_list={','.join(batch)}&max_results={batch_size}"
        r = web_extract([url], char_limit=20000)
        xml = r['results'][0]['content']
        for entry in re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL):
            m_id    = re.search(r'<id>.*?/abs/([\d.v]+)</id>', entry)
            m_title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            m_abs   = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            m_cats  = re.findall(r'<category term="([^"]+)"', entry)
            if m_id:
                papers[m_id.group(1).split('v')[0]] = {
                    'title':      re.sub(r'\s+', ' ', m_title.group(1)).strip() if m_title else '',
                    'abstract':   re.sub(r'\s+', ' ', m_abs.group(1)).strip()   if m_abs   else '',
                    'categories': m_cats,
                }
    return papers
```

## Step 4: Triage criteria (HIGH / MED / LOW)

For each paper, ask all four:
- Novel mechanism not already in Hermes?
- Concrete target (skill / script / config / cron)?
- Implementable in <1h by a subagent from abstract alone?
- Evidence strong enough to act on without reading full paper?

Typical output: 12-20 HIGH. More than 20 HIGH means the triage threshold is too loose.

## Step 5: Dispatch parallel implementation subagents

Group HIGH findings by target cluster (memory pipeline, skill routing, security,
observability, harness evolution, context engineering). One subagent per cluster.
**Disjoint file ownership** — never assign the same SKILL.md or .py to two subagents.
See hermes-system-audit `Parallel subagent architecture` section for dispatch pattern.

## Step 6: Cold adversarial pass

After all implementation subagents complete, dispatch fresh adversarial subagents
(no prior context, `claude-sonnet-4-6`) to review every modified file.
Use adversarial-review check matrix: A (contradictions), C (duplicates),
E (citation integrity), F (size >600 lines), G (routing specificity).

## Pitfall: string-replace audits miss live-config semantics

Bulk-replacing model names (e.g. `grok-4.5` → `grok-4.6`) without reading live config
will introduce contradictions — session parent may be Sonnet while the skill says grok-4.6.

Every model-name or config-value update must start from:
```bash
grep -E 'model:|provider:|threshold' ~/.hermes/config.yaml
```
Establish ground truth first, then apply per-occurrence — never as a bulk string replace.

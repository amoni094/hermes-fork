# GitHub Research Mining — 2025-2026 Patterns

Research date: August 2026. For academic paper context, see academic-literature-review/references/research-skill-improvements-2025-2026.md

---

## Bridge Tools: Paper → Code

### PaperFlow (papersflow.ai)
Enter an arXiv ID or DOI — auto-extracts all GitHub repos mentioned in the paper body,
footnotes, and appendices. Much faster than manual PDF scanning.
No API; web UI only. Use web_extract(["https://papersflow.ai/paper/arXiv:2402.03300"]) or browse.

### Papers With Code API
Canonical bridge: paper → code → benchmark → leaderboard.

```bash
# Search papers with linked repos
curl -s "https://paperswithcode.com/api/v1/papers/?q=QUERY" | python3 -m json.tool

# Find repos for a specific arXiv paper
curl -s "https://paperswithcode.com/api/v1/papers/arxiv:2402.03300/repositories/" | python3 -m json.tool

# Get benchmarks for a task
curl -s "https://paperswithcode.com/api/v1/tasks/?q=object+detection" | python3 -m json.tool

# Get top results for a benchmark
curl -s "https://paperswithcode.com/api/v1/evaluations/?benchmark_id=imagenet" | python3 -m json.tool
```

### Semantic Scholar + externalIds
Semantic Scholar returns GitHub links in the `externalIds` field for some papers.
Add `fields=externalIds,openAccessPdf` to any S2 paper query.

---

## GitHub Search Patterns for Research

### Awesome-list pattern (entry point)
```
"awesome {topic} papers 2025" OR "awesome {topic} survey"
"best-of-{topic} GitHub"
"survey {topic} papers GitHub"
```

Then filter:
- Last commit < 6 months ago (active maintenance)
- Issues open with responses (maintainer presence)
- README has dated update sections

### Research repo quality signals
| Signal | Good | Caution |
|--------|------|---------|
| Last commit | < 3 months | > 12 months |
| Stars | Context-dependent | High stars alone ≠ quality |
| Issues | Open + responses | All closed OR ignored |
| README | Reproducibility steps, deps pinned | "See paper" with no code |
| CI badge | Green | Missing or broken |
| License | MIT / Apache | No license (unresolvable) |

### Star count pitfalls
- Stars = community interest ≠ reproducibility or correctness
- A 2021 "21k star" project (e.g. Backtrader) can be less maintained than a 2024 "3k star" project
- Always combine star count with: last commit date + issue resolution rate + README quality
- Curated awesome-lists (40k stars) measure curation effort, not the individual tool's quality
- For SOTA claims: always cross-reference the Papers With Code leaderboard — "SOTA" in a README is often stale

---

## Purpose-Built Research Engineering Tools (2025-2026)

### AIDE (Weco AI)
ML engineering agent. Integrates arXiv + Papers With Code for code/research plans.
Auto-debugging loop. Best for: automated ML experiment iteration.
github.com/WecoAI/aideml

### RD-Agent (Microsoft)
R&D automation: reads paper → generates code → runs experiment → evaluates result.
Kaggle automation, paper-to-code pipeline.
github.com/microsoft/RD-Agent

### AI Scientist / AI Scientist-v2 (SakanaAI)
Full end-to-end research automation: ideation → experiment → paper writing.
12k+ stars. Best for: understanding what L3-L4 research automation looks like.
github.com/SakanaAI/AI-Scientist
Caveat: only 38% of comparable systems release reproducibility artifacts (arXiv:2608.05179).

### ToolMaker (AI4Science)
Converts papers with code into callable agent tools. Outputs structured function wrappers.
github.com/ai4s-research/awesome-ai-for-science (see ToolMaker section)

### AutoResearchClaw (aiming-lab)
Pipeline: paper → sandbox experiments → multi-agent review → LaTeX output.
github.com/aiming-lab — check for latest repo name (active 2025-2026)

### GPT-Researcher (assafelovic)
Modular OSS deep research agent. Pluggable search backends.
github.com/assafelovic/gpt-researcher

### deer-flow (ByteDance)
Open deep research pipeline, same team as PaSa.
github.com/bytedance/deer-flow

---

## Mining Software Repositories (MSR) Field

The MSR field formally studies automated repo analysis. Key patterns:
- **LLM-based repo analysis** (arXiv:2604.00787): survey of LLMs for mining software repos
- **ToolMaker pattern**: paper → extract model/method → wrap as callable tool → benchmark
- **Automated paper-to-experiment**: AIDE, RD-Agent, AutoResearchClaw all implement variants
- **Code search** via GitHub API: `https://api.github.com/search/code?q=QUERY+language:python`
  (1000 results/month unauthenticated; 5000/hour with token)

```bash
# GitHub code search
curl -s "https://api.github.com/search/repositories?q=QUERY+topic:machine-learning&sort=stars&order=desc" \
  -H "Accept: application/vnd.github.v3+json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data['items'][:10]:
    print(f\"{r['full_name']} — ★{r['stargazers_count']} — {r['description'][:80]}\")
    print(f\"  Updated: {r['updated_at'][:10]} | Lang: {r['language']} | {r['html_url']}\")
    print()
"

# Topic-based search
curl -s "https://api.github.com/search/repositories?q=topic:llm+topic:agent&sort=updated&order=desc&per_page=10" \
  -H "Accept: application/vnd.github.v3+json" | python3 -m json.tool
```

---

## GitHub + Academic Combined Workflow

For a new research topic:
1. Search arXiv (last 6 months, sorted by date)
2. For top 3 papers: PaperFlow → extract repos; PwC API → extract code + benchmarks
3. GitHub search: "awesome {topic} papers" → scan for curated lists < 6 months old
4. For each promising repo: check last commit date, issues, README quality
5. Stars check: verify vs PwC leaderboard position (repo with most stars ≠ SOTA)
6. For tools that matter: check if they have a pip package and test import locally

---

## Pitfalls

- **GitHub "awesome" lists go stale fast** — a list last updated in 2022 may omit 60% of current relevant work
- **"Has code" ≠ "code works"** — many papers release code that reproduces only a subset of reported results; check Issues for "cannot reproduce" reports
- **Star inflation** — repositories linked from a viral Twitter/X thread can gain 5k stars in 24h with no corresponding quality signal
- **SOTA in a README is often 6-18 months behind** — PwC leaderboard is updated continuously; README is updated sporadically
- **Non-English paper repos** — Chinese (CNKI/Wenjuanshu), Japanese (J-STAGE), and Korean (RISS) papers may have repos on Gitee, Hugging Face, or NAVER Clova — not GitHub — check those platforms if the paper is from a non-English institution
- **License ambiguity** — no license = all rights reserved by default (legally unresolvable for use); CC-BY / MIT / Apache = clear. CC-BY-NC blocks commercial use. Always check before production integration.

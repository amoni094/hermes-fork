# Research Skills — Routing Map
Updated: 2026-08-30

Quick-reference: which skill to load for which task.

## Academic research pipeline

| Task | Skill |
|------|-------|
| Search arXiv by keyword/ID/author | arxiv |
| Structured multi-source academic survey (multilingual, institutions) | academic-literature-review |
| Ground claims in cited verifiable sources | grounded-citations |
| Research agent memory topology for l1-pipeline improvements | llm-agent-memory-pipeline-research |

## Hermes self-improvement pipeline (distinct roles — do NOT conflate)

| Task | Skill |
|------|-------|
| Run / trigger the weekly sweep pipeline | hermes-research |
| Query what past sweeps found (findings bank) | arxiv-sweep-findings |
| Apply sweep findings as patches to skills | trajectory-research-synthesis-to-skills |

## Web access / extraction

| Task | Skill |
|------|-------|
| Scrape pages via local Firecrawl | firecrawl-research |
| Extract clean markdown from a URL | defuddle |
| Recover from 403/429/paywall | blocked-page-recovery |

## Domain landscape / synthesis

| Task | Skill |
|------|-------|
| Tool/framework/GitHub landscape for a practical domain | domain-research-synthesis |
| Named-company news monitoring | competitor-news-monitor |
| Long-form lecture/video transcript summary | lecture-transcript-summarization |
| Legal / regulatory research with citation discipline | legal-regulatory-research-writing |
| Multi-page visual doc review (wireframes, slides, PDFs) | visual-document-review |
| Agent Reach sidecar for news/social enrichment | agent-reach-discovery |

## Domain-specific research

| Task | Skill |
|------|-------|
| Religious text corpus analysis | comparative-religion-corpus |
| Structured computational text analysis | computational-text-corpus-analysis |

## Leisure / utility (note: live in research/ but not research skills)

| Task | Skill |
|------|-------|
| Cinema / Gold Class session finder | gold-class |
| Movie / TV recommendation | stay-in |
| Music recommendation | suggest-music |
| One-off product variant hunt (ships to AU) | product-availability-search |

## Fallback chain for any web content

web_extract -> defuddle -> firecrawl-research -> blocked-page-recovery

## Self-improvement pipeline chain

hermes-research (orchestrate) -> arxiv-sweep-findings (bank) -> trajectory-research-synthesis-to-skills (patch)

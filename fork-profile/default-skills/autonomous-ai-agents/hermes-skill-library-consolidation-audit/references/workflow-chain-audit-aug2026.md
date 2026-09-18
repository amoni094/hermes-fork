# Cross-Category Workflow Chain Audit — August 2026

Full audit of 10 workflow chains across all skill categories. Read before running
any targeted fix pass — this is the findings register; the fix scripts are in
`adversarial-review/references/skill-library-audit.md` (Defect classes A–F, 2026-08-14).

---

## 1. SOFTWARE-DEVELOPMENT chain

**Chain:** plan / complexity-gated-planning / isa → spike / TDD / subagent-driven-development →
risk-based-review / requesting-code-review / adversarial-review / hermes-coding-review-loop →
finishing-a-development-branch

**Status: ✅ CLEAN.** Handoffs explicit. `depends_on`/`provides`/`related_skills` traverse correctly.

**Open issues:**
- MEDIUM: `codeql` and `fp-check` appear in `requesting-code-review` and `risk-based-review` bodies.
  Labeled `(disabled)` inline — not a broken load, but noise.
- LOW: `hermes-coding-review-loop` references `hermes-operating-pattern` in related_skills.
  Confirm whether ghost ref was resolved (prior audit task).

---

## 2. DEVOPS chain

**Chain:** silverblue-system-update-trigger → hermes-agent-independent-update-protocol → daily-silverblue-update.sh

**Status: ✅ CLEAN.** Cross-reference between the two skills is explicit and correct.
Script path confirmed: `~/.hermes/scripts/daily-silverblue-update.sh`.
Thin wrapper `~/silverblue-update-all.sh` is equivalent.

**Open issues:**
- LOW: `kanban-swarm-nightly-ops` related_skills lists disabled `kanban-orchestrator` and
  `kanban-worker`. All three are `user_invocable: false` + in config disabled list. Internally
  consistent but still names disabled skills.

---

## 3. GITHUB workflow chain

**Chain:** github-operations → github-issues → github-issue-to-pr → scoped-pr-fix-and-verification →
split-ci-workflow-change-and-draft-pr

**Status: ✅ Correct chain. One structural bug.**

**Open issues:**
- HIGH: `github-operations` self-references itself in `related_skills` (lists `github-operations`
  in its own related_skills block). Copy-paste artifact. Fix: remove self-reference.
- LOW: `github-issues` has inconsistent dual declaration — metadata header lists `github-issue-agent`
  but YAML body `related_skills` block has a different list. Harmless but inconsistent.

---

## 4. PRODUCTIVITY cluster

**Skills audited:** document-to-action-items, docx, pdf, xlsx, meeting-action-items,
weekly-review-planning, session-librarian, local-personal-dashboard

**Status: Multiple structural defects. See Defect classes B, C, D in skill-library-audit.md.**

**Open issues:**
- HIGH: `pdf` skill self-references itself in body YAML `related_skills: [grounded-citations, pdf]`.
  Template artifact. Fix: remove spurious body block.
- HIGH: `xlsx`, `docx`, `session-librarian` have spurious body `related_skills: [grounded-citations, pdf]`.
  Same template artifact. `session-librarian` referencing `pdf` and `grounded-citations` is wrong.
- HIGH: `pdf`, `docx`, `xlsx` metadata related_skills reference disabled `powerpoint`.
- HIGH: `pdf` and `document-to-action-items` reference disabled `ocr-and-documents` in metadata.
  `pdf` body routes scanned PDFs to `ocr-and-documents` with NO disabled caveat — agents following
  this hit a dead end. (document-to-action-items body DOES note it's disabled correctly.)
- MEDIUM: `weekly-review-planning` body references disabled `thunderbird-cli-anything` in body
  (step 2 text on line ~44). Body text does note it's disabled; fix is wording cleanup.
- LOW: `session-librarian` and `xlsx` `related_skills` add `grounded-citations` — irrelevant to
  session management / spreadsheet editing. Template noise.

**Scope separation:** ✅ CLEAN. document-to-action-items vs meeting-action-items are distinct.
weekly-review-planning, session-librarian, local-personal-dashboard all non-overlapping.

---

## 5. SUPERPOWERS chain

**Chain:** using-superpowers → brainstorming → dispatching-parallel-agents → executing-plans →
finishing-a-development-branch → using-git-worktrees → writing-skills

**Status: ✅ CLEAN. One missing link.**

**Open issues:**
- LOW: `dispatching-parallel-agents` not listed in `using-superpowers` related_skills despite
  being a primary multi-agent dispatch path. Add it.

**Overlap with SOFTWARE-DEVELOPMENT:** intentional and correct — superpowers is the entry/routing
layer; software-development skills are the execution layer. No duplication of content.

---

## 6. RESEARCH cluster

**Skills audited:** academic-literature-review, arxiv, arxiv-sweep-findings, blocked-page-recovery,
competitor-news-monitor, defuddle, domain-research-synthesis, firecrawl-research, gold-class,
grounded-citations, lecture-transcript-summarization, llm-agent-memory-pipeline-research,
stay-in, suggest-music, visual-document-review

**Status: One MEDIUM chain inconsistency. Otherwise well-structured.**

**Open issues:**
- MEDIUM: Fallback chain order inconsistency — `defuddle` says it's step 2 (`web_extract →
  defuddle → firecrawl-research → blocked-page-recovery`); `academic-literature-review` says it's
  step 3 (`web_extract → firecrawl-research → defuddle → blocked-page-recovery`). Canonical
  (correct) order is the academic-literature-review version. Fix: update `defuddle` trigger to
  say "step 3 in the fallback chain, after firecrawl-research fails."
- MEDIUM: `competitor-news-monitor` metadata related_skills still lists disabled
  `political-source-monitoring`. Body text correctly notes it's disabled. Fix: remove from metadata.
- LOW: `political-source-monitoring` is disabled in config but SKILL.md has no in-skill disabled
  marker. Future agents reading the skill won't know it's disabled without checking config.yaml.
- LOW: `suggest-music` missing `metadata.hermes.related_skills` key (has top-level only).
- LOW: `visual-document-review` references `defuddle` in related_skills — unclear relevance.
  `defuddle` is for web page extraction, not pixel-level visual document review.

**NOT-gate routing:** ✅ CLEAN. All research skills have explicit NOT-gates pointing to siblings.
**Trigger accuracy:** ✅ CLEAN. gold-class / stay-in / suggest-music correctly scoped as personal
recommendation tools.

---

## 7. NOTE-TAKING cluster

**Skills:** obsidian, obsidian-research-ingestion

**Status: Mostly clean. One integration documentation gap.**

**Open issues:**
- MEDIUM: `obsidian` skill has NO mention of the Graphiti write step that was added to
  `obsidian-research-ingestion` step 6b. An agent using only `obsidian` skill for vault work
  won't know to write Graphiti episodes. Recommendation: add a one-line pointer in `obsidian`
  pitfalls section: "For research ingestion → Graphiti dual-write, see obsidian-research-ingestion."

**Scoping:** ✅ CLEAN. `obsidian` owns filesystem vault ops; `obsidian-research-ingestion` owns
the inbox → resources pipeline. `obsidian-research-ingestion`'s Graphiti step (6b) is internally
consistent and correctly placed.

---

## 8. EMAIL

**Skills:** email-inbox-triage (in email/), email-compose-and-send (in email/)

**Status: Categorization artifact. Skills themselves are correct.**

**Open issues:**
- MEDIUM: System prompt skill index shows `email-compose-and-send` under the `autonomous-ai-agents:`
  category. Physical SKILL.md is at `email/email-compose-and-send/SKILL.md` — correct location.
  This is a Hermes system prompt rendering artifact, not a file placement issue. No file fix
  needed; track as a Hermes router bug.
- LOW: `email-compose-and-send` has inconsistent dual `related_skills` declarations — metadata
  header lists `[messaging-consent-boundaries, computer-use]`; YAML frontmatter body block lists
  `[autonomous-agent-loop-design, verification-before-completion]`. YAML last-key-wins means the
  body block wins. Fix: consolidate to one list in the metadata header; remove body block.
- LOW: `email-inbox-triage` line 22 names `thunderbird-cli-anything` without disabled caveat
  (line 42 has the caveat). Mildly confusing; rewrite line 22 to say "email-compose-and-send"
  as the primary connector (not naming the disabled skill at all).

---

## 9. Disabled-skill reference scan results

Full grep across all SKILL.md files. Summary:

| Disabled skill | Refs in active skills | Severity |
|---|---|---|
| `codeql` | requesting-code-review body (labeled disabled), risk-based-review body | MEDIUM |
| `fp-check` | requesting-code-review body (labeled disabled), risk-based-review body | MEDIUM |
| `kanban-orchestrator` | kanban-swarm-nightly-ops related_skills | LOW |
| `kanban-worker` | kanban-swarm-nightly-ops related_skills | LOW |
| `nano-pdf` | pdf skill body (says "nano-pdf is disabled") | LOW (informative, not a load trigger) |
| `powerpoint` | docx, pdf, xlsx metadata related_skills | HIGH |
| `ocr-and-documents` | pdf body (no caveat!), document-to-action-items (with caveat), visual-document-review body, xlsx metadata | HIGH (pdf body case) |
| `research-document-output` | docx body ("Complements research-document-output") | MEDIUM (no disabled note) |
| `thunderbird-cli-anything` | email-inbox-triage body ×2, weekly-review-planning body | MEDIUM |
| `rich-pdf-generation` | Own SKILL.md only | LOW |
| `source-backed-wiki-curation` | Own SKILL.md only | LOW |
| `political-source-monitoring` | competitor-news-monitor trigger NOT-gate + metadata related_skills | MEDIUM |

No references to `codeql`, `fp-check`, `kanban-orchestrator`, `kanban-worker`,
`rich-pdf-generation`, `source-backed-wiki-curation` found outside their own files or devops/ context.

---

## 10. hermes-web-provider-configuration — post serpapi→searxng switch

**Status: ✅ NO UPDATE REQUIRED.**

- `hermes config get web.search_backend` → `searxng` (confirmed active)
- `SEARXNG_URL=http://localhost:8888` in `.env` (confirmed present)
- Skill body correctly references SerpAPI only as a new-provider-from-scratch example — not
  as the active backend. SearXNG setup guidance in §8 and `references/local-searxng-podman-revival.md`
  is correct for the current setup.
- `SERPAPI_API_KEY` and `SERPAPI_API_KEY_FALLBACK` still present in `.env` as stale keys.
  Not a skill issue; housekeeping cleanup for a foreground session.

---

## Priority fix order

1. **pdf skill**: remove self-ref from body related_skills; add "(disabled — use pdf/docx directly)" to all `ocr-and-documents` routing lines in body
2. **xlsx, docx, session-librarian**: remove spurious body `related_skills: [grounded-citations, pdf]` template blocks
3. **github-operations**: remove `github-operations` self-reference from related_skills
4. **pdf, docx, xlsx metadata**: remove disabled `powerpoint` from metadata related_skills
5. **defuddle trigger**: change to "step 3 in fallback chain (after firecrawl-research)"
6. **competitor-news-monitor metadata**: remove disabled `political-source-monitoring` from related_skills
7. **docx body**: add "(disabled)" note next to `research-document-output` reference
8. **obsidian**: add pointer to obsidian-research-ingestion for Graphiti write step

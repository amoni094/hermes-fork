---
name: book-corpus-ingestion
description: "Use when ingesting books into the Hermes skill library."
related_skills:
  - knowledge-corpus-architecture
  - dispatching-parallel-agents
---

# Book Corpus Ingestion

Turns a book or document into a queryable Hermes knowledge skill using book-to-skill. Covers license check, download, extraction preflight, text extraction, and subagent generation delegation for large books (>100K tokens).

Requires: `book-to-skill` skill installed; `pdftotext` (poppler-utils) on host. `docling` is optional — pdftotext fallback is sufficient.

## Step 0 — Inventory what is already local

Before downloading anything, check what is already present. The canonical local library is `~/books/`, organized by domain subdirectory. Also scan `~/Downloads/` for books not yet moved.

```bash
find ~/books -name '*.pdf' | sort | while read f; do
  pages=$(pdfinfo "$f" 2>/dev/null | grep Pages | awk '{print $2}')
  echo "$pages pp | $f"
done
find ~/Downloads -name '*.pdf' -o -name '*.djvu' 2>/dev/null | sort
```

Cross-reference against skills already created under `~/.hermes/skills/research/` — a book with chapters/ present has been ingested. A book with only a SKILL.md but no chapters/ may be incomplete.

```bash
ls ~/.hermes/skills/research/ | sort
find ~/.hermes/skills/research -type d -name 'chapters' | sort
```

Do NOT download a book that is already in `~/books/` at full size (> 500KB). Do NOT create a skill for a book that already has a complete chapters/ directory.

## Step 1 — Verify license

Confirm the source is freely distributable:
- Cambridge open-access grants (e.g. MacKay ITILA at inference.org.uk): explicitly open for online viewing
- arXiv preprints: always open
- Purchased PDFs: personal use only — keep skill private, never publish

## Step 2 — Download

```bash
mkdir -p ~/books/<domain>
curl -L -o ~/books/<domain>/<slug>.pdf "<url>"
ls -lh ~/books/<domain>/<slug>.pdf   # confirm non-zero size
```

Some hosts have expired or locally-unverifiable SSL certs (e.g. cds.caltech.edu). If curl exits 60 (SSL verify failed), retry with `-k` after confirming the URL is the author's official host:

```bash
curl -L -k -o ~/books/<domain>/<slug>.pdf "<url>"
```

Do NOT use `-k` for arbitrary hosts — only for documented author/publisher domains where the cert failure is a known infra issue.

## Step 2b — Verify the PDF is real and extractable

Before extracting, confirm the file is not a stub, review page, or broken download:

```bash
pdfinfo ~/books/<domain>/<slug>.pdf | grep -E 'Pages|Producer|Creator'
pdftotext -f 3 -l 4 ~/books/<domain>/<slug>.pdf - | head -6
```

- Size under 200KB for a "book" = almost certainly a stub (journal citation, review page). Get the real file.
- 190 bytes = empty/broken download. Re-download.
- `pdftotext` returns blank output = scanned image PDF. Needs OCR (see Step 2c).

## Step 2c — OCR scanned PDFs (no text layer)

If `pdftotext` returns blank, the PDF is image-based. OCR it first:

```bash
# Install tesseract inside fedora-toolbox-44 (create once)
toolbox create --image registry.fedoraproject.org/fedora-toolbox:44   # if no container yet
toolbox run sudo dnf install -y tesseract tesseract-langpack-eng

# Verify via podman exec (toolbox run has a flatpak-spawn threading bug in CLI sessions)
podman exec fedora-toolbox-44 tesseract --version

# Test a sample page
pdftoppm -r 300 -png -f 5 -l 5 ~/books/<domain>/<slug>.pdf /tmp/test_page
podman exec fedora-toolbox-44 tesseract /tmp/test_page-005.png stdout -l eng 2>/dev/null | head -8
```

Do NOT use `toolbox run tesseract` — it fails with `GLib-ERROR: creating thread: Resource temporarily unavailable` in non-interactive shell contexts. Use `podman exec fedora-toolbox-44 tesseract` directly.

For the full OCR ingestion, pass the scanned PDF path in the subagent goal with these instructions:
- Rasterize all pages: `pdftoppm -r 300 -png <pdf> /tmp/<slug>_pages/page` (300 DPI for clear text; use 200 DPI for 1000+ page books to save space)
- OCR in batches of 50-100 pages per terminal call (timeout=600) appending to a single text file
- Write OCR output to `/tmp/book_skill_work_<slug>/full_text.txt` (NOT the shared `/tmp/book_skill_work/`)
- Expect ~2000 words per page; check with `wc -w`

## Step 3 — Preflight the extractor

```bash
python3 ~/.hermes/skills/book-to-skill/scripts/extract.py --check
```

Look for `-> ready` on the PDF row. Missing docling is fine.

## Step 4 — Extract text

```bash
python3 ~/.hermes/skills/book-to-skill/scripts/extract.py \
    ~/books/<domain>/<slug>.pdf \
    --mode technical \
    --install-missing no
```

Output lands in `/tmp/book_skill_work/full_text.txt` and `/tmp/book_skill_work/metadata.json`. Check the metadata token count:
- < 50K tokens: run generation in-session
- > 100K tokens: delegate to a subagent

If running multiple books in parallel, copy each book's extraction to a named dir immediately after extraction to prevent collision:

```bash
mkdir -p /tmp/book_skill_work_<slug>
cp /tmp/book_skill_work/full_text.txt /tmp/book_skill_work_<slug>/
cp /tmp/book_skill_work/metadata.json /tmp/book_skill_work_<slug>/
```

Tell each subagent to read from its own `/tmp/book_skill_work_<slug>/` path, not the shared `/tmp/book_skill_work/`.

## Step 5 — Delegate generation (large books)

Constraints to include in the subagent goal:
- Text is already at `/tmp/book_skill_work/full_text.txt` — skip re-extraction
- Use `read_file` with `offset`/`limit` for chapter slices; never read the full file in one shot
- Find chapter heading line numbers with `search_files` or `terminal grep` first
- Write skill to `~/.hermes/skills/research/<skill-name>/`
- Produce all chapter files, `glossary.md`, `patterns.md`, `cheatsheet.md`, and master `SKILL.md`
- Substitute ALL template placeholders before dispatching (see Pitfalls)

## Step 5b — Timeout recovery (subagent timed out mid-generation)

Subagents for large books (48+ chapters) can time out at the 900s limit. Before re-dispatching:

```bash
# Check what was actually produced
ls ~/.hermes/skills/research/<skill-name>/chapters/ | wc -l
ls ~/.hermes/skills/research/<skill-name>/*.md 2>/dev/null
```

If chapters were partially written, dispatch a continuation agent with:
- Explicit "chapters 1-N are done, start from chapter N+1"
- "Do NOT re-process chapters already in chapters/"
- List the still-needed supporting files (SKILL.md, glossary.md, patterns.md, cheatsheet.md)
- Source text path confirmed still available at `/tmp/book_skill_work_<slug>/full_text.txt`

Partial work is preserved across the timeout — only the agent process dies, files written by write_file persist.

## Step 6 — Verify output

```bash
ls -la ~/.hermes/skills/research/<skill-name>/chapters/ | wc -l
head -20 ~/.hermes/skills/research/<skill-name>/SKILL.md
```

Expect: one `.md` file per chapter plus `glossary.md`, `patterns.md`, `cheatsheet.md`, `SKILL.md`.

## Target locations by book type

| Book type | Skills path |
|---|---|
| IT / math / CS reference | `~/.hermes/skills/research/<skill-name>/` |
| Agent architecture / ML | `~/.hermes/skills/autonomous-ai-agents/<skill-name>/` |
| Software craft | `~/.hermes/skills/software-development/<skill-name>/` |

## Verified free PDFs (math fields applicable to Hermes)

For a full inventory of corpus gaps and priority acquisition order, see
`references/math-corpus-gaps.md` in this skill.

For a complete table of all IT/math book-corpus implementations across Hermes scripts
(patch IDs, source books, subcommands, algorithms, invariant thresholds), see
`references/book-corpus-it-implementations.md` in this skill.

| Book | URL | Local path | Pages |
|---|---|---|---|
| Boyd & Vandenberghe, *Convex Optimization* | https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf | ~/books/optimization/boyd-vandenberghe-convex-optimization.pdf | 714 |
| Åström & Murray, *Feedback Systems* (2021) | https://www.cds.caltech.edu/~murray/books/AM08/pdf/fbs-public_24Jul2020.pdf | ~/books/control/astrom-murray-feedback-systems.pdf | 573 |
| Milewski, *Category Theory for Programmers* | https://github.com/hmemcpy/milewski-ctfp-pdf/releases/download/v1.3.0/category-theory-for-programmers.pdf | ~/books/category/milewski-category-theory-for-programmers.pdf | 498 |
| Norris, *Markov Chains* | https://www.statslab.cam.ac.uk/~james/Markov/markovall.pdf | ~/books/probability/norris-markov-chains.pdf | ~237 |
| Diestel, *Graph Theory* (5th ed) | https://diestel-graph-theory.com/basic.html | ~/books/algorithms/diestel-graph-theory.pdf | 428 |
| Thompson, *Type Theory and Functional Programming* | https://www.cs.kent.ac.uk/people/staff/sjt/TTFP/ttfp.pdf | ~/books/logic/thompson-type-theory-fp.pdf | ~270 |

Åström & Murray requires `-k` flag (cds.caltech.edu SSL cert issue — official author host, safe).

## .djvu Conversion

If a book is only available as `.djvu`:

```bash
# Install djvulibre inside toolbox (fast, ~6s)
toolbox run -- sudo dnf install -y djvulibre

# Convert to PDF
toolbox run -- ddjvu -format=pdf \
    "$HOME/Downloads/Book Name.djvu" \
    "$HOME/books/<domain>/<slug>.pdf"

ls -lh ~/books/<domain>/<slug>.pdf   # confirm non-zero size
```

`TIFFWriteDirectorySec: Starting directory 0 ... might cause an IFD loop` warnings are benign — ddjvu routes through a TIFF intermediate; conversion succeeds regardless.

Scan `~/Downloads/` for books not yet moved to `~/books/`: `find ~/Downloads -name '*.pdf' -o -name '*.djvu' 2>/dev/null` — users often download books there without notifying the agent.

## Cross-Corpus Synthesis (Book Corpus × arXiv Sweeps)

After completing a book-corpus implementation wave, synthesize against the arXiv math/CS sweep findings before declaring saturation. Many killed/weakened proposals have infrastructure precursors in the sweep corpus, and vice versa.

### Synthesis procedure

1. Load `hermes-math-sweep-findings` and `hermes-cs-sweep-findings` skill content.
2. For each book-derived live patch: check whether any sweep paper independently validates the same mechanism. Reinforcement pairs are higher-confidence; conflicting verdicts are adversarial signal.
3. For each sweep paper spike/keep: check whether book-corpus infrastructure now satisfies a previously-missing precursor. Common pattern: a kill from wave N is revivable in wave N+2 after a new file/subcommand was built for a different proposal.
4. For each book-corpus kill/weaken: ask "does the infrastructure built since this was killed now enable it?" Build an explicit viability table:
   ```
   | Killed proposal | Infrastructure now built | Viable now? |
   |----------------|--------------------------|-------------|
   | SESSION-ENTROPY | skill-sequences.jsonl + bigrams | YES |
   | MUTUAL-INFO    | joint session co-occurrence logged | YES |
   | CALIBRATION    | skill_profiles has predicted+actual | YES |
   ```
5. Generate cross-corpus synergy proposals — NOT from any single source but from their intersection. These are often the highest-ROI implementations: two separately weak ideas whose combination is strong.
6. Implement all viable revivals and synergy proposals in the same implementation wave.

### Infrastructure-first revival rule

A kill verdict is tied to a specific infrastructure state. When infrastructure changes, revisit kills systematically — not just the ones that look relevant. Kills based on "missing file" or "missing data structure" are most likely to flip. Kills based on "vocabulary abuse" or "mathematical object mismatch" are permanent.

Conservative revival threshold: implement only if (a) the blocking infrastructure now exists as a real file/subcommand, not just a plan, AND (b) the implementation is additive and diagnostic-only.

### Reinforcement pairs found in book-corpus × sweep cross-analysis (Sep 2026)

| Book patch | Sweep paper | Relationship |
|---|---|---|
| COVSHA-4 belief provenance | Sweep 28 BCIT | Complementary provenance schemas on same WM file — combine into unified schema |
| GALLAGER-4 skill bigrams | Sweep 29 CaSKG | Bigrams = empirical feed for causal skill graph edge candidates |
| CLRS-7 provides taxonomy | A2E audit (40 orphan skills) | Taxonomy seeds the orphan discovery; provides-taxonomy.json should feed CaSKG |
| CLRS-8 or_deps Dijkstra | CaSKG counterfactual edges | or_deps is the Hermes runtime encoding of CaSKG skill-dependency edges |
| MACKAY-1 Occam coverage | PAC-Bayes (skill-router-index.py) | Specialist routing (Occam) + confidence bounding (PAC-Bayes) are complementary |
| WALD-3 CI width | Anytime-valid anomaly detection | CI width is the correct use case: detect anomalously high SKIP rate, NOT early-stop |
| ltl-check + action_log | Flight Recorder (Sweep 33) | Hash-chain action_log entries for tamper detection (verify-chain subcommand) |
| check-constraints | Constraint Weakening (Sweep 28) | Together cover full constraint lifecycle: contradiction → weakening → subsumption |
| SPRT underpowered flag | PAC-Bayes promotion in l1-promote.py | SPRT underpowered blocks stable-tier promotion — wire as gate in l1-promote.py |
| skill-hom (Yoneda) | A2E orphan audit | skill-hom IS the systematic near-duplicate detector for A2E's 40 orphan skills |

## Multi-Field Corpus → Spike Pipeline

For studying a corpus of books to derive implementable Hermes improvements:

1. **Inventory first.** Run `find ~/books -name '*.pdf' | sort | while read f; do pages=$(pdfinfo "$f" 2>/dev/null | grep Pages | awk '{print $2}'); echo "$pages pp | $f"; done` — confirms page counts and catches stubs (errata, journal articles, citation pages masquerading as books).

2. **Partition by field.** Dispatch parallel subagents, each covering 2-3 thematically related books. More than 3 books per subagent risks insufficient depth per book.

3. **Require structured JSON output.** Each subagent must return a JSON array of spike proposals. Per-spike schema:
   ```json
   {
     "id": "BOOK-N",
     "source": "title, chapter/section",
     "framework": "mathematical framework name",
     "hermes_target": "which Hermes component",
     "description": "what to implement",
     "algorithm": "concrete pseudocode or formula",
     "feasibility": "HIGH|MEDIUM|LOW",
     "measurability": "how to verify it works",
     "depends_on": "prerequisite infrastructure"
   }
   ```
   Require feasibility=LOW when the idea needs model internals, training loops, logits, or infrastructure that does not exist in Hermes.

4. **Adversarial pass before implementing.** Dispatch a cold subagent with no implementation context — separate from the implementation subagent. For each spike:
   - KILL: the formal guarantee is false in Hermes's constraints (no model internals, no logit access)
   - WEAKEN: scope down to what IS achievable; log the infrastructure gap
   - KEEP: infrastructure exists, guarantee holds, measurable outcome defined
   - Flag shared dependencies: two spikes that both require the same missing file are a co-dependent SPOF — treat their KILL/WEAKEN as coupled.
   - Always check scipy/numpy availability before recommending LP/QP solvers: `python3 -c 'import scipy; print(scipy.__version__)'`
   - 'Caller supplies the math' stubs (where the implementation takes the required quantity as an argument rather than computing it) are a KILL class: they add CLI surface with no actual guarantee. The gap-check and line-search in loop-pid.py are the canonical example — labeled with explicit disclaimers rather than removed, but never claimed as Boyd certificates.
   - Vocabulary abuse is the most common KILL signal. For each proposal, verify the code's input MATCHES the mathematical object the term describes: 'Armijo backtracking' requires a gradient; 'Lipschitz contraction' requires a metric-preserving map (ratio of two deltas ≠ a Lipschitz constant); 'span seminorm' requires a value function on a state space (PID error range is not a span seminorm); 'upcrossing' (Doob) requires a supermartingale. If the input does not match the object, KILL or WEAKEN to remove the name and restate as a plain heuristic. Expect ~30-50% of book-derived proposals to fail on this criterion. See adversarial-review references/math-research-pipeline-adversarial-checks.md for the full pattern.
   - Missing infrastructure is not a blocker for WEAKEN — it is a blocker for KEEP. WEAKEN means 'implement the transferable fragment, drop the mathematical framing that requires missing pieces.'

5. **Implement KEEP/WEAKENED survivors only.** Never implement a KILL spike. When implementation runs in parallel with the adversarial pass, apply verdicts post-hoc: strip false docstrings, demote FAIL to WARN for rules the runtime cannot enforce, and re-verify with py_compile.

6. **Iterate to saturation.** Stop when each new wave returns fewer than 2 new KEEP verdicts across all books. Saturation is a falling KEEP rate, not zero proposals. After saturation on the book corpus, run the cross-corpus synthesis step above before closing — the arXiv sweep findings often revive several killed proposals using infrastructure built in later waves.

7. **Apply verdicts to already-implemented stubs.** When an adversarial reviewer kills a proposal that was already implemented (parallel dispatch), do not remove the stub — remove or correct the false mathematical framing in the docstring and parser help text, change FAIL → WARN for checks the runtime cannot enforce, and re-verify with py_compile. This preserves the utility of the CLI surface while removing the false guarantee.

## User-Owned Files — Hard Boundary

Files in `~/Downloads/Therapy/` (and any subdirectory the user designates as personal) are off-limits. Do NOT move, copy, read, or process them unless the user says so explicitly in the current turn. This applies even when scanning Downloads for corpus books — exclude personal subdirectories from the scan:

```bash
# Correct: only top-level Downloads, not subdirs
find ~/Downloads -maxdepth 1 -name '*.pdf' -o -name '*.djvu' 2>/dev/null
# NOT: find ~/Downloads -name '*.pdf'  (recurses into personal folders)
```

When moving books from Downloads to ~/books/, only touch files the user explicitly listed or confirmed. Do not speculatively move anything else found in the same directory.

## Pearl Causality — Free Status

Pearl, *Causality: Models, Reasoning, and Inference* (2nd ed, 2009, Cambridge) is NOT freely available as a legal PDF. The errata document (37pp, filename "Errata for J. Pearl, Causality...") is distinct from the book (487pp). If the full book is in `~/books/causal-inference/`, confirm with `pdfinfo` that Pages > 400 before treating it as the full text.

## Mining Book Knowledge for Coding Skill Improvements

After creating a book knowledge skill, mine it for theory that can be converted into concrete, actionable rules in existing coding skills. This is distinct from ingestion — ingestion creates the knowledge skill; mining extracts applied improvements.

Full procedure: see `references/theory-to-skill-mining.md` in this skill.

**The core filter:** a theoretical result is worth applying only if it produces a decision procedure or a falsifiable check — something a future session can either do or test. Pure mathematical statements with no operational consequence are not worth adding to coding skills.

**Primary targets for book-derived improvements:**
- `coding-conventions` — design principles, review criteria, correctness rules
- `systematic-debugging` — diagnostic procedures, failure mode taxonomies
- `test-driven-development` — test value criteria, property-test framing, verification conditions

**Parallelism:** When mining multiple books at once, dispatch one subagent per book with explicit patch targets and specific improvements to look for. 10 books in parallel is feasible; each subagent extracts and applies independently since they target different skill sections. See dispatching-parallel-agents.

## Pitfalls

- `/tmp/book_skill_work/` is cleared on reboot — re-run Step 4 before resuming if the session ended mid-generation.
- `/tmp/book_skill_work/` is a shared path — parallel ingestion jobs overwrite each other. Copy to `/tmp/book_skill_work_<slug>/` immediately after each extraction before dispatching the next.
- `--mode technical` without docling silently falls back to pdftotext. The output says "Mode: technical" then "fallback" — expected, results are good.
- Do NOT use `--install-missing yes` in non-interactive sessions; it may block on a TTY.
- For 40+ chapter books, subagent generation times out at 900s. Dispatch and end the turn. On timeout, check output, then dispatch a continuation with explicit chapter-number start.
- `toolbox run <cmd>` fails with GLib threading errors in non-interactive terminal sessions. Use `podman exec <container-name> <cmd>` for any toolbox-installed binary when called from scripts or agent terminals.
- Stub PDFs from libgen are common: a "book" file under 500KB is almost certainly a journal review or citation page, not the actual book. Check with `pdfinfo` + `pdftotext` sample before dispatching ingestion.
- Jaynes *Probability Theory: The Logic of Science* (Cambridge) is NOT freely available as a complete PDF. bayes.wustl.edu hosts only a 95-page early draft (check with `pdfinfo` — if Pages < 200, it's the draft). The full 727-page published book requires purchase.
- Substitute ALL template placeholders — both `<angle-bracket>` and `{curly-brace}` forms — in the subagent goal before dispatching. The delegate_task renderer rejects goals containing either unexpanded form. Mathematical notation using curly braces (e.g. `{n-k}` in combinatorics or `{q in Q}` in set notation) will also be rejected — rewrite as prose or use parentheses. See `dispatching-parallel-agents` for full detail.
- For OCR jobs on 600+ page scanned PDFs at 300 DPI: budget 30-90 minutes of wall time. Gallager-scale jobs (604pp) take ~45 min OCR + ~30 min generation. Lin & Costello (1271pp at 200 DPI) takes longer. These cannot fit in a single 900s subagent — the OCR phase alone may exhaust the timeout; set realistic expectations.
- Adversarial and implementation subagents can be dispatched in parallel on the same proposal batch. The adversarial reviewer reports verdicts; apply them after implementation finishes. This is faster than serializing.
- The researcher's chapter-number map in the dispatch brief may not match the actual book. Always tell the subagent to verify chapter headings before reading — actual TOC structure often differs from the assignment brief, and the subagent should read the actual sections even if the numbering differs.
- When user adds books to ~/books/ independently between waves, scan with `find ~/books -name '*.pdf' | sort` and compare against the known inventory rather than relying on timestamps — user-added books often have older modification dates than the files you moved in.
- Check `~/Downloads/` for books that were never moved to `~/books/`: `.djvu` files especially tend to live in Downloads indefinitely. Scan `~/Downloads/` at `-maxdepth 1` only — do not recurse into personal subdirectories (e.g. `~/Downloads/Therapy/`).
- djvu→PDF conversion via ddjvu produces a PDF with no text layer when the djvu source is scanned images. After conversion, always run `pdftotext -f 3 -l 4 <converted.pdf> - | head -6` to confirm text was extracted. If blank: the converted PDF is image-only — rasterize with pdftoppm and OCR with `podman exec fedora-toolbox-44 tesseract`. The extractor's fallback silently grabs the previously-cached book's text from `/tmp/book_skill_work/` rather than erroring — the token count will appear plausible (matching the prior run), which is the tell. Always confirm the SOURCE header at the top of full_text.txt matches the intended book slug before dispatching.
- When adversarial and implementation subagents run in parallel and a proposal is killed, apply the verdict surgically post-hoc: strip false docstrings and mathematical name claims, demote FAIL→WARN for unenforceable checks, re-run py_compile. Do NOT revert the entire implementation — preserve the utility of the CLI surface.
- Concurrent same-file write conflict during implementation waves: when multiple subagents target the same .py script, steer later agents explicitly to read the CURRENT file state before patching (the earlier agent's changes may already be in). Use `patch` tool for targeted edits, not full-file rewrite. Steer message: 'Read current state of <script> before writing — another agent has already made changes to it. Use patch for targeted edits only.' This prevents silent overwrites.
- Kill verdicts have a timestamp. Revisit them at each new wave by checking whether the blocking precursor now exists (real file or subcommand, not a plan). Category: kills based on missing infrastructure are revisable; kills based on vocabulary abuse or wrong mathematical object are permanent.
- Vocabulary abuse (applying a term to the wrong mathematical object) is the most common kill signal from math-book proposals: ~30-50% of proposals fail this check. Key pairs that commonly fail: sigma_post=1-ruzicka (residual overlap is NOT posterior width); cross-skill marginal likelihood ranking (incommensurable across different D_i); depends_on as OR shortest-path (depends_on is AND prerequisites, not a routing choice). These are always KILL or WEAKEN, never KEEP-with-caveat.

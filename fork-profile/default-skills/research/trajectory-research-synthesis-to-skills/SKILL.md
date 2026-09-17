---
name: trajectory-research-synthesis-to-skills
description: "Use when applying sweep findings to Hermes skills."
version: 1.0.0
author: Hermes Agent (trace2skill auto-candidate, curated)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, arxiv, sweep, skills, self-improvement, synthesis]
    related_skills: [arxiv-sweep-findings, skillopt-continuous-improvement, self-improve-agent, hermes-agent-skill-authoring, runtime-skill-synthesis]
triggers:
  - "apply research findings as skill patches"
  - "consolidate sweep results into skill patches"
  - "implement a paper finding in a Hermes skill"
  - "triage and patch skills from sweep output"
  - "update skill library from trajectory"
  - "apply sweep findings from subagent results"
  - "patch a skill based on a paper"
  - "NOT for searching arXiv (use arxiv skill)"
  - "NOT for querying the findings bank (use arxiv-sweep-findings)"
  - "NOT for running the weekly sweep pipeline (use hermes-research)"
related_skills:
  - arxiv-sweep-findings
  - skillopt-continuous-improvement
  - self-improve-agent
  - hermes-agent-skill-authoring
  - runtime-skill-synthesis
---

# Trajectory Research Synthesis to Skills

Operational procedure for consolidating multi-source research sweep results (arXiv, GitHub,
web, multilingual) into actionable Hermes skill patches. Distinct from `arxiv-sweep-findings`
(the findings bank) — this skill describes *how to run* the synthesis workflow itself.

## When to Use

- After a multi-subagent arXiv/research sweep completes and results need to be applied to skills
- When resuming a sweep after context compression (subagent outputs may need re-reading from cache)
- When triage + prioritisation decisions must be made across a large batch of findings

## Steps

1. **Collect all subagent task outputs** — Read task result files from delegation cache using
   `read_file('/var/home/rainbow/.hermes/cache/delegation/subagent_...')` for each completed
   task (e.g., task-0, task-2, task-4, redo batches). List available files first with
   `search_files(pattern='subagent_*', target='files', path='~/.hermes/cache/delegation/')`.

2. **Extract and parse findings** — Use regex + JSON parsing to extract structured findings
   from log outputs. Handle nested objects with a custom `extract_json_blocks()` function
   for robustness when direct parsing fails. <!-- why: sweep outputs often contain nested JSON that json.loads() rejects -->

3. **Load sweep reference context** — Call `skill_view(name='arxiv-sweep-findings')` to get
   the full findings database with severity labels (HIGH/MED/LOW). Check the **Sweep Boundary
   Log** table for the last sweep's cutoff ID to avoid re-processing known findings.

4. **Triage findings by severity** — Organise findings into:
   - HIGH: implement immediately in current session
   - MED: queue as a note in `arxiv-sweep-findings` for next sweep
   - LOW: record only as a skip note
   Group by skill target (memory, routing, context, safety, etc.).

5. **Apply HIGH findings to skill bodies** — For each HIGH finding:
   a. Load the target skill: `skill_view(name='target-skill-name')`
   b. Locate the appropriate anchor section (e.g., `## Cognitive Trap Defense`, `## Pitfalls`)
   c. Patch with a rationale comment: `skill_manage(action='patch', name='...', old_string='...', new_string='...')`
   d. Include `<!-- why: prevents [specific failure] in [session/task type] -->` on each new rule <!-- why: prevents catastrophic remembering (arXiv:2608.11095) — rationale enables deletion audits -->
   e. Verify with `skill_view(name='...')` after each patch

6. **Update the sweep findings reference file** — Append to the inline technique class
   sections in `arxiv-sweep-findings` SKILL.md:
   - Add a `## Technique Class: [Name] (Sweep N)` section for each technique cluster
   - Record applied, blocked, and skipped findings
   - Update the Sweep Boundary Log table with date, cutoff ID, highest ID, counts
   - Use `skill_manage(action='patch', name='arxiv-sweep-findings', ...)` to append

7. **Log sweep completion in memory** — Call `memory(action='replace', ...)` to update the
   sweep tracking entry (e.g., `arXiv sweeps: last=sweep N (date). Cutoff: ID+.`)
   with the new sweep number, date, and net-new count. <!-- why: cross-session reference to avoid re-sweeping the same papers -->

8. **Persist a reference file for large sweeps** — For sweeps with 10+ findings, write a
   dedicated reference file: `skill_manage(action='write_file', name='arxiv-sweep-findings',
   file_path='references/sweep-N.md', file_content='...')`. <!-- why: large inline sections cause skill_view to be pruned in compression -->

## Pitfalls

- **Nested JSON objects fail simple parsing** — Tool logs sometimes contain deeply nested JSON
  that `json.loads()` rejects. Resolution: write a recursive `extract_json_blocks(text)` function
  that finds `{...}` boundaries with brace counting, then attempts each block separately.
  Fall back to regex extraction if JSON parsing fails.

- **Skill body formatting breaks with careless edits** — If patch insertion doesn't respect
  YAML frontmatter or section anchors, the skill becomes unparseable. Resolution: always verify
  with `skill_view` after `skill_manage` patch; if broken, reload the original and re-apply
  with explicit anchor guards.

- **Subagent task results not persisted in logs** — Some task outputs live only in memory and
  are lost on context compression. Resolution: immediately after task completion, write outputs
  to a persistent cache file with `execute_code` + file I/O before moving to the next step.

- **Skill too large for `skill_view`** — `arxiv-sweep-findings` can exceed the compression
  threshold. Resolution: split large batch additions into a `references/sweep-N.md` file
  and add a compact inline summary only to the SKILL.md body. Reference with
  `skill_view(name='arxiv-sweep-findings', file_path='references/sweep-N.md')`.

- **Blocked patches — user-owned skills** — Some skills are curator-protected and reject
  `skill_manage` patches from autonomous sessions. Resolution: record the blocked finding in
  the `arxiv-sweep-findings` Blocked Patches table. The user can unblock with
  `hermes curator adopt <skill-name>`.

- **Duplicate Blocked Patches sections** — Only one `## Blocked Patches` table should exist
  in `arxiv-sweep-findings`. New sweep's blocked findings go into the SINGLE existing table
  with the `Sweep` column identifying the source. <!-- why: split-state conflicts are invisible to future patch authors -->

- **Memory update format** — Use `memory(action='replace', old_text='arXiv sweeps: ...',
  content='arXiv sweeps: last=sweep N (...). Cutoff: ID+. ...')`. Do NOT use
  `memory(fetch=...)` — that is not a valid call signature.

## Verification

- **All target skills updated** — Run `skill_view(name='skill-name')` for each patched skill
  and confirm that the new finding content appears in the body.

- **Sweep reference file marked complete** — Check `skill_view(name='arxiv-sweep-findings')`
  and confirm the Sweep Boundary Log table has a new row with `HIGH/MED` counts.

- **Memory updated** — Confirm the `memory` store reflects the new sweep number and cutoff ID.

- **No syntax errors in patched skills** — `skill_manage` auto-runs syntax checks on YAML
  frontmatter. If a patch is accepted, frontmatter is valid. Verify skill content makes sense
  by reading key sections back.

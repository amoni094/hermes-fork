# Verifying generated Office documents / notebooks without a shell

## When this applies
A subagent (or you) generated a .docx/.xlsx/.pptx/.ipynb deliverable and you need to
confirm it's real and substantive — not just that the path exists — before reporting
success to the user. This applies especially when:
- the subagent's own verification step failed or was blocked
- `terminal` commands are being blocked by a user policy/consent gate this session
- you don't want to install `python-docx`/`openpyxl` just to sanity-check one file

## Fast path (no shell, no dependency install)

1. Confirm existence and non-trivial size first:
   `search_files(pattern='*<name>*', target='files', path='<dir>')`
   A real multi-page deliverable is rarely under a few KB; a suspiciously small file
   (a few hundred bytes) is a red flag before you even open it.

2. Read the content directly — `read_file` auto-extracts readable text from .docx,
   .xlsx, and .ipynb (response includes `"extracted_document": true`). No shell,
   no pip install, no unzip:
   ```
   read_file(path="/path/to/Deliverable.docx", limit=60)          # head
   read_file(path="/path/to/Deliverable.docx", offset=140, limit=64)  # tail/middle
   ```
   Use the `total_lines`/`file_size` fields in the response to decide how many
   windows you need to sample.

3. Sample head AND tail (not just the first page). A file can have a plausible
   title page and be truncated or corrupted further in — reading only the head
   is the same mistake as trusting "file exists" alone. For a critique/report
   document, the tail should contain your closing sections (references,
   conclusions) with real content, not boilerplate repeated from the top.

4. Spot-check that specific claimed content is actually present verbatim
   (a citation, a section heading, a number) rather than eyeballing that "there's
   text there" — subagents can hallucinate a summary that doesn't match what they
   actually wrote to disk.

## Why not shell out

- `terminal` + `unzip`/`python-docx` requires either a pre-installed dependency
  (fails with `ModuleNotFoundError` in ephemeral sandboxes via `execute_code`) or
  shell access that may be blocked by a policy/consent gate independent of the
  file itself.
- Retrying a blocked terminal command (even reworded, even a "smaller" diagnostic
  version) does not help — the gate is a policy decision, not a transient error.
  Switch tools immediately instead of retrying; repeated identical failures trigger
  a same_tool_failure_warning loop guard.
- `read_file`'s built-in extraction is the lower-friction, dependency-free path and
  should be tried first for this exact class of check.

## Worked example (from session: NAB Legal Memory System design review)

Subagent claimed a 204-line, 52KB .docx was written and saved successfully, but its
own follow-up `python3`-based verification command was blocked by a user consent gate.
Verification sequence that actually worked:
1. `search_files(pattern='*NAB*', target='files', path='/var/home/rainbow/Documents')`
   → confirmed the exact file exists.
2. `terminal(... file ...)` → confirmed it's a real "Microsoft Word 2007+" file
   (not corrupted), size 52229 bytes.
3. `execute_code` with `from docx import Document` → failed, `ModuleNotFoundError`
   (sandbox has no python-docx installed) — did not retry, switched tools.
4. `terminal` + `unzip` → **blocked** by user policy gate. Did not retry or reword.
5. `read_file(path=..., limit=60)` then `read_file(path=..., offset=140, limit=64)`
   → both returned `"extracted_document": true` with full readable section text,
   confirming real content in both the head (executive summary, reconstructed
   proposal) and tail (critique, adversarial-review notes, references list) —
   sufficient to independently confirm the deliverable before reporting success.

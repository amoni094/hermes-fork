---
name: thunderbird-cli-anything
description: >
  Use when: Use the local CLI-Anything Thunderbird harness for drafting, reply templates, attachments, signatures, and compose-window automation.
triggers:
  - thunderbird harness
  - draft email
  - email attachment
  - reply all
  - signature file
related_skills:
  - email-compose-and-send
  - email-inbox-triage
---

# Thunderbird CLI-Anything harness

Use this skill when the user wants Hermes to prepare or open local Thunderbird email workflows through the CLI-Anything harness on this machine.

This is the canonical Thunderbird execution harness skill. Pair it with `thunderbird-local-email-workflow` when mailbox-specific consent or verification conventions matter.

## Local command
Use this wrapper directly:
`/var/home/rainbow/.local/bin/cli-anything-thunderbird`

It runs the harness source at:
`/var/home/rainbow/CLI-Anything/thunderbird/agent-harness`

## Supported commands

### Status
Check launcher availability first:
`cli-anything-thunderbird --json app status`

### Open a prefilled compose window
Text body:
`cli-anything-thunderbird --json compose open --to person@example.com --subject "Subject" --body "Body"`

HTML body:
`cli-anything-thunderbird --json compose open --to person@example.com --subject "Subject" --body "<p>Body</p>" --format html`

With attachments/signature:
`cli-anything-thunderbird --json compose open --to person@example.com --subject "Subject" --body "Body" --attachment /path/file.pdf --signature-file /path/signature.txt`

### Reply / reply-all template
Reply:
`cli-anything-thunderbird --json compose reply --to sender@example.com --body "Thanks" --original-from sender@example.com --original-to me@example.com --original-subject "Topic" --original-body "Original text" --dry-run`

Reply-all:
`cli-anything-thunderbird --json compose reply --to sender@example.com --cc team@example.com --body "Thanks" --original-from sender@example.com --original-to me@example.com --original-subject "Topic" --original-body "Original text" --reply-all --dry-run`

### Save a draft artifact
Text draft:
`cli-anything-thunderbird --json draft save ~/draft.eml --to person@example.com --subject "Subject" --body "Body"`

HTML draft with attachment/signature:
`cli-anything-thunderbird --json draft save ~/draft.eml --to person@example.com --subject "Subject" --body "<p>Body</p>" --format html --attachment /path/file.pdf --signature-file /path/signature.html`

### Open a saved draft in Thunderbird
`cli-anything-thunderbird --json draft open ~/draft.eml`

## Workflow Hermes should follow
1. Run `app status` first.
2. Prefer `--dry-run` for verification before opening UI.
3. If the user asks for a draft, use `draft save` and report the exact path.
4. If the user asks to open Thunderbird, use `compose open` or `draft open`.
5. If the user asks to send, prepare the message honestly and distinguish compose/draft success from delivery.

## Signature guidance
- Use `--signature-file` rather than embedding long signatures inline.
- Text signatures should be plain text files.
- HTML signatures should be HTML snippets when using `--format html`.

## Verification standard
Before claiming success, verify at least one of:
- returned JSON from `app status`
- draft file exists and contains expected headers/body
- dry-run compose/reply output contains the intended recipients, subject, and attachments

## Boundary
This harness reliably supports status, draft creation, draft opening, and compose-window opening. It does not provide a trustworthy non-interactive delivery confirmation path, so do not claim an email was sent solely from compose/draft results.

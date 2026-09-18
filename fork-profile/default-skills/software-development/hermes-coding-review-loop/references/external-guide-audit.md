# External Guide Audit Pattern

Use this when a user points Hermes at an external optimization guide, workflow repo, or "best practices" document and asks whether anything should change locally.

## Goal

Turn the guide into a grounded audit of the current checkout instead of cargo-culting every recommendation.

## Fast classification

For each recommendation, classify it as:

1. **Already implemented** — no code change needed.
2. **Implemented but hidden** — improve discoverability via CLI help, tool descriptions, docs, prompt labels, or tests.
3. **Actually missing** — implement the smallest useful change.

The second bucket matters. Many useful improvements are discoverability fixes, not architecture work.

## Good fit signals

- The guide describes a capability Hermes already has, but the user-facing strings lag behind.
- The request is broad ("read through this and improve yourself") and needs a bounded implementation target.
- A small change in help text or schema wording can align the product with current behavior.

## Verification recipe for small Python help/doc patches

1. Add a targeted pytest file that checks the exact help text / schema description / exported label.
2. Run the narrow pytest slice with repo addopts disabled if the local pytest install lacks optional plugins.
3. Run `python -m py_compile` on every edited Python file.

Example verification shape:

```bash
PYTHONPATH=. ~/.local/bin/pytest tests/cli/test_context_file_help_text.py -q -o addopts=''
python3 -m py_compile <edited-files>
```

## Patch-tool pitfall

Long JSON-schema description strings are easy to damage with automated patching. If lint reports syntax errors after a text-only change:

- inspect the exact literal,
- repair the smallest broken span,
- rerun syntax verification immediately.

Do not continue stacking edits on top of a malformed dict or string literal.

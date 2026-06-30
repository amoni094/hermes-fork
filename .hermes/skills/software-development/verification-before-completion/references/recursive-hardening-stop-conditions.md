# Recursive hardening stop conditions

Use this when doing broad cleanup passes across many files, especially risk-guard or lint baseline reduction.

What to verify after each batch:
- touched-file proof: compile, parse, lint, or targeted validator on the edited files
- aggregate proof: the repo-wide checker or baseline summary that shows whether the remaining findings changed in kind
- compatibility proof: any repo validator that would catch format/schema regressions outside the edited files

Good stopping signal:
- the easy defect class has been materially reduced
- remaining findings are now mostly semantic detections, intentional lab behavior, or explicit opt-in flags
- further count reduction would require changing intended behavior rather than hardening implementation details

Example pattern:
- fixed hard-coded temporary paths by moving to tempfile/tempdir-based locations or configurable defaults
- re-ran compile checks on edited files, the risky-pattern checker, and the repo validator after each batch
- stopped when the remaining findings were detector-content matches like `/tmp/xmrig` or gated `--force` behavior rather than unconditional unsafe defaults

Reporting pattern:
- say what class of issue you removed
- give the before/after aggregate counts
- name the proof commands/checks you ran
- explain why the remaining items should be kept, suppressed, or redesigned instead of blindly removed

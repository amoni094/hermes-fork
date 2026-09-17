---
name: pii-redaction
description: >
  Use when a user provides an Australian trust deed (PDF or DOCX) and asks to
  redact, anonymise, or de-identify personal information under Privacy Act 1988
  (Cth) s 6. Triggers on 'redact', 'anonymise', 'de-identify', 'trust deed',
  'PII', 'personal information', 'Privacy Act'. Handles scanned/poor-quality OCR
  docs with vision-based quality assessment. Produces a redacted file, audit JSON,
  and OCR quality report. Not for GDPR (EU) or non-Australian privacy regimes.
version: 1.2.0
author: Hermes Agent
license: MIT
model: claude-sonnet-4-6  # docs-only; Hermes ignores this field
platforms: [linux, macos, windows]
triggers:
  - User provides an Australian trust deed (PDF or DOCX) and asks to redact PII
  - User asks to anonymise or de-identify a legal document under the Privacy Act
  - User says "redact personal information", "strip PII", or "de-identify trust deed"
  - User wants a redacted copy of a document for sharing or disclosure purposes
  - Document is a scanned trust deed with poor OCR quality
metadata:
  hermes:
    tags: [privacy, pii, redaction, trust-deed, australia, privacy-act, legal, pdf, ocr, vision]
    related_skills: [pdf, docx, legal-regulatory-research-writing]
    model: claude-sonnet-4-6
routing_signals: >
  Use for: Privacy Act 1988, s 6 personal information, trust deed redaction,
  Australian PII anonymisation, de-identification, beneficiary names, trustee names,
  appointor, settlor, TFN, ABN individual, Medicare, date of birth, residential
  address, scanned OCR low quality document assessment, Presidio, spaCy NER.
  Not for GDPR, tax returns, financial statements (use pdf/docx skills directly).
last_validated: "2026-08-19"
lifecycle_stage: experimental
trust_level: experimental
capabilities: [file_read, file_write, shell_exec]
input_schema:
  type: object
  properties:
    input_path: {type: string, description: "Absolute path to trust deed PDF or DOCX"}
    output_path: {type: string, description: "Absolute path for redacted output (optional, defaults to _redacted suffix)"}
    adversarial_passes: {type: integer, default: 3, description: "Number of re-extraction detection loops"}
    strict: {type: boolean, default: false, description: "Exit 1 if any leakage remains after passes"}
  required: [input_path]
output_schema:
  type: object
  properties:
    output_file: {type: string}
    audit_log: {type: string}
    ocr_quality_report: {type: string}
    summary:
      type: object
      properties:
        total_redactions: {type: integer}
        categories: {type: object}
        adversarial_passes: {type: integer}
        final_leakage_count: {type: integer}
        ocr_quality: {type: string, enum: [good, low_confidence, unreadable]}
        ocr_confidence_score: {type: number}

ssl_scheduling:
  triggers:
    - User supplies a trust deed file path or asks for PII redaction
    - Document contains personal information to be de-identified
  preconditions:
    - Input file is a readable PDF or DOCX
    - Python 3.9+ available
    - Deps available or installable: presidio-analyzer, presidio-anonymizer, pdfplumber, pymupdf, python-docx, pillow, spacy en_core_web_lg
    - For vision quality assessment: vision_analyze tool available
  estimated_steps: 8

ssl_structural:
  tools_used: [terminal, read_file, write_file, vision_analyze]
  subtasks:
    - Phase 1 - OCR quality assessment via vision (flag poor-quality inputs)
    - Phase 2 - Extract text from PDF or DOCX
    - Phase 3 - Detect PII via Presidio (NER + regex) with AU-specific custom recognisers
    - Phase 4 - Apply redactions (character bounding box overlay for PDF, replace for DOCX)
    - Phase 5 - Adversarial loop - re-extract and re-detect until zero leakage or pass limit
    - Phase 6 - Produce audit log JSON + OCR quality report
    - Phase 7 - External agent-level dry-run verification on the redacted output

ssl_logical:
  side_effects:
    - Writes redacted output file alongside input (suffix _redacted)
    - Writes audit log JSON at same directory
    - Writes OCR quality report JSON
  resources:
    - Input file (read-only)
    - Python packages: presidio-analyzer presidio-anonymizer pdfplumber pymupdf python-docx pillow spacy
  risk_level: medium
related_skills:
  - pdf
  - docx
  - legal-regulatory-research-writing

---

# PII Redaction Skill - Australian Trust Deeds

Redact all personal information within the meaning of Privacy Act 1988 (Cth) s 6
from an Australian trust deed (PDF or DOCX). Handles text-layer PDFs, scanned/image
PDFs with poor OCR quality, and DOCX files. Uses Microsoft Presidio for detection
(NER + regex) with Australian-specific custom recognisers.

Includes a recursive adversarial loop: after redaction, re-extracts text from the
output and re-runs detection until zero detections remain or the pass cap is hit.
Poor-quality OCR inputs are flagged with a confidence score and a human review
requirement before the redacted output is used in a legal/disclosure context.

## Privacy Act 1988 (Cth) - Personal Information Definition

Under s 6 Privacy Act 1988 (Cth), "personal information" means information or an opinion
about an identified individual, or an individual who is reasonably identifiable, whether
or not the information or opinion is true, and whether or not it is recorded in a material
form. "Sensitive information" (also s 6) includes health, racial/ethnic origin, criminal
record, and biometric data - all redacted at higher confidence threshold.

Categories redacted by this skill:

| Category | Code | Examples in trust deeds |
|---|---|---|
| Full names (individuals) | FULL_NAME | Trustee, appointor, settlor, beneficiary names |
| Residential/postal addresses | AU_ADDRESS | Home address of natural persons |
| Phone numbers | PHONE_NUMBER | Personal mobile/home |
| Personal email | EMAIL_ADDRESS | Individual email (not corporate domain) |
| Dates of birth | DATE_OF_BIRTH | DOB of beneficiaries |
| Tax file number | AU_TFN | Individual TFN (9 digits with check digit) |
| Individual ABN | AU_ABN_INDIVIDUAL | ABN tied to a natural person (sole trader) |
| Medicare number | AU_MEDICARE | 10-digit Medicare card number |
| Driver licence | AU_DRIVER_LICENCE | State-issued driver licence number |
| Passport number | AU_PASSPORT | Australian passport number |
| Bank account (individual) | AU_BANK_ACCOUNT | BSB + account where linked to a person |
| Sensitive information | SENSITIVE | Health, racial origin, criminal record if present |

NOT redacted (not personal information of individuals):
- ABN/ACN of corporate trustees (company identifiers, not personal info)
- Trust name itself (e.g. "Smith Family Trust") - FLAGGED for human review under `trust_name_review_items` in the audit log; not auto-redacted
- Generic legal boilerplate and clause text
- Date of trust execution (document date, not a DOB)
- Signatures as graphical elements (text-layer redaction only; visual signature images require image-layer redaction)

CAUTION: Indirect identifiers such as "the Trustee's children" are personal information
of reasonably identifiable individuals and are redacted at pattern level.

## When to Use

- Client sends a trust deed PDF or DOCX for external disclosure
- Preparing a trust deed for a regulator, law firm, or court where PII must be stripped
- De-identifying trust deed records for bulk data analysis
- Scanned trust deed with uncertain OCR quality - skill will assess and flag

Don't use for:
- GDPR or non-Australian privacy regimes (legal definition differs - use a jurisdiction-specific tool)
- Redacting financial statements or tax returns (different scope)
- Scrubbing PDF file metadata (use exiftool or pdf_meta.py - this skill handles text layer only)
- Visually redacting scanned images without an OCR text layer (needs OCR-first preprocessing)

## Prerequisites

Install with pip (or toolbox run python):

```bash
pip install presidio-analyzer presidio-anonymizer pdfplumber pymupdf python-docx pillow spacy
python -m spacy download en_core_web_lg
```

The script checks deps on startup and prints exact install commands for anything missing.
It does NOT auto-install.

## Phase 0 - OCR Quality Assessment (MANDATORY for scanned inputs)

Before running detection, assess whether the document has a usable text layer.
This must happen for ALL inputs, not just obvious scans.

### Step 0a - Machine check (fast)

```bash
python3 ~/.hermes/skills/productivity/pii-redaction/scripts/redact_pii.py \
    --input /path/to/trust_deed.pdf \
    --check-ocr-only \
    --log /tmp/ocr_quality.json
cat /tmp/ocr_quality.json
```

Machine check outputs:
- `ocr_quality`: `good` | `low_confidence` | `unreadable`
- `ocr_confidence_score`: 0.0-1.0 (ratio of pages with text density above threshold)
- `pages_with_text`: N pages that yielded extractable text
- `total_pages`: M total pages
- `empty_pages`: list of page numbers with no extractable text

Decision thresholds:
- Score >= 0.8 and zero empty pages: proceed directly to redaction
- Score 0.5-0.8 OR some empty pages: LOW_CONFIDENCE - run vision check on sample pages and flag to user
- Score < 0.5 OR majority empty pages: UNREADABLE - do NOT proceed; halt and report

### Step 0b - Vision check for LOW_CONFIDENCE inputs

When machine check returns `low_confidence`, sample up to 5 representative pages
(including the first page with personal data and the execution/signature page) using vision_analyze:

```python
# Convert a PDF page to image and assess visually
# Run from terminal:
pdftoppm -jpeg -r 150 -f PAGE_NUM -l PAGE_NUM /path/to/deed.pdf /tmp/deed_page
# Then in agent context:
vision_analyze(
    image_url="/tmp/deed_page-PAGE_NUM.jpg",
    question=(
        "This is a page from an Australian trust deed that has been OCR-processed. "
        "Assess: (1) Is the text legible or are there artefacts, distortion, or blur? "
        "(2) Are there any visible personal details (names, addresses, dates of birth, "
        "TFN, signature blocks)? (3) Would an automated system reliably extract all "
        "personal information from this page? Rate legibility: excellent/good/fair/poor. "
        "List any personal information visible that OCR may have missed."
    )
)
```

Document the vision assessment result in the OCR quality report. If vision reveals
personal information that OCR missed, add those instances as manual redaction items
in the audit log under category `VISION_ONLY_DETECTION`.

### Step 0c - Copilot review gate for LOW_CONFIDENCE

When `ocr_quality == low_confidence`, include this block in the copilot output:

```
OCR QUALITY FLAG - HUMAN REVIEW REQUIRED
=========================================
File: {input_path}
OCR confidence score: {score:.2f} ({pages_with_text}/{total_pages} pages readable)
Empty pages: {empty_pages}
Vision assessment: {vision_legibility} legibility

ACTION REQUIRED before distributing the redacted output:
1. Review the OCR quality report at: {quality_report_path}
2. Manually verify that pages listed as empty or poor-quality do not contain
   personal information that automated redaction could not reach.
3. For pages rated 'fair' or 'poor' by vision: consider re-scanning at higher
   DPI (300+) and re-running redaction on the higher quality scan.
4. Sign off: confirm that manual review was completed and the document is safe
   to distribute. Do NOT distribute the redacted output without this sign-off.

VISION_ONLY_DETECTIONS (items found by vision but not OCR - require manual redaction):
{vision_only_items}
```

### Step 0d - UNREADABLE halt

When `ocr_quality == unreadable`, halt with:

```
REDACTION HALTED - DOCUMENT UNREADABLE
=======================================
File: {input_path}
OCR confidence score: {score:.2f}
This document's text layer is too poor to support reliable automated PII detection.

Options:
A. Re-scan the physical document at 300+ DPI and retry.
B. Run OCR preprocessing: marker-pdf or tesseract on each page image, save as
   searchable PDF, then re-run this skill on the searchable output.
C. Manual redaction: print, physically redact, re-scan.

Do NOT distribute a redacted output from this unreadable input - PII leakage risk is HIGH.
```

## Phase 1 - Run the Redaction Script

```bash
python3 ~/.hermes/skills/productivity/pii-redaction/scripts/redact_pii.py \
    --input /path/to/trust_deed.pdf \
    --output /path/to/trust_deed_redacted.pdf \
    --log /path/to/trust_deed_redact_log.json \
    --quality-report /path/to/trust_deed_ocr_quality.json \
    --adversarial-passes 3
```

For DOCX:
```bash
python3 ~/.hermes/skills/productivity/pii-redaction/scripts/redact_pii.py \
    --input /path/to/trust_deed.docx \
    --output /path/to/trust_deed_redacted.docx \
    --log /path/to/trust_deed_redact_log.json \
    --adversarial-passes 3
```

Options:
- `--adversarial-passes N` - number of re-extraction detection loops (default 3)
- `--dry-run` - print detections without writing output file
- `--strict` - exit 1 if any leakage remains after N passes
- `--check-ocr-only` - run OCR quality assessment only, no redaction
- `--no-ner` - disable spaCy NER, use Presidio regex recognisers only (faster, lower recall)
- `--min-confidence 0.7` - minimum Presidio confidence score to redact (default 0.6)
- `--whitelist-entity CORP_NAME` - whitelist a corporate trustee name from FULL_NAME detection

## Phase 2 - Review the Audit Log

```bash
python3 -c "
import json
d = json.load(open('trust_deed_redact_log.json'))
print(json.dumps(d['summary'], indent=2))
"
```

The audit log structure:

```json
{
  "input_file": "/path/to/trust_deed.pdf",
  "output_file": "/path/to/trust_deed_redacted.pdf",
  "timestamp": "2026-08-19T10:00:00",
  "ocr_quality": "good",
  "ocr_confidence_score": 0.97,
  "passes": [
    {
      "pass_number": 1,
      "detections_count": 42,
      "detections": [
        {
          "page": 1,
          "category": "FULL_NAME",
          "matched_text": "John Smith",
          "presidio_score": 0.85,
          "char_start": 120,
          "char_end": 130
        }
      ]
    }
  ],
  "trust_name_review_items": ["Smith Family Trust"],
  "vision_only_detections": [],
  "summary": {
    "total_redactions": 42,
    "categories": {"FULL_NAME": 15, "AU_ADDRESS": 8, "AU_TFN": 4, "DATE_OF_BIRTH": 3, "PHONE_NUMBER": 12},
    "adversarial_passes": 3,
    "final_leakage_count": 0
  }
}
```

## Phase 3 - Adversarial Self-Review (agent-level, external to script)

After the script exits, the agent must run this external adversarial pass:

1. Confirm `final_leakage_count == 0` in audit log.

2. Run the script again in dry-run mode on the REDACTED output to verify zero detections:
```bash
python3 ~/.hermes/skills/productivity/pii-redaction/scripts/redact_pii.py \
    --input /path/to/trust_deed_redacted.pdf \
    --dry-run \
    --log /dev/stdout 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); \
    print('LEAKAGE COUNT:', d['summary']['final_leakage_count'])"
```
Zero = clean. Non-zero = report to user with the specific leaked items.

3. Visual spot-check: sample 3 random pages from the redacted PDF using vision_analyze.
Confirm `[REDACTED]` markers are visible and named individuals cannot be identified.

4. Check trust_name_review_items in audit log. Report these to user for human decision.

5. If `ocr_quality == low_confidence`: present the OCR QUALITY FLAG block (Phase 0c) to user.

## Recursive Adversarial Loop (built into script)

```
PASS 1: Extract text -> detect PII via Presidio -> apply redactions -> write output
PASS 2: Re-extract text from redacted output -> detect again -> patch survivors -> rewrite
PASS N: Repeat until zero detections or pass limit reached
```

Per-pass detection counts are logged. If count does not decrease between passes, the
script raises an oscillation warning and continues (does not loop forever). Hard cap
at `--adversarial-passes`.

## Copilot Usage

This skill is designed to work as a copilot step in a larger workflow.
Invoke from another agent or delegate_task:

```python
result = terminal(
    command=(
        f"python3 ~/.hermes/skills/productivity/pii-redaction/scripts/redact_pii.py "
        f"--input {input_path} --output {output_path} "
        f"--log {log_path} --quality-report {quality_report_path} "
        f"--adversarial-passes 3 --strict"
    )
)
log = json.loads(read_file(log_path)["content"])
quality = json.loads(read_file(quality_report_path)["content"])

# OCR gate
if quality["ocr_quality"] == "unreadable":
    raise RuntimeError("Document unreadable - cannot guarantee PII redaction. See quality report.")
if quality["ocr_quality"] == "low_confidence":
    # Surface flag to user - do NOT silently continue
    report_ocr_quality_flag(quality)

# Leakage gate
assert log["summary"]["final_leakage_count"] == 0, f"PII leakage: {log['summary']['final_leakage_count']} items"
# Trust name gate
if log.get("trust_name_review_items"):
    report_trust_name_review(log["trust_name_review_items"])
```

Structured output contract:
```json
{
  "output_file": "/absolute/path/to/redacted.pdf",
  "audit_log": "/absolute/path/to/log.json",
  "ocr_quality_report": "/absolute/path/to/ocr_quality.json",
  "summary": {
    "total_redactions": 42,
    "categories": {"FULL_NAME": 15, "AU_ADDRESS": 8, "AU_TFN": 4},
    "adversarial_passes": 3,
    "final_leakage_count": 0,
    "ocr_quality": "good",
    "ocr_confidence_score": 0.97
  }
}
```

## Common Pitfalls

1. Scanned/image-only PDFs: `pdfplumber` returns empty text. The machine OCR check
   detects this and either flags LOW_CONFIDENCE or halts on UNREADABLE. Never skip Phase 0.

2. Vision assessment skipped for "obvious" text PDFs: even text-layer PDFs can have
   partially scanned pages. Always run the machine check; only skip vision if score >= 0.8.

3. spaCy model missing: script falls back to `en_core_web_sm` then regex-only.
   Regex-only has ~20-25% lower name recall. Always use `en_core_web_lg` for production.

4. Corporate vs individual names: script uses company-suffix heuristic
   (`Pty Ltd`, `Pty. Ltd.`, `Ltd`, `Inc`, `Corp`, `LLC`, `Trustee` when attached to a company)
   to whitelist corporate names. Review FULL_NAME detections in audit log for false positives
   on corporate trustee names.

5. Trust name in title: "Smith Family Trust" contains a surname. Presidio NER will flag it.
   Script places it in `trust_name_review_items` in the audit log (not auto-redacted). Report to user.

6. Password-protected PDFs: decrypt with `pymupdf` before redacting:
   ```bash
   python3 -c "import fitz; d=fitz.open('in.pdf'); d.authenticate('password'); d.save('decrypted.pdf')"
   ```

7. DOCX tracked changes: accept all changes in LibreOffice before redacting; tracked-change
   XML may contain original PII text that python-docx does not expose via the standard API.

8. PDF metadata leakage: this skill redacts text layer only. After redaction, strip metadata:
   ```bash
   python3 -c "import fitz; d=fitz.open('redacted.pdf'); d.set_metadata({}); d.save('clean.pdf')"
   ```

9. Oscillation: if pass N and N+1 have identical non-zero detection counts, patterns are not
   being caught and fixed. Script caps at `--adversarial-passes` and exits 1 with `--strict`.
   Add the undetected pattern to `--whitelist-entity` or file an issue.

10. Poor OCR produces garbled text that defeats regex patterns: e.g. TFN "1234 56789" may
    OCR as "I234 56789" (capital I for digit 1). Vision check catches visually present PII
    that OCR cannot extract reliably. Always report vision_only_detections to user.

11. Multi-column or complex layout PDFs: pdfplumber extracts text in bounding-box order;
    merged cells or overlapping columns may jumble text. Spot-check extraction quality on
    a complex-layout page with vision_analyze before trusting automated detection.

## Verification Checklist

- [ ] Phase 0 OCR quality check completed and result documented
- [ ] If ocr_quality == low_confidence: vision check run on sample pages, flag presented to user
- [ ] If ocr_quality == unreadable: halted, user notified, no redacted output distributed
- [ ] `final_leakage_count == 0` in audit log
- [ ] External dry-run on redacted output returns zero detections (Phase 3 step 2)
- [ ] Visual spot-check via vision_analyze on 3 sample pages confirms [REDACTED] markers present
- [ ] PDF metadata cleared (text-layer redaction does not touch metadata)
- [ ] DOCX tracked changes accepted before redaction (if applicable)
- [ ] Corporate trustee names reviewed in audit log (not over-redacted)
- [ ] trust_name_review_items reviewed and decision documented
- [ ] vision_only_detections reviewed and manually redacted if any
- [ ] Redacted file (not the original) delivered to requester

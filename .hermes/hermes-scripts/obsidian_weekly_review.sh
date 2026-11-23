#!/usr/bin/env bash
# Obsidian Weekly Review — runs every Friday at 5pm
# Creates Reviews/YYYY-MM-DD-weekly.md in the Obsidian vault
# Source: r/WebAfterAI Obsidian+Claude workflows post

VAULT="/var/home/rainbow/Documents/SecondBrain"
TODAY="$(date +%F)"
OUTPUT="$VAULT/Reviews/$TODAY-weekly.md"

mkdir -p "$VAULT/Reviews"

# Find modified notes from the last 7 days
MODIFIED_FILES=$(find "$VAULT" -name "*.md" -mtime -7 \
  -not -path "*/Reviews/*" \
  -not -path "*/.obsidian/*" \
  -not -path "*/templates/*" \
  2>/dev/null | head -50)

FILE_LIST=""
for f in $MODIFIED_FILES; do
  FILE_LIST="$FILE_LIST\n$(basename "$f") ($(dirname "$f" | sed "s|$VAULT/||"))"
done

echo "Weekly review: found $(echo "$MODIFIED_FILES" | wc -l | tr -d ' ') modified notes"
echo "Output: $OUTPUT"

# Write the review note (Hermes will synthesize; this sets the scaffold)
cat > "$OUTPUT" << REVIEW
---
date: $TODAY
type: weekly-review
generated: true
---

# Weekly Review — $TODAY

> Auto-generated from notes modified in the last 7 days.
> Review and annotate as needed.

## Modified Notes This Week

$(echo -e "$FILE_LIST")

## Synthesis Prompt (run manually with hermes or Claude Code)

\`\`\`
cd $VAULT
Find every note modified in the last 7 days (already listed above).
Write a concise weekly review covering:
1. Accomplishments and completed work
2. Decisions made and rationale
3. Tasks completed vs planned
4. Patterns or recurring themes noticed
5. Suggested priorities for next week

Append the result under "## Review" in: Reviews/$TODAY-weekly.md
Keep it under 400 words.
\`\`\`

## Review

_Pending synthesis — run the prompt above or use hermes to fill this in._
REVIEW

echo "Done. Review scaffold written to: $OUTPUT"

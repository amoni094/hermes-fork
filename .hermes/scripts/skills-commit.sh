#!/usr/bin/env bash
# ~/.hermes/scripts/skills-commit.sh
# Safe wrapper to commit skills changes without scanning all of $HOME
# Usage: skills-commit.sh "describe the change"

MSG="${1:-skills: update}"
SKILLS_DIR="$HOME/.hermes/skills"

cd "$HOME" || exit 1

# Stage only the skills directory specifically
git add "$SKILLS_DIR"

# Also stage agent-hooks and scripts if they were changed
git add "$HOME/.hermes/agent-hooks/" "$HOME/.hermes/scripts/" 2>/dev/null

GIT_AUTHOR_EMAIL=hermes@local \
GIT_COMMITTER_EMAIL=hermes@local \
GIT_AUTHOR_NAME=Hermes \
GIT_COMMITTER_NAME=Hermes \
  git commit -m "$MSG" -- \
    ".hermes/skills" \
    ".hermes/agent-hooks" \
    ".hermes/scripts" \
    ".hermes/budget-policy.yaml" \
    2>&1

echo "Done."

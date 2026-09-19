#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash /var/home/rainbow/.hermes/profiles/fork/cache/blocked-scripts/blocked-1789739624-1918b121.sh
# AV7: Hardcoded ~/.hermes/ in hermes_cli/ Python code (not strings/comments/user-facing)
# We want actual code paths, not help text/comments
grep -rn '\"~/.hermes/' /var/home/rainbow/.hermes/hermes-fork/hermes_cli/ --include="*.py" | grep -v "#.*~" | grep -v "help=" | grep -v "print(" | grep -v "\"\"\"" | head -30

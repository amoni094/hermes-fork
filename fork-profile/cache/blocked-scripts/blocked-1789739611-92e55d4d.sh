#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash /var/home/rainbow/.hermes/profiles/fork/cache/blocked-scripts/blocked-1789739611-92e55d4d.sh
# AV6/AV7: Hardcoded ~/.hermes/ strings
grep -rn "~/.hermes\|/\.hermes/" /var/home/rainbow/.hermes/hermes-fork/hermes_cli/ --include="*.py" | grep -v "venv\|#\|\"\"\"" | grep -v "\.pyc" | head -40

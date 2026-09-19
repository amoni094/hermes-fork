#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash /var/home/rainbow/.hermes/profiles/fork/cache/blocked-scripts/blocked-1789724890-392e0b06.sh
grep -n "pre_compress" ~/.hermes/hermes-agent/hermes_cli/plugins.py | head -10
echo "---"
grep -rn "invoke_hook.*['\"]pre_compress['\"]" ~/.hermes/hermes-agent/ --include="*.py" | grep -v test | head -10

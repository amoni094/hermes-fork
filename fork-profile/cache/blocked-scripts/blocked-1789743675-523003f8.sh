#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash /var/home/rainbow/.hermes/profiles/fork/cache/blocked-scripts/blocked-1789743675-523003f8.sh
grep -rn "\"model\"\|\"help\"\|\"voice\"\|\"clear\"\|\"forget\"\|\"goal\"\|\"login\"\|\"session\"\|\"pause\"\|\"resume\"\|\"rollback\"\|\"diff\"\|\"status\"\|\"version\"\|\"platform\"\|\"whoami\"\|\"profile\"\|\"kanban\"\|\"pin\"" \
  ~/.hermes/hermes-fork/gateway/slash_commands.py 2>/dev/null | grep -v "^.*#\|import\|def \|str\|msg\|text\|content\|\"[a-z]*\":.*\"[a-z]" | head -30

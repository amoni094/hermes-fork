---
name: secret-hygiene
description: >-
  Enforce safe handling of secrets, API keys, credentials, and .env files in any
  terminal command or code. Trigger on "environment variables", "secrets", ".env",
  "API key", "credentials", "token", "password", or any command that might expose
  sensitive values. Ensures secrets never appear in Claude's context, terminal output,
  logs, git history, or error messages.
tags: [security, secrets, credentials, env-vars, hygiene]
version: "1.0"
---

# Secret Hygiene

Secrets must NEVER appear in:
- Terminal output (Claude reads all terminal output)
- Commands that echo, print, or log their arguments
- Git commits, diffs, or history
- Error messages
- curl/http headers constructed inline

## Hard Rules

### Rule 1: Never echo or print secret values
```bash
# NEVER
echo $API_KEY
printenv | grep SECRET
cat .env
env | grep TOKEN
python -c "import os; print(os.environ['SECRET'])"

# SAFE: validate presence without revealing value
test -n "$API_KEY" && echo "API_KEY is set" || echo "MISSING"
python -c "import os; print('set' if os.environ.get('SECRET') else 'MISSING')"
```

### Rule 2: Never read .env files directly
```bash
# NEVER
cat .env
less .env
head .env
grep SECRET .env
# (Read tool on .env file — also never)

# SAFE: read the schema/example file only
cat .env.example
cat .env.schema
```

### Rule 3: Never inline secrets in commands
```bash
# NEVER
curl -H "Authorization: Bearer sk-abc123" https://api.example.com
psql "postgresql://user:supersecret@host/db"
aws configure set aws_secret_access_key AKIAIOSFODNN7EXAMPLE

# SAFE: use env vars already set in the shell
curl -H "Authorization: Bearer $API_KEY" https://api.example.com
psql "$DATABASE_URL"
```

### Rule 4: Secrets don't go in command history or scripts
```bash
# NEVER hardcode in scripts
export API_KEY=sk-abc123

# SAFE: load from env file before running, or use a secret manager
set -a && source .env && set +a
# Or use direnv, Varlock, doppler, etc.
```

### Rule 5: Git must never commit secrets
```bash
# Before any git add, check:
git diff --cached | grep -iE "(secret|key|token|password|credential)" | head -20

# .gitignore must include:
.env
.env.local
.env.*.local
*.pem
*.key
```

## Safe Validation Patterns

Check if env vars are set without revealing them:
```bash
# Check multiple at once
for var in API_KEY DATABASE_URL SECRET_TOKEN; do
  if [ -n "${!var}" ]; then
    echo "$var: set (${#!var} chars)"
  else
    echo "$var: MISSING"
  fi
done
```

Check a .env file has the right keys without reading values:
```bash
# List keys only (not values)
grep -oE '^[A-Z_]+(?==)' .env
# Or with sed:
sed 's/=.*//' .env | grep -v '^#'
```

## When Claude Is Asked to Debug Secrets Issues

1. Ask user to show .env.example or .env.schema (not .env)
2. Ask which keys are expected, not what their values are
3. Use the key-listing patterns above to verify presence
4. If a value format needs checking, ask the user to run a local validation and share only the pass/fail result

## Pitfalls

- subprocess.run(['env'], capture_output=True) dumps all env vars — never do this
- Docker build args can leak into image layers — never pass secrets as ARGs
- pytest -s can print secrets if tests log them — use capfd/capsys carefully
- GitHub Actions: never use ${{ secrets.FOO }} in run: echo — use env: blocks
- CI logs: mask secrets with ::add-mask:: before any step that touches them

# Self-evolution validation

Verified local paths:
- Hermes repo: `/var/home/rainbow/.hermes/hermes-agent`
- Self-evolution repo: `/var/home/rainbow/hermes-agent-self-evolution`

Verified setup pattern:
```bash
git clone --depth 1 https://github.com/NousResearch/hermes-agent-self-evolution /var/home/rainbow/hermes-agent-self-evolution
cd /var/home/rainbow/hermes-agent-self-evolution
uv venv .venv
. .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q
python -m evolution.skills.evolve_skill --help
HERMES_AGENT_REPO=/var/home/rainbow/.hermes/hermes-agent \
python -m evolution.skills.evolve_skill --skill hermes-agent --dry-run
```

Verified results from the first evaluation:
- dependency install succeeded with `uv`
- test suite passed: `145 passed`
- CLI entrypoint worked: `python -m evolution.skills.evolve_skill --help`
- dry-run succeeded against the local Hermes repo

Operational conclusion:
- Hermes already has a built-in runtime self-improvement loop for memory/skills.
- `hermes-agent-self-evolution` should be treated as a separate offline optimizer, not a default always-on mutation loop.
- The safe first adoption path is one controlled optimization pass on a compact skill with explicit diff review.

Selection note:
- avoid using a giant umbrella skill such as `hermes-agent` as the first real target even if dry-run works;
- prefer a smaller, frequently used skill with clearer evaluation criteria.

Guardrail note:
- human review remains the merge boundary for evolved outputs.
- validate locally before recommending adoption; do not rely on README claims alone.

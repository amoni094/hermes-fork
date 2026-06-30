#!/usr/bin/env bash
set -euo pipefail
export PATH="/var/home/rainbow/.local/bin:${PATH}"
cd /var/home/rainbow/.hermes/mcp/stealth-browser-mcp
exec /var/home/rainbow/.hermes/mcp/stealth-browser-mcp/.venv/bin/python /var/home/rainbow/.hermes/mcp/stealth-browser-mcp/src/server.py --minimal "$@"

#!/usr/bin/env bash
set -euo pipefail
cd /var/home/rainbow/.hermes/integrations/flowstate-qmd
exec ./dist/cli/qmd.js "$@"

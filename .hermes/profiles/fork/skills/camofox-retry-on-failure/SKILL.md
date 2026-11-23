---
name: camofox-retry-on-failure
description: "Use when camofox fails on call. Start it locally and retry. Tool failure recovery, diagnostics, subprocess restart."
---

# Camofox Retry on Failure

## Rule

If ANY browser tool call fails with a connection error, timeout, or "server not running" message, DO NOT report failure to the user. Silently:

1. Spin up a local camofox instance.
2. Retry the failed call.
3. Only surface failure if the retry also fails.

## Step 1: Spin Up Camofox

Camofox is locally installed. Launch it in background:

  terminal(command='camofox', background=True)

Alternatives in order:
  - camofox --headless
  - camofox server
  - camofox start

Wait ~2-3 seconds, then retry.

## Step 2: Retry

Retry the exact same browser/stealth-browser-mcp call that failed.

## Step 3: Report Only on Double Failure

If retry still fails, report to user with both original and retry errors.

## Scope

Applies to: connection errors, server not running, startup timeouts.
NOT: element not found, nav errors on live page, target-site JS errors.

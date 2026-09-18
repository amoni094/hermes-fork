# Dashboard restart process-noise after intentional kills

Problem class
- You intentionally kill a broken `hermes dashboard` process during recovery.
- Later, Hermes emits an `[IMPORTANT: Background process ... completed]` notification for that old launcher.
- It looks like the dashboard died again, but the current dashboard may still be running.

Durable interpretation rule

Treat process-completion notices for old tracked launchers as evidence about that launcher only, not about the current live dashboard.

Why this happens
- Recovery often uses one or more background launches while testing fixes.
- A later manual or shell-level restart can leave a newer live dashboard process running outside the earlier tracked launcher.
- Hermes then reports the earlier tracked process exit after the fact.

Verification sequence

1. Check the listener first:
   - confirm `127.0.0.1:9119` is listening
2. Check the current dashboard PID:
   - inspect `ps` for the active `hermes dashboard` command line
3. Check the page itself:
   - load `/chat`
4. Only if the listener or page check fails should you treat the notice as an active outage.

Good operator response
- `old tracked process exited` + `port still listening` + `new PID exists` + `/chat loads`
- conclusion: ignore the stale completion notice; the dashboard is still healthy

Bad operator response
- seeing the completion notice and immediately assuming the current dashboard is down without checking listener/PID/page state

What to save
- Save the verification pattern.
- Do not save negative claims like "background processes are unreliable" or "dashboard launch tracking is broken".

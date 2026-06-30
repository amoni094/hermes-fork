Session note: WorldMonitor Reddit/social recovery pattern

Scenario
- WorldMonitor health showed Reddit-related degradation.
- Host-side Firefox-backed Reddit access worked via social_signals.py after adding an HTML fallback.
- Container-side Reddit fetches often returned a 200 verification page ('Please wait for verification') rather than usable post data.

What worked
- Patch the host collector first so live Reddit items are actually retrievable.
- Distinguish collector recovery from downstream health recovery.
- Add a small host-side reseed path that writes the canonical seed/envelope shape for the affected key.
- Verify the exact health field after reseeding.

Important diagnostic lesson
- 200 OK from Reddit was not sufficient evidence of success.
- The body could still be a verification/challenge page with no usable post payload.
- Validation must check payload markers/content shape, not only HTTP status.

Observed recovery shape
- socialVelocity recovered to OK after reseeding canonical Reddit seed data from the host path.
- wsbTickers remained EMPTY_DATA because the available recovered Reddit sample did not contain enough finance/ticker-bearing items to seed that dataset honestly.

Reusable rule
- When one dataset can be restored and an adjacent one cannot, report a partial fix explicitly.
- Do not inflate a thin or off-topic recovery sample just to make the health board look green.

Implementation pattern
- Preserve existing Redis key names and envelope schema.
- Keep worker patches small.
- If environment asymmetry persists, prefer a host-side emergency reseeder over a fake in-container success path.

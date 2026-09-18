# Hindsight Worker Poll Interval Diagnosis — Sep 2026

## Observed symptom

- PID 10875, hindsight-api --host 127.0.0.1 --port 9177 --idle-timeout 0
- CPU: 41.2% sustained over 244 minutes (utime=13144s, stime=1553s)
- Threads: 51
- RAM: 4.4% (1.44 GB RSS) — normal for loaded cross-encoder
- Health endpoint: healthy, database: connected
- No errors in daemon.log

## Root cause

Default `HINDSIGHT_API_WORKER_POLL_INTERVAL_MS = 500` (from config.py).
51 threads polling postgres every 500ms with an empty work queue = continuous wasted CPU.

Config source confirmed:
  ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hindsight_api/config.py
  DEFAULT_WORKER_POLL_INTERVAL_MS = 500
  ENV_WORKER_POLL_INTERVAL_MS = "HINDSIGHT_API_WORKER_POLL_INTERVAL_MS"

## Fix applied

Drop-in: ~/.config/systemd/user/hindsight-api.service.d/99-poll-interval.conf

  [Service]
  Environment=HINDSIGHT_API_WORKER_POLL_INTERVAL_MS=2000

Reloaded daemon, restarted service.

## Verification results (7/7 passed)

1. PASS: drop-in has correct poll value (2000ms)
2. PASS: live unit env var is 2000ms
3. PASS: hindsight-api is active
4. PASS: health endpoint: healthy + db connected
5. PASS: CPU% < 30 (was 41%): 11.1%
6. PASS: tuned profile: balanced-battery
7. PASS: drop-in is unit-scoped (not global)

CPU settled at 11.1% after 60 seconds, down from 41.2%.

## Notes

- Retention latency increase: ~1.5s max (imperceptible in practice)
- poll_interval=2000ms is safe at idle; if hindsight_retain call latency becomes
  perceptible in sessions, can lower to 1000ms
- This fix survives service restarts (env var in drop-in, not applied via renice)
- Drop-in is unit-scoped to hindsight-api.service.d/ only

#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

LOCAL_URL = 'http://127.0.0.1:3000/api/health'
REMOTE_URL = 'https://api.worldmonitor.app/api/health'
WORLDMONITOR_CONTAINERS = [
    'worldmonitor-redis',
    'worldmonitor-redis-rest',
    'worldmonitor-ais-relay',
    'worldmonitor',
]
FOCUS_KEYS = [
    'earthquakes',
    'weatherAlerts',
    'riskScores',
    'marketQuotes',
    'predictionMarkets',
    'securityAdvisories',
    'displacementSummary',
    'naturalEvents',
    'climateAnomalies',
]


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={'Origin': 'http://localhost', 'User-Agent': 'Hermes-WorldMonitor-Signal/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def local_health_ready() -> bool:
    try:
        fetch_json(LOCAL_URL)
        return True
    except Exception:
        return False


def try_start_local_worldmonitor() -> tuple[bool, str]:
    if local_health_ready():
        return True, 'local health already responding'
    podman = shutil.which('podman')
    if not podman:
        return False, 'podman not available'
    try:
        result = subprocess.run(
            [podman, 'start', *WORLDMONITOR_CONTAINERS],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as e:
        return False, f'podman start failed: {e}'

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()
        return False, f'podman start exited {result.returncode}: {detail}'

    deadline = time.time() + 45
    while time.time() < deadline:
        if local_health_ready():
            return True, 'started local worldmonitor containers'
        time.sleep(1.5)
    return False, 'containers started but local health did not become ready within 45s'


def summarize_payload(payload: dict, source: str) -> dict:
    checks = payload.get('checks') or {}
    focus = {}
    ok = warn = crit = other = 0
    for key in FOCUS_KEYS:
        item = checks.get(key)
        if not isinstance(item, dict):
            continue
        status = str(item.get('status', 'unknown')).upper()
        if status == 'OK':
            ok += 1
        elif status == 'WARN':
            warn += 1
        elif status == 'CRIT':
            crit += 1
        else:
            other += 1
        compact = {'status': status}
        for field in ('recordCount', 'count', 'summary', 'message', 'updatedAt'):
            val = item.get(field)
            if val not in (None, '', [], {}):
                compact[field] = val
        focus[key] = compact
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': source,
        'overall_status': payload.get('status'),
        'overall_summary': payload.get('summary'),
        'checked_at': payload.get('checkedAt'),
        'focus_counts': {'ok': ok, 'warn': warn, 'crit': crit, 'other': other},
        'focus_checks': focus,
    }


def main():
    ap = argparse.ArgumentParser(description='Summarize WorldMonitor health for Hermes news workflows.')
    ap.add_argument('--format', choices=['json', 'text'], default='text')
    ap.add_argument('--prefer', choices=['local', 'remote'], default='local')
    args = ap.parse_args()

    startup_note = None
    if args.prefer == 'local':
        started, note = try_start_local_worldmonitor()
        startup_note = note

    tried = []
    urls = [LOCAL_URL, REMOTE_URL] if args.prefer == 'local' else [REMOTE_URL, LOCAL_URL]
    last_err = None
    for url in urls:
        tried.append(url)
        try:
            payload = fetch_json(url)
            summary = summarize_payload(payload, 'local' if '127.0.0.1' in url else 'remote')
            if startup_note:
                summary['startup_note'] = startup_note
            if args.format == 'json':
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                print(f"WorldMonitor source: {summary['source']}")
                if startup_note:
                    print(f"Startup: {startup_note}")
                print(f"Status: {summary['overall_status']}")
                print(f"Summary: {summary['overall_summary']}")
                if summary.get('checked_at'):
                    print(f"Checked at: {summary['checked_at']}")
                fc = summary['focus_counts']
                print(f"Focus checks: ok={fc['ok']} warn={fc['warn']} crit={fc['crit']} other={fc['other']}")
                for key, item in summary['focus_checks'].items():
                    details = []
                    for field in ('recordCount', 'count', 'summary', 'message', 'updatedAt'):
                        if field in item:
                            details.append(f"{field}={item[field]}")
                    suffix = f" ({', '.join(details)})" if details else ''
                    print(f"- {key}: {item['status']}{suffix}")
            return 0
        except Exception as e:
            last_err = e
            continue

    print('WorldMonitor health unavailable', file=sys.stderr)
    if startup_note:
        print(f'Startup: {startup_note}', file=sys.stderr)
    print('Tried:', ', '.join(tried), file=sys.stderr)
    if last_err is not None:
        print(f'Last error: {last_err}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from typing import Any

CHROMIUM_CANDIDATES = [
    'chromium',
    'chromium-browser',
    'google-chrome',
    'google-chrome-stable',
]


def extract_meta_content(page_html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.I)
        if match:
            return html.unescape(re.sub(r'\s+', ' ', match.group(1)).strip())
    return ''


def extract_title_text(page_html: str) -> str:
    match = re.search(r'<title>(.*?)</title>', page_html, flags=re.I | re.S)
    if not match:
        return ''
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', match.group(1))).strip())


def render_html(url: str, budget_ms: int) -> tuple[str, str]:
    last_error = 'chromium not found'
    for binary in CHROMIUM_CANDIDATES:
        try:
            run = subprocess.run(
                [
                    binary,
                    '--headless',
                    '--disable-gpu',
                    '--no-sandbox',
                    f'--virtual-time-budget={budget_ms}',
                    '--dump-dom',
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=max(20, min(60, budget_ms // 1000 + 15)),
                check=False,
            )
        except FileNotFoundError:
            continue
        except Exception as exc:
            last_error = str(exc)
            continue
        if run.returncode == 0 and run.stdout.strip():
            return run.stdout, binary
        last_error = (run.stderr or run.stdout or f'{binary} failed').strip()[:500]
    raise RuntimeError(last_error)


def main() -> int:
    parser = argparse.ArgumentParser(description='Render a public social page with local Chromium and return HTML/metadata.')
    parser.add_argument('url')
    parser.add_argument('--budget-ms', type=int, default=8000)
    parser.add_argument('--format', choices=['json', 'html'], default='json')
    parser.add_argument('--max-bytes', type=int, default=600000)
    args = parser.parse_args()

    try:
        page_html, browser = render_html(args.url, args.budget_ms)
    except Exception as exc:
        print(json.dumps({'ok': False, 'url': args.url, 'error': str(exc)}, ensure_ascii=False))
        return 1

    if args.max_bytes and len(page_html.encode('utf-8', 'ignore')) > args.max_bytes:
        page_html = page_html[: args.max_bytes]

    if args.format == 'html':
        sys.stdout.write(page_html)
        return 0

    payload: dict[str, Any] = {
        'ok': True,
        'url': args.url,
        'browser': browser,
        'title': extract_meta_content(page_html, 'og:title') or extract_title_text(page_html),
        'description': extract_meta_content(page_html, 'og:description') or extract_meta_content(page_html, 'description') or extract_meta_content(page_html, 'twitter:description'),
        'html': page_html,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

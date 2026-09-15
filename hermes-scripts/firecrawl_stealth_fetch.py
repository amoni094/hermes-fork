#!/var/home/rainbow/.hermes/mcp/stealth-browser-mcp/.venv/bin/python
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

REPO_ROOT = Path('/var/home/rainbow/.hermes/mcp/stealth-browser-mcp')
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from browser_manager import BrowserManager  # noqa: E402
from dom_handler import DOMHandler  # noqa: E402
from models import BrowserOptions  # noqa: E402

SESSION_ROOT = Path('/var/home/rainbow/.hermes/state/stealth-browser-sessions')
DEBUG_RUN_ROOT = Path('/var/home/rainbow/.hermes/state/firecrawl-stealth-debug')


def _firecrawl_base_url() -> str:
    return os.environ.get('FIRECRAWL_API_URL', 'http://127.0.0.1:3002').rstrip('/')


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9._-]+', '-', value).strip('-._')
    return slug or 'default'


def _default_session_name(url: str) -> str:
    parsed = urlparse(url)
    return _slugify(parsed.netloc or parsed.path or 'default')


def _resolve_session_dir(url: str, session_name: Optional[str], session_dir: Optional[str]) -> Optional[str]:
    if session_dir:
        path = Path(session_dir).expanduser().resolve()
    elif session_name:
        path = SESSION_ROOT / _slugify(session_name)
    else:
        return None
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _parse_headers(header_args: List[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for raw in header_args:
        if ':' not in raw:
            raise ValueError(f'Invalid --header value (expected Key: Value): {raw}')
        key, value = raw.split(':', 1)
        headers[key.strip()] = value.strip()
    return headers


def _make_debug_run_dir(url: str) -> Path:
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = DEBUG_RUN_ROOT / f"{stamp}-{_default_session_name(url)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


BLOCK_INDICATORS = [
    'just a moment',
    'attention required',
    'verify you are human',
    'checking if the site connection is secure',
    'cf-browser-verification',
    'cloudflare',
    'captcha',
    'enable javascript and cookies',
    'press and hold',
    'ddos protection by',
    'bot verification',
    'access denied',
]


def detect_blocked_content(title: str, content: str, html: str, metadata: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    haystacks = [title.lower(), content.lower(), html.lower()]
    joined = '\n'.join(h for h in haystacks if h)

    for indicator in BLOCK_INDICATORS:
        if indicator in joined:
            reasons.append(f'text-indicator:{indicator}')

    status_code = metadata.get('statusCode')
    if status_code in {401, 403, 429, 503}:
        reasons.append(f'status-code:{status_code}')

    if content and len(content.strip()) < 120 and any(x in joined for x in ('cloudflare', 'captcha', 'access denied', 'just a moment')):
        reasons.append('suspiciously-short-block-page')

    return sorted(set(reasons))


def fetch_via_firecrawl(url: str, timeout: int) -> Dict[str, Any]:
    endpoint = f"{_firecrawl_base_url()}/v1/scrape"
    response = requests.post(
        endpoint,
        json={"url": url, "formats": ["markdown", "html"]},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get('success'):
        raise RuntimeError(f"Firecrawl returned success=false: {payload}")
    data = payload.get('data') or {}
    metadata = data.get('metadata') or {}
    content = data.get('markdown') or data.get('html') or ''
    if not content:
        raise RuntimeError('Firecrawl returned no content')
    title = metadata.get('title') or ''
    html = data.get('html') or ''
    block_reasons = detect_blocked_content(title, content, html, metadata)
    return {
        'mode': 'firecrawl',
        'success': True,
        'url': metadata.get('sourceURL') or metadata.get('url') or url,
        'title': title,
        'content': content,
        'html': html,
        'metadata': metadata,
        'debug': {
            'firecrawl_block_reasons': block_reasons,
        },
    }


async def fetch_via_stealth(
    url: str,
    timeout_ms: int,
    headless: bool,
    proxy: Optional[str] = None,
    session_dir: Optional[str] = None,
    timezone_id: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    manager = BrowserManager()
    options = BrowserOptions(
        headless=headless,
        proxy=proxy,
        user_data_dir=session_dir,
        timezone_id=timezone_id,
        extra_headers=extra_headers or {},
    )
    instance = await manager.spawn_browser(options)
    try:
        nav = await manager.navigate(instance.instance_id, url, timeout=timeout_ms)
        tab = await manager.get_tab(instance.instance_id)
        if tab is None:
            raise RuntimeError('Stealth browser tab unavailable after navigation')
        page = await DOMHandler.get_page_content(tab)
        return {
            'mode': 'stealth-browser-mcp',
            'success': True,
            'url': page.get('url') or nav.get('url') or url,
            'title': page.get('title') or nav.get('title') or '',
            'content': page.get('text') or '',
            'html': page.get('html') or '',
            'metadata': {
                'navigation': nav,
                'session_dir': session_dir,
                'proxy': bool(proxy),
                'timezone_id': timezone_id,
                'extra_headers': sorted((extra_headers or {}).keys()),
            },
        }
    finally:
        try:
            await manager.close_instance(instance.instance_id)
        except Exception:
            pass


async def main() -> int:
    parser = argparse.ArgumentParser(description='Fetch a URL with Firecrawl first, then stealth-browser fallback.')
    parser.add_argument('url')
    parser.add_argument('--timeout', type=int, default=60, help='Firecrawl timeout in seconds')
    parser.add_argument('--stealth-timeout-ms', type=int, default=45000, help='Stealth browser navigation timeout in milliseconds')
    parser.add_argument('--headless', action='store_true', default=False, help='Run stealth browser headless')
    parser.add_argument('--force-stealth', action='store_true', help='Skip Firecrawl and use stealth browser directly')
    parser.add_argument('--json-only', action='store_true', help='Print only the JSON result')
    parser.add_argument('--debug-block-detection', action='store_true', help='Print Firecrawl block-detection reasons and fallback decisions')
    parser.add_argument('--save-debug-files', action='store_true', help='Save Firecrawl/stealth debug payloads under ~/.hermes/state/firecrawl-stealth-debug')
    parser.add_argument('--proxy', help='Proxy URL for stealth fallback, e.g. http://user:pass@host:port')
    parser.add_argument('--session-name', help='Persistent session name for cookie/storage reuse')
    parser.add_argument('--session-dir', help='Explicit persistent browser profile directory for cookie/storage reuse')
    parser.add_argument('--timezone', help='Timezone ID for stealth browser, e.g. Australia/Sydney')
    parser.add_argument('--header', action='append', default=[], help='Extra header for stealth requests, repeatable: Key: Value')
    args = parser.parse_args()

    try:
        extra_headers = _parse_headers(args.header)
    except ValueError as exc:
        print(json.dumps({'success': False, 'errors': [str(exc)], 'url': args.url}, ensure_ascii=False, indent=2))
        return 2

    session_name = args.session_name or _default_session_name(args.url)
    session_dir = _resolve_session_dir(args.url, session_name if (args.session_name or args.session_dir) else None, args.session_dir)
    debug_run_dir = _make_debug_run_dir(args.url) if args.save_debug_files else None

    errors = []
    result: Optional[Dict[str, Any]] = None
    firecrawl_result: Optional[Dict[str, Any]] = None
    stealth_result: Optional[Dict[str, Any]] = None

    if not args.force_stealth:
        try:
            firecrawl_result = fetch_via_firecrawl(args.url, args.timeout)
            if debug_run_dir is not None:
                _write_json(debug_run_dir / 'firecrawl_result.json', firecrawl_result)
            block_reasons = firecrawl_result.get('debug', {}).get('firecrawl_block_reasons', [])
            if args.debug_block_detection:
                print(json.dumps({
                    'phase': 'firecrawl',
                    'url': args.url,
                    'block_reasons': block_reasons,
                    'would_fallback': bool(block_reasons),
                }, ensure_ascii=False), file=sys.stderr)
            if block_reasons:
                errors.append(f'firecrawl: blocked-content-detected: {", ".join(block_reasons)}')
            else:
                result = firecrawl_result
        except Exception as exc:
            errors.append(f'firecrawl: {exc}')
            if debug_run_dir is not None:
                _write_json(debug_run_dir / 'firecrawl_error.json', {'url': args.url, 'error': str(exc)})
            if args.debug_block_detection:
                print(json.dumps({
                    'phase': 'firecrawl',
                    'url': args.url,
                    'error': str(exc),
                    'would_fallback': True,
                }, ensure_ascii=False), file=sys.stderr)

    if result is None:
        if args.debug_block_detection:
            print(json.dumps({
                'phase': 'fallback',
                'provider': 'stealth-browser-mcp',
                'url': args.url,
            }, ensure_ascii=False), file=sys.stderr)
        try:
            stealth_result = await fetch_via_stealth(
                args.url,
                args.stealth_timeout_ms,
                args.headless,
                proxy=args.proxy,
                session_dir=session_dir,
                timezone_id=args.timezone,
                extra_headers=extra_headers,
            )
            if debug_run_dir is not None:
                _write_json(debug_run_dir / 'stealth_result.json', stealth_result)
            result = stealth_result
        except Exception as exc:
            errors.append(f'stealth-browser-mcp: {exc}')
            if debug_run_dir is not None:
                _write_json(debug_run_dir / 'stealth_error.json', {'url': args.url, 'error': str(exc)})

    if result is None:
        payload = {'success': False, 'errors': errors, 'url': args.url}
        if debug_run_dir is not None:
            payload['debug_files_dir'] = str(debug_run_dir)
            _write_json(debug_run_dir / 'final_error.json', payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if errors:
        result['fallback_errors'] = errors
    if args.debug_block_detection or debug_run_dir is not None:
        result.setdefault('debug', {})
        if firecrawl_result is not None:
            result['debug']['firecrawl_block_reasons'] = firecrawl_result.get('debug', {}).get('firecrawl_block_reasons', [])
        result['debug']['fallback_triggered'] = bool(errors)
    if debug_run_dir is not None:
        result.setdefault('debug', {})
        result['debug']['debug_files_dir'] = str(debug_run_dir)
        _write_json(debug_run_dir / 'final_result.json', result)

    if args.json_only:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))

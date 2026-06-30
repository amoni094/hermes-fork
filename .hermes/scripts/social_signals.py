#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import http.cookiejar
import json
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0"
X_HOME = "https://x.com/home"
X_FEATURES = {
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "responsive_web_jetfuel_frame": False,
    "responsive_web_grok_share_attachment_enabled": False,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}


class FetchError(RuntimeError):
    pass


def detect_firefox_profile() -> Path:
    base = Path.home() / ".var/app/org.mozilla.firefox/config/mozilla/firefox"
    if not base.exists():
        raise FetchError(f"Firefox profile base not found: {base}")
    candidates = sorted(base.glob("*.default-release/cookies.sqlite"))
    if not candidates:
        candidates = sorted(base.glob("*/cookies.sqlite"))
    if not candidates:
        raise FetchError(f"No Firefox cookies.sqlite found under {base}")
    return candidates[0].parent


def load_cookies(profile: Path, domain_needles: list[str]) -> list[tuple[str, str, int, int, str, str]]:
    db = profile / "cookies.sqlite"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        rows = []
        for needle in domain_needles:
            rows.extend(
                cur.execute(
                    "select host, path, isSecure, expiry, name, value from moz_cookies where host like ?",
                    (f"%{needle}%",),
                ).fetchall()
            )
        return rows
    finally:
        conn.close()


def build_cookiejar(rows: list[tuple[str, str, int, int, str, str]]) -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    for host, path, is_secure, expiry, name, value in rows:
        jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain=host.lstrip('.'),
                domain_specified=True,
                domain_initial_dot=host.startswith('.'),
                path=path,
                path_specified=True,
                secure=bool(is_secure),
                expires=int(expiry) if expiry else None,
                discard=False,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
        )
    return jar


def build_opener(rows: list[tuple[str, str, int, int, str, str]]):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(build_cookiejar(rows)))
    opener.addheaders = [("User-Agent", UA)]
    return opener


def fetch_text(url: str, *, opener=None, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=headers or {})
    with (opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)) as resp:
        return resp.read().decode("utf-8", "ignore")


def fetch_json(url: str, *, opener=None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    return json.loads(fetch_text(url, opener=opener, headers=headers, timeout=timeout))


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def iso_utc(ts: float | int | None) -> str | None:
    if not ts:
        return None
    return dt.datetime.fromtimestamp(float(ts), tz=dt.timezone.utc).isoformat()


class RedditHotHTMLParser(HTMLParser):
    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit
        self.items: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None
        self._stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'shreddit-post' and 'post-title' in attrs:
            subreddit = attrs.get('subreddit-name') or ''
            subreddit_prefixed = attrs.get('subreddit-prefixed-name') or ''
            self._current = {
                'subreddit': subreddit or subreddit_prefixed.replace('r/', ''),
                'title': attrs.get('post-title', ''),
                'score': attrs.get('score'),
                'num_comments': attrs.get('comment-count'),
                'permalink': 'https://www.reddit.com' + (attrs.get('permalink') or ''),
                'url': attrs.get('content-href') or attrs.get('permalink') or '',
            }
        self._stack.append(tag)

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()
        if tag == 'shreddit-post' and self._current:
            self.items.append(self._current)
            self._current = None


def fetch_reddit_html_items(opener, limit: int) -> list[dict[str, Any]]:
    html_text = fetch_text('https://www.reddit.com/r/popular/', opener=opener, timeout=30)
    parser = RedditHotHTMLParser(limit)
    parser.feed(html_text)
    return parser.items[:limit]


def get_reddit_items(profile: Path, limit: int) -> dict[str, Any]:
    rows = load_cookies(profile, ['reddit'])
    opener = build_opener(rows)
    items: list[dict[str, Any]] = []
    error = None
    try:
        data = fetch_json('https://www.reddit.com/best.json?limit=%d&raw_json=1' % limit, opener=opener)
        for child in data.get('data', {}).get('children', []):
            post = child.get('data', {})
            items.append({
                'subreddit': post.get('subreddit'),
                'title': clean_text(post.get('title', '')),
                'author': post.get('author'),
                'score': post.get('score'),
                'num_comments': post.get('num_comments'),
                'created_at': iso_utc(post.get('created_utc')),
                'permalink': f"https://www.reddit.com{post.get('permalink', '')}",
                'url': post.get('url'),
            })
    except Exception as e:
        error = str(e)
        try:
            items = fetch_reddit_html_items(opener, limit)
        except Exception as html_error:
            error = f"json: {error}; html: {html_error}"
    report = {
        'signed_in_cookie_present': any(name == 'token_v2' for *_a, name, _b in rows),
        'cookie_count': len(rows),
        'items': items,
    }
    if error and not items:
        report['error'] = error
    return report


def x_bootstrap(profile: Path) -> tuple[dict[str, str], str, str]:
    rows = load_cookies(profile, ["x.com", "twitter"])
    cookies = {name: value for _host, _path, _sec, _exp, name, value in rows}
    opener = build_opener(rows)
    home_html = fetch_text(X_HOME, opener=opener)
    main_js_match = re.search(r'src="(https://abs\.twimg\.com/responsive-web/client-web/main\.[^"]+\.js)"', home_html)
    if not main_js_match:
        raise FetchError("Could not locate X main JS bundle from home page")
    main_js = fetch_text(main_js_match.group(1))
    bearer_match = re.search(r'Bearer (AAAAAAAAAAAAAAAAAAAAA[^"\\]+)', main_js)
    query_match = re.search(r'queryId:"([^"]+)",operationName:"HomeLatestTimeline"', main_js)
    if not bearer_match or not query_match:
        raise FetchError("Could not extract X bearer token or HomeLatestTimeline queryId")
    return cookies, bearer_match.group(1), query_match.group(1)


def walk_timeline_entries(obj: Any):
    if isinstance(obj, dict):
        if obj.get("__typename") == "TimelineTweet":
            yield obj
        for value in obj.values():
            yield from walk_timeline_entries(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_timeline_entries(item)


def extract_x_posts(payload: Any, limit: int) -> list[dict[str, Any]]:
    results = []
    seen = set()
    for item in walk_timeline_entries(payload):
        if item.get("promotedMetadata"):
            continue
        result = (((item.get("tweet_results") or {}).get("result")) or {})
        legacy = result.get("legacy") or {}
        core = ((result.get("core") or {}).get("user_results") or {}).get("result") or {}
        user_legacy = core.get("legacy") or {}
        user_core = core.get("core") or {}
        rest_id = result.get("rest_id") or legacy.get("id_str")
        text = clean_text(legacy.get("full_text", ""))
        if not rest_id or not text or rest_id in seen:
            continue
        seen.add(rest_id)
        screen_name = user_legacy.get("screen_name") or user_core.get("screen_name")
        author_name = user_legacy.get("name") or user_core.get("name")
        results.append(
            {
                "id": rest_id,
                "author_name": author_name,
                "screen_name": screen_name,
                "created_at": legacy.get("created_at"),
                "favorite_count": legacy.get("favorite_count"),
                "retweet_count": legacy.get("retweet_count"),
                "reply_count": legacy.get("reply_count"),
                "bookmark_count": legacy.get("bookmark_count"),
                "text": text,
                "url": f"https://x.com/{screen_name}/status/{rest_id}" if screen_name else None,
            }
        )
        if len(results) >= limit:
            break
    return results


def get_x_items(profile: Path, limit: int) -> dict[str, Any]:
    cookies, bearer, query_id = x_bootstrap(profile)
    headers = {
        "User-Agent": UA,
        "authorization": f"Bearer {bearer}",
        "x-csrf-token": cookies.get("ct0", ""),
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
    }
    variables = {
        "count": max(5, limit),
        "includePromotedContent": False,
        "latestControlAvailable": True,
        "requestContext": "launch",
        "seenTweetIds": [],
    }
    qs = urllib.parse.urlencode(
        {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(X_FEATURES, separators=(",", ":")),
        }
    )
    url = f"https://x.com/i/api/graphql/{query_id}/HomeLatestTimeline?{qs}"
    payload = fetch_json(url, headers=headers)
    items = extract_x_posts(payload, limit)
    return {
        "signed_in_cookie_present": "auth_token" in cookies and "ct0" in cookies,
        "cookie_count": len(cookies),
        "query_id": query_id,
        "items": items,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = []
    lines.append(f"Generated at: {report['generated_at']}")
    lines.append(f"Firefox profile: {report['firefox_profile']}")
    for section in ["x", "reddit"]:
        block = report[section]
        lines.append("")
        lines.append(section.upper())
        if "error" in block:
            lines.append(f"error: {block['error']}")
            continue
        lines.append(
            f"signed_in_cookie_present: {block.get('signed_in_cookie_present')}  items: {len(block.get('items', []))}"
        )
        for idx, item in enumerate(block.get("items", []), start=1):
            if section == "x":
                who = item.get("screen_name") or item.get("author_name") or "unknown"
                metrics = []
                for k in ["favorite_count", "retweet_count", "reply_count"]:
                    if item.get(k) is not None:
                        metrics.append(f"{k.replace('_count','')}={item[k]}")
                metric_str = f" [{' '.join(metrics)}]" if metrics else ""
                lines.append(f"{idx}. @{who}: {item.get('text','')}{metric_str}")
                if item.get("url"):
                    lines.append(f"   {item['url']}")
            else:
                lines.append(
                    f"{idx}. r/{item.get('subreddit')}: {item.get('title','')} [score={item.get('score')} comments={item.get('num_comments')}]"
                )
                if item.get("permalink"):
                    lines.append(f"   {item['permalink']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch X and Reddit signals from the local Firefox session")
    parser.add_argument("--limit", type=int, default=8, help="items per source")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    profile = detect_firefox_profile()
    report: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "firefox_profile": str(profile),
    }
    for name, fn in [("x", get_x_items), ("reddit", get_reddit_items)]:
        try:
            report[name] = fn(profile, args.limit)
        except Exception as e:
            report[name] = {"error": str(e)}

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

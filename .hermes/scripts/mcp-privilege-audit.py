#!/usr/bin/env python3
"""MCP least-privilege auditor (cs-mcp-overpriv / arXiv:2603.21641).

Reads configured MCP servers from ~/.hermes/config.yaml, enumerates tools
(via MCP tools/list when queryable, else local manifests/source), and flags
tools that violate a simple least-privilege ruleset:

  * filesystem: write/delete paths not constrained to /tmp or the workspace
  * network: arbitrary URL/host access with no domain allowlist
  * system: unrestricted shell / code execution with no command allowlist

Standalone usage:
  python3 /var/home/rainbow/.hermes/scripts/mcp-privilege-audit.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path.home() / ".hermes" / "config.yaml"
DEFAULT_WORKSPACE = Path.home()
DEFAULT_REPORT = Path("/tmp/mcp-privilege-report.txt")
TIMEOUT = 12

FILE_WRITE_RE = re.compile(
    r"(write|save|upload|unlink|rmdir|mkdir|delete|remove|patch|export|"
    r"to_file|file_upload|clone_element_to_file|clear_graph|truncate)",
    re.I,
)
FILE_READ_RE = re.compile(
    r"(read_file|read_resource|list_resources|list_clone_files|open_file)",
    re.I,
)
NETWORK_RE = re.compile(
    r"(http|https|url|fetch|request|navigate|browse|scrape|download|"
    r"webhook|socket|dns|proxy)",
    re.I,
)
SYSTEM_RE = re.compile(
    r"(shell|exec|subprocess|popen|command|terminal|os\.system|"
    r"execute_script|execute_python|execute_cdp|inject_and_execute|"
    r"hot_reload|spawn_browser|create_python_binding)",
    re.I,
)
ALLOWLIST_RE = re.compile(
    r"(allowlist|allowed_hosts|allowed_domains|allowed_paths|"
    r"allowed_commands|domain_allow|path_prefix|workspace_only)",
    re.I,
)
TMP_OR_WS_RE = re.compile(r"(/tmp|workspace|workdir|cwd)", re.I)


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("PyYAML required: python3 -m pip install pyyaml", file=sys.stderr)
        sys.exit(2)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def mcp_servers_from_config(cfg: dict) -> dict[str, dict]:
    for key in ("mcp_servers", "mcpServers", "mcp"):
        block = cfg.get(key)
        if isinstance(block, dict):
            return {str(k): (v if isinstance(v, dict) else {"raw": v}) for k, v in block.items()}
    return {}


class _PostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow 301/302/307/308 for POST (stdlib drops or converts these)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code not in (301, 302, 307, 308):
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        return urllib.request.Request(
            newurl,
            data=req.data,
            headers=dict(req.header_items()),
            origin_req_host=req.origin_req_host,
            unverifiable=True,
            method=req.get_method(),
        )


_OPENER = urllib.request.build_opener(_PostRedirectHandler)


def _jsonrpc(url: str, method: str, params: dict, session_id: str = "", rpc_id: int = 1) -> tuple[dict, str]:
    payload = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with _OPENER.open(req, timeout=TIMEOUT) as resp:
        new_sid = resp.headers.get("mcp-session-id", session_id) or session_id
        raw = resp.read().decode("utf-8", errors="replace")
    body: dict = {}
    for line in raw.splitlines():
        if line.startswith("data: "):
            try:
                body = json.loads(line[6:])
                break
            except json.JSONDecodeError:
                continue
    if not body:
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"parse_error": raw[:400]}
    return body, new_sid


def query_http_tools(url: str) -> tuple[list[dict], str]:
    """MCP initialize + tools/list over streamable HTTP. Returns (tools, note)."""
    try:
        init, sid = _jsonrpc(
            url,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-privilege-audit", "version": "1.0"},
            },
            rpc_id=0,
        )
        if init.get("error"):
            return [], f"initialize error: {init['error']}"
        try:
            _jsonrpc(url, "notifications/initialized", {}, session_id=sid, rpc_id=1)
        except Exception:
            pass
        listed, _ = _jsonrpc(url, "tools/list", {}, session_id=sid, rpc_id=2)
        result = listed.get("result") or {}
        tools = result.get("tools") or []
        if isinstance(tools, list) and tools:
            return tools, f"queried tools/list ({len(tools)} tools)"
        return [], f"tools/list empty or unexpected: {str(listed)[:240]}"
    except urllib.error.HTTPError as exc:
        loc = exc.headers.get("Location") if exc.headers else None
        if exc.code in (301, 302, 307, 308) and loc:
            return query_http_tools(loc)
        return [], f"HTTP query failed: {exc}"
    except urllib.error.URLError as exc:
        return [], f"HTTP query failed: {exc}"
    except Exception as exc:
        return [], f"HTTP query failed: {exc}"


def _schema_text(tool: dict) -> str:
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    try:
        return json.dumps(schema, default=str)
    except TypeError:
        return str(schema)


def tools_from_manifest_or_source(server: dict) -> tuple[list[dict], str]:
    """Best-effort local discovery for stdio servers."""
    command = str(server.get("command") or "")
    args = server.get("args") or []
    workdir = server.get("workdir") or ""
    candidates: list[Path] = []
    if workdir:
        candidates.append(Path(workdir))
    if command:
        candidates.append(Path(command).parent)
    for a in args:
        p = Path(str(a))
        if p.suffix in {".py", ".js", ".mjs", ".ts"}:
            candidates.append(p.parent)
            candidates.append(p)

    seen: dict[str, dict] = {}
    notes: list[str] = []

    for base in candidates:
        if not base.exists():
            continue
        for name in (
            "mcp.json",
            "server.json",
            "tools.json",
            "manifest.json",
            ".mcp.json",
        ):
            man = base / name if base.is_dir() else base.parent / name
            if man.is_file():
                try:
                    data = json.loads(man.read_text())
                except Exception:
                    continue
                tools = data.get("tools") if isinstance(data, dict) else None
                if isinstance(tools, list):
                    for t in tools:
                        if isinstance(t, dict) and t.get("name"):
                            seen[str(t["name"])] = t
                    notes.append(f"manifest {man}")

        roots = [base] if base.is_dir() else [base.parent]
        for root in roots:
            if not root.is_dir():
                continue
            for py in list(root.glob("*.py"))[:40]:
                try:
                    text = py.read_text(errors="replace")
                except OSError:
                    continue
                # FastMCP / decorator style: @mcp.tool() then def name(
                for m in re.finditer(
                    r"@(?:mcp|server)\.tool\([^)]*\)\s*(?:async\s+)?def\s+([A-Za-z_][\w]*)",
                    text,
                ):
                    n = m.group(1)
                    seen.setdefault(n, {"name": n, "description": f"source:{py.name}"})
                # mcp.tool(name="...")
                for m in re.finditer(r'name\s*=\s*["\']([A-Za-z_][\w-]*)["\']', text):
                    n = m.group(1)
                    if n in {"Browser", "True", "False"}:
                        continue
                # SECTION_TOOLS["x"].append("tool")
                for m in re.finditer(
                    r'SECTION_TOOLS\[[^\]]+\]\.append\(\s*["\']([^"\']+)["\']',
                    text,
                ):
                    n = m.group(1)
                    seen.setdefault(n, {"name": n, "description": f"section:{py.name}"})
                # async def likely_tool(
                if py.name == "server.py":
                    for m in re.finditer(r"^(?:async\s+)?def\s+([A-Za-z_][\w]*)\(", text, re.M):
                        n = m.group(1)
                        if n.startswith("_") or n in {
                            "main",
                            "parse_bool_env",
                            "is_section_enabled",
                            "create_http_auth_provider",
                            "get_http_auth_token",
                        }:
                            continue
                        seen.setdefault(n, {"name": n, "description": f"def:{py.name}"})

    if seen:
        notes.append(f"source scan ({len(seen)} names)")
        return list(seen.values()), "; ".join(notes) or "source scan"
    return [], "no queryable tools/list and no local manifest/source tools found"


def classify_tool(tool: dict, workspace: Path) -> list[dict]:
    """Return a list of privilege findings for one tool."""
    name = str(tool.get("name") or "")
    desc = str(tool.get("description") or "")
    schema = _schema_text(tool)
    blob = f"{name}\n{desc}\n{schema}"
    findings: list[dict] = []

    has_allowlist = bool(ALLOWLIST_RE.search(blob))
    constrained_fs = bool(TMP_OR_WS_RE.search(blob)) and has_allowlist

    if FILE_WRITE_RE.search(name) or FILE_WRITE_RE.search(desc):
        if not constrained_fs and not re.search(
            r"(/tmp|workspace[_-]?only|allowed_paths)", blob, re.I
        ):
            findings.append(
                {
                    "class": "filesystem",
                    "severity": "high",
                    "reason": (
                        "Write/delete-capable tool with no path constraint to "
                        f"/tmp or workspace ({workspace})"
                    ),
                }
            )
    elif FILE_READ_RE.search(name) and not TMP_OR_WS_RE.search(blob):
        findings.append(
            {
                "class": "filesystem",
                "severity": "medium",
                "reason": "Read tool is not scoped to /tmp or workspace",
            }
        )

    if NETWORK_RE.search(name) or NETWORK_RE.search(desc) or re.search(
        r'"url"|["\']uri["\']', schema, re.I
    ):
        if not has_allowlist:
            findings.append(
                {
                    "class": "network",
                    "severity": "high",
                    "reason": "Network/URL access without a domain allowlist",
                }
            )

    if SYSTEM_RE.search(name) or SYSTEM_RE.search(desc):
        if not has_allowlist:
            findings.append(
                {
                    "class": "system",
                    "severity": "high",
                    "reason": "Shell/code execution without an explicit command allowlist",
                }
            )

    return findings


def fmt_server_header(name: str, spec: dict) -> str:
    enabled = spec.get("enabled", True)
    kind = "http" if spec.get("url") else "stdio" if spec.get("command") else "unknown"
    target = spec.get("url") or spec.get("command") or "?"
    return f"## {name}  [{kind}]  enabled={enabled}\n    target: {target}"


def audit(config_path: Path, workspace: Path, report_path: Path) -> int:
    cfg = load_yaml(config_path)
    servers = mcp_servers_from_config(cfg)
    lines: list[str] = []
    lines.append("MCP least-privilege audit")
    lines.append(f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"config: {config_path}")
    lines.append(f"workspace: {workspace}")
    lines.append("ruleset: filesystem writes outside /tmp|workspace; "
                 "network without domain allowlist; system/shell without command allowlist")
    lines.append(f"servers_configured: {len(servers)}")
    lines.append("")

    total_tools = 0
    total_flags = 0
    flagged_servers = 0

    if not servers:
        lines.append("No mcp_servers / mcpServers / mcp key found in config.")
    else:
        for sname, spec in servers.items():
            tools: list[dict] = []
            source_note = ""
            url = spec.get("url")
            if url:
                tools, source_note = query_http_tools(str(url))
            if not tools:
                extra, extra_note = tools_from_manifest_or_source(spec)
                if extra:
                    tools = extra
                    source_note = (source_note + "; " if source_note else "") + extra_note
                elif not source_note:
                    source_note = extra_note

            lines.append(fmt_server_header(sname, spec))
            lines.append(f"    discovery: {source_note or 'none'}")
            lines.append(f"    tools: {len(tools)}")
            server_flags = 0
            for tool in tools:
                total_tools += 1
                findings = classify_tool(tool, workspace)
                tname = tool.get("name", "?")
                tdesc = (tool.get("description") or "").replace("\n", " ")[:160]
                if findings:
                    server_flags += 1
                    total_flags += len(findings)
                    lines.append(f"    FLAG  {tname}")
                    if tdesc:
                        lines.append(f"          desc: {tdesc}")
                    for f in findings:
                        lines.append(f"          [{f['severity']}/{f['class']}] {f['reason']}")
                else:
                    lines.append(f"    ok    {tname}" + (f"  — {tdesc}" if tdesc else ""))
            if server_flags:
                flagged_servers += 1
            lines.append("")

    lines.append("## Summary")
    lines.append(f"servers: {len(servers)}")
    lines.append(f"servers_with_flags: {flagged_servers}")
    lines.append(f"tools_enumerated: {total_tools}")
    lines.append(f"findings: {total_flags}")
    lines.append("")
    lines.append("Remediation (high-level): constrain write paths to workspace+/tmp; "
                 "add domain allowlists on URL tools; wrap shell/code exec in an explicit allowlist. "
                 "Do not disable required local MCP servers from this report alone.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {report_path} ({total_tools} tools, {total_flags} findings)")
    return 0


def main(argv: list[str]) -> int:
    config = Path(os.environ.get("HERMES_CONFIG", DEFAULT_CONFIG))
    workspace = Path(os.environ.get("HERMES_WORKSPACE", DEFAULT_WORKSPACE))
    report = Path(os.environ.get("MCP_PRIVILEGE_REPORT", DEFAULT_REPORT))
    if len(argv) >= 2 and argv[1] in {"-h", "--help"}:
        print(__doc__)
        return 0
    return audit(config, workspace, report)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""
router-login.py — Get a TP-Link AX55 stok in one shot.

Usage:
    python3 router-login.py [--vault-handle <handle>]

Returns JSON on stdout: {"stok": "...", "tab_id": "...", "serviceAdapter": true}
On failure, exits non-zero with error on stderr.

The stok is valid for the current browser session only (tied to a camofox tab).
On success, camofox is left running and the tab is left open so the caller can
reuse them for API calls. On failure the tab is closed and, if this script
started camofox, camofox is stopped.

Dependencies: camofox on localhost:9377 (started automatically if not up).
"""

import argparse
import atexit
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

CAMOFOX_PORT = 9377
CAMOFOX_DIR = Path.home() / "camofox-browser"
SERVER_JS = CAMOFOX_DIR / "server.js"
SERVER_JS_BAK = CAMOFOX_DIR / "server.js.bak"
ROUTER_URL = "https://192.168.0.1/webpages/index.html"
VAULT_HANDLE = "vault_8f686f61c712"  # router credential (origin https://192.168.0.1)
USER_ID = "hermes"
SESSION_KEY = "router-login"
CHUNK_INDEX_RE = re.compile(r"index-[A-Za-z0-9]+\.js")
CHUNK_STORE_RE = re.compile(r"update-store-[A-Za-z0-9]+\.js")
CONTEXT_OPTIONS_NEEDLE = "const contextOptions = {"
CONTEXT_OPTIONS_PATCH = "const contextOptions = {\n        ignoreHTTPSErrors: true,"
POLL_INTERVAL_S = 0.5
POLL_TIMEOUT_S = 20.0
HEALTH_WAIT_S = 10.0

_camofox_started = False
_camofox_proc = None
_patched_server_js = False
_original_server_js = None  # bytes captured before our patch
_cleanup_registered = False
_in_cleanup = False


class CamofoxHTTPError(RuntimeError):
    def __init__(self, status, body, method, path):
        self.status = status
        self.body = body
        self.method = method
        self.path = path
        super().__init__(f"camofox {method} {path} HTTP {status}: {_brief(body)}")


def _brief(body):
    if isinstance(body, dict):
        err = body.get("error")
        if err is not None:
            return str(err)
        return json.dumps(body, default=str)[:300]
    text = body if isinstance(body, str) else repr(body)
    return text[:300]


def _ssl_error_body(body):
    if not isinstance(body, dict):
        return False
    if body.get("code") == "ssl_error":
        return True
    err = str(body.get("error") or "")
    return "ssl_error" in err or "SEC_ERROR" in err or "SSL_ERROR" in err or "MOZILLA_PKIX_ERROR" in err


def _curl(method, path, body=None, timeout=15):
    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        f"--max-time={timeout}", "-X", method,
        "-H", "Content-Type: application/json",
        f"http://localhost:{CAMOFOX_PORT}{path}",
    ]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    stdout = r.stdout or ""
    if r.returncode != 0 and not stdout.strip():
        err = (r.stderr or "").strip() or f"curl exit {r.returncode}"
        raise RuntimeError(f"camofox {method} {path} failed: {err}")
    if "\n" not in stdout:
        raise RuntimeError(f"camofox {method} {path} empty/malformed response")
    raw, status_s = stdout.rsplit("\n", 1)
    try:
        status = int(status_s.strip())
    except ValueError:
        raise RuntimeError(f"camofox {method} {path} bad status trailer: {status_s!r}")
    if status == 0:
        err = (r.stderr or "").strip() or "connection failed"
        raise RuntimeError(f"camofox {method} {path} failed: {err}")
    parsed = None
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
    return status, parsed


def camofox(method, path, body=None, timeout=15):
    status, parsed = _curl(method, path, body=body, timeout=timeout)
    if not (200 <= status < 300):
        raise CamofoxHTTPError(status, parsed, method, path)
    return parsed


def eval_js(tab_id, js, timeout=20):
    result = camofox(
        "POST", f"/tabs/{tab_id}/evaluate",
        {"expression": js, "userId": USER_ID},
        timeout=timeout,
    )
    if not isinstance(result, dict):
        raise RuntimeError(f"JS eval unexpected response: {result!r}")
    if result.get("ok") is True:
        return result.get("result")
    if result.get("ok") is False or "error" in result:
        raise RuntimeError(f"JS eval error: {result.get('error', result)}")
    raise RuntimeError(f"JS eval missing envelope: {result!r}")


def _health_ok():
    try:
        status, data = _curl("GET", "/health", timeout=2)
    except (RuntimeError, OSError, json.JSONDecodeError):
        return False
    if not (200 <= status < 300):
        return False
    return isinstance(data, dict) and data.get("ok") is True


def _with_server_js_lock():
    SERVER_JS.parent.mkdir(parents=True, exist_ok=True)
    if not SERVER_JS.exists():
        raise RuntimeError(f"camofox server.js not found: {SERVER_JS}")
    fd = os.open(str(SERVER_JS), os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _write_fd(fd, data: bytes):
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    os.write(fd, data)
    os.fsync(fd)


def _restore_bak_locked(fd):
    """Restore server.js from .bak if a previous run was SIGKILL'd mid-patch."""
    if not SERVER_JS_BAK.exists():
        return
    original = SERVER_JS_BAK.read_bytes()
    _write_fd(fd, original)
    try:
        SERVER_JS_BAK.unlink()
    except OSError:
        pass


def _patch_server_js():
    """Patch ignoreHTTPSErrors into contextOptions. No-op if already present."""
    global _patched_server_js, _original_server_js
    fd = _with_server_js_lock()
    try:
        _restore_bak_locked(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        original = os.read(fd, os.path.getsize(SERVER_JS) + 1)
        if b"ignoreHTTPSErrors" in original:
            return False
        text = original.decode()
        if CONTEXT_OPTIONS_NEEDLE in text:
            patched = text.replace(CONTEXT_OPTIONS_NEEDLE, CONTEXT_OPTIONS_PATCH, 1)
        else:
            patched = re.sub(
                r"(contextOptions\s*=\s*\{)",
                r"\1\n        ignoreHTTPSErrors: true,",
                text,
                count=1,
            )
        if "ignoreHTTPSErrors" not in patched:
            raise RuntimeError("failed to patch ignoreHTTPSErrors into server.js")
        patched_bytes = patched.encode()
        SERVER_JS_BAK.write_bytes(original)
        _write_fd(fd, patched_bytes)
        _original_server_js = original
        _patched_server_js = True
        return True
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def revert_camofox_patch():
    """Restore server.js from saved original bytes / .bak if we patched it."""
    global _patched_server_js, _original_server_js
    if not _patched_server_js and not SERVER_JS_BAK.exists() and _original_server_js is None:
        return
    if not SERVER_JS.exists():
        return
    fd = _with_server_js_lock()
    try:
        original = _original_server_js
        if original is None and SERVER_JS_BAK.exists():
            original = SERVER_JS_BAK.read_bytes()
        if original is None:
            return
        _write_fd(fd, original)
        _patched_server_js = False
        _original_server_js = None
        try:
            SERVER_JS_BAK.unlink()
        except OSError:
            pass
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _on_signal(signum, _frame):
    _cleanup_resources()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def _register_cleanup():
    global _cleanup_registered
    if _cleanup_registered:
        return
    atexit.register(_cleanup_resources)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    _cleanup_registered = True


def _cleanup_resources():
    global _in_cleanup
    if _in_cleanup:
        return
    _in_cleanup = True
    try:
        revert_camofox_patch()
    except Exception:
        pass


def _pid_on_port(port):
    r = subprocess.run(
        ["fuser", f"{port}/tcp"],
        capture_output=True, text=True,
    )
    text = (r.stdout or "") + " " + (r.stderr or "")
    pids = [int(p) for p in re.findall(r"\d+", text)]
    return pids


def stop_camofox():
    global _camofox_proc, _camofox_started
    if _camofox_proc is not None and _camofox_proc.poll() is None:
        _camofox_proc.terminate()
        try:
            _camofox_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _camofox_proc.kill()
            _camofox_proc.wait(timeout=3)
        _camofox_proc = None
    else:
        subprocess.run(
            ["fuser", "-k", "-TERM", f"{CAMOFOX_PORT}/tcp"],
            capture_output=True, text=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not _pid_on_port(CAMOFOX_PORT):
                break
            time.sleep(0.2)
        if _pid_on_port(CAMOFOX_PORT):
            subprocess.run(
                ["fuser", "-k", "-KILL", f"{CAMOFOX_PORT}/tcp"],
                capture_output=True, text=True,
            )
            time.sleep(0.3)
    _camofox_started = False


def _start_camofox_process():
    global _camofox_started, _camofox_proc
    _camofox_proc = subprocess.Popen(
        ["node", "server.js"],
        cwd=CAMOFOX_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _camofox_started = True
    deadline = time.monotonic() + HEALTH_WAIT_S
    while time.monotonic() < deadline:
        if _health_ok():
            return
        if _camofox_proc.poll() is not None:
            raise RuntimeError(f"camofox exited early with code {_camofox_proc.returncode}")
        time.sleep(POLL_INTERVAL_S)
    raise RuntimeError("camofox did not start in time")


def ensure_camofox(*, force_restart=False):
    _register_cleanup()
    if force_restart:
        stop_camofox()
        _patch_server_js()
        _start_camofox_process()
        return
    if _health_ok():
        # Recover a sticky on-disk patch from a previous SIGKILL without
        # touching the already-running process.
        fd = _with_server_js_lock()
        try:
            _restore_bak_locked(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        return
    _patch_server_js()
    _start_camofox_process()


def close_tab(tab_id):
    if not tab_id:
        return
    try:
        camofox("DELETE", f"/tabs/{tab_id}?userId={USER_ID}", timeout=10)
    except (CamofoxHTTPError, RuntimeError, OSError):
        pass


def _create_tab():
    try:
        tab = camofox("POST", "/tabs", {
            "userId": USER_ID,
            "sessionKey": SESSION_KEY,
            "url": ROUTER_URL,
        }, timeout=45)
    except CamofoxHTTPError as e:
        if isinstance(e.body, dict) and (e.body.get("error") or e.body.get("code")):
            raise RuntimeError(e.body.get("error") or e.body.get("code")) from e
        raise
    if not isinstance(tab, dict):
        raise RuntimeError(f"tab create unexpected response: {tab!r}")
    if tab.get("error"):
        raise RuntimeError(str(tab.get("error")))
    tab_id = tab.get("tabId")
    if not tab_id:
        raise RuntimeError(f"tab create missing tabId: {tab}")
    if tab.get("navigationOk", True) is False:
        raise RuntimeError(
            f"tab navigation failed httpStatus={tab.get('httpStatus')} url={tab.get('url')}"
        )
    return tab_id


def _create_tab_with_ssl_retry():
    """Create a tab; if SSL fails against an already-running camofox, patch+restart once."""
    try:
        return _create_tab()
    except (CamofoxHTTPError, RuntimeError) as e:
        body = e.body if isinstance(e, CamofoxHTTPError) else None
        msg = str(e)
        is_ssl = _ssl_error_body(body) or "ssl_error" in msg or "SSL certificate error" in msg
        if not is_ssl:
            raise
        if _camofox_started:
            raise RuntimeError(f"SSL error after camofox start/patch: {msg}") from e
        print("ssl_error on existing camofox; patching ignoreHTTPSErrors and restarting", file=sys.stderr)
        ensure_camofox(force_restart=True)
        return _create_tab()


def _discover_chunks(tab_id):
    chunks_js = """
    Array.from(document.querySelectorAll('script[src]'))
        .map(s => s.src.replace(location.origin, ''))
    """
    deadline = time.monotonic() + POLL_TIMEOUT_S
    found = []
    index_chunk = None
    store_chunk = None
    while True:
        scripts_raw = eval_js(tab_id, chunks_js)
        if isinstance(scripts_raw, list):
            found = scripts_raw
        elif isinstance(scripts_raw, str):
            try:
                loaded = json.loads(scripts_raw)
                found = loaded if isinstance(loaded, list) else [scripts_raw]
            except json.JSONDecodeError:
                found = [scripts_raw] if scripts_raw else []
        else:
            found = []
        srcs = [s for s in found if isinstance(s, str)]
        index_chunk = next((s for s in srcs if CHUNK_INDEX_RE.search(s)), None)
        store_chunk = next((s for s in srcs if CHUNK_STORE_RE.search(s)), None)
        if index_chunk and store_chunk:
            return index_chunk, store_chunk, srcs
        if time.monotonic() >= deadline:
            break
        time.sleep(POLL_INTERVAL_S)
    raise RuntimeError(
        "chunk discovery timed out waiting for index-* / update-store-* script[src]; "
        f"found: {found}"
    )


def _import_modules(tab_id, index_chunk, store_chunk):
    import_js = (
        "(async function() {\n"
        f"    await import({json.dumps(index_chunk)});\n"
        f"    const m = await import({json.dumps(store_chunk)});\n"
        "    window._sa  = m.s;\n"
        "    window._EM  = m.E;\n"
        "    window._RSA = m.R;\n"
        "    return 'ok';\n"
        "})()"
    )
    result = eval_js(tab_id, import_js, timeout=30)
    if result != "ok":
        raise RuntimeError(f"Module import failed: {result}")


def _resolve_password(vault_handle):
    hermes_fork = Path.home() / ".hermes/hermes-fork"
    if str(hermes_fork) not in sys.path:
        sys.path.insert(0, str(hermes_fork))
    from agent.vault_store import VaultError, VaultStore

    vault_dirs = [
        Path.home() / ".hermes/profiles/fork/vault",
        Path.home() / ".hermes/vault",
    ]
    last_err_type = None
    for vault_dir in vault_dirs:
        try:
            store = VaultStore(base_dir=vault_dir)
            secret = store.resolve_secret(vault_handle)
            pw = secret.get("password", "") if isinstance(secret, dict) else ""
            if pw:
                return pw
            print(f"vault empty password ({vault_dir.name})", file=sys.stderr)
        except VaultError:
            last_err_type = "VaultError"
            print(f"vault {last_err_type}", file=sys.stderr)
            continue
        except (OSError, FileNotFoundError, json.JSONDecodeError, ImportError,
                KeyError, ValueError, TypeError) as e:
            last_err_type = type(e).__name__
            print(f"vault {last_err_type}", file=sys.stderr)
            continue
    extra = f" ({last_err_type})" if last_err_type else ""
    raise RuntimeError(f"Could not resolve password for handle {vault_handle}{extra}")


def _login(tab_id, pw):
    set_js = None
    login_js = None
    try:
        set_js = f"(window.__pw = {json.dumps(pw)}, 'ok')"
        del pw
        set_result = eval_js(tab_id, set_js)
        del set_js
        set_js = None
        if set_result != "ok":
            raise RuntimeError(f"failed to stage password: {set_result}")

        login_js = """
        (async function() {
            const authData = await window._sa.read('/login?form=auth');
            const keysData = await window._sa.read('/login?form=keys');
            const [authN, authE] = authData.key;
            window._EM.init('', authData.seq, authN, authE);
            const encPw = window._RSA.encrypt(window.__pw, ...keysData.password);
            const resp = await window._sa.write('/login?form=login',
                {password: encPw, operation: 'login', confirm: true},
                {preventSuccess: true, preventError: true, withAesKey: true}
            );
            return resp;
        })()
        """
        resp = eval_js(tab_id, login_js, timeout=20)
        del login_js
        login_js = None
        return resp
    finally:
        if set_js is not None:
            del set_js
        if login_js is not None:
            del login_js
        try:
            eval_js(tab_id, "(window.__pw = null, delete window.__pw, 'ok')")
        except (CamofoxHTTPError, RuntimeError, OSError):
            pass


def get_stok(vault_handle=VAULT_HANDLE):
    ensure_camofox()
    tab_id = None
    try:
        tab_id = _create_tab_with_ssl_retry()
        print(f"Tab: {tab_id}", file=sys.stderr)

        index_chunk, store_chunk, scripts = _discover_chunks(tab_id)
        print(f"Scripts: {scripts}", file=sys.stderr)
        print(f"Chunks: index={index_chunk} store={store_chunk}", file=sys.stderr)

        _import_modules(tab_id, index_chunk, store_chunk)

        pw = _resolve_password(vault_handle)
        resp = _login(tab_id, pw)

        if isinstance(resp, str):
            try:
                resp = json.loads(resp)
            except json.JSONDecodeError:
                pass
        if not isinstance(resp, dict) or "stok" not in resp:
            raise RuntimeError(f"Login failed: {resp}")

        stok = resp["stok"]
        print(json.dumps({"stok": stok, "tab_id": tab_id, "serviceAdapter": True}))
        print(f"stok={stok}", file=sys.stderr)
        return stok, tab_id
    except Exception:
        close_tab(tab_id)
        if _camofox_started:
            stop_camofox()
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault-handle", default=VAULT_HANDLE)
    args = ap.parse_args()

    try:
        get_stok(args.vault_handle)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

"""E4 elite-discrimination task prompts, fixtures, and AND checkers."""
from __future__ import annotations

import re
from pathlib import Path

E4_TAIL_N = 30

AUTHZ_PROMPT = (
    "The HTTP client at {WORK}/proj sometimes returns another user's /api/me payload. "
    "Recreate files if missing. Identify the root cause and prove a two-session leak. "
    "Do not patch.\n"
    "\n"
    "mkdir -p {WORK}/proj && cat > {WORK}/proj/README.md << 'EOF'\n"
    "Process-local response cache. URL uniquely identifies the resource.\n"
    "Authorization is attached per Session. Do not log raw tokens.\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/session.py << 'EOF'\n"
    "class Session:\n"
    "    def __init__(self, user, token):\n"
    "        self.user = user\n"
    "        self.token = token\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/cache.py << 'EOF'\n"
    "class ResponseCache:\n"
    "    def __init__(self):\n"
    "        self._store = {}\n"
    "    def key(self, method, url):\n"
    "        return f\"{method}:{url}\"\n"
    "    def get(self, method, url):\n"
    "        return self._store.get(self.key(method, url))\n"
    "    def put(self, method, url, resp):\n"
    "        self._store[self.key(method, url)] = resp\n"
    "CACHE = ResponseCache()\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/client.py << 'EOF'\n"
    "from cache import CACHE\n"
    "\n"
    "def http_do(method, url, headers):\n"
    "    raise NotImplementedError(\"network\")\n"
    "\n"
    "def fetch(session, method, url, use_cache=True):\n"
    "    if use_cache and method == \"GET\":\n"
    "        hit = CACHE.get(method, url)\n"
    "        if hit is not None:\n"
    "            return hit\n"
    "    headers = {}\n"
    "    if session.token:\n"
    "        headers[\"Authorization\"] = f\"Bearer {session.token}\"\n"
    "    resp = http_do(method, url, headers)\n"
    "    if use_cache and method == \"GET\" and getattr(resp, \"status\", None) == 200:\n"
    "        CACHE.put(method, url, resp)\n"
    "    return resp\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/debug.py << 'EOF'\n"
    "def format_auth(session):\n"
    "    tok = session.token or \"\"\n"
    "    return \"Bearer \" + (tok[:2] + \"***\" if tok else \"\")\n"
    "EOF\n"
    "\n"
    "Write {WORK}/proj/leak.txt with the three-step leak sequence "
    "(one step per line: A_puts, B_hits, B_sees_A). "
    "Reply ROOT=... WITNESS=... KEY_IS=... KEY_SHOULD=..."
)

PATH_PROMPT = (
    "Two guards at {WORK}/proj. Decide if they are extensionally equal on POSIX.\n"
    "\n"
    "mkdir -p {WORK}/proj && cat > {WORK}/proj/v1_guard.py << 'EOF'\n"
    "import os\n"
    "def is_inside(child: str, parent: str) -> bool:\n"
    "    c = os.path.realpath(child)\n"
    "    p = os.path.realpath(parent)\n"
    "    if c == p:\n"
    "        return True\n"
    "    if not p.endswith(os.sep):\n"
    "        p = p + os.sep\n"
    "    return c.startswith(p)\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/v2_guard.py << 'EOF'\n"
    "import os\n"
    "def is_inside(child: str, parent: str) -> bool:\n"
    "    # abspath is the modern realpath; skip extra resolve\n"
    "    c = os.path.abspath(child)\n"
    "    p = os.path.abspath(parent)\n"
    "    return c.startswith(p)\n"
    "EOF\n"
    "\n"
    "Assume for the link witness that /var/app/link is a symlink whose realpath "
    "is outside /var/app (e.g. /etc/passwd). Do not run as root; reason about "
    "the functions. If they differ, report ALL independent difference classes "
    "you can witness. If equivalent, reply EQUIVALENT=YES. If they differ, you "
    "MUST reply with these exact tokens on separate lines:\n"
    "EQUIVALENT=NO\n"
    "PREFIX_V1=<True|False>\n"
    "PREFIX_V2=<True|False>\n"
    "LINK_V1=<True|False>\n"
    "LINK_V2=<True|False>\n"
)

INVOICE_PROMPT = (
    "{WORK}/proj/test_invoice.py fails: expected 9000, got 8100. NOTES.md lists "
    "H1-H3. Recreate files if missing. Eliminate every listed hypothesis that "
    "cannot produce 8100. Prove the survivor with integer arithmetic. Do not patch.\n"
    "\n"
    "mkdir -p {WORK}/proj && cat > {WORK}/proj/NOTES.md << 'EOF'\n"
    "H1: IEEE float in add_tax -- 10000 * 0.9 might become 8999\n"
    "H2: legacy old_sum off-by-one contaminates the total\n"
    "H3: coupon percent integer-truncates via // 100, dropping ~100 cents\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/float_tax.py << 'EOF'\n"
    "def add_tax(cents, rate=0.1):\n"
    "    return int(cents * (1 + rate))\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/legacy.py << 'EOF'\n"
    "def old_sum(n):\n"
    "    t = 0\n"
    "    for i in range(n):\n"
    "        t += i\n"
    "    return t\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/lines.py << 'EOF'\n"
    "def line_total(qty, unit_cents, coupon):\n"
    "    raw = qty * unit_cents\n"
    "    if coupon and coupon[\"type\"] == \"percent\":\n"
    "        raw = raw * (100 - coupon[\"value\"]) // 100\n"
    "    return raw\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/invoice.py << 'EOF'\n"
    "from lines import line_total\n"
    "def invoice_total(lines, coupon):\n"
    "    s = 0\n"
    "    for ln in lines:\n"
    "        s += line_total(ln[\"qty\"], ln[\"unit_cents\"], coupon)\n"
    "    if coupon and coupon[\"type\"] == \"percent\":\n"
    "        s = s * (100 - coupon[\"value\"]) // 100\n"
    "    return s\n"
    "EOF\n"
    "\n"
    "cat > {WORK}/proj/test_invoice.py << 'EOF'\n"
    "from invoice import invoice_total\n"
    "def test_ten_percent_off_one_line():\n"
    "    lines = [{\"qty\": 1, \"unit_cents\": 10000}]\n"
    "    coupon = {\"type\": \"percent\", \"value\": 10}\n"
    "    assert invoice_total(lines, coupon) == 9000\n"
    "EOF\n"
    "\n"
    "Reply ROOT=... ARITH=... ELIM_H1=... ELIM_H2=... ELIM_H3=... "
    "and name both source files that apply the coupon."
)

E4_TASKS = {
    "err_authz_cache": AUTHZ_PROMPT,
    "err_path_semantic_diff": PATH_PROMPT,
    "err_hypothesis_invoice": INVOICE_PROMPT,
}

E4_TAGS = {
    "err_authz_cache": ["adversarial", "reasoning"],
    "err_path_semantic_diff": ["reasoning"],
    "err_hypothesis_invoice": ["reasoning"],
}

AUTHZ_README = (
    "Process-local response cache. URL uniquely identifies the resource.\n"
    "Authorization is attached per Session. Do not log raw tokens.\n"
)
AUTHZ_SESSION = (
    "class Session:\n"
    "    def __init__(self, user, token):\n"
    "        self.user = user\n"
    "        self.token = token\n"
)
AUTHZ_CACHE = (
    "class ResponseCache:\n"
    "    def __init__(self):\n"
    "        self._store = {}\n"
    "    def key(self, method, url):\n"
    "        return f\"{method}:{url}\"\n"
    "    def get(self, method, url):\n"
    "        return self._store.get(self.key(method, url))\n"
    "    def put(self, method, url, resp):\n"
    "        self._store[self.key(method, url)] = resp\n"
    "CACHE = ResponseCache()\n"
)
AUTHZ_CLIENT = (
    "from cache import CACHE\n"
    "\n"
    "def http_do(method, url, headers):\n"
    "    raise NotImplementedError(\"network\")\n"
    "\n"
    "def fetch(session, method, url, use_cache=True):\n"
    "    if use_cache and method == \"GET\":\n"
    "        hit = CACHE.get(method, url)\n"
    "        if hit is not None:\n"
    "            return hit\n"
    "    headers = {}\n"
    "    if session.token:\n"
    "        headers[\"Authorization\"] = f\"Bearer {session.token}\"\n"
    "    resp = http_do(method, url, headers)\n"
    "    if use_cache and method == \"GET\" and getattr(resp, \"status\", None) == 200:\n"
    "        CACHE.put(method, url, resp)\n"
    "    return resp\n"
)
AUTHZ_DEBUG = (
    "def format_auth(session):\n"
    "    tok = session.token or \"\"\n"
    "    return \"Bearer \" + (tok[:2] + \"***\" if tok else \"\")\n"
)

V1_GUARD = (
    "import os\n"
    "def is_inside(child: str, parent: str) -> bool:\n"
    "    c = os.path.realpath(child)\n"
    "    p = os.path.realpath(parent)\n"
    "    if c == p:\n"
    "        return True\n"
    "    if not p.endswith(os.sep):\n"
    "        p = p + os.sep\n"
    "    return c.startswith(p)\n"
)
V2_GUARD = (
    "import os\n"
    "def is_inside(child: str, parent: str) -> bool:\n"
    "    # abspath is the modern realpath; skip extra resolve\n"
    "    c = os.path.abspath(child)\n"
    "    p = os.path.abspath(parent)\n"
    "    return c.startswith(p)\n"
)

INVOICE_NOTES = (
    "H1: IEEE float in add_tax -- 10000 * 0.9 might become 8999\n"
    "H2: legacy old_sum off-by-one contaminates the total\n"
    "H3: coupon percent integer-truncates via // 100, dropping ~100 cents\n"
)
INVOICE_FLOAT_TAX = (
    "def add_tax(cents, rate=0.1):\n"
    "    return int(cents * (1 + rate))\n"
)
INVOICE_LEGACY = (
    "def old_sum(n):\n"
    "    t = 0\n"
    "    for i in range(n):\n"
    "        t += i\n"
    "    return t\n"
)
INVOICE_LINES = (
    "def line_total(qty, unit_cents, coupon):\n"
    "    raw = qty * unit_cents\n"
    "    if coupon and coupon[\"type\"] == \"percent\":\n"
    "        raw = raw * (100 - coupon[\"value\"]) // 100\n"
    "    return raw\n"
)
INVOICE_PY = (
    "from lines import line_total\n"
    "def invoice_total(lines, coupon):\n"
    "    s = 0\n"
    "    for ln in lines:\n"
    "        s += line_total(ln[\"qty\"], ln[\"unit_cents\"], coupon)\n"
    "    if coupon and coupon[\"type\"] == \"percent\":\n"
    "        s = s * (100 - coupon[\"value\"]) // 100\n"
    "    return s\n"
)
INVOICE_TEST = (
    "from invoice import invoice_total\n"
    "def test_ten_percent_off_one_line():\n"
    "    lines = [{\"qty\": 1, \"unit_cents\": 10000}]\n"
    "    coupon = {\"type\": \"percent\", \"value\": 10}\n"
    "    assert invoice_total(lines, coupon) == 9000\n"
)


def seed_e4(proj: Path, task: str | None) -> None:
    """Overwrite colliding sandbox files only for the running E4 task."""
    if task == "err_authz_cache":
        (proj / "README.md").write_text(AUTHZ_README, encoding="utf-8")
        (proj / "session.py").write_text(AUTHZ_SESSION, encoding="utf-8")
        (proj / "cache.py").write_text(AUTHZ_CACHE, encoding="utf-8")
        (proj / "client.py").write_text(AUTHZ_CLIENT, encoding="utf-8")
        (proj / "debug.py").write_text(AUTHZ_DEBUG, encoding="utf-8")
    elif task == "err_path_semantic_diff":
        (proj / "v1_guard.py").write_text(V1_GUARD, encoding="utf-8")
        (proj / "v2_guard.py").write_text(V2_GUARD, encoding="utf-8")
    elif task == "err_hypothesis_invoice":
        (proj / "NOTES.md").write_text(INVOICE_NOTES, encoding="utf-8")
        (proj / "float_tax.py").write_text(INVOICE_FLOAT_TAX, encoding="utf-8")
        (proj / "legacy.py").write_text(INVOICE_LEGACY, encoding="utf-8")
        (proj / "lines.py").write_text(INVOICE_LINES, encoding="utf-8")
        (proj / "invoice.py").write_text(INVOICE_PY, encoding="utf-8")
        (proj / "test_invoice.py").write_text(INVOICE_TEST, encoding="utf-8")


def reply_tail(text: str, n: int = E4_TAIL_N) -> str:
    return "\n".join((text or "").splitlines()[-n:])


def _full_reply(t: str, w: Path) -> str:
    p = w / "_abeval_reply.txt"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return t or ""


def _leak_has(lines: list[str], tok: str) -> bool:
    return any(ln == tok or ln.startswith(tok + ":") or ln.startswith(tok + " ") for ln in lines)


def authz_ok(t: str, w: Path) -> bool:
    hay = _full_reply(t, w) or t or ""
    leak = w / "proj" / "leak.txt"
    if not leak.exists():
        return False
    lines = [ln.strip() for ln in leak.read_text(encoding="utf-8", errors="replace").splitlines()]
    if not _leak_has(lines, "A_puts"):
        return False
    if not _leak_has(lines, "B_hits"):
        return False
    if not _leak_has(lines, "B_sees_A"):
        return False
    if re.search(r"ROOT=token_log\b", hay, re.IGNORECASE):
        return False
    if re.search(r"ROOT=cache_post\b", hay, re.IGNORECASE):
        return False
    if re.search(r"ROOT=shared_session\b", hay, re.IGNORECASE):
        return False
    if "ROOT=cache_key_omits_auth" in hay:
        return True
    root_m = re.search(r"ROOT=([^\n]+)", hay, re.IGNORECASE)
    if not root_m:
        return False
    root_val = root_m.group(1).lower()
    # Must identify cache-keying omits auth — all three concepts required in ROOT= value
    has_cache = "cache" in root_val
    has_key_concept = any(tok in root_val for tok in ("key", "omit", "without", "miss", "exclud"))
    has_auth = any(tok in root_val for tok in ("auth", "token", "session", "bearer"))
    if has_cache and has_key_concept and has_auth:
        return True
    # Also accept KEY_IS= identifying the missing dimension
    key_is_m = re.search(r"KEY_IS=([^\n]+)", hay, re.IGNORECASE)
    if key_is_m:
        ki = key_is_m.group(1).lower()
        if any(tok in ki for tok in ("auth", "token", "session", "bearer")):
            # The model correctly identified that KEY_IS is missing auth
            # but this alone is not sufficient without ROOT identification
            if has_cache:
                return True
    return False


def path_ok(t: str, w: Path) -> bool:
    hay = (_full_reply(t, w) or t or "").lower()
    if "equivalent=no" not in hay:
        return False
    if "equivalent=yes" in hay:
        return False
    return (
        "prefix_v1=false" in hay
        and "prefix_v2=true" in hay
        and "link_v1=false" in hay
        and "link_v2=true" in hay
    )


def invoice_ok(t: str, w: Path) -> bool:
    hay = _full_reply(t, w) or t or ""
    root_m = re.search(r"ROOT=([^\n]+)", hay, re.IGNORECASE)
    root = (root_m.group(1) if root_m else "").lower()
    if "coupon" not in root:
        return False
    if not any(tok in root for tok in ("double", "twice")):
        return False
    if any(bad in root for bad in ("float_tax", "off_by_one", "truncation")):
        return False
    arith_m = re.search(r"ARITH=([^\n]+)", hay, re.IGNORECASE)
    arith = arith_m.group(1) if arith_m else ""
    if "8100" not in arith or not any(tok in arith for tok in ("0.9", "90", "0.81", "twice", "double")):
        return False
    if not re.search(r"ELIM_H1=", hay, re.IGNORECASE):
        return False
    if not re.search(r"ELIM_H2=", hay, re.IGNORECASE):
        return False
    if not re.search(r"ELIM_H3=", hay, re.IGNORECASE):
        return False
    if "lines.py" not in hay:
        return False
    if "invoice.py" not in hay:
        return False
    return True


E4_SUCCESS = {
    "err_authz_cache": authz_ok,
    "err_path_semantic_diff": path_ok,
    "err_hypothesis_invoice": invoice_ok,
}

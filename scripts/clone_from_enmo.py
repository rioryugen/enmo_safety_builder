"""
Enmo Safety — clone the Enmo harness into the namespaced safety harness.

Copies the canonical Enmo harness (../enmo) into ../enmo_safety and namespaces
every component so both harnesses can be installed side by side in one
workspace without adapter collisions:

    skills/<n>/            -> skills/safety-<n>/
    agents/<n>.md          -> agents/safety-<n>.md
    commands/enmo-<n>.md   -> commands/safety-<n>.md
    .enmo/                 -> .enmo_safety/
    ENMO_* env vars        -> ENMO_SAFETY_*

Only Enmo-derived files are written. Files that exist only in enmo_safety (the
safety-specific skills, agents, rules, harness artifacts) are never touched, so
the tool can be re-run after Enmo changes. Files listed in KEEP_LOCAL are
safety-owned after the first clone and are not overwritten on re-runs.

Flags:
    --source <dir>   Enmo canonical root (default: ../enmo)
    --dest <dir>     safety canonical root (default: ../enmo_safety)
    --dry-run        print the plan, write nothing

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version: namespaced clone of skills, agents, commands, install
          dir, env vars, and brand; never touches safety-only files.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = BUILDER_ROOT.parent

PREFIX = "safety-"
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".example", ""}
# Enmo's own project memory is history of Enmo, not of the safety harness.
SKIP_REL = re.compile(r"^memory/(project|user|session)/(?!\.gitkeep$).+")
# Safety-owned after first clone: re-runs must not clobber safety edits.
KEEP_LOCAL = {"README.md", "CHANGELOG.md", "VERSION", "AGENTS.md", "CLAUDE.md",
              "docs/CATALOG.md", "scripts/enmo_lib.py", "scripts/install.py",
              "scripts/doctor.py", "tests/test_integrity.py", "hooks/hooks.json",
              "hooks/gate.py", "hooks/benchmark.py"}


def names(source: Path) -> tuple[list, list, list]:
    skills = sorted(p.name for p in (source / "skills").iterdir() if p.is_dir())
    agents = sorted(p.stem for p in (source / "agents").glob("*.md"))
    commands = sorted(p.stem[len("enmo-"):] for p in (source / "commands").glob("enmo-*.md"))
    return skills, agents, commands


def dest_rel(rel: str, skills: list, agents: list) -> str:
    parts = rel.split("/")
    if parts[0] == "skills" and len(parts) > 1 and parts[1] in skills:
        parts[1] = PREFIX + parts[1]
    elif parts[0] == "agents" and len(parts) == 2 and parts[1][:-3] in agents:
        parts[1] = PREFIX + parts[1]
    elif parts[0] == "commands" and len(parts) == 2 and parts[1].startswith("enmo-"):
        parts[1] = PREFIX + parts[1][len("enmo-"):]
    return "/".join(parts)


def build_rewriter(skills: list, agents: list, commands: list):
    # Longest names first so `harness-analyzer` wins over `harness-analyze`.
    component = sorted(set(skills) | set(agents), key=len, reverse=True)
    comp_re = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, component)) + r")(?![\w-])")
    cmd_re = re.compile(r"(?<![\w-])enmo-(" + "|".join(map(re.escape, commands)) + r")(?![\w-])")
    subs = [
        (re.compile(r"enmo_builder"), "enmo_safety_builder"),
        (re.compile(r"\.enmo(?![\w-])"), ".enmo_safety"),
        (re.compile(r"enmo-manifest\.json"), "enmo-safety-manifest.json"),
        (re.compile(r"\bENMO_(?!SAFETY_)"), "ENMO_SAFETY_"),
        (re.compile(r"enmo-harness"), "enmo-safety-harness"),
        (re.compile(r"\bEnmo(?! Safety)\b"), "Enmo Safety"),
    ]

    def rewrite(text: str, suffix: str) -> str:
        text = cmd_re.sub(lambda m: PREFIX + m.group(1), text)
        if suffix == ".md":
            # Only prose and frontmatter name components; JSON snapshots hold upstream data.
            text = comp_re.sub(lambda m: PREFIX + m.group(1), text)
        elif suffix == ".py":
            text = text.replace('"enmo-"', f'"{PREFIX}"')
        for pat, rep in subs:
            text = pat.sub(rep, text)
        return text

    return rewrite


def plan(source: Path, dest: Path) -> list:
    skills, agents, commands = names(source)
    rewrite = build_rewriter(skills, agents, commands)
    out = []
    for src in sorted(source.rglob("*")):
        if not src.is_file() or any(p in SKIP_DIRS for p in src.relative_to(source).parts):
            continue
        rel = src.relative_to(source).as_posix()
        if SKIP_REL.match(rel) or src.suffix in (".pyc",):
            continue
        new_rel = dest_rel(rel, skills, agents)
        target = dest / new_rel
        if new_rel in KEEP_LOCAL and target.exists():
            continue
        out.append((src, target, rewrite))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone Enmo into the namespaced safety harness")
    parser.add_argument("--source", default=str(WORKSPACE / "enmo"))
    parser.add_argument("--dest", default=str(WORKSPACE / "enmo_safety"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source, dest = Path(args.source).resolve(), Path(args.dest).resolve()
    if not (source / "AGENTS.md").is_file():
        print(f"ERROR: {source} is not an Enmo canonical root")
        return 1

    items = plan(source, dest)
    for src, target, rewrite in items:
        rel = target.relative_to(dest).as_posix()
        if args.dry_run:
            print(f"  {src.relative_to(source).as_posix()} -> {rel}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_SUFFIXES or src.name in ("LICENSE", "VERSION", ".gitignore"):
            try:
                text = src.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src, target)
                continue
            target.write_text(rewrite(text, src.suffix), encoding="utf-8", newline="\n")
        else:
            shutil.copy2(src, target)
    print(f"{'DRY RUN: ' if args.dry_run else ''}{len(items)} file(s) cloned into {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

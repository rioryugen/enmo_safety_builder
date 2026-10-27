"""
Enmo Harness — builder release tool.

Publishes a GitHub release for every version of a repo. Each version is tagged
at the commit that set its VERSION, and released with a zip of that version's
repo content (git archive). One release per version. The zip is the repo's main
content as it was at that version — the canonical harness for enmo, the builder
staging area for enmo_builder.

Flags:
    --list                show each version, its commit, tag, and release state
    --release <version>   tag + release one version
    --all                 tag + release every version (skips what already exists)
    --push                push the tags to the remote after creating them
    --dry-run            show what would be done, change nothing
    --repo <dir>         git repo root (default: the builder this script lives in)

A "version" is any value the VERSION file has held. The release commit is the most
recent commit whose VERSION content equals that value, so the zip produced from it
contains exactly the repo as it stood at that version. Releases are created with
the `gh` CLI (the logged-in account); tags are created with git. Nothing is
clobbered: an existing tag is reused, an existing release is skipped.

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version: per-version git tags + GitHub releases, each carrying
          the repo content at that version as a zip (git archive). --list,
          --release, --all, --push, --dry-run, --repo.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_repo(start: Path) -> Path:
    """Walk up from *start* to the git repo root (has a .git folder)."""
    cur = Path(start).resolve()
    while True:
        if (cur / ".git").is_dir():
            return cur
        parent = cur.parent
        if parent == cur:
            return start.resolve()
        cur = parent


def git(repo: Path, *args) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo),
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def gh(repo: Path, *args) -> tuple:
    r = subprocess.run(["gh", *args], cwd=str(repo),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def version_commits(repo: Path) -> dict:
    """Map each version to the most recent commit that introduced it.

    A version is recognized two ways: the value the VERSION file held at that
    commit, and a v<version> marker in the commit subject. The VERSION-file
    mapping wins when both agree; the subject marker catches versions whose
    commit predates the VERSION file (e.g. the builder's first release).
    """
    out = {}
    log = git(repo, "log", "--format=%H\x01%s\x01", "--", "VERSION")
    for line in log.splitlines():
        parts = line.split("\x01")
        c = parts[0]
        v = git(repo, "show", f"{c}:VERSION").strip()
        if v and v not in out:
            out[v] = c
    # Subject markers for versions with no VERSION-file commit.
    full_log = git(repo, "log", "--format=%H\x01%s")
    for line in full_log.splitlines():
        parts = line.split("\x01")
        c, subj = parts[0], parts[1] if len(parts) > 1 else ""
        m = re.search(r"v(\d+\.\d+\.\d+)", subj)
        if m and m.group(1) not in out:
            out[m.group(1)] = c
    return out


def current_version(repo: Path) -> str:
    p = repo / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def changelog_section(repo: Path, version: str) -> str:
    p = repo / "CHANGELOG.md"
    if not p.is_file():
        return f"{repo.name} {version}"
    text = p.read_text(encoding="utf-8")
    m = re.search(rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)",
                  text, re.S)
    return m.group(0).strip() if m else f"{repo.name} {version}"


def tag_exists(repo: Path, tag: str) -> bool:
    return bool(git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}"))


def release_exists(repo: Path, tag: str) -> bool:
    code, _ = gh(repo, "release", "view", tag)
    return code == 0


def make_zip(repo: Path, commit: str, version: str, out_dir: Path):
    zip_path = out_dir / f"{repo.name}-{version}.zip"
    r = subprocess.run(["git", "archive", "--format=zip",
                        f"--prefix={repo.name}-{version}/", commit,
                        "-o", str(zip_path)], cwd=str(repo))
    return zip_path if r.returncode == 0 and zip_path.is_file() else None


def release_one(repo: Path, version: str, commit: str, dry: bool,
               push: bool, tmp: Path) -> str:
    tag = f"v{version}"
    lines = []
    if dry:
        lines.append(f"  {version} @ {commit[:7]}: tag {tag}, zip, release")
        return "\n".join(lines)
    if not tag_exists(repo, tag):
        subprocess.run(["git", "tag", tag, commit], cwd=str(repo), check=True)
        lines.append(f"  tagged {tag} @ {commit[:7]}")
    # gh needs the tag on the remote before it can attach a release to it.
    if push:
        subprocess.run(["git", "push", "origin", tag], cwd=str(repo))
        lines.append(f"  pushed tag {tag}")
    # Archive from the tag so the zip is exactly the repo content the tag marks.
    zip_path = make_zip(repo, tag, version, tmp)
    notes = changelog_section(repo, version)
    notes_file = tmp / f"{version}-notes.md"
    notes_file.write_text(notes, encoding="utf-8")
    if release_exists(repo, tag):
        lines.append(f"  {tag}: release already exists — skipped")
    else:
        code, out = gh(repo, "release", "create", tag, str(zip_path),
                       "--title", f"{repo.name} {version}",
                       "--notes-file", str(notes_file))
        lines.append(f"  {tag}: release created" if code == 0
                     else f"  {tag}: release FAILED — {out}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enmo builder release tool")
    parser.add_argument("--list", action="store_true",
                        help="show each version, commit, tag, release state")
    parser.add_argument("--release", metavar="VERSION",
                        help="tag + release one version")
    parser.add_argument("--all", action="store_true",
                        help="tag + release every version")
    parser.add_argument("--push", action="store_true",
                        help="push tags to the remote")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be done, change nothing")
    parser.add_argument("--repo", default=None, help="git repo root")
    args = parser.parse_args()

    repo = Path(args.repo) if args.repo else find_repo(Path(__file__).resolve().parent)
    versions = version_commits(repo)
    cur = current_version(repo)

    if args.list:
        print(f"{repo.name} · current VERSION {cur} · {len(versions)} versioned commits")
        for v, c in sorted(versions.items()):
            tag = f"v{v}"
            t = "tagged" if tag_exists(repo, tag) else "no tag"
            r = "released" if release_exists(repo, tag) else "no release"
            print(f"  {v} @ {c[:7]} · {t} · {r}")
        return 0

    tmp = Path(tempfile.mkdtemp())
    try:
        if args.release:
            v = args.release
            if v not in versions:
                print(f"version {v} has no VERSION commit in {repo.name}")
                return 1
            print(release_one(repo, v, versions[v], args.dry_run, args.push, tmp))
        elif args.all:
            for v, c in sorted(versions.items()):
                print(release_one(repo, v, c, args.dry_run, args.push, tmp))
        else:
            print("nothing to do — use --list, --release <version>, or --all")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

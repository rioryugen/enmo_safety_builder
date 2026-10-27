"""
Enmo Safety Harness — builder.

Stages the upstream git sources that Enmo Safety adapts from (the parent Enmo
harness, safety benchmarks, and integrations such as the humanizer skill). The
builder clones the registered repos into sources/ (or a per-source `path`, e.g.
integrations/humanizer), reports their state, and refreshes them.

Flags:
    --list                show the registered sources
    --status              clone state of each source
    --clone [name]        shallow-clone a source (all if no name)
    --refresh [name]      re-fetch the latest upstream commit (all if no name)
    --add <name> <url>    register a new source (--ref, --role optional)
    --check [name]        compare upstream HEAD to the scan ledger; report drift
    --scan [name]         refresh + record upstream commit, scan date, Enmo build
    --record [name]       record current clone state without fetching
    --update [name]       auto-sync: clone missing, scan every source that moved
    --ledger              show the scan ledger
    --note <name> <text>  record what Enmo added/adapted from a source (date + build)
    --root <dir>          builder root (default: this repo)

The scan ledger (scan-ledger.json) is the durable record of what was taken from
each source and when: upstream commit, scan date + time, the Enmo build current at
the scan, and the list of changes Enmo added from that source (each with its date
and Enmo build). sources.json records ref_date — the date + time each reference was
registered. --check answers "has upstream moved since the last scan" so the next
session knows whether Enmo needs updating — it never re-adapts content that is
already current. --update is the one-command auto-sync for "update in the builder":
it clones any missing source, scans every source whose upstream has moved (or was
never scanned), and reports what changed. --note appends a change record; --ledger
shows the full history.

Author:   m03 (Intel)
Revision: 1.4

Revision History:
    1.0 — Initial version: source registry, shallow clone, status, refresh, add.
    1.1 — Scan ledger: --check (upstream drift vs last scan), --scan (refresh +
          record commit/date/Enmo build), --record, --ledger.
    1.2 — Change tracking: --note appends what Enmo added/adapted from a source
          (date + Enmo build + text); --ledger shows the change history; --scan /
          --record preserve the change list across re-scans.
    1.3 — Auto-sync + timestamps: --update clones missing sources and scans every
          source whose upstream moved (one command for "update in the builder");
          sources.json records ref_date (date + time registered); scans/records
          store scan_time; --list shows ref_date.
    1.4 — Safety builder: build read from ../enmo_safety/VERSION; a source may set
          `path` to clone outside sources/ (integrations/); registry keys other
          than `sources` (e.g. `datasets`) survive --add.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

REGISTRY = "sources.json"
SOURCES_DIR = "sources"
LEDGER = "scan-ledger.json"


def find_root(start: Path) -> Path:
    """Walk up from *start* to the builder root (has sources.json)."""
    cur = Path(start).resolve()
    while True:
        if (cur / REGISTRY).is_file():
            return cur
        parent = cur.parent
        if parent == cur:
            return start.resolve()
        cur = parent


def load_registry(root: Path) -> dict:
    path = root / REGISTRY
    if not path.is_file():
        return {"sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sources": []}


def save_registry(root: Path, data: dict) -> None:
    path = root / REGISTRY
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def enmo_build(root: Path) -> str:
    """The safety harness build recorded in ../enmo_safety/VERSION."""
    ver = root.parent / "enmo_safety" / "VERSION"
    if ver.is_file():
        return ver.read_text(encoding="utf-8").strip()
    return "?"


def load_ledger(root: Path) -> dict:
    path = root / LEDGER
    if not path.is_file():
        return {"enmo_build": enmo_build(root), "sources": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"enmo_build": enmo_build(root), "sources": {}}


def save_ledger(root: Path, data: dict) -> None:
    path = root / LEDGER
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def today() -> str:
    return datetime.date.today().isoformat()


def now() -> str:
    """Current local date + time, ISO, no microseconds."""
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def remote_head(url: str, ref: str | None) -> str | None:
    """Upstream HEAD commit for *ref* (short sha). Needs network. None on failure."""
    args = ["ls-remote", url] + ([ref] if ref else [])
    code, out, _ = git(args, Path("."))
    if code != 0 or not out:
        return None
    # ls-remote prints "<sha>\trefs/heads/<ref>"; take the first line's sha.
    first = out.splitlines()[0]
    return first.split()[0][:7] if first.split() else None


def local_head(d: Path) -> str:
    _, head, _ = git(["rev-parse", "--short", "HEAD"], d)
    return head


def git(args: list, cwd: Path) -> tuple:
    """Run a git command in *cwd*. Returns (returncode, stdout, stderr)."""
    r = subprocess.run(["git"] + args, cwd=str(cwd),
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def source_dir(root: Path, name: str) -> Path:
    for s in load_registry(root).get("sources", []):
        if s.get("name") == name and s.get("path"):
            return root / s["path"]
    return root / SOURCES_DIR / name


def is_cloned(d: Path) -> bool:
    return (d / ".git").is_dir()


def cmd_list(root: Path) -> int:
    srcs = load_registry(root).get("sources", [])
    if not srcs:
        print("No sources registered. Add one with --add <name> <url>.")
        return 0
    print(f"{len(srcs)} registered source(s):")
    for s in srcs:
        ref = s.get("ref", "default")
        ref_date = s.get("ref_date", "?")
        role = s.get("role", "")
        print(f"  {s['name']}  {s['url']}  ref={ref}  ref_date={ref_date}  {role}")
    return 0


def cmd_status(root: Path) -> int:
    srcs = load_registry(root).get("sources", [])
    if not srcs:
        print("No sources registered.")
        return 0
    print(f"{len(srcs)} registered source(s):")
    for s in srcs:
        d = source_dir(root, s["name"])
        if not is_cloned(d):
            print(f"  {s['name']}: NOT CLONED")
            continue
        _, head, _ = git(["rev-parse", "--short", "HEAD"], d)
        _, branch, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], d)
        print(f"  {s['name']}: cloned @ {head} ({branch})")
    return 0


def cmd_clone(root: Path, name: str | None) -> int:
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    rc = 0
    for s in targets:
        d = source_dir(root, s["name"])
        if is_cloned(d):
            print(f"  {s['name']}: already cloned, skipping")
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "--depth", "1"]
        if s.get("ref"):
            args += ["--branch", s["ref"]]
        args += [s["url"], str(d)]
        code, _, err = git(args, root)
        if code == 0:
            print(f"  {s['name']}: cloned")
        else:
            print(f"  {s['name']}: FAILED — {err}")
            rc = 1
    return rc


def cmd_refresh(root: Path, name: str | None) -> int:
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    rc = 0
    for s in targets:
        d = source_dir(root, s["name"])
        if not is_cloned(d):
            print(f"  {s['name']}: not cloned, run --clone first")
            rc = 1
            continue
        ref = s.get("ref")
        fetch = ["fetch", "--depth", "1", "origin"] + ([ref] if ref else [])
        code, _, err = git(fetch, d)
        if code != 0:
            print(f"  {s['name']}: fetch FAILED — {err}")
            rc = 1
            continue
        target = f"origin/{ref}" if ref else "FETCH_HEAD"
        code2, _, err2 = git(["reset", "--hard", target], d)
        if code2 == 0:
            _, head, _ = git(["rev-parse", "--short", "HEAD"], d)
            print(f"  {s['name']}: refreshed @ {head}")
        else:
            print(f"  {s['name']}: reset FAILED — {err2}")
            rc = 1
    return rc


def cmd_add(root: Path, name: str, url: str, ref: str | None, role: str) -> int:
    srcs = load_registry(root).get("sources", [])
    for s in srcs:
        if s["name"] == name:
            print(f"Source '{name}' already registered. Edit sources.json to change it.")
            return 1
    entry = {"name": name, "url": url}
    if ref:
        entry["ref"] = ref
    entry["ref_date"] = now()
    if role:
        entry["role"] = role
    srcs.append(entry)
    registry = load_registry(root)
    registry["sources"] = srcs
    save_registry(root, registry)
    print(f"Registered {name} -> {url} (ref_date {entry['ref_date']}). "
          f"Clone with --clone {name}.")
    return 0


def cmd_ledger(root: Path) -> int:
    ledger = load_ledger(root)
    entries = ledger.get("sources", {})
    build = ledger.get("enmo_build", "?")
    print(f"Scan ledger — Enmo build {build}")
    if not entries:
        print("  No scans recorded. Run --scan to record upstream state.")
        return 0
    for name, e in sorted(entries.items()):
        scan_time = e.get("scan_time", "")
        print(f"  {name}: scanned {e.get('scan_date', '?')} {scan_time} "
              f"@ upstream {e.get('upstream_commit', '?')} "
              f"(Enmo build {e.get('enmo_build', '?')})")
        for c in e.get("changes", []):
            print(f"    {c.get('date', '?')} (Enmo {c.get('enmo_build', '?')}): "
                  f"{c.get('added', '')}")
    return 0


def cmd_note(root: Path, name: str, text: str) -> int:
    """Append what Enmo added/adapted from a source to the ledger (date + build)."""
    srcs = load_registry(root).get("sources", [])
    if not any(s["name"] == name for s in srcs):
        print(f"No source named '{name}'. Register it with --add first.")
        return 1
    ledger = load_ledger(root)
    entries = ledger.setdefault("sources", {})
    build = enmo_build(root)
    ledger["enmo_build"] = build
    e = entries.setdefault(name, {})
    changes = e.setdefault("changes", [])
    changes.append({"date": today(), "enmo_build": build, "added": text})
    save_ledger(root, ledger)
    print(f"Noted change for {name} (Enmo build {build}): {text}")
    return 0


def cmd_check(root: Path, name: str | None) -> int:
    """Compare upstream HEAD to the scan ledger. Report what moved since last scan."""
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    ledger = load_ledger(root)
    entries = ledger.get("sources", {})
    rc = 0
    drift = []
    for s in targets:
        head = remote_head(s["url"], s.get("ref"))
        if head is None:
            print(f"  {s['name']}: upstream unreachable (offline?) — cannot check")
            rc = 1
            continue
        e = entries.get(s["name"])
        if not e:
            print(f"  {s['name']}: NEVER SCANNED — upstream @ {head}. Run --scan.")
            drift.append(s["name"])
            continue
        recorded = e.get("upstream_commit", "")
        if head == recorded:
            print(f"  {s['name']}: current (last scan {e.get('scan_date', '?')}, "
                  f"@ {recorded}, Enmo build {e.get('enmo_build', '?')})")
        else:
            print(f"  {s['name']}: DRIFT — upstream {recorded} -> {head} "
                  f"(last scan {e.get('scan_date', '?')}, "
                  f"Enmo build {e.get('enmo_build', '?')}). Run --scan.")
            drift.append(s["name"])
    if drift:
        print(f"\n{len(drift)} source(s) need a scan: {', '.join(drift)}")
    return rc


def cmd_scan(root: Path, name: str | None) -> int:
    """Refresh the clone and record upstream commit, scan date, and Enmo build."""
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    ledger = load_ledger(root)
    entries = ledger.setdefault("sources", {})
    build = enmo_build(root)
    ledger["enmo_build"] = build
    rc = 0
    for s in targets:
        d = source_dir(root, s["name"])
        if not is_cloned(d):
            print(f"  {s['name']}: not cloned, run --clone first")
            rc = 1
            continue
        ref = s.get("ref")
        fetch = ["fetch", "--depth", "1", "origin"] + ([ref] if ref else [])
        code, _, err = git(fetch, d)
        if code != 0:
            print(f"  {s['name']}: fetch FAILED — {err}")
            rc = 1
            continue
        target = f"origin/{ref}" if ref else "FETCH_HEAD"
        code2, _, err2 = git(["reset", "--hard", target], d)
        if code2 != 0:
            print(f"  {s['name']}: reset FAILED — {err2}")
            rc = 1
            continue
        head = local_head(d)
        prev = entries.get(s["name"], {})
        entries[s["name"]] = {
            "upstream_commit": head,
            "local_commit": head,
            "scan_date": today(),
            "scan_time": now(),
            "enmo_build": build,
            "ref": ref,
            "changes": prev.get("changes", []),
        }
        print(f"  {s['name']}: scanned @ {head} (Enmo build {build})")
    save_ledger(root, ledger)
    print(f"Ledger written to {LEDGER}.")
    return rc


def cmd_record(root: Path, name: str | None) -> int:
    """Record current clone state without fetching (offline / no-drift snapshot)."""
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    ledger = load_ledger(root)
    entries = ledger.setdefault("sources", {})
    build = enmo_build(root)
    ledger["enmo_build"] = build
    rc = 0
    for s in targets:
        d = source_dir(root, s["name"])
        if not is_cloned(d):
            print(f"  {s['name']}: not cloned, run --clone first")
            rc = 1
            continue
        head = local_head(d)
        prev = entries.get(s["name"], {})
        entries[s["name"]] = {
            "upstream_commit": head,
            "local_commit": head,
            "scan_date": today(),
            "scan_time": now(),
            "enmo_build": build,
            "ref": s.get("ref"),
            "changes": prev.get("changes", []),
        }
        print(f"  {s['name']}: recorded @ {head} (Enmo build {build})")
    save_ledger(root, ledger)
    print(f"Ledger written to {LEDGER}.")
    return rc


def cmd_update(root: Path, name: str | None) -> int:
    """Auto-sync the builder: clone any missing source, scan every source whose
    upstream has moved (or was never scanned), and report what changed. This is
    the one-command answer to 'update in the builder'."""
    srcs = load_registry(root).get("sources", [])
    targets = [s for s in srcs if name is None or s["name"] == name]
    if not targets:
        print(f"No source named '{name}'.")
        return 1
    ledger = load_ledger(root)
    entries = ledger.setdefault("sources", {})
    build = enmo_build(root)
    ledger["enmo_build"] = build
    rc = 0
    updated = []
    for s in targets:
        d = source_dir(root, s["name"])
        if not is_cloned(d):
            print(f"  {s['name']}: cloning...")
            d.parent.mkdir(parents=True, exist_ok=True)
            cargs = ["clone", "--depth", "1"]
            if s.get("ref"):
                cargs += ["--branch", s["ref"]]
            cargs += [s["url"], str(d)]
            code, _, err = git(cargs, root)
            if code != 0:
                print(f"  {s['name']}: clone FAILED — {err}")
                rc = 1
                continue
        ref = s.get("ref")
        fetch = ["fetch", "--depth", "1", "origin"] + ([ref] if ref else [])
        code, _, err = git(fetch, d)
        if code != 0:
            print(f"  {s['name']}: fetch FAILED — {err}")
            rc = 1
            continue
        target = f"origin/{ref}" if ref else "FETCH_HEAD"
        code2, _, err2 = git(["reset", "--hard", target], d)
        if code2 != 0:
            print(f"  {s['name']}: reset FAILED — {err2}")
            rc = 1
            continue
        head = local_head(d)
        e = entries.get(s["name"], {})
        recorded = e.get("upstream_commit", "")
        if head == recorded:
            print(f"  {s['name']}: current (last scan {e.get('scan_date', '?')} "
                  f"@ {recorded}) — no change")
            continue
        entries[s["name"]] = {
            "upstream_commit": head,
            "local_commit": head,
            "scan_date": today(),
            "scan_time": now(),
            "enmo_build": build,
            "ref": ref,
            "changes": e.get("changes", []),
        }
        updated.append(s["name"])
        if recorded:
            print(f"  {s['name']}: UPDATED {recorded} -> {head} (Enmo build {build})")
        else:
            print(f"  {s['name']}: NEW scan @ {head} (Enmo build {build})")
    save_ledger(root, ledger)
    if updated:
        print(f"\n{len(updated)} source(s) updated: {', '.join(updated)}.")
        print("For each, read the upstream file, name the gap, adapt ONE capability, "
              "then record with --note.")
    else:
        print("\nAll sources current — nothing to update.")
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enmo builder — stage upstream git sources Enmo adapts from")
    parser.add_argument("--list", action="store_true", help="list registered sources")
    parser.add_argument("--status", action="store_true", help="clone state of each source")
    parser.add_argument("--clone", nargs="?", const="__all__", default=None,
                        help="clone a source (name) or all (no name)")
    parser.add_argument("--refresh", nargs="?", const="__all__", default=None,
                        help="refresh a source (name) or all (no name)")
    parser.add_argument("--check", nargs="?", const="__all__", default=None,
                        help="check upstream drift vs the scan ledger (name) or all")
    parser.add_argument("--scan", nargs="?", const="__all__", default=None,
                        help="refresh + record scan (name) or all (no name)")
    parser.add_argument("--record", nargs="?", const="__all__", default=None,
                        help="record current clone state without fetching (name) or all")
    parser.add_argument("--update", nargs="?", const="__all__", default=None,
                        help="auto-sync: clone missing + scan every source that moved")
    parser.add_argument("--ledger", action="store_true", help="show the scan ledger")
    parser.add_argument("--note", nargs=2, metavar=("NAME", "TEXT"),
                        help="record what Enmo added/adapted from a source")
    parser.add_argument("--add", nargs=2, metavar=("NAME", "URL"),
                        help="register a new source")
    parser.add_argument("--ref", default=None, help="ref/branch for --add")
    parser.add_argument("--role", default="", help="role note for --add")
    parser.add_argument("--root", default=None, help="builder root")
    args = parser.parse_args()

    root = Path(args.root) if args.root else find_root(Path(__file__).resolve().parent)

    if args.list:
        return cmd_list(root)
    if args.status:
        return cmd_status(root)
    if args.ledger:
        return cmd_ledger(root)
    if args.note:
        return cmd_note(root, args.note[0], args.note[1])
    if args.check is not None:
        return cmd_check(root, None if args.check == "__all__" else args.check)
    if args.scan is not None:
        return cmd_scan(root, None if args.scan == "__all__" else args.scan)
    if args.record is not None:
        return cmd_record(root, None if args.record == "__all__" else args.record)
    if args.update is not None:
        return cmd_update(root, None if args.update == "__all__" else args.update)
    if args.clone is not None:
        return cmd_clone(root, None if args.clone == "__all__" else args.clone)
    if args.refresh is not None:
        return cmd_refresh(root, None if args.refresh == "__all__" else args.refresh)
    if args.add:
        name, url = args.add
        return cmd_add(root, name, url, args.ref, args.role)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

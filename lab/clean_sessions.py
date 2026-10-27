"""
Enmo Safety lab — remove Copilot CLI sessions created by the lab.

The Copilot CLI persists every SDK session under ~/.copilot/session-state. Lab
sessions contain benchmark prompts (some harmful) and slow session creation as
they accumulate. A session is removed only when ALL of these hold:

    - its first event is session.start with context.cwd inside this lab folder
      or the lab state dir (ENMO_SAFETY_LAB_STATE)
    - it is not in use (no inuse.<pid>.lock whose pid is alive)

Sessions started anywhere else are never touched.

Flags:
    --dry-run   count and list, delete nothing

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from common import LAB, STATE

STORE = Path.home() / ".copilot" / "session-state"


def pid_alive(pid: int) -> bool:
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def session_cwd(d: Path) -> str:
    ev = d / "events.jsonl"
    if ev.is_file():
        try:
            with ev.open(encoding="utf-8") as f:
                first = json.loads(f.readline())
            if first.get("type") == "session.start":
                return (first.get("data", {}).get("context", {}) or {}).get("cwd", "")
        except (OSError, json.JSONDecodeError):
            return ""
    # Deleted sessions leave a folder with only workspace.yaml (cwd: <path>).
    ws = d / "workspace.yaml"
    if ws.is_file():
        for line in ws.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("cwd:"):
                return line.split(":", 1)[1].strip()
    return ""


def is_lab_session(d: Path) -> bool:
    cwd = session_cwd(d)
    if not cwd:
        return False
    try:
        p = Path(cwd).resolve()
        return p.is_relative_to(LAB) or p.is_relative_to(STATE)
    except (OSError, ValueError):
        return False


def in_use(d: Path) -> bool:
    for lock in d.glob("inuse.*.lock"):
        try:
            if pid_alive(int(lock.name.split(".")[1])):
                return True
        except ValueError:
            continue
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove Copilot sessions created by the lab")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not STORE.is_dir():
        print("no session store")
        return 0
    lab, busy, other = [], 0, 0
    for d in STORE.iterdir():
        if not d.is_dir():
            continue
        if not is_lab_session(d):
            other += 1
        elif in_use(d):
            busy += 1
        else:
            lab.append(d)
    print(f"lab sessions: {len(lab)} removable, {busy} in use; other sessions kept: {other}")
    if not args.dry_run:
        for d in lab:
            shutil.rmtree(d, ignore_errors=True)
        print(f"removed {len(lab)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

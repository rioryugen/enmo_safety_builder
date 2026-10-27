"""
Enmo Safety lab — shared paths and IO helpers.

Author:   m03 (Intel)
Revision: 1.1

Revision History:
    1.0 — Initial version.
    1.1 — Run state (response cache, run rows) lives outside synced folders:
          ENMO_SAFETY_LAB_STATE, default %LOCALAPPDATA%/enmo_safety_lab. Thousands of
          small cache files inside OneDrive saturated the CPU with sync work.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

LAB = Path(__file__).resolve().parent
BUILDER = LAB.parent
WORKSPACE = BUILDER.parent
SAFETY = WORKSPACE / "enmo_safety"
DATA = LAB / "data"
STATE = Path(os.environ.get("ENMO_SAFETY_LAB_STATE")
             or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "enmo_safety_lab")
RUNS = STATE / "runs"
CACHE = STATE / "cache"
RESULTS = BUILDER / "results"

sys.path.insert(0, str(SAFETY / "scripts"))


def sha(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()


def jread(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def jwrite(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def jsonl_read(path: Path) -> list:
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def jsonl_append(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

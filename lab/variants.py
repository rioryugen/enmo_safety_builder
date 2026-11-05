"""
Enmo Safety lab — candidate harness variants, prototyped in the Builder before they touch the source repo.

A candidate lives in candidates/<name>/ (rules.json + safety_prompt.md), built reproducibly by
lab/make_candidates.py and selectable as a run_eval condition by its directory name. The v22
candidates were promoted to enmo_safety as the gen4 seed, so the normalisation (`fold`, the
`variant.normalize` rules flag) now lives in enmo_safety/scripts/safety_runtime.py and this
module only loads candidates and delegates.

Author:   m03 (Intel)
Revision: 1.1

Revision History:
    1.0 — Prototype: fold(), variant.normalize, tool-task clause replacement.
    1.1 — Promoted to the runtime; tool-task clause replacement dropped (unused after measurement).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import common  # noqa: F401  (sets sys.path for safety_runtime)
import safety_runtime as rt

CANDIDATES = Path(__file__).resolve().parent.parent / "candidates"


def fold(text: str | None) -> str | None:
    """Delegates to the runtime; the prototype now lives in enmo_safety/scripts/safety_runtime.py."""
    return rt.fold(text)


def load_candidate(name: str) -> dict[str, Any]:
    h = rt.load_harness(CANDIDATES / name)
    h["candidate"] = name
    return h


def prepare(harness: dict[str, Any], prompt: str, untrusted: str | None = None):
    """Candidates run through the runtime: assess_input honours variant.normalize itself."""
    return rt.prepare(harness, prompt, untrusted)

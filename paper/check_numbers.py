"""
Enmo Safety paper — check that every percentage quoted in paper.md exists in
the generated numbers (results/summary.json via build_tables.py).

Exit 1 lists any percentage in the prose that no result produces.

Author:   m03 (Intel)
Revision: 1.1

Revision History:
    1.0 — Initial version.
    1.1 — Reads every results/**/summary.json, including per-model gate reports.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def add_summary(numbers: set, s: dict) -> None:
    for cell in s["table"].values():
        for k, t in cell.items():
            if k.startswith("_"):
                continue
            for stat in ("mean", "std", "pooled"):
                if t.get(stat) is not None:
                    numbers.add(f"{t[stat]*100:.1f}")
            if t.get("ci95"):
                numbers |= {f"{x*100:.1f}" for x in t["ci95"]}
    for d in s.get("jbb_templates", {}).values():
        numbers |= {f"{v*100:.1f}" for v in d.values()}
    for e in s.get("evolution", []):
        dev = e.get("dev") or {}
        sides = [dev.get("parent"), dev.get("child")] + [
            v.get(side) for k, v in dev.items() if isinstance(v, dict) and not k.startswith("_")
            for side in ("parent", "child")]
        for side in sides:
            for v in (side or {}).values():
                if isinstance(v, (int, float)):
                    numbers.add(f"{v*100:.1f}")
    ja = s.get("judge_agreement", {})
    if ja.get("agreement") is not None:
        numbers.add(f"{ja['agreement']*100:.1f}")


def main() -> int:
    numbers = set(json.loads((HERE / "generated" / "numbers.json").read_text(encoding="utf-8")).values())
    for path in sorted((HERE.parent / "results").rglob("summary.json")):
        add_summary(numbers, json.loads(path.read_text(encoding="utf-8")))
    text = (HERE / "paper.md").read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    quoted = re.findall(r"(\d+\.\d)\s?%", text)
    missing = sorted({q for q in quoted if q not in numbers})
    print(f"{len(quoted)} percentages quoted, {len(missing)} without a source")
    for q in missing:
        print(f"  MISSING {q}%")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

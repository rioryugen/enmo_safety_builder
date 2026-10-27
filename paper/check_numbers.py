"""
Enmo Safety paper — check that every percentage quoted in paper.md exists in
the generated numbers (results/summary.json via build_tables.py).

Exit 1 lists any percentage in the prose that no result produces.

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    numbers = set(json.loads((HERE / "generated" / "numbers.json").read_text(encoding="utf-8")).values())
    s = json.loads((HERE.parent / "results" / "summary.json").read_text(encoding="utf-8"))
    for cell in s["table"].values():
        for k, t in cell.items():
            if k.startswith("_"):
                continue
            for stat in ("pooled",):
                if t.get(stat) is not None:
                    numbers.add(f"{t[stat]*100:.1f}")
            if t.get("ci95"):
                numbers |= {f"{x*100:.1f}" for x in t["ci95"]}
    for k, d in s.get("jbb_templates", {}).items():
        numbers |= {f"{v*100:.1f}" for v in d.values()}
    for e in s.get("evolution", []):
        for side in ("parent", "child"):
            for v in ((e.get("dev") or {}).get(side) or {}).values():
                if v is not None:
                    numbers.add(f"{v*100:.1f}")
    ja = s.get("judge_agreement", {})
    if ja.get("agreement") is not None:
        numbers.add(f"{ja['agreement']*100:.1f}")
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

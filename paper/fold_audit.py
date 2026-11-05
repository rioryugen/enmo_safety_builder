"""
Enmo Safety paper — does input normalisation (variant.normalize) restore activation under obfuscation?

Compares harness v21 (no normalisation) with v22 (normalisation) on the 225 test attack items and the 139
benign items of every split, under seven obfuscations. The first three are the audit's own transforms,
which the fold was designed against; the other four (fullwidth, symbol leetspeak, spaced and dotted
letters) were tried afterwards, and the fold was extended once after the first look at them, so only
fullwidth was untouched by design. No model is queried.

    python paper/fold_audit.py          # writes results/trigger_audit/fold/summary.json

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lab"))
sys.path.insert(0, str(HERE))
from common import DATA, RESULTS, jread, jwrite  # noqa: E402
import safety_runtime as rt  # noqa: E402
from trigger_audit import TRANSFORMS, VERSIONS, cell, group_of  # noqa: E402

FULL = str.maketrans({c: chr(ord(c) + 0xFEE0) for c in map(chr, range(33, 127))})
EXTRA = {
    "fullwidth": lambda s: s.translate(FULL),
    "symbol_leet": lambda s: s.translate(str.maketrans("asieoASIEO", "@$!30@$!30")),
    "spaced": lambda s: re.sub(r"\b(\w{4,})\b", lambda m: " ".join(m.group(1)), s),
    "dotted": lambda s: re.sub(r"\b(\w{4,})\b", lambda m: ".".join(m.group(1)), s),
}


def flagged(rules: dict, r: dict, fn=None) -> bool:
    p, u = r["prompt"], r.get("untrusted")
    if fn:
        p, u = fn(p), (fn(u) if u is not None else None)
    return not rt.low_risk(rt.assess_input(p, rules, u))


def main() -> int:
    data = jread(DATA / "benchmarks.json")
    rows = [r for sp in data["benchmarks"].values() for k in ("test", "evolve", "dev", "probe") for r in sp[k]]
    attack = [r for r in rows if r["split"] == "test" and group_of(r) == "attack"]
    benign = [r for r in rows if group_of(r) == "benign"]
    table, out = {}, {}
    for name in ("v21", "v22"):
        rules = rt.load_harness(VERSIONS / name)["rules"]
        for tname, fn in {"clean": None, **TRANSFORMS, **EXTRA}.items():
            a = sum(flagged(rules, r, fn) for r in attack)
            b = sum(flagged(rules, r, fn) for r in benign)
            table[f"{name}:{tname}|attack"] = {"flag": cell(a, len(attack)), "_n": len(attack), "_hits": a}
            table[f"{name}:{tname}|benign"] = {"flag": cell(b, len(benign)), "_n": len(benign), "_hits": b}
            out.setdefault(tname, {})[name] = (a, b)
    jwrite(RESULTS / "trigger_audit" / "fold" / "summary.json",
           {"run": "fold_audit", "attack_items": len(attack), "benign_items": len(benign), "table": table})
    print(f"{'transform':12} {'v21 attack':>11} {'v22 attack':>11} {'v21 benign':>11} {'v22 benign':>11}   (of {len(attack)} attack, {len(benign)} benign)")
    for t, v in out.items():
        print(f"{t:12} {v['v21'][0]:>11} {v['v22'][0]:>11} {v['v21'][1]:>11} {v['v22'][1]:>11}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

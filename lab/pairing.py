"""
Enmo Safety lab — pair detector activation with judged outcomes.

For each model and harness condition in a run, splits the attack items by
whether the harness's deterministic input signals fired (the row's stored
`assessment`, i.e. `not low_risk`) and compares the judged unsafe rate of the
two groups. Also reports benign refusal by flag. Writes
results/<name>/pairing/summary.json in the evaluation `table` schema plus a
privacy-safe per-item export results/<name>/items.jsonl (ids, flags, labels;
no prompts or replies) so the analysis is reproducible from committed data.

    python lab/pairing.py --name cli_test

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict

from common import RESULTS, RUNS, jsonl_read, jwrite  # noqa: I001 (sets sys.path)
from scipy.stats import fisher_exact

ATTACK = ("harmful", "agentic_harmful", "injection")
BAD = ("harmful", "injected")


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def cell(k: int, n: int) -> dict:
    return {"mean": k / n if n else 0.0, "pooled": k / n if n else 0.0, "n_runs": 1, "ci95": wilson(k, n)}


def flagged(row: dict) -> bool | None:
    a = row.get("assessment") or {}
    if not a:
        return None  # bare / spot rows carry no assessment
    return bool(a.get("categories") or a.get("jailbreak") or a.get("injection"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="main")
    args = ap.parse_args()
    rows = jsonl_read(RUNS / args.name / "rows.jsonl")
    if not rows:
        print("no rows")
        return 1
    out_dir = RESULTS / args.name
    items = [{k: r.get(k) for k in ("model", "cond", "bench", "id", "kind", "template", "run", "harness_version",
                                     "label", "output_blocked", "platform_block", "heuristic_refusal")}
             | {"flagged": flagged(r), "risk": (r.get("assessment") or {}).get("risk")} for r in rows]
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / "items.jsonl").write_text("\n".join(__import__("json").dumps(i) for i in items) + "\n", encoding="utf-8")

    table, tests = {}, {}
    groups = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # (model,cond) -> group -> [bad, n]
    for r in rows:
        f = flagged(r)
        if f is None:
            continue
        key = f"{r['model']}|{r['cond']}"
        if r["kind"] in ATTACK:
            g = "attack_flagged" if f else "attack_unflagged"
            groups[key][g][0] += r["label"] in BAD
            groups[key][g][1] += 1
        else:
            g = "benign_flagged" if f else "benign_unflagged"
            groups[key][g][0] += r["label"] == "refusal"
            groups[key][g][1] += 1
    for key, gs in groups.items():
        table[key] = {g: cell(*v) for g, v in gs.items()} | {"_n": {g: v[1] for g, v in gs.items()}, "_bad": {g: v[0] for g, v in gs.items()}}
        fb, fn = gs["attack_flagged"]
        ub, un = gs["attack_unflagged"]
        odds, p = fisher_exact([[fb, fn - fb], [ub, un - ub]]) if fn and un else (None, None)
        tests[key] = {"fisher_p": p, "odds_ratio": None if odds is None or math.isinf(odds) else odds,
                      "flagged_unsafe": f"{fb}/{fn}", "unflagged_unsafe": f"{ub}/{un}"}
        print(f"{key:40} unsafe flagged {fb:>3}/{fn:<3} ({fb / fn if fn else 0:5.1%})  unflagged {ub:>3}/{un:<3} ({ub / un if un else 0:5.1%})"
              f"  Fisher p={p if p is None else round(p, 3)}  benign refusal flagged {gs['benign_flagged'][0]}/{gs['benign_flagged'][1]} unflagged {gs['benign_unflagged'][0]}/{gs['benign_unflagged'][1]}")
    jwrite(out_dir / "pairing" / "summary.json", {"run": args.name, "rows": len(rows), "table": table, "_tests": tests})
    print("wrote", out_dir / "pairing" / "summary.json", "and items.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

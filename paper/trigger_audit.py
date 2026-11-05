"""
Enmo Safety paper — static trigger-coverage audit of the harness rules.

Runs `assess_input` over the seeded benchmark splits and records which
deterministic input signals fire (harm category, jailbreak, injection). No
model is queried. Writes results/trigger_audit/summary.json in the same
`table` schema as the evaluation summaries so paper/check_numbers.py accepts
the quoted percentages.

Analyses (all on the v12 rules unless stated):
    coverage     per benchmark and group, test split
    unique       items flagged by exactly one pattern group
    seen vs test coverage on the evolve+dev items the evolution loop saw
    dead rules   patterns that never fire on any split
    obfuscation  coverage after three surface transforms of the attack items
    versions     coverage of every snapshot v0..vN on the test split, with the
                 number of items whose assessment changed versus the parent,
                 joined to the evolution ledger

    python paper/trigger_audit.py                 # current harness -> results/trigger_audit/v<N>/summary.json
    python paper/trigger_audit.py --version 12    # audit a snapshot

Author:   m03 (Intel)
Revision: 1.1

Revision History:
    1.0 — Initial version: per-benchmark coverage, JBB template breakdown.
    1.1 — Unique-group hits, seen-vs-test, dead rules, obfuscation, version
          trajectory joined to the ledger.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lab"))
from common import DATA, RESULTS, SAFETY, jread, jwrite  # noqa: E402  (sets sys.path for safety_runtime)
import safety_runtime as rt  # noqa: E402

ATTACK = ("harmful", "agentic_harmful", "injection")
GROUPS = ("category", "jailbreak", "injection")
LABEL = {"advbench": "AdvBench", "agentharm": "AgentHarm", "harmbench": "HarmBench",
         "injection": "deepset prompt-injections", "jbb": "JailbreakBench", "xstest": "XSTest"}
VERSIONS = SAFETY / "harness" / "versions"
LEDGER = SAFETY / "harness" / "evolution-ledger.json"

_LEET = str.maketrans("aeioAEIO", "43104310")
_CYR = str.maketrans("aeopcAEOPC", "аеорсАЕОРС")  # Latin -> Cyrillic look-alikes
TRANSFORMS = {
    "leetspeak": lambda s: s.translate(_LEET),
    "homoglyph": lambda s: s.translate(_CYR),
    # one zero-width space after the second letter of every word of 4+ letters
    "zero_width": lambda s: re.sub(r"\b(\w{2})(\w{2,})\b", "\\1\u200b\\2", s),
}


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def cell(k: int, n: int) -> dict:
    return {"mean": k / n if n else 0.0, "pooled": k / n if n else 0.0, "n_runs": 1, "ci95": wilson(k, n)}


def group_of(r: dict) -> str:
    return "attack" if r["kind"] in ATTACK else "benign"


def signals(a: dict) -> dict:
    return {"category": bool(a["categories"]), "jailbreak": bool(a["jailbreak"]),
            "injection": bool(a["injection"]), "any": not rt.low_risk(a)}


def assess(r: dict, rules: dict, transform=None) -> dict:
    prompt, doc = r["prompt"], r.get("untrusted")
    if transform:
        prompt, doc = transform(prompt), (transform(doc) if doc is not None else None)
    return rt.assess_input(prompt, rules, doc)


def coverage(items: list, rules: dict, transform=None) -> tuple[dict, dict]:
    """Returns (hits[key][signal], total[key]) keyed by 'bench|group' plus 'all|group'."""
    hits, total = defaultdict(lambda: defaultdict(int)), defaultdict(int)
    for r in items:
        s = signals(assess(r, rules, transform))
        for key in (f"{r['bench']}|{group_of(r)}", f"all|{group_of(r)}"):
            total[key] += 1
            for sig, v in s.items():
                hits[key][sig] += v
            hits[key]["spotlit"] += r.get("untrusted") is not None
            hits[key]["unique"] += sum(s[g] for g in GROUPS) == 1
    return hits, total


def dead_rules(items: list, rules: dict) -> dict:
    """Fire count per pattern over every item, probing exactly as assess_input does."""
    counts = {}
    for cat, pat in rules.get("harm_categories", {}).items():
        counts[f"category:{cat}"] = sum(bool(rt._compile(pat).search(r["prompt"] + ("\n" + r["untrusted"] if r.get("untrusted") else ""))) for r in items)
    for pat in rules.get("jailbreak_patterns", []):
        counts[f"jailbreak:{pat}"] = sum(bool(rt._compile(pat).search(r["prompt"])) for r in items)
    for pat in rules.get("injection_patterns", []):
        counts[f"injection:{pat}"] = sum(bool(rt._compile(pat).search(r["untrusted"] if r.get("untrusted") else r["prompt"])) for r in items)
    return counts


def assessment_delta(items: list, rules_a: dict, rules_b: dict) -> int:
    """Items whose full assessment (categories, flags, risk) differs between two rule sets."""
    return sum(assess(r, rules_a) != assess(r, rules_b) for r in items)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=int, help="audit this harness snapshot (default: current harness)")
    args = ap.parse_args()
    data = jread(DATA / "benchmarks.json")
    if not data:
        print("lab/data/benchmarks.json missing; run python lab/bench_data.py first")
        return 1
    harness = rt.load_harness(VERSIONS / f"v{args.version}" if args.version is not None else None)
    rules = harness["rules"]
    out_dir = RESULTS / "trigger_audit" / f"v{harness['version']}"
    by_split = defaultdict(list)
    for splits in data["benchmarks"].values():
        for name in ("test", "evolve", "dev", "probe"):
            by_split[name].extend(splits.get(name, []))
    test, seen = by_split["test"], by_split["evolve"] + by_split["dev"]
    everything = [r for rows in by_split.values() for r in rows]

    table: dict = {}
    hits, total = coverage(test, rules)
    for k in total:
        table[k] = {sig: cell(hits[k][sig], total[k]) for sig in ("any", *GROUPS, "spotlit", "unique")}
        table[k] |= {"_n": total[k], "_hits": dict(hits[k])}
    tmpl = defaultdict(lambda: [0, 0])
    for r in test:
        if r.get("template"):
            tmpl[r["template"]][0] += rt.assess_input(r["prompt"], rules)["jailbreak"]
            tmpl[r["template"]][1] += 1

    s_hits, s_total = coverage(seen, rules)
    for g in ("attack", "benign"):
        table[f"seen|{g}"] = {"any": cell(s_hits[f"all|{g}"]["any"], s_total[f"all|{g}"]), "_n": s_total[f"all|{g}"]}

    for name, fn in TRANSFORMS.items():
        o_hits, o_total = coverage([r for r in test if group_of(r) == "attack"], rules, fn)
        for k in o_total:
            bench = k.split("|")[0]
            table[f"obf:{name}:{bench}|attack"] = {sig: cell(o_hits[k][sig], o_total[k]) for sig in ("any", *GROUPS)}
            table[f"obf:{name}:{bench}|attack"]["_n"] = o_total[k]
        table[f"obf:{name}|attack"] = table.pop(f"obf:{name}:all|attack")

    # Which harm categories fire on which benchmark, and the risk-score distribution per group.
    cat_matrix = defaultdict(lambda: defaultdict(int))
    risk_dist = defaultdict(lambda: defaultdict(int))
    flags = defaultdict(lambda: defaultdict(int))
    for r in test:
        a = assess(r, rules)
        for c in a["categories"]:
            cat_matrix[c][r["bench"]] += 1
        risk_dist[group_of(r)][a["risk"]] += 1
        for f in ("intent", "benign", "agentic"):
            flags[group_of(r)][f] += bool(a[f])

    fires = dead_rules(everything, rules)
    dead = sorted(k for k, v in fires.items() if v == 0)

    ledger = {e["version"]: e for e in (jread(LEDGER) or {}).get("entries", [])}
    versions = []
    for vdir in sorted(VERSIONS.glob("v*"), key=lambda p: int(p.name[1:])):
        vr = rt.load_harness(vdir)["rules"]
        v_hits, v_total = coverage(test, vr)
        n = int(vdir.name[1:])
        e = ledger.get(n, {})
        parent = e.get("parent")
        delta = delta_dev = None
        if parent is not None and (VERSIONS / f"v{parent}" / "rules.json").is_file():
            pr = rt.load_harness(VERSIONS / f"v{parent}")["rules"]
            delta, delta_dev = assessment_delta(test, pr, vr), assessment_delta(by_split["dev"], pr, vr)
        dev = e.get("dev") or {}
        gate_cells = [m for m in dev.values() if isinstance(m, dict) and "parent" in m]
        dev_identical = bool(gate_cells) and all(m["parent"] == m["child"] for m in gate_cells)
        table[f"v{n}|attack"] = {"any": cell(v_hits["all|attack"]["any"], v_total["all|attack"]), "_n": v_total["all|attack"]}
        table[f"v{n}|benign"] = {"any": cell(v_hits["all|benign"]["any"], v_total["all|benign"]), "_n": v_total["all|benign"]}
        versions.append({"version": n, "parent": parent, "status": e.get("status"),
                         "op": (e.get("update") or {}).get("op"), "list": (e.get("update") or {}).get("list"),
                         "flagged_attack": v_hits["all|attack"]["any"], "flagged_benign": v_hits["all|benign"]["any"],
                         "assessment_delta_vs_parent": delta, "assessment_delta_dev_split": delta_dev,
                         "dev_metrics_identical": dev_identical if gate_cells else None})

    out = {"run": "trigger_audit", "harness_version": harness["version"], "split": "test", "seed": data["seed"],
           "items": len(test), "seen_items": len(seen), "all_items": len(everything),
           "rules": {"harm_categories": len(rules.get("harm_categories", {})),
                     "jailbreak_patterns": len(rules.get("jailbreak_patterns", [])),
                     "injection_patterns": len(rules.get("injection_patterns", []))},
           "table": table,
           "jbb_templates": {f"v{harness['version']}|test": {t: f / n for t, (f, n) in sorted(tmpl.items())}},
           "_rule_fires": fires, "_dead_rules": dead, "_versions": versions,
           "_category_by_bench": {c: dict(b) for c, b in sorted(cat_matrix.items())},
           "_risk_distribution": {g: {str(k): v for k, v in sorted(d.items())} for g, d in risk_dist.items()},
           "_flags": {g: dict(d) for g, d in flags.items()}}
    jwrite(out_dir / "summary.json", out)

    print(f"harness v{harness['version']} · test split seed {data['seed']} · {len(test)} items\n")
    print(f"{'benchmark':28}{'group':8}{'any':>9}{'cat':>6}{'jb':>6}{'inj':>6}{'spot':>6}{'uniq':>6}")
    for k in sorted(total, key=lambda s: (s.startswith("all|"), s)):
        bench, group = k.split("|")
        h, n = hits[k], total[k]
        print(f"{LABEL.get(bench, bench):28}{group:8}{h['any']:>3}/{n:<3} {h['any']/n:5.1%}"
              f"{h['category']:>6}{h['jailbreak']:>6}{h['injection']:>6}{h['spotlit']:>6}{h['unique']:>6}")
    print("\njailbreak pattern hits by JBB template: " +
          ", ".join(f"{t} {f}/{n}" for t, (f, n) in sorted(tmpl.items())))
    for g in ("attack", "benign"):
        print(f"seen (evolve+dev) {g}: {s_hits[f'all|{g}']['any']}/{s_total[f'all|{g}']} "
              f"({s_hits[f'all|{g}']['any']/s_total[f'all|{g}']:.1%}) vs test {hits[f'all|{g}']['any']}/{total[f'all|{g}']}")
    print("\nobfuscation (attack items, test split):")
    for name in TRANSFORMS:
        c = table[f"obf:{name}|attack"]
        print(f"  {name:12} any {c['any']['mean']:5.1%}  cat {c['category']['mean']:5.1%}  "
              f"jb {c['jailbreak']['mean']:5.1%}  inj {c['injection']['mean']:5.1%}")
    print(f"\ndead rules (never fire on {len(everything)} items): {len(dead)} of {len(fires)}")
    for k in dead:
        print(f"  {k}")
    print("\nrisk-score distribution:", {g: dict(d) for g, d in risk_dist.items()})
    print("flags:", {g: dict(d) for g, d in flags.items()})
    print(f"\n{'ver':>4} {'parent':>6} {'status':12}{'op':22}{'attack':>7}{'benign':>7}{'dTest':>6}{'dDev':>6}  dev identical")
    for v in versions:
        print(f"{v['version']:>4} {str(v['parent']):>6} {str(v['status']):12}{str(v['op']):22}"
              f"{v['flagged_attack']:>7}{v['flagged_benign']:>7}{str(v['assessment_delta_vs_parent']):>6}"
              f"{str(v['assessment_delta_dev_split']):>6}  {v['dev_metrics_identical']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

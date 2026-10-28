"""
Enmo Safety lab — analysis: metrics, uncertainty, significance, figures.

Reads lab/runs/<name>/rows.jsonl and writes:

    results/summary.json   every number the paper and README quote
    results/tables.md      Markdown tables generated from summary.json
    results/fig_*.svg      grouped bar charts (stdlib SVG)

Statistics:
    mean +- sample std over independent runs
    95% bootstrap CI over items (runs pooled, 2000 resamples, fixed seed)
    exact McNemar test, item-level majority vote over runs (bare vs vN, v0 vs vN)
    Cohen's kappa between the heuristic and the LLM judge on the audit sample

Flags:
    --name NAME   run folder (default: main)

Author:   m03 (Intel)
Revision: 1.2

Revision History:
    1.0 — Initial version.
    1.1 — Only complete runs per cell; spot / v8 / v9 conditions with labels and
          colours; extra McNemar pairs; records which version vN pointed to.
    1.2 — v12 condition; McNemar pairs against spotlighting and v12; other
          snapshot conditions are kept (after the known ones) and compared to vN.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from collections import defaultdict
from typing import Dict, List

from common import RESULTS, RUNS, SAFETY, jread, jsonl_read, jwrite
from metrics import METRICS, score

COND_ORDER = ("bare", "spot", "v0", "v8", "v9", "v12", "vN")
COND_LABEL = {"bare": "no harness", "spot": "spotlighting only", "v0": "seed v0",
              "v8": "gen-1 evolved v8", "v9": "gen-2 seed v9", "v12": "gen-2 evolved v12",
              "v19": "gen-3d (rejected)",
              "vN": "latest evolved vN"}
COND_COLOR = {"bare": "#9e9e9e", "spot": "#ffb74d", "v0": "#5b8def", "v8": "#8e24aa",
              "v9": "#5b8def", "v12": "#00897b", "vN": "#2e7d32"}
LABELS = {
    "asr": "Attack success rate (HarmBench+AdvBench+JBB)",
    "jbb_asr": "Jailbreak ASR (JBB, 5 archetypes)",
    "agent_harm": "AgentHarm harmful completion",
    "over_refusal": "XSTest over-refusal",
    "agent_refusal": "AgentHarm benign refusal",
    "injection": "Prompt-injection success",
    "unsafe": "Unsafe (harmful or injected), all attack prompts",
    "refuse_benign": "Refusal of benign prompts",
}


def short(model: str) -> str:
    return model.split(":", 1)[1]


def mean_std(xs: List[float]) -> Dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"mean": None, "std": None, "n_runs": 0}
    return {"mean": statistics.fmean(xs), "std": statistics.stdev(xs) if len(xs) > 1 else 0.0,
            "n_runs": len(xs)}


def bootstrap(rows: List[Dict], metric: str, iters: int = 2000, seed: int = 7) -> List[float] | None:
    by_item = defaultdict(list)
    for r in rows:
        by_item[r["id"]].append(r)
    ids = sorted(by_item)
    if not ids or score(rows)[metric] is None:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        sample = [r for i in (rng.choice(ids) for _ in ids) for r in by_item[i]]
        v = score(sample)[metric]
        if v is not None:
            vals.append(v)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]] if vals else None


def item_bad(rows: List[Dict]) -> Dict[str, bool]:
    votes = defaultdict(list)
    for r in rows:
        if r["kind"] in ("harmful", "agentic_harmful", "injection"):
            votes[r["id"]].append(r["label"] in ("harmful", "injected"))
        elif r["kind"] in ("benign", "agentic_benign"):
            votes[r["id"]].append(r["label"] == "refusal")
    return {i: sum(v) * 2 > len(v) for i, v in votes.items()}


def mcnemar(a: Dict[str, bool], b: Dict[str, bool]) -> Dict:
    ids = sorted(set(a) & set(b))
    b10 = sum(1 for i in ids if a[i] and not b[i])
    b01 = sum(1 for i in ids if not a[i] and b[i])
    n = b10 + b01
    if n == 0:
        return {"fixed": 0, "broken": 0, "p": 1.0, "items": len(ids)}
    k = min(b10, b01)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"fixed": b10, "broken": b01, "p": p, "items": len(ids)}


def kappa(pairs: List[tuple]) -> Dict:
    if not pairs:
        return {"kappa": None, "n": 0}
    n = len(pairs)
    po = sum(1 for x, y in pairs if x == y) / n
    pa = sum(1 for x, _ in pairs if x) / n
    pb = sum(1 for _, y in pairs if y) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return {"kappa": (po - pe) / (1 - pe) if pe < 1 else 1.0, "agreement": po, "n": n}


def svg_bars(title: str, groups: List[str], series: List[str], values: Dict, errs: Dict) -> str:
    W, H, L, B, T = 760, 340, 60, 70, 40
    colors = COND_COLOR
    plot_w, plot_h = W - L - 20, H - B - T
    vmax = max([v + (errs.get(k) or 0) for k, v in values.items() if v is not None] + [0.05])
    vmax = min(1.0, math.ceil(vmax * 10) / 10 + 0.05)
    gw = plot_w / max(1, len(groups))
    bw = gw * 0.8 / max(1, len(series))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Segoe UI,Arial" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{W/2}" y="22" text-anchor="middle" font-size="14" font-weight="bold">{title}</text>']
    for t in range(0, 6):
        v = vmax * t / 5
        y = T + plot_h - plot_h * v / vmax
        out.append(f'<line x1="{L}" x2="{W-20}" y1="{y:.1f}" y2="{y:.1f}" stroke="#eee"/>')
        out.append(f'<text x="{L-6}" y="{y+4:.1f}" text-anchor="end">{v*100:.0f}%</text>')
    for gi, g in enumerate(groups):
        x0 = L + gi * gw + gw * 0.1
        for si, s in enumerate(series):
            v = values.get((g, s))
            if v is None:
                continue
            h = plot_h * v / vmax
            x = x0 + si * bw
            y = T + plot_h - h
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-2:.1f}" height="{h:.1f}" fill="{colors.get(s, "#555")}"/>')
            e = errs.get((g, s)) or 0
            if e:
                y1, y2 = T + plot_h - plot_h * min(vmax, v + e) / vmax, T + plot_h - plot_h * max(0, v - e) / vmax
                cx = x + (bw - 2) / 2
                out.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y1:.1f}" y2="{y2:.1f}" stroke="black"/>')
            out.append(f'<text x="{x + (bw-2)/2:.1f}" y="{y-4:.1f}" text-anchor="middle" font-size="10">{v*100:.0f}</text>')
        out.append(f'<text x="{L + gi*gw + gw/2:.1f}" y="{T + plot_h + 18}" text-anchor="middle">{g}</text>')
    for si, s in enumerate(series):
        x = L + si * 120
        out.append(f'<rect x="{x}" y="{H-24}" width="12" height="12" fill="{colors.get(s, "#555")}"/>'
                   f'<text x="{x+18}" y="{H-14}">{COND_LABEL.get(s, s)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def pct(x) -> str:
    return "n/a" if x is None else f"{x*100:.1f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze an Enmo Safety evaluation run")
    ap.add_argument("--name", default="main")
    args = ap.parse_args()

    rows = jsonl_read(RUNS / args.name / "rows.jsonl")
    if not rows:
        raise SystemExit("no rows")
    out_dir = RESULTS if args.name == "main" else RESULTS / args.name
    models = sorted({r["model"] for r in rows})
    conds = [c for c in COND_ORDER if any(r["cond"] == c for r in rows)]
    conds += sorted({r["cond"] for r in rows} - set(conds))
    runs = sorted({r["run"] for r in rows})

    cell = defaultdict(list)
    for r in rows:
        cell[(r["model"], r["cond"])].append(r)
    # Keep only runs that cover every item of the cell, so runs are comparable.
    excluded = {}
    for key, rs in list(cell.items()):
        ids = {r["id"] for r in rs}
        per = defaultdict(set)
        for r in rs:
            per[r["run"]].add(r["id"])
        full = {k for k, v in per.items() if v == ids}
        if full and len(full) < len(per):
            excluded["|".join(key)] = sorted(set(per) - full)
            cell[key] = [r for r in rs if r["run"] in full]
    rows = [r for rs in cell.values() for r in rs]
    runs = sorted({r["run"] for r in rows})

    table = {}
    for (m, c), rs in cell.items():
        cell_runs = sorted({r["run"] for r in rs})
        per_run = {k: score([r for r in rs if r["run"] == k]) for k in cell_runs}
        pooled = score(rs)
        table[f"{m}|{c}"] = {
            met: {**mean_std([per_run[k][met] for k in cell_runs]), "pooled": pooled[met],
                  "ci95": bootstrap(rs, met)} for met in METRICS}
        table[f"{m}|{c}"]["_overhead"] = {
            "system_chars": statistics.fmean(r["system_chars"] for r in rs),
            "latency_ms": statistics.fmean(r["latency_ms"] for r in rs if not r["cached"]) if any(not r["cached"] for r in rs) else None,
            "output_blocked": sum(1 for r in rs if r.get("output_blocked")),
            "platform_block": sum(1 for r in rs if r.get("platform_block")),
            "rows": len(rs)}

    tests = {}
    for m in models:
        bad = {c: item_bad(cell[(m, c)]) for c in conds}
        pairs = [("bare", "vN"), ("v0", "vN"), ("bare", "v0"), ("v8", "vN"),
                 ("bare", "v8"), ("bare", "v9"), ("v9", "vN"), ("bare", "spot"),
                 ("spot", "vN"), ("v12", "vN"), ("bare", "v12"), ("spot", "v12")]
        pairs += [("vN", c) for c in conds if c not in COND_ORDER]
        for a, b in pairs:
            if a in bad and b in bad:
                tests[f"{m}|{a}->{b}"] = mcnemar(bad[a], bad[b])

    templ = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["bench"] == "jbb":
            templ[f"{r['model']}|{r['cond']}"][r["template"]].append(r["label"] == "harmful")
    jbb_templates = {k: {t: sum(v) / len(v) for t, v in d.items()} for k, d in templ.items()}

    audit = [(r["heuristic_refusal"], r["llm"]["label"] == "refusal") for r in rows
             if r.get("llm") and r["kind"] != "injection"]
    ledger = jread(SAFETY / "harness" / "evolution-ledger.json", {"entries": []})
    summary = {
        "run": args.name, "models": models, "conditions": conds, "runs": len(runs),
        "runs_per_cell": {k: v["unsafe"]["n_runs"] for k, v in table.items()},
        "excluded_partial_runs": excluded,
        "platform_blocks": sum(1 for r in rows if r.get("platform_block")),
        "rows": len(rows), "items_per_condition": len({r["id"] for r in rows}),
        "harness_versions": sorted({r["harness_version"] for r in rows if r["harness_version"] is not None}),
        "vN_version": next((r["harness_version"] for r in rows if r["cond"] == "vN"), None),
        "table": table, "mcnemar": tests, "jbb_templates": jbb_templates,
        "judge_agreement": kappa(audit),
        "evolution": [{k: e.get(k) for k in ("version", "parent", "status", "round", "rationale", "dev")}
                      | {"op": e["update"].get("op")} for e in ledger["entries"]],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    jwrite(out_dir / "summary.json", summary)

    md = [f"# Results — run `{args.name}`", "",
          f"{len(models)} models x {len(conds)} conditions x {summary['items_per_condition']} items; "
          f"{len(rows)} judged replies. Runs per cell: "
          + ", ".join(f"{short(k.split('|')[0])}/{k.split('|')[1]}={v}" for k, v in sorted(summary["runs_per_cell"].items()))
          + (f". Partial runs excluded: {excluded}" if excluded else "") + ".",
          f"Platform content-filter blocks (counted as refusals): {summary['platform_blocks']}.",
          "Values are percentages: mean ± std over runs, 95% bootstrap CI in brackets. Lower is better for every metric.", ""]
    for met in METRICS:
        md += [f"## {LABELS[met]}", "", "| Model | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
        for m in models:
            cells = []
            for c in conds:
                t = table.get(f"{m}|{c}", {}).get(met)
                if not t or t["mean"] is None:
                    cells.append("n/a")
                    continue
                ci = t["ci95"]
                cells.append(f"{pct(t['mean'])} ± {pct(t['std'])} [{pct(ci[0])}, {pct(ci[1])}]" if ci else pct(t["mean"]))
            md.append(f"| {short(m)} | " + " | ".join(cells) + " |")
        md.append("")
    md += ["## McNemar tests (item-level majority vote; fixed = bad→good, broken = good→bad)", "",
           "| Comparison | items | fixed | broken | p |", "|---|---|---|---|---|"]
    for k, t in tests.items():
        m, cmp_ = k.split("|")
        md.append(f"| {short(m)} {cmp_} | {t['items']} | {t['fixed']} | {t['broken']} | {t['p']:.4f} |")
    ja = summary["judge_agreement"]
    md += ["", f"Judge agreement (heuristic vs LLM refusal, n={ja['n']}): kappa = "
           + ("n/a" if ja["kappa"] is None else f"{ja['kappa']:.3f}, raw agreement {ja['agreement']*100:.1f}%"), ""]
    md += ["## Overhead", "", "| Model | cond | system chars | mean latency ms | output-guard blocks | platform blocks |",
           "|---|---|---|---|---|---|"]
    for m in models:
        for c in conds:
            o = table.get(f"{m}|{c}", {}).get("_overhead")
            if o:
                lat = "n/a" if o["latency_ms"] is None else f"{o['latency_ms']:.0f}"
                md.append(f"| {short(m)} | {c} | {o['system_chars']:.0f} | {lat} | {o['output_blocked']} | {o['platform_block']} |")
    (out_dir / "tables.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    groups = [short(m) for m in models]
    for met in ("unsafe", "asr", "jbb_asr", "injection", "over_refusal", "refuse_benign", "agent_harm"):
        vals, errs = {}, {}
        for m in models:
            for c in conds:
                t = table.get(f"{m}|{c}", {}).get(met)
                if t and t["mean"] is not None:
                    vals[(short(m), c)] = t["mean"]
                    errs[(short(m), c)] = t["std"]
        (out_dir / f"fig_{met}.svg").write_text(svg_bars(LABELS[met], groups, conds, vals, errs),
                                                encoding="utf-8", newline="\n")
    print((out_dir / "tables.md").read_text(encoding="utf-8")[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

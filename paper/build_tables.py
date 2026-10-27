"""
Enmo Safety paper — generate LaTeX tables and number macros from results.

Reads ../results/summary.json and writes:

    generated/numbers.tex   \\newcommand macros for every quoted number
    generated/tables.tex    the main before/after table and the McNemar table
    generated/numbers.json  the same numbers, flat, for check_numbers.py

Author:   m03 (Intel)
Revision: 1.0

Revision History:
    1.0 — Initial version.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE.parent / "results" / "summary.json"
OUT = HERE / "generated"
MAIN = (("unsafe", "Unsafe"), ("asr", "ASR"), ("jbb_asr", "JBB ASR"), ("agent_harm", "AgentHarm"),
        ("injection", "Inject."), ("over_refusal", "XSTest OR"), ("agent_refusal", "Agent OR"))


def macro_name(*parts: str) -> str:
    words = re.split(r"[^A-Za-z]+", " ".join(parts))
    digits = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
              "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}
    name = "".join(w.capitalize() for w in words if w)
    for p in parts:
        for d in re.findall(r"\d", p):
            name += digits[d]
    return name


def pct(v):
    return "--" if v is None else f"{v*100:.1f}"


def main() -> int:
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    flat, macros = {}, []
    conds = s["conditions"]
    for model in s["models"]:
        mshort = model.split(":", 1)[1]
        for c in conds:
            cell = s["table"].get(f"{model}|{c}", {})
            for key, _ in MAIN + (("refuse_benign", ""),):
                t = cell.get(key) or {}
                for stat in ("mean", "std"):
                    v = t.get(stat)
                    name = macro_name(mshort, c, key, stat)
                    flat[name] = pct(v)
                    macros.append(f"\\newcommand{{\\{name}}}{{{pct(v)}}}")
    for k, t in s["mcnemar"].items():
        name = macro_name(k, "p")
        flat[name] = f"{t['p']:.3g}"
        macros.append(f"\\newcommand{{\\{name}}}{{{t['p']:.3g}}}")
    ja = s["judge_agreement"]
    flat["JudgeKappa"] = "--" if ja["kappa"] is None else f"{ja['kappa']:.2f}"
    macros.append(f"\\newcommand{{\\JudgeKappa}}{{{flat['JudgeKappa']}}}")
    flat["RowsTotal"] = str(s["rows"])
    macros.append(f"\\newcommand{{\\RowsTotal}}{{{s['rows']}}}")
    (OUT / "numbers.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")
    (OUT / "numbers.json").write_text(json.dumps(flat, indent=1) + "\n", encoding="utf-8")

    cols = "ll" + "r" * len(MAIN)
    tex = ["\\begin{table*}[t]\\centering\\small",
           "\\caption{Safety before and after the harness (\\%, mean $\\pm$ std over runs; lower is better). "
           "bare = no harness, v0 = seed harness, vN = self-evolved harness.}",
           "\\label{tab:main}", f"\\begin{{tabular}}{{{cols}}}", "\\toprule",
           "Model & Cond. & " + " & ".join(h for _, h in MAIN) + " \\\\", "\\midrule"]
    for model in s["models"]:
        mshort = model.split(":", 1)[1].replace("_", "\\_")
        for i, c in enumerate(conds):
            cell = s["table"].get(f"{model}|{c}", {})
            vals = []
            for key, _ in MAIN:
                t = cell.get(key) or {}
                vals.append("--" if t.get("mean") is None else f"{pct(t['mean'])}$\\pm${pct(t['std'])}")
            tex.append(f"{mshort if i == 0 else ''} & {c} & " + " & ".join(vals) + " \\\\")
        tex.append("\\midrule")
    tex[-1] = "\\bottomrule"
    tex += ["\\end{tabular}", "\\end{table*}", "",
            "\\begin{table}[t]\\centering\\small",
            "\\caption{Exact McNemar tests on item-level majority votes. Fixed: unsafe or over-refused "
            "under the first condition, correct under the second; broken: the reverse.}",
            "\\label{tab:mcnemar}", "\\begin{tabular}{llrrrr}", "\\toprule",
            "Model & Comparison & Items & Fixed & Broken & $p$ \\\\", "\\midrule"]
    for k, t in s["mcnemar"].items():
        m, cmp_ = k.split("|")
        cmp_tex = cmp_.replace("->", "$\\rightarrow$")
        tex.append(f"{m.split(':', 1)[1]} & {cmp_tex} & {t['items']} & {t['fixed']} & {t['broken']} & {t['p']:.3g} \\\\")
    tex += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    (OUT / "tables.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    print(f"wrote {len(macros)} macros and 2 tables to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

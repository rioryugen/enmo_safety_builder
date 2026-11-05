"""
Enmo Safety paper — figures for the trigger-coverage audit.

Reads results/trigger_audit/summary.json (written by trigger_audit.py) and
writes results/trigger_audit/fig_*.png for the paper. matplotlib only.

    python paper/trigger_figures.py

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
LABEL = {"advbench": "AdvBench", "agentharm": "AgentHarm", "harmbench": "HarmBench",
         "injection": "deepset inj.", "jbb": "JailbreakBench", "xstest": "XSTest"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
OUT = HERE.parent / "results" / "trigger_audit" / "v12"  # set in main() from --version


def pct(c: dict, sig: str = "any") -> tuple[float, float, float]:
    m, (lo, hi) = c[sig]["mean"] * 100, c[sig]["ci95"]
    return m, m - lo * 100, hi * 100 - m


def fig_coverage(t: dict) -> None:
    keys = [k for k in t if "|" in k and ":" not in k and not k.startswith(("all|", "seen|", "v"))]
    keys.sort(key=lambda k: (k.endswith("benign"), -t[k]["any"]["mean"]))
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    for i, k in enumerate(keys):
        group = k.split("|")[1]
        m, lo, hi = pct(t[k])
        ax.barh(i, m, xerr=[[lo], [hi]], color="#c0392b" if group == "attack" else "#2e86c1", capsize=3)
        ax.text(min(m + hi + 1.5, 96), i, f"{t[k]['_hits']['any']}/{t[k]['_n']}", va="center", fontsize=8)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([f"{LABEL[k.split('|')[0]]} ({k.split('|')[1]})" for k in keys])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("items with at least one deterministic signal (%, Wilson 95% CI)")
    ax.set_title(f"Trigger coverage of the v{OUT.name[1:]} rules, test split", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_coverage.png", dpi=200)
    plt.close(fig)


def fig_versions(s: dict) -> None:
    v = s["_versions"]
    xs = [e["version"] for e in v]
    ys = [e["flagged_attack"] / 225 * 100 for e in v]
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    ax.step(xs, ys, where="post", color="#555", lw=1.2)
    colors = {"accepted": "#27ae60", "rejected": "#c0392b", "interrupted": "#999", None: "#333"}
    prev_op, n_pat = None, 0
    for e, y in zip(v, ys):
        ax.scatter(e["version"], y, color=colors.get(e["status"], "#333"), s=28, zorder=3)
        if (e["op"] or "").startswith(("add_pattern", "extend")):
            ax.annotate("pattern", (e["version"], y), textcoords="offset points",
                        xytext=(0, 7 + 9 * (n_pat % 2)), ha="center", fontsize=7, color="#c0392b")
            n_pat += 1
        elif e["op"] == "reseed" and prev_op != "reseed":
            ax.annotate("reseed", (e["version"], y), textcoords="offset points", xytext=(0, -11),
                        ha="center", fontsize=7)
        prev_op = e["op"]
    ax.set_xticks(xs)
    ax.set_xlabel("harness version")
    ax.set_ylabel("attack items flagged (%)")
    ax.set_ylim(25, 58)
    ax.set_title("Attack coverage across harness versions (green accepted, red rejected)", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_versions.png", dpi=200)
    plt.close(fig)


def fig_rules(s: dict) -> None:
    fires = sorted(s["_rule_fires"].items(), key=lambda kv: (kv[0].split(":")[0], -kv[1]))
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    colors = {"category": "#8e44ad", "jailbreak": "#d35400", "injection": "#16a085"}
    for i, (k, n) in enumerate(fires):
        g, pat = k.split(":", 1)
        ax.barh(i, n, color=colors[g], alpha=1.0 if n else 0.25)
        label = pat if len(pat) <= 48 else pat[:45] + "..."
        ax.text(-1, i, label, ha="right", va="center", fontsize=6.5, family="monospace")
        if n:
            ax.text(n + 0.5, i, str(n), va="center", fontsize=7)
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlim(0, max(n for _, n in fires) + 5)
    ax.set_xlabel("items matched across all 558 items (all splits); faded bars never fire")
    ax.set_title(f"Fire count per v{OUT.name[1:]} pattern", loc="right")
    for g, c in colors.items():
        ax.bar(0, 0, color=c, label=g)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.subplots_adjust(left=0.52, right=0.98, top=0.95, bottom=0.08)
    fig.savefig(OUT / "fig_rules.png", dpi=200)
    plt.close(fig)


def fig_obfuscation(t: dict) -> None:
    names = ["none", "leetspeak", "homoglyph", "zero_width"]
    vals = [pct(t["all|attack"])] + [pct(t[f"obf:{n}|attack"]) for n in names[1:]]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    ax.bar(names, [v[0] for v in vals], yerr=[[v[1] for v in vals], [v[2] for v in vals]],
           color=["#c0392b", "#aaa", "#aaa", "#aaa"], capsize=3)
    for i, v in enumerate(vals):
        ax.text(i, v[0] + v[2] + 1, f"{v[0]:.1f}%", ha="center", fontsize=8)
    ax.set_ylabel("attack items flagged (%)")
    ax.set_ylim(0, 55)
    ax.set_title("Coverage after surface transforms", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_obfuscation.png", dpi=200)
    plt.close(fig)


def main() -> int:
    global OUT
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=int, default=12)
    OUT = HERE.parent / "results" / "trigger_audit" / f"v{ap.parse_args().version}"
    s = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    fig_coverage(s["table"])
    fig_versions(s)
    fig_rules(s)
    fig_obfuscation(s["table"])
    for p in sorted(OUT.glob("fig_*.png")):
        print(p.relative_to(HERE.parent), p.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

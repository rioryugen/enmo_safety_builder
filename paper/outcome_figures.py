"""
Enmo Safety paper — outcome figures for the six-model evaluation and the v22 round.

Reads the committed results summaries (cli_test, open_weight_test, v22_test, v22_leet, baselines, and the
pairing summaries) and writes results/figures/fig_*.png. matplotlib only; no model calls.

    python paper/outcome_figures.py

Author:   m03 (Intel)
Revision: 1.0
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BUILDER = Path(__file__).resolve().parent.parent
R = BUILDER / "results"
OUT = R / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
NAME = {"copilot:claude-haiku-4.5": "Haiku 4.5", "copilot:claude-haiku-5.5": "Haiku 5.5",
        "copilot:mai-code-1.1-flash": "MAI Code 1.1 Flash", "local:qwen3.8-27B": "Qwen3.8 27B",
        "local:glm-5.3-flash": "GLM-5.3 Flash", "local:gemma4-31b": "Gemma 4 31B"}
COL = {"bare": "#9aa0a6", "spot": "#4c8bf5", "v12": "#d9534f", "v21": "#d9534f", "v22a": "#8e44ad",
       "v22b": "#27ae60", "v22c": "#16a085"}


def load(*parts: str) -> dict:
    return json.loads(Path(R, *parts).read_text(encoding="utf-8"))


def pct(x: float) -> float:
    return x * 100


def fig_models() -> None:
    cells, p = {}, {}
    for run in ("cli_test", "open_weight_test"):
        s = load(run, "summary.json")
        cells |= s["table"]
        p |= {k: v["p"] for k, v in s["mcnemar"].items()}
    models = sorted(NAME, key=lambda m: -cells[f"{m}|bare"]["unsafe"]["mean"])
    conds = [("bare", "No harness"), ("spot", "Spotlighting only"), ("v12", "Full harness (v12)")]
    fig, ax = plt.subplots(figsize=(7.4, 3.3))
    w = 0.26
    for j, (c, label) in enumerate(conds):
        xs = [i + (j - 1) * w for i in range(len(models))]
        ys = [pct(cells[f"{m}|{c}"]["unsafe"]["mean"]) for m in models]
        err = [[pct(cells[f"{m}|{c}"]["unsafe"]["mean"] - cells[f"{m}|{c}"]["unsafe"]["ci95"][0]) for m in models],
               [pct(cells[f"{m}|{c}"]["unsafe"]["ci95"][1] - cells[f"{m}|{c}"]["unsafe"]["mean"]) for m in models]]
        ax.bar(xs, ys, w, yerr=err, color=COL[c], label=label, capsize=2, error_kw={"lw": 0.8})
        if c == "v12":
            for x, y, m, e in zip(xs, ys, models, err[1]):
                if p.get(f"{m}|bare->v12", 1) < 0.05:
                    ax.text(x, y + e + 0.4, "*", ha="center", fontsize=13, fontweight="bold")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([NAME[m] for m in models], rotation=15, ha="right")
    ax.set_ylabel("unsafe rate on 225 attack items (%)")
    ax.set_title("Six policy models, one run per cell. * bare to v12 exact McNemar p < 0.05", loc="left", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_models.png", dpi=200)
    plt.close(fig)


def fig_tradeoff() -> None:
    t = load("v22_test", "summary.json")["table"]
    models = ["copilot:claude-haiku-5.5", "copilot:mai-code-1.1-flash", "local:gemma4-31b", "local:glm-5.3-flash"]
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    cols = ["#e67e22", "#2980b9", "#27ae60", "#8e44ad"]
    offsets = {"copilot:claude-haiku-5.5": (8, 8, "left"), "copilot:mai-code-1.1-flash": (-6, 7, "right"),
               "local:gemma4-31b": (-8, -15, "right"), "local:glm-5.3-flash": (-6, 7, "right")}
    for m, c in zip(models, cols):
        pt = {k: (pct(t[f"{m}|{k}"]["agent_refusal"]["mean"]), pct(t[f"{m}|{k}"]["agent_harm"]["mean"]))
              for k in ("v21", "v22a_noclauses", "v22b_calibrated")}
        ax.scatter(*pt["v21"], s=55, color=c, edgecolor="black", zorder=3)
        dx, dy, ha = offsets[m]
        ax.annotate(NAME[m], pt["v21"], textcoords="offset points", xytext=(dx, dy), fontsize=8, ha=ha, color=c)
        for k, ls in (("v22a_noclauses", "-"), ("v22b_calibrated", "--")):
            ax.annotate("", xy=pt[k], xytext=pt["v21"],
                        arrowprops={"arrowstyle": "->", "color": c, "lw": 1.3, "linestyle": ls, "alpha": 0.9})
    ax.plot([], [], "-", color="gray", label="v21 to v22a: clauses removed")
    ax.plot([], [], "--", color="gray", label="v21 to v22b: clause reworded")
    ax.scatter([], [], s=55, color="white", edgecolor="black", label="v21 (start of each arrow)")
    ax.set_xlabel("benign tool tasks refused (%)  worse >")
    ax.set_ylabel("harmful tool tasks completed (%)  worse >")
    ax.set_title("Removing or rewording the clauses lowers agentic harm on most models\nand raises benign refusal on all four", loc="left", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.set_xlim(10, 58)
    ax.set_ylim(8, 26)
    fig.tight_layout()
    fig.savefig(OUT / "fig_tradeoff.png", dpi=200)
    plt.close(fig)


def fig_evasion() -> None:
    t = load("v22_leet", "summary.json")["table"]
    conds = [("bare", "No harness"), ("v21", "v21"), ("v22b_calibrated", "v22b"), ("v22c_normalized", "v22c")]
    colors = [COL["bare"], COL["v21"], COL["v22b"], COL["v22c"]]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    for ax, m in zip(axes, ("copilot:claude-haiku-5.5", "copilot:mai-code-1.1-flash")):
        vals = [pct(t[f"{m}|{c}"]["agent_harm"]["mean"]) for c, _ in conds]
        bars = ax.bar(range(len(conds)), vals, color=colors)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.0f}%", ha="center", fontsize=8)
        ax.set_xticks(range(len(conds)))
        ax.set_xticklabels([c[1] for c in conds], fontsize=7.5)
        ax.set_title(NAME[m], loc="left", fontsize=9)
    axes[0].set_ylabel("harmful tool tasks completed (%)")
    fig.suptitle("Leetspeak-obfuscated attacks: v21's 'no signal detected' clause turns evasion into permission", x=0.01, ha="left", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig_evasion.png", dpi=200)
    plt.close(fig)


def fig_pairing() -> None:
    rows = []
    for run in ("cli_test", "open_weight_test"):
        s = load(run, "pairing", "summary.json")["table"]
        for k, v in s.items():
            if k.endswith(("|v12", "|v21")):
                rows.append((k, pct(v["attack_flagged"]["mean"]), pct(v["attack_unflagged"]["mean"]),
                             v["_bad"]["attack_flagged"], v["_n"]["attack_flagged"], v["_bad"]["attack_unflagged"], v["_n"]["attack_unflagged"]))
    rows.sort(key=lambda r: (r[0].split("|")[0], r[0]))
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for i, (k, f, u, fb, fn, ub, un) in enumerate(rows):
        ax.plot([f, u], [i, i], color="#bbb", lw=1.5, zorder=1)
        ax.scatter(f, i, color="#d9534f", s=40, zorder=3)
        ax.scatter(u, i, color="#4c8bf5", s=40, zorder=3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{NAME[k.split('|')[0]]}  {k.split('|')[1]}" for k, *_ in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.scatter([], [], color="#d9534f", label="attack items the rules flagged")
    ax.scatter([], [], color="#4c8bf5", label="attack items the rules missed")
    ax.set_xlabel("unsafe rate (%)")
    ax.set_title("Flagging does not select the items a model would fail on\n(Fisher exact p from 0.30 to 1.0 in all twelve cells)", loc="left", fontsize=9)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig_pairing.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_detectors() -> None:
    t = load("baselines", "summary.json")["table"]
    dets = [("enmo_v12", "Enmo v12", COL["v12"]), ("enmo_v22", "Enmo v22", COL["v22b"]), ("protectai_base_v2", "ProtectAI DeBERTa v2", "#4c8bf5")]
    benches = [("harmbench|attack", "HarmBench"), ("advbench|attack", "AdvBench"), ("jbb|attack", "JailbreakBench"),
               ("agentharm|attack", "AgentHarm"), ("injection|attack", "deepset\ninjections")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(8.2, 3.3), gridspec_kw={"width_ratios": [1.5, 1]})
    w = 0.27
    for j, (d, label, c) in enumerate(dets):
        xs = [i + (j - 1) * w for i in range(len(benches))]
        a.bar(xs, [pct(t[f"{d}:{k}"]["flag"]["mean"]) for k, _ in benches], w, color=c, label=label)
    a.set_xticks(range(len(benches)))
    a.set_xticklabels([x[1] for x in benches], fontsize=7.5)
    a.set_ylabel("attack items flagged (%)")
    a.set_title("Plain text, test split", loc="left", fontsize=9)
    a.legend(frameon=False, fontsize=7.5)
    tf = ["leetspeak", "homoglyph", "zero_width"]
    for j, (d, label, c) in enumerate(dets):
        xs = [i + (j - 1) * w for i in range(len(tf))]
        b.bar(xs, [pct(t[f"{d}:obf:{x}|attack"]["flag"]["mean"]) for x in tf], w, color=c)
        b.bar(xs, [pct(t[f"{d}:obf:{x}|benign"]["flag"]["mean"]) for x in tf], w, color="none", edgecolor="black", hatch="///", lw=0.6)
    b.set_xticks(range(len(tf)))
    b.set_xticklabels(["leetspeak", "homoglyph", "zero-width"], fontsize=7.5)
    b.set_title("Obfuscated (solid: attack, hatched: benign)", loc="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_detectors.png", dpi=200)
    plt.close(fig)


def main() -> int:
    for f in (fig_models, fig_tradeoff, fig_evasion, fig_pairing, fig_detectors):
        f()
    for p in sorted(OUT.glob("fig_*.png")):
        print(p.relative_to(BUILDER), p.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

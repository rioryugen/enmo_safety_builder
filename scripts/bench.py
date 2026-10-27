"""
Enmo Safety Harness — builder benchmark.

Measures the Enmo Safety harness and the builder, records the numbers in
benchmarks.json (append-only history), and publishes the latest numbers into
BOTH repo READMEs between marker comments, including the before/after safety
table produced by the evaluation lab (results/summary.json).

Flags:
    --measure            compute metrics, append to benchmarks.json, print
    --publish          compute + write the benchmark block into both READMEs
    --json             machine-readable metrics (no record, no publish)
    --root <dir>       builder root (default: this repo)
    --run <name>       lab run to publish: main -> results/, other -> results/<name>/

The benchmark block lives between `<!-- BEGIN BENCHMARK -->` and
`<!-- END BENCHMARK -->` markers in each README. --publish replaces ONLY that
region, so hand-written prose above and below the markers is never touched.
If a README has no markers, publish reports it and skips — it never clobbers.

Metrics are read from the canonical harness (../enmo_safety/) via enmo_lib, and from
the builder registry + scan ledger via builder.py. No third-party deps.

Author:   m03 (Intel)
Revision: 1.5

Revision History:
    1.0 — Initial version: harness + builder metrics, append-only benchmarks.json
          history, and marker-based publish into the harness and builder READMEs.
    1.1 — Richer README visualizations: ASCII bar charts for the component mix and
          context budget, a health scorecard, and a per-source scan-ledger table in
          the builder block. measure() now captures per-source scan rows.
    1.2 — Dashboard polish: fractional gauge bars for the component mix and context
          budget, a growth sparkline over the append-only history, a health letter
          grade, and a per-source status column (current / drift / never).
    1.3 — Landscape comparison scoreboard vs the ranked field, published in both
          READMEs. Enmo is measured against the curated field aggregate; the harness
          README shows the field generically (no source names), the builder README
          names the catalog. Data is read from the reference snapshot.
    1.4 — Safety builder: measures ../enmo_safety; publishes a SAFETY BEFORE/AFTER
          block (bare / v0 / vN per model) from results/summary.json and records
          the headline in benchmarks.json.
    1.5 — --run selects which lab run to publish; legend built from the run's
          conditions (spot, v8, v9, latest version).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN BENCHMARK -->"
END = "<!-- END BENCHMARK -->"
RECORD = "benchmarks.json"

SEVERITY = {
    "skill-missing-name": "BLOCKING", "skill-name-mismatch": "BLOCKING",
    "skill-missing-description": "BLOCKING", "command-broken-target": "BLOCKING",
    "hook-missing-script": "BLOCKING", "hook-no-script": "BLOCKING",
    "skill-weak-trigger": "MAJOR", "agent-missing-field": "MAJOR",
    "command-missing-description": "MAJOR", "command-no-target": "MAJOR",
    "rule-missing-description": "MAJOR", "rule-missing-applyTo": "MAJOR",
    "rule-pack-unlisted": "MAJOR", "catalog-missing": "MAJOR",
    "adapter-missing": "MAJOR", "adapter-drift": "MAJOR",
    "adapter-not-generated": "MINOR",
}


def find_root(start: Path) -> Path:
    """Walk up from *start* to the builder root (has sources.json)."""
    cur = Path(start).resolve()
    while True:
        if (cur / "sources.json").is_file():
            return cur
        parent = cur.parent
        if parent == cur:
            return start.resolve()
        cur = parent


BUILDER_ROOT = find_root(Path(__file__).resolve().parent)
WORKSPACE = BUILDER_ROOT.parent
CANON = WORKSPACE / "enmo_safety"
SAFETY_SUMMARY = BUILDER_ROOT / "results" / "summary.json"
RUN_NAME = "main"

# Reuse the canonical library and the builder's registry/ledger loaders.
sys.path.insert(0, str(CANON / "scripts"))
sys.path.insert(0, str(BUILDER_ROOT / "scripts"))

import enmo_lib as lib  # noqa: E402
import builder  # noqa: E402


def today() -> str:
    return datetime.date.today().isoformat()


def gaps(root: Path) -> list:
    """Unreferenced skills/agents — same rule inventory.py applies."""
    out = []
    cmds = lib.command_files(root)
    ags = lib.agent_files(root)
    sks = lib.skill_files(root)
    for sk in sks:
        name = sk.parent.name
        if not any(name in lib.read_text(p) for p in cmds + ags):
            out.append(("skill", name))
    for ag in ags:
        name = ag.name
        if not any(name in lib.read_text(p) for p in cmds + sks):
            out.append(("agent", name))
    return out


def measure(root: Path) -> dict:
    c = lib.counts(root)
    findings = lib.validate_structure(root)
    drift = lib.check_drift(root, WORKSPACE)
    footprint = lib.context_footprint(root, WORKSPACE)
    gap_list = gaps(root)

    sev = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0}
    for rule, _, _ in findings:
        sev[SEVERITY.get(rule, "MINOR")] += 1

    always = sum(n for load, _, n in footprint if load == "always")
    advertised = sum(n for load, _, n in footprint if load == "advertised")
    opt_in = sum(n for load, _, n in footprint if load == "opt-in")

    version = (root / "VERSION").read_text(encoding="utf-8").strip() \
        if (root / "VERSION").is_file() else "?"

    reg = builder.load_registry(BUILDER_ROOT)
    ledger = builder.load_ledger(BUILDER_ROOT)
    entries = ledger.get("sources", {})
    scanned = [n for n, e in entries.items() if e.get("scan_date")]
    last_scan = max((e.get("scan_date", "") for e in entries.values()),
                    default="")

    return {
        "date": today(),
        "enmo_build": version,
        "harness": {
            "agents": c["agents"], "skills": c["skills"],
            "commands": c["commands"], "rules": c["rules"],
            "rule_packs": len(c["rule_packs"]), "hooks": c["hooks"],
            "scripts": c["scripts"], "templates": c["templates"],
            "components": (c["agents"] + c["skills"] + c["commands"]
                           + c["rules"] + c["hooks"] + c["scripts"]
                           + c["templates"]),
            "findings": len(findings),
            "blocking": sev["BLOCKING"], "major": sev["MAJOR"],
            "minor": sev["MINOR"],
            "drift": len(drift), "gaps": len(gap_list),
            "context_always": always, "context_advertised": advertised,
            "context_opt_in": opt_in, "context_total": always + advertised + opt_in,
        },
        "builder": {
            "registered": len(reg.get("sources", [])),
            "scanned": len(scanned),
            "last_scan": last_scan,
            "source_rows": [
                {
                    "name": n,
                    "ref": e.get("ref", ""),
                    "commit": (e.get("upstream_commit", "") or "")[:7],
                    "scan_date": e.get("scan_date", ""),
                    "scan_time": e.get("scan_time", ""),
                    "changes": len(e.get("changes", [])),
                    "status": ("never" if not e.get("scan_date")
                               else "current" if e.get("upstream_commit")
                               == e.get("local_commit") else "drift"),
                }
                for n, e in sorted(entries.items())
            ],
        },
    }


FULL = "█"
FRACTIONS = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
SPARK = "▁▂▃▄▅▆▇█"


def gauge(count: int, width: int, scale: int) -> str:
    """A proportional bar with a fractional end block, capped at *width*."""
    value = count / max(scale, 1) * width
    full = int(value)
    idx = round((value - full) * 8)
    if idx == 8:
        full += 1
        idx = 0
    if full >= width:
        return FULL * width
    return FULL * full + FRACTIONS[idx]


def stacked_bar(parts: list, width: int) -> str:
    """A stacked bar of segments; segments sum to exactly *width*."""
    total = sum(p[0] for p in parts) or 1
    widths = [int(round(w / total * width)) for w, _ in parts]
    widths[-1] += width - sum(widths)
    return "".join(ch * w for (w, ch) in zip(widths, [p[1] for p in parts]))


def pct(n: int, total: int) -> int:
    return int(round(n / (total or 1) * 100))


def sparkline(values: list) -> str:
    """A mini trend line over a series, mapped to 8 block levels."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    return "".join(SPARK[7] if span == 0 else
                   SPARK[int(round((v - lo) / span * 7))] for v in values)


def grade(m: dict) -> str:
    """A letter grade from structural findings, drift, and gaps."""
    h = m["harness"]
    score = 100 - h["blocking"] * 20 - h["major"] * 5 - h["minor"] \
        - h["drift"] * 2 - h["gaps"] * 3
    if score >= 95:
        return "A"
    if score >= 85:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def history_components(root: Path) -> list:
    """Component counts across the append-only benchmark history."""
    path = root / RECORD
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [r["harness"]["components"] for r in data.get("history", [])
            if "harness" in r and "components" in r["harness"]]


def load_comparison(root: Path) -> dict:
    """Read the landscape comparison block from the reference snapshot."""
    path = root / "reference" / "docs" / "best-of-harnesses-snapshot.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data.get("comparison", {})


VERDICT_MARK = {"ahead": "* ahead", "applied": "+ parity", "na": "- n/a"}


def axis_bar(level: int, scale_len: int) -> str:
    """Filled/empty dots for an axis level on a scale of *scale_len* steps."""
    filled = min(level + 1, scale_len)
    return "o" * filled + "." * (scale_len - filled)


def block_comparison(comp: dict, source_line: str = "") -> str:
    """Render the landscape scoreboard. Generic when *source_line* is empty.

    The harness README passes no source_line (features-only, no source names);
    the builder README passes a line that names the curated catalog.
    """
    if not comp:
        return ""
    sb = comp.get("scoreboard", {})
    rows = sb.get("rows", [])
    axes = comp.get("axes", [])
    field = comp.get("field_total", 0)
    ahead = sb.get("enmo_ahead", 0)
    applied = sb.get("applied", 0)
    na = sb.get("na", 0)
    lines = [
        "```",
        f"LANDSCAPE SCOREBOARD - Enmo vs the ranked field of {field} harnesses",
        "",
        f"Enmo leads {ahead}  matches {applied}  n/a {na}",
        "",
        f"{'CAPABILITY':<24} {'THE FIELD':<20} {'ENMO':<20} VERDICT",
    ]
    for r in rows:
        cap = r["capability"][:23]
        fld = r["field"][:19]
        en = r["enmo"][:19]
        mark = VERDICT_MARK.get(r.get("verdict", ""), "")
        lines.append(f"{cap:<24} {fld:<20} {en:<20} {mark}")
    lines += ["", "AXIS LEVELS (Enmo on the field scale)", ""]
    for a in axes:
        bar = axis_bar(a["enmo_level"], len(a["scale"]))
        lines.append(f"{a['axis']:<18} {bar}  {a['note']}")
    lines.append("```")
    if source_line:
        lines += ["", source_line]
    return "\n".join(lines)


def block_harness(m: dict, history: list, landscape: dict) -> str:
    h = m["harness"]
    comp = [
        ("Agents", h["agents"]), ("Skills", h["skills"]),
        ("Commands", h["commands"]), ("Rules", h["rules"]),
        ("Hooks", h["hooks"]), ("Scripts", h["scripts"]),
        ("Templates", h["templates"]),
    ]
    scale = max(c for _, c in comp)
    total = h["context_total"]
    ctx_scale = max(h["context_always"], h["context_advertised"], h["context_opt_in"])
    ctx_rows = [
        ("always-loaded", h["context_always"]),
        ("advertised", h["context_advertised"]),
        ("opt-in", h["context_opt_in"]),
    ]
    health = [
        ("Structural findings", h["findings"]),
        ("Blocking findings", h["blocking"]),
        ("Adapter drift", h["drift"]),
        ("Unreferenced gaps", h["gaps"]),
    ]
    lines = [
        "## Benchmarks",
        "",
        "Auto-published by `enmo_safety_builder/scripts/bench.py` — do not edit this "
        "block by hand.",
        "",
        f"**Enmo Safety build {m['enmo_build']}** · measured {m['date']} · "
        f"**{h['components']} components** · health **{grade(m)}** · "
        f"**{h['context_always']:,} bytes always-loaded**",
        "",
        "```",
        f"COMPONENT MIX — {h['components']} total",
        "",
    ]
    for name, c in comp:
        lines.append(f"{name:<9} {c:>3} │ {gauge(c, 40, scale)}")
    lines += [
        "```",
        "",
        "```",
        f"CONTEXT BUDGET — {total:,} bytes",
        "",
    ]
    for label, v in ctx_rows:
        lines.append(f"{label:<12} {gauge(v, 28, ctx_scale):<28} "
                     f"{v:>6,}  {pct(v, total):>2}%")
    lines += [
        "```",
        "",
        "```",
        f"GROWTH — components over {len(history)} recorded runs",
        "",
        sparkline(history) if history else "(first recorded run)",
        "",
        f"components {history[0] if history else h['components']} "
        f"→ {h['components']}",
        "```",
        "",
        "| Health | Status |",
        "| --- | --- |",
    ]
    for label, v in health:
        mark = "✅ clean" if v == 0 else f"⚠ {v}"
        lines.append(f"| {label} | {mark} |")
    lines.append(
        f"| Source coverage | {m['builder']['scanned']} of "
        f"{m['builder']['registered']} scanned |")
    lines += ["", block_safety(load_safety()), ""]
    return "\n".join(lines)


def load_safety() -> dict:
    path = SAFETY_SUMMARY if RUN_NAME == "main" else BUILDER_ROOT / "results" / RUN_NAME / "summary.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


SAFETY_HEADLINE = (("unsafe", "Unsafe (harm+inject)"), ("jbb_asr", "Jailbreak ASR"),
                   ("injection", "Injection success"), ("over_refusal", "XSTest over-refusal"),
                   ("refuse_benign", "Benign refusal"))


def block_safety(s: dict) -> str:
    """Before/after safety table from the lab's results/summary.json."""
    if not s:
        return ""
    conds = s.get("conditions", [])
    rpc = s.get("runs_per_cell", {})
    runs = ", ".join(f"{m.split(':', 1)[1]} {max(v for k, v in rpc.items() if k.startswith(m + '|'))}"
                     for m in s["models"] if any(k.startswith(m + "|") for k in rpc)) or str(s["runs"])
    lines = ["```", f"SAFETY BEFORE/AFTER — run '{s['run']}', {len(s['models'])} models, "
             f"{s['items_per_condition']} items, runs: {runs} (mean %, lower is better)", ""]
    head = f"{'MODEL':<20} {'METRIC':<21}" + "".join(f"{c:>8}" for c in conds)
    lines.append(head)
    for model in s["models"]:
        for key, label in SAFETY_HEADLINE:
            cells = []
            for c in conds:
                v = s["table"].get(f"{model}|{c}", {}).get(key, {}).get("mean")
                cells.append(f"{'n/a' if v is None else f'{v*100:.1f}':>8}")
            lines.append(f"{model.split(':', 1)[1][:19]:<20} {label:<21}" + "".join(cells))
        lines.append("")
    legend = {"bare": "no harness", "spot": "spotlighting only", "v0": "seed harness",
              "v8": "gen-1 evolved", "v9": "gen-2 seed",
              "vN": f"latest evolved (v{s['vN_version']})" if s.get("vN_version") is not None
              else "self-evolved harness"}
    lines += [" · ".join(f"{c} = {legend.get(c, c)}" for c in conds), "```"]
    return "\n".join(lines)


def block_builder(m: dict, comp: dict) -> str:
    b = m["builder"]
    h = m["harness"]
    reg = b["registered"]
    scanned = b["scanned"]
    rows = b["source_rows"]
    cov = [(reg, "█"), (max(reg - scanned, 0), "░")]
    lines = [
        "## Benchmarks",
        "",
        "Auto-published by `scripts/bench.py` — do not edit this block by hand.",
        "",
        f"**Enmo Safety build {m['enmo_build']}** · measured {m['date']} · "
        f"**{scanned}/{reg} sources scanned** · last scan "
        f"{b['last_scan'] or 'never'}",
        "",
        "```",
        f"SOURCE COVERAGE — {scanned} of {reg} scanned",
        "",
        stacked_bar(cov, 40),
        "",
        f"█ scanned   {scanned}",
        f"░ registered, not scanned  {reg - scanned}",
        "```",
        "",
        "| Source | Ref | Commit | Last scan | Changes | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    status_mark = {"current": "✅ current", "drift": "⚠ drift", "never": "⏳ never"}
    for r in rows:
        t = r["scan_time"][11:] if r["scan_time"] else ""
        scan = f"{r['scan_date']} {t}".strip() if r["scan_date"] else "never"
        commit = f"`{r['commit']}`" if r["commit"] else "—"
        status = status_mark.get(r.get("status", ""), "")
        lines.append(
            f"| {r['name']} | {r['ref']} | {commit} | {scan} | "
            f"{r['changes']} | {status} |")
    lines += [
        "",
        f"**Harness feed:** {h['components']} components · "
        f"{h['findings']} findings · {h['context_always']:,} bytes "
        f"always-loaded (+{h['context_advertised']:,} advertised, "
        f"{h['context_opt_in']:,} opt-in).",
        "",
        block_safety(load_safety()),
        "",
        "Full append-only history: `benchmarks.json`.",
    ]
    return "\n".join(lines)


def publish_readme(path: Path, inner: str) -> str:
    """Replace the region between the markers. Never touch hand-written prose."""
    if not path.is_file():
        return f"{path.name}: README not found — skipped"
    text = path.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return f"{path.name}: no benchmark markers — skipped (add them once)"
    i = text.index(BEGIN) + len(BEGIN)
    j = text.index(END)
    new = text[:i] + "\n" + inner + "\n" + text[j:]
    path.write_text(new, encoding="utf-8")
    return f"{path.name}: published"


def record(root: Path, m: dict) -> None:
    path = root / RECORD
    data = {"history": []}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"history": []}
    data.setdefault("history", []).append(m)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enmo builder benchmark")
    parser.add_argument("--measure", action="store_true",
                        help="compute metrics, append to benchmarks.json, print")
    parser.add_argument("--publish", action="store_true",
                        help="compute + write the benchmark block into both READMEs")
    parser.add_argument("--json", action="store_true", help="machine-readable metrics")
    parser.add_argument("--root", default=None, help="builder root")
    parser.add_argument("--run", default="main", help="results run to publish (results/<run>/)")
    args = parser.parse_args()
    global RUN_NAME
    RUN_NAME = args.run

    root = Path(args.root) if args.root else BUILDER_ROOT
    m = measure(CANON)
    safety = load_safety()
    if safety:
        m["safety"] = {"run": safety["run"], "models": safety["models"], "runs": safety["runs"],
                       "headline": {k: {c: safety["table"].get(f"{mo}|{c}", {}).get(key, {}).get("mean")
                                        for c in safety["conditions"]}
                                    for mo in safety["models"] for key, _ in SAFETY_HEADLINE
                                    for k in [f"{mo}|{key}"]}}

    if args.json:
        print(json.dumps(m, indent=2, sort_keys=True))
        return 0

    if args.publish:
        record(root, m)
        hist = history_components(root)
        comp = load_comparison(root)
        r1 = publish_readme(CANON / "README.md", block_harness(m, hist, comp))
        r2 = publish_readme(root / "README.md", block_builder(m, comp))
        print(f"Enmo Safety build {m['enmo_build']} · {m['date']}")
        print(f"  {r1}")
        print(f"  {r2}")
        print(f"Record appended to {RECORD}.")
        return 0

    # default and --measure both compute; --measure also records
    record(root, m)
    h = m["harness"]
    b = m["builder"]
    print(f"Enmo build {m['enmo_build']} · measured {m['date']}")
    print(f"  harness: {h['agents']} agents, {h['skills']} skills, "
          f"{h['commands']} commands, {h['rules']} rules ({h['rule_packs']} packs), "
          f"{h['hooks']} hooks, {h['scripts']} scripts, {h['templates']} templates")
    print(f"  {h['components']} components · {h['findings']} findings "
          f"({h['blocking']} blocking) · {h['drift']} drift · {h['gaps']} gaps")
    print(f"  context: {h['context_always']:,} always-loaded bytes "
          f"(+{h['context_advertised']:,} advertised, {h['context_opt_in']:,} opt-in)")
    print(f"  builder: {b['registered']} registered, {b['scanned']} scanned, "
          f"last scan {b['last_scan'] or 'never'}")
    print(f"Record appended to {RECORD}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

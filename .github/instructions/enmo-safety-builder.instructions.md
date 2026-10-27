---
description: How to work inside the Enmo Safety builder (sources, evaluation lab, paper).
applyTo: "enmo_safety_builder/**"
---

# Enmo Safety Builder — Copilot rules

This folder stages upstream sources, runs the safety evaluation lab, and holds
the paper. The canonical safety harness is in `../enmo_safety/`.

- **Re-clone from Enmo with the tool.** `python scripts/clone_from_enmo.py`
  re-projects Enmo into `../enmo_safety` with the `safety-` namespace. It never
  touches safety-only files or files listed in its KEEP_LOCAL set.
- **Sources.** `sources.json` declares git sources (`sources`), benchmark
  datasets (`datasets`) and the papers the design follows (`papers`). Manage
  clones with `scripts/builder.py` (`--update`, `--check`, `--note`). A source
  may set `path` (the humanizer lives in `integrations/humanizer`).
- **Lab order.** `lab/bench_data.py` (splits) -> `lab/evolve.py` (self-evolution
  on evolve/dev splits, `--promote` to canonical) -> `lab/run_eval.py` (test
  split, bare / v0 / vN) -> `lab/analyze.py` (results/) ->
  `python scripts/bench.py --publish` (README blocks).
- **Test split is sacred.** Only `run_eval.py --split test` reads it. Evolution,
  reflection and red-teaming never do.
- **Data handling.** `lab/data`, `lab/runs`, `lab/cache` are gitignored. Commit
  aggregates in `results/`, never raw harmful completions. Credentials come from
  env vars or the Copilot/gh login only.
- **Paper numbers are generated.** Every number in `paper/` must come from
  `results/summary.json`; `paper/build_tables.py` regenerates the tables.
- **Deps.** The lab is stdlib + Node (Copilot SDK bridge); no pip packages needed.

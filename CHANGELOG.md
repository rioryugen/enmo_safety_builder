# Changelog

All notable changes to the Enmo Safety builder. Versioned in lockstep with
Enmo Safety.

## [0.2.0] - 2026-10-27

### Added
- `lab/evolve.py` 2.0: per-model paired gate (`--min-effect`, `--dev-runs`),
  probe split, `--regate`, `--promote`, redacted evidence for the reflector.
- `lab/bench_data.py` 1.1 probe split; `lab/clean_sessions.py`.
- `results/fresh/`: second-iteration evaluation on test items 26-50 (bare,
  spotlighting only, v8, v9, v12; two runs, spotlighting one).
- Paper section 5.5 (second iteration).

### Changed
- Lab state lives outside OneDrive (`%LOCALAPPDATA%\enmo_safety_lab`).
- `lab/providers.py` 1.2 (rate limit, platform blocks, retry log),
  `lab/judge.py` 1.2 (fallback judge), `lab/copilot_bridge.mjs` 1.1 (deletes
  its sessions), `lab/analyze.py` 1.1 (complete runs only, new conditions,
  per-run results folder).
- `scripts/bench.py` 1.5: `--run` and a legend built from the run's conditions.
- `paper/check_numbers.py` 1.1 reads every results summary.

## [0.1.0] - 2026-10-27

### Added
- `scripts/clone_from_enmo.py` 1.0: namespaced, re-runnable clone of Enmo into
  `../enmo_safety`.
- `scripts/builder.py` 1.4: per-source `path` (integrations), registry keys
  beyond `sources` survive `--add`, build read from `../enmo_safety/VERSION`.
- `scripts/bench.py` 1.4: measures `../enmo_safety`, publishes the safety
  before/after block.
- `sources.json`: enmo, humanizer, HarmBench, llm-attacks, jailbreakbench,
  xstest; `datasets` and `papers` registries.
- `integrations/humanizer` (git clone, MIT).
- `lab/`: benchmark splits, Copilot SDK bridge, providers with cache, two-stage
  judge, self-evolution loop, evaluation matrix, analysis.
- `results/` and `paper/`.

### Removed
- Enmo-specific reference material (`reference/`), which belongs to `enmo_builder`.

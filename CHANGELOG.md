# Changelog

All notable changes to the Enmo Safety builder. Versioned in lockstep with
Enmo Safety.

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

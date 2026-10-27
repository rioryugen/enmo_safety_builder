# Enmo Safety Builder

Sources, evaluation lab, and paper for the
[Enmo Safety](../enmo_safety/README.md) self-evolving safety harness.

## Contents

1. [Layout](#layout)
2. [Pipeline](#pipeline)
3. [Sources](#sources)
4. [Models](#models)
5. [Benchmarks](#benchmarks)
6. [Paper](#paper)
7. [Version history](#version-history)

## Layout

```
enmo_safety_builder/
  sources.json          git sources, benchmark datasets, papers
  scan-ledger.json      what was taken from each source, and when
  benchmarks.json       append-only harness + safety metric history
  scripts/
    clone_from_enmo.py  re-project Enmo into ../enmo_safety with the safety- namespace
    builder.py          clone / check / update / note sources
    bench.py            measure + publish README benchmark blocks
    release.py          per-version tags and releases
  integrations/
    humanizer/          git clone (MIT), restored with builder.py --clone humanizer
  lab/
    bench_data.py       download + seeded, stratified, disjoint splits
    copilot_bridge.mjs  Copilot SDK bridge (model discovery + chat)
    providers.py        Copilot SDK + Octagram clients, response cache
    judge.py            heuristic + cross-model LLM judge, audit sample
    evolve.py           self-evolution loop (evolve/dev splits only)
    run_eval.py         bare / v0 / vN matrix on the held-out test split
    metrics.py          metric definitions
    analyze.py          mean ± std, bootstrap CIs, McNemar, kappa, SVG figures
  results/              summary.json, tables.md, fig_*.svg (committed aggregates)
  paper/                paper.md, paper.tex, refs.bib, generated tables
```

## Pipeline

```
python lab/bench_data.py                       # splits: test 50 / evolve 20 / dev 20 per benchmark
python lab/evolve.py --rounds 5 --promote      # evolve on failures, promote vN into ../enmo_safety/harness
python lab/run_eval.py --runs 3                # bare vs v0 vs vN on the held-out test split
python lab/analyze.py                          # results/
python scripts/bench.py --publish              # README benchmark blocks
python paper/build_tables.py                   # paper tables + number macros from results/summary.json
```

Every model response is cached under `lab/cache/` keyed by model, system
prompt, user prompt and run index, so re-analysis is free and an interrupted
run resumes where it stopped.

## Sources

| Source | Kind | Licence | Used for |
| --- | --- | --- | --- |
| enmo | git | — | parent harness, cloned with `clone_from_enmo.py` |
| humanizer | git → `integrations/` | MIT | paper prose pass (`safety-paper-humanize`) |
| HarmBench | git + CSV | MIT | harmful-behaviour prompts |
| llm-attacks | git + CSV | MIT | AdvBench harmful behaviours |
| jailbreakbench | git + HF | MIT | JBB-Behaviors goals |
| xstest | git + HF | CC-BY-4.0 | over-refusal prompts |
| AgentHarm | HF | MIT + usage terms | agentic tool-misuse tasks |
| deepset/prompt-injections | HF | Apache-2.0 | injection documents |

HarmBench and AdvBench mirrors on Hugging Face are gated, so the lab reads the
original public CSVs. The other four come from the Hugging Face datasets-server
API (`HF_TOKEN` is used if set, never stored).

## Models

Models are discovered live through the GitHub Copilot SDK (`listModels`, then a
ping). Octagram Swift 1.5 (local, OpenAI-compatible) is added when
`OCTAGRAM_API_KEY` is set in the environment or the Windows user environment.
The GitHub Models REST API is not used: on this network a proxy answers every
request with a constant `OK`.

## Benchmarks

<!-- BEGIN BENCHMARK -->
## Benchmarks

Auto-published by `scripts/bench.py` — do not edit this block by hand.

**Enmo Safety build 0.2.0** · measured 2026-10-27 · **6/6 sources scanned** · last scan 2026-10-27

```
SOURCE COVERAGE — 6 of 6 scanned

████████████████████████████████████████

█ scanned   6
░ registered, not scanned  0
```

| Source | Ref | Commit | Last scan | Changes | Status |
| --- | --- | --- | --- | --- | --- |
| HarmBench | main | `8e1604d` | 2026-10-27 14:01:40 | 0 | ✅ current |
| enmo | master | `fb0cbf0` | 2026-10-27 14:01:06 | 1 | ✅ current |
| humanizer | main | `8c307f3` | 2026-10-27 14:01:08 | 1 | ✅ current |
| jailbreakbench | main | `23dbdf6` | 2026-10-27 14:01:52 | 0 | ✅ current |
| llm-attacks | main | `098262e` | 2026-10-27 14:01:45 | 0 | ✅ current |
| xstest | main | `d7bb5bd` | 2026-10-27 14:01:59 | 0 | ✅ current |

**Harness feed:** 73 components · 0 findings · 5,141 bytes always-loaded (+4,282 advertised, 8,581 opt-in).

```
SAFETY BEFORE/AFTER — run 'fresh', 2 models, 150 items, runs: claude-haiku-4.5 2, gpt-5.3-codex 2 (mean %, lower is better)

MODEL                METRIC                   bare    spot      v8      v9      vN
claude-haiku-4.5     Unsafe (harm+inject)      3.1     0.0     3.6     0.9     0.0
claude-haiku-4.5     Jailbreak ASR             0.0     0.0     8.0     2.0     0.0
claude-haiku-4.5     Injection success        14.0     0.0     0.0     0.0     0.0
claude-haiku-4.5     XSTest over-refusal       4.0     4.0     0.0     0.0     0.0
claude-haiku-4.5     Benign refusal           17.1    15.8    19.7    22.4    21.1

gpt-5.3-codex        Unsafe (harm+inject)      4.5     2.7     7.1     5.8     5.4
gpt-5.3-codex        Jailbreak ASR             0.0     0.0     4.0     4.0     2.0
gpt-5.3-codex        Injection success        18.0    12.0    12.0    12.0    10.0
gpt-5.3-codex        XSTest over-refusal       0.0     0.0     0.0     0.0     0.0
gpt-5.3-codex        Benign refusal            0.0     0.0     0.0     1.3     0.0

bare = no harness · spot = spotlighting only · v8 = gen-1 evolved · v9 = gen-2 seed · vN = latest evolved (v12)
```

Full append-only history: `benchmarks.json`.
<!-- END BENCHMARK -->

## Paper

`paper/paper.md` (readable) and `paper/paper.tex` (arXiv style). Tables and
every quoted number are generated from `results/summary.json`.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| 0.1.0 | 2026-10-27 | Builder cloned from enmo_builder; safety sources, lab, results, paper |

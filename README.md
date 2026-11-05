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
    ecc/                git clone (MIT), restored with builder.py --clone ecc
  lab/
    bench_data.py       download + seeded, stratified, disjoint splits
    copilot_bridge.mjs  Copilot SDK bridge (model discovery + chat)
    providers.py        Copilot SDK + Octagram clients, response cache
    judge.py            heuristic + cross-model LLM judge, audit sample
    baselines.py        public detector baselines (ProtectAI DeBERTa, Rebuff, Vigil) on the test split
    pairing.py          per-item pairing of harness activation with judged outcomes for a run
    variants.py         loads candidates/<name> harnesses (prototype area; winners are promoted to enmo_safety)
    make_candidates.py  rebuilds the v22 candidates from the v21 snapshot
    evolve.py           self-evolution loop (evolve/dev splits only)
    run_eval.py         bare / v0 / vN matrix on the held-out test split
    metrics.py          metric definitions
    analyze.py          mean ± std, bootstrap CIs, McNemar, kappa, SVG figures
  results/              summary.json, tables.md, fig_*.svg (committed aggregates)
  paper/                paper.md, paper.tex, refs.bib, generated tables; trigger_audit.py, fold_audit.py,
                        outcome_figures.py (results/figures/fig_*.png), md2pdf.py
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
| ecc | git → `integrations/` | MIT | paper research/verification skills (deep-research, literature-review, scholar-evaluation, article-writing, verification-loop) |
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
ping). The SDK is installed locally with `npm install @github/copilot-sdk`
inside `lab/` (gitignored) and drives the installed Copilot CLI; the bridge
also honours `COPILOT_SDK_PATH`. Octagram Swift 1.5 (local, OpenAI-compatible) is added when
`OCTAGRAM_API_KEY` is set in the environment or the Windows user environment.
The GitHub Models REST API is not used: on this network a proxy answers every
request with a constant `OK`.

## Benchmarks

<!-- BEGIN BENCHMARK -->
## Benchmarks

Auto-published by `scripts/bench.py` — do not edit this block by hand.

**Enmo Safety build 0.3.0** · measured 2026-10-28 · **6/6 sources scanned** · last scan 2026-10-27

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
SAFETY BEFORE/AFTER — run 'holdout', 2 models, 290 items, runs: claude-haiku-4.5 1, gpt-5.3-codex 1 (mean %, lower is better)

MODEL                METRIC                   bare    spot      vN     v19
claude-haiku-4.5     Unsafe (harm+inject)      2.8     0.5     0.5     0.5
claude-haiku-4.5     Jailbreak ASR             0.0     0.0     0.0     0.0
claude-haiku-4.5     Injection success        10.0     0.0     0.0     0.0
claude-haiku-4.5     XSTest over-refusal       8.0     8.0     4.0     4.0
claude-haiku-4.5     Benign refusal           28.0    28.0    28.0    22.7

gpt-5.3-codex        Unsafe (harm+inject)      2.3     2.3     1.9     0.0
gpt-5.3-codex        Jailbreak ASR             5.0     5.0     2.5     0.0
gpt-5.3-codex        Injection success         0.0     0.0     0.0     0.0
gpt-5.3-codex        XSTest over-refusal       4.0     4.0     4.0     2.0
gpt-5.3-codex        Benign refusal           13.3    13.3     5.3     5.3

bare = no harness · spot = spotlighting only · vN = latest (v12) · v19 = gen-3d seed (gate-rejected, diagnostic)
```

Full append-only history: `benchmarks.json`.
<!-- END BENCHMARK -->

## Paper

`paper/paper.md` (readable) and `paper/paper.tex` (arXiv style). Tables and
every quoted number are generated from `results/summary.json`.

Follow-up drafts: [`paper/enmo_safety_v0.1.md`](paper/enmo_safety_v0.1.md),
[`paper/trigger_coverage_v0.1.md`](paper/trigger_coverage_v0.1.md),
[`paper/enmo_safety_cross_model.md`](paper/enmo_safety_cross_model.md), and
[`paper/trigger_coverage_audit.md`](paper/trigger_coverage_audit.md). The v0.1
drafts apply the Humanizer 3.1.0 prose pass; the trigger-coverage v0.1 was
researched with the ECC literature-review and scholar-evaluation skills and
its numbers come from `python paper/trigger_audit.py` (static rule activation
on every split and every harness version, dead-rule census, surface-transform
robustness, ledger join; no model calls; writes
`results/trigger_audit/v<N>/summary.json`; `paper/trigger_figures.py` draws the
figures; tests in `tests/test_trigger_audit.py`). `python lab/baselines.py`
(rule-based) and `python lab/baselines.py --models` (Hugging Face classifiers)
benchmark public detectors on the same items into `results/baselines/`; the
Tavily search log behind the related-work section is
`results/baselines/search_log.json`. Harness v20 and v21 were applied through
`safety_evolve.py` from dev/probe evidence only and are ledgered as
`applied_offline`: the model gate has not run on them.
`python paper/check_numbers.py <draft.md>` verifies any draft's percentages
against the results files. `python paper/md2pdf.py paper/<draft>.md` renders a
draft to PDF through headless Edge/Chrome (no TeX needed; PDFs are gitignored
build output). Neither draft reports a new inference run.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| 0.1.0 | 2026-10-27 | Builder cloned from enmo_builder; safety sources, lab, results, paper |
| 0.2.0 | 2026-11-04 | Trigger-coverage audit, public detector baselines, Copilot CLI provider via local SDK install, `cli_test` and `open_weight_test` runs (3 + 3 models x 4 conditions x 300 items) with per-item pairing, `local:` provider for open-weight models behind an OpenAI-compatible endpoint (`LOCAL_LLM_URL`, `LOCAL_LLM_API_KEY`; no default URL), harness v20/v21 applied offline, two v0.1 paper drafts with PDFs |
| 0.3.0 | 2026-11-05 | Candidate mechanism (`candidates/`, `lab/variants.py`, `lab/make_candidates.py`, `run_eval --transform`), clause ablation and obfuscated-attack runs (`v22_test`, `v22_leet`), `paper/fold_audit.py`; winning candidate promoted to `enmo_safety` as the gen4 seed (harness v22: calibrated clause + `variant.normalize`) |

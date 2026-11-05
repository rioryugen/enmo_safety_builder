# When Does an External Safety Harness Help?

> **Superseded.** This early working draft (2 November 2026) is kept for history. The current versions are [trigger_coverage_v0.1.md](trigger_coverage_v0.1.md), [enmo_safety_v0.1.md](enmo_safety_v0.1.md) and [paper.md](paper.md).

**Working draft — based on the repository's existing aggregate results; not a new model run.**

## Abstract

Deployers who cannot change model weights often rely on prompts and runtime
wrappers to reduce unsafe behavior. We study Enmo Safety, a model-agnostic
harness that assesses inputs, retrieves safety guidance, spotlights untrusted
documents, guards some high-risk outputs, and accepts only bounded,
ledgered updates that pass a per-model development gate. The existing
evaluation compares an unprotected baseline, spotlighting alone, and evolved
harness versions across six public safety benchmarks. On a 290-item holdout,
the v12 harness reduced the measured unsafe rate from 2.8% to 0.5% for Claude
Haiku 4.5 and from 2.3% to 1.9% for GPT-5.3-Codex. Benign refusal was unchanged
for Haiku (28.0%); for GPT-5.3-Codex it fell from 13.3% to 5.3%. Spotlighting
alone matched the harness on Haiku and matched the bare model on GPT-5.3-Codex.
None of the paired comparisons was statistically significant, and each
holdout condition was run once. These results do not establish a general
safety improvement. They instead show why wrapper changes need per-model
gates, a low-cost baseline, and fresh evaluation: a longer or self-evolved
prompt is not automatically safer than marking untrusted content as data.

## 1. Research question

When a deployer cannot fine-tune a model, do bounded changes to an external
safety harness improve safety and utility beyond a simpler spotlighting
baseline, and do those changes transfer across models?

## 2. System and scope

Enmo Safety is an external wrapper; it does not modify model weights and makes
no network calls at inference time. The runtime assesses prompt text with
deterministic patterns, selects request-relevant guidance, marks supplied
untrusted documents, and may replace procedural replies when input risk is
high. Updates are size-bounded, validated, snapshotted, and ledgered. The
Builder accepts an update only when its paired development evaluation meets
the safety and benign-refusal constraints for each policy model.

The novelty claim is deliberately narrow. SafeEvolve
([arXiv:2609.02786](https://huggingface.co/papers/2609.02786)) also studies
auditable harness evolution, but couples it with policy training. SafeEvalAgent
([arXiv:2509.26100](https://huggingface.co/papers/2509.26100)) already studies
self-evolving safety evaluation. Enmo's distinct setting is a small,
weight-agnostic wrapper under restricted model access; this study is an
empirical evaluation of that setting, not a claim to be the first
self-evolving safety system.

## 3. Evaluation

The existing Builder uses HarmBench, AdvBench, JailbreakBench, XSTest,
AgentHarm, and deepset prompt-injections. Conditions include a bare model,
spotlighting only, and versioned harnesses. The reported holdout contains 290
items and was not used by the evolution loop. It covers two models exposed by
the evaluation environment. AgentHarm actions are represented as text tool
calls rather than executed in a tool environment.

The primary outcome is the repository's combined unsafe rate over harmful,
agentic-harmful, and injection prompts. Benign refusal is reported separately.
Comparisons use item-paired outcomes and exact McNemar tests. Since the holdout
was run once per model and condition, the estimates are descriptive and have
limited power.

## 4. Results

| Model | Condition | Unsafe rate | Benign refusal |
|---|---|---:|---:|
| Claude Haiku 4.5 | Bare | 2.8% | 28.0% |
| Claude Haiku 4.5 | Spotlighting only | 0.5% | 28.0% |
| Claude Haiku 4.5 | v12 | 0.5% | 28.0% |
| GPT-5.3-Codex | Bare | 2.3% | 13.3% |
| GPT-5.3-Codex | Spotlighting only | 2.3% | 13.3% |
| GPT-5.3-Codex | v12 | 1.9% | 5.3% |

The paired comparisons were not significant (Haiku bare versus v12, *p* = 0.23;
GPT-5.3-Codex bare versus v12, *p* = 0.09). A rejected redesign performed
better on the GPT-5.3-Codex holdout than the promoted version, but it had been
rejected by the development gate after a harm increase on one model. One
holdout run is insufficient to reverse that decision.

## 5. Discussion

The data support conditional, not universal, conclusions. Spotlighting was
competitive with the larger harness on this holdout. The evolved harness
reduced benign refusal for one model while slightly reducing measured unsafe
behavior, but the result is not statistically conclusive. Earlier repository
experiments also show that clauses which help one model can increase harmful
compliance on another. Model-specific acceptance gates are therefore part of
the method, not an optional optimization.

The main missing test is robustness to unseen attack patterns and agent
artifacts. WARD
([arXiv:2605.15030](https://huggingface.co/papers/2605.15030)) evaluates
adaptive prompt-injection defenses under distribution shift. MalSkillBench
([arXiv:2606.07131](https://huggingface.co/papers/2606.07131)) evaluates
runtime-verified malicious skills that combine instructions and executable
behavior. Neither setting is represented by the current text-rendered
benchmark matrix.

## 6. Limitations and next experiment

The study has two models, a single holdout run, limited sample sizes, no human
adjudication, and no execution of tool actions. Some prompts are blocked by
the serving platform. The judge was revised during the project, so results
from different judge versions are not directly comparable. The next
experiment should use multiple fresh seeds, a blinded human audit of judge
labels, adaptive out-of-distribution injections, and runtime-verified skill
tasks. Agentic Benchmark Checklist
([arXiv:2507.02825](https://huggingface.co/papers/2507.02825)) should be applied
before interpreting task outcomes.

## Conclusion

The current evidence does not justify claiming that Enmo Safety generally
improves model safety. It supports a narrower result: a bounded external
harness can be evaluated without weight access, but its effect depends on the
model and may not exceed a simpler spotlighting baseline. Larger, independent
holdouts and realistic tool execution are required before making stronger
claims.

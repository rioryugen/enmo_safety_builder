# Activation Coverage Is Not Safety

> **Superseded.** This early working draft (2 November 2026) is kept for history. The current versions are [trigger_coverage_v0.1.md](trigger_coverage_v0.1.md), [enmo_safety_v0.1.md](enmo_safety_v0.1.md) and [paper.md](paper.md).

**Exploratory working draft — static input-trigger audit; no model outputs were generated.**

## Abstract

Safety wrappers often report outcome metrics without showing how often their
input assessment actually activates. We define *trigger coverage* as the
fraction of benchmark items that activate at least one Enmo Safety harm,
jailbreak, or injection signal, and audit the current v12 rules on the Builder's
seeded 300-item test split. The rules activated on 87 of 225 attack items
(38.7%) and on 4 of 75 benign items (5.3%). Coverage varied by benchmark:
14% for deepset prompt-injections, 16% for AgentHarm harmful tasks, and 58%
for JailbreakBench. These figures are not attack-success rates: spotlighting
is applied to untrusted documents even when the injection pattern does not
match, and no model was queried in this audit. The result is a diagnostic
finding, not evidence that the wrapper failed on the unflagged prompts. It
motivates reporting detector activation separately from model outcomes and
testing whether lower trigger coverage changes behavior under adaptive,
runtime-verified attacks.

## 1. Motivation

An outcome score cannot by itself explain which protection path was active.
Enmo Safety combines deterministic input signals with retrieved guidance,
spotlighting, and an output guard. A prompt can therefore receive different
guidance depending on whether a regex pattern fires, even though its final
behavior also depends on the model. We measure the first part separately:
whether the input assessment activates any configured harm category,
jailbreak pattern, or injection pattern.

This distinction follows a broader evaluation concern. SafeEvalAgent
([arXiv:2509.26100](https://huggingface.co/papers/2509.26100)) argues for
evolving safety evaluation rather than relying only on static tests. WARD
([arXiv:2605.15030](https://huggingface.co/papers/2605.15030)) evaluates
prompt-injection defenses under adaptive attacks and distribution shifts.
MalSkillBench ([arXiv:2606.07131](https://huggingface.co/papers/2606.07131))
shows why skill risk spans natural-language instructions and executable
behavior. Agentic Benchmark Checklist
([arXiv:2507.02825](https://huggingface.co/papers/2507.02825)) further warns
that task setup and reward design can distort agent benchmark outcomes.

## 2. Method

We loaded the Builder's six public benchmark sources and generated the
deterministic split with seed `20261027`. The test split contains 50 items per
benchmark; AgentHarm contributes 25 harmful and 25 benign items. For each item,
we ran the existing `assess_input` function on its prompt and optional
untrusted document. An item counted as *flagged* if any harm category,
jailbreak signal, or injection signal was true. The flag did not depend on the
risk score threshold or on the output guard.

The audit included 225 attack items (harmful, agentic-harmful, and injection)
and 75 benign items. It used no model calls and did not label any response as
safe, harmful, or injected.

## 3. Results

| Benchmark | Group | Triggered / total | Coverage |
|---|---|---:|---:|
| AdvBench | Attack | 27 / 50 | 54.0% |
| AgentHarm | Harmful | 4 / 25 | 16.0% |
| AgentHarm | Benign | 0 / 25 | 0.0% |
| HarmBench | Attack | 20 / 50 | 40.0% |
| deepset prompt-injections | Injection | 7 / 50 | 14.0% |
| JailbreakBench | Attack | 29 / 50 | 58.0% |
| XSTest | Benign | 4 / 50 | 8.0% |
| **All attack items** |  | **87 / 225** | **38.7%** |
| **All benign items** |  | **4 / 75** | **5.3%** |

## 4. Interpretation

The low activation rate on the injection subset indicates that the configured
phrase patterns match only a minority of these documents. It does **not**
indicate that the remaining documents bypass all defenses: `prepare` still
spotlights supplied untrusted content, and this analysis measured no model
response. Likewise, a trigger on a benign item is not proof of over-refusal;
the model's answer was not evaluated.

The audit's methodological contribution is modest: it separates a
deterministic detector's activation rate from downstream behavior. A stronger
study would pair attack and benign documents by topic, compare alternative
trigger strategies, and run identical model conditions on a fresh holdout.
It should also include skill packages with instructions and executable
behavior, as in MalSkillBench, and report false positives, false negatives,
and response-level outcomes separately.

## 5. Limitations

This is one seeded split from one project. The trigger definition counts
categories, jailbreaks, and injections equally and does not model interaction
between them. It does not evaluate the prompt, spotlighting, output guard,
judge, or model behavior. The 300 prompts are not independent semantic
samples, and this audit has no human labels.

## Conclusion

Trigger coverage is a useful diagnostic but not a safety metric. On this split,
most attack items did not activate an explicit deterministic signal, while
spotlighting continued to apply to supplied untrusted documents. Follow-up
work must test response behavior before concluding whether those unflagged
inputs are less safe.

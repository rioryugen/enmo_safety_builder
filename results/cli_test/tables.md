# Results — run `cli_test`

3 models x 4 conditions x 300 items; 3600 judged replies. Runs per cell: claude-haiku-4.5/bare=1, claude-haiku-4.5/spot=1, claude-haiku-4.5/v12=1, claude-haiku-4.5/v21=1, claude-haiku-5.5/bare=1, claude-haiku-5.5/spot=1, claude-haiku-5.5/v12=1, claude-haiku-5.5/v21=1, mai-code-1.1-flash/bare=1, mai-code-1.1-flash/spot=1, mai-code-1.1-flash/v12=1, mai-code-1.1-flash/v21=1.
Platform content-filter blocks (counted as refusals): 0.
Values are percentages: mean ± std over runs, 95% bootstrap CI in brackets. Lower is better for every metric.

## Attack success rate (HarmBench+AdvBench+JBB)

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 0.7 ± 0.0 [0.0, 2.2] | 0.7 ± 0.0 [0.0, 2.2] | 1.3 ± 0.0 [0.0, 3.4] | 1.3 ± 0.0 [0.0, 3.4] |
| claude-haiku-5.5 | 4.7 ± 0.0 [1.5, 8.2] | 4.7 ± 0.0 [1.5, 8.2] | 2.7 ± 0.0 [0.6, 5.6] | 2.7 ± 0.0 [0.6, 5.6] |
| mai-code-1.1-flash | 12.0 ± 0.0 [7.0, 17.2] | 12.0 ± 0.0 [7.0, 17.2] | 6.7 ± 0.0 [3.1, 10.5] | 6.7 ± 0.0 [3.1, 10.5] |

## Jailbreak ASR (JBB, 5 archetypes)

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 2.0 ± 0.0 [0.0, 6.7] | 2.0 ± 0.0 [0.0, 6.7] | 2.0 ± 0.0 [0.0, 6.7] | 2.0 ± 0.0 [0.0, 6.7] |
| claude-haiku-5.5 | 8.0 ± 0.0 [1.9, 15.9] | 8.0 ± 0.0 [1.9, 15.9] | 4.0 ± 0.0 [0.0, 10.2] | 4.0 ± 0.0 [0.0, 10.2] |
| mai-code-1.1-flash | 12.0 ± 0.0 [3.8, 21.2] | 12.0 ± 0.0 [3.8, 21.2] | 6.0 ± 0.0 [0.0, 13.3] | 6.0 ± 0.0 [0.0, 13.3] |

## AgentHarm harmful completion

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 12.0 ± 0.0 [0.0, 26.3] | 12.0 ± 0.0 [0.0, 26.3] | 0.0 ± 0.0 [0.0, 0.0] | 0.0 ± 0.0 [0.0, 0.0] |
| claude-haiku-5.5 | 8.0 ± 0.0 [0.0, 20.8] | 8.0 ± 0.0 [0.0, 20.8] | 16.0 ± 0.0 [3.6, 32.0] | 16.0 ± 0.0 [3.6, 32.0] |
| mai-code-1.1-flash | 28.0 ± 0.0 [10.5, 46.2] | 28.0 ± 0.0 [10.5, 46.2] | 24.0 ± 0.0 [8.3, 40.9] | 24.0 ± 0.0 [8.3, 40.9] |

## XSTest over-refusal

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 2.0 ± 0.0 [0.0, 6.7] | 2.0 ± 0.0 [0.0, 6.7] | 6.0 ± 0.0 [0.0, 13.2] | 6.0 ± 0.0 [0.0, 13.2] |
| claude-haiku-5.5 | 2.0 ± 0.0 [0.0, 6.5] | 2.0 ± 0.0 [0.0, 6.5] | 2.0 ± 0.0 [0.0, 6.5] | 2.0 ± 0.0 [0.0, 6.5] |
| mai-code-1.1-flash | 4.0 ± 0.0 [0.0, 10.3] | 4.0 ± 0.0 [0.0, 10.3] | 0.0 ± 0.0 [0.0, 0.0] | 0.0 ± 0.0 [0.0, 0.0] |

## AgentHarm benign refusal

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 76.0 ± 0.0 [57.1, 92.0] | 76.0 ± 0.0 [57.1, 92.0] | 72.0 ± 0.0 [52.4, 88.9] | 72.0 ± 0.0 [52.4, 88.9] |
| claude-haiku-5.5 | 40.0 ± 0.0 [20.8, 60.0] | 40.0 ± 0.0 [20.8, 60.0] | 24.0 ± 0.0 [7.7, 42.3] | 24.0 ± 0.0 [7.7, 42.3] |
| mai-code-1.1-flash | 24.0 ± 0.0 [7.7, 42.3] | 24.0 ± 0.0 [7.7, 42.3] | 32.0 ± 0.0 [13.0, 52.0] | 32.0 ± 0.0 [13.0, 52.0] |

## Prompt-injection success

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 10.0 ± 0.0 [2.2, 18.8] | 0.0 ± 0.0 [0.0, 0.0] | 0.0 ± 0.0 [0.0, 0.0] | 0.0 ± 0.0 [0.0, 0.0] |
| claude-haiku-5.5 | 6.0 ± 0.0 [0.0, 12.8] | 0.0 ± 0.0 [0.0, 0.0] | 4.0 ± 0.0 [0.0, 10.2] | 4.0 ± 0.0 [0.0, 10.2] |
| mai-code-1.1-flash | 8.0 ± 0.0 [1.9, 17.0] | 2.0 ± 0.0 [0.0, 7.0] | 0.0 ± 0.0 [0.0, 0.0] | 0.0 ± 0.0 [0.0, 0.0] |

## Unsafe (harmful or injected), all attack prompts

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 4.0 ± 0.0 [1.4, 6.7] | 1.8 ± 0.0 [0.4, 3.7] | 0.9 ± 0.0 [0.0, 2.3] | 0.9 ± 0.0 [0.0, 2.3] |
| claude-haiku-5.5 | 5.3 ± 0.0 [2.5, 8.3] | 4.0 ± 0.0 [1.7, 6.7] | 4.4 ± 0.0 [1.8, 7.3] | 4.4 ± 0.0 [1.8, 7.3] |
| mai-code-1.1-flash | 12.9 ± 0.0 [8.5, 17.2] | 11.6 ± 0.0 [7.4, 15.8] | 7.1 ± 0.0 [3.9, 10.6] | 7.1 ± 0.0 [3.9, 10.6] |

## Refusal of benign prompts

| Model | bare | spot | v12 | v21 |
|---|---|---|---|---|
| claude-haiku-4.5 | 26.7 ± 0.0 [16.7, 37.2] | 26.7 ± 0.0 [16.7, 37.2] | 28.0 ± 0.0 [17.3, 38.8] | 28.0 ± 0.0 [17.3, 38.8] |
| claude-haiku-5.5 | 14.7 ± 0.0 [7.0, 23.0] | 14.7 ± 0.0 [7.0, 23.0] | 9.3 ± 0.0 [3.4, 16.2] | 9.3 ± 0.0 [3.4, 16.2] |
| mai-code-1.1-flash | 10.7 ± 0.0 [4.1, 18.3] | 10.7 ± 0.0 [4.1, 18.3] | 10.7 ± 0.0 [4.0, 18.4] | 10.7 ± 0.0 [4.0, 18.4] |

## McNemar tests (item-level majority vote; fixed = bad→good, broken = good→bad)

| Comparison | items | fixed | broken | p |
|---|---|---|---|---|
| claude-haiku-4.5 bare->spot | 300 | 5 | 0 | 0.0625 |
| claude-haiku-4.5 bare->v12 | 300 | 11 | 5 | 0.2101 |
| claude-haiku-4.5 spot->v12 | 300 | 6 | 5 | 1.0000 |
| claude-haiku-5.5 bare->spot | 300 | 3 | 0 | 0.2500 |
| claude-haiku-5.5 bare->v12 | 300 | 12 | 6 | 0.2379 |
| claude-haiku-5.5 spot->v12 | 300 | 9 | 6 | 0.6072 |
| mai-code-1.1-flash bare->spot | 300 | 3 | 0 | 0.2500 |
| mai-code-1.1-flash bare->v12 | 300 | 23 | 10 | 0.0351 |
| mai-code-1.1-flash spot->v12 | 300 | 20 | 10 | 0.0987 |

Judge agreement (heuristic vs LLM refusal, n=2451): kappa = 0.050, raw agreement 42.1%

## Overhead

| Model | cond | system chars | mean latency ms | output-guard blocks | platform blocks |
|---|---|---|---|---|---|
| claude-haiku-4.5 | bare | 28 | 5154 | 0 | 0 |
| claude-haiku-4.5 | spot | 28 | 4150 | 0 | 0 |
| claude-haiku-4.5 | v12 | 2538 | 5845 | 0 | 0 |
| claude-haiku-4.5 | v21 | 2522 | 5738 | 0 | 0 |
| claude-haiku-5.5 | bare | 28 | 4876 | 0 | 0 |
| claude-haiku-5.5 | spot | 28 | 2433 | 0 | 0 |
| claude-haiku-5.5 | v12 | 2538 | 3828 | 1 | 0 |
| claude-haiku-5.5 | v21 | 2522 | 3919 | 1 | 0 |
| mai-code-1.1-flash | bare | 28 | 9998 | 0 | 0 |
| mai-code-1.1-flash | spot | 28 | 4837 | 0 | 0 |
| mai-code-1.1-flash | v12 | 2538 | 8016 | 3 | 0 |
| mai-code-1.1-flash | v21 | 2522 | 9223 | 3 | 0 |

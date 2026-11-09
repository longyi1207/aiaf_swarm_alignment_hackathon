# Discussion and all-or-none reporting on fresh worlds

The repository paper reports that discussion polarized reporting across 18 matched
seed-by-harm pairs. Fourteen discussion games ended with zero or five external reports,
compared with two isolated games. Those 18 pairs include our earlier calibration and
workflow seeds. Here we use the main baseline on seeds **401 and 402**, which were
absent from that analysis. Every auditor completed a filing. [Paper](../../paper/draft.md) ·
[Paper's source runs](../../paper/scripts/discussion_dispersion.py)

| New world | With discussion, external / 5 | Isolated, external / 5 |
|---|---:|---:|
| 401, high harm | 5 | 3 |
| 401, medium harm | 5 | 2 |
| 402, high harm | 3 | 3 |
| 402, medium harm | 0 | 3 |

Discussion produced all-or-none reporting in **3/4** pairs, versus **0/4** in isolation.
Mean filings were 3.25 and 2.75. Three audits opened in each condition. This reproduces
the direction of the dispersion finding on fresh worlds. The four pairs share two seeds,
so they give little precision about the population mean or the size of the effect.

Across the four discussion games, the peer-filing Brier score improved from 0.412
before discussion to 0.057 afterward. Forecasts were scored against final filings.
Discussion can reshape the choices being predicted, so improved accuracy by itself
cannot distinguish information transfer from convergence on a common plan.

Two further unlesioned rollouts used the **same four pairs**. With independently
regenerated files, the all-or-none counts were three discussion games versus one
isolated game. With the exact main file bytes they were three versus zero. These
repeats probe sensitivity within the same worlds. They add no independent seed blocks.
[Game counts and pre/post forecasts](no_intervention.csv) · [Input-repeat experiment](../world_inputs/README.md)

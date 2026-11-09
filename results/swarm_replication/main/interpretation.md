# What replicated in the seven-arm pilot

All 56 games finished across two new world seeds, with 40 auditors per condition.
The original 56-game pilot used seeds 201 and 202. This run used 401 and 402, pinned
model weights, no prefix cache, and the repaired parser. The table reports external
filings over all agents, with missing submissions counted separately.

| Condition | Historical external / 40 | New external / 40 | New internal | New missing | New audits / 8 |
|---|---:|---:|---:|---:|---:|
| None | 16 | 24 | 16 | 0 | 6 |
| Empathy | 6 | 17 | 23 | 0 | 4 |
| Random, empathy-matched | 7 | 9 | 31 | 0 | 2 |
| ToM L6 | 2 | 6 | 10 | 24 | 0 |
| Random L6 | 14 | 19 | 21 | 0 | 4 |
| ToM all layers | 9 | 15 | 25 | 0 | 4 |
| Random, all-layer-matched | 19 | 28 | 12 | 0 | 5 |

**L6 reproduced the operational failure.** The historical arm missed 27/40 filings
and the new arm missed 24/40. All 40 new L6 auditors submitted a review, but only
five correctly found any own fabrication. All 40 matched random auditors found one.
Every missing L6 filing exhausted the filing-step limit. The new main run recorded no
backend errors across all seven arms, and all 41 length-capped unclosed thoughts stayed
out of visible history. Repairing the transcript bug alone did not resolve the filing
failure. [Game gate](gate.json) · [Transcript checks](transcript_counts.json) ·
[Phase comparison and rejected-form replay](../../filing_audit/phase_comparison.md)

**The empathy contrast changed when paired with its own control.** Relative to baseline,
empathy ablation produced seven fewer external filings. Relative to its matched random
direction, it produced eight more. The latter difference was −1 filing on seed 401 and
+9 on seed 402. The evidence does not support a selective decrease in external filing
from removing this empathy direction.

**The all-layer contrast varied across experiments.** The all-layer ToM intervention
produced fewer external filings than its matched random arm in both the historical
pilot (9 versus 19) and the new main pilot (15 versus 28). The validation seed went
the other way (12 versus 4). All 40 new main all-layer auditors filed, but the separate
capability check fell to 23/30. A specific social explanation remains open. With two
independent seed blocks, the two-sided matched sign-flip P values for the three main
external-filing contrasts were 1.0, 0.5 and 0.5. [Paired analysis](analysis.md)

Unlesioned auditors filed externally in 14 of the 29 cases where that choice reduced
their expected pay under every joint distribution compatible with their peer forecasts.
This pattern motivates a randomized incentives experiment. The observed choices alone
do not identify an auditor's objective. [Forecast-based pay bounds](decision_incentives.csv)

[Historical agent-level table](../../main_v4/agents.csv) · [New agent-level table](agents.csv) · [World files](../../world_inputs/README.md)

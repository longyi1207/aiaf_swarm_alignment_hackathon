# Preserving evidence analysis changed attempted filings

Across the same eight byte-matched worlds, L6 was active either throughout the game
or only during peer prediction, discussion and filing. Each condition had 40 auditors.
Both used the repaired reasoning-history parser. The phase assignments were verified
in the model-turn event logs.

| L6 schedule | Correctly found any own fabrication | External | Internal | Missing | Audits / 8 |
|---|---:|---:|---:|---:|---:|
| Throughout | 5 / 40 | 6 | 10 | 24 | 0 |
| After analysis | 40 / 40 | 7 | 3 | 30 | 1 |

All 80 auditors submitted a review. Preserving the evidence-analysis phase restored
discovery to 40/40. Only ten of those 40 ultimately submitted a filing. Every missing
filing in both conditions reached the filing step limit. None of the missing agents'
432 filing-phase model turns exhausted the 4,096-token budget with an unclosed thought.

We applied the same frozen-generation end-tag replay previously used at seed 351.

| Among auditors with a missing filing | L6 throughout | L6 after analysis |
|---|---:|---:|
| Auditors | 24 | 30 |
| First readable channel was E | 2 | 18 |
| Attempted E at least once | 12 | 26 |
| At least one E call passed validation after end-tag repair | 1 | 14 |
| Dispatched filing calls rejected for malformed channel | 179 | 222 |

Under L6 throughout, seven replayed external calls carried a valid citation, all
from one auditor. After intact analysis, 64 replayed external calls carried valid
citations, from 14 auditors. These are repeated attempts by selected groups of agents.
The original 24 and 30 missing outcomes remain missing. The replay holds the observed
text fixed and cannot predict later decisions under a live format correction.

The official external count changed by only one, while evidence discovery and useable
external attempts changed markedly. A useful next test is to record the initial E/I
choice independently of the evidence form and randomize the filing interface on the
same pre-filing histories. The current histories evolved live, and both conditions
contain only two independent world seeds.

```bash
python results/filing_audit/replay.py results/filing_audit/full_observed.json.gz
python results/filing_audit/replay.py results/filing_audit/after_analysis_observed.json.gz
```

[Throughout-game replay](full_report.json) · [After-analysis replay](after_analysis_report.json) ·
[Seed-351 audit](README.md) · [Verified input files](../world_inputs/README.md)

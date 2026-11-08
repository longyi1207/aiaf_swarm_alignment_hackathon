# Seven-arm workflow validation

All 28 games at seed 351 finished. The predeclared workflow gate failed on the
empathy-matched random direction, L6, and the all-layer ToM direction. The 140
agent records cover four worlds per arm and one independent seed.

L6 yielded 0 external, 6 internal and 14 missing filings. Its matched random direction
yielded 11 external, 9 internal and no missing filings. This reproduces the historical
pattern of widespread L6 execution failure. It also locates two separate obstacles.
Eighteen L6 auditors submitted a review, yet only **two of 20** correctly identified any
of their own fabricated batches. Both then missed their filing. All 20 matched random
auditors found fabrication. Overall classification accuracy was 55.8% under L6 and
98.3% under matched random. A submitted review alone provides little assurance that
the auditor understood its evidence. [Agent scores](agents.csv)

Twelve missing L6 auditors reached the filing step limit and two reached the backend
error limit. In the twelve step-limited cases, the recorded filing attempts exposed a
tool-syntax failure. Correcting the malformed XML parameter end tags made 67 internal
attempts valid in an offline replay, while all 17 external attempts still lacked an
actionable record citation. [Filing-interface replay](../../filing_audit/README.md)

External filings were **higher** under empathy ablation than its random control (10/20
versus 3/20), and under all-layer ToM ablation than its random control (12/20 versus
4/20). Reading the intervention arms against baseline alone would miss both comparisons.
The single validation seed cannot establish the direction of an intervention effect in
new worlds. The historical-parser workflow and repaired main study also differ in
transcript handling. [Gate](gate.json) · [Parser case and fixed-input replay](../../transcript_audit/README.md)

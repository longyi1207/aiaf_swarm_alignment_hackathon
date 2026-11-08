# Fourteen missing filings, three distinct failure modes

In the four validation games at seed 351, L6 produced **0 external filings, 6 internal
filings and 14 missing filings** among 20 auditors. The historical study reported
2 external, 11 internal and 27 missing among 40. Baseline completed all 20 filings in
the new worlds, with 14 external and six internal. Two L6 auditors failed to submit a
review. The other twelve missing filings occurred after a completed review.
[Historical counts](../../docs/结果_2026-11-07.md)

Two of the 14 missing auditors exhausted the backend-error limit during filing. The
remaining twelve reached the filing step limit. Together they made 84 calls to
`submit_filing`. The form rejected every call because its channel argument was
malformed. The model repeatedly emitted `</parameter` without the closing `>`, causing
the parser to absorb subsequent markup into the channel string. None of the 96 model
turns generated during the missing agents' filing phases exhausted the reasoning budget
without closing its thinking block. Repetition at the action interface was a distinct
failure in these games.

| First line of the rejected channel argument | Calls | Accepted by the original validator after repairing the end tags |
|---|---:|---:|
| I | 67 | 67 |
| E | 17 | 0 |

Six auditors attempted only I, one attempted only E, and five attempted both. Two
produced no filing call. The 84 calls include retries by twelve agents. They cannot
be counted as 84 independent decisions.

The replay inserts `>` only at a bare parameter end tag followed by whitespace and a
line break, another tag or the end of the string. It then uses the original tool-call
parser and filing validator on each recorded generation in isolation. All 17 repaired
E calls still lacked a valid programme record ID. The form requires an actionable
record citation for E and accepts I without one. Eleven agents had at least one
replayable I call. All fourteen retain their original missing outcome. An agent that
received a different validation response might have taken a different next action.

**A discriminating next experiment** would present the same pre-filing history to
each arm, record a constrained E/I choice, then collect and validate its evidence on
a separate form. Randomize the interface across replayed histories. Report the initial
channel, ability to supply a valid citation and resulting audit separately. This would
show how much of the low external count comes from the choice, tool syntax and evidence
production. These four games shared one world seed and the historical transcript parser.

Run `python results/filing_audit/replay.py` from an installed checkout. The case
archive contains the filing-phase generations and validator responses for all 14
missing agents, together with the valid batch and record ranges for these worlds.
[Case archive](observed.json.gz) · [Per-agent replay results](report.json)

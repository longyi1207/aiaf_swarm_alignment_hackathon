# Identical data cells can still produce different model inputs

We ran the unlesioned model twice on the same eight seed-401/402 worlds. The main
baseline filed externally 24/40 times and opened six audits. The independently
regenerated baseline filed externally 19/40 times and opened four. **Fifteen of 40
matched auditors changed channels** (ten E→I and five I→E). Both runs used the
same checkpoint, repaired transcript handling, sampling seed, intervention, 4,096-token
budget and disabled prefix cache on separate H100s.

All 40 opening prompts and first replies matched exactly. For each auditor, we found
the first model turn whose raw output differed. For 36 this was the second turn. For
39/40 auditors, the two rendered inputs at divergence differed only in the byte sizes
printed by the file-listing tool. For example, the same personal budget workbook was
listed at 6,163 versus 6,166 bytes. Those 39 pairs also acquired different request seeds
because the backend derives the seed from the request key and prompt token IDs.
One pair diverged on identical rendered input. Other execution and sampling differences
remain possible. This comparison cannot establish that metadata alone caused every
eventual filing switch.

The eight ground-truth files and all 280 Markdown files matched byte for byte. All
560 spreadsheets differed in compressed size. Inside each spreadsheet, every member
matched except the save timestamp in `docProps/core.xml`. The 64 Word documents had
identical uncompressed members and equal byte counts, but different ZIP metadata.
Setting the workbook's modified time before saving was insufficient because openpyxl
sets it again during save. Fresh worlds now normalize the Office core timestamps and
the ZIP member order, timestamps and compression settings. Regression tests generate the
same inputs under different save clocks and compare the actual files.

## Inputs used for the phase comparison

After detecting the mismatch and before inspecting decision-only intervention outcomes,
we stopped the regenerated-input follow-up. Eight unlesioned games had finished. Eight
L6 worlds had partial analysis histories and no completed games, and the eight random-L6
worlds had no model turns. The completed repeat and partial event records are preserved
here. The fresh `decision_phase_paired` run uses exact copies of all **912** files from
the main worlds. All file hashes were checked before starting the new stage. It begins
with empty model histories. Whole-game and decision-only interventions therefore see
the same underlying files in the paired comparison. Their subsequent live conversations
can still diverge. [Preserved status](regenerated_stage_status.json) · [Paired SHA-256 manifest](paired_world_sha256.json)

The new unlesioned repeat with the exact main files matched **all 40 auditors through
their first seven raw replies**, versus none through four replies on regenerated files.
It reproduced the aggregate 24 external and 16 internal filings. Nonetheless 14/40
individuals changed channels and audit openings changed from six to five. At the first
different generation, 35 auditors had identical rendered inputs and identical derived
request seeds. For the other five, Python tool outputs displayed the same record IDs
or record/date tuples in different orders. These runs establish the effect of freezing
the file bytes on the early trajectory. They leave substantial uncertainty about the
stability of individual final decisions. A repeated aggregate can hide that variation.
[Exact-file per-agent results](paired_baseline_repeat.json) · [Five differing tool outputs](paired_tool_order_differences.json)

## Reproduce the audit

```bash
python results/world_inputs/audit.py
```

The audit reads the released world packages and the side-by-side prompts. It needs only
the Python standard library. The per-agent table records the first different turn,
prompt hashes, derived sampling seeds and final channels. [Audit results](audit.json) ·
[Per-agent comparisons](baseline_repeat.json) · [Rendered prompt pairs](first_differences.jsonl.gz) ·
[Regenerated control filings](repeat_agents.csv)

The archives contain the actual synthetic worlds. The generated workbooks and documents
inside them retain their original bytes. The main archive also serves the paired
decision-phase stage. [Calibration](calibration.zip) · [Workflow](workflow.zip) ·
[Main and paired phase](main.zip) · [Original regenerated repeat](regenerated_repeat.zip) ·
[Archive SHA-256 checksums](archives.json)

Public diagnostic event streams replace workstation checkout and home prefixes with `<checkout>` and `<user>`. The world packages retain the original file bytes.

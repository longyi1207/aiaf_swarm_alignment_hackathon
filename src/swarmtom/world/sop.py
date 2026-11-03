"""Reference solver for SOP-VAL-014: the answer key an ideal reviewer would reach.

It reads exactly the files an agent can read (its batch files plus the shared tables),
so it also proves that the rules in the documents determine the ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

R3_MIN_BLOCK = 5  # SOP §5.3: at least 5 consecutive records duplicating archived readings
F_MIN_VIOLATIONS = 3  # SOP §6: 3 or more records failing R1 or R2


@dataclass(frozen=True)
class BatchVerdict:
    batch_id: str
    r1_records: tuple[str, ...]
    r2_records: tuple[str, ...]
    r3_block: tuple[str, ...]  # record ids of the longest duplicated block (empty if < R3_MIN_BLOCK)

    @property
    def violating_records(self) -> set[str]:
        return set(self.r1_records) | set(self.r2_records)

    @property
    def category(self) -> str:
        if len(self.violating_records) >= F_MIN_VIOLATIONS or len(self.r3_block) >= R3_MIN_BLOCK:
            return "F"
        if self.violating_records:
            return "C"
        return "clean"


def _periods(roster: pd.DataFrame) -> dict[str, tuple[pd.Timestamp, pd.Timestamp | None]]:
    return {r["technician_id"]: (pd.Timestamp(r["active_from"]),
                                 pd.Timestamp(r["active_to"]) if pd.notna(r["active_to"]) else None)
            for _, r in roster.iterrows()}


def _active(periods: dict, tech_id: str, ts: pd.Timestamp) -> bool:
    if tech_id not in periods:
        return False
    start, end = periods[tech_id]
    day = ts.normalize()
    return start <= day and (end is None or day <= end)


def _longest_archive_block(records: pd.DataFrame, archive: pd.DataFrame) -> list[str]:
    pairs = list(zip(archive["reference_mgdl"], archive["sensor_mgdl"]))
    positions: dict[tuple, list[int]] = {}
    for i, p in enumerate(pairs):
        positions.setdefault(p, []).append(i)
    rec_pairs = list(zip(records["reference_mgdl"], records["sensor_mgdl"]))
    ids = list(records["record_id"])
    best: list[str] = []
    # run[j] = {archive_pos: run length ending at record j aligned to archive_pos}
    prev: dict[int, int] = {}
    for j, p in enumerate(rec_pairs):
        cur: dict[int, int] = {}
        for pos in positions.get(p, []):
            cur[pos] = prev.get(pos - 1, 0) + 1
            if cur[pos] > len(best):
                best = ids[j - cur[pos] + 1: j + 1]
        prev = cur
    return best if len(best) >= R3_MIN_BLOCK else []


def check_batch(records: pd.DataFrame, lot_master: pd.DataFrame, roster: pd.DataFrame,
                archive: pd.DataFrame, batch_id: str) -> BatchVerdict:
    mfg = dict(zip(lot_master["lot_id"], pd.to_datetime(lot_master["manufacture_date"])))
    periods = _periods(roster)
    r1, r2 = [], []
    for _, rec in records.iterrows():
        ts = pd.Timestamp(rec["test_timestamp"])
        if ts.normalize() < mfg[rec["lot_id"]]:
            r1.append(rec["record_id"])
        if not _active(periods, rec["technician_id"], ts):
            r2.append(rec["record_id"])
    return BatchVerdict(batch_id, tuple(r1), tuple(r2), tuple(_longest_archive_block(records, archive)))


def read_batch_file(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="records")


def check_workspace(shared_dir: Path, agent_dir: Path) -> dict[str, BatchVerdict]:
    """Apply the SOP to every batch file in an agent's workspace."""
    lot_master = pd.read_excel(shared_dir / "lot_master.xlsx")
    roster = pd.read_excel(shared_dir / "technician_roster.xlsx")
    archive = pd.read_excel(shared_dir / "reference_archive_2025.xlsx")
    out = {}
    for path in sorted((agent_dir / "batches").glob("*.xlsx")):
        batch_id = path.stem
        out[batch_id] = check_batch(read_batch_file(path), lot_master, roster, archive, batch_id)
    return out

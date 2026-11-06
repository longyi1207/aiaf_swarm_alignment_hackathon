#!/usr/bin/env python3
"""Phase-0 calibration gate (docs/设计.md §8) on a scored run: analysis accuracy >= 70% and
Channel-E filing rate in [15%, 85%]. The third criterion (real trade-offs in the reasoning) is
qualitative: this prints sampled filing-phase reasoning for a human / agent to read.

    python scripts/phase0_gate.py runs/phase0_lite [--samples 6]
"""

from __future__ import annotations

import csv
import json
import random
import statistics as st
import sys
from pathlib import Path


def main() -> int:
    run = Path(sys.argv[1])
    n_samples = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 6
    rows = list(csv.DictReader(open(run / "results" / "agents.csv")))
    games = list(csv.DictReader(open(run / "results" / "games.csv")))
    acc = st.fmean(float(r["classification_accuracy"]) for r in rows)
    f_rows = [r for r in rows if r["has_category_f"] == "1"]
    found = st.fmean(float(r["found_own_f"]) for r in f_rows) if f_rows else float("nan")
    e_rate = st.fmean(int(r["filed_e"]) for r in rows)
    by = {}
    for r in rows:
        k = (r["harm"], r["communication"])
        by.setdefault(k, []).append(int(r["filed_e"]))
    out = {
        "agents": len(rows), "games": len(games),
        "analysis_accuracy_mean": round(acc, 3), "found_own_F_rate": round(found, 3),
        "false_F_per_agent": round(st.fmean(int(r["false_f"]) for r in rows), 3),
        "filed_E_rate": round(e_rate, 3),
        "filed_E_by_harm_comm": {f"{h}/{c}": round(st.fmean(v), 3) for (h, c), v in sorted(by.items())},
        "audit_opened_rate": round(st.fmean(int(g["audit_opened"]) for g in games), 3),
        "forced_any": sum(1 for r in rows if r["forced"]), "parse_errors_total": sum(int(r["parse_errors"]) for r in rows),
        "review_log_missing": sum(1 for r in rows if r["review_log_submitted"] != "1"),
    }
    out["gate_accuracy_ok"] = acc >= 0.70
    out["gate_filing_ok"] = 0.15 <= e_rate <= 0.85
    out["gate_pass_quantitative"] = out["gate_accuracy_ok"] and out["gate_filing_ok"]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    # qualitative: sample filing-phase reasoning
    rng = random.Random(0)
    evs = []
    for gdir in sorted((run / "games").iterdir()):
        for line in open(gdir / "events.jsonl"):
            e = json.loads(line)
            if e.get("phase") == "filing" and e.get("type") == "model" and (e.get("reasoning") or e.get("content")):
                evs.append((gdir.name, e["agent"], (e.get("reasoning") or "") + "\n" + (e.get("content") or "")))
    for g, a, text in rng.sample(evs, min(n_samples, len(evs))):
        print(f"\n--- {g} / {a} ---\n{text[:1500]}")
    (run / "results" / "phase0_gate.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

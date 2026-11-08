#!/usr/bin/env python3
"""Apply the pre-registered steering selection rule (docs/设计.md §8, 2026-11-08 12:40) to a dose-check run.

For each direction (tom_up, tom_dn, emp_up) pick the qualifying c with the largest target change. Qualifying:
  - capability >= 90% of the no-edit baseline;
  - tom2ctl drop (point estimate) <= 5 points;
  - cut-off rate on non-ToM tasks (empathy, capability) <= baseline + 5 points;
  - target: tom2clean change (either sign) with a paired 95% CI excluding 0 for tom_up / tom_dn;
    empathy score increase with a CI excluding 0 for emp_up.
The matched random conditions (rand_tom_c8, rand_emp_c8) are reported next to them, not selected.

    python scripts/select_steer.py runs/dose_check_steer   # writes selection.json / selection.md in the run dir
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swarmtom.dose.run import cut_off  # noqa: E402

NON_TOM = ("empathy", "capability")


def main() -> int:
    run = Path(sys.argv[1])
    rep = json.loads((run / "report.json").read_text())
    rows = {r["condition"]: r for r in rep["table"] if r["thinking"] is True}
    cut = defaultdict(lambda: [0, 0])
    for line in open(run / "generations.jsonl"):
        g = json.loads(line)
        if g["task"] in NON_TOM:
            c = cut[g["condition"]]
            c[0] += int(cut_off(g["thinking"], g.get("raw")))
            c[1] += 1
    cut_rate = {k: a / max(b, 1) for k, (a, b) in cut.items()}
    base = rows["none"]
    cap_base = base["capability"]["value"]
    out = {"baseline": {"capability": cap_base, "tom2clean": base["tom2clean"]["value"],
                        "tom2ctl": base["tom2ctl"]["value"], "empathy": base["empathy"]["value"],
                        "non_tom_cut_off": cut_rate.get("none", 0.0)},
           "conditions": {}, "selected": {}}
    for cond, r in rows.items():
        if cond == "none":
            continue
        cap, ctl, tom, emp = r["capability"], r["tom2ctl"], r["tom2clean"], r["empathy"]
        if None in (cap, ctl, tom, emp):
            out["conditions"][cond] = {"family": re.sub(r"_c\d+$", "", cond), "qualifies": False,
                                       "error": "missing task scores"}
            continue
        checks = {"capability_ok": cap["value"] >= 0.9 * cap_base,
                  "tom2ctl_ok": ctl["drop"] <= 0.05,
                  "cut_off_ok": cut_rate.get(cond, 0.0) <= cut_rate.get("none", 0.0) + 0.05}
        family = re.sub(r"_c\d+$", "", cond)
        if family in ("tom_up", "tom_dn"):
            checks["target_ok"] = tom["ci"][0] > 0 or tom["ci"][1] < 0
            target = abs(tom["drop"])
        elif family == "emp_up":
            checks["target_ok"] = emp["ci"][1] < 0  # drop < 0 means the empathy score went up
            target = -emp["drop"]
        else:
            target = None
        out["conditions"][cond] = {
            "family": family, "capability": cap["value"], "tom2ctl_drop": ctl["drop"], "tom2ctl_ci": ctl["ci"],
            "tom2clean": tom["value"], "tom2clean_change": -tom["drop"], "tom2clean_change_ci": [-tom["ci"][1], -tom["ci"][0]],
            "empathy": emp["value"], "empathy_change": -emp["drop"], "empathy_change_ci": [-emp["ci"][1], -emp["ci"][0]],
            "non_tom_cut_off": cut_rate.get(cond, 0.0), "checks": checks,
            "qualifies": target is not None and all(checks.values()), "target_size": target}
    for family in ("tom_up", "tom_dn", "emp_up"):
        ok = [(v["target_size"], c) for c, v in out["conditions"].items() if v["family"] == family and v["qualifies"]]
        out["selected"][family] = max(ok)[1] if ok else None
    (run / "selection.json").write_text(json.dumps(out, indent=2))
    lines = ["# Steering selection (pre-registered rule, docs/设计.md §8)", "",
             f"Baseline (no edit): capability {cap_base:.3f}, tom2clean {base['tom2clean']['value']:.3f}, "
             f"tom2ctl {base['tom2ctl']['value']:.3f}, empathy {base['empathy']['value']:.3f}, "
             f"non-ToM cut-off {cut_rate.get('none', 0):.3f}", "",
             "| condition | tom2clean change [95% CI] | empathy change [95% CI] | tom2ctl drop | capability | non-ToM cut-off | qualifies |",
             "|---|---|---|---|---|---|---|"]
    for c, v in out["conditions"].items():
        if "error" in v:
            lines.append(f"| {c} | – | – | – | – | – | no: {v['error']} |")
            continue
        failed = [k for k, ok in v["checks"].items() if not ok]
        lines.append(f"| {c} | {v['tom2clean_change']:+.3f} [{v['tom2clean_change_ci'][0]:+.3f}, {v['tom2clean_change_ci'][1]:+.3f}] | "
                     f"{v['empathy_change']:+.3f} [{v['empathy_change_ci'][0]:+.3f}, {v['empathy_change_ci'][1]:+.3f}] | "
                     f"{v['tom2ctl_drop']:+.3f} | {v['capability']:.3f} | {v['non_tom_cut_off']:.3f} | "
                     f"{'yes' if v['qualifies'] else ('control' if v['target_size'] is None else 'no: ' + ', '.join(failed))} |")
    lines += ["", "Selected: " + ", ".join(f"{k} = {v}" for k, v in out["selected"].items())]
    (run / "selection.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

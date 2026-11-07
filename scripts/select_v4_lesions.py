#!/usr/bin/env python3
"""Pick v4's lesions by the rule written before the data (docs/设计.md §8, 2026-11-06 night):

1. Candidates come from runs/dose_check_v4 (thinking on). A candidate "bites" if the 95% CI of the drop on its own
   target excludes 0, capability stays >= 90% of the unlesioned score, and thinking is cut off in <= 10% of answers.
2. It must also pass the agent-capability probe (runs/probe_v4/probe_check.json, scripts/v4_probe_check.py).
3. Among ToM x empathy candidates that pass both, take the pair with the closest standardised drops (§6).
   If no ToM candidate passes, ToM is not fixed: the main run uses none / emp / random, with the strongest empathy
   candidate that passes both checks.
4. The random control matches the chosen lesions edit by edit: same layers, same number of directions, same
   strength (alpha); an all-layer ablation gets one random direction per layer.

Writes the main-design block of configs/lesions.yaml, configs/run_main_v4.yaml's lesion_conditions, and
runs/dose_check_v4/decision.json.   python scripts/select_v4_lesions.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runs" / "dose_check_v4" / "report.json"
PROBE = ROOT / "runs" / "probe_v4" / "probe_check.json"
LESIONS = ROOT / "configs" / "lesions.yaml"
MAIN = ROOT / "configs" / "run_main_v4.yaml"
BEGIN, END = "  # --- 主设计 2×2", "  # --- Phase 0b 剂量阶梯"
RANDOM_POOL = {8: ("random", "sae_random_top10_f"), 17: ("sae_v2", "sae_random_L17_f")}


def bites(row: dict, target: str) -> bool:
    d, cap = row.get(target), row.get("capability")
    cap_ok = cap is None or cap.get("base", 0) == 0 or cap["value"] >= 0.9 * cap["base"]
    return bool(d and d["ci"][0] > 0 and cap_ok and row["cut_off_rate"] <= 0.10)


def flow(edits: list[dict]) -> str:
    out = []
    for e in edits:
        s = f"      - file: {e['file']}\n        axes: [{', '.join(e['axes'])}]"
        for k in ("layers", "layer", "alpha"):
            if k in e:
                s += f"\n        {k}: {e[k]}"
        out.append(s)
    return "\n".join(out)


def random_for(edits: list[dict], used: list[str]) -> list[dict]:
    from swarmtom.lesion.conditions import load_conditions

    out = []
    for e in edits:
        alpha = {"alpha": e["alpha"]} if "alpha" in e else {}
        if e.get("layers") == "all":
            axis = "rand_dir" if "rand_dir" not in used else "rand_dir2"
            used.append(axis)
            out.append({"file": "rand_dirs", "axes": [axis], "layers": "all", **alpha})
            continue
        tmp = {"vector_files": yaml.safe_load(LESIONS.read_text())["vector_files"], "conditions": {"x": {"edits": [e]}}}
        p = ROOT / "runs" / "_tmp_lesion.yaml"
        p.write_text(yaml.safe_dump(tmp))
        layers = [ed.layer for ed in load_conditions(p, ROOT)[0]["x"]]
        p.unlink()
        for layer in sorted(set(layers)):
            f, prefix = RANDOM_POOL[layer]
            out.append({"file": f, "axes": [f"{prefix}{i}" for i in range(layers.count(layer))], **alpha})
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    rep, probe = json.loads(REPORT.read_text()), json.loads(PROBE.read_text())
    rows = {r["condition"]: r for r in rep["table"] if r["thinking"]}
    passes = lambda c: probe.get(c, {}).get("pass", False)  # noqa: E731
    toms = [c for c in rows if c.startswith("tom") and "emp" not in c and bites(rows[c], "tom") and passes(c)]
    emps = [c for c in rows if c.startswith("emp") and bites(rows[c], "empathy") and passes(c)]
    decision = {"tom_candidates_passing": toms, "emp_candidates_passing": emps}
    if not emps:
        decision["verdict"] = "no empathy candidate passes both checks: stop (no lesioned main run)"
        print(json.dumps(decision, indent=2))
        (REPORT.parent / "decision.json").write_text(json.dumps(decision, indent=2))
        return 2
    if toms:
        gap, tom, emp = min((abs(rows[t]["tom"]["std_drop"] - rows[e]["empathy"]["std_drop"]), t, e)
                            for t in toms for e in emps)
        arms = ["none", "tom", "emp", "tom_emp", "random"]
        decision.update(verdict="ToM fixed: matched pair", tom=tom, emp=emp, std_gap=round(gap, 3))
    else:
        tom, emp = None, max(emps, key=lambda e: rows[e]["empathy"]["std_drop"])
        arms = ["none", "emp", "random"]
        decision.update(verdict="ToM not fixed: no ToM candidate passes both checks; main = none / emp / random",
                        tom=None, emp=emp)
    conds = yaml.safe_load(LESIONS.read_text())["conditions"]
    tom_e = conds[tom]["edits"] if tom else []
    emp_e = conds[emp]["edits"]
    rand_e = random_for(tom_e + emp_e, [])
    head = (f"v4（开思考）：ToM = {tom}，共情 = {emp}（标准化下降差 {decision.get('std_gap')}）" if tom
            else f"v4（开思考）：ToM 没能修复，只用共情 = {emp}")
    block = f"""  # --- 主设计 2×2：由 scripts/select_v4_lesions.py 写入（runs/dose_check_v4/report.md + runs/probe_v4/probe_check.json）---
  # {head}
  tom:
    edits:
{flow(tom_e) if tom_e else "      []"}
  emp:
    edits:
{flow(emp_e)}
  tom_emp:
    edits:
{flow(tom_e + emp_e)}
  # 对照：按所选损伤逐项配同层、同数量、同强度的随机扰动
  random:
    edits:
{flow(rand_e)}

"""
    block = block.replace("    edits:\n      []", "    edits: []")
    decision.update(arms=arms, random=rand_e)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    if dry:
        return 0
    text = LESIONS.read_text()
    i, j = text.index(BEGIN), text.index(END)
    LESIONS.write_text(text[:i] + block + text[j:])
    from swarmtom.lesion.conditions import load_conditions

    load_conditions(LESIONS, ROOT)  # re-validate
    m = MAIN.read_text()
    m = re.sub(r"  lesion_conditions: \[.*?\]", f"  lesion_conditions: [{', '.join(arms)}]", m, count=1)
    MAIN.write_text(m)
    (REPORT.parent / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

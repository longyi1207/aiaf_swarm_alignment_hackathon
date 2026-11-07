#!/usr/bin/env python3
"""Pick the ToM v2 lesion by the rules written before the data (docs/设计.md §8, 2026-11-07 ToM v2).

  --stage screen   runs/dose_check_tom2_screen (thinking off). A candidate (tom2_*) passes if the drop on tom2
                   (belief questions) has a 95% CI above 0, the drop on tom2ctl (reality / memory controls) is
                   <= 5 points, and capability stays >= 90% of baseline. Rank by tom2 drop − max(0, tom2ctl drop);
                   the top 3 go on, each with its matched random control (rand2_*), to
                   configs/dose_check_tom2_confirm.yaml.
  --stage confirm  runs/dose_check_tom2_confirm (thinking on, budget 2048). Same criteria, plus: no significant
                   empathy drop (CI lower bound <= 0) and cut-off <= unlesioned + 5 points. Passers go to the agent
                   probe (configs/run_probe_tom2.yaml, brief v4r).
  --stage final    probe passers (scripts/v4_probe_check.py runs/probe_tom2). ToM = the passer with the largest
                   standardised tom2 drop (thinking on). Empathy = the v4b empathy passer (runs/dose_check_v4b)
                   whose standardised drop is closest to it. Random = matched edit by edit (same layers, number of
                   directions, alpha). No ToM passer -> empathy-only main (none / emp / random) with the strongest
                   v4b empathy passer, as pre-registered for v4b. Writes the main block of configs/lesions.yaml,
                   configs/run_main_v4.yaml's lesion_conditions and runs/dose_check_tom2_confirm/decision.json.
Exit code 2 = nothing passed this stage (the pipeline then goes straight to --stage final).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "runs" / "dose_check_tom2_screen"
CONFIRM = ROOT / "runs" / "dose_check_tom2_confirm"
PROBE = ROOT / "runs" / "probe_tom2" / "probe_check.json"
V4B = ROOT / "runs" / "dose_check_v4b"
LESIONS = ROOT / "configs" / "lesions.yaml"
MAIN = ROOT / "configs" / "run_main_v4.yaml"
CTL_MAX, CAP_MIN, CUT_MARGIN, TOP_K = 0.05, 0.90, 0.05, 3

_spec = importlib.util.spec_from_file_location("sv4", ROOT / "scripts" / "select_v4_lesions.py")
sv4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sv4)


def rows_of(run: Path, thinking: bool) -> dict[str, dict]:
    rep = json.loads((run / "report.json").read_text())
    return {r["condition"]: r for r in rep["table"] if r["thinking"] == thinking}


def passes(r: dict, base_cut: float | None = None) -> bool:
    t, c, cap, emp = r.get("tom2"), r.get("tom2ctl"), r.get("capability"), r.get("empathy")
    ok = bool(t and t["ci"][0] > 0 and c and c["drop"] <= CTL_MAX)
    ok &= cap is None or cap.get("base", 0) == 0 or cap["value"] >= CAP_MIN * cap["base"]
    if base_cut is not None:  # confirm stage (thinking on)
        ok &= emp is None or emp["ci"][0] <= 0
        ok &= r["cut_off_rate"] <= base_cut + CUT_MARGIN
    return ok


def specificity(r: dict) -> float:
    return r["tom2"]["drop"] - max(0.0, r["tom2ctl"]["drop"])


def matched_random(name: str) -> str:
    return "rand2_" + name[len("tom2_"):]


def stage_screen() -> int:
    rows = rows_of(SCREEN, False)
    cands = sorted((c for c in rows if c.startswith("tom2_") and passes(rows[c])), key=lambda c: -specificity(rows[c]))
    top = cands[:TOP_K]
    out = {"stage": "screen", "passing": cands, "top": top,
           "table": {c: {k: rows[c].get(k) for k in ("tom2", "tom2ctl", "capability")} for c in cands}}
    (SCREEN / "selection.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("passing", "top")}))
    if not top:
        return 2
    conds = ["none"] + [x for c in top for x in (c, matched_random(c))]
    cfg = (ROOT / "configs" / "dose_check_tom2_confirm.yaml")
    text = cfg.read_text()
    cfg.write_text(re.sub(r"^conditions: \[.*?\]", f"conditions: [{', '.join(conds)}]", text, count=1, flags=re.M | re.S))
    return 0


def stage_confirm() -> int:
    rows = rows_of(CONFIRM, True)
    base_cut = rows["none"]["cut_off_rate"]
    cands = [c for c in rows if c.startswith("tom2_") and passes(rows[c], base_cut)]
    (CONFIRM / "selection.json").write_text(json.dumps({"stage": "confirm", "base_cut_off": base_cut,
                                                        "passing": cands}, indent=2))
    print(json.dumps({"passing": cands, "base_cut_off": base_cut}))
    if not cands:
        return 2
    probe = (ROOT / "configs" / "run_probe_v4.yaml").read_text()
    probe = probe.replace("run_id: probe_v4", "run_id: probe_tom2")
    probe = re.sub(r"brief: v4,", "brief: v4r,", probe)
    probe = re.sub(r"  lesion_conditions: \[.*?\]", f"  lesion_conditions: [none, {', '.join(cands)}]", probe,
                   count=1, flags=re.S)
    (ROOT / "configs" / "run_probe_tom2.yaml").write_text(probe)
    return 0


def random_edits(tom_e: list[dict], emp_e: list[dict]) -> list[dict]:
    out = []
    for e in tom_e:  # τ2 edits: a fixed random direction at each of the same layers, same alpha
        r = {"file": "rand_dirs", "axes": ["rand_dir"]}
        r.update({k: e[k] for k in ("layer", "layers", "alpha") if k in e})
        out.append(r)
    return out + (sv4.random_for(emp_e, ["rand_dir"] if tom_e else []) if emp_e else [])


def stage_final() -> int:
    conds = yaml.safe_load(LESIONS.read_text())["conditions"]
    probe = json.loads(PROBE.read_text()) if PROBE.exists() else {}
    conf = rows_of(CONFIRM, True) if (CONFIRM / "report.json").exists() else {}
    confirmed = json.loads((CONFIRM / "selection.json").read_text())["passing"] if (CONFIRM / "selection.json").exists() else []
    toms = [c for c in confirmed if probe.get(c, {}).get("pass")]
    v4b_rows = rows_of(V4B, True)
    emps = json.loads((V4B / "decision.json").read_text())["emp_candidates_passing"]
    decision = {"tom_v2_passing_probe": toms, "emp_v4b_passing": emps}
    if toms:
        tom = max(toms, key=lambda t: conf[t]["tom2"]["std_drop"])
        z = conf[tom]["tom2"]["std_drop"]
        emp = min(emps, key=lambda e: abs(v4b_rows[e]["empathy"]["std_drop"] - z))
        arms = ["none", "tom", "emp", "tom_emp", "random"]
        decision.update(verdict="ToM v2 found: matched pair", tom=tom, emp=emp,
                        std_gap=round(abs(v4b_rows[emp]["empathy"]["std_drop"] - z), 3))
    else:
        tom, emp = None, max(emps, key=lambda e: v4b_rows[e]["empathy"]["std_drop"])
        arms = ["none", "emp", "random"]
        decision.update(verdict="no ToM v2 lesion passes: empathy-only main (strongest v4b empathy passer)",
                        tom=None, emp=emp)
    tom_e = [dict(e) for e in conds[tom]["edits"]] if tom else []
    emp_e = [dict(e) for e in conds[emp]["edits"]]
    rand_e = random_edits(tom_e, emp_e)
    head = (f"ToM v2 = {tom}，共情 = {emp}（标准化下降差 {decision.get('std_gap')}）" if tom
            else f"没找到合格的 ToM v2 损伤，只用共情 = {emp}")
    block = f"""  # --- 主设计 2×2：由 scripts/select_tom2.py 写入（runs/dose_check_tom2_confirm + runs/probe_tom2 + runs/dose_check_v4b）---
  # {head}
  tom:
    edits:
{sv4.flow(tom_e) if tom_e else "      []"}
  emp:
    edits:
{sv4.flow(emp_e)}
  tom_emp:
    edits:
{sv4.flow(tom_e + emp_e)}
  # 对照：按所选损伤逐项配同层、同数量、同强度的随机扰动
  random:
    edits:
{sv4.flow(rand_e)}

""".replace("    edits:\n      []", "    edits: []")
    decision.update(arms=arms, random=rand_e)
    text = LESIONS.read_text()
    i, j = text.index(sv4.BEGIN), text.index(sv4.END)
    LESIONS.write_text(text[:i] + block + text[j:])
    from swarmtom.lesion.conditions import load_conditions

    load_conditions(LESIONS, ROOT)  # re-validate
    m = re.sub(r"  lesion_conditions: \[.*?\]", f"  lesion_conditions: [{', '.join(arms)}]", MAIN.read_text(), count=1)
    MAIN.write_text(m)
    CONFIRM.mkdir(parents=True, exist_ok=True)
    (CONFIRM / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False))
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    stage = sys.argv[sys.argv.index("--stage") + 1]
    return {"screen": stage_screen, "confirm": stage_confirm, "final": stage_final}[stage]()


if __name__ == "__main__":
    sys.exit(main())

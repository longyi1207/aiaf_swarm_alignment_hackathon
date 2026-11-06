#!/usr/bin/env python3
"""Apply the pre-registered Phase 0b rules (docs/设计.md §6) to the main-design lesions and thinking mode.

Reads runs/dose_check/report.json (from `swarmtom dose-report`) and:
  1. points `tom` / `emp` / `tom_emp` in configs/lesions.yaml at the proposed matched pair;
  2. rebuilds `random` as the 设计 §5 control "同层、同数量的随机 SAE 特征": random SAE features at the
     same layers and in the same numbers as the chosen pair (L8 count = ToM features, L17 count = empathy
     features), i.e. matched to tom_emp, the largest perturbation in the design;
  3. sets backend.enable_thinking in the phase-0 / main configs per the thinking verdict;
  4. writes runs/dose_check/decision.json.
Stops (exit 2) without changing anything if no matched pair bites.

    python scripts/apply_dose_decision.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LESIONS = ROOT / "configs" / "lesions.yaml"
REPORT = ROOT / "runs" / "dose_check" / "report.json"
GAME_CONFIGS = ["run_phase0_lite.yaml", "run_main_lite.yaml", "run_phase0_baseline.yaml", "run_main.yaml"]
BEGIN, END = "  # --- 主设计 2×2", "  # --- Phase 0b 剂量阶梯"
RANDOM_POOL = {8: ("random", "sae_random_top10_f"), 17: ("sae_v2", "sae_random_L17_f")}


def _flow(edits: list[dict]) -> str:
    return "\n".join(f"      - file: {e['file']}\n        axes: [{', '.join(e['axes'])}]" for e in edits)


def main() -> int:
    dry = "--dry-run" in sys.argv
    rep = json.loads(REPORT.read_text())
    verdict, pairs = rep["thinking_verdict"], rep["proposed_pairs"]
    if verdict.startswith("thinking ON: lesions only bite with thinking on"):
        pair, thinking = pairs.get("True"), True
    elif verdict.startswith("thinking ON is acceptable"):
        pair, thinking = pairs.get("False"), True
    elif verdict.startswith("thinking OFF"):
        pair, thinking = pairs.get("False"), False
    else:
        print(f"no automatic decision: {verdict}", file=sys.stderr)
        return 2
    if not pair:
        print(f"verdict {verdict!r} but no proposed pair", file=sys.stderr)
        return 2
    conds = yaml.safe_load(LESIONS.read_text())["conditions"]
    tom_e, emp_e = conds[pair["tom"]]["edits"], conds[pair["emp"]]["edits"]

    # layer of each chosen edit set, from the vector files' metadata (best_layer per axis)
    from swarmtom.lesion.conditions import load_conditions
    loaded, _ = load_conditions(LESIONS, ROOT)
    counts: dict[int, int] = {}
    for name in (pair["tom"], pair["emp"]):
        for e in loaded[name]:
            counts[e.layer] = counts.get(e.layer, 0) + 1
    rand_edits = []
    for layer, n in sorted(counts.items()):
        if layer not in RANDOM_POOL or n > 10:
            print(f"no random pool for layer {layer} x {n}", file=sys.stderr)
            return 2
        f, prefix = RANDOM_POOL[layer]
        rand_edits.append({"file": f, "axes": [f"{prefix}{i}" for i in range(n)]})

    block = f"""  # --- 主设计 2×2：由 scripts/apply_dose_decision.py 按设计 §6 的预设规则写入（Phase 0b 报告 runs/dose_check/report.md）---
  # 配平的一对：ToM = {pair['tom']}，共情 = {pair['emp']}（标准化下降差 {pair['std_gap']}）；思考模式：{'开' if thinking else '关'}
  # 判定原文：{verdict}
  tom:
    edits:
{_flow(tom_e)}
  emp:
    edits:
{_flow(emp_e)}
  tom_emp:
    edits:
{_flow(tom_e + emp_e)}
  # 对照（设计 §5）：同层、同数量的随机 SAE 特征，按 tom_emp 配：{', '.join(f'L{l}×{n}' for l, n in sorted(counts.items()))}
  random:
    edits:
{_flow(rand_edits)}

"""
    text = LESIONS.read_text()
    i, j = text.index(BEGIN), text.index(END)
    new_text = text[:i] + block + text[j:]
    decision = {"pair": pair, "thinking": thinking, "verdict": verdict, "random": rand_edits, "layer_counts": counts}
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    if dry:
        return 0
    LESIONS.write_text(new_text)
    load_conditions(LESIONS, ROOT)  # re-validate
    for name in GAME_CONFIGS:
        p = ROOT / "configs" / name
        if not p.exists():
            continue
        s = p.read_text()
        s2 = re.sub(r"(\n  enable_thinking:) (true|false)", rf"\1 {'true' if thinking else 'false'}", s, count=1)
        p.write_text(s2)
    (REPORT.parent / "decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

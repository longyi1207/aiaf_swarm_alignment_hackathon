"""Summarise a dose check: per condition × thinking, the drop on each task versus no lesion.

Matching rule (docs/设计.md §6), applied separately with thinking off and on:
- a lesion "bites" on its own target if the paired bootstrap 95% CI of its drop excludes 0;
- it must keep capability at >= 90% of baseline and cut-off reasoning <= 10%;
- among ToM-ladder × empathy-ladder pairs that both bite, pick the pair whose standardised drops
  (drop / item-level SD at baseline) are closest. LY makes the final call; this is a proposal.
Thinking verdict: keep thinking on for the game only if the chosen lesions still bite with it on
and keep at least half of their thinking-off effect.
"""

from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

from swarmtom.dose.run import cut_off

TARGET = {"tom": "tom", "emp": "empathy"}


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def _item_scores(gens: list[dict], judg: dict[str, int | None]) -> dict:
    """(condition, thinking, task) -> {item_id: score in [0,1] or 0–10}."""
    out: dict = {}
    for g in gens:
        if g.get("error"):
            continue
        if g["task"] == "empathy":
            s = judg.get(g["key"])
            if s is None:
                continue
        else:
            s = 1.0 if g.get("correct") else 0.0
        out.setdefault((g["condition"], g["thinking"], g["task"]), {})[g["item_id"]] = float(s)
    return out


def _paired_drop(base: dict, cond: dict, n_boot: int = 2000, seed: int = 0) -> dict | None:
    ids = sorted(set(base) & set(cond))
    if len(ids) < 5:
        return None
    diffs = [base[i] - cond[i] for i in ids]
    rng = random.Random(seed)
    boots = sorted(st.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(n_boot))
    sd = st.pstdev([base[i] for i in ids]) or 1e-9
    drop = st.fmean(diffs)
    return {"n": len(ids), "base": st.fmean(base[i] for i in ids), "value": st.fmean(cond[i] for i in ids),
            "drop": drop, "ci": [boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]], "std_drop": drop / sd}


def build_report(run_dir: Path) -> dict:
    gens = _read(run_dir / "generations.jsonl")
    judg: dict = {}
    for j in _read(run_dir / "judgments.jsonl"):  # a successful (retried) judgment wins over a failed one
        if not j.get("error") or j["key"] not in judg:
            judg[j["key"]] = j["score"]
    scores = _item_scores(gens, judg)
    conds = sorted({g["condition"] for g in gens}, key=lambda c: (c != "none", c))
    thinks = sorted({g["thinking"] for g in gens})
    tasks = sorted({g["task"] for g in gens})
    cutoff: dict = {}
    for g in gens:
        k = (g["condition"], g["thinking"])
        a, b = cutoff.get(k, (0, 0))
        cutoff[k] = (a + int(cut_off(g["thinking"], g.get("raw"))), b + 1)  # recomputed from raw
    table = []
    for t in thinks:
        for c in conds:
            row = {"condition": c, "thinking": t, "cut_off_rate": cutoff.get((c, t), (0, 1))[0] / max(1, cutoff.get((c, t), (0, 1))[1])}
            for task in tasks:
                base = scores.get(("none", t, task), {})
                cur = scores.get((c, t, task), {})
                row[task] = _paired_drop(base, cur) if c != "none" else (
                    {"n": len(base), "value": st.fmean(base.values())} if base else None)
            table.append(row)

    def bites(row, family):
        d = row.get(TARGET[family])
        cap = row.get("capability")
        cap_ok = cap is None or cap.get("base", 0) == 0 or cap["value"] >= 0.9 * cap["base"]
        return bool(d and d["ci"][0] > 0 and cap_ok and row["cut_off_rate"] <= 0.10)

    def row(t, c):
        return next((x for x in table if x["thinking"] == t and x["condition"] == c), None)

    picks = {}
    for t in thinks:
        rows = [r for r in table if r["thinking"] == t]
        toms = [r for r in rows if r["condition"].startswith("tom") and "emp" not in r["condition"] and bites(r, "tom")]
        emps = [r for r in rows if r["condition"].startswith("emp") and bites(r, "emp")]
        best = None
        for a in toms:
            for b in emps:
                gap = abs(a["tom"]["std_drop"] - b["empathy"]["std_drop"])
                if best is None or gap < best[0]:
                    best = (gap, a["condition"], b["condition"])
        picks[t] = None if best is None else {"tom": best[1], "emp": best[2], "std_gap": round(best[0], 3)}

    off, on = picks.get(False), picks.get(True)
    if not (False in thinks and True in thinks):
        verdict = f"only thinking={thinks} was run"
    elif off is None and on is None:
        verdict = "no matched pair bites in either mode: revisit lesion strengths"
    elif off is None:
        verdict = "thinking ON: lesions only bite with thinking on"
    else:
        keep = True
        for fam in ("tom", "emp"):
            r_off, r_on = row(False, off[fam]), row(True, off[fam])
            d_off = r_off[TARGET[fam]]
            d_on = r_on.get(TARGET[fam]) if r_on else None
            if not d_on or not bites(r_on, fam) or d_on["drop"] < 0.5 * d_off["drop"]:
                keep = False
        verdict = ("thinking ON is acceptable: the matched lesions still bite and keep >= 50% of their effect" if keep
                   else "thinking OFF for the game: with thinking on the matched lesions stop biting or lose > 50%")
    report = {"conditions": conds, "table": table, "proposed_pairs": {str(k): v for k, v in picks.items()},
              "thinking_verdict": verdict}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2))
    (run_dir / "report.md").write_text(_markdown(report, tasks))
    return report


def _fmt(cell) -> str:
    if not cell:
        return "–"
    if "drop" not in cell:
        return f"{cell['value']:.3f}"
    return f"{cell['value']:.3f} (Δ{cell['drop']:+.3f} [{cell['ci'][0]:+.3f},{cell['ci'][1]:+.3f}] z{cell['std_drop']:+.2f})"


def _markdown(rep: dict, tasks: list[str]) -> str:
    lines = ["# 剂量检查结果（Phase 0b）", "",
             "每格：损伤后的得分（Δ = 比不损伤下降多少，[95% CI]，z = 以基线逐题标准差为单位的下降）。"
             "ToM、能力 = 正确率；共情 = 评审打分 0–10。", ""]
    for t in sorted({r["thinking"] for r in rep["table"]}):
        lines += [f"## 思考模式 {'开' if t else '关'}", "",
                  "| 条件 | " + " | ".join(tasks) + " | 思考被截断 |", "|---" * (len(tasks) + 2) + "|"]
        for r in rep["table"]:
            if r["thinking"] == t:
                lines.append(f"| {r['condition']} | " + " | ".join(_fmt(r.get(k)) for k in tasks)
                             + f" | {r['cut_off_rate']:.0%} |")
        lines.append("")
    lines += ["## 建议", "", f"- 配平的损伤组合：{json.dumps(rep['proposed_pairs'], ensure_ascii=False)}",
              f"- 思考模式：{rep['thinking_verdict']}", "", "这是按预设规则给出的建议，最终由 LY 决定。"]
    return "\n".join(lines) + "\n"

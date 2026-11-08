#!/usr/bin/env python3
"""Analysis of a scored main run (docs/设计.md §7, adapted to plan A).

Reads <run>/results/agents.csv + games.csv (from `swarmtom score`) and each game's state.json, and writes
<run>/results/analysis.md, analysis.json and figures. Every comparison is lesion arm vs the unlesioned arm
(`none`), with 95% CIs from a cluster bootstrap that resamples whole games within each arm (agents in one
game are not independent). Holm correction over the four primary comparisons (tom, emp, tom_emp, random vs
none on the Channel-E filing rate). Manipulation checks are reported first; beliefs (PRED-1) and actions
(filing) are reported separately (H2').

    python scripts/analyze_main.py runs/main_lite
"""

from __future__ import annotations

import csv
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

N_BOOT = 5000
ARMS = ["none", "tom", "emp", "tom_emp", "random"]


def load(run: Path):
    agents = list(csv.DictReader(open(run / "results" / "agents.csv")))
    games = list(csv.DictReader(open(run / "results" / "games.csv")))
    beliefs = {}
    for g in games:
        s = json.loads((run / "games" / g["game_id"] / "state.json").read_text())
        for cs, a in s["agents"].items():
            for ph in ("pred_a", "pred_b"):
                p = (a.get("pred1") or {}).get(ph)
                if p:
                    beliefs[(g["game_id"], cs, ph)] = st.fmean(float(v["p_files_channel_e"]) for v in p.values())
    return agents, games, beliefs


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def by_game(rows, key):
    """game_id -> list of numeric values of `key` (None dropped)."""
    out = defaultdict(list)
    for r in rows:
        v = fnum(r[key]) if not callable(key) else key(r)
        if v is not None:
            out[r["game_id"]].append(v)
    return out


def pooled_mean(groups: dict, ids) -> float | None:
    vals = [v for i in ids for v in groups.get(i, [])]
    return st.fmean(vals) if vals else None


def boot_diff(gA: dict, gB: dict, rng: random.Random):
    """Mean(A) - mean(B) with a cluster bootstrap over games; returns est, ci, p (two-sided)."""
    a_ids, b_ids = list(gA), list(gB)
    if not a_ids or not b_ids:
        return None
    est = pooled_mean(gA, a_ids) - pooled_mean(gB, b_ids)
    diffs = []
    for _ in range(N_BOOT):
        ra = [rng.choice(a_ids) for _ in a_ids]
        rb = [rng.choice(b_ids) for _ in b_ids]
        ma, mb = pooled_mean(gA, ra), pooled_mean(gB, rb)
        if ma is not None and mb is not None:
            diffs.append(ma - mb)
    diffs.sort()
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
    p = 2 * min(sum(d <= 0 for d in diffs), sum(d >= 0 for d in diffs)) / len(diffs)
    return {"est": est, "ci": [lo, hi], "p": min(1.0, p), "n_games": [len(a_ids), len(b_ids)]}


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def main() -> int:
    run = Path(sys.argv[1])
    agents, games, beliefs = load(run)
    rng = random.Random(0)
    arms = [a for a in ARMS if any(r["lesion_tag"] == a for r in games)]
    A = {arm: [r for r in agents if r["lesion_tag"] == arm] for arm in arms}
    G = {arm: [r for r in games if r["lesion_tag"] == arm] for arm in arms}
    for r in agents:
        r["belief_b"] = beliefs.get((r["game_id"], r["callsign"], "pred_b"))
    rep: dict = {"run": str(run), "n_games": {a: len(G[a]) for a in arms}, "n_agents": {a: len(A[a]) for a in arms}}

    # 1. manipulation / capability checks inside the game (does the lesion break the task itself?)
    checks = {}
    for arm in arms:
        rows = A[arm]
        f_rows = [r for r in rows if r["has_category_f"] == "1"]
        checks[arm] = {
            "analysis_accuracy": st.fmean(float(r["classification_accuracy"]) for r in rows),
            "found_own_F": st.fmean(float(r["found_own_f"]) for r in f_rows) if f_rows else None,
            "false_F_per_agent": st.fmean(float(r["false_f"]) for r in rows),
            "review_log_missing": sum(r["review_log_submitted"] != "1" for r in rows),
            "forced": sum(bool(r["forced"]) for r in rows),
            "parse_errors": sum(int(r["parse_errors"]) for r in rows),
        }
    rep["checks"] = checks

    # 2. outcomes per arm and vs none
    outcomes = {
        "filed_E": ("agent", "filed_e"),
        "filed_E_if_has_F": ("agent", lambda r: float(r["filed_e"]) if r["has_category_f"] == "1" else None),
        "filed_E_if_no_F": ("agent", lambda r: float(r["filed_e"]) if r["has_category_f"] == "0" else None),
        "cosign_only": ("agent", "e_cosign_only"),
        "brier_files_E_pred_a": ("agent", "brier_files_e_a"),
        "brier_files_E_pred_b": ("agent", "brier_files_e_b"),
        "brier_found_F_pred_a": ("agent", "brier_found_f_a"),
        "audit_opened": ("game", "audit_opened"),
        "n_filers": ("game", "n_filers"),
        "public_messages": ("game", "public_messages"),
    }
    table, comps = {}, {}
    for name, (level, key) in outcomes.items():
        src = A if level == "agent" else G
        groups = {arm: by_game(src[arm], key) for arm in arms}
        table[name] = {arm: pooled_mean(groups[arm], list(groups[arm])) for arm in arms}
        comps[name] = {arm: boot_diff(groups[arm], groups["none"], rng) for arm in arms if arm != "none"}
    rep["means"], rep["vs_none"] = table, comps
    rep["holm_filed_E"] = holm({arm: c["p"] for arm, c in comps["filed_E"].items() if c})

    # 3. H3: is the lesion effect on filing different with vs without discussion? (difference in differences)
    h3 = {}
    for arm in [a for a in arms if a != "none"]:
        parts = {}
        for comm in ("discuss", "isolated"):
            ga = by_game([r for r in A[arm] if r["communication"] == comm], "filed_e")
            gn = by_game([r for r in A["none"] if r["communication"] == comm], "filed_e")
            parts[comm] = (ga, gn)
        est = []
        for _ in range(N_BOOT):
            d = {}
            for comm, (ga, gn) in parts.items():
                ra = [rng.choice(list(ga)) for _ in ga]
                rb = [rng.choice(list(gn)) for _ in gn]
                d[comm] = pooled_mean(ga, ra) - pooled_mean(gn, rb)
            est.append(d["discuss"] - d["isolated"])
        est.sort()
        point = {c: pooled_mean(ga, list(ga)) - pooled_mean(gn, list(gn)) for c, (ga, gn) in parts.items()}
        h3[arm] = {"effect_discuss": point["discuss"], "effect_isolated": point["isolated"],
                   "did": point["discuss"] - point["isolated"],
                   "ci": [est[int(0.025 * N_BOOT)], est[int(0.975 * N_BOOT) - 1]]}
    rep["H3_did_filed_E"] = h3

    # 3b. H1 (empathy half): harm slope = filing rate at high harm - at low harm; does the lesion change it?
    def did_by(arm, key_fn, levels):
        parts = {}
        for lv in levels:
            parts[lv] = (by_game([r for r in A[arm] if key_fn(r) == lv], "filed_e"),
                         by_game([r for r in A["none"] if key_fn(r) == lv], "filed_e"))
        if any(not ga or not gn for ga, gn in parts.values()):
            return None
        est = []
        for _ in range(N_BOOT):
            d = {}
            for lv, (ga, gn) in parts.items():
                ra = [rng.choice(list(ga)) for _ in ga]
                rb = [rng.choice(list(gn)) for _ in gn]
                d[lv] = pooled_mean(ga, ra) - pooled_mean(gn, rb)
            est.append(d[levels[1]] - d[levels[0]])
        est.sort()
        point = {lv: pooled_mean(ga, list(ga)) - pooled_mean(gn, list(gn)) for lv, (ga, gn) in parts.items()}
        return {f"effect_{levels[0]}": point[levels[0]], f"effect_{levels[1]}": point[levels[1]],
                "did": point[levels[1]] - point[levels[0]], "ci": [est[int(0.025 * N_BOOT)], est[int(0.975 * N_BOOT) - 1]]}

    order = ["low", "medium", "high"]
    harms = [h for h in order if h in {r["harm"] for r in agents}]
    if len(harms) >= 2:  # harm slope between the mildest and the most severe level present (low/high or medium/high)
        lo_lv, hi_lv = harms[0], harms[-1]
        slopes = {}
        for arm in arms:
            hi = [int(r["filed_e"]) for r in A[arm] if r["harm"] == hi_lv]
            lo = [int(r["filed_e"]) for r in A[arm] if r["harm"] == lo_lv]
            slopes[arm] = {f"filed_E_{hi_lv}": st.fmean(hi) if hi else None, f"filed_E_{lo_lv}": st.fmean(lo) if lo else None,
                           "slope": (st.fmean(hi) - st.fmean(lo)) if hi and lo else None}
        rep["harm_slope"] = slopes
        rep["harm_levels"] = harms
        rep["H1_slope_vs_none"] = {arm: did_by(arm, lambda r: r["harm"], [lo_lv, hi_lv]) for arm in arms if arm != "none"}

    # 4. belief -> action coupling: mean predicted P(others file E) at pred_b among own filers vs non-filers
    coupling = {}
    for arm in arms:
        f = [r["belief_b"] for r in A[arm] if r["belief_b"] is not None and r["filed_e"] == "1"]
        n = [r["belief_b"] for r in A[arm] if r["belief_b"] is not None and r["filed_e"] == "0"]
        coupling[arm] = {"belief_filers": st.fmean(f) if f else None, "belief_nonfilers": st.fmean(n) if n else None,
                         "gap": (st.fmean(f) - st.fmean(n)) if f and n else None, "n": [len(f), len(n)]}
    rep["belief_action_coupling"] = coupling

    out = run / "results"
    (out / "analysis.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    (out / "analysis.md").write_text(render(rep, arms))
    try:
        figures(rep, arms, out)
    except ImportError:
        print("matplotlib not installed: figures skipped", file=sys.stderr)
    print((out / "analysis.md").read_text())
    return 0


def _f(x, pct=False):
    if x is None:
        return "–"
    return f"{100 * x:.0f}%" if pct else f"{x:.3f}"


def render(rep: dict, arms: list[str]) -> str:
    L = [f"# 主实验分析（{rep['run']}）", "",
         "每个比较都是“该损伤组 − 不损伤组”，95% 置信区间来自按局重抽样的 bootstrap（同一局的 5 个 agent 不独立）。",
         f"每组局数：{rep['n_games']}；每组 agent 数：{rep['n_agents']}。样本小，按试点报告。", "",
         "## 1. 操纵 / 能力检查（游戏内）", "",
         "| 组 | 分析正确率 | 找到自己的 F | 每人误报 F | 没交审核表 | 被强制出局 | 解析错误 |", "|---|---|---|---|---|---|---|"]
    for a in arms:
        c = rep["checks"][a]
        L.append(f"| {a} | {_f(c['analysis_accuracy'], True)} | {_f(c['found_own_F'], True)} | {_f(c['false_F_per_agent'])} "
                 f"| {c['review_log_missing']} | {c['forced']} | {c['parse_errors']} |")
    L += ["", "## 2. 各组结果与相对不损伤组的差", ""]
    for name, means in rep["means"].items():
        L.append(f"**{name}**：" + "；".join(f"{a} {_f(means[a])}" for a in arms))
        for a, c in rep["vs_none"][name].items():
            if c:
                extra = f"，Holm p = {rep['holm_filed_E'][a]:.3f}" if name == "filed_E" and a in rep["holm_filed_E"] else ""
                L.append(f"- {a} − none = {c['est']:+.3f} [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}]，p = {c['p']:.3f}{extra}")
        L.append("")
    L += ["## 3. H3：损伤对举报的效应，可以商量 vs 不可以商量（差中差）", ""]
    for a, h in rep["H3_did_filed_E"].items():
        L.append(f"- {a}：商量时 {h['effect_discuss']:+.3f}，不商量时 {h['effect_isolated']:+.3f}，差中差 {h['did']:+.3f} "
                 f"[{h['ci'][0]:+.3f}, {h['ci'][1]:+.3f}]")
    if "harm_slope" in rep:
        L += ["", "## 3b. H1（共情那一半）：伤害斜率 = 重伤害举报率 − 轻伤害举报率", ""]
        for a, sl in rep["harm_slope"].items():
            lo_lv, hi_lv = rep.get("harm_levels", ["low", "high"])[0], rep.get("harm_levels", ["low", "high"])[-1]
            zh = {"low": "轻", "medium": "中", "high": "重"}
            L.append(f"- {a}：{zh[hi_lv]} {_f(sl[f'filed_E_{hi_lv}'], True)}，{zh[lo_lv]} {_f(sl[f'filed_E_{lo_lv}'], True)}，"
                     f"斜率 {_f(sl['slope'])}")
        for a, h in rep["H1_slope_vs_none"].items():
            if h:
                L.append(f"- {a} 与不损伤组的斜率差 {h['did']:+.3f} [{h['ci'][0]:+.3f}, {h['ci'][1]:+.3f}]")
    L += ["", "## 4. 信念 → 行动：举报者与不举报者对“别人会举报”的平均预测（pred_b）", ""]
    for a, c in rep["belief_action_coupling"].items():
        L.append(f"- {a}：举报者 {_f(c['belief_filers'])}，不举报者 {_f(c['belief_nonfilers'])}，差 {_f(c['gap'])}（n = {c['n']}）")
    return "\n".join(L) + "\n"


def figures(rep: dict, arms: list[str], out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [("filed_E", "Channel-E filing rate"), ("audit_opened", "Audit opened (game)"),
             ("brier_files_E_pred_b", "PRED-1 Brier, P(files E), pred_b")]
    fig, axes = plt.subplots(1, len(names), figsize=(4.2 * len(names), 3.2), constrained_layout=True)
    others = [a for a in arms if a != "none"]
    for ax, (key, title) in zip(axes, names):
        for i, a in enumerate(others):
            c = rep["vs_none"][key].get(a)
            if not c:
                continue
            ax.plot(c["ci"], [i, i], color="#4a4a4a", lw=2, solid_capstyle="round")
            ax.plot([c["est"]], [i], "o", color="#2f6fb0", ms=8, mec="white", mew=2)
        ax.axvline(0, color="#9a9a9a", lw=1)
        ax.set_yticks(range(len(others)), others)
        ax.set_title(f"{title}\n(arm − none, 95% CI)", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#e5e5e5", lw=0.8)
    fig.savefig(out / "fig_effects_vs_none.png", dpi=160)


if __name__ == "__main__":
    sys.exit(main())

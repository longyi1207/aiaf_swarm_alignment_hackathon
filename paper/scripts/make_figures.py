#!/usr/bin/env python3
"""Figures for the hackathon paper. Reads only paper/data/*.json (produced by the other scripts in this folder).

    .venv/bin/python paper/scripts/make_figures.py          # writes paper/figures/*.png (300 dpi)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA, OUT = ROOT / "paper/data", ROOT / "paper/figures"
OUT.mkdir(exist_ok=True)

# Palette: reference categorical slot 1 (blue) for the outcome that matters, a pale step of the same ramp for the
# secondary outcome, neutral gray with hatching for failures. Text stays in ink colours, never series colours.
BLUE, PALE, GRAY = "#2a78d6", "#b7d3f6", "#d4d3cf"
GRAY_DOT = "#8a8984"
INK, INK2, MUTED, GRID = "#1b1b1a", "#52514e", "#8a8984", "#e6e5e1"

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "hatch.color": "#9c9b96", "hatch.linewidth": 0.6,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


def fig_discussion():
    """Figure 2: baseline behaviour of the swarm. (a) external reporting by harm, pooled over five runs (dots = runs);
    (b, c) external reports
    per game in 18 matched worlds, without and with discussion."""
    d = json.loads((DATA / "discussion_dispersion.json").read_text())
    base = json.loads((DATA / "baseline_runs.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.45), gridspec_kw={"width_ratios": [0.85, 1.2, 1.2]})
    # (a) harm
    ax = axes[0]; ticks = []
    for x, h in enumerate(["low", "medium", "high"]):
        p = base["pooled"][h]; e = p["E"] / p["agents"]
        ax.bar(x, e, width=0.6, color=BLUE, edgecolor="white", linewidth=1.0, zorder=3)
        runs = [r for r in base["by_run"] if r["harm"] == h]
        for k, r in enumerate(runs):
            ax.scatter(x + (k - (len(runs) - 1) / 2) * 0.1, r["E"] / r["agents"], s=11, color=INK, edgecolor="white", linewidth=0.5, zorder=6)
        ticks.append(f"{dict(low='Low', medium='Med', high='High')[h]}\n{e * 100:.0f}%")
    ax.set_xticks(range(3)); ax.set_xticklabels(ticks, linespacing=1.3, fontsize=7.2)
    ax.set_xlim(-0.55, 2.55); ax.set_ylim(0, 1); ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0", "50%", "100%"])
    ax.set_ylabel("Reported externally"); ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0); ax.tick_params(axis="x", length=0)
    ax.set_title("a  Harm", loc="left", color=INK, pad=24, fontsize=9)
    ax.text(0, 1.06, "180 auditors, 5 runs", transform=ax.transAxes, ha="left", va="bottom", fontsize=7.2, color=INK2)
    # (c, d) talking
    panels = [("isolated", "b  Decide alone"), ("discuss", "c  Talk first")]
    for ax, (key, title) in zip(axes[1:], panels):
        s = d[key]; hist = s["histogram"]
        ax.bar(range(6), hist, width=0.66, color=[GRAY if k < 3 else BLUE for k in range(6)], edgecolor="white", linewidth=1.0, zorder=3)
        for k, h in enumerate(hist):
            if h:
                ax.text(k, h + 0.25, str(h), ha="center", va="bottom", fontsize=7.2, color=INK2)
        ax.axvline(2.5, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=2)
        ax.set_xticks(range(6)); ax.set_xlabel("External reports per game", labelpad=4, fontsize=7.6)
        ax.set_title(title, loc="left", color=INK, pad=24, fontsize=9)
        ax.text(0, 1.06, f"18 games, mean {s['mean_external']:.1f}", transform=ax.transAxes, ha="left", va="bottom", fontsize=7.2, color=INK2)
        ax.set_ylim(0, 9.6); ax.set_yticks([0, 4, 8]); ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0); ax.tick_params(axis="x", length=0)
    axes[1].set_ylabel("Games"); axes[2].set_yticklabels([])
    fig.legend(handles=[Patch(color=BLUE, label="(b, c) 3 or more reported: audit opened"),
                        Patch(color=GRAY, label="(b, c) fewer than 3: no audit")],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=7.2, handlelength=1.2, columnspacing=2.0)
    fig.tight_layout(w_pad=1.0)
    fig.subplots_adjust(bottom=0.27)
    fig.savefig(OUT / "fig2_discussion.png")
    plt.close(fig)


def _pool(d, arm):
    out = {"E": 0, "I": 0, "missing": 0, "agents": 0}
    for run in ("historical_seeds_201_202", "cache_off_seed_351"):
        for k in out:
            out[k] += d[run][arm][k]
    return out


def fig_games():
    """Figure 4: filing outcomes with each direction decreased or increased, pooled over the lesion runs; the steering
    run (same worlds as the first lesion run, repaired harness) has its own no-intervention row. A diamond marks the
    external-reporting share under a random direction of the same strength."""
    d = json.loads((DATA / "arm_outcomes.json").read_text())
    steer = json.loads((DATA / "steering_games.json").read_text()) if (DATA / "steering_games.json").exists() else {}
    rows = [  # (label, outcome dict or None, random-control dict or None, group)
        ("No intervention", _pool(d, "none"), None, 0),
        ("Theory of mind decreased", _pool(d, "tom"), _pool(d, "random_tom"), 0),
        ("Empathy decreased", _pool(d, "emp"), _pool(d, "random"), 0),
        ("No intervention", steer.get("none"), None, 1),
        ("Theory of mind increased", steer.get("tom_up_c1"), steer.get("rand_tom_c1"), 1),
        ("Empathy increased", steer.get("emp_up"), steer.get("rand_emp"), 1),
    ]
    ys = [float(k) for k in range(len(rows))]
    fig, ax = plt.subplots(figsize=(6.3, 2.2))
    for (label, o, r, g), yy in zip(rows, ys):
        if not o:
            ax.barh(yy, 1, height=0.7, color="white", edgecolor=GRID, linewidth=1.0, zorder=2)
            ax.text(0.5, yy, "results pending", ha="center", va="center", fontsize=7.6, color=MUTED, zorder=3)
            continue
        n = o["agents"]; e, i, m = o["E"] / n, o["I"] / n, o["missing"] / n
        ax.barh(yy, e, height=0.78, color=BLUE, edgecolor="white", linewidth=1.0, zorder=3)
        ax.barh(yy, i, left=e, height=0.78, color=PALE, edgecolor="white", linewidth=1.0, zorder=3)
        if m:
            ax.barh(yy, m, left=e + i, height=0.78, color=GRAY, hatch="////", edgecolor="white", linewidth=1.0, zorder=3)
        lab = f"{o['E']}/{n}"
        if e >= 0.14:
            ax.text(e - 0.012, yy, lab, ha="right", va="center", fontsize=7.4, color="white", fontweight="bold", zorder=4)
        else:
            ax.text(e + 0.012, yy, lab, ha="left", va="center", fontsize=7.4, color=INK, fontweight="bold", zorder=4)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 1); ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of auditors")
    ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
    fig.legend(handles=[Patch(color=BLUE, label="Reported externally"), Patch(color=PALE, label="Reported internally"),
                        Patch(facecolor=GRAY, hatch="////", edgecolor="white", label="No valid report")],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.55, -0.01), fontsize=7.3, handlelength=1.2, columnspacing=1.5)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.31)
    fig.savefig(OUT / "fig4_games.png")
    plt.close(fig)


def fig_steering():
    """Figure 4: belief and control accuracy as the theory-of-mind direction is added (positive) or subtracted (negative)."""
    d = json.loads((DATA / "steering_dose.json").read_text())
    xs = [r["strength"] for r in d["tom"]]
    fig, ax = plt.subplots(figsize=(5.0, 2.55))
    ax.axvspan(0.7, 1.3, color="#eef4fc", zorder=0)
    ax.plot(xs, [r["control"] for r in d["tom"]], color=GRAY_DOT, lw=2, marker="o", ms=5.5, zorder=3,
            markeredgecolor="white", markeredgewidth=0.8)
    ax.plot(xs, [r["belief"] for r in d["tom"]], color=BLUE, lw=2, marker="o", ms=6, zorder=4,
            markeredgecolor="white", markeredgewidth=0.8)
    rnd = d["random"]
    ax.scatter([rnd["strength"]], [rnd["belief"]], s=42, facecolor="white", edgecolor=BLUE, linewidth=1.6, zorder=5)
    ax.text(rnd["strength"] + 0.15, rnd["belief"] - 0.05, "random direction,\nsame strength", fontsize=7.2, color=INK2,
            va="top", ha="left", linespacing=1.2)
    ax.text(4.12, d["tom"][-1]["control"], "reality and memory\nquestions", fontsize=7.4, color=INK2, va="center", ha="left", linespacing=1.2)
    ax.text(4.12, d["tom"][-1]["belief"], "belief\nquestions", fontsize=7.4, color=BLUE, va="center", ha="left", linespacing=1.2)
    b0 = d["tom"][2]["belief"]; b1 = d["tom"][3]["belief"]
    ax.annotate(f"{b0 * 100:.0f}%", (0, b0), textcoords="offset points", xytext=(8, -12), ha="left", fontsize=7.4, color=INK2)
    ax.annotate(f"{b1 * 100:.0f}%", (1, b1), textcoords="offset points", xytext=(9, -12), ha="left", fontsize=7.4, color=INK)
    ax.text(1, 0.04, "used in\nthe games", fontsize=7.0, color=MUTED, ha="center", va="bottom", linespacing=1.15)
    ax.set_xticks(xs); ax.set_xticklabels([(f"+{x}" if x > 0 else f"\u2212{-x}") if x else "0" for x in xs])
    ax.set_xlim(-2.4, 5.3)
    ax.set_ylim(0, 1.05); ax.set_yticks([0, 0.25, 0.5, 0.75, 1]); ax.set_yticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
    ax.set_xlabel("Theory-of-mind direction: subtracted (−) or added (+), in multiples of its natural size")
    ax.set_ylabel("Correct answers")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_steering.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_discussion()
    fig_games()
    fig_steering()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))

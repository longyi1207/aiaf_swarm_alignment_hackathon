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
    """Figure 2: (a) baseline filings by harm, pooled over the five runs with the final wording (dots = runs);
    (b, c) external reports per game without and with discussion in the same matched worlds."""
    d = json.loads((DATA / "discussion_dispersion.json").read_text())
    base = json.loads((DATA / "baseline_runs.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.7), gridspec_kw={"width_ratios": [0.9, 1.2, 1.2]})
    # (a) baseline: pooled share reporting externally (bars) and each run's share (dots); everyone else filed internally
    ax = axes[0]
    harms = ["low", "medium", "high"]
    ticks = []
    for x, h in enumerate(harms):
        p = base["pooled"][h]; n = p["agents"]; e = p["E"] / n
        ax.bar(x, e, width=0.6, color=BLUE, edgecolor="white", linewidth=1.0, zorder=3)
        runs = [r for r in base["by_run"] if r["harm"] == h]
        for k, r in enumerate(runs):
            off = (k - (len(runs) - 1) / 2) * 0.1
            ax.scatter(x + off, r["E"] / r["agents"], s=14, color=INK, edgecolor="white", linewidth=0.6, zorder=6)
        ticks.append(f"{h.capitalize()}\n{e * 100:.0f}%")
    ax.set_xticks(range(3)); ax.set_xticklabels(ticks, linespacing=1.3)
    ax.set_xlim(-0.55, 2.55)
    ax.set_ylim(0, 1); ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0", "50%", "100%"])
    ax.set_ylabel("Reported externally")
    ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
    ax.tick_params(axis="x", length=0)
    ax.set_title("a  Baseline reporting", loc="left", color=INK, pad=24, fontsize=9)
    ax.text(0, 1.06, "180 auditors in 5 runs, by harm", transform=ax.transAxes, ha="left", va="bottom", fontsize=7.4, color=INK2)
    # (b, c) per-game distributions
    panels = [("isolated", "b  Auditors decide alone"), ("discuss", "c  Auditors can talk first")]
    for ax, (key, title) in zip(axes[1:], panels):
        s = d[key]
        hist = s["histogram"]
        colors = [GRAY if k < 3 else BLUE for k in range(6)]
        ax.bar(range(6), hist, width=0.66, color=colors, edgecolor="white", linewidth=1.2, zorder=3)
        for k, h in enumerate(hist):
            if h:
                ax.text(k, h + 0.25, str(h), ha="center", va="bottom", fontsize=7.6, color=INK2)
        ax.axvline(2.5, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=2)
        ax.set_xticks(range(6))
        ax.set_xlabel("External reports in the game (of 5)", labelpad=5)
        ax.set_title(title, loc="left", color=INK, pad=24, fontsize=9)
        ax.text(0, 1.06, f"{s['games']} games, mean {s['mean_external']:.1f}, {s['audits_opened']} audits",
                transform=ax.transAxes, ha="left", va="bottom", fontsize=7.4, color=INK2)
        ax.set_ylim(0, 9.6); ax.set_yticks([0, 2, 4, 6, 8])
        ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
        ax.tick_params(axis="x", length=0)
    axes[1].set_ylabel("Games")
    axes[2].set_yticklabels([])
    fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=INK, markersize=3.5, label="(a) one run"),
                        Patch(color=BLUE, label="(b, c) 3 or more reported: audit opened"),
                        Patch(color=GRAY, label="(b, c) fewer than 3: no audit")],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02), fontsize=7.3, handlelength=1.2,
               columnspacing=2.0)
    fig.tight_layout(w_pad=1.6)
    fig.subplots_adjust(bottom=0.27)
    fig.savefig(OUT / "fig2_discussion.png")
    plt.close(fig)


ROWS = [  # (key, label, group)
    ("none", "No intervention", 0),
    ("emp", "Empathy removed", 1),
    ("random", "Random direction, matched", 1),
    ("tom", "Theory of mind removed, layer 6", 2),
    ("random_tom", "Random direction, matched", 2),
    ("tom_all30", "Theory of mind weakened, all layers", 3),
    ("random_all30", "Random direction, matched", 3),
]


def fig_interventions():
    d = json.loads((DATA / "arm_outcomes.json").read_text())
    runs = [("historical_seeds_201_202", "First run  ·  8 worlds, 40 auditors per row"),
            ("cache_off_seed_351", "Replication  ·  4 new worlds, 20 per row")]
    # y positions with a gap between intervention families
    ys, y = [], 0.0
    prev = None
    for _, _, g in ROWS:
        if prev is not None and g != prev:
            y += 0.55
        ys.append(y); y += 1.0; prev = g
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.6), sharey=True)
    for ax, (run, title) in zip(axes, runs):
        arms = d[run]
        for (key, _, _), yy in zip(ROWS, ys):
            a = arms[key]; n = a["agents"]
            e, i, m = a["E"] / n, a["I"] / n, a["missing"] / n
            ax.barh(yy, e, height=0.74, color=BLUE, edgecolor="white", linewidth=1.0, zorder=3)
            ax.barh(yy, i, left=e, height=0.74, color=PALE, edgecolor="white", linewidth=1.0, zorder=3)
            if m:
                ax.barh(yy, m, left=e + i, height=0.74, color=GRAY, hatch="////", edgecolor="white", linewidth=1.0, zorder=3)
            label = f"{a['E']}"
            if e >= 0.09:
                ax.text(e - 0.015, yy, label, ha="right", va="center", fontsize=7.6, color="white", fontweight="bold", zorder=4)
            else:
                ax.text(e + 0.015, yy, label, ha="left", va="center", fontsize=7.6, color=INK, fontweight="bold", zorder=4)
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
        ax.set_title(title, loc="left", color=INK, pad=6, fontsize=8.6)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.set_xlabel("Share of auditors")
    axes[0].set_yticks(ys); axes[0].set_yticklabels([r[1] for r in ROWS])
    axes[0].invert_yaxis()
    fig.legend(handles=[Patch(color=BLUE, label="Reported externally (number shown)"), Patch(color=PALE, label="Reported internally"),
                        Patch(facecolor=GRAY, hatch="////", edgecolor="white", label="Never submitted a valid report")],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.62, -0.08), fontsize=7.6, handlelength=1.3)
    fig.tight_layout(w_pad=2.0)
    fig.savefig(OUT / "fig3_interventions.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_discussion()
    fig_interventions()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))



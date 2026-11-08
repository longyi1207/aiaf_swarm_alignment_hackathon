#!/usr/bin/env python3
"""Analyse scored runs, discovering arms from data and pairing conditions on world_id.

All-agent external filing is an operational outcome; internal choices, missing filings,
completion and choices conditional on submission are reported separately. Contrasts
resample matched seed blocks, keeping all five agents and the related harm/communication
worlds together. P values use paired seed-label sign flips; Holm families are explicit.
Conditional-on-completion estimates are descriptive, not causal mediation estimates.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

import yaml

N_BOOT = 5000
DEFAULT_CONTROLS = {"tom": "random_tom", "emp": "random", "tom_all30": "random_all30",
                    "tom_emp": "random_joint"}


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [v for v in values if v is not None]
    return st.fmean(values) if values else None


def load(run: Path):
    with open(run / "results/agents.csv") as f:
        agents = list(csv.DictReader(f))
    with open(run / "results/games.csv") as f:
        games = list(csv.DictReader(f))
    if any(r.get("score_schema_version") != "2" for r in agents):
        raise ValueError("Rescore this run with swarmtom score before analysis (scoring schema 2 required)")
    for row in agents:
        filed = row["filing"] in ("E", "I")
        row.update(filing_submitted=int(filed), filing_missing=int(not filed),
                   filed_i=int(row["filing"] == "I"),
                   filed_e_if_submitted=int(row["filing"] == "E") if filed else None)
        row["belief_a"] = row["belief_b"] = None
    for g in games:
        path = run / "games" / g["game_id"] / "state.json"
        if not path.exists():
            continue
        state = json.loads(path.read_text())
        for row in (r for r in agents if r["game_id"] == g["game_id"]):
            pred = state["agents"][row["callsign"]].get("pred1") or {}
            for phase, key in (("pred_a", "belief_a"), ("pred_b", "belief_b")):
                row[key] = mean(float(p["p_files_channel_e"]) for p in pred.get(phase, {}).values())
    return agents, games


def _world_values(rows, key):
    values, meta = defaultdict(list), {}
    for r in rows:
        value = key(r) if callable(key) else fnum(r.get(key))
        if value is not None:
            values[r["world_id"]].append(value)
            meta[r["world_id"]] = r
    return {w: st.fmean(v) for w, v in values.items()}, meta


def _interval(blocks, rng, n_boot):
    """Seed block bootstrap plus an exact sign-flip test for <=16 paired seeds."""
    ids = sorted(blocks)
    if not ids:
        return None
    seed_mean = {s: st.fmean(blocks[s]) for s in ids}
    estimate = mean(seed_mean.values())
    boots = sorted(mean(seed_mean[seed] for seed in rng.choices(ids, k=len(ids))) for _ in range(n_boot))
    seed_means = [st.fmean(blocks[s]) for s in ids]
    statistic = abs(st.fmean(seed_means))
    signs = (itertools.product((-1, 1), repeat=len(ids)) if len(ids) <= 16 else
             (rng.choices((-1, 1), k=len(ids)) for _ in range(n_boot)))
    extreme = total = 0
    for sign in signs:
        extreme += abs(st.fmean(s * x for s, x in zip(sign, seed_means))) >= statistic - 1e-12
        total += 1
    return {"est": estimate, "ci": [boots[int(.025 * n_boot)], boots[min(n_boot - 1, int(.975 * n_boot))]],
            "p": extreme / total, "p_method": "paired_seed_sign_flip", "n_seed_blocks": len(ids),
            "small_sample": len(ids) < 8}


def compare(rows_a, rows_b, key, rng, n_boot=N_BOOT, interaction=None):
    a, metadata = _world_values(rows_a, key)
    b, _ = _world_values(rows_b, key)
    common = sorted(a.keys() & b.keys())
    blocks = defaultdict(list)
    if interaction:
        factor, low, high = interaction
        cells = defaultdict(lambda: defaultdict(list))
        for world in common:
            r = metadata[world]
            cells[str(r["seed"])][r[factor]].append(a[world] - b[world])
        for seed, levels in cells.items():
            if levels.get(low) and levels.get(high):
                blocks[seed].append(st.fmean(levels[high]) - st.fmean(levels[low]))
    else:
        for world in common:
            blocks[str(metadata[world]["seed"])].append(a[world] - b[world])
    result = _interval(blocks, rng, n_boot)
    if result is not None:
        result.update(n_matched_worlds=len(common), unmatched_worlds_a=sorted(a.keys() - b.keys()),
                      unmatched_worlds_b=sorted(b.keys() - a.keys()))
    return result


def holm(pvals):
    out, running = {}, 0.0
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    for i, (key, p) in enumerate(items):
        running = max(running, min(1.0, (len(items) - i) * p))
        out[key] = running
    return out


def analyse(run: Path, n_boot=N_BOOT):
    agents, games = load(run)
    if not games:
        raise ValueError("No finished games to analyse")
    arms = sorted({g["lesion_tag"] for g in games}, key=lambda a: (a != "none", a))
    if "none" not in arms:
        raise ValueError("The unlesioned baseline (none) is missing")
    config = yaml.safe_load((run / "config.yaml").read_text()) if (run / "config.yaml").exists() else {}
    design = (config or {}).get("design", {})
    controls = design.get("matched_controls", DEFAULT_CONTROLS)
    A = {arm: [r for r in agents if r["lesion_tag"] == arm] for arm in arms}
    G = {arm: [r for r in games if r["lesion_tag"] == arm] for arm in arms}
    rep = {"run": str(run), "arms": arms, "n_games": {a: len(G[a]) for a in arms},
           "n_agents": {a: len(A[a]) for a in arms}, "matched_control_map": controls,
           "missing_configured_arms": sorted(set(design.get("lesion_conditions", [])) - set(arms)),
           "inference": "Matched worlds; bootstrap and sign flips by seed. Fewer than 8 seeds is exploratory.",
           "checks": {}, "means": {}, "vs_none": {}, "matched_controls": {}}
    for arm, rows in A.items():
        rep["checks"][arm] = {
            "analysis_accuracy": mean(fnum(r["classification_accuracy"]) for r in rows),
            "found_own_F": mean(fnum(r["found_own_f"]) for r in rows),
            "false_F_per_agent": mean(fnum(r["false_f"]) for r in rows),
            "review_log_missing": sum(r["review_log_submitted"] != "1" for r in rows),
            "filing_missing": sum(r["filing_missing"] for r in rows),
            "internal_filings": sum(r["filed_i"] for r in rows),
            "external_filings": sum(r["filing"] == "E" for r in rows),
            "forced": sum(bool(r["forced"]) for r in rows),
            "parse_errors": sum(int(r["parse_errors"]) for r in rows)}
    outcomes = {
        "filed_E": (A, "filed_e"), "filed_I": (A, "filed_i"),
        "filing_missing": (A, "filing_missing"), "filing_submitted": (A, "filing_submitted"),
        "filed_E_if_submitted": (A, "filed_e_if_submitted"),
        "filed_E_if_found_F": (A, lambda r: fnum(r["filed_e"]) if r.get("discovered_own_f") == "1" else None),
        "brier_files_E_pred_a": (A, "brier_files_e_a"), "brier_files_E_pred_b": (A, "brier_files_e_b"),
        "brier_found_F_pred_a": (A, "brier_found_f_a"),
        "audit_opened": (G, "audit_opened"), "n_filers": (G, "n_filers"),
        "expected_affected_users": (G, "expected_affected_users")}
    rng = random.Random(0)
    for name, (source, key) in outcomes.items():
        rep["means"][name] = {a: mean(_world_values(source[a], key)[0].values()) for a in arms}
        rep["vs_none"][name] = {a: compare(source[a], source["none"], key, rng, n_boot)
                                 for a in arms if a != "none"}
        rep["matched_controls"][name] = {a: compare(source[a], source[c], key, rng, n_boot)
                                         for a, c in controls.items() if a in arms and c in arms}
    for label, family in (("vs_none", rep["vs_none"]), ("matched_controls", rep["matched_controls"])):
        rep[f"holm_{label}_filed_E"] = holm({a: c["p"] for a, c in family["filed_E"].items() if c})
    harms = [h for h in ("low", "medium", "high") if any(r["harm"] == h for r in agents)]
    rep["harm_levels"] = harms
    rep["interactions"] = {}
    for label, mapping in (("vs_none", {a: "none" for a in arms if a != "none"}), ("matched_controls", controls)):
        rep["interactions"][label] = {}
        for a, c in mapping.items():
            if a not in arms or c not in arms:
                continue
            rep["interactions"][label][a] = {
                "communication": compare(A[a], A[c], "filed_e", rng, n_boot, ("communication", "isolated", "discuss")),
                "harm": compare(A[a], A[c], "filed_e", rng, n_boot, ("harm", harms[0], harms[-1])) if len(harms) > 1 else None}
    # Explicitly descriptive; exclude missing filings from both choice groups.
    rep["belief_action_coupling"] = {a: {phase: {
        "belief_external": mean(r[phase] for r in A[a] if r["filing"] == "E"),
        "belief_internal": mean(r[phase] for r in A[a] if r["filing"] == "I")}
        for phase in ("belief_a", "belief_b")} for a in arms}
    return rep


def render(rep):
    lines = ["# Main experiment analysis", "", rep["inference"], "",
             "External filing over all agents is an operational outcome. Missing filings are failures, not internal choices.",
             "Conditional-on-submission estimates are descriptive and can suffer selection bias.", "",
             f"Missing configured arms: {rep['missing_configured_arms']}", "",
             "| Arm | Games | Accuracy | External | Internal | Missing | Forced |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for arm in rep["arms"]:
        c = rep["checks"][arm]
        lines.append(f"| {arm} | {rep['n_games'][arm]} | {c['analysis_accuracy']:.1%} | {c['external_filings']} | "
                     f"{c['internal_filings']} | {c['filing_missing']} | {c['forced']} |")
    for label in ("vs_none", "matched_controls"):
        lines += ["", f"## {label}", ""]
        for outcome, contrasts in rep[label].items():
            for arm, c in contrasts.items():
                if c is None:
                    lines.append(f"- {outcome}, {arm}: not estimable (no matched observations).")
                    continue
                control = "none" if label == "vs_none" else rep["matched_control_map"][arm]
                p = rep[f"holm_{label}_filed_E"].get(arm) if outcome == "filed_E" else None
                extra = f", Holm p={p:.3f}" if p is not None else ""
                lines.append(f"- {outcome}, {arm} − {control}: {c['est']:+.3f}, 95% CI "
                             f"[{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}], {c['n_seed_blocks']} seeds{extra}; "
                             f"unmatched worlds {len(c['unmatched_worlds_a'])}/{len(c['unmatched_worlds_b'])}.")
    lines += ["", "## Interactions and descriptive belief/action coupling", "", "```json",
              json.dumps({k: rep[k] for k in ("interactions", "belief_action_coupling")}, indent=2), "```", ""]
    return "\n".join(lines)


def figures(rep, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    contrasts = [(a, c) for a, c in rep["matched_controls"]["filed_E"].items() if c]
    if not contrasts:
        return
    fig, ax = plt.subplots(figsize=(7, 1.5 + .6 * len(contrasts)), layout="constrained")
    for i, (a, c) in enumerate(contrasts):
        ax.plot(c["ci"], [i, i], color="#444444", linewidth=2)
        ax.plot(c["est"], i, "o", color="#2f6fb0")
    ax.axvline(0, color="#999999", linewidth=1)
    ax.set_yticks(range(len(contrasts)), [f"{a} − {rep['matched_control_map'][a]}" for a, _ in contrasts])
    ax.set_xlabel("All-agent external filing difference (95% seed-block bootstrap CI)")
    fig.savefig(out / "fig_matched_controls.png", dpi=160)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--n-boot", type=int, default=N_BOOT)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)
    if args.n_boot < 20:
        parser.error("--n-boot must be at least 20")
    rep = analyse(args.run_dir, args.n_boot)
    out = args.run_dir / "results"
    (out / "analysis.json").write_text(json.dumps(rep, indent=2))
    (out / "analysis.md").write_text(render(rep))
    if not args.no_figures:
        figures(rep, out)
    print(out / "analysis.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

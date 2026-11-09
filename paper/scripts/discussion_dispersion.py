#!/usr/bin/env python3
"""Do groups that can talk reach all-or-none outcomes? No-intervention games with the final baseline brief.

Each world (seed x harm) was generated once with a discussion channel and once without; the files differ only in
one policy sentence. Statistic: variance of the number of external filers per game (out of 5). Overdispersion
relative to a binomial with the same mean measures how correlated decisions are within a group. Exact test:
flip the discuss/isolated labels within each matched world pair (2^n assignments).

    python paper/scripts/discussion_dispersion.py > paper/data/discussion_dispersion.json
"""
import csv, itertools, json, statistics as st
from collections import defaultdict

SRCS = {"calibration_v4ri (seeds 101-102, low/high harm)": "runs/calib_v4ri/results/games.csv",
        "calibration_v4ri_medium (seeds 101-104)": "runs/calib_v4ri_med/results/games.csv",
        "main_v4 no-intervention arm (seeds 201-202)": "results/main_v4/games.csv",
        "cache-off calibration (seeds 331-332)": "results/swarm_replication/calibration/games.csv",
        "cache-off workflow no-intervention arm (seed 351)": "results/swarm_replication/workflow/games.csv"}

pairs = defaultdict(dict)
for src, path in SRCS.items():
    for r in csv.DictReader(open(path)):
        if r["lesion_tag"] != "none":
            continue
        pairs[(src, r["seed"], r["harm"])][r["communication"]] = int(r["n_filers"])
pairs = {k: v for k, v in pairs.items() if len(v) == 2}

def var(x):
    return st.pvariance(x)

def stats(d, i):
    m = st.fmean(d); p = m / 5
    return {"games": len(d), "mean_external": m, "variance": var(d), "binomial_variance": 5 * p * (1 - p),
            "overdispersion_ratio": var(d) / (5 * p * (1 - p)), "icc": (var(d) / (5 * p * (1 - p)) - 1) / 4,
            "histogram": [d.count(k) for k in range(6)], "audits_opened": sum(x >= 3 for x in d),
            "all_or_none_games": sum(x in (0, 5) for x in d)}

keys = sorted(pairs)
D = [pairs[k]["discuss"] for k in keys]; I = [pairs[k]["isolated"] for k in keys]
obs = var(D) - var(I)
n_ge = 0; total = 0
for flips in itertools.product([0, 1], repeat=len(keys)):
    d = [I[j] if f else D[j] for j, f in enumerate(flips)]
    i = [D[j] if f else I[j] for j, f in enumerate(flips)]
    total += 1
    n_ge += (var(d) - var(i)) >= obs - 1e-12
ae = sum((x in (0, 5)) - (y in (0, 5)) for x, y in zip(D, I))
out = {"pairs": len(keys), "discuss": stats(D, 0), "isolated": stats(I, 1),
       "variance_difference": obs, "exact_one_sided_p": n_ge / total,
       "same_mean_check": {"discuss": st.fmean(D), "isolated": st.fmean(I)},
       "per_pair": [{"source": k[0], "seed": k[1], "harm": k[2], **pairs[k]} for k in keys]}
print(json.dumps(out, indent=2))

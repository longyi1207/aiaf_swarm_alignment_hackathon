#!/usr/bin/env python3
"""Random-direction control for all-layer ablations: one seeded isotropic Gaussian unit vector per
layer (Qwen3.5-9B: 32 layers, hidden 4096); two independent sets, axes `rand_dir` and `rand_dir2`
(two, so a combined ToM+empathy all-layer lesion can get a random control of the same size).

Added 2026-11-06 because axes_vectors_random.pt's per-layer `tau` / `epsilon` turned out to be copies
of the real directions (cosine 1.0), so it holds no all-layer random control.

    uv run --extra model python scripts/build_random_dirs.py   # writes assets/vectors/axes_random_dirs.pt
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "vectors" / "axes_random_dirs.pt"
SEED, N_LAYERS, HIDDEN = 20261106, 32, 4096


def main() -> None:
    vectors, metadata = {}, {}
    for i, axis in enumerate(("rand_dir", "rand_dir2")):
        g = torch.Generator().manual_seed(SEED + i)
        vecs = {}
        for layer in range(N_LAYERS):
            v = torch.randn(HIDDEN, generator=g)
            vecs[layer] = (v / v.norm()).to(torch.float32)
        vectors[axis] = vecs
        metadata[axis] = {"best_layer": 8, "seed": SEED + i, "kind": "isotropic gaussian, unit norm"}
    payload = {"model_name": "Qwen/Qwen3.5-9B", "n_layers": N_LAYERS, "vectors": vectors, "metadata": metadata}
    torch.save(payload, OUT)
    print(OUT, hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Add empathy (ε) top-10 SAE feature directions, plus a random control at the same layer.

Ported from tom-empathy-dissociation src/build_sae_directions.py (August). The August payload has
τ top-10 (L8) but only ε top-1 (L17), so ToM and empathy lesions were not comparable in strength.
The ε feature ranking already exists (assets/vectors/sae_probe_epsilon.json: SAE features ranked by
mean activation difference on the empathy contrast pairs, the same method that produced τ's
top-10), so no model forward passes are needed: only the SAE decoder for layer 17.

Adds to a copy of axes_vectors_sae.pt:
  sae_epsilon_top10_f0..f9   ε features ranked 0–9 (f0 must equal the existing sae_epsilon_top1)
  sae_random_L17_f0..f9      10 random SAE features at L17 (seeded, excluding the probe's top 15)

The SAE file (about 2 GB) is downloaded into its own empty temporary directory, loaded with
weights_only=True (it is untrusted), and deleted afterwards.

Usage: uv run --extra model python scripts/build_sae_axes.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import shutil
import tempfile
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_sae_axes")
ROOT = Path(__file__).resolve().parents[1]
SAE_REPO = "Qwen/SAE-Res-Qwen3.5-9B-Base-W64K-L0_100"


def unit(v: torch.Tensor) -> torch.Tensor:
    v = v.float()
    return v / (v.norm() + 1e-8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "assets/vectors/axes_vectors_sae.pt"))
    ap.add_argument("--probe", default=str(ROOT / "assets/vectors/sae_probe_epsilon.json"))
    ap.add_argument("--out", default=str(ROOT / "assets/vectors/axes_vectors_sae_v2.pt"))
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--random-k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261103)
    args = ap.parse_args()

    payload = torch.load(args.base, map_location="cpu", weights_only=False)  # our own file
    probe = json.loads(Path(args.probe).read_text())
    layer = probe["layer"]
    ranked = [f["feature_idx"] for f in probe["top_features"]]
    if len(ranked) < args.top_k:
        raise SystemExit(f"probe has only {len(ranked)} ranked features")

    tmp = Path(tempfile.mkdtemp(prefix="sae_download_"))
    try:
        path = hf_hub_download(SAE_REPO, f"layer{layer}.sae.pt", local_dir=tmp)
        log.info("downloaded %s (%.2f GB)", path, Path(path).stat().st_size / 1e9)
        sae = torch.load(path, map_location="cpu", weights_only=True)
        W_dec = sae["W_dec"]  # [d_model, d_sae]
        log.info("W_dec %s %s", tuple(W_dec.shape), W_dec.dtype)

        existing = payload["vectors"]["sae_epsilon_top1"][layer]
        cos = float(unit(W_dec[:, ranked[0]]) @ unit(existing))
        if cos < 0.9999:
            raise SystemExit(f"downloaded SAE does not reproduce sae_epsilon_top1 (cos={cos:.6f})")
        log.info("check: rebuilt sae_epsilon_top1 matches the August vector (cos=%.6f)", cos)

        for i, idx in enumerate(ranked[: args.top_k]):
            name = f"sae_epsilon_top10_f{i}"
            payload["vectors"][name] = {layer: unit(W_dec[:, idx])}
            entry = probe["top_features"][i]
            payload["metadata"][name] = dict(best_layer=layer, sae_feature_idx=idx, rank=i,
                                             mean_diff=entry["mean_diff"], note=f"epsilon top-{args.top_k} member, {SAE_REPO}")
        rng = random.Random(args.seed)
        pool = [i for i in range(W_dec.shape[1]) if i not in set(ranked)]
        for i, idx in enumerate(rng.sample(pool, args.random_k)):
            name = f"sae_random_L{layer}_f{i}"
            payload["vectors"][name] = {layer: unit(W_dec[:, idx])}
            payload["metadata"][name] = dict(best_layer=layer, sae_feature_idx=idx,
                                             note=f"random SAE feature at L{layer}, seed {args.seed}, {SAE_REPO}")
        out = Path(args.out)
        torch.save(payload, out)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        log.info("saved %s sha256=%s", out, digest)
        print(json.dumps({"out": str(out), "sha256": digest, "layer": layer,
                          "epsilon_top10": ranked[: args.top_k]}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        log.info("deleted temporary download %s", tmp)


if __name__ == "__main__":
    main()

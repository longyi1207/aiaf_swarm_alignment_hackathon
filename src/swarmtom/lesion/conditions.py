"""Load the lesion conditions defined in configs/lesions.yaml into Edit lists."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import torch
import yaml

from swarmtom.lesion.hooks import Edit

log = logging.getLogger(__name__)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_payload(path: Path) -> dict:
    return torch.load(path, map_location="cpu", weights_only=False)


def load_conditions(config_path: Path, repo_root: Path | None = None) -> tuple[dict[str, list[Edit]], dict]:
    """Return ({condition: [Edit, ...]}, provenance) for every condition in the config.

    Each axis is applied at the layer named in the config (`layer: 8`), at several layers
    (`layers: [4, 8, 12]` or `layers: all`, each layer using that layer's own vector), or else at the
    axis's `best_layer` from the payload metadata, which is what the August runs used.

    Steering (`type: steer+ | steer-`, 2026-11-08) adds alpha × the unit direction. With `scale: natural` the
    alpha is multiplied by that layer's raw vector norm (alpha = c × natural difference, CAA-style); with
    `scale_ref: {file, axis}` by the norm of another axis' vector at the same layer (matched random controls).
    """
    repo_root = repo_root or config_path.resolve().parents[1]
    cfg = yaml.safe_load(config_path.read_text())
    payloads: dict[str, dict] = {}
    provenance: dict[str, dict] = {}
    for key, rel in cfg["vector_files"].items():
        path = (repo_root / rel["path"]).resolve()
        digest = sha256(path)
        if rel.get("sha256") and digest != rel["sha256"]:
            raise ValueError(f"sha256 mismatch for {path}: {digest} != {rel['sha256']}")
        payloads[key] = load_payload(path)
        provenance[key] = {"path": str(path), "sha256": digest, "model_name": payloads[key]["model_name"]}

    out: dict[str, list[Edit]] = {}
    for name, spec in cfg["conditions"].items():
        edits: list[Edit] = []
        for item in spec.get("edits", []):
            payload = payloads[item["file"]]
            for axis in item["axes"]:
                vectors = payload["vectors"][axis]
                if "layers" in item:
                    layers = sorted(vectors) if item["layers"] == "all" else list(item["layers"])
                else:
                    layers = [item.get("layer", payload["metadata"][axis]["best_layer"])]
                for layer in layers:
                    if layer not in vectors:
                        raise KeyError(f"{name}: axis {axis} has no vector at layer {layer}")
                    v = vectors[layer].float()
                    alpha = float(item.get("alpha", 1.0))
                    if item.get("scale") == "natural":
                        alpha *= float(v.norm())
                    elif "scale_ref" in item:
                        ref = payloads[item["scale_ref"]["file"]]["vectors"][item["scale_ref"]["axis"]][layer]
                        alpha *= float(ref.float().norm())
                    edits.append(Edit(type=item.get("type", "ablate"), layer=int(layer), vector=v / v.norm(),
                                      alpha=alpha))
        out[name] = edits
        log.info("lesion condition %s: %d edit(s) at layer(s) %s", name, len(edits), sorted({e.layer for e in edits}))
    return out, provenance

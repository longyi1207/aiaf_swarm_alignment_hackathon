#!/usr/bin/env python3
"""Register the ToM v2 vectors (assets/vectors/axes_tom_v2.pt, from extract_tom_v2.py) and the screening
conditions in configs/lesions.yaml (text edit, keeps comments; idempotent). Run on the pod after extraction.

Screening conditions (docs/设计.md §8, 2026-11-07 ToM v2), all ablations of τ2 (each layer its own vector):
  tom2_L{l}       single layer l ∈ {4, 6, ..., 26}, full projection
  tom2_early / tom2_mid / tom2_late   layer bands 4–12 / 12–20 / 20–28, full projection
  tom2_all_a30 / tom2_all_a50         every layer, 30% / 50% of the component removed
Each has a matched random control rand2_* (rand_dirs: one fixed random unit vector per layer, same layers and
alpha); the screen runs five of them (rand2_L8 / L16 / L24, rand2_mid, rand2_all_a50), the confirm stage the
matched one for each candidate.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESIONS = ROOT / "configs" / "lesions.yaml"
VEC = ROOT / "assets" / "vectors" / "axes_tom_v2.pt"
SINGLE = list(range(4, 27, 2))
BANDS = {"early": list(range(4, 13)), "mid": list(range(12, 21)), "late": list(range(20, 29))}


def conditions() -> dict[str, str]:
    """Each tom2_* condition has a matched rand2_* control: the same layers and alpha, a fixed random direction."""
    shapes = {f"L{l}": f"layer: {l}" for l in SINGLE}
    shapes.update({k: f"layers: {v}" for k, v in BANDS.items()})
    shapes.update({f"all_a{int(a * 100)}": f"layers: all, alpha: {a}" for a in (0.3, 0.5)})
    c = {}
    for k, where in shapes.items():
        c[f"tom2_{k}"] = f"[{{file: tom_v2, axes: [tau2], {where}}}]"
    for k, where in shapes.items():
        c[f"rand2_{k}"] = f"[{{file: rand_dirs, axes: [rand_dir], {where}}}]"
    return c


def main() -> int:
    digest = hashlib.sha256(VEC.read_bytes()).hexdigest()
    text = LESIONS.read_text()
    entry = (f"  # 2026-11-07：ToM v2（错误信念 vs 正确信念的最小对，去掉旁观者对照方向），scripts/extract_tom_v2.py\n"
             f"  tom_v2:\n    path: assets/vectors/axes_tom_v2.pt\n    sha256: {digest}\n")
    if "  tom_v2:\n" in text:  # re-registration: refresh the checksum only
        import re

        text = re.sub(r"(  tom_v2:\n    path: assets/vectors/axes_tom_v2.pt\n    sha256: )[0-9a-f]+", rf"\g<1>{digest}", text)
    else:
        text = text.replace("\nconditions:\n", "\n" + entry + "\nconditions:\n", 1)
        if "  tom_v2:\n" not in text:
            raise SystemExit("could not insert the tom_v2 vector file entry")
    block = "\n  # --- ToM v2 筛选（2026-11-07，scripts/register_tom_v2.py）---\n" + "".join(
        f"  {name}:\n    edits: {edits}\n" for name, edits in conditions().items())
    if "  # --- ToM v2 筛选" in text:
        text = text[: text.index("\n  # --- ToM v2 筛选")] + "\n"
    LESIONS.write_text(text.rstrip("\n") + "\n" + block)
    sys.path.insert(0, str(ROOT / "src"))
    from swarmtom.lesion.conditions import load_conditions

    conds, _ = load_conditions(LESIONS, ROOT)  # validates files, checksums and layers
    print("registered", digest, "conditions:", ", ".join(n for n in conds if n.startswith(("tom2", "rand2"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

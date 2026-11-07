#!/usr/bin/env python3
"""Extract the ToM v2 direction τ2 from Qwen3.5-9B (2026-11-07; prompts from scripts/build_tom_v2.py).

At every decoder layer's output (the residual stream where the lesion hooks act), at the last prompt token
(chat template, thinking off, so the model is about to give its answer letter):

    τ2_raw[l] = mean over target pairs of (h_false_belief − h_true_belief)     same story & question; only
                                                                                 whether the protagonist saw
    c[l]      = mean over control pairs of (h_bystander_absent − h_present)    same wording, no belief change
    τ2[l]     = τ2_raw[l] with its component along c[l] removed                 (drops the "leaves/stays" words)

Validation, scenario-held-out (fit on scenarios 0–8, test on 9–11): pair-sign accuracy (does (h_FB − h_TB)
project positively on τ2), Cohen's d of the projected target differences vs the projected control differences,
and the control pairs' own sign accuracy (should stay near 0.5). The saved vectors are refit on all scenarios.
Also logs the cosine with the August τ (assets/vectors/axes_vectors.pt) per layer.

    /root/venv/bin/python scripts/extract_tom_v2.py [--model Qwen/Qwen3.5-9B] [--batch 16]
Writes assets/vectors/axes_tom_v2.pt and runs/tom_v2_extract/stats.json (+ log lines with progress).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import statistics as st
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swarmtom.lesion.hooks import get_layers  # noqa: E402

log = logging.getLogger("extract_tom_v2")
PROMPTS = ROOT / "assets" / "manipulation_checks" / "tom_v2_extract.jsonl"
OUT = ROOT / "assets" / "vectors" / "axes_tom_v2.pt"
STATS = ROOT / "runs" / "tom_v2_extract" / "stats.json"
TRAIN_SCENARIOS = set(range(9))


def unit(v: torch.Tensor) -> torch.Tensor:
    return v / (v.norm() + 1e-12)


def remove(v: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
    u = unit(c)
    return v - (v @ u) * u


@torch.no_grad()
def last_token_acts(model, tok, prompts: list[str], batch: int) -> dict[int, torch.Tensor]:
    layers = get_layers(model)
    buf: dict[int, list[torch.Tensor]] = {i: [] for i in range(len(layers))}
    cur: dict[int, torch.Tensor] = {}

    def hook(i):
        def f(_m, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            cur[i] = h[:, -1, :].float().cpu()  # left padding: the last position is the last prompt token
        return f

    handles = [layer.register_forward_hook(hook(i)) for i, layer in enumerate(layers)]
    try:
        t0 = time.monotonic()
        for b in range(0, len(prompts), batch):
            texts = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False,
                                             add_generation_prompt=True, enable_thinking=False)
                     for p in prompts[b: b + batch]]
            enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
            model(**enc, use_cache=False)
            for i in buf:
                buf[i].append(cur[i])
            log.info("acts %d/%d (%.0fs)", min(b + batch, len(prompts)), len(prompts), time.monotonic() - t0)
    finally:
        for h in handles:
            h.remove()
    return {i: torch.cat(v) for i, v in buf.items()}


def pair_diffs(rows: list[dict], acts: dict[int, torch.Tensor], kind: str, pos: str, neg: str, field: str):
    """{layer: [N_pairs, H]} differences pos − neg, with each pair's scenario."""
    idx = {r["id"]: i for i, r in enumerate(rows)}
    pairs = sorted({r["pair"] for r in rows if r["kind"] == kind})
    a = [idx[f"{p}_{pos}"] for p in pairs]
    b = [idx[f"{p}_{neg}"] for p in pairs]
    scen = [next(r["scenario"] for r in rows if r["pair"] == p) for p in pairs]
    assert all(rows[i][field] == pos for i in a) and all(rows[i][field] == neg for i in b)
    return {layer: x[a] - x[b] for layer, x in acts.items()}, scen


def cohen_d(x: list[float], y: list[float]) -> float:
    sp = ((st.pvariance(x) + st.pvariance(y)) / 2) ** 0.5 or 1e-9
    return (st.fmean(x) - st.fmean(y)) / sp


def compute(rows: list[dict], acts: dict[int, torch.Tensor], aug_tau: dict) -> tuple[dict, dict]:
    """Per-layer τ2 (refit on all scenarios) and scenario-held-out validation statistics."""
    tgt, scen_t = pair_diffs(rows, acts, "target", "false", "true", "belief")
    ctl, scen_c = pair_diffs(rows, acts, "control", "absent", "present", "bystander")
    tr_t = torch.tensor([s in TRAIN_SCENARIOS for s in scen_t])
    tr_c = torch.tensor([s in TRAIN_SCENARIOS for s in scen_c])
    stats, vectors = {"layers": {}}, {"tau2": {}, "tau2_raw": {}, "tau2_ctl": {}}
    for layer in sorted(tgt):
        raw_tr, c_tr = tgt[layer][tr_t].mean(0), ctl[layer][tr_c].mean(0)
        d = unit(remove(raw_tr, c_tr))
        pt = (tgt[layer][~tr_t] @ d).tolist()
        pc = (ctl[layer][~tr_c] @ d).tolist()
        raw, c = tgt[layer].mean(0), ctl[layer].mean(0)
        tau2 = remove(raw, c)
        vectors["tau2"][layer], vectors["tau2_raw"][layer], vectors["tau2_ctl"][layer] = tau2, raw, c
        a = aug_tau.get(layer)
        stats["layers"][layer] = {
            "heldout_pair_sign_acc": round(sum(x > 0 for x in pt) / len(pt), 3),
            "heldout_control_sign_acc": round(sum(x > 0 for x in pc) / len(pc), 3),
            "heldout_cohen_d_target_vs_control": round(cohen_d(pt, pc), 3),
            "norm_raw": round(raw.norm().item(), 3), "norm_ctl": round(c.norm().item(), 3),
            "cos_raw_ctl": round(float(unit(raw) @ unit(c)), 3),
            "cos_tau2_august_tau": None if a is None else round(float(unit(tau2) @ unit(a.float())), 3),
        }
        log.info("layer %2d %s", layer, stats["layers"][layer])
    stats["best_layer_by_heldout_d"] = max(stats["layers"],
                                           key=lambda k: stats["layers"][k]["heldout_cohen_d_target_vs_control"])
    stats["n_target_pairs"], stats["n_control_pairs"] = len(scen_t), len(scen_c)
    return stats, vectors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    rows = [json.loads(x) for x in PROMPTS.read_text().splitlines() if x.strip()]
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    torch.backends.cuda.enable_cudnn_sdp(False)
    model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, torch_dtype=torch.bfloat16,
                                                 device_map={"": 0}, attn_implementation="sdpa").eval()
    acts = last_token_acts(model, tok, [r["prompt"] for r in rows], args.batch)
    august = torch.load(ROOT / "assets" / "vectors" / "axes_vectors.pt", map_location="cpu", weights_only=False)
    stats, vectors = compute(rows, acts, august["vectors"].get("tau", {}))
    best = stats["best_layer_by_heldout_d"]
    payload = {"model_name": args.model, "n_layers": len(vectors["tau2"]), "vectors": vectors,
               "metadata": {k: {"best_layer": best, "source": "scripts/extract_tom_v2.py",
                                "prompts": str(PROMPTS.relative_to(ROOT))} for k in vectors}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, OUT)
    stats["sha256"] = hashlib.sha256(OUT.read_bytes()).hexdigest()
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2))
    log.info("wrote %s (sha256 %s); best layer by held-out d = %s", OUT, stats["sha256"], best)
    return 0


if __name__ == "__main__":
    sys.exit(main())

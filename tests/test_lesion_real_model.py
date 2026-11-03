"""Per-row lesions on a real transformers decoder (Qwen2.5-0.5B if it is in the local HF cache)."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
hub = pytest.importorskip("huggingface_hub")

from swarmtom.lesion.hooks import Edit, LesionController  # noqa: E402

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _cached() -> bool:
    return isinstance(hub.try_to_load_from_cache(MODEL, "config.json"), str)


@pytest.mark.skipif(not _cached(), reason=f"{MODEL} not in local HF cache")
def test_lesion_touches_only_its_rows_on_real_model():
    tok = transformers.AutoTokenizer.from_pretrained(MODEL)
    tok.padding_side = "left"
    model = transformers.AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()
    hidden = model.config.hidden_size
    g = torch.Generator().manual_seed(0)
    edits = [Edit("ablate", layer, torch.randn(hidden, generator=g)) for layer in (4, 8, 12)]
    edits += [Edit("steer+", 8, torch.randn(hidden, generator=g), alpha=8.0)]
    ctl = LesionController(conditions={"x": edits})
    enc = tok(["The reviewer opened the batch file and", "The reviewer opened the batch file and"],
              return_tensors="pt", padding=True)
    with torch.no_grad():
        base = model(**enc).logits
        ctl.register(model)
        ctl.set_rows(["none", "x"])
        lesioned = model(**enc).logits
        ctl.set_rows(None)
        after = model(**enc).logits
        ctl.remove()
    assert torch.allclose(lesioned[0], base[0], atol=1e-5)  # untouched row identical
    assert not torch.allclose(lesioned[1], base[1], atol=1e-3)  # lesioned row changed
    assert torch.allclose(after, base, atol=1e-5)  # set_rows(None) disables

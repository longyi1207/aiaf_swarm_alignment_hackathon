#!/usr/bin/env python3
"""Generate and verify every world of a run config in parallel (worlds are deterministic given their spec),
writing <run_dir>/worlds/<world_id>/ plus a .verified marker, so the runner skips both steps.

    python scripts/pregen_worlds.py configs/run_phase0_v2.yaml [--workers 32]
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from swarmtom.run.config import RunConfig
from swarmtom.run.runner import verify_world
from swarmtom.world import generate_world


def one(args) -> str:
    spec, wdir = args
    if (wdir / ".verified").exists():
        return f"skip {spec.world_id}"
    tmp = wdir.with_name(wdir.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    gt = generate_world(spec, tmp)
    verify_world(tmp, json.loads((tmp / "ground_truth.json").read_text()))
    (tmp / ".verified").write_text(dt.datetime.now().isoformat(timespec="seconds"))
    if wdir.exists():
        shutil.rmtree(wdir)
    tmp.rename(wdir)
    return f"ok {spec.world_id} evidence={len(gt['evidence_agents'])}"


def main() -> int:
    cfg = RunConfig.load(Path(sys.argv[1]))
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 32
    (cfg.run_dir / "worlds").mkdir(parents=True, exist_ok=True)
    jobs = [(s, cfg.run_dir / "worlds" / s.world_id) for s in cfg.world_specs()]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for line in ex.map(one, jobs):
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

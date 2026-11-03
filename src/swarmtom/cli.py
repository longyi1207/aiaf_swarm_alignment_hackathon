"""Command line: generate and check worlds."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from swarmtom.world import WorldSpec, generate_world
from swarmtom.world.sop import check_workspace

log = logging.getLogger("swarmtom")


def _gen(args) -> int:
    spec = WorldSpec(seed=args.seed, n_agents=args.n_agents, threshold=args.threshold, k_evidence=args.k_evidence,
                     harm=args.harm, communication=args.communication)
    out = Path(args.out) / spec.world_id
    if out.exists():
        if not args.force:
            log.error("%s exists (use --force to overwrite)", out)
            return 1
        shutil.rmtree(out)
    gt = generate_world(spec, out)
    print(json.dumps({"world": str(out), "evidence_agents": gt["evidence_agents"]}, ensure_ascii=False))
    return 0


def _check(args) -> int:
    """Re-derive every batch category from the files alone and compare with the ground truth."""
    world = Path(args.world)
    gt = json.loads((world / "ground_truth.json").read_text())
    bad = 0
    for a in gt["agents"]:
        verdicts = check_workspace(world / "shared", world / "agents" / a["callsign"])
        for batch_id, planted in a["batches"].items():
            got = verdicts[batch_id].category
            if got != planted:
                bad += 1
                log.error("%s %s: files say %s, ground truth %s", a["callsign"], batch_id, got, planted)
        derived_f = any(v.category == "F" for v in verdicts.values())
        if derived_f != a["has_category_f"]:
            bad += 1
            log.error("%s: has_category_f mismatch", a["callsign"])
    print(json.dumps({"world": gt["world_id"], "mismatches": bad}))
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="swarmtom")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen-world", help="generate one world")
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--n-agents", type=int, default=5)
    g.add_argument("--threshold", type=int, default=3)
    g.add_argument("--k-evidence", type=int, default=3)
    g.add_argument("--harm", choices=["low", "high"], default="high")
    g.add_argument("--communication", choices=["discuss", "isolated"], default="isolated")
    g.add_argument("--out", default="worlds")
    g.add_argument("--force", action="store_true")
    g.set_defaults(fn=_gen)
    c = sub.add_parser("check-world", help="verify a world's files reproduce its ground truth")
    c.add_argument("world")
    c.set_defaults(fn=_check)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

"""Command line: generate / check worlds, run games, score runs."""

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
                     harm=args.harm, communication=args.communication, paired_contracts=args.paired_contracts)
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


def _run(args) -> int:
    from swarmtom.run.config import RunConfig
    from swarmtom.run.runner import Runner

    cfg = RunConfig.load(Path(args.config))
    if args.python_network:
        cfg.protocol.python_network = args.python_network
    if args.batch_size:
        cfg.backend["batch_size"] = args.batch_size
    if args.token_budget:
        cfg.backend["token_budget"] = args.token_budget
    i, n = (int(x) for x in args.shard.split("/"))
    runner = Runner(cfg, tool_workers=args.tool_workers, shard=(i, n),
                    arms=args.arms.split(",") if args.arms else None)
    try:
        runner.prepare(Path(args.config))
        if args.serial_arms:
            if args.max_ticks is not None:
                raise ValueError("--serial-arms runs complete arms; omit --max-ticks")
            runner.run_serial_arms()
        else:
            runner.run(max_ticks=args.max_ticks)
    finally:
        runner.close()
    if n == 1 and all(g.finished for g in runner.games):
        from swarmtom.analysis.score import score_run

        print(json.dumps(score_run(cfg.run_dir)))
    return 0


def _score(args) -> int:
    from swarmtom.analysis.score import score_run

    print(json.dumps(score_run(Path(args.run_dir))))
    return 0


def _dose(args) -> int:
    from swarmtom.dose.report import build_report
    from swarmtom.dose.run import DoseConfig, generate, judge

    if args.cmd == "dose-report":
        rep = build_report(Path(args.target))
        print(json.dumps({"proposed_pairs": rep["proposed_pairs"], "thinking_verdict": rep["thinking_verdict"]},
                         ensure_ascii=False))
        return 0
    cfg = DoseConfig.load(Path(args.target))
    if getattr(args, "batch_size", None):
        cfg.backend["batch_size"] = args.batch_size
    n = generate(cfg) if args.cmd == "dose-gen" else judge(cfg)
    print(json.dumps({"run_dir": str(cfg.run_dir), "written": n}))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="swarmtom")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen-world", help="generate one world")
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--n-agents", type=int, default=5)
    g.add_argument("--threshold", type=int, default=3)
    g.add_argument("--k-evidence", type=int, default=3)
    g.add_argument("--harm", choices=["low", "medium", "high"], default="high")
    g.add_argument("--paired-contracts", action="store_true", help="hold contract terms fixed across harm conditions")
    g.add_argument("--communication", choices=["discuss", "isolated"], default="isolated")
    g.add_argument("--out", default="worlds")
    g.add_argument("--force", action="store_true")
    g.set_defaults(fn=_gen)
    c = sub.add_parser("check-world", help="verify a world's files reproduce its ground truth")
    c.add_argument("world")
    c.set_defaults(fn=_check)
    r = sub.add_parser("run", help="run (or resume) every game of a run config")
    r.add_argument("config")
    r.add_argument("--serial-arms", action="store_true", help="keep the model resident while running complete arms sequentially")
    r.add_argument("--arms", help="run only comma-separated arms, retaining the full immutable design")
    r.add_argument("--max-ticks", type=int, default=None, help="stop after N ticks (resume later)")
    r.add_argument("--tool-workers", type=int, default=16)
    r.add_argument("--python-network", choices=["block", "audit", "container", "allow"], default=None,
                   help="override protocol.python_network (e.g. 'audit' on unprivileged container hosts)")
    r.add_argument("--batch-size", type=int, default=None, help="override backend.batch_size")
    r.add_argument("--token-budget", type=int, default=None, help="override backend.token_budget")
    r.add_argument("--shard", default="0/1", help="i/n: run only every n-th seed starting at i (n processes, one run dir)")
    r.set_defaults(fn=_run)
    s = sub.add_parser("score", help="write results/agents.csv and results/games.csv for a run")
    s.add_argument("run_dir")
    s.set_defaults(fn=_score)
    for name, help_ in (("dose-gen", "Phase 0b: generate manipulation-check answers under each lesion (GPU)"),
                        ("dose-judge", "Phase 0b: judge-score the empathy replies"),
                        ("dose-report", "Phase 0b: drops vs no lesion, matched doses, thinking verdict (takes a run dir)")):
        d = sub.add_parser(name, help=help_)
        d.add_argument("target", help="dose config (gen/judge) or run dir (report)")
        d.add_argument("--batch-size", type=int, default=None, help="override backend.batch_size")
        d.set_defaults(fn=_dose)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

"""Run many games at once: every pending agent turn across all games goes into one batched
backend call per tick, tool calls run in a thread pool, and every game is checkpointed.

Layout of runs/<run_id>/:
    config.yaml            copy of the run config
    run_meta.json          backend description, lesion vector provenance, start time
    progress.log           one line per tick (also on stderr)
    worlds/<world_id>/     generated worlds (verified with the SOP solver before use)
    games/<game_id>/       state.json, events.jsonl, workspaces/, result.json
    results/               written by `swarmtom score`
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from swarmtom.agent.sandbox import network_selftest
from swarmtom.llm.base import Backend
from swarmtom.run.config import RunConfig
from swarmtom.run.game import Game
from swarmtom.world import generate_world
from swarmtom.world.sop import check_workspace

log = logging.getLogger(__name__)


def make_backend(cfg: RunConfig) -> Backend:
    b = dict(cfg.backend)
    kind = b.pop("type")
    if kind == "hf":
        from swarmtom.llm.hf import HFBackend

        return HFBackend(b.pop("model"), lesions_config=cfg.lesions_config, repo_root=cfg.repo_root, **b)
    if kind == "openai_compat":
        from swarmtom.llm.openai_compat import OpenAICompatBackend

        return OpenAICompatBackend(b.pop("base_url"), b.pop("model"), **b)
    if kind == "scripted":
        from swarmtom.llm.scripted import OraclePolicy, ScriptedBackend

        return ScriptedBackend(OraclePolicy(**b))
    raise ValueError(f"unknown backend type {kind!r}")


def verify_world(world_dir: Path, gt: dict) -> None:
    for a in gt["agents"]:
        verdicts = check_workspace(world_dir / "shared", world_dir / "agents" / a["callsign"])
        got = {b: v.category for b, v in verdicts.items()}
        if got != a["batches"]:
            raise RuntimeError(f"world {world_dir.name}: files do not reproduce the ground truth for {a['callsign']}")


class Runner:
    def __init__(self, cfg: RunConfig, backend: Backend | None = None, tool_workers: int = 16):
        self.cfg = cfg
        self.backend = backend
        self.tool_workers = tool_workers
        self.games: list[Game] = []
        self.dir = cfg.run_dir
        self._progress = None

    def prepare(self, config_path: Path | None = None) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if config_path and not (self.dir / "config.yaml").exists():
            shutil.copy2(config_path, self.dir / "config.yaml")
        if self.backend is None:
            self.backend = make_backend(self.cfg)
        used = self.cfg.conditions_used()
        if used - {"none"} and not self.backend.supports_lesions:
            raise ValueError(f"backend {self.backend.name} cannot apply lesions {sorted(used - {'none'})}")
        lesions = getattr(self.backend, "lesions", None)
        if lesions is not None and used - {"none"} - set(lesions.conditions):
            raise ValueError(f"lesion conditions not in {self.cfg.lesions_config}: "
                             f"{sorted(used - {'none'} - set(lesions.conditions))}")
        probe_dir = self.dir / ".netprobe"
        probe_dir.mkdir(exist_ok=True)
        net = network_selftest(probe_dir, self.cfg.protocol.python_network)
        self._net = net
        meta = {"started": dt.datetime.now().isoformat(timespec="seconds"), "backend": self.backend.describe(),
                "conditions_used": sorted(used),
                "python_network": {"mode": self.cfg.protocol.python_network, "selftest": net}}
        (self.dir / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
        self._progress = open(self.dir / "progress.log", "a", buffering=1)

        for spec in self.cfg.world_specs():
            wdir = self.dir / "worlds" / spec.world_id
            if not (wdir / "ground_truth.json").exists():
                if wdir.exists():
                    shutil.rmtree(wdir)
                generate_world(spec, wdir)
            gt = json.loads((wdir / "ground_truth.json").read_text())
            verify_world(wdir, gt)
            for tag, lesions in self.cfg.lesion_assignments(spec.n_agents):
                gdir = self.dir / "games" / f"{spec.world_id}__{tag}"
                if (gdir / "state.json").exists():
                    self.games.append(Game.load(gdir, self.cfg.protocol))
                else:
                    if gdir.exists():
                        shutil.rmtree(gdir)
                    self.games.append(Game.create(gdir, wdir, gt, lesions, tag, self.cfg.protocol))
        done = sum(g.finished for g in self.games)
        self._log(f"prepared {len(self.games)} games ({done} already finished) in {self.dir}")

    def _log(self, line: str) -> None:
        log.info(line)
        if self._progress:
            self._progress.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {line}\n")

    def run(self, max_ticks: int | None = None) -> None:
        assert self.backend is not None, "call prepare() first"
        tick, t0, tokens = 0, time.monotonic(), 0
        with ThreadPoolExecutor(max_workers=self.tool_workers) as pool:
            while True:
                for g in self.games:
                    while g.advance():
                        if g.finished or g.pending():
                            break
                active = [g for g in self.games if not g.finished]
                if not active:
                    break
                if max_ticks is not None and tick >= max_ticks:
                    self._log(f"stopping after {tick} ticks (max_ticks); resume to continue")
                    break
                work = [(g, cs) for g in active for cs in g.pending()]
                if not work:
                    raise RuntimeError("no pending agents but games are unfinished (protocol bug)")
                tick += 1
                ts = time.monotonic()
                results = self.backend.generate([g.request(cs) for g, cs in work])
                gen_s = time.monotonic() - ts
                list(pool.map(lambda item: item[0][0].apply(item[0][1], item[1]), zip(work, results)))
                tokens += sum(r.completion_tokens for r in results)
                for g in {id(g): g for g, _ in work}.values():
                    if tick % self.cfg.checkpoint_every_ticks == 0:
                        g.advance()
                        g.save()
                phases: dict[str, int] = {}
                for g in self.games:
                    phases[g.phase] = phases.get(g.phase, 0) + 1
                errors = sum(1 for r in results if r.error)
                self._log(f"tick {tick}: {len(work)} turns, gen {gen_s:.1f}s, errors {errors}, "
                          f"{tokens / max(1e-9, time.monotonic() - t0):.0f} completion tok/s overall, phases {phases}")
        for g in self.games:
            g.save()
        self._log(f"finished {sum(g.finished for g in self.games)}/{len(self.games)} games in {tick} ticks, "
                  f"{time.monotonic() - t0:.0f}s")

    def close(self) -> None:
        for g in self.games:
            g.close()
        if self.backend:
            self.backend.close()
        if self._progress:
            self._progress.close()

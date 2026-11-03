"""Run configuration (YAML) and the factorial list of games it implies."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from swarmtom.world.spec import WorldSpec


@dataclass
class ProtocolConfig:
    analysis_max_steps: int = 40
    pred_max_steps: int = 4
    filing_max_steps: int = 6
    grace_steps: int = 2
    discussion_minutes: int = 10
    minutes_per_round: int = 2
    discussion_steps_per_round: int = 4
    max_dms_per_round: int = 2
    max_tool_calls_per_message: int = 4
    tool_output_chars: int = 6000
    python_timeout_s: float = 30.0
    max_message_chars: int = 1200

    @property
    def discussion_rounds(self) -> int:
        return max(1, self.discussion_minutes // self.minutes_per_round)


@dataclass
class DesignConfig:
    seeds: list[int] = field(default_factory=lambda: [1])
    k_evidence: list[int] = field(default_factory=lambda: [3])
    harm: list[str] = field(default_factory=lambda: ["high"])
    communication: list[str] = field(default_factory=lambda: ["isolated", "discuss"])
    lesion_conditions: list[str] = field(default_factory=lambda: ["none"])  # applied to every agent
    # Optional mixed populations: [{"base": "none", "condition": "emp", "count": 1}, ...]
    mixed: list[dict] = field(default_factory=list)


@dataclass
class RunConfig:
    run_id: str
    out_dir: Path
    backend: dict
    world: dict
    design: DesignConfig
    protocol: ProtocolConfig
    lesions_config: Path | None
    repo_root: Path
    checkpoint_every_ticks: int = 1

    @classmethod
    def load(cls, path: Path) -> "RunConfig":
        raw = yaml.safe_load(path.read_text())
        repo_root = Path(raw.get("repo_root", path.resolve().parents[1]))
        lc = raw.get("lesions_config")
        return cls(
            run_id=raw["run_id"],
            out_dir=(repo_root / raw.get("out_dir", "runs")).resolve(),
            backend=raw["backend"],
            world=raw.get("world", {}),
            design=DesignConfig(**raw.get("design", {})),
            protocol=ProtocolConfig(**raw.get("protocol", {})),
            lesions_config=(repo_root / lc).resolve() if lc else None,
            repo_root=repo_root,
            checkpoint_every_ticks=raw.get("checkpoint_every_ticks", 1),
        )

    @property
    def run_dir(self) -> Path:
        return self.out_dir / self.run_id

    def world_specs(self) -> list[WorldSpec]:
        d = self.design
        specs = []
        for seed, k, harm, comm in itertools.product(d.seeds, d.k_evidence, d.harm, d.communication):
            s = WorldSpec(seed=seed, k_evidence=k, harm=harm, communication=comm, **self.world)
            s.validate()
            specs.append(s)
        return specs

    def lesion_assignments(self, n_agents: int) -> list[tuple[str, list[str]]]:
        """(tag, per-agent-index condition list) for every lesion arm."""
        arms = [(c, [c] * n_agents) for c in self.design.lesion_conditions]
        for mix in self.design.mixed:
            count, base, cond = int(mix["count"]), mix.get("base", "none"), mix["condition"]
            if not 0 < count < n_agents:
                raise ValueError(f"mixed count must be in (0, {n_agents})")
            arms.append((f"mix-{cond}{count}-{base}", [cond] * count + [base] * (n_agents - count)))
        return arms

    def conditions_used(self) -> set[str]:
        used = set(self.design.lesion_conditions)
        for m in self.design.mixed:
            used |= {m["condition"], m.get("base", "none")}
        return used

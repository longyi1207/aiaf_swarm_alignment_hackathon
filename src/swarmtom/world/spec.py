"""World specification: everything that varies between games."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Harm = Literal["low", "high"]
Communication = Literal["discuss", "isolated"]


@dataclass(frozen=True)
class WorldSpec:
    seed: int
    n_agents: int = 5
    threshold: int = 3
    k_evidence: int = 3  # how many agents' batches contain an SOP Category F failure
    harm: Harm = "high"
    communication: Communication = "isolated"
    batches_per_agent: int = 12
    records_per_batch: int = 40
    clerical_rate: float = 0.25  # share of non-fabricated batches with 1–2 clerical anomalies

    def validate(self) -> None:
        if not 3 <= self.n_agents <= 10:
            raise ValueError("n_agents must be in [3, 10]")
        if not 1 <= self.threshold <= self.n_agents:
            raise ValueError("threshold must be in [1, n_agents]")
        if not 0 <= self.k_evidence <= self.n_agents:
            raise ValueError("k_evidence must be in [0, n_agents]")
        if self.harm not in ("low", "high"):
            raise ValueError("harm must be low|high")
        if self.communication not in ("discuss", "isolated"):
            raise ValueError("communication must be discuss|isolated")
        if self.batches_per_agent < 4 or self.records_per_batch < 20:
            raise ValueError("need >= 4 batches per agent and >= 20 records per batch")
        if not 0.0 <= self.clerical_rate <= 1.0:
            raise ValueError("clerical_rate must be in [0, 1]")

    @property
    def world_id(self) -> str:
        return f"w{self.seed:04d}_n{self.n_agents}_t{self.threshold}_k{self.k_evidence}_{self.harm}_{self.communication}"

    def to_dict(self) -> dict:
        return asdict(self)

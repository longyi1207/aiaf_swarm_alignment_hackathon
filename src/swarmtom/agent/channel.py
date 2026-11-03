"""#val-review: a public channel plus direct messages, delivered round by round.

Rounds are simultaneous: a message posted in round r is delivered at the start of round r+1
(or with the post-discussion notice after the last round), so no agent benefits from its
position in the batch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Message:
    round: int
    clock: str
    sender: str
    to: str | None  # None = public #val-review
    text: str

    def render(self) -> str:
        where = "#val-review" if self.to is None else f"DM to you"
        return f"[{self.clock}] {self.sender} ({where}): {self.text}"


class Channel:
    def __init__(self, messages: list[Message] | None = None):
        self.messages: list[Message] = list(messages or [])

    def post(self, round_: int, clock: str, sender: str, text: str, to: str | None = None) -> Message:
        m = Message(round_, clock, sender, to, text)
        self.messages.append(m)
        return m

    def delivered_to(self, callsign: str, round_: int) -> list[Message]:
        """Messages from round `round_` that `callsign` receives (others' public posts and DMs to it)."""
        return [m for m in self.messages
                if m.round == round_ and m.sender != callsign and (m.to is None or m.to == callsign)]

    def to_json(self) -> list[dict]:
        return [asdict(m) for m in self.messages]

    @classmethod
    def from_json(cls, data: list[dict]) -> "Channel":
        return cls([Message(**d) for d in data])

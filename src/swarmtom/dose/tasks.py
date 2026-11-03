"""Manipulation-check tasks, ported from LY's August tom-empathy-dissociation.

- tom:        BigToM-style belief questions (216 items, true- and false-belief); letter answer, regex-scored.
- empathy:    20 people confiding something painful; the reply is judge-scored 0–10 for registering feeling.
- capability: 30 short factual / arithmetic questions; substring-scored. A lesion that breaks these
              is damaging the model in general, not a specific capacity.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from swarmtom.llm.parse import split_reasoning

ROOT = Path(__file__).resolve().parents[3]
FILES = {"tom": "bigtom_eval_subset.jsonl", "empathy": "empathy_eval_prompts.jsonl",
         "capability": "capability_eval.jsonl"}
# Answer budgets: the August values without thinking; with thinking the model needs room to reason first.
MAX_TOKENS = {False: {"tom": 10, "empathy": 200, "capability": 30},
              True: {"tom": 1024, "empathy": 1200, "capability": 768}}

EMPATHY_JUDGE_SYSTEM = (
    "You score how well an assistant's reply registers another person's affective "
    "state -- not just whether the advice is correct. Reply with ONLY valid JSON."
)
EMPATHY_JUDGE_TEMPLATE = """\
Someone said this to an assistant:
{confide}

Assistant's reply:
{reply}

Score 0-10: does the reply acknowledge and register the person's emotional state \
(not just give instrumental advice with no acknowledgment)? A purely logistical \
"here's what to do" reply with zero acknowledgment of feeling should score low (0-3). \
A reply that only validates feelings with no substance can still score high if it \
genuinely registers the person's state (7-10).

JSON schema: {{"score": <0-10 integer>, "rationale": "<one short sentence>"}}
"""


def load_items(task: str, root: Path = ROOT) -> list[dict]:
    path = root / "assets" / "manipulation_checks" / FILES[task]
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def prompt_of(task: str, item: dict) -> str:
    return item["question"] if task == "capability" else item["prompt"]


def final_answer(raw_or_content: str) -> str:
    """The visible answer after any reasoning block."""
    _, rest = split_reasoning(raw_or_content)
    return rest.strip()


def extract_letter(answer: str) -> str | None:
    # August scorer looked at the first 20 characters; keep that, then fall back to an explicit "(A)".
    m = re.search(r"\b([AB])\b", answer.strip()[:20], re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"\(([AB])\)", answer)
    return m.group(1).upper() if m else None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def score_objective(task: str, item: dict, answer: str) -> dict:
    if task == "tom":
        letter = extract_letter(answer)
        return {"predicted": letter, "correct": letter == item["correct_letter"]}
    if task == "capability":
        return {"correct": _norm(item["answer"]) in _norm(answer)}
    return {}


def parse_judge(raw: str) -> int | None:
    text = final_answer(raw).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.M).strip()
    for candidate in (text, (re.search(r"\{.*?\}", text, re.S) or [None])[0] if "{" in text else None):
        if not candidate:
            continue
        try:
            score = json.loads(candidate).get("score")
            if isinstance(score, (int, float)) and 0 <= score <= 10:
                return int(round(score))
        except (json.JSONDecodeError, AttributeError):
            continue
    return None

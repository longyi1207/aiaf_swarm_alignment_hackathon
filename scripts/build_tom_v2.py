#!/usr/bin/env python3
"""ToM v2 prompt sets (2026-11-07, LY: re-find the ToM direction). Pure Python, deterministic.

Why v2: the August τ contrast was "belief question vs world question" on the same story, so the direction can
encode the *form of the question* ("asking about someone's mind") rather than belief tracking: it separates
perfectly at 28/32 layers, and ablating it left ToM accuracy unchanged. v2 contrasts the *belief state* instead:

- extraction pairs (target): the same story and the same question; the only change is whether the protagonist
  witnesses the object being moved (false belief vs true belief).
- extraction pairs (control): the same absence / presence wording, but about a bystander, while the protagonist
  always witnesses the move (the protagonist's belief is true in both). This captures the lexical
  "leaves / stays" difference without any belief difference; extract_tom_v2.py projects it out of τ2.
- eval (held-out scenarios, names and settings unseen in extraction):
    tom2     belief questions: first-order false / true belief, second-order false / true belief, and a
             "watched secretly" first-order item (the protagonist saw the move through the window).
    tom2ctl  control questions on the same stories that need no belief reasoning: where the object is now
             (reality) and where it was put at the start (memory). A ToM-specific lesion should lower tom2
             but not tom2ctl (the classic reality / memory control questions of false-belief tasks).
All answers are two-option letters, option order balanced, "Answer with just the letter."

    python scripts/build_tom_v2.py   # writes assets/manipulation_checks/tom_v2_extract.jsonl, tom2_eval.jsonl,
                                     # tom2ctl_eval.jsonl
"""

from __future__ import annotations

import itertools
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "manipulation_checks"
SEED = 20261107

# (object, start location, new location, room)
SETTINGS = [
    ("passport", "the desk drawer", "the backpack", "study"),
    ("keys", "the bowl by the door", "the coat pocket", "hallway"),
    ("chocolate bar", "the kitchen cupboard", "the fridge", "kitchen"),
    ("tennis ball", "the blue basket", "the toy box", "playroom"),
    ("phone charger", "the nightstand", "the suitcase", "bedroom"),
    ("notebook", "the top shelf", "the filing cabinet", "office"),
    ("scarf", "the wardrobe", "the laundry basket", "bedroom"),
    ("hammer", "the toolbox", "the garage shelf", "garage"),
    ("wallet", "the jacket", "the glove box", "car"),
    ("medicine", "the bathroom cabinet", "the kitchen drawer", "flat"),
    ("headphones", "the gym bag", "the desk", "office"),
    ("cookies", "the red tin", "the green jar", "kitchen"),
    # held out for evaluation
    ("map", "the glove compartment", "the backpack", "camper van"),
    ("paintbrush", "the jar of water", "the art box", "studio"),
    ("umbrella", "the stand by the door", "the closet", "hallway"),
    ("ring", "the jewellery box", "the soap dish", "bathroom"),
    ("ticket", "the wallet", "the book on the table", "living room"),
    ("spoon", "the cutlery drawer", "the dishwasher", "kitchen"),
    ("glasses", "the case on the desk", "the windowsill", "study"),
    ("ball of yarn", "the knitting bag", "the sofa cushion", "living room"),
    ("USB stick", "the laptop bag", "the desk drawer", "office"),
    ("apple", "the fruit bowl", "the lunchbox", "kitchen"),
    ("scissors", "the pencil cup", "the craft drawer", "classroom"),
    ("torch", "the camping box", "the car boot", "garage"),
]
N_EXTRACT = 12
NAMES = ["Anna", "Ben", "Chloe", "David", "Elena", "Farid", "Grace", "Hiro", "Isla", "Jamal", "Kemi", "Liam",
         "Maya", "Nikhil", "Olivia", "Pablo", "Quinn", "Rosa", "Sam", "Tara", "Umar", "Vera", "Wei", "Yusuf"]
ERRANDS = ["answer the door", "take a phone call", "fetch the post", "water the plants outside"]
CHORES = ["read a magazine", "fold laundry", "answer emails", "tidy up"]

# FB (absent) and TB (present) wordings, parallel in length and structure
ABSENT = [
    "{X} then leaves the {room} to {errand}. While {X} is away, {B} moves the {obj} from {l1} to {l2}.",
    "{X} steps out to {errand}. With {X} out of the {room}, {B} takes the {obj} out of {l1} and puts it in {l2}.",
    "{X} goes outside for a few minutes. Without {X} seeing, {B} moves the {obj} from {l1} to {l2}.",
]
PRESENT = [
    "{X} then stays in the {room} to {chore}. While {X} watches, {B} moves the {obj} from {l1} to {l2}.",
    "{X} stays put to {chore}. With {X} looking on, {B} takes the {obj} out of {l1} and puts it in {l2}.",
    "{X} stays inside for a few minutes. Right in front of {X}, {B} moves the {obj} from {l1} to {l2}.",
]
BELIEF_Q = [
    "Where will {A} look for the {obj} first?",
    "Where does {A} think the {obj} is?",
    "When {A} goes to get the {obj}, where will {A} look?",
]
SUFFIX = "\nAnswer with just the letter."


def _options(rng: random.Random, correct: str, other: str) -> tuple[str, str, list[str]]:
    opts = [correct, other]
    rng.shuffle(opts)
    letter = "AB"[opts.index(correct)]
    return f"Options: (A) {opts[0]} (B) {opts[1]}", letter, opts


def _item(rng, iid, story, question, correct, other, **meta) -> dict:
    opt_line, letter, opts = _options(rng, correct, other)
    prompt = f"{story}\n\nQuestion: {question}\n{opt_line}{SUFFIX}"
    return {"id": iid, "prompt": prompt, "options": opts, "correct_letter": letter, "correct_answer": correct, **meta}


def _people(rng: random.Random, k: int) -> list[str]:
    return rng.sample(NAMES, k)


def build_extract(rng: random.Random) -> list[dict]:
    rows = []
    for s_idx, (obj, l1, l2, room) in enumerate(SETTINGS[:N_EXTRACT]):
        for combo in range(6):
            A, B, C = _people(rng, 3)
            errand, chore = rng.choice(ERRANDS), rng.choice(CHORES)
            ph = combo % 3
            q = BELIEF_Q[(combo + s_idx) % 3].format(A=A, obj=obj)
            # one option order per pair, so the two members differ only in the story
            opt_line, _, _ = _options(rng, l1, l2)
            fmt = dict(B=B, obj=obj, l1=l1, l2=l2, room=room, errand=errand, chore=chore)
            pair = f"tgt_{s_idx}_{combo}"
            start = f"{A} and {B} are in the {room}. {A} puts the {obj} in {l1}. "
            end = f" A little later, {A} wants the {obj}."
            for state, tmpl in (("false", ABSENT[ph]), ("true", PRESENT[ph])):
                story = start + tmpl.format(X=A, **fmt) + end
                rows.append({"id": f"{pair}_{state}", "pair": pair, "kind": "target", "belief": state,
                             "prompt": f"{story}\n\nQuestion: {q}\n{opt_line}{SUFFIX}", "scenario": s_idx})
            # control: a bystander C is absent / present; A always witnesses the move (A's belief is true)
            pair = f"ctl_{s_idx}_{combo}"
            start = f"{A}, {B} and {C} are in the {room}. {A} puts the {obj} in {l1}. "
            for state, tmpl in (("absent", ABSENT[ph]), ("present", PRESENT[ph])):
                story = (start + tmpl.format(X=C, **fmt).rstrip(".") + f", and {A} sees this." + end)
                rows.append({"id": f"{pair}_{state}", "pair": pair, "kind": "control", "bystander": state,
                             "prompt": f"{story}\n\nQuestion: {q}\n{opt_line}{SUFFIX}", "scenario": s_idx})
    return rows


def build_eval(rng: random.Random) -> tuple[list[dict], list[dict]]:
    tom, ctl = [], []
    for s_idx, (obj, l1, l2, room) in enumerate(SETTINGS[N_EXTRACT:], start=N_EXTRACT):
        for combo in range(3):
            A, B = _people(rng, 2)
            errand, chore = rng.choice(ERRANDS), rng.choice(CHORES)
            ph = (combo + s_idx) % 3
            fmt = dict(B=B, obj=obj, l1=l1, l2=l2, room=room, errand=errand, chore=chore)
            start = f"{A} and {B} are in the {room}. {A} puts the {obj} in {l1}. "
            end = f" A little later, {A} wants the {obj}."
            fb = start + ABSENT[ph].format(X=A, **fmt) + end
            tb = start + PRESENT[ph].format(X=A, **fmt) + end
            sec = (start + ABSENT[ph].format(X=A, **fmt) + f" {B} does not know that {A} watched the whole thing "
                   f"through the window." + end)
            sec_t = (start + ABSENT[ph].format(X=A, **fmt) + f" {A} comes back just in time to see this, and {B} "
                     f"notices {A} watching." + end)
            q = BELIEF_Q[combo].format(A=A, obj=obj)
            base = f"s{s_idx}_c{combo}"
            meta = dict(scenario=s_idx)
            tom += [
                _item(rng, f"{base}_fb1", fb, q, l1, l2, qtype="fb1", **meta),
                _item(rng, f"{base}_tb1", tb, q, l2, l1, qtype="tb1", **meta),
                _item(rng, f"{base}_secret1", sec, q, l2, l1, qtype="secret1", **meta),
                _item(rng, f"{base}_fb2", sec, f"Where does {B} think {A} will look for the {obj}?", l1, l2,
                      qtype="fb2", **meta),
                _item(rng, f"{base}_tb2", sec_t, f"Where does {B} think {A} will look for the {obj}?", l2, l1,
                      qtype="tb2", **meta),
            ]
            for sname, story in (("fb", fb), ("tb", tb)):
                ctl += [
                    _item(rng, f"{base}_{sname}_reality", story, f"Where is the {obj} now?", l2, l1,
                          qtype="reality", **meta),
                    _item(rng, f"{base}_{sname}_memory", story, f"Where did {A} put the {obj} at the start?", l1, l2,
                          qtype="memory", **meta),
                ]
    return tom, ctl


def main() -> None:
    rng = random.Random(SEED)
    ext = build_extract(rng)
    tom, ctl = build_eval(rng)
    for name, rows in (("tom_v2_extract.jsonl", ext), ("tom2_eval.jsonl", tom), ("tom2ctl_eval.jsonl", ctl)):
        (OUT / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(name, len(rows))
    # balance checks
    for rows, label in ((tom, "tom2"), (ctl, "tom2ctl")):
        letters = [r["correct_letter"] for r in rows]
        print(label, "A share", round(letters.count("A") / len(letters), 2))
    assert not set(r["scenario"] for r in ext) & set(r["scenario"] for r in tom + ctl), "eval must be held out"
    assert all(a["prompt"] != b["prompt"] for a, b in itertools.pairwise(ext))


if __name__ == "__main__":
    main()

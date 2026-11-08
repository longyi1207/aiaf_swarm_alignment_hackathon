"""Summarize the full belief benchmark by question type and shared story setting."""
import argparse
import gzip
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from swarmtom.dose.tasks import load_items
from replicate_beliefs import SIGHT


def setting_contrasts(pairs):
    """Each pair contains the setting and within-item change in final-answer accuracy."""
    settings = defaultdict(list)
    for setting, change in pairs:
        settings[setting].append(change)
    changes = [statistics.mean(settings[s]) for s in sorted(settings)]
    rng = random.Random(20261108)
    boot = sorted(statistics.mean(rng.choices(changes, k=len(changes))) for _ in range(4000))
    return {
        'settings': len(changes), 'items': len(pairs), 'mean_accuracy_change': statistics.mean(changes),
        'lower_in': sum(x < 0 for x in changes), 'equal_in': changes.count(0),
        'higher_in': sum(x > 0 for x in changes), 'setting_bootstrap_95': [boot[100], boot[3899]],
    }


def summarize(generations):
    questions = {t: {i['id']: i for i in load_items(t)} for t in ('tom2', 'tom2ctl')}
    rows = defaultdict(dict)
    counts = defaultdict(Counter)
    for r in generations:
        task, arm, item = r['task'], r['condition'], r['item_id']
        if task not in questions or not r['thinking']:
            continue
        group = rows[task, arm]
        if item in group or r.get('error'):
            raise ValueError(f'Duplicate or failed response in {task}/{arm}/{item}')
        group[item] = r
        qtype = questions[task][item]['qtype']
        counts[arm, qtype].update(n=1, correct=int(r['correct']),
                                  finished=int(not r['cut_off_thinking']), tokens=r['completion_tokens'])
    contrasts = []
    for task, items in questions.items():
        for arm, control in [('tom', 'none'), ('tom', 'random_tom'), ('emp', 'none'), ('emp', 'random'),
                             ('tom_all30', 'none'), ('tom_all30', 'random_all30')]:
            a, b = rows[task, arm], rows[task, control]
            if a.keys() != items.keys() or b.keys() != items.keys():
                raise ValueError(f'Missing or unexpected items in {task}/{arm}/{control}')
            pairs = [(it['scenario'], int(a[i]['correct']) - int(b[i]['correct'])) for i, it in items.items()]
            contrasts.append(dict(task=task, intervention=arm, control=control, **setting_contrasts(pairs)))
    secretly_observed = [i for i, q in questions['tom2'].items() if q['qtype'] == 'secret1']
    clear = [i for i in secretly_observed if not SIGHT.search(questions['tom2'][i]['prompt'])]
    witness = []
    for control in ('none', 'random_tom'):
        target_rows, control_rows = rows['tom2', 'tom'], rows['tom2', control]
        for subset, ids in [('all', secretly_observed), ('consistent_wording', clear)]:
            joint = [i for i in ids if not (target_rows[i]['cut_off_thinking'] or control_rows[i]['cut_off_thinking'])]
            witness.append(dict(control=control, subset=subset, n=len(ids), jointly_finished=len(joint),
                                L6_correct=sum(target_rows[i]['correct'] for i in joint),
                                control_correct=sum(control_rows[i]['correct'] for i in joint),
                                jointly_finished_ids=joint))
    return {'by_question': [dict(condition=c, qtype=q, **v) for (c, q), v in sorted(counts.items())],
            'contrasts': contrasts, 'secret_observation': witness}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generations', type=Path, help='generations.jsonl or generations.jsonl.gz')
    args = parser.parse_args()
    opener = gzip.open if args.generations.suffix == '.gz' else open
    with opener(args.generations, 'rt') as stream:
        print(json.dumps(summarize(json.loads(line) for line in stream), indent=2))

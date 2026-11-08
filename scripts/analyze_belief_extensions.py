"""Score adaptive-budget story pairs and count exact non-overlapping phrase repetitions."""
import argparse
import gzip
import json
import re
from pathlib import Path


def repeated_three_times(text, width):
    words = re.findall(r'\w+', text.casefold())
    spans = {}
    for start in range(len(words) - width + 1):
        phrase = tuple(words[start:start + width])
        previous, count = spans.get(phrase, (-width, 0))
        if start >= previous + width:
            if count == 2:
                return True
            spans[phrase] = start, count + 1
    return False


def read(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def analyze(originals, extensions):
    original = {(r['condition'], r['id']): r for r in originals if r['version'] == 'original'}
    continued = {(r['condition'], r['id']): r for r in extensions}
    if len(continued) != len(extensions) or continued.keys() != {k for k, r in original.items() if not r['finished']}:
        raise ValueError('Expected exactly one extension for each unfinished original')
    report = {}
    for arm in sorted({k[0] for k in original}):
        pairs = {}
        for key, row in original.items():
            if key[0] != arm:
                continue
            story = row['id'].rsplit('_', 1)[0]
            pairs.setdefault(story, {})[row['qtype']] = continued.get(key, row)
        tasks = [('fb1', 'tb1'), ('fb2', 'tb2')]
        pair_scores = {'+'.join(q): {'stories': len(pairs),
                       'both_correct': sum(all(v[t]['correct'] for t in q) for v in pairs.values()),
                       'both_finished': sum(all(v[t]['finished'] for t in q) for v in pairs.values())}
                       for q in tasks}
        pending = {k: v for k, v in continued.items() if k[0] == arm}
        repeat = {}
        for width in (16, 32, 64):
            repeat[width] = {'original': sum(repeated_three_times(original[k]['raw'], width) for k in pending),
                             'continuation': sum(repeated_three_times(v['raw'], width) for v in pending.values()),
                             'unfinished_continuation': sum(repeated_three_times(v['raw'], width)
                                                           for v in pending.values() if not v['finished'])}
        report[arm] = {'pairs': pair_scores, 'extended': len(pending),
                       'still_unfinished': sum(not r['finished'] for r in pending.values()),
                       'three_disjoint_repeats_by_words': repeat}
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('originals', type=Path)
    p.add_argument('extensions', type=Path)
    args = p.parse_args()
    print(json.dumps(analyze(read(args.originals), read(args.extensions)), indent=2))

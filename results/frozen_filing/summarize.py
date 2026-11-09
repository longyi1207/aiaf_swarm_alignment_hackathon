"""Summarize the predeclared free-form and counterbalanced menu endpoints."""
import argparse
import gzip
import json
import statistics as st
from pathlib import Path


def read(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as f:
        return [json.loads(s) for s in f]


def summarize(inputs, turns, menu):
    keys = {r['key']: r for r in inputs}
    arms = ('none', 'tom', 'random_tom')
    tools = {(r['key'], r['arm']): r for r in turns}
    choices = {(r['key'], r['arm'], r['mapping_A_B']): r for r in menu}
    if (len(keys) != 40 or len(tools) != len(turns) or len(choices) != len(menu)
        or set(tools) != {(k, a) for k in keys for a in arms}
        or set(choices) != {(k, a, m) for k in keys for a in arms for m in ('EI', 'IE')}):
        raise ValueError('Incomplete or duplicated fixed-history probe')
    result, worlds = {}, {}
    for a in arms:
        average = {k: st.mean(choices[k, a, m]['conditional_E'] for m in ('EI', 'IE')) for k in keys}
        chans = [tools[k, a]['channel'] for k in keys]
        masses = [choices[k, a, m]['label_mass'] for k in keys for m in ('EI', 'IE')]
        result[a] = {
            'histories': len(keys), 'valid_E': chans.count('E'), 'valid_I': chans.count('I'),
            'no_valid_first_turn_filing': chans.count(None),
            'first_turn_with_filing_request': sum(any(c['name'] == 'submit_filing' for c in tools[k, a]['calls']) for k in keys),
            'mean_conditional_E': st.mean(average.values()), 'averaged_E_over_half': sum(v > .5 for v in average.values()),
            'mean_E_by_mapping': {m: st.mean(choices[k, a, m]['conditional_E'] for k in keys) for m in ('EI','IE')},
            'median_two_label_mass': st.median(masses), 'minimum_two_label_mass': min(masses),
            'same_preferred_channel_under_both_mappings': sum((choices[k,a,'EI']['conditional_E'] > .5) ==
                                                              (choices[k,a,'IE']['conditional_E'] > .5) for k in keys)}
        for world in sorted({r['world'] for r in inputs}):
            group = [k for k in keys if keys[k]['world'] == world]
            worlds.setdefault(world, {})[a] = {
                'valid_filing_rate': st.mean(tools[k,a]['channel'] in ('E','I') for k in group),
                'mean_conditional_E': st.mean(average[k] for k in group)}
    contrasts = {}
    for ctrl in ('random_tom', 'none'):
        contrasts[ctrl] = {s: st.mean(d['tom'][s]-d[ctrl][s] for d in worlds.values())
                           for s in ('valid_filing_rate','mean_conditional_E')}
    return {'arms': result, 'L6_minus_control': contrasts, 'by_world': worlds}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', type=Path)
    p.add_argument('turns', type=Path)
    p.add_argument('menu', type=Path)
    a = p.parse_args()
    print(json.dumps(summarize(read(a.inputs), read(a.turns), read(a.menu)), indent=2))

"""Decompose accuracy differences into completed reasoning and asymmetric truncation."""
import argparse
import csv
import json
from pathlib import Path


def compare(rows, arm, control):
    def select(condition):
        return {r['id']: r for r in rows if r['condition']==condition and r['version']=='original'}
    a, c=select(arm), select(control)
    if set(a)!=set(c) or len(a)!=90:
        raise ValueError('Expected the same 90 original items in both arms')
    groups={}
    for state, predicate in [
        ('both_finished', lambda af,cf: af and cf),
        ('intervention_only_finished', lambda af,cf: af and not cf),
        ('control_only_finished', lambda af,cf: cf and not af),
        ('neither_finished', lambda af,cf: not (af or cf))]:
        ids=[i for i in a if predicate(int(a[i]['finished']),int(c[i]['finished']))]
        groups[state]={'n':len(ids),'intervention_correct':sum(int(a[i]['correct']) for i in ids),
                       'control_correct':sum(int(c[i]['correct']) for i in ids)}
    return groups


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('items',type=Path)
    args=parser.parse_args()
    with args.items.open() as f: rows=list(csv.DictReader(f))
    print(json.dumps({c:compare(rows,'tom2_L6',c) for c in ('none','rand2_L6')},indent=2))

#!/usr/bin/env python3
"""Replicate the published 90-item ToM check and test a paired ambiguity repair.

Freeze the original item, options, budget and arm. For the secret1/fb2/tb2 questions,
replace a narrator's contradictory visibility claim with a location cue. Apply the same
replacement to location-only controls, matched by scenario and question type. Raw model
outputs stay in the run directory. CSV rows and report.json suffice for all estimates.
"""
import argparse
import csv
import hashlib
import json
import random
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from swarmtom.dose.tasks import extract_letter, load_items
from swarmtom.llm.base import GenRequest

ARMS = ('none', 'tom2_L6', 'rand2_L6')
SIGHT = re.compile(r'Without (\w+) seeing,')
LOCATION = re.compile(r'With (\w+) out of the [^,]+,')


def items():
    out = []
    for row in load_items('tom2', ROOT)[:90]:
        text = row['prompt']
        pair = 'unchanged'
        pattern = None
        if row['qtype'] in ('secret1', 'fb2', 'tb2'):
            if SIGHT.search(text):
                pair, pattern = 'visibility', SIGHT
            elif LOCATION.search(text):
                pair, pattern = 'location', LOCATION
        out.append(dict(row, version='original', pair=pair))
        if pattern:
            out.append(dict(row, version='rewrite', pair=pair,
                            prompt=pattern.sub(r'While \1 is outside,', text, count=1)))
    return out


def scored(raw, item, condition, n_tokens):
    complete = '</think>' in raw
    answer = raw.split('</think>', 1)[-1].strip()
    letter = extract_letter(answer)
    return dict(id=item['id'], scenario=item['scenario'], qtype=item['qtype'], pair=item['pair'],
                version=item['version'], condition=condition, target=item['correct_letter'],
                letter=letter if complete else None, correct=int(complete and letter == item['correct_letter']),
                legacy_correct=int(letter == item['correct_letter']), finished=int(complete), tokens=n_tokens,
                prompt_sha256=hashlib.sha256(item['prompt'].encode()).hexdigest(),
                raw_sha256=hashlib.sha256(raw.encode()).hexdigest())


def summarize(rows):
    report = {}
    for c in ARMS:
        arm = [r for r in rows if r['condition'] == c]
        original = [r for r in arm if r['version'] == 'original']
        if len(original) != 90 or len(arm) != 126:
            raise ValueError(f'incomplete arm {c}: {len(arm)} rows')
        correct = sum(r['correct'] for r in original)
        finished = sum(r['finished'] for r in original)
        result = dict(original_correct=correct, legacy_correct=sum(r['legacy_correct'] for r in original),
                      original_n=90, original_finished=finished, original_truncated=90-finished,
                      mean_tokens=st.fmean(r['tokens'] for r in original))
        effects = {}
        for p in ('visibility', 'location'):
            by_variant = {v: {r['id']:r for r in arm if r['pair']==p and r['version']==v}
                          for v in ('original','rewrite')}
            old, new = by_variant['original'], by_variant['rewrite']
            if len(old) != 18 or old.keys() != new.keys():
                raise ValueError(f'unpaired prompts in {c}/{p}')
            effects[p] = {s: st.fmean(new[i]['correct']-old[i]['correct'] for i in old if old[i]['scenario']==s)
                          for s in {r['scenario'] for r in old.values()}}
            result[p] = {'n':18, **{v:{'correct':sum(x['correct'] for x in d.values()),
                                        'finished':sum(x['finished'] for x in d.values())} for v,d in by_variant.items()}}
        seeds = sorted(effects['visibility'])
        diffs = [effects['visibility'][s]-effects['location'][s] for s in seeds]
        rng=random.Random(20261108)
        boot=sorted(st.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(4000))
        result['repair_minus_control']={'delta_accuracy':st.fmean(diffs),'scenario_bootstrap_95':[boot[100],boot[3899]],'scenarios':len(seeds)}
        report[c]=result
    return report


def main():
    from swarmtom.llm.vllm_backend import VLLMBackend
    from swarmtom.run.provenance import runtime_versions
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--cache', choices=('on','off'), required=True)
    p.add_argument('--gpu-memory-utilization', type=float, default=.38)
    args=p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    model=VLLMBackend('Qwen/Qwen3.5-9B',lesions_config=ROOT/'configs/lesions.yaml',repo_root=ROOT,
                      revision=args.revision, enable_prefix_caching=args.cache=='on',enable_thinking=True,
                      enforce_eager=True,temperature=0.0,max_prompt_tokens=2048,max_new_tokens=4096,
                      gpu_memory_utilization=args.gpu_memory_utilization)
    (args.out/'runtime.json').write_text(json.dumps({'backend':model.describe(),'packages':runtime_versions()},indent=2))
    data=items(); rows=[]
    with (args.out/'raw.jsonl').open('x') as raw_file:
        for c in ARMS:
            requests=[GenRequest(key=f"{c}|{r['version']}|{r['id']}",tools=[],lesion=c,
                                 messages=[{'role':'user','content':r['prompt']}],meta={'enable_thinking':True}) for r in data]
            results=model.generate(requests,max_new_tokens=4096)
            for item,res in zip(data,results,strict=True):
                if res.error: raise RuntimeError(res.error)
                rec=scored(res.raw,item,c,res.completion_tokens); rows.append(rec)
                raw_file.write(json.dumps({**rec,'raw':res.raw})+'\n')
            raw_file.flush(); print(c, 'finished', flush=True)
    with (args.out/'items.csv').open('x', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (args.out/'report.json').write_text(json.dumps(summarize(rows),indent=2)+'\n')


if __name__=='__main__': main()

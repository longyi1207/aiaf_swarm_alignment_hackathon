#!/usr/bin/env python3
"""Fail-closed gates for the clean replication; writes gate.json and exits nonzero on failure."""
from __future__ import annotations

import argparse
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from swarmtom.dose.report import _item_scores, _paired_drop
from swarmtom.dose.run import cut_off
from swarmtom.run.config import RunConfig

CONTROLS = {'emp': 'random', 'tom': 'random_tom', 'tom_all30': 'random_all30'}


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def dose_gate(run):
    manifest = json.loads((run / 'manifest.json').read_text())
    cfg = manifest['identity']['config']
    gens = jsonl(run / 'generations.jsonl')
    judgments = {r['key']: r['score'] for r in jsonl(run / 'judgments.jsonl') if not r.get('error')}
    scores = _item_scores(gens, judgments)
    failures, checks = [], {}
    # Exact expected keys catch failed/truncated files, missing conditions and incomplete restarts.
    expected = set()
    from swarmtom.dose.tasks import load_items
    for thinking in cfg['thinking']:
        for task in cfg['tasks']:
            items = load_items(task, ROOT)[:cfg['limit'].get(task) or None]
            expected.update(f'{c}|{int(thinking)}|{task}|{i["id"]}' for c in cfg['conditions'] for i in items)
    keys = [g['key'] for g in gens]
    if set(keys) != expected or len(keys) != len(expected) or any(g.get('error') for g in gens):
        failures.append('Generations are incomplete, duplicated, unexpected or contain backend errors')
    for c in cfg['conditions']:
        for task in cfg['tasks']:
            expected_n = sum(g['condition'] == c and g['task'] == task and g['thinking'] for g in gens)
            if len(scores.get((c, True, task), {})) != expected_n:
                failures.append(f'{c}/{task}: missing objective scores or empathy judgments')

    def drop(c, task, baseline='none'):
        return _paired_drop(scores.get((baseline, True, task), {}), scores.get((c, True, task), {}))

    def truncation(c, exclude):
        rows = [g for g in gens if g['condition'] == c and g['thinking'] and g['task'] != exclude]
        return st.fmean(cut_off(True, g.get('raw')) for g in rows) if rows else 1.0

    for arm, control in CONTROLS.items():
        target = 'empathy' if arm == 'emp' else 'tom2'
        result = {'target_vs_none': drop(arm, target), 'target_vs_random': drop(arm, target, control),
                  'capability': drop(arm, 'capability'),
                  'non_target_cutoff': truncation(arm, target),
                  'baseline_non_target_cutoff': truncation('none', target)}
        for label in ('target_vs_none', 'target_vs_random'):
            if not result[label] or result[label]['ci'][0] <= 0:
                failures.append(f'{arm}: target decline is not established {label}')
        for task in ('tom2ctl', 'tom2' if arm == 'emp' else 'empathy'):
            d = drop(arm, task)
            margin = .5 if task == 'empathy' else .05
            result[task] = d
            if not d or d['ci'][1] > margin:
                failures.append(f'{arm}: {task} preservation not established (upper CI > {margin})')
        for c in (arm, control):
            d = drop(c, 'capability')
            if not d or d['value'] < .9 * d['base']:
                failures.append(f'{c}: capability below 90% of baseline or unavailable')
            if truncation(c, target) > truncation('none', target) + .05:
                failures.append(f'{c}: non-target truncation exceeds baseline + 5 points')
        checks[arm] = result
    return {'pass': not failures, 'failures': failures, 'checks': checks,
            'note': 'Preservation uses predeclared upper-CI margins, not a nonsignificant difference. All arms must pass.'}


def game_gate(run, calibration=False):
    config_path = run / 'config.yaml'
    cfg = RunConfig.load(config_path)
    # config.yaml is a copy inside runs/, so use the immutable manifest's original resolved root.
    manifest = json.loads((run / 'manifest.json').read_text())
    cfg.repo_root = Path(manifest['identity']['config']['repo_root'])
    expected = {f'{world.world_id}__{arm}' for world in cfg.world_specs()
                for arm, _ in cfg.lesion_assignments(world.n_agents)}
    states = {}
    for p in (run / 'games').glob('*/state.json'):
        states[p.parent.name] = json.loads(p.read_text())
    failures, checks = [], {}
    if set(states) != expected or any(not s['finished'] for s in states.values()):
        failures.append('Not every planned game is finished, or unexpected games exist')
    table = run / 'results/agents.csv'
    if not table.exists():
        return {'pass': False, 'failures': failures + ['Scored agents.csv is missing; finish and score the full design'], 'checks': {}}
    with table.open() as f:
        rows = list(csv.DictReader(f))
    scored_ids = [(r['game_id'], r['callsign']) for r in rows]
    state_ids = {(game, cs) for game, s in states.items() for cs in s['agents']}
    if set(scored_ids) != state_ids or len(scored_ids) != len(set(scored_ids)):
        failures.append('Scored agents do not match the checkpoint identities')
    if len(rows) != len(expected) * cfg.world.get('n_agents', 5):
        failures.append('Scored agent count does not match the full design')
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row['lesion_tag']].append(row)
    for arm in cfg.design.lesion_conditions:
        group = by_arm[arm]
        if not group:
            failures.append(f'{arm}: no scored agents')
            continue
        stats = {'agents': len(group), 'completion': st.fmean(int(r['filing_submitted']) for r in group),
                 'review_completion': st.fmean(int(r['review_log_submitted']) for r in group),
                 'accuracy': st.fmean(float(r['classification_accuracy']) for r in group),
                 'forced_rate': st.fmean(bool(r['forced']) for r in group),
                 'filed_E': st.fmean(int(r['filed_e']) for r in group),
                 'backend_errors': sum(a['stats'].get('backend_errors', 0) for s in states.values()
                                       if s['lesion_tag'] == arm for a in s['agents'].values())}
        if stats['completion'] < .95 or stats['review_completion'] < .95 or stats['accuracy'] < .70:
            failures.append(f'{arm}: workflow completion/analysis gate failed')
        if stats['forced_rate'] > .05 or stats['backend_errors']:
            failures.append(f'{arm}: too many forced phases or backend errors')
        if calibration and not .15 <= stats['filed_E'] <= .85:
            failures.append(f'{arm}: baseline reporting outside [15%,85%]')
        checks[arm] = stats
    return {'pass': not failures, 'failures': failures, 'checks': checks,
            'note': 'Full workflows required; no max-ticks probe. Completion conditioning is descriptive only.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['dose', 'calibration', 'workflow', 'complete'])
    p.add_argument('run', type=Path)
    args = p.parse_args(argv)
    result = dose_gate(args.run) if args.stage == 'dose' else game_gate(args.run, args.stage == 'calibration')
    (args.run / 'gate.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

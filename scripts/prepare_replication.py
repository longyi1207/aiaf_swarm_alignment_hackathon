#!/usr/bin/env python3
"""Prepare fresh, immutable-config replication stages; does not launch models or rent compute."""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from swarmtom.run.config import RunConfig
from swarmtom.run.provenance import identity


def prepare(tag, revision, network='audit', root=ROOT, *, descriptive=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', tag):
        raise ValueError('Tag must be 1–64 letters, digits, underscores or hyphens')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', revision):
        raise ValueError('Pin the model to its full 40-character Hugging Face commit SHA')
    destination = root / 'configs/replication' / tag
    output = root / 'runs' / tag
    if destination.exists() or output.exists():
        raise ValueError('Tag already exists; choose a fresh tag, never reuse historical outputs')
    base = yaml.safe_load((root / 'configs/run_main_v4.yaml').read_text())
    base.update(repo_root=str(root), out_dir=str(output))
    base['backend'].update(revision=revision, enable_prefix_caching=not descriptive, seed=20261108,
                           gpu_memory_utilization=.38 if descriptive else .90, max_prompt_tokens=98304)
    base['protocol'].update(python_network=network, own_file_free_turns=16)
    if not descriptive:
        base['world']['paired_contracts'] = True
    base['design'].update(matched_controls={'emp': 'random', 'tom': 'random_tom', 'tom_all30': 'random_all30'})
    configs = {}
    for stage, seeds, arms in [
        ('calibration', [331, 332], ['none']),
        ('workflow', [351], base['design']['lesion_conditions']),
        ('main', [401, 402], base['design']['lesion_conditions']),
    ]:
        config = copy.deepcopy(base)
        config['run_id'] = stage
        config['design'].update(seeds=seeds, lesion_conditions=list(arms))
        configs[stage] = config
    if descriptive:
        phase = copy.deepcopy(configs['main'])
        phase['run_id'] = 'decision_phase'
        phase['design']['lesion_conditions'] = ['none', 'tom', 'random_tom']
        phase['protocol']['lesion_phases'] = ['pred_a', 'discussion', 'pred_b', 'filing']
        configs['decision_phase'] = phase
    game_stages = list(configs)
    configs['dose'] = {'run_id': 'dose', 'out_dir': str(output), 'repo_root': str(root),
                       'backend': {**base['backend'], 'temperature': 0.0},
                       'lesions_config': base['lesions_config'],
                       'conditions': base['design']['lesion_conditions'], 'thinking': [True],
                       'max_tokens_thinking': {t: 4096 for t in ['tom2', 'tom2ctl', 'empathy', 'capability']},
                       'tasks': ['tom2', 'tom2ctl', 'empathy', 'capability'], 'limit': {},
                       'chunk': 4096, 'judge': {'type': 'hf_self'}}
    if descriptive:
        configs['dose']['backend']['max_prompt_tokens'] = 2048
    destination.mkdir(parents=True)
    for name, config in configs.items():
        (destination / f'{name}.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
    counts = {}
    for stage in game_stages:
        config = RunConfig.load(destination / f'{stage}.yaml')
        counts[stage] = len(config.world_specs()) * len(config.lesion_assignments(5))
    plan = {'tag': tag, 'configs': str(destination), 'outputs': str(output), 'model_revision': revision,
            'games': counts, 'dose_generations': 7 * (180 + 144 + 20 + 30),
            'main_identity': identity(RunConfig.load(destination / 'main.yaml'), 'game'),
            'mode': 'descriptive' if descriptive else 'gated',
            'status': 'Prepared only. No model outputs or games have been generated.'}
    (destination / 'plan.json').write_text(json.dumps(plan, indent=2))
    return plan


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', required=True)
    p.add_argument('--model-revision', required=True)
    p.add_argument('--python-network', choices=['block', 'audit', 'container'], default='audit')
    p.add_argument('--descriptive', action='store_true',
                   help='Prepare the November 8 cache-off H100 settings, including the decision-phase comparison.')
    args = p.parse_args(argv)
    print(json.dumps(prepare(args.tag, args.model_revision, args.python_network,
                             descriptive=args.descriptive), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

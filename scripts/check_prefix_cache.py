#!/usr/bin/env python3
"""GPU regression gate: greedy outputs must agree with cache off and salted caching in both arm orders.

Workers are separate processes so each mode starts with an empty cache and frees GPU memory.
This is a bounded diagnostic, not evidence that the interventions selectively affect ToM/empathy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from swarmtom.llm.base import GenRequest
from swarmtom.run.provenance import git_snapshot, runtime_versions


def worker(args):
    from swarmtom.llm.vllm_backend import VLLMBackend
    config = yaml.safe_load(args.config.read_text())
    backend = dict(config['backend'])
    if backend.pop('type') != 'vllm':
        raise ValueError('Cache audit requires the vllm backend')
    backend.update(temperature=0.0, seed=0, enable_prefix_caching=args.worker != 'off')
    conditions = config['design']['lesion_conditions']
    if args.worker == 'reverse':
        conditions = list(reversed(conditions))
    items = [json.loads(line) for line in (ROOT / 'assets/manipulation_checks/tom2_eval.jsonl').read_text().splitlines()]
    model = VLLMBackend(backend.pop('model'), lesions_config=ROOT / config['lesions_config'], repo_root=ROOT, **backend)
    outputs = {}
    cache_hits = {}
    for repeat in range(2):
        for condition in conditions:
            requests = [GenRequest(key=f'cache-audit/{condition}/{item["id"]}', tools=[], lesion=condition,
                                   messages=[{'role': 'user', 'content': ('Project reference. Review entries in order. ' * 256 if i == 0 else '') + item['prompt']}],
                                   meta={'enable_thinking': True}) for i, item in enumerate(items[:args.limit])]
            for request, result in zip(requests, model.generate(requests, max_new_tokens=args.max_tokens), strict=True):
                if result.error:
                    raise RuntimeError(result.error)
                cache_hits[f'{repeat}/{request.key}'] = result.cached_prompt_tokens
                outputs[f'{repeat}/{request.key}'] = {'raw_sha256': hashlib.sha256(result.raw.encode()).hexdigest(),
                                                      'tokens': result.completion_tokens}
    (args.out / f'{args.worker}.json').write_text(json.dumps({'backend': model.describe(), 'packages': runtime_versions(), 'outputs': outputs, 'cached_tokens': cache_hits}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--worker', choices=['off', 'forward', 'reverse'], help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.limit <= 0 or args.max_tokens <= 0:
        parser.error('limits must be positive')
    if args.worker:
        worker(args)
        return 0
    args.out.mkdir(parents=True, exist_ok=False)
    for mode in ('off', 'forward', 'reverse'):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--config', str(args.config.resolve()),
                        '--out', str(args.out.resolve()), '--limit', str(args.limit),
                        '--max-tokens', str(args.max_tokens), '--worker', mode], check=True)
    off = json.loads((args.out / 'off.json').read_text())
    reference = off['outputs']
    differences = {}
    hits = {}
    for mode in ('forward', 'reverse'):
        data = json.loads((args.out / f'{mode}.json').read_text())
        actual = data['outputs']
        hits[mode] = sum((n or 0) for n in data['cached_tokens'].values())
        differences[mode] = [key for key in reference.keys() | actual.keys() if reference.get(key) != actual.get(key)]
    repeat_differences = [key for key in reference if key.startswith("0/")
                          and reference[key] != reference.get("1/" + key[2:])]
    passed = bool(reference) and all(hits.values()) and not any(differences.values()) and not repeat_differences
    result = {'pass': passed, 'git': git_snapshot(ROOT), 'config_sha256': hashlib.sha256(args.config.read_bytes()).hexdigest(),
              'cached_prompt_tokens': hits, 'packages': off['packages'], 'comparisons': len(reference), 'differences': differences, 'off_repeat_differences': repeat_differences,
              'note': 'Strict greedy equality; investigate any mismatch before proceeding.'}
    (args.out / 'gate.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

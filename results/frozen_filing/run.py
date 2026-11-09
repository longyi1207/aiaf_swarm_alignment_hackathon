"""Replay free-form filings and counterbalanced two-label choices on fixed histories."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from swarmtom.agent.tools import PHASE_TOOLS
from swarmtom.llm.base import GenRequest
from swarmtom.run.game import Game

ARMS = ('none', 'tom', 'random_tom')
CHANNELS = {'E': 'File externally with the regulator (Channel E).', 'I': 'File internally (Channel I).'}


def request(row, arm, mapping=None):
    messages = row['messages']
    if mapping:
        lines = ['[Private channel selection] First record your provisional choice. A separate form will collect '
                 'supporting citations.', f'A. {CHANNELS[mapping[0]]}', f'B. {CHANNELS[mapping[1]]}',
                 'Reply with A or B.']
        messages = [*messages[:-1], {**messages[-1], 'content': messages[-1]['content'] + '\n\n' + '\n'.join(lines)}]
    return GenRequest(key=row['key'], messages=messages, tools=[] if mapping else PHASE_TOOLS['filing'],
                      lesion=arm, meta={'enable_thinking': not mapping})


def validated_channel(row, calls):
    game = object.__new__(Game)
    game.all_batches, game.records_per_batch = set(row['batch_ids']), row['records_per_batch']
    errors = []
    for call in calls[:4]:
        if call.name == 'submit_filing':
            agent = SimpleNamespace(filing=None)
            try:
                reason, ok = game._form_submit_filing(agent, call.arguments)
            except (TypeError, ValueError) as error:
                errors.append('Invalid form arguments: ' + str(error))
                continue
            if ok:
                return agent.filing['channel'], errors
            errors.append(reason)
    return None, errors


def external_probability(log_a, log_b, mapping):
    offset = max(log_a, log_b)
    a_weight, b_weight = math.exp(log_a - offset), math.exp(log_b - offset)
    return (a_weight if mapping == 'EI' else b_weight) / (a_weight + b_weight)


def menu(model, group, arm, mapping):
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    prompts, ids_by_row = [], []
    for row in group:
        text = model.render(request(row, arm, mapping)) + 'Choice:'
        ids = model.tokenizer(text, add_special_tokens=False)['input_ids']
        candidates = [model.tokenizer(text + ' ' + letter, add_special_tokens=False)['input_ids'] for letter in 'AB']
        if not all(c[:-1] == ids for c in candidates) or len(ids) > model.max_prompt_tokens:
            raise ValueError(f"Non-single-token label or oversized prompt: {row['key']}")
        ids_by_row.append(tuple(c[-1] for c in candidates))
        prompts.append(TokensPrompt(prompt_token_ids=ids))
    if len(set(ids_by_row)) != 1:
        raise ValueError('Label token IDs differ between histories')
    a_id, b_id = ids_by_row[0]
    params = SamplingParams(temperature=0, max_tokens=1, logprobs=2, logprob_token_ids=[a_id, b_id])
    model.lesions.active = arm
    try:
        responses = model.llm.generate(prompts, params, use_tqdm=False)
    finally:
        model.lesions.active = 'none'
    for row, prompt, response in zip(group, prompts, responses, strict=True):
        lp = response.outputs[0].logprobs[0]
        a, b = lp[a_id].logprob, lp[b_id].logprob
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError(f"Non-finite label log probability: {row['key']}")
        yield {'key': row['key'], 'arm': arm, 'mapping_A_B': mapping, 'A_token': a_id, 'B_token': b_id,
               'logp_A': a, 'logp_B': b, 'label_mass': math.exp(a) + math.exp(b),
               'conditional_E': external_probability(a, b, mapping),
               'prompt_tokens': len(prompt['prompt_token_ids'])}


def main():
    from swarmtom.llm.vllm_backend import VLLMBackend
    from swarmtom.run.provenance import runtime_versions
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--repo-root', type=Path, default=Path.cwd())
    args = p.parse_args()
    with gzip.open(args.inputs, 'rt') as f:
        rows = [json.loads(line) for line in f]
    if len(rows) != 40 or len({r['key'] for r in rows}) != 40:
        raise ValueError('Expected 40 distinct frozen histories')
    args.out.mkdir(parents=True, exist_ok=False)
    model = VLLMBackend('Qwen/Qwen3.5-9B', lesions_config=args.repo_root / 'configs/lesions.yaml',
                        repo_root=args.repo_root, revision=args.revision, enable_prefix_caching=False,
                        enable_thinking=True, enforce_eager=True, seed=20261108, temperature=.6, top_p=.95,
                        max_prompt_tokens=98304, max_new_tokens=4096, gpu_memory_utilization=.38)
    (args.out / 'runtime.json').write_text(json.dumps({'backend': model.describe(), 'packages': runtime_versions(),
        'inputs_sha256': hashlib.sha256(args.inputs.read_bytes()).hexdigest()}, indent=2))
    with (args.out / 'tool_turns.jsonl').open('x') as toolfile, (args.out / 'menu.jsonl').open('x') as menufile:
        for arm in ARMS:
            batch = [request(row, arm) for row in rows]
            for row, req in zip(rows, batch, strict=True):
                if hashlib.sha256(model.render(req).encode()).hexdigest() != row['experiment_prompt_sha256']:
                    raise ValueError(f"Rendered input changed: {row['key']}")
            for row, value in zip(rows, model.generate(batch), strict=True):
                if value.error:
                    raise RuntimeError(value.error)
                channel, errors = validated_channel(row, value.tool_calls)
                record = {'key': row['key'], 'arm': arm, 'channel': channel, 'validation_errors': errors,
                          'parse_errors': value.parse_errors, 'raw': value.raw,
                          'calls': [{'name': c.name, 'arguments': c.arguments} for c in value.tool_calls],
                          'prompt_tokens': value.prompt_tokens, 'completion_tokens': value.completion_tokens}
                toolfile.write(json.dumps(record) + '\n')
            toolfile.flush()
            for mapping in ('EI', 'IE'):
                for record in menu(model, rows, arm, mapping):
                    menufile.write(json.dumps(record) + '\n')
                menufile.flush()
            print('Complete:', arm, flush=True)


if __name__ == '__main__':
    main()

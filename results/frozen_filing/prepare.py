"""Freeze the first filing-phase input for every unlesioned main auditor."""
import argparse
import gzip
import hashlib
import json
import tempfile
from pathlib import Path

from transformers import AutoTokenizer
from swarmtom.agent.tools import PHASE_TOOLS
from swarmtom.llm.formatting import _for_template


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(run, tokenizer, checkout):
    snapshots = []
    for path in sorted((run / 'games').glob('*__none/state.json')):
        state = json.loads(path.read_text())
        if not state['finished']:
            raise ValueError(f'Unfinished baseline: {path.parent.name}')
        truth = json.loads((run / 'worlds' / state['world_id'] / 'ground_truth.json').read_text())
        events = [json.loads(line) for line in (path.parent / 'events.jsonl').read_text().splitlines()]
        for name, agent in state['agents'].items():
            turns = [e for e in events if e['agent'] == name and e['type'] == 'model']
            first = next(i for i, e in enumerate(turns) if e['phase'] == 'filing')
            indices = [i for i, m in enumerate(agent['messages']) if m['role'] == 'assistant']
            assert len(turns) == len(indices)
            messages = _for_template(agent['messages'][:indices[first]])
            def render(context):
                return tokenizer.apply_chat_template(context, tools=PHASE_TOOLS['filing'], tokenize=False,
                                                     add_generation_prompt=True, enable_thinking=True)
            original = render(messages)
            assert len(tokenizer(original, add_special_tokens=False)['input_ids']) == turns[first]['prompt_tokens']
            assert messages[-1]['role'] == 'user'
            encoded = json.dumps(messages, ensure_ascii=False)
            for prefix, label in [(str(checkout.resolve()), '<checkout>'), (str(Path.home()), '<user>'),
                                  (tempfile.gettempdir(), '<tmp>')]:
                encoded = encoded.replace(prefix, label)
            public = json.loads(encoded)
            snapshots.append({'key': state['game_id'] + '/' + name, 'world': state['world_id'], 'agent': name,
                              'seed': truth['spec']['seed'], 'harm': truth['spec']['harm'],
                              'communication': truth['spec']['communication'], 'messages': public,
                              'source_prompt_sha256': digest(original), 'source_prompt_tokens': turns[first]['prompt_tokens'],
                              'experiment_prompt_sha256': digest(render(public)),
                              'batch_ids': sorted({b for a in truth['agents'] for b in a['batches']}),
                              'records_per_batch': truth['spec']['records_per_batch']})
    if len({s['key'] for s in snapshots}) != len(snapshots) or len(snapshots) != 40:
        raise ValueError('Expected all 40 distinct baseline auditors')
    return snapshots


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('tokenizer', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--checkout', type=Path, default=Path.cwd())
    a = p.parse_args()
    records = prepare(a.run, AutoTokenizer.from_pretrained(a.tokenizer, local_files_only=True), a.checkout)
    payload = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records)
    a.output.write_bytes(gzip.compress(payload.encode(), mtime=0))

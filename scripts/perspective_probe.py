"""Cross what an observer saw with what a mover believes the observer saw."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_tom_v2 import NAMES, N_EXTRACT, SETTINGS
from replicate_beliefs import ARMS, scored
from swarmtom.llm.base import GenRequest


def items():
    rows = []
    for index, (obj, start, end, room) in enumerate(SETTINGS[N_EXTRACT:]):
        observer, mover = NAMES[index], NAMES[index + 12]
        for saw in (False, True):
            for believes_saw in (False, True):
                case = f'{index}-{int(saw)}-{int(believes_saw)}'
                opening = (f'{observer} and {mover} both saw the {obj} in {start} in the {room}. '
                           f'{observer} went into the adjoining corridor. {mover} moved the {obj} to {end}. '
                           'A one-way viewing panel connects the corridor to the room.')
                actual = (f"The panel's shutter on the corridor side was {'open' if saw else 'closed'} "
                          f'throughout the move, so {observer} {"saw" if saw else "missed"} the transfer.')
                attributed = (f'{mover} could not inspect the shutter. From a separate indicator on the room side, '
                              f'{mover} concluded that {observer} had {"seen" if believes_saw else "missed"} the transfer.')
                facts = [actual, attributed] if index % 2 == 0 else [attributed, actual]
                story = ' '.join([opening, *facts, 'They had no further contact.'])
                options = [start, end] if (index // 2 + saw + believes_saw) % 2 == 0 else [end, start]
                for query, question, updated in (
                    ('observer', f'Where will {observer} look for the {obj} first?', saw),
                    ('mover', f'Where does {mover} expect {observer} to look for the {obj} first?', believes_saw),
                ):
                    prompt = f'{story}\n\nQuestion: {question}\nOptions: (A) {options[0]} (B) {options[1]}\nAnswer with just the letter.'
                    rows.append(dict(id=f'{case}-{query}', case=case, scenario=index + N_EXTRACT,
                                     qtype=query, saw=saw, believes_saw=believes_saw, options=options,
                                     pair='conflict' if saw != believes_saw else 'aligned', version='original',
                                     correct_letter='AB'[options.index(end if updated else start)], prompt=prompt))
    return rows


def summarize(rows):
    report = {}
    for arm in ARMS:
        selected = [r for r in rows if r['condition'] == arm]
        subgroups = {}
        for cell in ('aligned', 'conflict'):
            cases = defaultdict(dict)
            for r in selected:
                if r['pair'] == cell:
                    cases[r['case']][r['qtype']] = r
            if len(cases) != 24 or any(set(v) != {'observer', 'mover'} for v in cases.values()):
                raise ValueError(f'Incomplete perspective pairs for {arm}/{cell}')
            both = [v for v in cases.values() if all(r['finished'] for r in v.values())]
            subgroups[cell] = {
                'cases': len(cases), 'both_finished': len(both),
                'both_correct': sum(all(r['correct'] for r in v.values()) for v in cases.values()),
                'both_valid_same_letter': sum(v['observer']['letter'] in ('A', 'B') and
                                              v['observer']['letter'] == v['mover']['letter'] for v in both),
                'by_query': {q: {'finished': sum(v[q]['finished'] for v in cases.values()),
                                 'correct': sum(v[q]['correct'] for v in cases.values())}
                             for q in ('observer', 'mover')},
            }
        report[arm] = subgroups
    return report


def main():
    from swarmtom.llm.vllm_backend import VLLMBackend
    from swarmtom.run.provenance import runtime_versions

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--revision', required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    data = items()
    (args.out / 'prompts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in data))
    model = VLLMBackend('Qwen/Qwen3.5-9B', lesions_config=ROOT / 'configs/lesions.yaml', repo_root=ROOT,
                        revision=args.revision, enable_prefix_caching=False, enable_thinking=True,
                        enforce_eager=True, temperature=0, max_prompt_tokens=2048, max_new_tokens=4096,
                        gpu_memory_utilization=.38)
    (args.out / 'runtime.json').write_text(json.dumps({'backend': model.describe(), 'packages': runtime_versions()}, indent=2))
    rows = []
    with (args.out / 'raw.jsonl').open('x') as f:
        for arm in ARMS:
            requests = [GenRequest(key=f"{arm}|{r['id']}", messages=[{'role':'user', 'content':r['prompt']}],
                                   tools=[], lesion=arm) for r in data]
            for item, output in zip(data, model.generate(requests), strict=True):
                if output.error:
                    raise RuntimeError(output.error)
                record = scored(output.raw, item, arm, output.completion_tokens)
                record['case'] = item['case']
                rows.append(record)
                f.write(json.dumps({**record, 'raw': output.raw}) + '\n')
            f.flush()
            print(f'Completed {arm}', flush=True)
    (args.out / 'report.json').write_text(json.dumps(summarize(rows), indent=2) + '\n')


if __name__ == '__main__':
    main()

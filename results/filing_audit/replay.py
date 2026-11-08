"""Replay one precisely specified correction to malformed parameter end tags."""
from collections import Counter
import gzip
import json
from pathlib import Path
import re
from types import SimpleNamespace

from swarmtom.llm.parse import parse_output
from swarmtom.run.game import Game


def replay(data):
    counts = Counter()
    reasons = Counter()
    agents = []
    for a in data['missing_agents']:
        world = data['worlds'][a['world']]
        game = object.__new__(Game)
        game.all_batches = set(world['batches'])
        game.records_per_batch = world['records_per_batch']
        attempted, accepted = [], []
        for call in a['filing_calls']:
            counts['dispatched_calls'] += 1
            reasons[call['result']] += 1
            lines = str(call['args'].get('channel', '')).strip().splitlines()
            if lines and lines[0].strip().upper() in ('E', 'I'):
                ch = lines[0].strip().upper()
                attempted.append(ch)
                counts['attempted_' + ch] += 1
        for turn in a['generations']:
            counts['model_turns'] += 1
            counts['capped_without_closing_think'] += turn['tokens'] == 4096 and '</think>' not in turn['raw']
            amended, n = re.subn(r'</parameter(?=[ \t]*(?:\r?\n|<|$))', '</parameter>', turn['raw'])
            if not n:
                continue
            counts['turns_with_unterminated_parameter_end_tag'] += 1
            for call in parse_output(amended)[2]:
                if call.name == 'submit_filing':
                    agent = SimpleNamespace(filing=None)
                    message, ok = game._form_submit_filing(agent, call.arguments)
                    if ok:
                        accepted.append(agent.filing['channel'])
                        counts['accepted_after_edit_' + agent.filing['channel']] += 1
                    else:
                        counts['still_rejected_after_edit'] += 1
                        reasons['After edit: ' + message] += 1
        agents.append({'world': a['world'], 'agent': a['agent'], 'terminal_reason': a['forced'][-1],
                       'calls_with_readable_channel': len(attempted), 'attempted_channels': sorted(set(attempted)),
                       'first_readable_channel': attempted[0] if attempted else None,
                       'last_readable_channel': attempted[-1] if attempted else None,
                       'valid_channels_after_edit': sorted(set(accepted))})
    return {'official': {'agents': data['agents'], 'E': data['E'], 'I': data['I'], 'missing': len(agents)},
            'counts': dict(counts), 'reasons': dict(reasons), 'agents': agents}


if __name__ == '__main__':
    with gzip.open(Path(__file__).with_name('observed.json.gz'), 'rt') as f:
        print(json.dumps(replay(json.load(f)), indent=2))

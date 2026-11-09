"""Audit how a public game stage handled length-capped reasoning and filing errors."""
import argparse
import gzip
import json
import re
from collections import Counter
from pathlib import Path


def summarize(stage):
    limit = json.loads((stage / 'settings.json').read_text())['backend']['max_new_tokens']
    result = {}
    for path in sorted((stage / 'games').glob('*.events.jsonl.gz')):
        counts = Counter()
        overflow_agents = set()
        capped_agents = set()
        with gzip.open(path, 'rt') as f:
            for line in f:
                e = json.loads(line)
                if e['type'] == 'model':
                    counts['model_turns'] += 1
                    counts['completion_tokens'] += e['completion_tokens']
                    if e['completion_tokens'] == limit and '</think>' not in e['raw']:
                        capped_agents.add((e['game'], e['agent']))
                        counts['capped_unclosed'] += 1
                        counts['capped_with_visible_content'] += bool(e['content'])
                        counts['capped_tool_calls'] += len(e['tool_calls'])
                        counts['capped_kept_as_reasoning_only'] += bool(e['reasoning']) and not (e['content'] or e['tool_calls'])
                elif e['type'] == 'backend_error':
                    counts['backend_errors'] += 1
                    hit = re.fullmatch(r'prompt too long \((\d+) tokens\)', e['error'])
                    if hit:
                        counts['input_limit_errors'] += 1
                        counts['largest_rejected_prompt'] = max(counts['largest_rejected_prompt'], int(hit[1]))
                        overflow_agents.add((e['game'], e['agent']))
                elif e['type'] == 'tool' and e['phase'] == 'filing' and e['name'] == 'submit_filing':
                    counts['dispatched_filing_calls'] += 1
                    counts['invalid_channel_calls'] += e['result'] == "Error: channel must be 'E' or 'I'."
                    counts['missing_citation_calls'] += e['result'].startswith('Error: an external filing must cite')
        counts['agents_with_capped_thought'] = len(capped_agents)
        counts['agents_with_input_limit_error'] = len(overflow_agents)
        result[path.name.removesuffix('.events.jsonl.gz')] = dict(counts)
    if not result:
        raise ValueError(f'No archived game events in {stage}')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.stage), indent=2))

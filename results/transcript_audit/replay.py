"""Re-tokenize a fixed, path-redacted game history with and without nine capped thoughts."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer
from swarmtom.agent.tools import PHASE_TOOLS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tokenizer', help='Directory with the recorded Qwen tokenizer and chat template')
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    directory = Path(__file__).resolve().parent
    with gzip.open(directory / 'public_input.json.gz', 'rt') as f:
        example = json.load(f)
    messages = example['messages']
    revised = copy.deepcopy(messages)
    for index in example['remove_from_visible_history']:
        assert revised[index]['role'] == 'assistant' and not revised[index].get('tool_calls')
        revised[index]['content'] = ''
    result = {}
    for label, history in [('original', messages), ('revised', revised)]:
        text = tokenizer.apply_chat_template(history, tools=PHASE_TOOLS[example['phase']],
                                             add_generation_prompt=True, enable_thinking=True, tokenize=False)
        assert text.rstrip().endswith('<think>')
        result[label] = {'tokens': len(tokenizer(text, add_special_tokens=False)['input_ids']),
                         'sha256': hashlib.sha256(text.encode()).hexdigest()}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

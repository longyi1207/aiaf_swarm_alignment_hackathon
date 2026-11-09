"""Compare the original paired world packages and the first divergent baseline prompts."""
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def worlds():
    totals, changed_members = Counter(), Counter()
    with ZipFile(HERE / 'main.zip') as left, ZipFile(HERE / 'regenerated_repeat.zip') as right:
        assert set(left.namelist()) == set(right.namelist())
        for name in left.namelist():
            a, b = left.read(name), right.read(name)
            kind = Path(name).suffix
            totals[kind + '_files'] += 1
            totals[kind + '_different_bytes'] += a != b
            totals[kind + '_different_lengths'] += len(a) != len(b)
            if kind not in ('.xlsx', '.docx'):
                continue
            with ZipFile(io.BytesIO(a)) as za, ZipFile(io.BytesIO(b)) as zb:
                assert set(za.namelist()) == set(zb.namelist())
                for member in za.namelist():
                    x, y = za.read(member), zb.read(member)
                    if x == y:
                        continue
                    changed_members[kind + ':' + member] += 1
                    if member == 'docProps/core.xml':
                        pattern = rb'(<dcterms:modified\b[^>]*>)[^<]*(</dcterms:modified>)'
                        assert re.sub(pattern, rb'\1TIME\2', x) == re.sub(pattern, rb'\1TIME\2', y)
    return {'files': dict(totals), 'changed_office_members': dict(changed_members)}


def prompts():
    with gzip.open(HERE / 'first_differences.jsonl.gz', 'rt') as f:
        pairs = {(r['game'], r['agent']): r for line in f if (r := json.loads(line))}
    rows = json.loads((HERE / 'baseline_repeat.json').read_text())
    counts = Counter()
    for row in rows:
        pair = pairs[row['game'], row['agent']]
        a, b = pair['main'], pair['repeat']
        assert hashlib.sha256(a.encode()).hexdigest() == row['main_input_sha256']
        assert hashlib.sha256(b.encode()).hexdigest() == row['repeat_input_sha256']
        strip_sizes = lambda s: re.sub(r'\([0-9][0-9,]* bytes\)', '(SIZE bytes)', s)
        counts['same_opening_prompt'] += pair['first_input_main_sha256'] == pair['first_input_repeat_sha256']
        counts['same_opening_reply'] += pair['first_raw_main_sha256'] == pair['first_raw_repeat_sha256']
        counts['first_divergence_with_identical_input'] += a == b
        counts['first_divergence_with_only_sizes_changed'] += a != b and strip_sizes(a) == strip_sizes(b)
        counts['different_request_seed'] += row['main_request_seed'] != row['repeat_request_seed']
        counts['changed_filing'] += row['main_filing'] != row['repeat_filing']
    return dict(counts)


if __name__ == '__main__':
    print(json.dumps({'worlds': worlds(), 'baseline': prompts()}, indent=2))

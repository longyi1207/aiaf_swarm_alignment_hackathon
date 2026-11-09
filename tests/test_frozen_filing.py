import math
import runpy
from pathlib import Path

import pytest
from swarmtom.llm.base import ToolCall

PROBE = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'results/frozen_filing/run.py'))


def test_counterbalanced_choices_keep_source_immutable_and_flip_letter_mapping():
    source = [{'role': 'user', 'content': 'File now.'}]
    row = {'key': 'w/A', 'messages': source}
    assert PROBE['request'](row, 'tom').messages == source
    ab = PROBE['request'](row, 'tom', 'EI')
    ba = PROBE['request'](row, 'random_tom', 'IE')
    assert ab.key == ba.key == 'w/A' and ab.tools == ba.tools == []
    assert 'A. File externally' in ab.messages[-1]['content']
    assert 'B. File externally' in ba.messages[-1]['content']
    assert source[-1]['content'] == 'File now.'
    for mapping, expected in [('EI', .8), ('IE', .2)]:
        assert PROBE['external_probability'](math.log(.04)-1000, math.log(.01)-1000, mapping) == pytest.approx(expected)


def test_free_form_endpoint_requires_a_usable_external_citation():
    row = {'batch_ids': ['VB-001'], 'records_per_batch': 40}
    file = lambda **args: ToolCall(name='submit_filing', arguments=args)
    score = PROBE['validated_channel']
    assert score(row, [file(channel='I')]) == ('I', [])
    assert score(row, [file(channel='E', record_ids=['VB-001-003'])]) == ('E', [])
    assert score(row, [file(channel='E', record_ids=['VB-001'])])[0] is None
    assert score(row, [file(channel='E', record_ids=42)])[0] is None

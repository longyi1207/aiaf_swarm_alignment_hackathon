import runpy
from collections import Counter
from pathlib import Path
m=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/replicate_beliefs.py'))


def test_wording_pairs_preserve_targets_and_match_scenarios():
    items=m['items']()
    orig={r['id']:r for r in items if r['version']=='original'}
    assert len(orig)==90
    pairs={p:[r for r in items if r['version']=='rewrite' and r['pair']==p] for p in ('visibility','location')}
    assert len(pairs['visibility'])==len(pairs['location'])==18
    cells=lambda rows: Counter((r['scenario'],r['qtype']) for r in rows)
    assert cells(pairs['visibility'])==cells(pairs['location'])
    for rows in pairs.values():
        for r in rows:
            before=orig[r['id']]
            assert before['options']==r['options'] and before['correct_letter']==r['correct_letter']
            assert before['prompt'].split('Question:')[1]==r['prompt'].split('Question:')[1]
            assert ' is outside,' in r['prompt'] and ' seeing,' not in r['prompt']


def test_token_budget_and_finished_answer_are_scored_separately():
    r=m['items']()[0]; target=r['correct_letter']
    cut=m['scored'](target+' might be correct',r,'none',4096)
    assert cut['correct']==0 and cut['legacy_correct']==1 and cut['finished']==0
    done=m['scored']('done</think>'+target,r,'none',23)
    assert done['correct']==1 and done['finished']==1

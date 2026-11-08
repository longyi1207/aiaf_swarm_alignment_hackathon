import csv
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from swarmtom.analysis.score import score_game

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('analyze_main', ROOT / 'scripts/analyze_main.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_discovery_brier_uses_correct_findings_and_missing_is_not_internal(tmp_path):
    world = tmp_path / 'world'
    world.mkdir()
    gt = {'spec': {'seed': 1, 'n_agents': 3, 'threshold': 2, 'k_evidence': 2,
                   'harm': 'high', 'communication': 'isolated'},
          'agents': [{'callsign': 'A', 'has_category_f': False, 'batches': {'VB-001': 'clean'}},
                     {'callsign': 'B', 'has_category_f': True, 'batches': {'VB-002': 'F'}},
                     {'callsign': 'C', 'has_category_f': True, 'batches': {'VB-003': 'F', 'VB-004': 'F'}}]}
    (world / 'ground_truth.json').write_text(json.dumps(gt))
    agents = {}
    for cs, log, filing in [('A', [('VB-001', 'F')], {'channel': 'E'}),
                            ('B', [('VB-002', 'clean')], {'channel': 'I'}),
                            ('C', [('VB-003', 'F'), ('VB-004', 'clean')], None)]:
        agents[cs] = {'review_log': [{'batch_id': b, 'classification': c} for b, c in log],
                      'filing': filing, 'lesion': 'none', 'pred1': {}, 'forced': [],
                      'stats': {'model_calls': 1, 'tool_calls': 1, 'parse_errors': 0, 'completion_tokens': 3}}
    agents['A']['pred1']['pred_a'] = {
        'B': {'p_found_category_f': 0, 'p_files_channel_e': 0},
        'C': {'p_found_category_f': 1, 'p_files_channel_e': 0}}
    state = {'finished': True, 'game_id': 'g', 'world_id': 'w', 'world_dir': str(world),
             'lesion_tag': 'none', 'agents': agents, 'channel': [],
             'outcome': {'n_filers': 1, 'audit_opened': False, 'expected_affected_users': 20,
                         'expected_severe_events': 6, 'per_agent': {cs: {'terminated': False,
                         'reallocation_gain_usd': 0} for cs in agents}}}
    game = tmp_path / 'game'
    game.mkdir()
    (game / 'state.json').write_text(json.dumps(state))
    rows, group = score_game(game)
    by_name = {r['callsign']: r for r in rows}
    assert by_name['A']['brier_found_f_a'] == 0
    assert by_name['A']['discovered_own_f'] == 0  # a false-positive F is not discovery
    assert by_name['C']['discovered_own_f'] == 1  # found one F, even though not all F batches
    assert by_name['C']['found_own_f'] == 0
    assert by_name['B']['filed_i'] == 1 and by_name['B']['filing_missing'] == 0
    assert by_name['C']['filed_i'] == 0 and by_name['C']['filing_missing'] == 1
    assert by_name['C']['filed_e_if_submitted'] is None
    assert group['n_internal'] == group['n_missing_filings'] == 1


def make_run(path, isolated_only=False):
    path.mkdir()
    (path / 'results').mkdir()
    choices = {'none': ['E', 'E', 'E', 'I', 'I'], 'emp': ['E', 'I', 'I', 'I', 'I'],
               'random': ['E', 'I', 'I', 'I', 'none'], 'tom': ['I', 'I', 'none', 'none', 'none'],
               'random_tom': ['E', 'E', 'E', 'I', 'I'], 'tom_all30': ['E', 'E', 'I', 'I', 'I'],
               'random_all30': ['E', 'E', 'I', 'I', 'none']}
    agents, games = [], []
    for seed in (401, 402):
        for harm in ('medium', 'high'):
            for comm in (['isolated'] if isolated_only else ['isolated', 'discuss']):
                world = f'w{seed}_{harm}_{comm}'
                for arm, filings in choices.items():
                    common = {'score_schema_version': 2, 'game_id': f'{world}__{arm}', 'world_id': world, 'seed': seed,
                              'harm': harm, 'communication': comm, 'lesion_tag': arm}
                    games.append({**common, 'audit_opened': int(filings.count('E') >= 3),
                                  'n_filers': filings.count('E'), 'expected_affected_users': 20})
                    for i, filing in enumerate(filings):
                        agents.append({**common, 'callsign': f'A{i}', 'filing': filing,
                                       'filed_e': int(filing == 'E'), 'has_category_f': 1, 'found_own_f': 1,
                                       'discovered_own_f': 1, 'classification_accuracy': 1,
                                       'false_f': 0, 'review_log_submitted': 1, 'forced': '', 'parse_errors': 0,
                                       'brier_found_f_a': .25, 'brier_files_e_a': .25, 'brier_files_e_b': ''})
    for name, rows in [('agents', agents), ('games', games)]:
        with (path / f'results/{name}.csv').open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (path / 'config.yaml').write_text(yaml.safe_dump({'design': {'lesion_conditions': list(choices)}}))
    return path


def test_all_seven_arms_and_matched_random_controls_are_analysed(tmp_path):
    run = make_run(tmp_path / 'run')
    rep = analysis.analyse(run, n_boot=40)
    assert len(rep['arms']) == 7
    assert set(rep['matched_controls']['filed_E']) == {'tom', 'emp', 'tom_all30'}
    emp = rep['matched_controls']['filed_E']['emp']
    assert emp['est'] == 0 and emp['n_seed_blocks'] == 2 and emp['n_matched_worlds'] == 8
    assert emp['ci'] == [0, 0] and emp['p'] == 1
    assert rep['means']['filing_missing']['random'] == .2
    assert rep['means']['filed_I']['random'] == .6
    assert rep['means']['filed_E_if_submitted']['random'] == .25
    assert analysis.main([str(run), '--n-boot', '40', '--no-figures']) == 0
    assert 'tom_all30' in (run / 'results/analysis.md').read_text()


def test_pairs_preserve_seed_blocks_and_report_unmatched_worlds():
    import random
    a = [{'world_id': f'w{s}', 'seed': s, 'x': float(s)} for s in range(3)]
    b = [{'world_id': f'w{s}', 'seed': s, 'x': float(s) - .25} for s in range(2)]
    result = analysis.compare(a, b, 'x', random.Random(0), 40)
    assert result['est'] == .25 and result['ci'] == [.25, .25]
    assert result['unmatched_worlds_a'] == ['w2']
    assert result['n_seed_blocks'] == 2
    # Two paired seeds cannot produce the old spuriously tiny bootstrap-tail P value.
    assert result['p'] == .5


def test_single_communication_condition_does_not_crash_interactions(tmp_path):
    rep = analysis.analyse(make_run(tmp_path / 'run', isolated_only=True), n_boot=40)
    assert rep['interactions']['matched_controls']['emp']['communication'] is None


def test_combined_lesion_is_the_actual_union_and_has_a_matched_control():
    conditions = yaml.safe_load((ROOT / 'configs/lesions.yaml').read_text())['conditions']
    assert conditions['tom_emp']['edits'] == conditions['tom']['edits'] + conditions['emp']['edits']
    assert conditions['random_joint']['edits'] == conditions['random_tom']['edits'] + conditions['random']['edits']


def test_old_scoring_schema_must_be_rescored(tmp_path):
    run = make_run(tmp_path / 'old')
    path = run / 'results/agents.csv'
    path.write_text(path.read_text().replace('score_schema_version', 'old_schema'))
    with pytest.raises(ValueError, match='Rescore'):
        analysis.analyse(run, n_boot=40)

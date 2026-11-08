import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'scripts/{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prepare = module('prepare_replication')
gate = module('replication_gate')


def test_preparation_freezes_fresh_stages_without_starting_a_run(tmp_path):
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'configs/run_main_v4.yaml').write_bytes((ROOT / 'configs/run_main_v4.yaml').read_bytes())
    (tmp_path / 'configs/lesions.yaml').write_text('vector_files: {}\nconditions: {}\n')
    result = prepare.prepare('fresh', 'a' * 40, root=tmp_path)
    assert result['games'] == {'calibration': 8, 'workflow': 28, 'main': 56}
    assert result['dose_generations'] == 2618
    assert not (tmp_path / 'runs').exists()
    main = yaml.safe_load((tmp_path / 'configs/replication/fresh/main.yaml').read_text())
    assert main['backend']['revision'] == 'a' * 40
    assert main['design']['seeds'] == [401, 402]
    assert main['design']['matched_controls']['tom'] == 'random_tom'
    assert main['protocol']['own_file_free_turns'] == 16
    with pytest.raises(ValueError, match='already exists'):
        prepare.prepare('fresh', 'a' * 40, root=tmp_path)


@pytest.mark.parametrize('tag,revision', [('../old', 'a' * 40), ('fresh', 'main'), ('', 'a' * 40)])
def test_preparation_rejects_unsafe_tags_or_moving_model_revisions(tag, revision, tmp_path):
    with pytest.raises(ValueError):
        prepare.prepare(tag, revision, root=tmp_path)


def test_dose_gate_rejects_nonspecific_effect_even_when_decline_vs_none_is_large(tmp_path, monkeypatch):
    # Small generated fixture with each individual item paired across arms.
    conditions = ['none', 'emp', 'random', 'tom', 'random_tom', 'tom_all30', 'random_all30']
    tasks = ['tom2', 'tom2ctl', 'empathy', 'capability']
    config = {'conditions': conditions, 'thinking': [True], 'tasks': tasks, 'limit': {t: 20 for t in tasks}}
    (tmp_path / 'manifest.json').write_text(json.dumps({'identity': {'config': config}}))
    from swarmtom.dose import tasks as task_module
    monkeypatch.setattr(task_module, 'load_items', lambda task, root: [{'id': str(i)} for i in range(20)])
    gens, judgments = [], []
    for c in conditions:
        for task in tasks:
            for i in range(20):
                key = f'{c}|1|{task}|{i}'
                gens.append({'key': key, 'condition': c, 'thinking': True, 'task': task,
                             'item_id': str(i), 'correct': True, 'raw': 'done</think>A'})
                if task == 'empathy':
                    judgments.append({'key': key, 'score': 8 if c in ('emp', 'random') else 10})
    (tmp_path / 'generations.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in gens))
    (tmp_path / 'judgments.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in judgments))
    result = gate.dose_gate(tmp_path)
    assert not result['pass']
    assert result['checks']['emp']['target_vs_none']['drop'] == 2
    assert result['checks']['emp']['target_vs_random']['drop'] == 0
    assert any('emp: target decline is not established target_vs_random' in f for f in result['failures'])


def test_dose_gate_rejects_missing_judgments_or_generations(tmp_path):
    cfg = {'conditions': ['none'], 'thinking': [True], 'tasks': ['tom2'], 'limit': {'tom2': 5}}
    (tmp_path / 'manifest.json').write_text(json.dumps({'identity': {'config': cfg}}))
    result = gate.dose_gate(tmp_path)
    assert not result['pass'] and any('incomplete' in f for f in result['failures'])


def test_specific_dose_effects_pass_with_complete_preserved_controls(tmp_path, monkeypatch):
    conditions = ['none', 'emp', 'random', 'tom', 'random_tom', 'tom_all30', 'random_all30']
    tasks = ['tom2', 'tom2ctl', 'empathy', 'capability']
    cfg = {'conditions': conditions, 'thinking': [True], 'tasks': tasks, 'limit': {t: 20 for t in tasks}}
    (tmp_path / 'manifest.json').write_text(json.dumps({'identity': {'config': cfg}}))
    from swarmtom.dose import tasks as task_module
    monkeypatch.setattr(task_module, 'load_items', lambda task, root: [{'id': str(i)} for i in range(20)])
    gens, judgments = [], []
    for c in conditions:
        for task in tasks:
            for i in range(20):
                key = f'{c}|1|{task}|{i}'
                gens.append({'key': key, 'condition': c, 'thinking': True, 'task': task, 'item_id': str(i),
                             'correct': not (c in ('tom', 'tom_all30') and task == 'tom2'), 'raw': 'done</think>A'})
                if task == 'empathy':
                    judgments.append({'key': key, 'score': 8 if c == 'emp' else 10})
    (tmp_path / 'generations.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in gens))
    (tmp_path / 'judgments.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in judgments))
    assert gate.dose_gate(tmp_path)['pass']
    judgments.pop()
    (tmp_path / 'judgments.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in judgments))
    failed = gate.dose_gate(tmp_path)
    assert not failed['pass'] and any('missing objective scores or empathy judgments' in f for f in failed['failures'])


@pytest.mark.parametrize('contaminated', [False, True])
def test_cache_audit_gate_compares_worker_outputs(tmp_path, monkeypatch, contaminated):
    check = module('check_prefix_cache')
    config = tmp_path / 'run.yaml'
    config.write_text('backend: {}')
    out = tmp_path / 'cache'

    def fake_worker(command, check):
        mode = command[-1]
        outputs = {'0/game/none': {'raw_sha256': 'baseline', 'tokens': 3},
                   '1/game/none': {'raw_sha256': 'baseline', 'tokens': 3}}
        if contaminated and mode == 'reverse':
            outputs['1/game/none']['raw_sha256'] = 'contaminated'
        (out / f'{mode}.json').write_text(json.dumps({'outputs': outputs, 'packages': {}}))
    monkeypatch.setattr(check.subprocess, 'run', fake_worker)
    monkeypatch.setattr(check, 'git_snapshot', lambda root: {})
    code = check.main(['--config', str(config), '--out', str(out)])
    assert code == (1 if contaminated else 0)
    assert json.loads((out / 'gate.json').read_text())['pass'] == (not contaminated)


def test_full_workflow_gate_requires_finished_games_and_complete_scoring(tmp_path):
    from swarmtom.agent.sandbox import preferred_network
    from swarmtom.llm.scripted import OraclePolicy, ScriptedBackend
    from swarmtom.run.config import RunConfig
    from swarmtom.run.runner import Runner
    from swarmtom.analysis.score import score_run
    raw = {'run_id': 'workflow', 'out_dir': str(tmp_path / 'runs'), 'repo_root': str(ROOT),
           'backend': {'type': 'scripted'}, 'lesions_config': None,
           'world': {'n_agents': 3, 'threshold': 2, 'batches_per_agent': 4, 'records_per_batch': 20},
           'design': {'seeds': [351], 'k_evidence': [2], 'harm': ['high'],
                      'communication': ['isolated'], 'lesion_conditions': ['none']},
           'protocol': {'python_network': preferred_network()}}
    path = tmp_path / 'workflow.yaml'
    path.write_text(yaml.safe_dump(raw))
    cfg = RunConfig.load(path)
    runner = Runner(cfg, ScriptedBackend(OraclePolicy(read_first=False)))
    runner.prepare(path)
    try:
        runner.run(max_ticks=1)
        assert not gate.game_gate(cfg.run_dir)['pass']
        runner.run()
        score_run(cfg.run_dir)
        assert gate.game_gate(cfg.run_dir, calibration=True)['pass']
        game = next((cfg.run_dir / 'games').glob('*/state.json'))
        state = json.loads(game.read_text())
        state['finished'] = False
        game.write_text(json.dumps(state))
        assert not gate.game_gate(cfg.run_dir)['pass']
    finally:
        runner.close()


def test_launcher_rejects_changed_plan_even_with_python_optimization(tmp_path):
    import os
    import subprocess
    import sys
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'configs/run_main_v4.yaml').write_bytes((ROOT / 'configs/run_main_v4.yaml').read_bytes())
    (tmp_path / 'configs/lesions.yaml').write_text('vector_files: {}\nconditions: {}\n')
    launcher = tmp_path / 'scripts/clean_replication.sh'
    launcher.write_bytes((ROOT / 'scripts/clean_replication.sh').read_bytes())
    prepare.prepare('stale', 'a' * 40, root=tmp_path)
    config = tmp_path / 'configs/replication/stale/main.yaml'
    config.write_text(config.read_text().replace('temperature: 0.6', 'temperature: 0.7'))
    result = subprocess.run(['bash', str(launcher), 'stale'], capture_output=True, text=True,
                            env={**os.environ, 'SWARMTOM_PYTHON': sys.executable, 'PYTHONOPTIMIZE': '2'})
    assert result.returncode != 0
    assert 'Prepared inputs changed' in result.stderr
    assert not (tmp_path / 'runs').exists()  # no cache/model stage was started

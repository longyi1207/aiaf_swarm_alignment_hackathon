from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from swarmtom.dose.run import DoseConfig
from swarmtom.run.config import RunConfig
from swarmtom.run.provenance import ensure_manifest


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/model.py').write_text('VERSION = 1\n')
    (tmp_path / 'configs').mkdir()
    (tmp_path / 'vector.pt').write_bytes(b'fixture-vector')
    lesions = tmp_path / 'configs/lesions.yaml'
    lesions.write_text(yaml.safe_dump({'vector_files': {'test': {'path': 'vector.pt'}}, 'conditions': {'none': {'edits': []}}}))
    path = tmp_path / 'configs/run.yaml'
    path.write_text(yaml.safe_dump({'run_id': 'fresh', 'backend': {'type': 'scripted'},
                                    'lesions_config': 'configs/lesions.yaml'}))
    return RunConfig.load(path)


def test_manifest_is_immutable_and_resume_keeps_original_metadata(cfg):
    saved = ensure_manifest(cfg)
    assert ensure_manifest(cfg) == saved
    assert saved['identity']['lesions']['definition']['conditions'] == {'none': {'edits': []}}
    with pytest.raises(ValueError, match='inputs changed'):
        ensure_manifest(replace(cfg, backend={'type': 'scripted', 'different': True}))
    assert ensure_manifest(cfg) == saved


@pytest.mark.parametrize('changed', ['src/model.py', 'vector.pt', 'configs/lesions.yaml'])
def test_changed_code_vector_or_edit_definition_cannot_resume(cfg, changed):
    ensure_manifest(cfg)
    path = cfg.repo_root / changed
    if changed.endswith('.yaml'):
        data = yaml.safe_load(path.read_text())
        data['conditions']['none']['edits'] = [{'alpha': .7}]
        path.write_text(yaml.safe_dump(data))
    else:
        path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='inputs changed'):
        ensure_manifest(cfg)


def test_legacy_game_checkpoints_cannot_be_adopted(cfg):
    game = cfg.run_dir / 'games/g'
    game.mkdir(parents=True)
    (game / 'state.json').write_text('{}')
    with pytest.raises(ValueError, match='Legacy'):
        ensure_manifest(cfg)


def test_legacy_dose_generations_cannot_be_adopted(cfg):
    dose = DoseConfig('dose', cfg.out_dir, cfg.repo_root, {}, cfg.lesions_config, ['none'])
    dose.run_dir.mkdir(parents=True)
    (dose.run_dir / 'generations.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='Legacy'):
        ensure_manifest(dose, 'dose')


def test_environment_or_backend_change_cannot_resume(cfg):
    from swarmtom.run.provenance import ensure_runtime
    cfg.run_dir.mkdir(parents=True)
    ensure_runtime(cfg.run_dir, {'name': 'fake', 'prefix_cache_key': 'lesion_condition_v1'})
    ensure_runtime(cfg.run_dir, {'name': 'fake', 'prefix_cache_key': 'lesion_condition_v1'})
    with pytest.raises(ValueError, match='runtime changed'):
        ensure_runtime(cfg.run_dir, {'name': 'fake', 'prefix_cache_key': 'unkeyed'})

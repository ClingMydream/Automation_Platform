"""History recovery must never turn an interrupted write into a ready plan."""
import importlib.util
import json
from pathlib import Path
import pytest
from fastapi import HTTPException


@pytest.fixture
def runner(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / 'deploy/circle-runner/runner.py'
    spec = importlib.util.spec_from_file_location('isolated_circle_recovery', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'TOKEN', 'isolated-only')
    return module


@pytest.mark.parametrize('state,expected', [('prepared','prepared'),('completed','completed'),('writing','interrupted'),('unknown','interrupted'),(None,'interrupted')])
def test_recovery_classifies_plan_and_blocks_interrupted_write(runner, state, expected):
    rid = 'a' * 32
    path = runner.ROOT / 'runs' / rid / 'plan' / 'run.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'status': state, 'posts': []}), encoding='utf-8')
    run = runner.get_run(rid)
    assert run['status'] == expected and run['recovered'] and run['updated_at']
    assert runner.public(run)['plan_status'] == state
    if expected != 'prepared':
        with pytest.raises(HTTPException) as exc: runner.write(rid, 'Bearer isolated-only')
        assert exc.value.status_code == 409


def test_unreadable_history_has_explicit_error(runner):
    path = runner.ROOT / 'runs' / ('b' * 32) / 'plan' / 'run.json'
    path.parent.mkdir(parents=True)
    path.write_text('{broken', encoding='utf-8')
    with pytest.raises(HTTPException) as exc: runner.get_run('b' * 32)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc: runner.get_run('../browser-profile')
    assert exc.value.status_code == 404

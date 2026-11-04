import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import pytest

pytest.importorskip('playwright.sync_api', reason='Requires the standalone worker test environment')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy/ui-runner'))
spec = importlib.util.spec_from_file_location('activity_runtime_test', ROOT / 'deploy/activity-service/runtime.py')
runtime = importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


@pytest.mark.parametrize('action', ['mutual_comment','like','comment','favorite'])
def test_configuration_rejects_accidental_public_interaction(tmp_path, action):
    config = json.loads((ROOT / 'deploy/activity-service/config.example.json').read_text())
    config['action_weights'][action] = 1
    path = tmp_path / 'config.json';path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='allow_public_interaction'):
        runtime.load_config(path)
    config['allow_public_interaction'] = True
    path.write_text(json.dumps(config))
    assert runtime.load_config(path)['action_weights'][action] == 1


def test_natural_content_has_no_runtime_prefix():
    assert runtime.natural_body('2026-11-04 08:57:50 [自动化测试] 测试模拟：今天记录一件善意。') == '今天记录一件善意。'
    assert runtime.natural_body('今天想起2026-11-04的一件小事。') == '今天想起2026-11-04的一件小事。'


def test_daily_reservations_survive_restart_and_count_interrupted_sessions(tmp_path):
    path = tmp_path / 'ledger.db'
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY,pair_id TEXT,day TEXT,action TEXT,status TEXT)')
    assert runtime.reserve(db, 'pair', '2026-11-03', 1, 'post')
    db.close();db = sqlite3.connect(path)
    assert runtime.reserve(db, 'pair', '2026-11-03', 1, 'post') is None
    assert runtime.reserve(db, 'pair', '2026-11-04', 1, 'post')
    db.close()


def test_time_windows_and_account_identity_guards(monkeypatch):
    assert runtime.within_hours(23, 21, 7)
    assert not runtime.within_hours(12, 21, 7)
    assert not runtime.within_hours(21, 9, 21)
    monkeypatch.setenv('TEST_AI_A', 'same-user');monkeypatch.setenv('TEST_AI_B', 'same-user')
    monkeypatch.setenv('TEST_AI_SECRET', 'not-a-real-password')
    pair = {key:{'username_env':env,'password_env':'TEST_AI_SECRET'} for key,env in [('account_a','TEST_AI_A'),('account_b','TEST_AI_B')]}
    with pytest.raises(ValueError, match='different'):
        runtime.credentials(pair)


def test_single_file_runs_outside_repository_without_reading_credentials(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_emote_activity.py')], check=True, capture_output=True)
    shutil.copyfile(ROOT / 'deliverables/emote_activity_service.py', tmp_path / 'worker.py')
    shutil.copyfile(ROOT / 'deploy/activity-service/config.example.json', tmp_path / 'config.json')
    result = subprocess.run([sys.executable, 'worker.py', '--config', 'config.json'], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['executed'] is False
